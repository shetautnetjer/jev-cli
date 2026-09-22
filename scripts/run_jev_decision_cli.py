#!/usr/bin/env python3
"""Run jev-cli directly from a source checkout without installing it first."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from jev_cli.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
