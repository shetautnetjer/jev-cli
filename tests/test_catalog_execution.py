import json
from pathlib import Path

from typer.testing import CliRunner

from jev_cli.cli import app


def test_catalog_run_retains_decision_then_observation(tmp_path: Path) -> None:
    runner = CliRunner()
    contract = tmp_path / "route.yaml"
    db = tmp_path / "catalog.sqlite"
    assert runner.invoke(app, ["init", str(contract)]).exit_code == 0
    assert runner.invoke(app, ["catalog", "import", str(contract), "--db", str(db)]).exit_code == 0
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"__mock_answers__": {"route": "inspect"}}))
    args = [
        "catalog",
        "run",
        "example.route",
        "1",
        "--run-id",
        "run1",
        "--step-id",
        "step1",
        "--provider",
        "mock",
        "--state-file",
        str(state),
        "--db",
        str(db),
    ]
    ran = runner.invoke(app, args)
    assert ran.exit_code == 0, ran.output
    assert json.loads(ran.stdout)["answers"]["route"]["value"] == "inspect"
    decisions = runner.invoke(app, ["catalog", "decisions", "run1", "--db", str(db)])
    row = json.loads(decisions.stdout)[0]
    assert row["status"] == "completed"
    assert row["receipt"]["state_sha256"]
    assert "state" not in row
    assert (
        json.loads(runner.invoke(app, ["catalog", "outcomes", "run1", "--db", str(db)]).stdout)
        == []
    )
    duplicate = runner.invoke(app, args)
    assert duplicate.exit_code != 0
    assert "already exists" in duplicate.output
    observed = runner.invoke(
        app,
        [
            "catalog",
            "observe",
            "run1",
            "step1",
            "--result",
            "success",
            "--effect-ref",
            "test:observed-state",
            "--db",
            str(db),
        ],
    )
    assert observed.exit_code == 0, observed.output
    outcomes = json.loads(
        runner.invoke(app, ["catalog", "outcomes", "run1", "--db", str(db)]).stdout
    )
    assert outcomes[0]["observed_result"] == "success"
    assert outcomes[0]["effect_receipt_ref"] == "test:observed-state"
    assert (
        runner.invoke(app, ["catalog", "find", "represented route", "--db", str(db)]).exit_code == 0
    )


def test_catalog_failed_call_is_retained_and_not_retried(tmp_path: Path) -> None:
    import pytest

    from jev_cli.catalog import connect, import_contract, run_contract
    from jev_cli.models import DecisionContract, StatePacket

    class Broken:
        name = "broken"
        calls = 0

        def evaluate(self, contract, state):
            self.calls += 1
            raise RuntimeError("provider unavailable")

    contract = DecisionContract(
        id="x", version="1", questions={"q": {"type": "noul", "instructions": "Present?"}}
    )
    provider = Broken()
    with connect(tmp_path / "db") as db:
        import_contract(db, contract)
        for _ in range(2):
            with pytest.raises((RuntimeError, ValueError)):
                run_contract(
                    db, "x", "1", StatePacket(data="evidence"), provider, run_id="r", step_id="s"
                )
        assert provider.calls == 1
        row = db.execute("select status, error_code from decisions").fetchone()
        assert tuple(row) == ("failed", "evaluation_failed")


def test_outcome_cannot_replace_retained_answer(tmp_path: Path) -> None:
    import pytest

    from jev_cli.catalog import connect, import_contract, record_outcome, run_contract
    from jev_cli.models import DecisionContract, StatePacket
    from jev_cli.providers.mock import MockProvider

    contract = DecisionContract(
        id="x", version="1", questions={"q": {"type": "noul", "instructions": "Present?"}}
    )
    with connect(tmp_path / "db") as db:
        import_contract(db, contract)
        receipt = run_contract(
            db, "x", "1", StatePacket(data="evidence"), MockProvider(), run_id="r", step_id="s"
        )
        altered = receipt.model_copy(update={"state_sha256": "another-observation"})
        with pytest.raises(ValueError, match="retained decision"):
            record_outcome(db, altered, run_id="r", step_id="s", observed_result="success")
        assert db.execute("select count(*) from outcomes").fetchone()[0] == 0
