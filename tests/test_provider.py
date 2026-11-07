import json

import httpx
import pytest

from jev_cli.models import DecisionContract, StatePacket
from jev_cli.providers.typesafe import TypeSafeProvider


def _batch_contract() -> DecisionContract:
    return DecisionContract(
        id="test.batch",
        version="1",
        model="jev-1.13.0",
        questions={
            f"q{i}": {"type": "noul", "instructions": f"Does evidence support claim {i}?"}
            for i in range(32)
        },
    )


@pytest.mark.parametrize(
    "fault", ["missing", "extra", "wrong-type", "nonfinite", "boolean", "model", "usage", "json"]
)
def test_direct_provider_rejects_invalid_batch_without_leaking_content(fault: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert len(json.loads(request.content)["questions"]) == 32
        answers = {f"q{i}": {"type": "noul", "noul": 0.9} for i in range(32)}
        body = {
            "model": "jev-1.13.0",
            "answers": answers,
            "usage": {"input_tokens": 100, "output_tokens": 64},
        }
        if fault == "missing":
            del answers["q31"]
        elif fault == "extra":
            answers["private-secret-marker"] = {"type": "noul", "noul": 0.9}
        elif fault == "wrong-type":
            answers["q0"] = {"type": "choice", "choice": "private-secret-marker"}
        elif fault == "nonfinite":
            return httpx.Response(
                200, content=json.dumps(body).replace('"noul": 0.9', '"noul": NaN', 1)
            )
        elif fault == "boolean":
            answers["q0"]["noul"] = True
        elif fault == "model":
            body["model"] = "private-secret-marker"
        elif fault == "usage":
            body["usage"]["input_tokens"] = -1
        elif fault == "json":
            return httpx.Response(200, text="private-secret-marker")
        return httpx.Response(200, json=body)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = TypeSafeProvider(api_key="fake-test-key", client=client)
        with pytest.raises(RuntimeError, match="invalid") as caught:
            provider.evaluate(_batch_contract(), StatePacket(data="private-source-text"))
        assert "private" not in str(caught.value)


def test_direct_provider_accepts_complete_32_question_batch() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": {key: {"type": "noul", "noul": 0.9} for key in body["questions"]},
                "usage": {"input_tokens": 100, "output_tokens": 64},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = TypeSafeProvider(api_key="fake-test-key", client=client).evaluate(
            _batch_contract(), StatePacket(data="evidence")
        )
    assert len(calls) == 1
    assert set(result.answers) == set(_batch_contract().questions)


def test_typesafe_provider_normalizes_answers_and_auth() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer fake-test-key"
        body = json.loads(request.content)
        assert body["model"] == "jev-latest"
        assert body["questions"]["route"]["type"] == "choice"
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": {
                    "route": {
                        "type": "choice",
                        "choice": "inspect",
                        "probabilities": {"inspect": 0.9, "unknown_no_match": 0.1},
                        "confidence": 0.8,
                    }
                },
                "usage": {"input_tokens": 100, "output_tokens": 20},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = TypeSafeProvider(api_key="fake-test-key", client=client)
    contract = DecisionContract.model_validate(
        {
            "id": "test.route",
            "version": "1",
            "questions": {
                "route": {
                    "type": "choice",
                    "instructions": "Which?",
                    "criteria": {"inspect": "Read", "unknown_no_match": "No match"},
                }
            },
        }
    )
    result = provider.evaluate(contract, StatePacket(data={"request": "show"}))
    assert result.resolved_model == "jev-1.13.0"
    assert result.answers["route"].value == "inspect"
    assert result.answers["route"].probabilities == {
        "inspect": 0.9,
        "unknown_no_match": 0.1,
    }
