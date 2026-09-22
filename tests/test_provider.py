import json

import httpx

from jev_cli.models import DecisionContract, StatePacket
from jev_cli.providers.typesafe import TypeSafeProvider


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
