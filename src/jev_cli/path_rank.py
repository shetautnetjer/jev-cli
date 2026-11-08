"""Local-only filename recall for optional path-first Jev search.

Path scores are navigation leads, never source evidence or model probabilities.
"""

from __future__ import annotations

import re
from pathlib import Path

from jev_cli.discovery import DiscoveredFile

SENSITIVE_NAMES = {
    "credentials",
    "credentials.json",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "id_rsa",
    "id_ed25519",
    ".netrc",
    ".npmrc",
}
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def rank_paths(query: str, files: list[DiscoveredFile]) -> list[tuple[DiscoveredFile, float]]:
    """Rank eligible file names by token overlap; use stable path order for ties."""
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    ranked = []
    for file in files:
        path = file.relative_path or Path(file.path.name)
        parts = path.parts
        if any(
            part.startswith(".")
            or part.lower() in SENSITIVE_NAMES
            or part.lower().endswith(SENSITIVE_SUFFIXES)
            for part in parts
        ):
            continue
        tokens = set(re.findall(r"[a-z0-9]+", path.as_posix().lower()))
        score = len(words & tokens) / len(words) if words else 0.0
        ranked.append((file, score))
    return sorted(ranked, key=lambda item: (-item[1], str(item[0].path)))
