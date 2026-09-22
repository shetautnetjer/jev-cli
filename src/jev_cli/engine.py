from __future__ import annotations

import hashlib
import json
from typing import Any

from jev_cli.models import (
    CompositionRule,
    DecisionContract,
    DecisionReceipt,
    NormalizedAnswer,
    StatePacket,
)
from jev_cli.providers.base import ProviderAdapter


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _matches(rule: CompositionRule, answer: NormalizedAnswer) -> bool:
    actual = answer.value
    expected = rule.value
    if rule.operator == "eq":
        return actual == expected
    if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
        return False
    if rule.operator == "gte":
        return actual >= expected
    if rule.operator == "lte":
        return actual <= expected
    return False


def compose(contract: DecisionContract, answers: dict[str, NormalizedAnswer]) -> Any:
    policy = contract.composition
    if policy:
        for rule in policy.rules:
            answer = answers.get(rule.question)
            if answer is not None and _matches(rule, answer):
                return rule.result
        return policy.default

    if len(answers) == 1:
        return next(iter(answers.values())).value
    return {key: answer.value for key, answer in answers.items()}


def execute(
    contract: DecisionContract,
    state: StatePacket,
    provider: ProviderAdapter,
) -> DecisionReceipt:
    result = provider.evaluate(contract, state)
    return DecisionReceipt(
        contract_id=contract.id,
        contract_version=contract.version,
        contract_sha256=sha256_json(contract.model_dump(mode="json", exclude_none=True)),
        state_sha256=sha256_json(state.data),
        state_reference=state.reference,
        provider=provider.name,
        requested_model=result.requested_model,
        resolved_model=result.resolved_model,
        answers=result.answers,
        usage=result.usage,
        provider_elapsed_ms=result.elapsed_ms,
        composition=compose(contract, result.answers),
    )
