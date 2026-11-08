import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jev_cli.catalog import (
    connect,
    find_contracts,
    get_contract,
    import_contract,
    list_outcomes,
    record_outcome,
)
from jev_cli.cli import app
from jev_cli.engine import execute, sha256_json
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


_LITERAL_CONTRACT = {
    "id": "literal.find",
    "version": "1",
    "questions": {
        "pick": {
            "type": "choice",
            "instructions": 'Visit the café, say "hi" at C:\\temp\nthen\tleave',
            "criteria": {
                "go": "Straße — 日本語",
                "unknown_no_match": "No suitable option",
            },
        }
    },
}


@pytest.mark.parametrize(
    "needle",
    [
        "café",
        "CAFÉ",
        'say "hi"',
        "C:\\temp",
        "temp\nthen",
        "then\tleave",
        "straSSe",
        "日本語",
        "literal.find",
    ],
)
def test_catalog_find_matches_literal_text_of_stored_contract(tmp_path: Path, needle: str) -> None:
    contract = DecisionContract.model_validate(_LITERAL_CONTRACT)
    with connect(tmp_path / "c.sqlite") as db:
        fingerprint = import_contract(db, contract)
        stored = db.execute("SELECT contract_json FROM contracts").fetchone()[0]
        # The stored form is the escaped JSON, so literal text must not need to match it.
        assert "café" not in stored
        assert [row["contract_id"] for row in find_contracts(db, needle)] == ["literal.find"]
        assert find_contracts(db, needle)[0]["fingerprint"] == fingerprint


def test_catalog_find_matches_preexisting_escaped_rows_and_keeps_fingerprint(
    tmp_path: Path,
) -> None:
    contract = DecisionContract.model_validate(_LITERAL_CONTRACT)
    raw = contract.model_dump(mode="json", exclude_none=True)
    legacy_json = json.dumps(raw, sort_keys=True)
    assert "\\u00e9" in legacy_json
    with connect(tmp_path / "c.sqlite") as db:
        # A row written by an earlier release: escaped JSON, fingerprint of the raw contract.
        db.execute(
            "INSERT INTO contracts VALUES (?,?,?,?,?,?,?)",
            (
                contract.id,
                contract.version,
                sha256_json(raw),
                "general",
                None,
                "active",
                legacy_json,
            ),
        )
        found = find_contracts(db, "café")
        assert [row["fingerprint"] for row in found] == [sha256_json(raw)]
        assert find_contracts(db, "no such text") == []
        assert import_contract(db, contract) == sha256_json(raw)
        assert get_contract(db, contract.id, contract.version) == contract


def test_catalog_find_honours_scope_and_rejects_blank(tmp_path: Path) -> None:
    contract = DecisionContract.model_validate(_LITERAL_CONTRACT)
    with connect(tmp_path / "c.sqlite") as db:
        import_contract(db, contract, scope="alpha")
        assert find_contracts(db, "café", scope="alpha")
        assert find_contracts(db, "café", scope="beta") == []
        with pytest.raises(ValueError, match="empty"):
            find_contracts(db, "   ")


