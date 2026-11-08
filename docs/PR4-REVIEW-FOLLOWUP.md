# PR #4 review follow-up

This qualification follows `017c490044c9945ddbe6c1150be2bdb336657ffd`.
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
- The explicit-file filtering note is a documentation clarification. Directory
  and glob inputs use root-relative exclusions; explicit inputs filter their
  canonical basename. Checking every absolute ancestor would change selection
  of valid files inside hidden checkouts. The existing behavior is retained and
  now has a directory-versus-literal regression. Secure traversal is unchanged.

No command, parameter, contract field, receipt field or dependency was replaced.
The two runtime changes are confined to hook-name validation and Rust's fallback
identity comparison. No provider or installation configuration was changed.

## Documentation and verification

The review reported 22.03% docstring coverage across 59 touched functions. This
follow-up adds 46 useful contract/scenario docstrings in eight Python files,
explaining reservations, replay, ownership, private-input handling and projection
drift. Full ASTs with docstrings removed and all assertion counts match the
runtime-fixed source captured before that documentation pass. The pinned Pipelex
adapter, method, skill and projection remain byte-identical. Passing the remote
coverage threshold requires an exact-head review; it is not inferred here.

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

The original editable checkout and explicit evaluation consumers remain unchanged.
The new source must be built and identified by its own artifact hashes before
activation; the previously prepared `017c490` installation is historical evidence,
not the repaired release. Source/evidence hashes and final-byte controls are in
the separate `/tmp/jev-pr4-review-fixes-20261107/` packet.
