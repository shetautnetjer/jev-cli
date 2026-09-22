from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from jev_cli.models import DecisionContract, StatePacket


def load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_contract(path: Path) -> DecisionContract:
    return DecisionContract.model_validate(load_mapping(path))


def state_from_source(
    *,
    state_text: str | None = None,
    state_file: Path | None = None,
    reference: str | None = None,
) -> StatePacket:
    if state_text is not None and state_file is not None:
        raise ValueError("Use either --state or --state-file, not both")

    if state_file is not None:
        raw = state_file.read_text(encoding="utf-8")
        if state_file.suffix.lower() == ".json":
            data: Any = json.loads(raw)
        else:
            data = raw
        return StatePacket(data=data, reference=reference or str(state_file))

    if state_text is not None:
        return StatePacket(data=state_text, reference=reference)

    if sys.stdin.isatty():
        raise ValueError("No state supplied. Use --state, --state-file, or stdin.")
    raw = sys.stdin.read()
    return StatePacket(data=raw, reference=reference)


def dump_json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", exclude_none=True)
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
