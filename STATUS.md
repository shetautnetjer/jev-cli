# Jev CLI continuation

## 2026-11-07 — Bounded MCP adapter qualification

The isolated `codex/jev-mcp-adapter-20261107` branch starts at
`55dbf5193465445028245408265cfcbdcc2df5a4`. Commit `29c5cfc` imports only the
existing MCP/catalog execution candidate; its exact source hashes and the two
section-level extractions are in [MCP-CANDIDATE-IMPORT.json](docs/MCP-CANDIDATE-IMPORT.json).
Hooks, path ranking, Rust, Pipelex, Monty and private runtime files remain outside
this import. The original dirty checkout's thirteen sampled source hashes and
complete Git status match before/after this work.

The adapter accepts the current service's versioned fallback resolution while
retaining the requested alias and resolved model separately. Both primary and
fallback receipts require an enabled negotiated route, matching provider and
requested model; absent/null route metadata cannot bypass those checks. Primary
resolution remains exact. This does not change server fallback policy.

Qualification used Python 3.13.15, MCP 1.30.0 and AnyIO 4.15.1 with synthetic stdio
servers, isolated test homes and mock HTTP transports. The dated-model controls
failed twice before the alias fix; seven missing/disabled/mismatched-route
controls failed before the provenance fix. The final pre-merge suite passed all
67 tests. Ruff lint/format and mypy over 22 source files passed. CI now installs
the MCP extra so those cases run. Delivered-reply witnesses prevent transport
timeouts from satisfying invalid-receipt assertions. A credit-exhaustion fixture
checks that the service's reason, attempt code and usage survive normalization.

Earlier positive stdio failures were reproduced in restricted execution. A
minimal Python/AnyIO diagnostic recorded `EPERM` on asyncio's self-pipe write;
the same two unchanged positive tests passed with authorized local IPC. No
transport workaround was added. Failures, raw protocol bytes and successful
logs are retained under `/tmp/jev-mcp-repair-20261107/` for SUPERAGENT evidence.

Swan indexed this exact worktree (35 Python files, then 825 symbols), was refreshed
after the changes, and resolved the known adapter symbol/callers. Its independent
pyright invocation cannot resolve this worktree's external packages and reports
22 import/symbol errors; that checker is not qualified as clean. The actual
dependency environment's mypy check above passed. No trust override was granted.

No live model calls, service changes, installed defaults or publication are part
of this qualification. Upstream synchronization and checks against the merged
dependency requirements remain the next step before publication.
