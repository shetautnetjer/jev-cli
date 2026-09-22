from __future__ import annotations

import time
from typing import Any

import httpx

from jev_cli.models import (
    DecisionContract,
    NormalizedAnswer,
    ProviderResult,
    ProviderUsage,
    StatePacket,
)
from jev_cli.secrets import resolve_typesafe_api_key


class TypeSafeProvider:
    name = "typesafe"
    endpoint = "https://api.typesafe.ai/v1/systemone"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _key(self) -> str:
        return self._api_key or resolve_typesafe_api_key().value

    def evaluate(self, contract: DecisionContract, state: StatePacket) -> ProviderResult:
        payload = {
            "state": state.data,
            "model": contract.model,
            "questions": {
                key: question.model_dump(mode="json", exclude_none=True)
                for key, question in contract.questions.items()
            },
        }
        started = time.perf_counter()
        try:
            response = self._client.post(
                self.endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {self._key()}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"TypeSafe request failed with HTTP {exc.response.status_code}."
            ) from None
        except httpx.RequestError:
            raise RuntimeError("TypeSafe request failed due to a transport error.") from None
        elapsed_ms = (time.perf_counter() - started) * 1000
        body: dict[str, Any] = response.json()
        answers: dict[str, NormalizedAnswer] = {}
        for qid, raw in body.get("answers", {}).items():
            qtype = raw.get("type")
            if qtype == "choice":
                value = raw["choice"]
            elif qtype == "noul":
                value = float(raw["noul"])
            elif qtype == "score":
                value = float(raw["score"])
            else:
                raise ValueError(f"Unsupported answer type for {qid}: {qtype!r}")
            answers[qid] = NormalizedAnswer(
                id=qid,
                type=qtype,
                value=value,
                probabilities=raw.get("probabilities"),
                confidence=raw.get("confidence"),
            )
        usage_raw = body.get("usage")
        usage = ProviderUsage.model_validate(usage_raw) if isinstance(usage_raw, dict) else None
        return ProviderResult(
            requested_model=contract.model,
            resolved_model=body.get("model"),
            answers=answers,
            usage=usage,
            elapsed_ms=elapsed_ms,
        )
