from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jev_cli.discovery import TextChunk
from jev_cli.engine import execute
from jev_cli.models import DecisionContract, NoulCriteria, NoulQuestion, StatePacket
from jev_cli.providers.base import ProviderAdapter
from jev_cli.retrieval.base import RetrievalAdapter


@dataclass
class SearchHit:
    chunk: TextChunk
    retrieval_score: float
    semantic_probability: float | None = None
    features: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.chunk.path),
            "start_line": self.chunk.start_line,
            "end_line": self.chunk.end_line,
            "retrieval_score": self.retrieval_score,
            "semantic_probability": self.semantic_probability,
            "features": self.features,
            "text": self.chunk.text,
        }


def rank_chunks(
    query: str,
    chunks: list[TextChunk],
    retriever: RetrievalAdapter,
) -> list[SearchHit]:
    scores = retriever.score(query, chunks)
    if len(scores) != len(chunks):
        raise ValueError("Retriever returned wrong number of scores")
    hits = [
        SearchHit(chunk=chunk, retrieval_score=score)
        for chunk, score in zip(chunks, scores, strict=True)
    ]
    hits.sort(key=lambda hit: hit.retrieval_score, reverse=True)
    return hits


def semantic_judge(
    query: str,
    hits: list[SearchHit],
    provider: ProviderAdapter,
    *,
    model: str = "jev-latest",
) -> list[SearchHit]:
    contract = DecisionContract(
        id="jev-cli.search.relevance",
        version="1",
        model=model,
        questions={
            "relevant": NoulQuestion(
                instructions={
                    "question": (
                        "Does state.candidate contain evidence directly useful for "
                        "answering state.query?"
                    ),
                    "guidance": "Judge only direct usefulness to the stated query.",
                },
                criteria=NoulCriteria(
                    true="The candidate contains direct evidence useful for the query.",
                    false="The candidate does not contain direct evidence useful for the query.",
                ),
            )
        },
    )
    for hit in hits:
        state = StatePacket(
            data={"query": query, "candidate": hit.chunk.text},
            reference=f"{hit.chunk.path}:{hit.chunk.start_line}-{hit.chunk.end_line}",
        )
        receipt = execute(contract, state, provider)
        hit.semantic_probability = float(receipt.answers["relevant"].value)
    hits.sort(
        key=lambda hit: (
            hit.semantic_probability if hit.semantic_probability is not None else -1.0,
            hit.retrieval_score,
        ),
        reverse=True,
    )
    return hits
