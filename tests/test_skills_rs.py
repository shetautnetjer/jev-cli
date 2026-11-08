"""Cross-language fixtures for the optional Rust projection/replay binary."""

import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from jev_cli.engine import execute
from jev_cli.models import DecisionContract, StatePacket
from jev_cli.providers.mock import MockProvider

BINARY = os.getenv("SKILLS_RS_BIN")
pytestmark = pytest.mark.skipif(not BINARY, reason="Build skills-rs and set SKILLS_RS_BIN")
SKILL = Path(__file__).resolve().parents[1] / "integrations" / "pipelex"


def invoke(*args):
    """Run the explicitly selected offline binary and parse its single JSON result."""
    result = subprocess.run(
        [BINARY, *map(str, args)], text=True, capture_output=True, timeout=10, check=False
    )
    return result, json.loads(result.stdout)


def fixture_packet(value=0.95, default="needs_evidence", state=None):
    """Produce Python-owned typed receipts with configurable composition and state hashing."""
    contract = DecisionContract(
        id="test.rust-parity",
        version="1",
        model="jev-1.13.0",
        questions={
            "supported": {"type": "noul", "instructions": "Is the claim supported?"},
            "kind": {
                "type": "choice",
                "instructions": "Choose the represented kind.",
                "criteria": {"decision": "An accepted choice.", "unknown": "Not represented."},
            },
            "clarity": {
                "type": "score",
                "instructions": "Rate the clarity of evidence.",
                "criteria": ["Absent", "Ambiguous", "Explicit"],
            },
        },
        composition={
            "rules": [
                {"question": "supported", "operator": "gte", "value": 0.8, "result": "ready"}
            ],
            "default": default,
        },
    )
    packet = StatePacket(
        data=state
        if state is not None
        else {
            "source": "A source supports a planned decision, not a completed deployment.",
            "__mock_answers__": {"supported": value, "kind": "decision", "clarity": 2},
        },
        reference="fixture:rust-parity",
    )
    return contract, packet, execute(contract, packet, MockProvider())


def write_inputs(tmp_path, contract, state, receipt):
    """Serialize contract, state and receipt independently for cross-language replay."""
    values = [
        contract.model_dump(mode="json", exclude_none=True),
        state.data,
        receipt.model_dump(mode="json"),
    ]
    files = [tmp_path / name for name in ["contract.json", "state.json", "receipt.json"]]
    for path, value in zip(files, values, strict=True):
        path.write_text(json.dumps(value, ensure_ascii=False))
    return files


@pytest.fixture
def projection(tmp_path):
    """Generate a fresh projection from the pinned method source for each replay fixture."""
    path = tmp_path / "projection.json"
    result, value = invoke("project", SKILL, "--out", path)
    assert result.returncode == 0, result.stdout
    assert value["schema_version"] == "jev-cli/skill-projection-v1"
    return path


@pytest.mark.parametrize(
    "probability,default,expected",
    [
        (0.95, "needs_evidence", "ready"),
        (0.5, "needs_evidence", "needs_evidence"),
        (0.5, "unrepresented", "unknown_no_match"),
    ],
)
def test_rust_replay_matches_python_receipt(tmp_path, projection, probability, default, expected):
    """Verified Rust replay preserves Python answers and recomputes routes without inference."""
    contract, state, receipt = fixture_packet(probability, default)
    paths = write_inputs(tmp_path, contract, state, receipt)
    result, value = invoke("replay", projection, *paths, "--skill-dir", SKILL)
    assert result.returncode == 0, result.stdout
    assert value["output"]["receipt"] == receipt.model_dump(mode="json")
    assert value["output"]["disposition"] == expected
    assert value["inference_attempted"] is False
    assert value["authority_granted"] is False
    assert value["source_verified"] is True


@pytest.mark.parametrize("number", [0.0000001, 0.00001, 0.0001, 1e15, 1e16, 1e20, -0.0, 1.0])
def test_canonical_state_hash_matches_python_for_unicode_and_numbers(tmp_path, projection, number):
    """Unicode and numeric formatting must produce identical canonical state hashes."""
    contract, state, receipt = fixture_packet(state={"résumé": "Ma’at 🧠", "number": number})
    paths = write_inputs(tmp_path, contract, state, receipt)
    result, value = invoke("replay", projection, *paths)
    assert result.returncode == 0, result.stdout
    assert value["source_verified"] is False
    assert value["output"]["receipt"]["state_sha256"] == receipt.state_sha256


