from __future__ import annotations

from typing import Any

from jev_cli.models import DecisionContract, NormalizedAnswer, ProviderResult, StatePacket


class MockProvider:
    """Deterministic provider for tests, examples, and offline benchmark plumbing."""

    name = "mock"

    def evaluate(self, contract: DecisionContract, state: StatePacket) -> ProviderResult:
        supplied: dict[str, Any] = {}
        if isinstance(state.data, dict):
            raw = state.data.get("__mock_answers__", {})
            if isinstance(raw, dict):
                supplied = raw

        answers: dict[str, NormalizedAnswer] = {}
        for qid, question in contract.questions.items():
            wanted = supplied.get(qid)
            if question.type == "choice":
                choice_value = str(wanted) if wanted is not None else next(iter(question.criteria))
                probs = {key: float(key == choice_value) for key in question.criteria}
                answers[qid] = NormalizedAnswer(
                    id=qid,
                    type="choice",
                    value=choice_value,
                    probabilities=probs,
                    confidence=1.0,
                )
            elif question.type == "noul":
                noul_value = float(wanted) if wanted is not None else 1.0
                answers[qid] = NormalizedAnswer(id=qid, type="noul", value=noul_value)
            else:
                score_value = float(wanted) if wanted is not None else 0.0
                probs = {
                    str(i): float(i == round(score_value)) for i in range(len(question.criteria))
                }
                answers[qid] = NormalizedAnswer(
                    id=qid,
                    type="score",
                    value=score_value,
                    probabilities=probs,
                    confidence=1.0,
                )
        return ProviderResult(
            requested_model=contract.model,
            resolved_model="mock",
            answers=answers,
            elapsed_ms=0.0,
        )
