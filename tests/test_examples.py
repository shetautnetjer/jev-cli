from pathlib import Path

from jev_cli.io import load_contract

ROOT = Path(__file__).resolve().parents[1]


def test_public_yaml_examples_are_valid_decision_contracts() -> None:
    examples = [
        ROOT / "examples" / "route.yaml",
        ROOT / "examples" / "informed-route.yaml",
        ROOT / "examples" / "decision-basis.yaml",
    ]
    for path in examples:
        contract = load_contract(path)
        assert contract.id
        assert contract.questions


def test_informed_route_preserves_no_match() -> None:
    contract = load_contract(ROOT / "examples" / "informed-route.yaml")
    route = contract.questions["route"]
    assert route.type == "choice"
    assert "unknown_no_match" in route.criteria


def test_decision_basis_example_separates_movement_and_reason() -> None:
    contract = load_contract(ROOT / "examples" / "decision-basis.yaml")
    assert set(contract.questions) == {
        "next_operator",
        "decision_basis",
        "prepared_effect_present",
    }
    assert contract.questions["next_operator"].type == "choice"
    assert contract.questions["decision_basis"].type == "choice"
    assert contract.questions["prepared_effect_present"].type == "noul"
