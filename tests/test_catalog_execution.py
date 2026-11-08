import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

import pytest
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


@pytest.mark.parametrize("different_content", [False, True])
@pytest.mark.parametrize("existing_read", [False, True])
def test_contract_import_reserves_before_reading_identity(
    tmp_path: Path, different_content: bool, existing_read: bool
) -> None:
    """A real second importer cannot change admission between the read and insert."""
    from jev_cli.catalog import DDL, connect, get_contract, import_contract
    from jev_cli.engine import sha256_json
    from jev_cli.models import DecisionContract

    path = tmp_path / "catalog.sqlite"
    with (
        closing(sqlite3.connect(path, factory=InterleavedConnection)) as first,
        closing(connect(path)) as second,
    ):
        first.row_factory = sqlite3.Row
        first.executescript(DDL)
        second.execute("PRAGMA busy_timeout = 1")
        if existing_read:
            # WAL lets a competing writer commit despite this reader. Only the
            # import's writer reservation can exclude it before the identity read.
            assert first.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
            first.execute("BEGIN")
            assert first.execute("SELECT count(*) FROM contracts").fetchone()[0] == 0
        contract = DecisionContract(
            id="fixture", version="1", questions={"q": {"type": "noul", "instructions": "First?"}}
        )
        competitor = (
            contract.model_copy(update={"model": "other-model"}) if different_content else contract
        )
        blocked = []

        def competing_import():
            """Interleave at the original read-to-write race, using a real SQLite writer."""
            try:
                import_contract(second, competitor)
            except sqlite3.OperationalError as error:
                assert error.sqlite_errorname == "SQLITE_BUSY"
                blocked.append(True)

        first.write_prefix = "INSERT INTO contracts"
        first.before_write = competing_import
        digest = import_contract(first, contract)
        assert blocked == [True]
        assert first.in_transaction is existing_read
        if existing_read:
            first.commit()
        assert digest == sha256_json(contract.model_dump(mode="json", exclude_none=True))
        assert get_contract(second, contract.id, contract.version) == contract
        if different_content:
            with pytest.raises(ValueError, match="increment its version"):
                import_contract(second, competitor)
        else:
            assert import_contract(second, competitor) == digest
        assert second.execute("SELECT count(*) FROM contracts").fetchone()[0] == 1
        assert second.execute("SELECT count(*) FROM questions").fetchone()[0] == 1
        assert not first.in_transaction and not second.in_transaction


@pytest.mark.parametrize("command", ["run", "observe", "import"])
def test_catalog_cli_writer_contention_is_safe_and_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    """Real BEGIN IMMEDIATE contention stays a safe CLI failure with no inference."""
    import jev_cli.catalog as catalog_module
    import jev_cli.cli as cli_module
    from jev_cli.catalog import connect, import_contract
    from jev_cli.models import DecisionContract, DecisionReceipt, NormalizedAnswer

    marker = "PRIVATE-CONTENTION-FIXTURE"
    contract = DecisionContract(
        id="fixture", version="1", questions={"q": {"type": "noul", "instructions": marker}}
    )
    path = tmp_path / "catalog.sqlite"
    contract_file = tmp_path / "contract.json"
    contract_file.write_text(contract.model_dump_json(), encoding="utf-8")

    class ForbiddenProvider:
        """Record cleanup while refusing any evaluation in this admission-only fixture."""

        name = "fixture"
        calls = 0
        closes = 0

        def evaluate(self, contract, state):
            self.calls += 1
            raise AssertionError("Contention must not reach a provider")

        def close(self):
            self.closes += 1

    provider = ForbiddenProvider()
    with closing(connect(path)) as owner, closing(connect(path)) as waiting:
        digest = import_contract(owner, contract)
        receipt = DecisionReceipt(
            contract_id=contract.id,
            contract_version=contract.version,
            contract_sha256=digest,
            state_sha256="fixture",
            state_reference=marker,
            provider="fixture",
            requested_model="fixture",
            answers={"q": NormalizedAnswer(id="q", type="noul", value="true")},
        )
        with owner:
            owner.execute(
                "INSERT INTO decisions (run_id,step_id,contract_id,version,state_digest,"
                "status,receipt_json) VALUES (?,?,?,?,?,'completed',?)",
                (
                    "retained",
                    "s",
                    contract.id,
                    contract.version,
                    "fixture",
                    receipt.model_dump_json(),
                ),
            )
        before = [dict(row) for row in owner.execute("SELECT * FROM decisions")]
        waiting.execute("PRAGMA busy_timeout = 1")
        monkeypatch.setattr(catalog_module, "connect", lambda _path: waiting)
        monkeypatch.setattr(cli_module, "_provider", lambda *_args: provider)
        if command == "run":
            args = [
                "catalog",
                "run",
                contract.id,
                contract.version,
                "--run-id",
                "new",
                "--step-id",
                "s",
                "--provider",
                "mock",
                "--state",
                marker,
            ]
        elif command == "observe":
            args = ["catalog", "observe", "retained", "s", "--result", "unresolved"]
        else:
            args = ["catalog", "import", str(contract_file)]
        owner.execute("BEGIN IMMEDIATE")
        try:
            result = CliRunner().invoke(app, [*args, "--db", str(path)])
        finally:
            owner.rollback()

        assert result.exit_code == (1 if command == "run" else 2), result.output
        assert isinstance(result.exception, SystemExit), repr(result.exception)
        assert "database operation failed" in result.output
        assert "before retrying" in result.output
        assert marker not in result.output
        assert "database is locked" not in result.output
        assert "Traceback" not in result.output
        assert provider.calls == 0
        assert provider.closes == (1 if command == "run" else 0)
        with pytest.raises(sqlite3.ProgrammingError):
            waiting.execute("SELECT 1")
        assert [dict(row) for row in owner.execute("SELECT * FROM decisions")] == before
        assert owner.execute("SELECT count(*) FROM outcomes").fetchone()[0] == 0


