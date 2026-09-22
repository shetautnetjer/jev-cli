from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "github-token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "openai-key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "jwt-like": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
}

# Project-specific private strings are assembled so the gate can scan itself.
PRIVATE_LITERALS = [
    "/home/" + "aya-hmw",
    "shetaut" + "netjer",
    "Heme-" + "Menat-Weret",
    "127.0.0.1:" + "8971",
    "127.0.0.1:" + "8972",
    "/home/" + "aya-hmw/.aya",
]

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".sh",
    ".ps1",
    ".ini",
    ".cfg",
}


def iter_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_PARTS for part in path.parts):
            continue
        if (
            path.name == "uv.lock"
            or path.suffix.lower() in TEXT_SUFFIXES
            or path.name in {"Dockerfile", "LICENSE", ".gitignore", ".dockerignore"}
        ):
            result.append(path)
    return result


def scan_text(label: str, text: str, where: str) -> list[str]:
    failures: list[str] = []
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            failures.append(f"{where}: matched secret pattern {name}")
    for literal in PRIVATE_LITERALS:
        if literal in text:
            failures.append(f"{where}: matched private-installation literal")
    forbidden_flag = "--" + "api-key"
    if forbidden_flag in text:
        failures.append(f"{where}: raw API-key CLI flag is forbidden")
    return failures


def scan_worktree() -> list[str]:
    failures: list[str] = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        failures.extend(scan_text("worktree", text, str(path.relative_to(ROOT))))
    return failures


def scan_history() -> list[str]:
    if not (ROOT / ".git").exists():
        return []
    check = subprocess.run(
        ["git", "-C", str(ROOT), "rev-list", "--all"],
        check=False,
        capture_output=True,
        text=True,
    )
    if check.returncode != 0 or not check.stdout.strip():
        return []
    history = subprocess.run(
        ["git", "-C", str(ROOT), "log", "-p", "--format=", "--all", "--no-ext-diff"],
        check=False,
        capture_output=True,
        text=True,
    )
    if history.returncode != 0:
        return ["git history: could not inspect patch history"]
    failures = scan_text("history", history.stdout, "git history")
    return failures


def main() -> int:
    failures = scan_worktree() + scan_history()
    if failures:
        print("PUBLICATION GATE: FAIL")
        for failure in sorted(set(failures)):
            print(f"- {failure}")
        return 1
    print("PUBLICATION GATE: PASS")
    print(f"Scanned {len(iter_files())} public text/config files; no forbidden material found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
