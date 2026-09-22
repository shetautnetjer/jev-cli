from __future__ import annotations

from typing import Any


class GLiNERExtractor:
    name = "gliner"

    def __init__(self, model_id: str = "gliner-community/gliner_small-v2.5") -> None:
        try:
            from gliner import GLiNER  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "GLiNER support is optional. Install with: pip install 'jev-cli[extraction]'"
            ) from exc
        self.model_id = model_id
        self._model: Any = GLiNER.from_pretrained(model_id)

    def extract(
        self,
        text: str,
        labels: list[str],
        *,
        threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        if not labels:
            return []
        rows = self._model.predict_entities(text, labels, threshold=threshold)
        return [
            {
                "text": row.get("text"),
                "label": row.get("label"),
                "score": float(row.get("score", 0.0)),
                "start": row.get("start"),
                "end": row.get("end"),
            }
            for row in rows
        ]
