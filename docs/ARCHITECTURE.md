# Architecture

## Goal

`jev-cli` is a clean-room, file-layout-agnostic command-line toolkit for defining, executing, testing, and applying TypeSafe System One / Jev **Decision Contracts**.

```text
input/state
  -> deterministic preparation
  -> DecisionContract
  -> ProviderAdapter
  -> typed answers
  -> CompositionPolicy
  -> DecisionReceipt
```

Optional search and local-model helpers sit beside this spine rather than replacing it.

## Boundaries

The CLI does **not** own global capability discovery, model routing, permissions, execution authority, truth, or verification.

A host may serve this repository's `skill/SKILL.md` through its existing **Skills MCP**. Jev may be exposed through a dedicated **Jev MCP**, while generative models can remain behind a host model core-call or future **Models MCP**.

These are separate integration roles. `jev-cli` does not become another registry or router.

No private MCP endpoint, selected local port, token path, hostname, or installation-specific address belongs in the public project.

## Core types

- `StatePacket`: runtime state plus optional source/reference metadata.
- `DecisionContract`: versioned model alias, questions, composition policy, and consequence policy.
- `ChoiceQuestion`, `NoulQuestion`, `ScoreQuestion`: typed System One primitives.
- `DecisionReceipt`: contract/state digests, provider/model identity, typed answers, usage, latency, and composition result. Raw state is excluded by default.
- `ProviderAdapter`: executes a Decision Contract.
- `CompositionPolicy`: deterministic interpretation of answers.
- `EvidenceFeature`: optional typed annotation from retrieval/extraction helpers.
- `BenchmarkCase`: frozen state + contract + expected observable outcome.

## Provider layer

V0 ships a direct `TypeSafeProvider`. It accepts credentials only through process environment or secret-file resolution.

Providers receive validated internal models and return normalized answers. Provider-specific response shapes should not leak into command behavior.

A later generic `JevMCPProvider` can call any compatible Jev MCP configured by the host, without baking a private address into this repository.

## ModelCallAdapter / ReasonerAdapter

Some workflows benefit from a compact generative model before or after Jev:

```text
messy task
 -> injected ModelCallAdapter proposes bounded state/candidates
 -> deterministic validation
 -> Jev DecisionContract
 -> deterministic composition
```

or:

```text
Jev -> missing_candidate_or_contract
 -> injected ModelCallAdapter repairs/proposes
 -> deterministic validation
 -> Jev retry
```

The adapter is an interface in V0. A host can bridge it to an existing model core-call or a future Models MCP. Vendor-specific reasoners are intentionally not core dependencies.

## Search

Search is split into distinct stages:

1. file discovery;
2. text extraction/chunking;
3. candidate recall;
4. ranking/features;
5. optional Jev judgment;
6. result composition.

Core search provides deterministic lexical candidate recall. Optional BGE and GLiNER adapters may add semantic ranking and typed extraction.

Optional semantic ranking does not silently delete legal candidates. Any top-k/candidate-limit pruning is explicit and visible because recall loss cannot be repaired downstream.

V0 semantic search uses an explicit candidate pool and does not impose one universal confidence threshold.

## Skills MCP relationship

This repository contains only the skill document needed for a Skills MCP to catalog it: `skill/SKILL.md`.

The host Skills MCP owns skill indexing, types/taxonomy, snapshots, and discovery. If a host classifies the skill, natural classes include semantic decision, routing, retrieval, and extraction.

The skill can teach an agent how to build and use Decision Contracts, but the skill document itself does not grant tool execution or mutation authority.

## CLI V0

- `jev init` — scaffold a Decision Contract.
- `jev ask` — execute one ad-hoc Choice/Noul/Score question.
- `jev run` — execute a saved contract against stdin/file/JSON state.
- `jev batch` — execute a saved contract against JSONL states.
- `jev search` — file-layout-agnostic discovery/chunking/recall with optional Jev semantic judgment.
- `jev bench` — run frozen benchmark cases and emit aggregate + per-case receipts.
- `jev cookbook` — list bundled recipes.
- `jev doctor` — validate provider configuration and optional extras without exposing secret values.

`jev graph` and `jev serve` are deferred until the contract/receipt surface is proven stable.

## File-layout agnosticism

Inputs can come from stdin, a file, a directory, globs, JSON/JSONL, or a caller-prepared manifest. No source language or repository layout is assumed.

Discovery, chunking, retrieval, provider evaluation, and formatting remain separate modules.

## Staged implementation

1. schemas + internal models;
2. TypeSafe provider + secret resolver;
3. engine + receipts;
4. `init`, `ask`, `run`, `doctor`;
5. `batch`, deterministic search, semantic-search candidate-pool hook;
6. benchmark harness + cookbook;
7. optional BGE/GLiNER adapters;
8. agent `SKILL.md` for Skills MCP ingestion;
9. Docker/CI/security/publication gate;
10. later Jev MCP adapter and provider-neutral compact-reasoner experiments.
