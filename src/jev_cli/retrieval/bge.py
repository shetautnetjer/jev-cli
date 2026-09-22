from __future__ import annotations

from typing import Any

from jev_cli.discovery import TextChunk


class BGERetriever:
    name = "bge"

    def __init__(self, model_id: str = "BAAI/bge-small-en-v1.5") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "BGE support is optional. Install with: pip install 'jev-cli[retrieval]'"
            ) from exc
        self.model_id = model_id
        self._model: Any = SentenceTransformer(model_id)

    def score(self, query: str, chunks: list[TextChunk]) -> list[float]:
        if not chunks:
            return []
        query_vec = self._model.encode([query], normalize_embeddings=True)[0]
        chunk_vecs = self._model.encode(
            [chunk.text for chunk in chunks],
            normalize_embeddings=True,
        )
        return [float(query_vec @ vector) for vector in chunk_vecs]
