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

## 2026-11-07 — Synchronize current upstream before publication

The repaired source is recorded separately in `3ab93d5`. The subsequent merge
includes `origin/main` at `a65826a`, including its pytest 9.0.3 update. Conflicts
in search discovery, its tests and security documentation retain the existing
local `97d4548` behavior: ancestor/glob no-follow checks, FIFO handling and the
associated controls. No MCP changes were mixed into those search resolutions.
The merged lock retains the MCP extra; pytest is its sole package-version change.

An isolated worktree `.venv` was created from the frozen lock. The offline attempt
correctly refused the uncached pytest wheel; the subsequent locked dependency
fetch populated only that test environment. The original environment and dirty
source remained unchanged. With Python 3.13.15 / pytest 9.0.3 / MCP 1.30.0 /
AnyIO 4.15.1, all 67 tests passed again, along with Ruff lint/format and mypy over
22 source files. The prior pre-merge and restricted failures remain separate
evidence; they were not overwritten by these successful runs.

Swan clean-rebuilt the exact worktree after the dependency change: 35 Python
files, 825 symbols and zero stale/new files. Known-symbol lookup passed. Its
separate pyright adapter still has the dependency-resolution limitation described
above (22 errors); this does not replace the qualified environment's mypy result.
SUPERAGENT will retain the compact qualification packet and handle remote review,
publication and merge. No runtime adoption or live provider result is claimed.

## 2026-11-07 — Serialize catalog admission before publication

A review of the complete proposed delta found a two-writer race in the imported
catalog: outcome admission and run reservation read their guards before SQLite
started a write transaction. An isolated two-connection probe at `eb129d8`
stored a completed decision and a conflicting outcome under the same run/step
with different state digests. The failed witness remains separate evidence.

Both paths now acquire `BEGIN IMMEDIATE` before their admission reads and commit
their corresponding batch/reservation atomically. The reservation commits before
provider work. Two real-connection interleaving controls failed before the fix
and pass afterward; a late duplicate-question control confirms the complete
outcome batch rolls back while preserving prior committed rows. No SQL schema,
store, provider policy or background process changed.

The full offline suite passes 70 tests in the locked pytest 9.0.3 environment.
Ruff and mypy checks passed for the change; independent source review found no
remaining material issue in these transaction boundaries. Earlier 67-test
qualification remains frozen. The added probe and red/green evidence are under
`/tmp/jev-catalog-review-20261107/` and the `catalog-*` runs in
`/tmp/jev-mcp-repair-20261107/` for a separate SUPERAGENT follow-up packet.

## 2026-11-07 — Publication branch with unchanged CI workflow

`codex/jev-mcp-catalog-20261107` starts from upstream `a65826a`. It carries the
qualified delta from `07f7f41` with byte-identical runtime and tests, while leaving
the upstream CI workflow unchanged. MCP is now also a development dependency,
so the existing `uv sync --extra dev` installs the SDK required by the stdio tests.
The separate optional MCP extra remains available. Original import `29c5cfc`,
adapter repair `3ab93d5`, upstream merge `eb129d8` and catalog fix `07f7f41` remain
preserved on the original repair branch; the import provenance manifest remains
unchanged in this publication branch.

Offline lock regeneration initially selected pytest 9.1.1. That transient run
is retained separately, then the qualified pytest 9.0.3 version was restored
using an explicit resolver pin. A semantic comparison confirms every locked
package/version is unchanged from `07f7f41`; only MCP's development-extra
membership changes. The installed uv writer emits lock format revision 3 instead
of 5. The final `uv sync --offline --locked --extra dev` succeeds without changing
the lock. This affected only the private test environment, not installed defaults.

All 70 tests pass in the final dev-only pytest 9.0.3 environment; Ruff lint/format
and mypy over 22 source files pass. Hash comparisons enforce runtime/test equality
with the qualified repair and exact workflow equality with upstream. Swan indexed
the publication worktree separately (35 Python files, 855 symbols, zero stale
files), without a trust override. Remote publication/review and service adoption
remain distinct; this branch does not claim any live Jev call or runtime cutover.

## 2026-11-07 — Merge the reviewed dependency security update

Dependabot PR #2 at `980455e2` changes only the locked certifi, filelock and
setuptools versions and their distribution metadata. Its normal upstream merge
`abbdb2e` is incorporated by `4f1f275`. The candidate now locks certifi
2026.10.18, filelock 4.2.1 and setuptools 84.1.0, matching the reviewed GitHub
advisory fixes. A parsed comparison proves no other package version changed;
pytest remains 9.0.3 and MCP's development-extra membership is preserved.
Runtime, tests and the CI workflow remain byte-identical to `e60a6c9`.

A dev-only locked sync changed only installed certifi and left the lock bytes
unchanged. All 70 offline tests passed again with Python 3.13.15; Ruff lint/format
and mypy over 22 source files passed. Optional retrieval/extraction dependencies
filelock and setuptools were not installed or executed, so their updated lock
entries do not establish model-backed retrieval qualification. No live provider
calls or default environment changes were made.

