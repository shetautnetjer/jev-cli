import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from jev_cli.models import DecisionContract, StatePacket  # noqa: E402
from jev_cli.providers.mcp import MCPConfig, MCPProvider  # noqa: E402

SERVER = """
import sys
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP

server = FastMCP("test-jev")
mode, log = sys.argv[1:]

@server.tool()
def jev_capabilities() -> dict[str, Any]:
    return {"model": "jev-1.13.0", "providers": {
        "primary": {"id": "typesafe_direct", "enabled": True, "model": "jev-1.13.0"},
        "fallback": {"id": "openrouter", "enabled": True, "model": "typesafe/jev-1.13"}
    }}

@server.tool()
def jev_evaluate(request: dict[str, Any]) -> dict[str, Any]:
    Path(log).write_text("evaluated")
    if mode == "error":
        return {"status": "error", "error": {"code": "private-secret-marker"}}
    answers = {
      "route": {"type": "choice", "choice": "inspect",
                "probabilities": {"inspect": 0.8, "unknown_no_match": 0.2}, "confidence": 0.8},
      "present": {"type": "noul", "noul": 0.7},
      "priority": {"type": "score", "score": 0.25,
                   "probabilities": {"0": 0.75, "1": 0.25}, "confidence": 0.75}
    }
    if mode == "partial": del answers["present"]
    if mode == "invalid": answers["route"]["choice"] = "invented"
    if mode == "wrong-contract": request["contract_id"] = "other"
    result = {
      "status": "ok", "project_id": request["project_id"], "contract_id": request["contract_id"],
      "contract_version": request["contract_version"], "request_id": "test-request",
      "provider": "openrouter", "requested_model": "typesafe/jev-1.13",
      "resolved_model": "typesafe/jev-1.13", "fallback_used": True,
      "fallback_reason": "rate_limited", "provider_attempts": [
        {"provider": "typesafe", "status": "error", "error": {"code": "rate_limited"}},
        {"provider": "openrouter", "status": "ok"}
      ], "elapsed_ms": 25, "usage": {"input_tokens": 10, "output_tokens": 5},
      "answers": answers, "private_unexpected_field": "private-secret-marker"
    }
    if mode == "wrong-primary-model":
        result.update(fallback_used=False, provider="typesafe_direct",
                      requested_model="unrelated-model", resolved_model="unrelated-model")
    if mode == "wrong-fallback-model":
        result.update(requested_model="unrelated-model", resolved_model="unrelated-model")
    return result

server.run(transport="stdio")
"""


@pytest.fixture
def contract() -> DecisionContract:
    return DecisionContract(
        id="test.route",
        version="1",
        model="jev-1.13.0",
        questions={
            "route": {
                "type": "choice",
                "instructions": "Which action?",
                "criteria": {"inspect": "Read", "unknown_no_match": "No match"},
            },
            "present": {"type": "noul", "instructions": "Is evidence present?"},
            "priority": {"type": "score", "instructions": "Urgency?", "criteria": ["Low", "High"]},
        },
    )


def provider(tmp_path: Path, mode: str) -> MCPProvider:
    script = tmp_path / "server.py"
    script.write_text(SERVER)
    return MCPProvider(
        MCPConfig(
            command=sys.executable,
            args=[str(script), mode, str(tmp_path / "called")],
            project_id="test",
            timeout_seconds=10,
        )
    )


def test_stdio_mcp_roundtrip_preserves_routing_without_unknown_fields(tmp_path, contract) -> None:
    result = provider(tmp_path, "ok").evaluate(contract, StatePacket(data={"evidence": "ready"}))
    assert result.answers["route"].value == "inspect"
    assert result.answers["present"].value == 0.7
    assert result.answers["priority"].value == 0.25
    assert result.metadata["fallback_used"] is True
    assert len(result.metadata["provider_attempts"]) == 2
    assert "private-secret-marker" not in result.model_dump_json()


@pytest.mark.parametrize(
    "mode",
    [
        "partial",
        "invalid",
        "wrong-contract",
        "error",
        "wrong-primary-model",
        "wrong-fallback-model",
    ],
)
def test_stdio_mcp_rejects_invalid_receipts(tmp_path, contract, mode) -> None:
    with pytest.raises(RuntimeError, match="MCP evaluation failed") as caught:
        provider(tmp_path, mode).evaluate(contract, StatePacket(data="private-state"))
    assert "private" not in str(caught.value)


def test_model_mismatch_refused_before_evaluation(tmp_path, contract) -> None:
    contract.model = "jev-9.9.9"
    with pytest.raises(RuntimeError):
        provider(tmp_path, "ok").evaluate(contract, StatePacket(data="evidence"))
    assert not (tmp_path / "called").exists()


def test_public_catalog_cli_uses_actual_stdio_transport(tmp_path, contract) -> None:
    from typer.testing import CliRunner

    from jev_cli.cli import app

    p = provider(tmp_path, "ok")
    config = tmp_path / "mcp.json"
    config.write_text(p.config.model_dump_json())
    source = tmp_path / "contract.json"
    source.write_text(contract.model_dump_json())
    db = tmp_path / "catalog.sqlite"
    runner = CliRunner()
    assert runner.invoke(app, ["catalog", "import", str(source), "--db", str(db)]).exit_code == 0
    result = runner.invoke(
        app,
        [
            "catalog",
            "run",
            contract.id,
            contract.version,
            "--db",
            str(db),
            "--run-id",
            "r",
            "--step-id",
            "s",
            "--provider",
            "mcp",
            "--mcp-config",
            str(config),
            "--state",
            "Observed evidence",
        ],
    )
    assert result.exit_code == 0, result.output
    saved = json.loads(runner.invoke(app, ["catalog", "decisions", "r", "--db", str(db)]).stdout)
    assert saved[0]["receipt"]["provider_metadata"]["fallback_used"] is True
    assert saved[0]["receipt"] == json.loads(result.stdout)
