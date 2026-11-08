# Monty and the existing question catalog

Status: optional offline feasibility probe, verified with Monty 1.0.0 on
2026-09-25. No core CLI command, default dependency, provider configuration,
production database, or live agent integration changed.

## The database foundation already exists

`src/jev_cli/catalog.py` owns versioned contracts, typed questions and allowed
answers, recorded decisions, and separately observed outcomes. The CLI already
supports `catalog import`, `find`, `show`, `run`, `decisions`, `observe` and
`outcomes`. The `transitions` table is reserved; it is not a graph executor.

Keep three kinds of information distinct:

- Question definition: wording, input meaning, choices/rubric, version and source.
- Answer occurrence: evidence reference/digest, actual provider, distribution,
  chosen answer and retained receipt.
- Observed outcome: what happened afterward, the verification reference and any
  later correction. A model answer does not create this evidence by itself.

This is a reusable decision library with an execution record, rather than a
lookup table that treats yesterday's answer as true for a new situation.

## Where Monty fits

[Monty](https://pydantic.dev/docs/monty/get-started/) runs short Python programs.
Its [host-function interface](https://pydantic.dev/docs/monty/concepts/host-functions/)
can call existing catalog, retrieval and model adapters. Its
[snapshots](https://pydantic.dev/docs/monty/concepts/snapshots/) preserve interpreter
state at a pending call. Host resources and completed effects remain the host's
responsibility; a snapshot is not an action receipt.

A candidate flow is:

```text
task and source evidence
  -> Decide metadata / candidate ranking, where that vocabulary is qualified
  -> find relevant versioned questions in the existing catalog
  -> Monty executes preparation, branching and host calls
  -> Jev evaluates Choice / Noul / Score through the existing provider adapter
  -> host validates returned IDs and reopens actual sources
  -> decision receipt, separately verified outcome, reviewed reusable lesson
```

Decide and Jev retain their different contracts. An adapter for local Decide
labels must preserve provider identity and task qualification; it must not
relabel classifier scores as Jev Noul or Score semantics. A stronger model can
author or revise a program/question, while a tested version can subsequently
be reused without generating the same glue again.

The prototype's `find_questions` and `answer_question` are host callbacks.
SQLite, Pydantic and `jev-cli` run on the host; the Monty program receives plain
values. Ordinary fixed composition already works without Monty. Monty is useful
when the workflow requires a short programmable sequence or suspended execution;
its adoption should follow that need, not replace every existing function.

## Run the probe

From the repository root:

```bash
uv run --no-project --with-requirements integrations/monty/requirements.txt python integrations/monty/probe.py
```

The isolated environment avoids changing the project's dependency lock. A
temporary catalog is created from `examples/route.yaml` and deleted on exit.
No private paths, credentials, network requests, real model calls or application
effects are part of the probe. The explicit mock answer tests plumbing only.

The probe verifies:

1. Finding the existing stored contract through a host callback.
2. Pausing before the answer callback and dumping the interpreter snapshot.
3. Restoring in a fresh worker pool and retaining a typed decision.
4. Restoring again and letting the existing hook replay the receipt: one mock
   provider invocation, one decision, and no automatically assumed outcome.
5. Recording a separate test-observed outcome through the current catalog API.
6. Returning an explicit no-match result without inference when no question fits.

The probe prints its measured result and source/program hashes to stdout; save
that output with the revision being exercised. Historical generated output is
not shipped as evidence for this reconciled source. The fixture supplies its
expected mock answer explicitly, rather than relying on option order. This does
not alter model or catalog semantics. See [API reconciliation](../../docs/API-RECONCILIATION.md)
for the current source qualification, including the isolated Monty replay check.

## Remaining integration work

This probe does not install Monty as a CLI runner or connect Decide, live Jev,
Caura or Hermes. The next bounded implementation would expose an optional
runner over the current catalog APIs, then test one real read-only retrieval
workflow. Preserve question/program version and fingerprints, exact source
references, provider receipts, unknown paths and host-owned effect verification.
Do not create another question store, model service or memory authority.

Monty's Python support and snapshot compatibility are version-specific; keep
the tested version pinned and qualify changes. Do not claim the project's
runtime latency or production behavior from upstream benchmark numbers.
