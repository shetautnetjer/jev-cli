"""Keep the local CLI capabilities while adopting the reviewed published source."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from jev_cli.cli import app


def test_command_tree_keeps_published_and_local_entry_points() -> None:
    """Updating the editable source must retain local hook and path-search entry points."""
    command = get_command(app)
    assert set(command.commands) >= {
        "init",
        "ask",
        "run",
        "batch",
        "search",
        "bench",
        "cookbook",
        "doctor",
        "version",
        "catalog",
        "hook",
    }
    assert set(command.commands["catalog"].commands) == {
        "import",
        "list",
        "show",
        "find",
        "run",
        "decisions",
        "record",
        "observe",
        "outcomes",
    }
    search_options = {
        option for param in command.commands["search"].params for option in param.opts
    }
    assert {"--path-first", "--path-limit", "--semantic", "--semantic-limit"} <= search_options
    hook_options = {option for param in command.commands["hook"].params for option in param.opts}
    assert {"--db", "--event-file", "--provider", "--mcp-config"} <= hook_options


@pytest.mark.parametrize("entry", ["package", "module", "console"])
def test_native_entry_points_register_hook(entry: str) -> None:
    """Import-based and direct-module launches must expose the same registered hook command."""
    prefix = {
        "package": [sys.executable, "-m", "jev_cli"],
        "module": [sys.executable, "-m", "jev_cli.cli"],
        "console": [str(Path(sys.executable).parent / "jev")],
    }[entry]
    result = subprocess.run(
        [*prefix, "hook", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "retained recommendation" in " ".join(result.stdout.split())


def test_path_first_keeps_secure_traversal_refusal(tmp_path: Path, monkeypatch) -> None:
    """The local path selector must retain published refusal of unsupported traversal."""
    monkeypatch.setattr("jev_cli.discovery.SECURE_NOFOLLOW_AVAILABLE", False)
    result = CliRunner().invoke(
        app,
        ["search", "source", str(tmp_path), "--path-first", "--path-limit", "1"],
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "Secure no-follow traversal is unavailable" in result.output
