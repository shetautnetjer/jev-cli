from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolvedSecret:
    value: str
    source: str


def resolve_typesafe_api_key() -> ResolvedSecret:
    direct = os.getenv("TYPESAFE_API_KEY")
    if direct:
        return ResolvedSecret(direct, "environment:TYPESAFE_API_KEY")

    configured = os.getenv("TYPESAFE_API_KEY_FILE")
    candidates = [Path(configured)] if configured else []
    candidates.append(Path("/run/secrets/typesafe_api_key"))

    for path in candidates:
        if not path.exists():
            continue
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise RuntimeError("Configured TypeSafe API key file is empty.")
        return ResolvedSecret(
            value,
            "file:TYPESAFE_API_KEY_FILE" if configured else "file:/run/secrets/typesafe_api_key",
        )

    raise RuntimeError(
        "TypeSafe API key not configured. Set TYPESAFE_API_KEY or TYPESAFE_API_KEY_FILE."
    )
