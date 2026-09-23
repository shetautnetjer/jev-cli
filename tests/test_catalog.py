import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jev_cli.catalog import connect, get_contract, import_contract, list_outcomes, record_outcome
from jev_cli.cli import app
from jev_cli.engine import execute
from jev_cli.models import DecisionContract, StatePacket
from jev_cli.providers.mock import MockProvider


def test_catalog_keeps_versions_and_observed_outcomes_separate(tmp_path: Path) -> None:
    db_path = tmp_path / "questions.sqlite"
    contract = DecisionContract.model_validate(
        {
            "id": "browser.next",
            "version": "1",
            "questions": {
                "operation": {
                    "type": "choice",
                    "instructions": "Which observed action advances the goal?",
                    "criteria": {
                        "click": "Observed clickable control",
                        "unknown_no_match": "No suitable control",
                    },
                }
            },
        }
    )
    with connect(db_path) as db:
        fingerprint = import_contract(db, contract)
        assert import_contract(db, contract) == fingerprint
        assert get_contract(db, "browser.next", "1") == contract
        changed = contract.model_copy(update={"model": "jev-1.13.0"})
        with pytest.raises(ValueError, match="increment"):
            import_contract(db, changed)
        state = StatePacket(data={"__mock_answers__": {"operation": "click"}})
        receipt = execute(contract, state, MockProvider())
        record_outcome(db, receipt, run_id="run-1", step_id="step-1", observed_result="unresolved")
        rows = list_outcomes(db, "run-1")
        assert len(rows) == 1
        assert rows[0]["observed_result"] == "unresolved"
        assert json.loads(rows[0]["answer_json"])["value"] == "click"
        with pytest.raises(ValueError, match="fingerprint"):
            record_outcome(
                db,
                receipt.model_copy(update={"contract_sha256": "wrong"}),
                run_id="run-1",
                step_id="step-2",
                observed_result="success",
            )


def test_catalog_cli_import_and_show(tmp_path: Path) -> None:
    runner = CliRunner()
    contract_path = tmp_path / "route.yaml"
    db_path = tmp_path / "catalog.sqlite"
    assert runner.invoke(app, ["init", str(contract_path)]).exit_code == 0
    imported = runner.invoke(app, ["catalog", "import", str(contract_path), "--db", str(db_path)])
    assert imported.exit_code == 0, imported.output
    shown = runner.invoke(app, ["catalog", "show", "example.route", "1", "--db", str(db_path)])
    assert shown.exit_code == 0, shown.output
    assert "unknown_no_match" in shown.output