def test_catalog_cli_find_matches_unicode_text(tmp_path: Path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "c.sqlite"
    contract_path = tmp_path / "literal.json"
    contract_path.write_text(json.dumps(_LITERAL_CONTRACT, ensure_ascii=False), encoding="utf-8")
    imported = runner.invoke(app, ["catalog", "import", str(contract_path), "--db", str(db_path)])
    assert imported.exit_code == 0, imported.output
    found = runner.invoke(app, ["catalog", "find", "café", "--db", str(db_path)])
    assert found.exit_code == 0, found.output
    assert [row["contract_id"] for row in json.loads(found.stdout)] == ["literal.find"]


SECRET = "TOP-SECRET-RECEIPT-VALUE"


@pytest.fixture
def record_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Imported route contract, a valid receipt file, and tracking of opened connections."""
    import sqlite3

    import jev_cli.catalog as catalog_module
    from jev_cli.io import dump_json

    runner = CliRunner()
    contract_path = tmp_path / "route.yaml"
    db_path = tmp_path / "catalog.sqlite"
    assert runner.invoke(app, ["init", str(contract_path)]).exit_code == 0
    assert (
        runner.invoke(
            app, ["catalog", "import", str(contract_path), "--db", str(db_path)]
        ).exit_code
        == 0
    )
    with connect(db_path) as db:
        contract = get_contract(db, "example.route", "1")
    receipt = execute(
        contract,
        StatePacket(data={"__mock_answers__": {"route": "inspect"}}),
        MockProvider(),
    )
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(dump_json(receipt), encoding="utf-8")

    opened: list[sqlite3.Connection] = []
    real_connect = catalog_module.connect

    def tracking_connect(path: Path) -> sqlite3.Connection:
        conn = real_connect(path)
        opened.append(conn)
        return conn

    monkeypatch.setattr(catalog_module, "connect", tracking_connect)

    def record(path: Path | None = None, *, step: str = "step-1"):
        result = runner.invoke(
            app,
            [
                "catalog",
                "record",
                str(path or receipt_path),
                "--run-id",
                "run-1",
                "--step-id",
                step,
                "--result",
                "unresolved",
                "--db",
                str(db_path),
            ],
        )
        for conn in opened:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")
        return result

    return type(
        "RecordEnv",
        (),
        {
            "record": staticmethod(record),
            "receipt": receipt,
            "receipt_path": receipt_path,
            "db_path": db_path,
            "tmp_path": tmp_path,
        },
    )


def _assert_clean_cli_error(result, *, absent: str | None = None) -> None:
    assert result.exit_code == 2, result.output
    assert isinstance(result.exception, SystemExit), repr(result.exception)
    assert "Traceback" not in result.output
    if absent:
        assert absent not in result.output


def test_catalog_record_success_closes_connection(record_env) -> None:
    result = record_env.record()
    assert result.exit_code == 0, result.output
    assert "recorded" in result.output
    with connect(record_env.db_path) as db:
        rows = list_outcomes(db, "run-1")
    assert [row["question_id"] for row in rows] == ["route"]


def test_catalog_record_write_refusal_is_a_clean_error(record_env, monkeypatch) -> None:
    import jev_cli.catalog as catalog_module

    tracked_connect = catalog_module.connect

    def read_only_connect(path: Path):
        connection = tracked_connect(path)
        connection.execute("PRAGMA query_only=ON")
        return connection

    monkeypatch.setattr(catalog_module, "connect", read_only_connect)
    receipt = record_env.receipt.model_copy(update={"state_reference": SECRET})
    record_env.receipt_path.write_text(receipt.model_dump_json(), encoding="utf-8")

    # The database opens normally; SQLite itself refuses the subsequent write.
    # record() also checks that the opened connection is closed on this error.
    result = record_env.record()

    _assert_clean_cli_error(result, absent=SECRET)
    assert "database operation failed" in result.output
    assert "before retrying" in result.output
    with connect(record_env.db_path) as db:
        assert list_outcomes(db, "run-1") == []


def test_catalog_record_duplicate_outcome_is_a_clean_error(record_env) -> None:
    assert record_env.record().exit_code == 0
    second = record_env.record()
    _assert_clean_cli_error(second)
    assert "already recorded" in second.output
    with connect(record_env.db_path) as db:
        assert len(list_outcomes(db, "run-1")) == 1


def test_catalog_record_unknown_question_is_a_clean_error(record_env) -> None:
    answer = record_env.receipt.answers["route"]
    ghost = record_env.receipt.model_copy(update={"answers": {"ghost": answer}})
    ghost_path = record_env.tmp_path / "ghost.json"
    from jev_cli.io import dump_json

    ghost_path.write_text(dump_json(ghost), encoding="utf-8")
    result = record_env.record(ghost_path)
    _assert_clean_cli_error(result)
    assert "question" in result.output.lower()
    with connect(record_env.db_path) as db:
        assert list_outcomes(db, "run-1") == []


@pytest.mark.parametrize(
    "content",
    [
        '{"contract_id": "' + SECRET,
        json.dumps({"contract_id": SECRET, SECRET: SECRET}),
        json.dumps([SECRET]),
        "",
    ],
)
def test_catalog_record_malformed_receipt_is_a_clean_error(record_env, content: str) -> None:
    bad = record_env.tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    result = record_env.record(bad)
    _assert_clean_cli_error(result, absent=SECRET)
    assert "receipt" in result.output.lower()


def test_catalog_record_non_utf8_receipt_is_a_clean_error(record_env) -> None:
    bad = record_env.tmp_path / "bad.json"
    bad.write_bytes(b"\xff\xfe" + SECRET.encode())
    _assert_clean_cli_error(record_env.record(bad), absent=SECRET)


def test_catalog_record_missing_or_unreadable_receipt_is_a_clean_error(record_env) -> None:
    _assert_clean_cli_error(record_env.record(record_env.tmp_path / "absent.json"))
    _assert_clean_cli_error(record_env.record(record_env.tmp_path))


def test_catalog_record_unmatched_fingerprint_does_not_echo_receipt(record_env) -> None:
    from jev_cli.io import dump_json

    altered = record_env.receipt.model_copy(update={"contract_sha256": SECRET})
    path = record_env.tmp_path / "altered.json"
    path.write_text(dump_json(altered), encoding="utf-8")
    result = record_env.record(path)
    _assert_clean_cli_error(result, absent=SECRET)
    assert "fingerprint" in result.output


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


@pytest.mark.parametrize("kind", ["missing", "directory"])
def test_catalog_import_rejects_non_file_inputs(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "contract.yaml"
    if kind == "directory":
        path.mkdir()
    db_path = tmp_path / "catalog.sqlite"
    result = CliRunner().invoke(app, ["catalog", "import", str(path), "--db", str(db_path)])

    _assert_clean_cli_error(result)
    assert "file" in result.output.lower()
    assert not db_path.exists()


@pytest.mark.parametrize("error_type", [PermissionError, FileNotFoundError])
def test_catalog_import_handles_post_validation_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type: type[OSError]
) -> None:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(_LITERAL_CONTRACT), encoding="utf-8")
    db_path = tmp_path / "catalog.sqlite"
    original = Path.read_text

    def failed_read(self: Path, *args, **kwargs):
        if self == path:
            raise error_type(SECRET)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failed_read)
    result = CliRunner().invoke(app, ["catalog", "import", str(path), "--db", str(db_path)])

    _assert_clean_cli_error(result, absent=SECRET)
    assert "Contract file cannot be read" in result.output
    assert not db_path.exists()


@pytest.mark.parametrize(
    ("suffix", "content"),
    [
        (".yaml", f"questions: [{SECRET}\n".encode()),
        (".json", f'{{"id": "{SECRET}",'.encode()),
        (".yaml", b"\xff\xfe" + SECRET.encode()),
        (".yaml", b""),
        (".json", json.dumps([SECRET]).encode()),
        (".json", json.dumps({"id": SECRET}).encode()),
        pytest.param(".json", b"[" * 1500 + b"0" + b"]" * 1500, id="deep-json"),
        pytest.param(".yaml", b"[" * 1500 + b"0" + b"]" * 1500, id="deep-yaml"),
    ],
)
def test_catalog_import_handles_invalid_contract_file_without_content_leak(
    tmp_path: Path, suffix: str, content: bytes
) -> None:
    path = tmp_path / f"contract{suffix}"
    path.write_bytes(content)
    db_path = tmp_path / "catalog.sqlite"
    result = CliRunner().invoke(app, ["catalog", "import", str(path), "--db", str(db_path)])

    _assert_clean_cli_error(result, absent=SECRET)
    assert "not a valid decision contract" in result.output
    assert not db_path.exists()


def test_catalog_import_keeps_version_mismatch_and_closes_connections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sqlite3

    import jev_cli.catalog as catalog_module

    path = tmp_path / "contract.json"
    path.write_text(json.dumps(_LITERAL_CONTRACT), encoding="utf-8")
    db_path = tmp_path / "catalog.sqlite"
    opened = []
    original = catalog_module.connect

    def tracking_connect(path: Path):
        db = original(path)
        opened.append(db)
        return db

    monkeypatch.setattr(catalog_module, "connect", tracking_connect)
    runner = CliRunner()
    args = ["catalog", "import", str(path), "--db", str(db_path)]
    imported = runner.invoke(app, args)
    assert imported.exit_code == 0, imported.output
    path.write_text(json.dumps({**_LITERAL_CONTRACT, "model": "other-model"}), encoding="utf-8")
    mismatch = runner.invoke(app, args)
    _assert_clean_cli_error(mismatch)
    assert "increment its version" in mismatch.output
    assert len(opened) == 2
    for db in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            db.execute("SELECT 1")
    with connect(db_path) as db:
        assert get_contract(db, "literal.find", "1").model == "jev-latest"


@pytest.mark.parametrize("command", ["list", "show", "outcomes"])
@pytest.mark.parametrize("deny_read", [False, True], ids=["success", "read-refused"])
def test_catalog_read_commands_close_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str, deny_read: bool
) -> None:
    import sqlite3
    from contextlib import closing

    import jev_cli.catalog as catalog_module

    db_path = tmp_path / "catalog.sqlite"
    with closing(connect(db_path)) as db:
        import_contract(db, DecisionContract.model_validate(_LITERAL_CONTRACT))
    opened: list[sqlite3.Connection] = []

    def tracked_connect(path: Path) -> sqlite3.Connection:
        db = connect(path)
        opened.append(db)
        if deny_read:
            db.set_authorizer(
                lambda action, *_: (
                    sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_SELECT else sqlite3.SQLITE_OK
                )
            )
        return db

    monkeypatch.setattr(catalog_module, "connect", tracked_connect)
    arguments = {"list": [], "show": ["literal.find", "1"], "outcomes": ["run-1"]}
    result = CliRunner().invoke(
        app, ["catalog", command, *arguments[command], "--db", str(db_path)]
    )
    if deny_read:
        assert result.exit_code != 0
        assert isinstance(result.exception, sqlite3.DatabaseError)
    else:
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        if command == "list":
            assert [row["contract_id"] for row in payload] == ["literal.find"]
        elif command == "show":
            assert payload["id"] == "literal.find"
        else:
            assert payload == []
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")


def test_catalog_show_closes_connection_on_missing_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sqlite3

    import jev_cli.catalog as catalog_module

    opened: list[sqlite3.Connection] = []

    def tracked_connect(path: Path) -> sqlite3.Connection:
        db = connect(path)
        opened.append(db)
        return db

    monkeypatch.setattr(catalog_module, "connect", tracked_connect)
    result = CliRunner().invoke(
        app,
        ["catalog", "show", "absent", "1", "--db", str(tmp_path / "catalog.sqlite")],
    )
    _assert_clean_cli_error(result)
    assert "Unknown contract ID/version" in result.output
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")
