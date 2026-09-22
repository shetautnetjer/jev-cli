from pathlib import Path

from typer.testing import CliRunner

from jev_cli.cli import app

runner = CliRunner()


def test_cli_init_and_mock_run(tmp_path: Path) -> None:
    contract = tmp_path / "contract.yaml"
    result = runner.invoke(app, ["init", str(contract)])
    assert result.exit_code == 0
    assert contract.exists()

    state = tmp_path / "state.json"
    state.write_text(
        '{"request":"show","__mock_answers__":{"route":"inspect"}}',
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["run", str(contract), "--state-file", str(state), "--provider", "mock"],
    )
    assert result.exit_code == 0
    assert '"provider": "mock"' in result.stdout


def test_search_semantic_requires_explicit_pool(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("decision contract", encoding="utf-8")
    result = runner.invoke(
        app,
        ["search", "decision", str(tmp_path), "--semantic", "--provider", "mock"],
    )
    assert result.exit_code == 2


def test_missing_credential_is_concise(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY_FILE", raising=False)
    result = runner.invoke(
        app,
        [
            "ask",
            "noul",
            "--instructions",
            "Is this explicit?",
            "--state",
            "yes",
        ],
    )
    assert result.exit_code == 1
    assert "TypeSafe API key not configured" in result.output
    assert "Traceback" not in result.output