@pytest.mark.parametrize("fault", ["state", "contract", "composition", "missing", "range", "type"])
def test_replay_rejects_mismatches_without_echoing_source(tmp_path, projection, fault):
    """Tampered state, identity, answers or composition fail without exposing source markers."""
    contract, state, receipt = fixture_packet()
    paths = write_inputs(tmp_path, contract, state, receipt)
    record = receipt.model_dump(mode="json")
    if fault == "state":
        paths[1].write_text(json.dumps({"changed": "private-source-marker"}))
    elif fault == "contract":
        obj = contract.model_dump(mode="json", exclude_none=True)
        obj["version"] = "changed"
        paths[0].write_text(json.dumps(obj))
    elif fault == "composition":
        record["composition"] = "private-source-marker"
    elif fault == "missing":
        del record["answers"]["kind"]
    elif fault == "range":
        record["answers"]["supported"]["value"] = 2
    else:
        record["answers"]["supported"]["type"] = "choice"
    paths[2].write_text(json.dumps(record))
    result, value = invoke("replay", projection, *paths)
    assert result.returncode != 0
    assert value["status"] == "error"
    assert "private-source-marker" not in result.stdout + result.stderr


def test_projection_is_deterministic_and_does_not_overwrite(tmp_path, projection):
    """Repeated projection is stable and refuses replacement without leaving temporary artifacts."""
    before = projection.read_bytes()
    first = json.loads(before)
    result, second = invoke("project", SKILL)
    assert result.returncode == 0
    assert first == second
    result, _ = invoke("project", SKILL, "--out", projection)
    assert result.returncode != 0
    assert projection.read_bytes() == before
    assert not list(tmp_path.glob(".skills-rs-*.tmp"))


def test_projector_rejects_python_drift_and_unsupported_methods(tmp_path):
    """Changed adapter bytes or unsupported method nodes cannot produce an accepted projection."""
    folder = tmp_path / "skill"
    shutil.copytree(SKILL, folder)
    adapter = folder / "jev_method.py"
    original = adapter.read_bytes()
    adapter.write_bytes(original + b"\n# changed behavior needs qualification\n")
    result, _ = invoke("project", folder)
    assert result.returncode != 0
    adapter.write_bytes(original)
    method = folder / "decision.mthds"
    method.write_text(method.read_text().replace('type = "PipeSequence"', 'type = "PipeLLM"'))
    target = tmp_path / "bad.json"
    result, _ = invoke("project", folder, "--out", target)
    assert result.returncode != 0
    assert not target.exists()


def test_verify_detects_source_or_artifact_drift(tmp_path, projection):
    """Verification checks both source hashes and the projection contents against alteration."""
    folder = tmp_path / "skill"
    shutil.copytree(SKILL, folder)
    guide = folder / "SKILL.md"
    guide.write_text(guide.read_text() + "\nChanged guide.\n")
    result, _ = invoke("verify", projection, folder)
    assert result.returncode != 0
    artifact = json.loads(projection.read_text())
    altered = copy.deepcopy(artifact)
    altered["entrypoint"] = "unrelated"
    projection.write_text(json.dumps(altered))
    result, _ = invoke("verify", projection, SKILL)
    assert result.returncode != 0


def test_cli_rejects_duplicate_receipt_keys(tmp_path, projection):
    """Ambiguous duplicate JSON fields are rejected without echoing their supplied values."""
    contract, state, receipt = fixture_packet()
    paths = write_inputs(tmp_path, contract, state, receipt)
    raw = paths[2].read_text()
    paths[2].write_text(raw[:-1] + ', "composition": "private-source-marker"}')
    result, value = invoke("replay", projection, *paths)
    assert result.returncode != 0
    assert value["status"] == "error"
    assert "private-source-marker" not in result.stdout + result.stderr


def test_replay_accepts_complete_32_question_receipt(tmp_path, projection):
    """The full supported batch keeps all typed answers and its Python-computed composition."""
    questions = {
        f"q{i}": {"type": "noul", "instructions": f"Is fixture fact {i} supported?"}
        for i in range(32)
    }
    contract = DecisionContract(
        id="test.batch-32",
        version="1",
        questions=questions,
        composition={
            "rules": [{"question": "q31", "operator": "gte", "value": 0.8, "result": "ready"}],
            "default": "needs_evidence",
        },
    )
    state = StatePacket(data={"__mock_answers__": {key: 0.95 for key in questions}})
    receipt = execute(contract, state, MockProvider())
    result, value = invoke("replay", projection, *write_inputs(tmp_path, contract, state, receipt))
    assert result.returncode == 0, result.stdout
    assert value["output"]["receipt"] == receipt.model_dump(mode="json")
    assert len(value["output"]["receipt"]["answers"]) == 32


