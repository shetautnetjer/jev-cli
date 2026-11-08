# Skills-rs: qualified skill-flow projection

This local Rust projector works with the existing Skills MCP catalog. It does
not replace the server, create a memory store, or dispatch agent actions.

Version 0.1 supports the qualified `integrations/pipelex` decision method:
a typed input, one Jev evaluation, deterministic composition and a conditional
return. It projects that supported behavior into a versioned JSON artifact for
the Rust replay runtime. It does not translate arbitrary Python or compile all
of Pipelex; unsupported operators, expressions, adapters and references fail.

## Build and use

From the repository root:

```sh
cargo build --release --locked --manifest-path rust/skills-rs/Cargo.toml
rust/skills-rs/target/release/skills-rs project integrations/pipelex --out projection.json
rust/skills-rs/target/release/skills-rs verify projection.json integrations/pipelex
rust/skills-rs/target/release/skills-rs replay projection.json contract.json state.json receipt.json \
  --skill-dir integrations/pipelex
```

`project` always prints the artifact as JSON. `--out` publishes a new file without
overwriting an existing destination. Source files and the artifact carry SHA-256
digests; `verify` reprojects source and checks equality. A content hash detects
drift; the host/catalog's source approval establishes trust.

`contract.json` is the existing DecisionContract in JSON form, `state.json` is
the original state data, and `receipt.json` is a retained `jev-cli/receipt-v1`.
Use `python -m jev_cli run` or the existing catalog to obtain receipts; replay
never calls a model. A Pipelex wrapper's nested `receipt` must be extracted first.

Replay checks the contract, state digest and complete typed answers, recomputes
composition, and follows the projected branch. It returns the original receipt
inside an explicitly marked replay result with `inference_attempted=false` and
`authority_granted=false`. Without `--skill-dir`, artifact integrity is checked
but current source is not reopened; `source_verified` is false.
Here "source" means the skill definition files, not the external evidence behind
the judgment. Receipt hashes establish internal consistency, not authenticated
provider origin or factual correctness. Its source locator is preserved but not
dereferenced. MCP replay requires explicit fallback metadata; it cannot recreate
the negotiated capability snapshot absent from a normalized receipt.

## Artifact contract

These are portable Jev CLI contracts, not new host registry identities:

| Field | Meaning |
| --- | --- |
| `schema_version` | `jev-cli/skill-projection-v1` for projection; `jev-cli/skill-replay-v1` for replay. |
| `projector_version` | Version of the bounded projection implementation. |
| `source_files` | Exact guide, method and adapter filenames mapped to SHA-256. |
| `domain`, `entrypoint` | Validated names from the method, not executable paths. |
| `branches`, `default_handler` | Only the qualified registered return handlers. |
| `artifact_sha256` | Canonical projection digest excluding this digest field itself. |

Replay adds the selected handler, original receipt and disposition, and explicit
no-inference/no-authority markers. JSON inputs reject duplicate object keys.
Canonical numbers are restricted to finite binary64 floats and signed/unsigned
64-bit integers; larger integer literals are rejected rather than rounded.

## Supported source and compatibility

The projector accepts the current typed wrappers `DecisionInput` and
`DecisionOutput`, a two-step sequence, the fixed disposition expression, and the
four qualified `jev_*` functions. The Python adapter implementation is pinned
by content hash because function names alone cannot establish their behavior.
Changing that adapter requires a new qualification and projector release.

Original `.mthds` and question contracts remain the authoring sources. Keep
candidate selection separate from projection: Jev proposes among eligible
skills; the host verifies the selected skill version and chooses a qualified
implementation. Repetition, new evidence, provider calls and effects remain
host-owned; this first projector does not implement adaptive loops.

The existing Skills MCP can serve linked `.mthds` and JSON artifacts with their
source snapshots. Link an approved projection from its skill guide after
qualification. No execute tool or catalog server replacement is required.

## Verification

```sh
cargo test --locked --manifest-path rust/skills-rs/Cargo.toml
cargo clippy --manifest-path rust/skills-rs/Cargo.toml --all-targets -- -D warnings
SKILLS_RS_BIN="$PWD/rust/skills-rs/target/release/skills-rs" \
  .venv/bin/python -m pytest tests/test_skills_rs.py -q
```

The Python tests compare existing model/receipt behavior across languages and
exercise Unicode, number canonicalization, source/receipt tampering, unsupported
operators and refusal to overwrite. These are replay/contract tests; they do not
prove inference accuracy, skill selection quality, live MCP deployment or agent
effects. Benchmark local overhead separately from remote inference and token use.
