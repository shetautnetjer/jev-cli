"""Offline path→source discovery; no external provider or catalog mutation."""

import json
from pathlib import Path

from typer.testing import CliRunner

from jev_cli.cli import app

runner = CliRunner()


def test_path_first_reads_only_selected_source_and_labels_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    """Filename recall limits source reads and labels unverified navigation separately from hits."""
    invoice = tmp_path / "src" / "billing" / "invoice_handler.py"
    invoice.parent.mkdir(parents=True)
    invoice.write_text("def send_invoice():\n    return 'invoice sent'\n", encoding="utf-8")
    session = tmp_path / "src" / "auth" / "session.py"
    session.parent.mkdir(parents=True)
    session.write_text("def login():\n    return 'ok'\n", encoding="utf-8")
    monkeypatch.setattr(
        "jev_cli.cli._provider",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("provider called")),
    )

    result = runner.invoke(
        app, ["search", "invoice", str(tmp_path), "--path-first", "--path-limit", "1"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["path_candidates"][0]["evidence_type"] == "path-candidate"
    assert data["path_candidates"][0]["path"] == str(invoice)
    assert data["path_candidates"][0]["path_score"] > 0
    assert data["chunks_considered"] == 1
    assert data["hits"][0]["evidence_type"] == "source-chunk"
    assert data["hits"][0]["path"] == str(invoice)
    assert data["hits"][0]["semantic_probability"] is None
    assert data["path_candidates"][0]["verified"] is False
    assert data["catalog_recorded"] is False


def test_path_first_hides_ignored_and_sensitive_names(tmp_path: Path) -> None:
    """Directory discovery excludes ignored, sensitive and symlinked paths before ranking."""
    (tmp_path / "safe.py").write_text("def visible(): pass\n", encoding="utf-8")
    (tmp_path / ".env").write_text("secret=do-not-report\n", encoding="utf-8")
    (tmp_path / "private.key").write_text("secret=do-not-report\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("def ignored(): pass\n", encoding="utf-8")
    outside = tmp_path.parent / "outside-secret.py"
    outside.write_text("def outside(): pass\n", encoding="utf-8")
    (tmp_path / "alias.py").symlink_to(outside)
    result = runner.invoke(
        app, ["search", "secret", str(tmp_path), "--path-first", "--path-limit", "4"]
    )
    assert result.exit_code == 0, result.output
    text = result.stdout
    assert "safe.py" in text
    for forbidden in (
        ".env",
        "private.key",
        "ignored.py",
        "alias.py",
        "outside-secret.py",
        "do-not-report",
    ):
        assert forbidden not in text


def test_path_first_optional_mock_jev_judges_selected_chunks(tmp_path: Path) -> None:
    """Explicit semantic judging receives only the bounded set selected by path ranking."""
    chosen = tmp_path / "invoice.py"
    chosen.write_text("def invoice():\n    return 1\n", encoding="utf-8")
    (tmp_path / "session.py").write_text("def session():\n    return 2\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "search",
            "invoice",
            str(tmp_path),
            "--path-first",
            "--path-limit",
            "1",
            "--semantic",
            "--semantic-limit",
            "1",
            "--provider",
            "mock",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["files_discovered"] == 2
    assert data["files_selected"] == 1
    assert data["semantic_pool"] == 1
    assert data["hits"][0]["path"] == str(chosen)
    assert data["hits"][0]["semantic_probability"] == 1.0
    assert data["catalog_recorded"] is False


def test_path_limit_requires_path_first(tmp_path: Path) -> None:
    """A path-only limit cannot silently change ordinary search behavior."""
    (tmp_path / "safe.py").write_text("hello\n", encoding="utf-8")
    result = runner.invoke(app, ["search", "hello", str(tmp_path), "--path-limit", "1"])
    assert result.exit_code == 2


def test_explicit_path_keeps_hidden_parent_selection_but_filters_basename(tmp_path: Path) -> None:
    """Directory exclusions must not silently redefine a caller's explicit file selection."""
    hidden = tmp_path / ".checkout"
    hidden.mkdir()
    source = hidden / "selected.py"
    source.write_text("def selected(): return 1\n")
    sensitive = hidden / ".env"
    sensitive.write_text("fixture=never-selected\n")
    directory = runner.invoke(
        app, ["search", "selected", str(tmp_path), "--path-first", "--path-limit", "2"]
    )
    assert directory.exit_code == 0, directory.output
    assert json.loads(directory.stdout)["files_selected"] == 0
    literal = runner.invoke(
        app, ["search", "selected", str(source), "--path-first", "--path-limit", "2"]
    )
    assert literal.exit_code == 0, literal.output
    assert json.loads(literal.stdout)["files_selected"] == 1
    assert json.loads(literal.stdout)["hits"][0]["path"] == str(source)
    excluded = runner.invoke(
        app, ["search", "fixture", str(sensitive), "--path-first", "--path-limit", "2"]
    )
    assert excluded.exit_code == 0, excluded.output
    assert json.loads(excluded.stdout)["files_selected"] == 0
    assert "never-selected" not in excluded.output
