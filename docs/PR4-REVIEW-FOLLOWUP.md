# PR #4 review follow-up

The qualified implementation is
[`9c4e07850b22b292170c97be98f8286e0f86945d`](https://github.com/shetautnetjer/jev-cli/commit/9c4e07850b22b292170c97be98f8286e0f86945d),
following `017c490044c9945ddbe6c1150be2bdb336657ffd`.
The prior [reconciliation record](API-RECONCILIATION.md), import hashes and earlier
qualification packets retain the bytes and results exercised at that revision.

## Findings and repairs

- [Versioned fallback replay](https://github.com/shetautnetjer/jev-cli/pull/4#discussion_r4504930958):
  Rust now accepts a resolved fallback model equal to its requested alias or
  beginning with that alias plus `-`, matching Python normalization. It still
  rejects prefix collisions, unrelated labels, empty service identity,
  `jev-latest` as fallback identity and versioned primary-model mismatches.
- [Unknown hook provider](https://github.com/shetautnetjer/jev-cli/pull/4#discussion_r4504930966):
  the CLI rejects unsupported provider names as usage errors before reading
  hook input or opening the catalog. A typo no longer creates a database or
  consumes the event ID as a retained failure. Provider construction remains
  lazy; valid MCP replay still needs no new configuration, while genuine
  initialization failures for selected providers remain durable failures.
- The explicit-file filtering note concerns `--path-first` search only. In that
  mode, exclusions use each discovered file's scan root. A glob-matched directory
  becomes its own root: `data/*` can select `data/credentials`, so a contained
  `report.txt` is checked without the `credentials` parent component and can be
  selected for semantic processing when enabled. Explicit file inputs filter
  their canonical basename. Ordinary search does not apply this basename
  filter and can read an explicitly selected `.env` file. Checking every absolute
  ancestor would change selection of valid files inside hidden checkouts. The
  existing behavior is retained and has a directory-versus-literal regression.
  Secure traversal is unchanged.

No command, parameter, contract field, receipt field or dependency was replaced.
The two runtime changes are confined to hook-name validation and Rust's fallback
identity comparison. No provider or installation configuration was changed.

### Final publication-scanner follow-up

[Review of `904b14f`](https://github.com/shetautnetjer/jev-cli/pull/4#pullrequestreview-5816606313)
found that the publication scanner checked absolute path components. A checkout
beneath `target` or `.venv` could therefore report success after scanning zero
files. The scanner now applies its existing exclusions relative to the repository
root. Internal build/environment trees remain excluded.

The four cases in [the publication regression](../tests/test_publication.py)
run the real scanner as a subprocess in disposable Git repositories. They check
untracked synthetic findings beneath ordinary, `target` and `.venv` ancestors,
plus retained internal exclusions with a nonzero scanned-file count. The prior
scanner fails three cases and passes one; the repaired scanner passes all four.
Run them with `python -m pytest -q tests/test_publication.py` after the development
installation below. The full offline optional suite now passes **203 tests**.
The runtime/package results and hashes below remain pinned to `9c4e078`: this
follow-up changes only the publication script, its tests and documentation.

## Documentation and verification

The review reported 22.03% docstring coverage across 59 touched functions. This
follow-up adds 46 useful contract/scenario docstrings in eight Python files,
explaining reservations, replay, ownership, private-input handling and projection
drift. Full ASTs with docstrings removed and all assertion counts match the
runtime-fixed source captured before that documentation pass. The pinned Pipelex
adapter, method, skill and projection remain byte-identical. The completed
[`9c4e078` review](https://github.com/shetautnetjer/jev-cli/pull/4#pullrequestreview-5816575257)
reports **51.52% coverage across 66 functions**, below its advisory 80% threshold.
This warning remains open; passing tests and the added docstrings do not establish
that the coverage check passed. Executable code and pinned artifacts are not
changed merely to raise that metric.

The final tests reproduce three failures against an isolated copy of `017c490`:
catalog creation from an invalid provider, consumption of an existing event ID,
and rejection of a normalized versioned MCP receipt. The other seven controls
pass there. All ten pass after repair, including the existing path policy and
the five invalid-identity controls.

Final offline qualification: **160 core tests pass**, with **33 optional skips**;
**199 tests pass** with Pipelex and the built Rust binary, with no skips. Rust's
13 unit tests, offline build and Clippy pass. Ruff lint/format and mypy over 24
package source files pass. Monty again restores in fresh pools, reuses one mock
decision and records a separate observed outcome. No live provider was called.

## Public qualification references and reproduction

The checked regressions are available in the exact qualified source:

| Boundary | Public fixture at `9c4e078` | Recorded result |
| --- | --- | --- |
| Invalid provider causes no database creation or event consumption | [Two catalog cases](https://github.com/shetautnetjer/jev-cli/blob/9c4e07850b22b292170c97be98f8286e0f86945d/tests/test_hooks.py#L214) | Both fail on `017c490`; both pass after repair |
| Normalized Python receipt survives Rust replay | [Exact/versioned fallback cases](https://github.com/shetautnetjer/jev-cli/blob/9c4e07850b22b292170c97be98f8286e0f86945d/tests/test_skills_rs.py#L244) | Exact alias passes both revisions; versioned alias passes only after repair |
| Invalid identities remain rejected | [Five negative cases](https://github.com/shetautnetjer/jev-cli/blob/9c4e07850b22b292170c97be98f8286e0f86945d/tests/test_skills_rs.py#L300) | All five pass both revisions |
| Explicit and discovered paths retain distinct selection rules | [Path-first scope case](https://github.com/shetautnetjer/jev-cli/blob/9c4e07850b22b292170c97be98f8286e0f86945d/tests/test_search_path_first.py#L109) | Passes both revisions; filtering behavior is unchanged |

[Exact-head PR CI](https://github.com/shetautnetjer/jev-cli/actions/runs/42445648482)
passed Python 3.11/3.12/3.13 and Docker. Optional integration totals above are local
qualification results, not claims that those cases ran in CI. The recorded local
environments used Python 3.13.15, MCP 1.30.0, Pipelex 0.64.0 and Monty 1.0.0.

Run these from a clean checkout of `9c4e078` with `uv` and Cargo available. They
install test dependencies; they use synthetic fixtures and do not call live model
providers. The dependency installers may need network access on a fresh machine.

```bash
uv sync --locked --extra dev --python 3.13
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src/jev_cli
cargo test --locked --manifest-path rust/skills-rs/Cargo.toml
cargo clippy --locked --manifest-path rust/skills-rs/Cargo.toml --all-targets -- -D warnings
cargo build --locked --manifest-path rust/skills-rs/Cargo.toml

optional_env="$(mktemp -d)"
uv venv --python 3.13 "$optional_env"
uv pip install --python "$optional_env/bin/python" -e '.[dev,mcp]' mcp==1.30.0 \
  -r integrations/pipelex/requirements.txt -r integrations/monty/requirements.txt
SKILLS_RS_BIN="$PWD/rust/skills-rs/target/debug/skills-rs" \
  "$optional_env/bin/python" -m pytest -q
"$optional_env/bin/python" integrations/monty/probe.py
```

Expected totals at the qualified revision are 160 passed / 33 optional skips in
the core environment, 199 passed / zero skips with optional integrations, and 13
Rust unit tests. The Python fixtures that use local stdio MCP servers require an
environment permitting ordinary local IPC. A denied IPC operation is not evidence
that a receipt was delivered or rejected correctly.

To reproduce the negative control without altering the checked-out source, build
the public baseline in a new temporary directory and run the final ten tests
against it. This deliberately exits nonzero: **three failures and seven passes**.

```bash
baseline_root="$(mktemp -d)"
git archive 017c490044c9945ddbe6c1150be2bdb336657ffd | tar -x -C "$baseline_root"
cargo build --locked --manifest-path "$baseline_root/rust/skills-rs/Cargo.toml"
PYTHONPATH="$baseline_root/src" \
SKILLS_RS_BIN="$baseline_root/rust/skills-rs/target/debug/skills-rs" \
  .venv/bin/python -m pytest tests/test_hooks.py tests/test_skills_rs.py \
  tests/test_search_path_first.py -q \
  -k 'invalid_provider_does or normalized_mcp_fallback or ambiguous_mcp_identity or explicit_path_keeps'
```

The same selection with no `PYTHONPATH` override and the current checkout's Rust
binary passes all ten cases. These commands recreate the controls from public
Git source; private logs are not required to inspect their assertions.

The qualification wheel `jev_cli-0.1.0-py3-none-any.whl` had SHA256
`06fbcb50f79214189edd9c3c81cc52a27afc2c130738078a2096e847a4e41500`;
its source archive had SHA256
`715b4af29968145e1ae6d4a0b4c801cad32d2dd7adb2d41e3b576a9ec91571ac`.
These identify the local tested artifacts, not a separately published release;
subsequent documentation/build-metadata changes can produce different archives.
An independent non-editable installation of that wheel passed 26 API/ownership
cases with MCP 1.30.0.

The original editable checkout and explicit evaluation consumers were unchanged
by this qualification. Raw logs, source hashes, AST comparisons and final-byte
controls remain local artifacts in `/tmp/jev-pr4-review-fixes-20261107/`; they are
supplemental to the public source, fixtures, CI result and reproduction procedure
above. The earlier `017c490` installation/qualification packet remains historical.