@pytest.mark.parametrize("operator,operand", [("eq", True), ("gte", True), ("lte", 1)])
def test_numeric_and_boolean_composition_matches_python(tmp_path, projection, operator, operand):
    """Rust comparisons preserve Python numeric/boolean rule semantics for represented operands."""
    contract, state, _ = fixture_packet(value=1)
    rule = contract.composition.rules[0]
    rule.operator = operator
    rule.value = operand
    receipt = execute(contract, state, MockProvider())
    result, value = invoke("replay", projection, *write_inputs(tmp_path, contract, state, receipt))
    assert result.returncode == 0, result.stdout
    assert value["output"]["disposition"] == receipt.composition == "ready"


@pytest.mark.parametrize("resolved", ["typesafe/jev-1.13", "typesafe/jev-1.13-20260917"])
def test_replay_preserves_normalized_mcp_fallback_identity(tmp_path, projection, resolved):
    """Rust replay must retain aliases and versioned labels accepted by Python normalization."""
    contract, state, receipt = normalized_mcp_packet(resolved)
    result, value = invoke("replay", projection, *write_inputs(tmp_path, contract, state, receipt))
    assert result.returncode == 0, result.stdout
    assert value["output"]["receipt"] == receipt.model_dump(mode="json")
    assert value["output"]["receipt"]["requested_model"] == "typesafe/jev-1.13"
    assert value["output"]["receipt"]["resolved_model"] == resolved


def normalized_mcp_packet(resolved="typesafe/jev-1.13-20260917"):
    """Create an actual normalized receipt from advertised fixture routing, without transport."""
    from jev_cli.providers.mcp import normalize

    contract = DecisionContract(
        id="test.mcp-replay",
        version="1",
        model="jev-1.13.0",
        questions={"present": {"type": "noul", "instructions": "Is evidence present?"}},
        composition={
            "rules": [{"question": "present", "operator": "gte", "value": 0.8, "result": "ready"}],
            "default": "needs_evidence",
        },
    )
    state = StatePacket(data={"source": "fixture evidence"})
    normalized = normalize(
        {
            "project_id": "fixture",
            "contract_id": contract.id,
            "contract_version": contract.version,
            "answers": {"present": {"type": "noul", "noul": 0.9}},
            "provider": "openrouter",
            "requested_model": "typesafe/jev-1.13",
            "resolved_model": resolved,
            "fallback_used": True,
            "elapsed_ms": 1,
        },
        contract,
        "fixture",
        capabilities={
            "providers": {
                "fallback": {"id": "openrouter", "enabled": True, "model": "typesafe/jev-1.13"}
            }
        },
    )

    class NormalizedProvider:
        name = "mcp"

        def evaluate(self, selected, packet):
            return normalized

    return contract, state, execute(contract, state, NormalizedProvider())


@pytest.mark.parametrize(
    "fault", ["prefix_collision", "unrelated", "empty_service", "alias", "primary"]
)
def test_replay_rejects_ambiguous_mcp_identity_after_alias_support(tmp_path, projection, fault):
    """Accepting a version suffix must not weaken fallback provenance or primary pinning."""
    contract, state, receipt = normalized_mcp_packet()
    if fault == "prefix_collision":
        receipt.resolved_model = "typesafe/jev-1.130-20260917"
    elif fault == "unrelated":
        receipt.resolved_model = "other/model"
    elif fault == "empty_service":
        receipt.provider_metadata["service_provider"] = ""
    elif fault == "alias":
        receipt.requested_model = "jev-latest"
        receipt.resolved_model = "jev-latest-20260917"
    else:
        receipt.provider_metadata["fallback_used"] = False
        receipt.requested_model = contract.model
        receipt.resolved_model = contract.model + "-20260917"
    result, value = invoke("replay", projection, *write_inputs(tmp_path, contract, state, receipt))
    assert result.returncode != 0
    assert value["status"] == "error"