Swan clean-rebuilt the exact publication worktree (35 Python files, 855 symbols)
and resolved the known catalog symbol. The independent pyright limitation above
remains. The separate follow-up evidence is under
`/tmp/jev-dependency-review-20261107/`; earlier qualification packets remain
unchanged. Remote review and merge are handled separately by SUPERAGENT.

## 2026-11-07 — Resolve PR #3 review findings

Native Sonnet under the existing Claude Max login repaired four verified review
findings in an isolated worktree. Catalog discovery now searches decoded literal
text (including already escaped Unicode rows) without changing fingerprints or
stored bytes. Receipt recording reports malformed input and constraint failures
without quoting receipt contents and closes its connection. Directory/glob search
reports unavailable no-follow primitives; separate lexical/canonical glob roots
preserve ../ and symlinked prefixes while rejecting internal aliases.

Independent review additionally reproduced a real post-connect SQLite write
refusal. A fixed diagnostic now handles remaining database errors without
claiming an uncertain write did not commit. Known constraint messages use native
SQLite error names. Red-first tests cover each repair, including a query-only
SQLite connection. All 102 offline tests, Ruff lint/format and mypy pass in the
locked development environment with native local IPC. Platform-absence tests
are simulated on Linux; Windows and real disk-corruption recovery are unqualified.

The native worker completed 52 of 80 turns; its receipt verifies first-party
claude.ai Max authentication with no API/provider override. Parent verification
and the SQLite follow-up remain distinct from the original worker result.
SUPERAGENT retains native receipts, frozen red/green evidence, source hashes and
independent review. No live Jev provider, runtime defaults or original dirty
checkout changed. The current Swan map was refreshed for the isolated review
worktree; publication-map refresh follows integration.

## 2026-11-07 — Serialize concurrent imports and report writer contention

PR #3's next review at `1b82ed2` found import identity lookup outside its write
reservation and uncaught database contention in the run/observe commands.
Fresh imports now acquire `BEGIN IMMEDIATE` before fingerprint lookup and retain
the entire contract/question batch in that transaction. Two real SQLite
connections prove identical and conflicting import attempts cannot interleave
between lookup and insert; subsequent identical imports remain idempotent and
different content retains the version-mismatch error.

Active caller transactions now use an import-local savepoint and a no-row write
before lookup to acquire the writer. This deliberately improves the former
conditional behavior: an already-imported contract returned before `with db`,
but a new import committed the caller's pending transaction. Imports now leave
active caller transactions under caller control. A stale WAL read snapshot
fails with SQLite's native error without ending that transaction. A late batch
failure rolls back only the import unless SQLite itself aborts the entire
transaction; that native abort/error remains visible rather than being masked
by savepoint cleanup.

Run, observe and import CLI commands report fixed database diagnostics without
SQLite/receipt contents and close acquired connections. The contention tests use
two actual connections and a 1 ms busy timeout; no provider evaluation occurs,
and the run command still closes its provider. They preserve existing decisions
and outcomes and do not claim uncertain failures are safe to retry blindly.

The final offline suite passes 114 tests with native local IPC. Ruff lint/format
and mypy over 22 source files pass. The separate evidence packet at
`/tmp/jev-pr3-round2-20261107/` retains the base interleaving failures, follow-up
savepoint cleanup failure, successful checks and source hashes. The exact
publication Swan map is refreshed: 35 files, 971 symbols, zero stale/new files,
with `_import_transaction` resolving to the current source. No schema, provider
policy, permission default, service or live catalog changed. Original Sonnet
qualification remains frozen; coordinating review and publication are recorded
by SUPERAGENT.

## 2026-11-07 — Validate catalog import files before opening the store

PR #3's review at `c8a8412` identified uncaught missing/unreadable import files.
The import argument now requires an existing readable file, and its separate
load boundary handles post-validation disappearance/read refusal. Invalid
UTF-8, JSON, YAML, mapping/schema input and parser-depth errors produce fixed
diagnostics without quoting contract contents. A bounded nested-YAML fixture
reproduced the additional raw RecursionError before that final guard was added.
No catalog is opened or created until the contract successfully loads. Existing
backend version-mismatch errors remain actionable, and success/mismatch still
close their acquired connections. Other CLI commands and parsers are unchanged.

All 127 offline tests pass with native local IPC, including 13 new import-input
controls. Ruff lint/format, mypy over 22 source files and diff checks pass.
Separate red/green evidence and final source hashes are retained at
`/tmp/jev-pr3-file-input-20261107/`; earlier packets remain frozen. The exact
publication Swan map is refreshed and resolves `catalog_import` at the current
source. No live provider, service, default setting or existing catalog changed.
Coordinating review and publication are recorded by SUPERAGENT.
