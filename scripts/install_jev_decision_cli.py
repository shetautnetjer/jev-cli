#!/usr/bin/env python3
"""Install jev-cli from a source checkout using the selected Python interpreter."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install jev-cli from this checkout with an explicit Python interpreter."
    )
    parser.add_argument(
        "--editable",
        action="store_true",
        help="Install in editable development mode.",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Also install the development/test extra.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    target = f"{root}[dev]" if args.dev else str(root)

    command = [sys.executable, "-m", "pip", "install"]
    if args.editable:
        command.append("-e")
    command.append(target)

    print("Installing jev-cli with:", sys.executable)
    completed = subprocess.run(command, check=False)
    if completed.returncode == 0:
        print("Installed. Run: jev --help")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
