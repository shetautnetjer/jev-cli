import pytest
from pydantic import ValidationError

from jev_cli.models import ChoiceQuestion, DecisionContract, ScoreQuestion


def test_choice_requires_multiple_options() -> None:
    with pytest.raises(ValidationError):
        ChoiceQuestion(instructions="Pick one", criteria={"only": None})


def test_choice_accepts_explicit_unknown() -> None:
    q = ChoiceQuestion(
        instructions="Pick one",
        criteria={"a": None, "unknown_no_match": "Nothing else fits"},
    )
    assert "unknown_no_match" in q.criteria


def test_score_bounds() -> None:
    with pytest.raises(ValidationError):
        ScoreQuestion(instructions="Rate", criteria=["only"])


def test_contract_rejects_unknown_composition_question() -> None:
    with pytest.raises(ValidationError):
        DecisionContract.model_validate(
            {
                "id": "x",
                "version": "1",
                "questions": {
                    "route": {
                        "type": "choice",
                        "instructions": "Pick",
                        "criteria": {"a": None, "b": None},
                    }
                },
                "composition": {
                    "rules": [
                        {
                            "question": "missing",
                            "operator": "eq",
                            "value": "a",
                            "result": "A",
                        }
                    ]
                },
            }
        )
