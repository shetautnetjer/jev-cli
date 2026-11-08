import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jev_cli.catalog import connect, import_contract
from jev_cli.cli import app
from jev_cli.hooks import HookConfig, HookEvent, run_hook
from jev_cli.models import DecisionContract
from jev_cli.providers.mock import MockProvider


def setup(tmp_path):
    db = connect(tmp_path / "catalog.sqlite")
    import_contract(
        db,
        DecisionContract(
            id="turn.route",
            version="1",
            questions={
                "route": {
                    "type": "choice",
                    "instructions": "Select represented intent",
                    "criteria": {"casual": "Casual conversation", "unknown": "Missing coverage"},
                }
            },
        ),
    )
    config = HookConfig.model_validate(
        {"routes": {"turn.prepare": {"contract_id": "turn.route", "version": "1"}}}
    )
    event = HookEvent.model_validate(
        {
            "source": "test-runtime",
            "id": "event-1",
            "name": "turn.prepare",
            "correlation": {"operation_id": "op-1"},
            "state": {"data": {"request": "hello"}, "reference": "fixture:hello"},
        }
    )
    return db, config, event


class CountingProvider(MockProvider):
    calls = 0

    def evaluate(self, contract, state):
        self.calls += 1
        return super().evaluate(contract, state)


def test_hook_replay_retains_one_decision_and_no_automatic_effect(tmp_path):
    db, config, event = setup(tmp_path)
    p = CountingProvider()
    first = run_hook(db, config, event, lambda: p)
    replay = run_hook(db, config, event, lambda: pytest.fail("replay called provider"))
    assert first["status"] == replay["status"] == "completed"
    assert replay["replayed"] is True
    assert p.calls == 1
    assert first["telemetry"]["evaluation_attempted"] is True
    assert replay["telemetry"]["evaluation_attempted"] is False
    assert replay["telemetry"]["usage"] is None
    assert first["receipt"] == replay["receipt"]
    assert db.execute("select count(*) from decisions").fetchone()[0] == 1
    assert db.execute("select count(*) from outcomes").fetchone()[0] == 0
    assert "hello" not in json.dumps(first["telemetry"])
    assert first["telemetry"]["operation_id"] == "op-1"
    db.close()


def test_unmapped_event_skips_without_opening_provider(tmp_path):
    db, config, event = setup(tmp_path)
    event.name = "tool.finished"
    out = run_hook(db, config, event, lambda: pytest.fail("unmapped event called provider"))
    assert out["status"] == "skipped"
    assert db.execute("select count(*) from decisions").fetchone()[0] == 0
    db.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "turn.other"),
        ("correlation", {"operation_id": "op-2"}),
        ("state", {"data": {"request": "different"}, "reference": "fixture:hello"}),
    ],
)
def test_reused_event_id_cannot_change_evidence(tmp_path, field, value):
    db, config, event = setup(tmp_path)
    run_hook(db, config, event, CountingProvider)
    changed = event.model_dump()
    changed[field] = value
    event2 = HookEvent.model_validate(changed)
    config.routes["turn.other"] = config.routes["turn.prepare"]
    with pytest.raises(ValueError, match="different"):
        run_hook(db, config, event2, lambda: pytest.fail("changed event called provider"))
    db.close()


def test_pending_and_failed_are_not_automatically_retried(tmp_path):
    db, config, event = setup(tmp_path)
    observed = []

    class Broken:
        name = "broken"

        def evaluate(self, contract, state):
            # Simulate delivery overlap while the original invocation is running.
            other = connect(tmp_path / "catalog.sqlite")
            observed.append(
                run_hook(other, config, event, lambda: pytest.fail("duplicate called provider"))
            )
            other.close()
            raise RuntimeError("SECRET_PROVIDER_ERROR")

    first = run_hook(db, config, event, Broken)
    replay = run_hook(db, config, event, lambda: pytest.fail("failed call retried"))
    assert observed[0]["status"] == "pending"
    assert first["status"] == replay["status"] == "failed"
    assert "SECRET" not in json.dumps(first)
    db.close()


def test_factory_failure_is_retained(tmp_path):
    db, config, event = setup(tmp_path)

    def broken():
        raise RuntimeError("SECRET_CONFIG_ERROR")

    result = run_hook(db, config, event, broken)
    assert result["status"] == "failed"
    assert db.execute("select status from decisions").fetchone()[0] == "failed"
    assert "SECRET" not in json.dumps(result)
    db.close()


