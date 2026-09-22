from __future__ import annotations

from typing import Protocol

from jev_cli.discovery import TextChunk


class RetrievalAdapter(Protocol):
    name: str
    model_id: str

    def score(self, query: str, chunks: list[TextChunk]) -> list[float]: ...
