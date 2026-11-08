"""Offline Monty/catalog feasibility probe; no model, network or production DB calls.

Run in an isolated environment containing pydantic-monty==1.0.0 and this project's
ordinary dependencies. The mock provider tests orchestration, not model quality.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pydantic_monty import FunctionSnapshot, Monty, MontyComplete  # noqa: E402

from jev_cli.catalog import connect, find_contracts, import_contract, observe_decision  # noqa: E402
from jev_cli.hooks import HookConfig, HookEvent, run_hook  # noqa: E402
from jev_cli.io import load_contract  # noqa: E402
from jev_cli.providers.mock import MockProvider  # noqa: E402

PROGRAM = """
matches = find_questions(query)
if len(matches) != 1:
    result = {"status": "unknown_no_match", "candidates": len(matches)}
else:
    item = matches[0]
    result = answer_question(item["contract_id"], item["version"], evidence)
result
"""


class CountingMock(MockProvider):
    def __init__(self):
        self.calls = 0

    def evaluate(self, contract, state):
        """Count inference and unwrap hook evidence before applying explicit mock answers."""
        self.calls += 1
        # Hook packets wrap the fixture under evidence. Explicit mock answers
        # avoid treating JSON option order as a semantic decision.
        fixture = state.model_copy(update={"data": state.data["evidence"]})
        return super().evaluate(contract, fixture)


def probe():
    """Exercise snapshot restore, durable hook replay and separate observed outcomes offline."""
    provider = CountingMock()
    with tempfile.TemporaryDirectory(prefix="jev-monty-probe-") as temporary:
        db = connect(Path(temporary) / "catalog.sqlite")
        try:
            contract = load_contract(ROOT / "examples/route.yaml")
            fingerprint = import_contract(
                db, contract, scope="probe", source_ref="examples/route.yaml"
            )
            config = HookConfig.model_validate(
                {
                    "routes": {
                        "probe.route": {"contract_id": contract.id, "version": contract.version}
                    }
                }
            )

            def find_questions(query):
                """Limit interpreter discovery to the temporary probe catalog scope."""
                return find_contracts(db, query, scope="probe")

            def answer_question(contract_id, version, evidence):
                """Admit only the fixture contract through the host-owned durable hook."""
                if (contract_id, version) != (contract.id, contract.version):
                    raise ValueError("Question is not part of this probe")
                event = HookEvent.model_validate(
                    {
                        "source": "monty-probe",
                        "id": "fixture-1",
                        "name": "probe.route",
                        "state": {"data": evidence, "reference": "fixture:report-inspection"},
                    }
                )
                return run_hook(db, config, event, lambda: provider)

            callbacks = {"find_questions": find_questions, "answer_question": answer_question}
            inputs = {
                "query": "represented route",
                "evidence": {
                    "request": "Inspect the report",
                    "__mock_answers__": {"route": "inspect"},
                },
            }

            with Monty(max_processes=1) as pool, pool.checkout() as session:
                step = session.feed_start(PROGRAM, inputs=inputs, external_lookup=callbacks)
                for _ in range(10):
                    if (
                        isinstance(step, FunctionSnapshot)
                        and step.function_name == "answer_question"
                    ):
                        break
                    if isinstance(step, MontyComplete):
                        raise AssertionError("Program finished before the expected question call")
                    step = step.resume_auto()
                else:
                    raise AssertionError("Expected question suspension was not reached")
                assert provider.calls == 0
                snapshot = step.dump()

            # Each context starts a fresh worker pool. Only interpreter bytes
            # travel; catalog/provider operations stay with the host.
            results = []
            for _ in range(2):
                with Monty(max_processes=1) as pool, pool.checkout() as session:
                    step = session.load_snapshot(snapshot, external_lookup=callbacks)
                    assert isinstance(step, FunctionSnapshot)
                    assert step.function_name == "answer_question"
                    for _ in range(10):
                        if isinstance(step, MontyComplete):
                            break
                        step = step.resume_auto()
                    assert isinstance(step, MontyComplete)
                    results.append(step.output)

            first, replay = results
            assert first["status"] == replay["status"] == "completed"
            assert first["receipt"]["answers"]["route"]["value"] == "inspect"
            assert not first["replayed"] and replay["replayed"]
            assert first["receipt"] == replay["receipt"]
            assert provider.calls == 1
            assert db.execute("SELECT count(*) FROM decisions").fetchone()[0] == 1
            assert db.execute("SELECT count(*) FROM outcomes").fetchone()[0] == 0

            # This outcome verifies the test's retained decision, not an
            # application-side action or correctness of a model judgment.
            observe_decision(
                db,
                first["run_id"],
                first["step_id"],
                observed_result="success",
                effect_receipt_ref="test:retained-inspect-decision",
            )
            assert db.execute("SELECT count(*) FROM outcomes").fetchone()[0] == 1
            with Monty(max_processes=1) as pool, pool.checkout() as session:
                missing = session.feed_run(
                    PROGRAM,
                    inputs={**inputs, "query": "no-such-question-fixture"},
                    external_lookup=callbacks,
                )
            assert missing == {"status": "unknown_no_match", "candidates": 0}
            assert provider.calls == 1

            return {
                "scope": "offline feasibility; mock answers; temporary catalog; not deployed",
                "host_probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "monty_version": importlib.metadata.version("pydantic-monty"),
                "contract_id": contract.id,
                "contract_sha256": fingerprint,
                "program_sha256": hashlib.sha256(PROGRAM.encode()).hexdigest(),
                "snapshot_bytes": len(snapshot),
                "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
                "restored_in_fresh_worker_pool": True,
                "answer": first["receipt"]["answers"]["route"]["value"],
                "mock_provider_calls": provider.calls,
                "retained_decisions": 1,
                "replay_reused_receipt": replay["replayed"],
                "observed_outcomes": 1,
                "missing_question": missing,
            }
        finally:
            db.close()


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))
