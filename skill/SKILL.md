---
name: jev-decision-contracts
description: Build and evaluate bounded TypeSafe System One / Jev Decision Contracts; use Choice for exclusive alternatives, Noul for one proposition, Score for an ordered rubric, and preserve explicit unknown/no-match when candidate coverage is incomplete.
---

# Jev Decision Contracts

Use this skill when a workflow needs fast typed semantic judgment rather than open-ended generation.

## Before calling Jev

1. Separate exact facts from semantic judgment. Keep IDs, arithmetic, hashes, permissions, known lifecycle/freshness, and structural invariants in deterministic code.
2. Identify the one decision meaning.
3. Protect the legal candidate set. Add `unknown_no_match`, `other`, or `none` when coverage may be incomplete.
4. Choose the primitive:
   - Choice: one mutually exclusive represented option.
   - Noul: one independently meaningful yes/no proposition.
   - Score: one ordered rubric with concrete levels.
5. If several questions use the same unchanged state and are independently answerable, send them together.

## CLI workflow

- Start from `jev init contract.yaml`.
- Validate behavior offline with `--provider mock` when possible.
- Run real state with `jev run contract.yaml --state-file state.json`.
- Use `jev batch` for JSONL states.
- Use `jev search` for file discovery/chunking/ranking. Semantic judging requires an explicit `--semantic-limit`; treat that limit as a recall/cost decision.
- Use `jev bench` for frozen evaluation cases.

Never pass credentials in argv. Configure `TYPESAFE_API_KEY` or `TYPESAFE_API_KEY_FILE`.

## Failure handling

If the true option may be missing, do not force a relative winner. Escalate to candidate/contract repair.

Probability is not verification or permission. Keep deterministic composition and action policy outside the model.

BGE/GLiNER are optional evidence helpers. They may rank or annotate candidates; do not let them silently delete legal semantic possibilities without a separately evaluated pruning contract.