@pytest.mark.parametrize("already_imported", [False, True])
def test_contract_import_keeps_existing_writer_transaction(
    tmp_path: Path, already_imported: bool
) -> None:
    """An import must not commit another caller's pending writes or release its writer."""
    from jev_cli.catalog import connect, import_contract
    from jev_cli.models import DecisionContract

    contract = DecisionContract(
        id="fixture", version="1", questions={"q": {"type": "noul", "instructions": "Present?"}}
    )
    with closing(connect(tmp_path / "db")) as caller, closing(connect(tmp_path / "db")) as observer:
        caller.execute("CREATE TABLE caller_notes (note TEXT)")
        if already_imported:
            import_contract(caller, contract)
        caller.execute("INSERT INTO caller_notes VALUES ('pending')")
        import_contract(caller, contract)
        assert caller.in_transaction
        assert observer.execute("SELECT count(*) FROM caller_notes").fetchone()[0] == 0
        assert observer.execute("SELECT count(*) FROM contracts").fetchone()[0] == int(
            already_imported
        )
        observer.execute("PRAGMA busy_timeout = 1")
        with pytest.raises(sqlite3.OperationalError) as blocked:
            observer.execute("BEGIN IMMEDIATE")
        assert blocked.value.sqlite_errorname == "SQLITE_BUSY"
        caller.rollback()
        assert observer.execute("SELECT count(*) FROM caller_notes").fetchone()[0] == 0
        assert observer.execute("SELECT count(*) FROM contracts").fetchone()[0] == int(
            already_imported
        )


def test_contract_import_preserves_stale_read_snapshot_on_refusal(tmp_path: Path) -> None:
    """An unupgradeable WAL read snapshot fails before lookup without ending caller state."""
    from jev_cli.catalog import connect, import_contract
    from jev_cli.models import DecisionContract

    contract = DecisionContract(
        id="fixture", version="1", questions={"q": {"type": "noul", "instructions": "Present?"}}
    )
    with closing(connect(tmp_path / "db")) as caller, closing(connect(tmp_path / "db")) as writer:
        assert caller.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        caller.execute("PRAGMA busy_timeout = 1")
        caller.execute("BEGIN")
        assert caller.execute("SELECT count(*) FROM contracts").fetchone()[0] == 0
        import_contract(writer, contract)
        with pytest.raises(sqlite3.OperationalError) as blocked:
            import_contract(caller, contract)
        assert blocked.value.sqlite_errorname == "SQLITE_BUSY_SNAPSHOT"
        assert caller.in_transaction
        assert caller.execute("SELECT count(*) FROM contracts").fetchone()[0] == 0
        caller.rollback()
        assert caller.execute("SELECT count(*) FROM contracts").fetchone()[0] == 1


@pytest.mark.parametrize("abort_mode", ["ABORT", "ROLLBACK"])
def test_contract_import_late_failure_preserves_sqlite_transaction_semantics(
    tmp_path: Path, abort_mode: str
) -> None:
    """Retain caller writes unless SQLite itself aborts the entire transaction."""
    from jev_cli.catalog import connect, import_contract
    from jev_cli.models import DecisionContract

    contract = DecisionContract(
        id="fixture",
        version="1",
        questions={
            "first": {"type": "noul", "instructions": "First?"},
            "second": {"type": "noul", "instructions": "Second?"},
        },
    )
    with closing(connect(tmp_path / "db")) as caller, closing(connect(tmp_path / "db")) as observer:
        caller.executescript(
            "CREATE TABLE caller_notes (note TEXT);"
            "CREATE TRIGGER reject_second BEFORE INSERT ON questions "
            "WHEN NEW.question_id='second' BEGIN "
            f"SELECT RAISE({abort_mode}, 'fixture rejection'); END;"
        )
        caller.execute("INSERT INTO caller_notes VALUES ('pending')")
        with pytest.raises(sqlite3.IntegrityError) as rejected:
            import_contract(caller, contract)
        assert rejected.value.sqlite_errorname == "SQLITE_CONSTRAINT_TRIGGER"
        if abort_mode == "ROLLBACK":
            assert not caller.in_transaction
            assert observer.execute("SELECT count(*) FROM caller_notes").fetchone()[0] == 0
            assert observer.execute("SELECT count(*) FROM contracts").fetchone()[0] == 0
            return
        assert caller.in_transaction
        assert caller.execute("SELECT note FROM caller_notes").fetchone()[0] == "pending"
        assert caller.execute("SELECT count(*) FROM contracts").fetchone()[0] == 0
        assert caller.execute("SELECT count(*) FROM questions").fetchone()[0] == 0
        assert observer.execute("SELECT count(*) FROM caller_notes").fetchone()[0] == 0
        caller.commit()
        assert observer.execute("SELECT note FROM caller_notes").fetchone()[0] == "pending"
        assert observer.execute("SELECT count(*) FROM contracts").fetchone()[0] == 0


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
