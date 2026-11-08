# Jev CLI continuation

## 2026-11-07 — Bound publication exclusions to the checkout

Final review of `904b14f` found that the publication scanner skipped every file
when an absolute checkout ancestor was named `target` or `.venv`. Exclusions now
use paths relative to the repository root, preserving internal build exclusions.
Four real scanner subprocess cases fail three times on the prior source and all
pass after the one-line fix; the full offline optional suite passes 203 tests.
The README and review follow-up clarify that a glob-matched directory becomes
its own scan root. No Jev package, search behavior or dependency changed.
Ruff, formatting and the publication scan pass; the exact Swan map was refreshed
without changing trust. New evidence is in `/tmp/jev-pr4-final-scope-20261107/`;
the earlier runtime qualification and package artifacts remain historical records.

## 2026-11-07 — Clarify final review documentation

Review of `9c4e078` requested an explicit distinction between ordinary search and
the `--path-first` basename filter. The README and review follow-up now state it,
and the follow-up links exact public tests/CI and portable reproduction commands.
Actual remote docstring coverage is 51.52% across 66 functions, below the advisory
80% threshold; it is recorded as a remaining warning. This follow-up changes only
Markdown documentation and preserves all executable source, tests and artifacts.

## 2026-11-07 — Address PR #4 review findings

Following `017c490`, Rust replay now accepts the same versioned fallback labels
as Python, with the existing primary/provenance rejections preserved. Unsupported
hook provider names fail before database creation or event admission. Explicit
file-selection semantics are clarified without changing path filtering.
The [review follow-up](docs/PR4-REVIEW-FOLLOWUP.md) links the findings and records
the compatibility limits. Earlier import/qualification manifests remain unchanged.

Final-byte controls fail three times against `017c490`, then all ten pass after
repair. The complete suite passes 160 core cases (33 optional skips), or 199 with
optional integrations (zero skips). Rust's 13 tests, build/Clippy, Monty replay,
Ruff, formatting and mypy pass. Forty-six concise contract/scenario docstrings
preserve all eight executable ASTs and assertion counts; pinned projection inputs
are unchanged. Remote docstring coverage remains to be verified after publication.
New evidence is in `/tmp/jev-pr4-review-fixes-20261107/`; no installed consumer,
original dirty checkout or live provider was changed by this follow-up.

## 2026-11-07 — Reconcile published fixes with local CLI capabilities

This isolated candidate starts at published main `b4f41da` and imports the local
hook/path-first APIs plus optional Rust, Pipelex and Monty source from the dirty
`55dbf51` checkout. All 32 selected original source hashes, original HEAD and Git
status remain unchanged. No installed launcher or service was changed. The
[reconciliation record](docs/API-RECONCILIATION.md) explains source provenance,
compatibility boundaries and the clean-checkout update route; its linked manifest
distinguishes raw source, initial merge and final repairs.

The direct-module launch guard now follows hook registration. Hook and direct
catalog admission also reject pending caller transactions before entering their
own transaction, fixing an independently reproduced caller-work rollback. Replay
and unmapped hooks remain read-only. Four new ownership cases demonstrate
preserved writes and durable reservation before provider evaluation. Five final-byte
API controls fail on published main without the local APIs; the module-entry
control also fails on the initial import before this repair. The core environment
passes 157 tests with 26 optional skips; a separate environment exercises all
189 tests, including Rust/Pipelex, without skips. All 134 published cases remain
unchanged. Rust's 13 unit tests, offline build/Clippy, Monty fresh-pool replay,
Ruff, mypy and package builds pass. The complete CLI parameter inventory matches
the original except the retained published import-file prevalidation; malformed
path diagnostics occur earlier. Decision models and the path-ranking AST are
unchanged; separate full-AST comparisons isolate the two admission guards and
their documentation. The publication scan passes.

Swan's exact candidate map has 47 files and 1,325 symbols with no stale Python
files and a verified hook/CLI caller. Nested Rust symbols are not covered by that
map; Cargo and parity tests provide their qualification. Raw evidence and failure
controls are in `/tmp/jev-api-reconcile-20261107/`. This is offline source and
packaging qualification, pending review/publication and an explicit installation
step; no live provider or optional BGE/GLiNER execution was performed.

## 2026-11-07 — Explain reviewed test boundaries

After `9fc3d78`, review reported 70.15% docstring coverage; all touched production
functions were already documented. Twelve concise scenario/helper docstrings now
explain SQLite closure and path races, failed-run retry prevention, invalid response
batches and symlink anchoring. This follow-up changes four test files and this note;
no production code, assertions, inputs or historical evidence were changed.
The four full ASTs match `9fc3d78` after removing docstrings, with all 195 assertions
and 58 test functions unchanged. All 134 tests, Ruff checks/format and mypy pass;
independent review is clear. Exact Swan map: 35 files, 1,008 symbols, zero stale/new
files. Evidence is in `/tmp/jev-pr3-test-contract-docs-20261107/`; remote coverage
must be checked after publication rather than inferred from these local checks.

## 2026-11-07 — Close remaining catalog read connections

The final PR summary review identified three read commands that used SQLite's
transaction context manager without closing its connection. `catalog list`,
`show` and `outcomes` now explicitly close their owned handles after success or
failure. Existing returned data, errors and transaction behavior remain intact.
Seven real-SQLite controls cover all three success paths, denied SELECTs and the
missing-contract diagnostic: the final test bytes fail seven times against
`0b694404789b67aa483b53c09f103fdb4464f3b7`, then pass with the repair.

Twenty-one concise docstrings explain changed production contracts and ownership;
no test docstrings or historical qualification fixtures were rewritten. Stripping
docstrings from the seven production files produces identical ASTs before/after
that documentation pass, separate from the three connection fixes. This is local
documentation evidence, not a claim that CodeRabbit's coverage warning passed.

The final suite passes 134 tests with native local IPC for synthetic MCP servers;
Ruff checks, formatting of 61 files and mypy over 22 source files pass. Independent
review found no material issue. Swan refreshed the exact publication worktree:
35 Python files, 1,008 symbols, zero stale/new files and verified `catalog_list`.
Evidence is retained under `/tmp/jev-pr3-close-handles-20261107/` for SUPERAGENT
publication. No live model call, installed client or service change occurred.

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
