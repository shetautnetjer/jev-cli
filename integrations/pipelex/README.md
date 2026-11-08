# Jev methods through Pipelex

An optional, executable typed-method pilot. `decision.mthds` runs a Jev
DecisionContract and branches on its caller-defined composition. It preserves
the existing DecisionReceipt, including probabilities, model, source hash and
usage. The result is advisory: `ready` does not authorize an action or prove
that the task succeeded.

## Run

Use a separate environment so the normal CLI remains small:

```sh
uv venv /tmp/jev-pipelex-venv
uv pip install --python /tmp/jev-pipelex-venv/bin/python -e '.[mcp]' -r integrations/pipelex/requirements.txt
/tmp/jev-pipelex-venv/bin/python integrations/pipelex/run_pilot.py \
  --contract integrations/pipelex/contract.yaml \
  --state-file integrations/pipelex/state.json \
  --reference fixture:source-review --provider mock
```

Mock is the default. Select `--provider typesafe` for the existing direct
credential route or `--provider mcp --mcp-config /path/to/mcp.json` for an existing
Jev service. Credentials never appear in method files or command arguments.
The service's request limit is deployment-specific. Check `jev_capabilities`
before use; this source reconciliation does not deploy or reconfigure a service.

Stdout is one JSON result; failures expose only an error class. The runner does not record
raw evidence in the catalog, dispatch actions, retry uncertain calls, or ingest
anything into memory. Use the existing catalog/hook surfaces for durable
run/step reservations and independently observed outcomes.

The contract must compose its answers to a string. This example recognizes
`ready` and `needs_evidence`; other strings take the `unknown_no_match` branch.
The original composition remains in the receipt. Each application supplies its
own evaluated criteria and consequences; there is no universal confidence cutoff.

## Qualified Rust projection

The repository's `rust/skills-rs` crate provides a bounded native projector and
offline receipt replay. From the repository root, build it with

```sh
cargo build --release --locked --manifest-path rust/skills-rs/Cargo.toml
```

Then verify the [checked projection](projection.json):

```sh
rust/skills-rs/target/release/skills-rs verify integrations/pipelex/projection.json integrations/pipelex
rust/skills-rs/target/release/skills-rs replay integrations/pipelex/projection.json contract.json state.json receipt.json --skill-dir integrations/pipelex
```

The three JSON inputs are the exact contract, original state data and retained
DecisionReceipt (extract the nested receipt from a pilot result first). No new
provider call occurs. This first projection supports this method's sequence,
typed Jev adapter and disposition branch only; it is not a general Pipelex
compiler. The existing catalog stays the discovery owner. Source verification
checks the skill definition bytes, not the truth of the evidence in a receipt.
Reproject changed supported sources into a new artifact and review the diff
before catalog intake; changing the adapter requires renewed qualification.

## Typed integration

`jev_method.py` wraps the existing models:

- `DecisionInput`: `DecisionContract` plus `StatePacket`.
- `DecisionOutput`: the unchanged `DecisionReceipt` plus routing disposition.
- `bind_provider(provider)`: caller-owned provider binding, isolated per context
  and inherited by Pipelex worker threads. Method input cannot select credentials
  or a provider endpoint.
- `register_pipelex()`: register the explicit adapter classes/functions after
  the host boots Pipelex.

`function_only_runtime.py` uses Pipelex's public model-manager injection seam.
This pilot enables only registered Python functions, using the host-bound Jev
provider; it deliberately has no Pipelex-managed LLM backend. Ordinary Pipelex
applications can register the adapter in their existing configured runtime.
The pilot's local backend config and disabled tracing avoid a second inference
account and extra transcript logging. Pipelex does not account for calls inside
PipeFunc as native inference; use the embedded Jev receipt for usage, not both.

## Tests and reuse

```sh
uv pip install --python /tmp/jev-pipelex-venv/bin/python -e '.[dev,mcp]' -r integrations/pipelex/requirements.txt
/tmp/jev-pipelex-venv/bin/python -m pytest tests/test_pipelex_integration.py -q
```

Tests execute the real parser, type checks, sequence, Python operator and
conditional controller. HTTP is replaced with a fixture provider; this is not a
live Jev or end-to-end agent quality benchmark. Concurrent provider bindings and
the missing-provider case are checked separately. The dependency is pinned to
Pipelex 0.64.0 (Elastic-2.0); the adapter is original project code.

This can be a method leaf in a skill catalog: a guide explains when to use it,
typed inputs/outputs describe compatibility, and links describe composition.
Keep one method file as the source; expose its signature and provenance through
the host's existing catalog. Collection batches do not implement an adaptive
question/answer loop. The host still owns new evidence, progress, stopping,
recovery, and actual effects. SQL stores definitions/receipts; GraphQL, if added,
queries that same state rather than becoming an execution engine.

Browser/CUA, design and coding can reuse this shape when they provide represented
targets and current evidence. Trading examples must remain simulation data until
an independently authorized execution path exists. No such application adapter
is shipped by this pilot.
