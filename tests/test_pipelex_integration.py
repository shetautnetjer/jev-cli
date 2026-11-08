"""Optional integration: run the real Pipelex interpreter, with Jev mocked at HTTP only."""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

pytest.importorskip("pipelex")

PILOT = Path(__file__).resolve().parents[1] / "integrations" / "pipelex"
sys.path.insert(0, str(PILOT))

from function_only_runtime import boot  # noqa: E402
from jev_method import (  # noqa: E402
    DecisionInput,
    DecisionOutput,
    bind_provider,
)
from pipelex.pipelex import Pipelex  # noqa: E402
from pipelex.pipeline.runner import PipelexMTHDSProtocol  # noqa: E402

from jev_cli.models import DecisionContract, StatePacket  # noqa: E402
from jev_cli.providers.typesafe import TypeSafeProvider  # noqa: E402


@pytest.fixture
def pipelex_runtime(monkeypatch, tmp_path):
    monkeypatch.chdir(PILOT)
    boot()
    yield
    Pipelex.teardown_if_needed()


@pytest.mark.parametrize(
    "probability,default_route,expected",
    [
        (0.95, "needs_evidence", "ready"),
        (0.5, "needs_evidence", "needs_evidence"),
        (0.5, "unrepresented", "unknown_no_match"),
    ],
)
def test_pipelex_runs_32_questions_then_branches(
    pipelex_runtime, probability, default_route, expected
):
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": {
                    key: {"type": "noul", "noul": probability} for key in payload["questions"]
                },
                "usage": {"input_tokens": 500, "output_tokens": 64},
            },
        )

    contract = DecisionContract(
        id="example.memory-evidence",
        version="1",
        model="jev-1.13.0",
        questions={
            f"q{i}": {"type": "noul", "instructions": f"Does evidence support claim {i}?"}
            for i in range(32)
        },
        composition={
            "rules": [{"question": "q0", "operator": "gte", "value": 0.8, "result": "ready"}],
            "default": default_route,
        },
    )
    packet = DecisionInput(
        contract=contract,
        state=StatePacket(data={"text": "source evidence"}, reference="fixture:1"),
    )

    async def run():
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with bind_provider(TypeSafeProvider(api_key="fake-test-key", client=client)):
                return await PipelexMTHDSProtocol(library_dirs=[]).execute(
                    mthds_contents=[(PILOT / "decision.mthds").read_text()],
                    inputs={
                        "packet": {"concept": "jev_workflows.DecisionInput", "content": packet}
                    },
                )

    result = asyncio.run(run())
    output = result.pipe_output.main_stuff.content
    assert isinstance(output, DecisionOutput)
    assert output.disposition == expected
    assert len(output.receipt.answers) == 32
    assert len(calls) == 1
    assert output.receipt.state_reference == "fixture:1"
    assert output.receipt.composition == ("ready" if probability == 0.95 else default_route)


def test_pipelex_provider_scope_survives_concurrent_worker_threads(pipelex_runtime):
    """Two agents sharing an interpreter must never borrow each other's provider."""
    import time

    from jev_method import evaluate_jev
    from pipelex.core.concepts.concept_factory import ConceptFactory
    from pipelex.core.memory.working_memory_factory import WorkingMemoryFactory
    from pipelex.core.stuffs.stuff_factory import StuffFactory

    from jev_cli.providers.mock import MockProvider

    def packet(value):
        contract = DecisionContract(
            id="example.scope",
            version="1",
            questions={
                "route": {
                    "type": "choice",
                    "instructions": "Which route?",
                    "criteria": {"first": "First", "second": "Second"},
                }
            },
        )
        concept = ConceptFactory.make(
            concept_code="DecisionInput",
            domain_code="jev_workflows",
            description="Test input",
            structure_class_name="DecisionInput",
        )
        return WorkingMemoryFactory.make_from_single_stuff(
            StuffFactory.make_stuff(
                concept=concept,
                content=DecisionInput(contract=contract, state=StatePacket(data={"marker": value})),
                name="packet",
            )
        )

    class ScopedProvider(MockProvider):
        def __init__(self, value):
            self.value = value

        def evaluate(self, contract, state):
            time.sleep(0.02)
            assert state.data["marker"] == self.value
            return super().evaluate(
                contract, StatePacket(data={"__mock_answers__": {"route": self.value}})
            )

    async def one(value):
        with bind_provider(ScopedProvider(value)):
            return await asyncio.to_thread(evaluate_jev, packet(value))

    async def run():
        return await asyncio.gather(one("first"), one("second"))

    assert [r.disposition for r in asyncio.run(run())] == ["first", "second"]
    with pytest.raises(RuntimeError, match="bind"):
        evaluate_jev(packet("first"))


@pytest.mark.parametrize("broken", [False, True, "invalid-json"])
def test_pilot_cli_has_one_json_result_and_does_not_log_private_inputs(tmp_path, broken):
    import subprocess

    import yaml

    contract = yaml.safe_load((PILOT / "contract.yaml").read_text())
    if broken is True:
        contract.pop("composition")
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract))
    state_path = tmp_path / "state.json"
    state_path.write_text(
        "private-source-marker"
        if broken == "invalid-json"
        else json.dumps(
            {
                "private-source-marker": "must not be printed",
                "__mock_answers__": {"supported": 0.95, "kind": "decision", "clarity": 2},
            }
        )
    )
    result = subprocess.run(
        [
            sys.executable,
            str(PILOT / "run_pilot.py"),
            "--contract",
            str(contract_path),
            "--state-file",
            str(state_path),
            "--reference",
            "fixture:cli",
            "--provider",
            "mock",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert "private-source-marker" not in result.stdout + result.stderr
    payload = json.loads(result.stdout)
    if broken:
        assert result.returncode == 1
        assert payload["status"] == "failed"
    else:
        assert result.returncode == 0
        assert payload["disposition"] == "ready"
