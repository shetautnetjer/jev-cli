from jev_cli.engine import execute
from jev_cli.models import DecisionContract, StatePacket
from jev_cli.providers.mock import MockProvider


def test_receipt_does_not_persist_raw_state() -> None:
    contract = DecisionContract.model_validate(
        {
            "id": "test.route",
            "version": "1",
            "questions": {
                "route": {
                    "type": "choice",
                    "instructions": "Which?",
                    "criteria": {
                        "inspect": "Read",
                        "unknown_no_match": "No match",
                    },
                }
            },
            "composition": {
                "rules": [
                    {
                        "question": "route",
                        "operator": "eq",
                        "value": "inspect",
                        "result": "READ_ONLY",
                    }
                ],
                "default": "ESCALATE",
            },
        }
    )
    secret_state = "sensitive text that must not appear in receipt"
    receipt = execute(
        contract,
        StatePacket(data={"text": secret_state, "__mock_answers__": {"route": "inspect"}}),
        MockProvider(),
    )
    rendered = receipt.model_dump_json()
    assert secret_state not in rendered
    assert receipt.composition == "READ_ONLY"
    assert len(receipt.state_sha256) == 64
