from __future__ import annotations

import time

import httpx

from jev_cli.models import (
    DecisionContract,
    ProviderResult,
    StatePacket,
)
from jev_cli.providers.validation import normalize_answers, normalize_usage
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
        try:
            body = response.json()
            resolved = body["model"]
            if not isinstance(resolved, str) or not resolved or len(resolved) > 128:
                raise ValueError
            if contract.model != "jev-latest" and resolved != contract.model:
                raise ValueError
            answers = normalize_answers(body["answers"], contract)
            usage = normalize_usage(body.get("usage"))
        except (KeyError, TypeError, ValueError, AttributeError, RuntimeError):
            raise RuntimeError("TypeSafe returned an invalid Jev response") from None
        return ProviderResult(
            requested_model=contract.model,
            resolved_model=resolved,
            answers=answers,
            usage=usage,
            elapsed_ms=elapsed_ms,
        )
