# Published fixes with the retained local APIs

As of 2026-11-07, this isolated candidate starts at published main
`b4f41da6e5e4c9673644b881b1fad33f162892d9`. It reconciles selected uncommitted
source from `codex/catalog-mcp-execution` at
`55dbf5193465445028245408265cfcbdcc2df5a4`; it is not a wholesale replacement
of that working tree. [Import provenance](API-RECONCILIATION-IMPORT.json)
separates original source hashes, the initial reconciled import and final bytes.
The original checkout and its editable installation remain unchanged.

## Retained surfaces

| Surface | Reconciliation and boundary |
| --- | --- |
| CLI and Python models | Preserve every existing local command, parameter and default; the decision models remain byte-identical. Keep published catalog/MCP validation and safe file traversal, including earlier validation of the import file. |
| Host hooks | Import `HookConfig`, `HookEvent` and `run_hook`, plus `jev hook`, over the existing catalog. Existing reservations, replay rules and host-owned outcome recording remain in place. Hooks return recommendations, without dispatching tools or changing models. |
| Path-first search | Import local filename ranking and `--path-first`/`--path-limit`; retain published refusal when secure traversal is unavailable. Semantic judging remains opt-in. |
| Rust Skills-rs | Preserve the optional projection/replay crate and all pinned adapter, skill, method and projection bytes. It remains a separately built offline executable. |
| Pipelex | Preserve the optional function-only adapter, runtime, method and mock pilot; no direct provider configuration or production service is changed. |
| Monty | Preserve the optional offline snapshot/replay feasibility probe. It is not installed as a general CLI runner. |

The initial imported CLI registered `hook` below its direct-module launch guard.
The guard now runs after all command registrations, so console, package and
`python -m jev_cli.cli` entry points expose the same command.

Independent review also found that first admission on a connection with pending
caller writes could roll those writes back when `BEGIN IMMEDIATE` failed. Both
`run_contract` and the hook's new-admission path now reject before entering that
transaction. They do not commit, roll back or close the caller's pending work.
Hook replay and unmapped events remain read-only. After the caller deliberately
ends its transaction, admission still commits the reservation before inference.
These guards and registration ordering are the only runtime reconciliation
repairs; AST comparisons isolate them from formatting and documentation changes.

Published dependency metadata and `uv.lock` are retained. Rust, Pipelex and Monty
remain optional source integrations rather than new core dependencies. Generic
function-only Pipelex configuration is included; generated traces, historical
probe output, runtime databases, credentials, IDE metadata and private planning
files are excluded. New qualification does not rewrite historical packets.

## Offline qualification

- Frozen Python 3.13.15 core environment: **157 passed**, with **26 optional
  skips** (the missing Pipelex module contributes one collection skip).
- Separate environment with Pipelex 0.64.0 and the built Rust executable:
  **189 passed**, no skips; this includes all 134 unchanged published tests,
  13 hook cases, four path-first cases, five API controls, seven Pipelex cases,
  25 Rust/Python parity cases and one direct catalog ownership case.
- Rust: **13 unit tests**, locked offline build and Clippy with warnings denied.
- Monty 1.0.0: snapshot resumed in fresh worker pools, one mock provider call,
  one retained decision, replayed receipt, separately observed test outcome,
  and no-match without inference.
- Ruff lint and formatting pass; mypy passes over 24 source files. Source and
  wheel builds succeed offline. A separate non-editable wheel installation passes
  23 API, hook, path-search and transaction-ownership cases; its imports resolve
  inside that temporary environment rather than the source checkout.
- The five new API tests fail against published main without the local APIs.
  The direct-module test separately fails against the initial reconciled import
  before registration repair. The same final test bytes pass on this candidate.
- Hook and direct catalog ownership regressions fail before their guards exactly
  because the caller transaction disappears. After repair, writes remain pending;
  replay/unmapped paths still work, and a separate connection observes a committed
  reservation before the provider runs on a subsequent admitted call.
- Full local command/argument/option/default inventory matches the original CLI.
  Type descriptors match except the published `catalog import` contract-file
  validation: it requires an existing file and rejects directories during argument
  parsing. All published test files and model bytes are unchanged.

Swan mapped this exact worktree's Python source (47 files, 1,325 symbols), with
zero stale files and a verified `run_hook` definition and CLI caller. The nested
Rust crate did not produce indexed symbols in that map; its coverage comes from
source review and Cargo/cross-language checks. No trust override was enabled.

These checks use mock providers and temporary state. They establish source and
packaging compatibility, not live provider behavior, deployment or continuous
scheduling. Existing published fixes intentionally continue rejecting malformed
provider receipts and unsafe traversal; preserving the API does not remove those
checks. Missing-file/directory diagnostics for `catalog import` occur earlier than
in the original dirty checkout; the candidate preserves published behavior here.
Optional BGE/GLiNER model execution was not exercised.

## Update route

Review and publish this candidate before changing the installed launcher. The
current editable installation points at the original dirty checkout, so pulling
main or reinstalling there would mix release changes with unrelated local work.
The observed installed entry is that checkout's `.venv/bin/jev`; no `jev` on the
inspected non-login PATH or existing local-bin launcher was found. Use a clean
checkout of the accepted revision and its own environment for the eventual update,
smoke-test the same command inventory, then explicitly redirect each selected
consumer or create a separately identified PATH launcher. A new PATH launcher
does not update callers using the old explicit path or source-run script. Preserve
the prior target (or prior absence of a launcher) for rollback. The ordinary
wheel includes the hook/path-ranking modules; optional integrations remain in
the repository and use their documented separate environments/builds.

The package version remains `0.1.0`; use the source revision and recorded package
hashes to identify this candidate. Only isolated candidate/test environments were
created; no installed consumer or launcher was changed. No provider call,
credential lookup or service deployment is part of this qualification.
