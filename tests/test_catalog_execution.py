import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
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


class InterleavedConnection(sqlite3.Connection):
    """Allow a competing real connection to run after admission reads, before first DML."""

    before_write: Callable[[], None] | None = None
    write_prefix = ""

    def execute(self, sql, parameters=(), /):
        """Invoke the one-shot interleaving without replacing SQLite operations."""
        if sql.startswith(self.write_prefix) and self.before_write is not None:
            callback, self.before_write = self.before_write, None
            callback()
        return super().execute(sql, parameters)


def test_outcome_admission_excludes_competing_run_reservation(tmp_path: Path) -> None:
    """An outcome writer owns admission through insert, excluding contradictory inference."""
    import pytest

    from jev_cli.catalog import DDL, connect, import_contract, record_outcome, run_contract
    from jev_cli.engine import execute
    from jev_cli.models import DecisionContract, StatePacket
    from jev_cli.providers.mock import MockProvider

    path = tmp_path / "catalog.sqlite"
    with (
        closing(sqlite3.connect(path, factory=InterleavedConnection)) as first,
        closing(connect(path)) as second,
    ):
        first.row_factory = sqlite3.Row
        first.executescript(DDL)
        second.execute("PRAGMA busy_timeout = 0")
        contract = DecisionContract(
            id="fixture", version="1", questions={"q": {"type": "noul", "instructions": "Present?"}}
        )
        import_contract(second, contract)
        external = execute(contract, StatePacket(data="external-A"), MockProvider())
        blocked = []

        class CountingProvider(MockProvider):
            """Count attempted inference and assert its transaction boundary."""

            calls = 0

            def evaluate(self, contract, state):
                """A losing reservation must never reach this provider."""
                self.calls += 1
                assert not second.in_transaction
                return super().evaluate(contract, state)

        provider = CountingProvider()

        def competing_run():
            """Attempt the competing admission at the exact first-write boundary."""
            try:
                run_contract(
                    second,
                    "fixture",
                    "1",
                    StatePacket(data="native-B"),
                    provider,
                    run_id="r",
                    step_id="s",
                )
            except sqlite3.OperationalError as error:
                assert "locked" in str(error)
                blocked.append(True)

        first.write_prefix = "INSERT INTO outcomes"
        first.before_write = competing_run
        record_outcome(first, external, run_id="r", step_id="s", observed_result="unresolved")
        assert blocked == [True]
        assert provider.calls == 0
        assert second.execute("SELECT count(*) FROM decisions").fetchone()[0] == 0
        assert (
            second.execute("SELECT state_digest FROM outcomes").fetchone()[0]
            == external.state_sha256
        )
        with pytest.raises(ValueError, match="already exists in outcomes"):
            run_contract(
                second,
                "fixture",
                "1",
                StatePacket(data="native-B"),
                provider,
                run_id="r",
                step_id="s",
            )
        assert provider.calls == 0
        assert not first.in_transaction and not second.in_transaction


def test_outcome_batch_rolls_back_after_late_question_conflict(tmp_path: Path) -> None:
    """A later duplicate question cannot leave earlier answers partially inserted."""
    import pytest

    from jev_cli.catalog import connect, import_contract, record_outcome
    from jev_cli.engine import execute
    from jev_cli.models import DecisionContract, StatePacket
    from jev_cli.providers.mock import MockProvider

    path = tmp_path / "catalog.sqlite"
    with closing(connect(path)) as first, closing(connect(path)) as observer:
        contract = DecisionContract(
            id="fixture",
            version="1",
            questions={
                "first": {"type": "noul", "instructions": "First present?"},
                "second": {"type": "noul", "instructions": "Second present?"},
            },
        )
        import_contract(first, contract)
        receipt = execute(contract, StatePacket(data="fixture-state"), MockProvider())
        record_outcome(first, receipt, run_id="r", step_id="s", observed_result="unresolved")
        # Retain one committed conflicting row as an explicit partial-history fixture.
        with first:
            first.execute("DELETE FROM outcomes WHERE question_id='first'")
        before = [dict(row) for row in observer.execute("SELECT * FROM outcomes")]
        assert len(before) == 1 and before[0]["question_id"] == "second"
        with pytest.raises(sqlite3.IntegrityError):
            record_outcome(first, receipt, run_id="r", step_id="s", observed_result="unresolved")
        assert [dict(row) for row in observer.execute("SELECT * FROM outcomes")] == before
        assert not first.in_transaction


def test_run_reservation_excludes_competing_outcome_admission(tmp_path: Path) -> None:
    """A run reserves its identity before an external outcome can pass admission."""
    import pytest

    from jev_cli.catalog import DDL, connect, import_contract, record_outcome, run_contract
    from jev_cli.engine import execute
    from jev_cli.models import DecisionContract, StatePacket
    from jev_cli.providers.mock import MockProvider

    path = tmp_path / "catalog.sqlite"
    with (
        closing(sqlite3.connect(path, factory=InterleavedConnection)) as first,
        closing(connect(path)) as second,
    ):
        first.row_factory = sqlite3.Row
        first.executescript(DDL)
        second.execute("PRAGMA busy_timeout = 0")
        contract = DecisionContract(
            id="fixture", version="1", questions={"q": {"type": "noul", "instructions": "Present?"}}
        )
        import_contract(second, contract)
        external = execute(contract, StatePacket(data="external-A"), MockProvider())
        blocked = []

        def competing_outcome():
            """Attempt a conflicting outcome after the run's guard, before its insert."""
            try:
                record_outcome(
                    second, external, run_id="r", step_id="s", observed_result="unresolved"
                )
            except sqlite3.OperationalError as error:
                assert "locked" in str(error)
                blocked.append(True)

        class CheckedProvider(MockProvider):
            """Verify provider work begins after the reservation transaction commits."""

            def evaluate(self, contract, state):
                """Observe durable pending state from the other database connection."""
                assert not first.in_transaction
                assert second.execute("SELECT status FROM decisions").fetchone()[0] == "pending"
                return super().evaluate(contract, state)

        first.write_prefix = "INSERT INTO decisions"
        first.before_write = competing_outcome
        receipt = run_contract(
            first,
            "fixture",
            "1",
            StatePacket(data="native-B"),
            CheckedProvider(),
            run_id="r",
            step_id="s",
        )
        assert blocked == [True]
        assert second.execute("SELECT count(*) FROM outcomes").fetchone()[0] == 0
        assert (
            second.execute("SELECT state_digest FROM decisions").fetchone()[0]
            == receipt.state_sha256
        )
        with pytest.raises(ValueError, match="retained decision"):
            record_outcome(second, external, run_id="r", step_id="s", observed_result="unresolved")
        assert not first.in_transaction and not second.in_transaction
