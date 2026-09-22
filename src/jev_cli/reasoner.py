from __future__ import annotations

from typing import Any, Protocol


class ModelCallAdapter(Protocol):
    """Host-supplied bridge to an existing generative model core-call/router."""

    name: str

    def complete_json(
        self,
        *,
        instruction: str,
        state: Any,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]: ...


ReasonerAdapter = ModelCallAdapter
