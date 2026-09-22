from pathlib import Path

from jev_cli.secrets import resolve_typesafe_api_key


def test_secret_file_resolution_does_not_expose_value(monkeypatch, tmp_path: Path) -> None:
    p = tmp_path / "key"
    p.write_text("super-secret-value\n", encoding="utf-8")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("TYPESAFE_API_KEY_FILE", str(p))
    resolved = resolve_typesafe_api_key()
    assert resolved.value == "super-secret-value"
    assert "super-secret-value" not in resolved.source
