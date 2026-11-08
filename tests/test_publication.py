from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCANNER = Path(__file__).resolve().parents[1] / "scripts" / "verify_jev_cli_publication.py"


def _checkout(tmp_path: Path, ancestor: str) -> Path:
    """Copy the real gate into a disposable repository without borrowing its Git history."""
    root = tmp_path / ancestor / "checkout"
    (root / "scripts").mkdir(parents=True)
    shutil.copyfile(SCANNER, root / "scripts" / SCANNER.name)
    (root / "README.md").write_text("Public fixture\n", encoding="utf-8")
    subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
    return root


def _scan(root: Path) -> subprocess.CompletedProcess[str]:
    """Execute the copied gate so ROOT is derived from the actual checkout location."""
    return subprocess.run(
        [sys.executable, str(root / "scripts" / SCANNER.name)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize("ancestor", ["workspace", "target", ".venv"])
def test_publication_scans_untracked_files_under_excluded_ancestor(
    tmp_path: Path, ancestor: str
) -> None:
    """An excluded ancestor must not hide an uncommitted finding from the real gate."""
    root = _checkout(tmp_path, ancestor)
    fixture = root / "untracked.txt"
    fixture.write_text("-----BEGIN " + "PRIVATE KEY-----\n", encoding="utf-8")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", fixture.name],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert status.stdout.strip() == "?? untracked.txt"

    result = _scan(root)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "PUBLICATION GATE: FAIL" in result.stdout
    assert "untracked.txt: matched secret pattern private-key" in result.stdout
    assert fixture.read_text(encoding="utf-8").strip() not in result.stdout


def test_publication_retains_in_repository_build_exclusions(tmp_path: Path) -> None:
    """Only internal build/environment trees are skipped, even beneath a target ancestor."""
    root = _checkout(tmp_path, "target")
    for excluded in ("target", ".venv", "__pycache__"):
        directory = root / "nested" / excluded
        directory.mkdir(parents=True)
        (directory / "fixture.txt").write_text(
            "-----BEGIN " + "PRIVATE KEY-----\n", encoding="utf-8"
        )

    result = _scan(root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PUBLICATION GATE: PASS" in result.stdout
    assert "Scanned 2 public text/config files" in result.stdout
