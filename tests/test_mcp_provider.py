import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from jev_cli.models import DecisionContract, StatePacket  # noqa: E402
from jev_cli.providers.mcp import MCPConfig, MCPProvider  # noqa: E402

SERVER = """
import json
import sys
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP

server = FastMCP("test-jev")
mode, log = sys.argv[1:]

@server.tool()
def jev_capabilities() -> dict[str, Any]:
    Path(log + ".caps").write_text("capabilities")
    caps = {"model": "jev-1.13.0", "providers": {
        "primary": {"id": "typesafe_direct", "enabled": True, "model": "jev-1.13.0"},
        "fallback": {"id": "openrouter", "enabled": mode != "disabled-fallback",
                     "model": "typesafe/jev-1.13"}
    }}
    if mode == "missing-providers": del caps["providers"]
    if mode == "missing-fallback": del caps["providers"]["fallback"]
    if mode == "null-fallback": caps["providers"]["fallback"] = None
    if mode == "missing-primary": del caps["providers"]["primary"]
    if mode == "null-primary": caps["providers"]["primary"] = None
    if mode == "disabled-primary": caps["providers"]["primary"]["enabled"] = False
    return caps

@server.tool()
def jev_evaluate(request: dict[str, Any]) -> dict[str, Any]:
    Path(log).write_text(json.dumps(request))
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
    if mode in {"dated", "credit-exhausted"}:
        result["resolved_model"] = "typesafe/jev-1.13-20260917"
    if mode == "credit-exhausted":
        result["fallback_reason"] = "provider_credit_exhausted"
        result["provider_attempts"][0]["error"]["code"] = "provider_credit_exhausted"
    if mode == "prefix-collision":
        result["resolved_model"] = "typesafe/jev-1.130-20260917"
    if mode == "wrong-requested-model":
        result["requested_model"] = "typesafe/jev-1.14"
    if mode == "wrong-provider":
        result["provider"] = "unadvertised-provider"
    if mode in {"primary", "missing-primary", "null-primary", "disabled-primary",
                "wrong-primary-provider", "primary-versioned"}:
        result.update(fallback_used=False, provider="typesafe_direct",
                      requested_model="jev-1.13.0", resolved_model="jev-1.13.0",
                      fallback_reason=None,
                      provider_attempts=[{"provider": "typesafe_direct", "status": "ok"}])
    if mode == "wrong-primary-provider":
        result["provider"] = "unadvertised-provider"
    if mode == "primary-versioned":
        result["resolved_model"] = "jev-1.13.0-20260917"
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


@pytest.fixture
def wire_replies(monkeypatch):
    """Observe actual SDK replies so a connection timeout cannot pass rejection tests."""
    from mcp import ClientSession

    replies = {}
    original = ClientSession.call_tool

    async def observed(self, name, *args, **kwargs):
        """Retain the returned SDK object without replacing transport or validation."""
        result = await original(self, name, *args, **kwargs)
        replies[name] = result
        return result

    monkeypatch.setattr(ClientSession, "call_tool", observed)
    return replies


@pytest.mark.parametrize(
    ("mode", "requested", "resolved", "fallback"),
    [
        ("ok", "typesafe/jev-1.13", "typesafe/jev-1.13", True),
        ("dated", "typesafe/jev-1.13", "typesafe/jev-1.13-20260917", True),
        ("credit-exhausted", "typesafe/jev-1.13", "typesafe/jev-1.13-20260917", True),
        ("primary", "jev-1.13.0", "jev-1.13.0", False),
    ],
)
def test_stdio_mcp_roundtrip_preserves_routing_without_unknown_fields(
    tmp_path, contract, mode, requested, resolved, fallback
) -> None:
    """Preserve the requested alias and returned model version through real stdio."""
    result = provider(tmp_path, mode).evaluate(contract, StatePacket(data={"evidence": "ready"}))
    assert result.answers["route"].value == "inspect"
    assert result.answers["present"].value == 0.7
    assert result.answers["priority"].value == 0.25
    assert result.metadata is not None
    assert result.metadata["fallback_used"] is fallback
    assert len(result.metadata["provider_attempts"]) == (2 if fallback else 1)
    assert result.metadata["service_provider"] == ("openrouter" if fallback else "typesafe_direct")
    expected_reason = "provider_credit_exhausted" if mode == "credit-exhausted" else "rate_limited"
    assert result.metadata["fallback_reason"] == (expected_reason if fallback else None)
    if fallback:
        assert result.metadata["provider_attempts"][0]["error_code"] == expected_reason
    assert result.usage is not None
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5
    assert result.requested_model == requested
    assert result.resolved_model == resolved
    assert json.loads((tmp_path / "called").read_text())["contract_id"] == contract.id
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
        "prefix-collision",
        "wrong-requested-model",
        "wrong-provider",
        "disabled-fallback",
        "missing-providers",
        "missing-fallback",
        "null-fallback",
        "missing-primary",
        "null-primary",
        "disabled-primary",
        "wrong-primary-provider",
        "primary-versioned",
    ],
)
def test_stdio_mcp_rejects_invalid_receipts(tmp_path, contract, mode, wire_replies) -> None:
    """Reject a delivered invalid receipt, not an earlier initialization timeout."""
    with pytest.raises(RuntimeError, match="MCP evaluation failed") as caught:
        provider(tmp_path, mode).evaluate(contract, StatePacket(data="private-state"))
    assert "private" not in str(caught.value)
    assert (tmp_path / "called").exists()
    assert isinstance(wire_replies["jev_evaluate"].structuredContent, dict)


def test_model_mismatch_refused_before_evaluation(tmp_path, contract, wire_replies) -> None:
    """Require a capability response before refusing a mismatched primary pin."""
    contract.model = "jev-9.9.9"
    with pytest.raises(RuntimeError):
        provider(tmp_path, "ok").evaluate(contract, StatePacket(data="evidence"))
    assert not (tmp_path / "called").exists()
    assert (tmp_path / "called.caps").exists()
    assert "jev_capabilities" in wire_replies
    assert "jev_evaluate" not in wire_replies


def test_public_catalog_cli_uses_actual_stdio_transport(tmp_path, contract) -> None:
    """Round-trip a versioned fallback receipt through catalog persistence and CLI output."""
    from typer.testing import CliRunner

    from jev_cli.cli import app

    p = provider(tmp_path, "dated")
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
    assert saved[0]["receipt"]["requested_model"] == "typesafe/jev-1.13"
    assert saved[0]["receipt"]["resolved_model"] == "typesafe/jev-1.13-20260917"
    assert saved[0]["receipt"] == json.loads(result.stdout)
