from __future__ import annotations

import re

from jev_cli.discovery import TextChunk

TOKEN = re.compile(r"[A-Za-z0-9_./:-]{2,}")


def _tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in TOKEN.finditer(text)}


class LexicalRetriever:
    name = "lexical"
    model_id = "token-overlap-v1"

    def score(self, query: str, chunks: list[TextChunk]) -> list[float]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return [0.0 for _ in chunks]
        result: list[float] = []
        for chunk in chunks:
            overlap = query_tokens & _tokens(chunk.text)
            result.append(len(overlap) / len(query_tokens))
        return result
