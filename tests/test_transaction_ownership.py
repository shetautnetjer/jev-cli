"""Keep first-admission transactions separate from caller-owned SQLite writes."""

import sqlite3
from contextlib import closing

import pytest

from jev_cli.catalog import connect, import_contract, run_contract
from jev_cli.models import DecisionContract, StatePacket
from jev_cli.providers.mock import MockProvider


def test_catalog_run_preserves_pending_caller_work_and_allows_later_admission(tmp_path):
    """Reject before touching caller writes, then permit admission after caller rollback."""
    with closing(connect(tmp_path / "catalog.sqlite")) as db:
        contract = DecisionContract(
            id="transaction.owner",
            version="1",
            questions={"present": {"type": "noul", "instructions": "Is evidence present?"}},
        )
        import_contract(db, contract)
        db.execute("CREATE TABLE caller_work (content TEXT)")
        db.execute("INSERT INTO caller_work VALUES ('caller-owned pending bytes')")
        calls = []

        class ObserveReservation(MockProvider):
            def evaluate(self, selected, state):
                # A separate connection must see the committed reservation before inference.
                with closing(connect(tmp_path / "catalog.sqlite")) as other:
                    status = other.execute("SELECT status FROM decisions").fetchone()[0]
                calls.append(status)
                return super().evaluate(selected, state)

        provider = ObserveReservation()
        state = StatePacket(data={"__mock_answers__": {"present": 0.9}})
        with pytest.raises((ValueError, sqlite3.OperationalError)) as rejected:
            run_contract(db, contract.id, "1", state, provider, run_id="r", step_id="s")
        assert db.in_transaction
        assert db.execute("SELECT content FROM caller_work").fetchone()[0] == (
            "caller-owned pending bytes"
        )
        assert db.execute("SELECT count(*) FROM decisions").fetchone()[0] == 0
        assert calls == []
        assert isinstance(rejected.value, ValueError)
        assert "pending transaction" in str(rejected.value)
        db.rollback()
        assert db.execute("SELECT count(*) FROM caller_work").fetchone()[0] == 0
        receipt = run_contract(db, contract.id, "1", state, provider, run_id="r", step_id="s")
        assert receipt.answers["present"].value == 0.9
        assert calls == ["pending"]
        assert not db.in_transaction
        assert db.execute("SELECT status FROM decisions").fetchone()[0] == "completed"
