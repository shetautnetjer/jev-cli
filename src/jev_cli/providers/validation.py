"""Common wire-answer checks for direct and MCP Jev providers."""

from __future__ import annotations

import math
from typing import Any

from jev_cli.models import DecisionContract, NormalizedAnswer, ProviderUsage


def probability(value: Any) -> bool:
    """Accept finite numeric probabilities in [0, 1], excluding booleans."""
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def normalize_answers(raw_answers: Any, contract: DecisionContract) -> dict[str, NormalizedAnswer]:
    """Reject incomplete, mistyped or inconsistent batches without echoing payloads."""
    try:
        if not isinstance(raw_answers, dict) or set(raw_answers) != set(contract.questions):
            raise ValueError
        answers = {}
        for qid, question in contract.questions.items():
            raw = raw_answers[qid]
            if raw["type"] != question.type:
                raise ValueError
            value = raw[question.type]
            dist = raw.get("probabilities")
            confidence = raw.get("confidence")
            if question.type == "noul":
                if not probability(value):
                    raise ValueError
                dist = confidence = None
            else:
                expected = (
                    set(question.criteria)
                    if question.type == "choice"
                    else {str(i) for i in range(len(question.criteria))}
                )
                if not isinstance(dist, dict) or set(dist) != expected:
                    raise ValueError
                if not all(probability(p) for p in dist.values()):
                    raise ValueError
                if abs(sum(dist.values()) - 1) > 0.01 or not probability(confidence):
                    raise ValueError
                if question.type == "choice":
                    if not isinstance(value, str) or value not in expected:
                        raise ValueError
                    if dist[value] < max(dist.values()) - 1e-6:
                        raise ValueError
                else:
                    if type(value) not in (int, float) or not math.isfinite(value):
                        raise ValueError
                    if not 0 <= value <= len(question.criteria) - 1:
                        raise ValueError
                    if abs(value - sum(int(k) * p for k, p in dist.items())) > 0.02:
                        raise ValueError
            answers[qid] = NormalizedAnswer(
                id=qid,
                type=question.type,
                value=value,
                probabilities=dist,
                confidence=confidence,
            )
        return answers
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise RuntimeError("Provider returned invalid Jev answers") from None


def normalize_usage(raw: Any) -> ProviderUsage | None:
    """Accept absent usage or nonnegative integer token counters without coercion."""
    if raw is None:
        return None
    try:
        counters = {k: raw[k] for k in ("input_tokens", "output_tokens")}
        if any(type(v) is not int or v < 0 for v in counters.values()):
            raise ValueError
        return ProviderUsage(**counters)
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Provider returned invalid Jev usage") from None