def test_new_hook_rejects_pending_caller_transaction_without_rollback(tmp_path):
    """Admission must not roll back unrelated writes on the caller's connection."""
    db, config, event = setup(tmp_path)
    try:
        db.execute("CREATE TABLE caller_work (content TEXT)")
        db.execute("INSERT INTO caller_work VALUES ('caller-owned pending bytes')")
        assert db.in_transaction
        with pytest.raises((ValueError, RuntimeError)) as rejected:
            run_hook(db, config, event, lambda: pytest.fail("admission opened provider"))
        assert db.in_transaction
        assert db.execute("SELECT content FROM caller_work").fetchone()[0] == (
            "caller-owned pending bytes"
        )
        assert db.execute("SELECT count(*) FROM decisions").fetchone()[0] == 0
        assert isinstance(rejected.value, ValueError)
        assert "pending transaction" in str(rejected.value)
        db.rollback()
        assert not db.in_transaction
        assert db.execute("SELECT count(*) FROM caller_work").fetchone()[0] == 0
    finally:
        db.close()


@pytest.mark.parametrize("existing", ["replay", "unmapped"])
def test_read_only_hook_paths_preserve_pending_caller_transaction(tmp_path, existing):
    """Replaying a receipt or skipping an unmapped event needs no owned transaction."""
    db, config, event = setup(tmp_path)
    try:
        if existing == "replay":
            retained = run_hook(db, config, event, MockProvider)
        else:
            event.name = "unmapped.event"
        db.execute("CREATE TABLE caller_work (content TEXT)")
        db.execute("INSERT INTO caller_work VALUES ('caller-owned pending bytes')")
        result = run_hook(db, config, event, lambda: pytest.fail("read opened provider"))
        assert db.in_transaction
        assert db.execute("SELECT content FROM caller_work").fetchone()[0] == (
            "caller-owned pending bytes"
        )
        if existing == "replay":
            assert result["replayed"]
            assert result["receipt"] == retained["receipt"]
        else:
            assert result["status"] == "skipped"
        db.rollback()
        assert db.execute("SELECT count(*) FROM caller_work").fetchone()[0] == 0
    finally:
        db.close()


def test_cli_reads_stdin_and_replay_needs_no_credentials(tmp_path: Path):
    db, config, event = setup(tmp_path)
    db.close()
    cfg = tmp_path / "hooks.json"
    cfg.write_text(config.model_dump_json())
    runner = CliRunner()
    args = ["hook", str(cfg), "--db", str(tmp_path / "catalog.sqlite"), "--provider", "mock"]
    out = runner.invoke(app, args, input=event.model_dump_json())
    assert out.exit_code == 0, out.output
    result = json.loads(out.stdout)
    assert result["status"] == "completed"
    args[-1] = "mcp"  # no config needed when reopening a completed receipt
    out = runner.invoke(app, args, input=event.model_dump_json())
    assert out.exit_code == 0, out.output
    assert json.loads(out.stdout)["replayed"] is True


def test_telemetry_excludes_provider_usage_extensions(tmp_path):
    from jev_cli.models import ProviderUsage

    db, config, event = setup(tmp_path)

    class Extra(CountingProvider):
        def evaluate(self, contract, state):
            result = super().evaluate(contract, state)
            result.usage = ProviderUsage(input_tokens=10, debug="PRIVATE_PROVIDER_TEXT")
            return result

    result = run_hook(db, config, event, Extra)
    assert result["telemetry"]["usage"] == {"input_tokens": 10}
    assert "PRIVATE" not in json.dumps(result["telemetry"])
    db.close()


def test_cli_database_failure_is_content_free(tmp_path):
    db, config, event = setup(tmp_path)
    db.close()
    cfg = tmp_path / "hooks.json"
    cfg.write_text(config.model_dump_json())
    broken = tmp_path / "broken.sqlite"
    broken.write_bytes(b"invalid sqlite bytes")
    result = CliRunner().invoke(
        app, ["hook", str(cfg), "--db", str(broken)], input=event.model_dump_json()
    )
    assert result.exit_code == 1
    assert "Hook failed:" in result.output
    assert "hello" not in result.output
