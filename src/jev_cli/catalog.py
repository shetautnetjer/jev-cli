from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from jev_cli.engine import execute, sha256_json
from jev_cli.models import DecisionContract, DecisionReceipt, StatePacket
from jev_cli.providers.base import ProviderAdapter

DDL = """
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
CREATE TABLE IF NOT EXISTS contracts (
    contract_id TEXT NOT NULL,
    version TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    scope TEXT NOT NULL,
    source_ref TEXT,
    status TEXT NOT NULL,
    contract_json TEXT NOT NULL,
    PRIMARY KEY (contract_id, version)
);
CREATE TABLE IF NOT EXISTS questions (
    contract_id TEXT NOT NULL,
    version TEXT NOT NULL,
    question_id TEXT NOT NULL,
    primitive TEXT NOT NULL CHECK (primitive IN ('choice','noul','score')),
    wording TEXT NOT NULL,
    criteria_json TEXT NOT NULL,
    state_schema_json TEXT NOT NULL DEFAULT '{}',
    consequence_class TEXT NOT NULL DEFAULT 'unspecified',
    PRIMARY KEY (contract_id, version, question_id),
    FOREIGN KEY (contract_id, version) REFERENCES contracts(contract_id, version)
);
CREATE TABLE IF NOT EXISTS transitions (
    contract_id TEXT NOT NULL,
    version TEXT NOT NULL,
    question_id TEXT NOT NULL,
    answer_key TEXT NOT NULL,
    next_operator TEXT NOT NULL,
    predicate_ref TEXT,
    PRIMARY KEY (contract_id, version, question_id, answer_key),
    FOREIGN KEY (contract_id, version, question_id)
        REFERENCES questions(contract_id, version, question_id)
);
CREATE TABLE IF NOT EXISTS outcomes (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    version TEXT NOT NULL,
    question_id TEXT NOT NULL,
    answer_json TEXT NOT NULL,
    state_digest TEXT NOT NULL,
    provider_receipt_ref TEXT,
    effect_receipt_ref TEXT,
    observed_result TEXT NOT NULL CHECK (
        observed_result IN ('success','failure','unresolved','superseded')
    ),
    correction_ref TEXT,
    PRIMARY KEY (run_id, step_id, question_id),
    FOREIGN KEY (contract_id, version, question_id)
        REFERENCES questions(contract_id, version, question_id)
);
CREATE TABLE IF NOT EXISTS decisions (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    version TEXT NOT NULL,
    state_digest TEXT NOT NULL,
    state_reference TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending','completed','failed')),
    receipt_json TEXT,
    error_code TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at TEXT,
    PRIMARY KEY (run_id, step_id),
    FOREIGN KEY (contract_id, version) REFERENCES contracts(contract_id, version)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(DDL)
    return db


def import_contract(
    db: sqlite3.Connection,
    contract: DecisionContract,
    *,
    scope: str = "general",
    source_ref: str | None = None,
) -> str:
    raw = contract.model_dump(mode="json", exclude_none=True)
    digest = sha256_json(raw)
    existing = db.execute(
        "SELECT fingerprint FROM contracts WHERE contract_id=? AND version=?",
        (contract.id, contract.version),
    ).fetchone()
    if existing:
        if existing["fingerprint"] != digest:
            raise ValueError(
                "Contract version already exists with different content; increment its version"
            )
        return digest
    with db:
        db.execute(
            "INSERT INTO contracts VALUES (?,?,?,?,?,?,?)",
            (
                contract.id,
                contract.version,
                digest,
                scope,
                source_ref,
                "active",
                json.dumps(raw, sort_keys=True),
            ),
        )
        for qid, question in contract.questions.items():
            q = question.model_dump(mode="json", exclude_none=True)
            db.execute(
                "INSERT INTO questions (contract_id,version,question_id,primitive,"
                "wording,criteria_json) VALUES (?,?,?,?,?,?)",
                (
                    contract.id,
                    contract.version,
                    qid,
                    q["type"],
                    json.dumps(q["instructions"]),
                    json.dumps(q.get("criteria")),
                ),
            )
    return digest


def list_contracts(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in db.execute(
            "SELECT contract_id, version, fingerprint, scope, source_ref, status "
            "FROM contracts ORDER BY contract_id, version"
        )
    ]


def get_contract(db: sqlite3.Connection, contract_id: str, version: str) -> DecisionContract:
    row = db.execute(
        "SELECT contract_json FROM contracts WHERE contract_id=? AND version=?",
        (contract_id, version),
    ).fetchone()
    if row is None:
        raise ValueError("Unknown contract ID/version")
    return DecisionContract.model_validate_json(row["contract_json"])


def record_outcome(
    db: sqlite3.Connection,
    receipt: DecisionReceipt,
    *,
    run_id: str,
    step_id: str,
    observed_result: str,
    provider_receipt_ref: str | None = None,
    effect_receipt_ref: str | None = None,
) -> None:
    if observed_result not in {"success", "failure", "unresolved", "superseded"}:
        raise ValueError("Invalid observed result")
    with db:
        # Reserve the writer before admission reads; a competing run must not
        # appear between the decision check and this outcome batch's insertion.
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT fingerprint FROM contracts WHERE contract_id=? AND version=?",
            (receipt.contract_id, receipt.contract_version),
        ).fetchone()
        if row is None or row["fingerprint"] != receipt.contract_sha256:
            raise ValueError("Receipt does not match an imported contract fingerprint")
        decision = db.execute(
            "SELECT status,receipt_json FROM decisions WHERE run_id=? AND step_id=?",
            (run_id, step_id),
        ).fetchone()
        if decision is not None:
            if decision["status"] != "completed" or (
                DecisionReceipt.model_validate_json(decision["receipt_json"]) != receipt
            ):
                raise ValueError(
                    "Outcome receipt does not match the retained decision for this run/step"
                )
        for qid, answer in receipt.answers.items():
            db.execute(
                "INSERT INTO outcomes (run_id,step_id,contract_id,version,question_id,"
                "answer_json,state_digest,provider_receipt_ref,effect_receipt_ref,"
                "observed_result) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    step_id,
                    receipt.contract_id,
                    receipt.contract_version,
                    qid,
                    answer.model_dump_json(),
                    receipt.state_sha256,
                    provider_receipt_ref,
                    effect_receipt_ref,
                    observed_result,
                ),
            )


def list_outcomes(db: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in db.execute(
            "SELECT * FROM outcomes WHERE run_id=? ORDER BY step_id, question_id", (run_id,)
        )
    ]


def run_contract(
    db: sqlite3.Connection,
    contract_id: str,
    version: str,
    state: StatePacket,
    provider: ProviderAdapter,
    *,
    run_id: str,
    step_id: str,
) -> DecisionReceipt:
    """Reserve a step before inference; retain its answer without claiming an effect."""
    if not run_id.strip() or not step_id.strip():
        raise ValueError("Run and step IDs must not be empty")
    contract = get_contract(db, contract_id, version)
    try:
        with db:
            # The outcomes guard and reservation share one write transaction.
            # Commit it before executing the provider below.
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM outcomes WHERE run_id=? AND step_id=?", (run_id, step_id)
            ).fetchone():
                raise ValueError("Run/step already exists in outcomes; use a new step ID")
            db.execute(
                "INSERT INTO decisions (run_id,step_id,contract_id,version,state_digest,"
                "state_reference,status) VALUES (?,?,?,?,?,?,'pending')",
                (run_id, step_id, contract_id, version, sha256_json(state.data), state.reference),
            )
    except sqlite3.IntegrityError:
        raise ValueError("Run/step already exists; inspect it before creating a new step") from None
    try:
        receipt = execute(contract, state, provider)
        with db:
            db.execute(
                "UPDATE decisions SET status='completed',receipt_json=?,"
                "completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE run_id=? AND step_id=?",
                (receipt.model_dump_json(exclude_none=True), run_id, step_id),
            )
    except Exception:
        # Never retain exception text: transports may include private input or credentials.
        with db:
            db.execute(
                "UPDATE decisions SET status='failed',error_code='evaluation_failed',"
                "completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE run_id=? AND step_id=?",
                (run_id, step_id),
            )
        raise
    return receipt


def list_decisions(db: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    result = []
    for row in db.execute(
        "SELECT * FROM decisions WHERE run_id=? ORDER BY created_at,step_id", (run_id,)
    ):
        item = dict(row)
        raw = item.pop("receipt_json")
        item["receipt"] = json.loads(raw) if raw else None
        result.append(item)
    return result


def observe_decision(
    db: sqlite3.Connection,
    run_id: str,
    step_id: str,
    *,
    observed_result: str,
    effect_receipt_ref: str | None = None,
) -> None:
    row = db.execute(
        "SELECT status,receipt_json FROM decisions WHERE run_id=? AND step_id=?", (run_id, step_id)
    ).fetchone()
    if row is None or row["status"] != "completed":
        raise ValueError("No completed decision for this run/step")
    if observed_result in {"success", "failure"} and not (effect_receipt_ref or "").strip():
        raise ValueError("Success/failure observations require an --effect-ref")
    try:
        record_outcome(
            db,
            DecisionReceipt.model_validate_json(row["receipt_json"]),
            run_id=run_id,
            step_id=step_id,
            observed_result=observed_result,
            provider_receipt_ref=f"catalog:decisions/{run_id}/{step_id}",
            effect_receipt_ref=effect_receipt_ref,
        )
    except sqlite3.IntegrityError:
        raise ValueError(
            "Outcome already recorded; existing evidence was not overwritten"
        ) from None


def find_contracts(
    db: sqlite3.Connection,
    text: str,
    *,
    scope: str | None = None,
) -> list[dict[str, Any]]:
    """Literal, case-insensitive discovery with no implicit top-k pruning."""
    if not text.strip():
        raise ValueError("Search text must not be empty")
    # contract_json is stored as escaped JSON (non-ASCII as \uXXXX, quotes and
    # newlines backslash-escaped), so a raw substring test cannot match literal
    # user text. Compare against the decoded strings instead; stored rows and
    # fingerprints are untouched, which also covers rows written by earlier releases.
    db.create_function("jev_contract_contains", 2, _contract_contains, deterministic=True)
    return [
        dict(row)
        for row in db.execute(
            "SELECT contract_id,version,fingerprint,scope,source_ref,status FROM contracts "
            "WHERE (? IS NULL OR scope=?) AND jev_contract_contains(contract_json, ?) "
            "ORDER BY contract_id,version",
            (scope, scope, text),
        )
    ]


def _json_strings(node: Any) -> Iterator[str]:
    """Yield every decoded key, string and scalar rendering in a JSON value."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from _json_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _json_strings(value)
    elif isinstance(node, str):
        yield node
    elif node is not None:
        yield json.dumps(node)


def _contract_contains(contract_json: str | None, text: str | None) -> int:
    if not contract_json or not text:
        return 0
    try:
        decoded = json.loads(contract_json)
    except ValueError:
        return 0
    needle = text.casefold()
    return int(any(needle in value.casefold() for value in _json_strings(decoded)))
