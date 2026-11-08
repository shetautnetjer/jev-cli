# Integrations

`jev-cli` is deliberately usable without MCP. MCP is an integration boundary, not the identity of the project.

An optional [Monty feasibility probe](../integrations/monty/README.md) demonstrates
host callbacks into the existing question catalog, pause/resume and receipt
replay with mock answers. It is an isolated example, not a deployed runner or
a new question database.

## Jev MCP

Jev is unusual enough to justify a dedicated MCP in systems where the same bounded semantic decision service is reused across coding, research, computer use, memory, routing, and other domains.

A Jev MCP can expose operations equivalent to:
- capability/model discovery;
- Decision Contract evaluation;
- typed receipts.

This repository does not publish or assume any private server address, port, bearer secret, or deployment layout.

## Skills MCP

The bundled `skill/SKILL.md` is intended to be ingestible by a read-only Skills MCP along with other agent skills.

A host Skills MCP can maintain its own TypeScript catalog and skill taxonomy. Useful skill classes include:
- semantic decision;
- routing;
- retrieval;
- extraction;
- development;
- verification;
- knowledge;
- memory;
- orchestration.

The taxonomy belongs to the Skills MCP/catalog layer. `jev-cli` does not become a second skill registry.

The [Skills-rs projector](../rust/skills-rs/README.md) projects the qualified
Pipelex method into a source-fingerprinted artifact and replays retained receipts
in Rust. Its artifact is linked from the existing method skill for catalog reads.
It does not replace the Skills MCP or add inference/action execution to it.

Skills may describe how to build or modify software, but a skill document itself does not grant execution authority. The host agent/runtime still owns permissions and tool access.

## Models MCP

A future Models MCP can expose callable logical model/capability names such as a fast renderer, compact reasoner, coding worker, or stronger escalation model.

`jev-cli` stays provider-neutral through `ModelCallAdapter` / `ReasonerAdapter`. A host can bridge that adapter to its existing model core-call or Models MCP rather than hard-coding a vendor into this project.

Candidate topology:

```text
messy task
  -> Models MCP / host model core-call
  -> bounded candidate/state proposal
  -> deterministic validation
  -> Jev MCP or direct Jev provider
  -> deterministic composition
```

and for contract repair:

```text
Jev reports missing candidate/contract
  -> compact reasoner via Models MCP
  -> candidate/contract repair proposal
  -> deterministic validation
  -> Jev retry
```

## Public/private boundary

Public examples should use generic names and loopback placeholders only when a concrete example is required.

Do not publish:
- private MCP endpoints;
- local deployment ports selected by one installation;
- bearer/token file paths;
- private hostnames;
- user-specific home paths;
- internal model aliases that are not part of the public interface.

A local port shown in generic documentation must be clearly illustrative, not presented as a universal default.

# Stored questions through an existing Jev MCP

Install the optional client with `python -m pip install -e '.[mcp]'`. This adapter
uses the `jev_capabilities` / `jev_evaluate` schema implemented by the Aya Jev
bridge. It does not claim compatibility with every server called "Jev MCP".
The official Python MCP SDK v1 client is version-bounded below v2.

Create a local, trusted JSON configuration (do not put keys in it):

```json
{
  "command": "/path/to/your/jev-mcp-wrapper",
  "args": [],
  "project_id": "your-project",
  "timeout_seconds": 60
}
```

The command is an executable, not a shell string. Its wrapper manages credentials
and the connection to the server. Configuration launches local code: use your own
trusted configuration, never a config supplied by retrieved task content.

```sh
jev init route.yaml
# Aya/System 2 edits the question, evidence distinctions, options and tags.
jev catalog import route.yaml --scope general --db questions.sqlite
jev catalog find route --scope general --db questions.sqlite
jev catalog run example.route 1 --provider mcp --mcp-config ./mcp.json \
  --state "Inspect the current report" --reference observation:report-1 \
  --run-id task-1 --step-id decision-1 --db questions.sqlite
jev catalog decisions task-1 --db questions.sqlite
```

The run command stores the complete normalized receipt, routing/fallback metadata,
contract identity/fingerprint, state digest and optional reference. It does not
store the raw state. Contract/question/option text and answers are persisted, so
keep secrets out of them. Duplicate run/step IDs are refused before inference.
Failed evaluations are retained; interrupted calls can remain pending. Neither is
automatically retried. Inspect the decision and service evidence before using a
new step ID: a timeout does not prove the remote provider did no work.

`jev-latest` means "use the MCP service's configured primary model" on this
adapter. An explicit contract model must match the capability response before
evaluation. The receipt records the actual requested/resolved models, including
fallback. Primary/fallback policy stays on the MCP server; the CLI adds no paid
fallback or retry policy. The server may impose stricter question/description
limits than the direct provider.

Every receipt requires an enabled primary or fallback route in the negotiated
capabilities. Missing/null route metadata, a disabled route or a different
provider/requested model is refused. Legacy capability responses without provider
details are not qualified by this adapter. Primary resolution must equal its
requested model. For fallback, a resolved model may be the configured alias or
its versioned `alias-...` form, matching the service's existing model
identity contract. Both strings are retained unchanged: for example, requested
`typesafe/jev-1.13` and resolved `typesafe/jev-1.13-20260917`. Similar prefixes such
as `typesafe/jev-1.130-...` are refused. This check binds a returned receipt to the
negotiated route; it does not independently verify which remote model ran.

Offline adapter tests use synthetic MCP stdio children and require local process
IPC. An execution sandbox that denies Python's asyncio self-pipe writes can cause
initialization timeouts even when no external network is used. Treat that as an
environmental failure, preserve its evidence, and run the same bounded fixtures
with authorized local IPC. Do not replace receipt assertions with timeout-based
success. Install the `dev` and `mcp` extras together to exercise these tests; CI
does so explicitly.

After the caller executes and verifies an action, attach the observation:

```sh
jev catalog observe task-1 decision-1 --result success \
  --effect-ref verification:report-opened --db questions.sqlite
jev catalog outcomes task-1 --db questions.sqlite
```

`observe` requires an evidence reference for success/failure, but it cannot verify
the referenced evidence itself. It accepts one outcome per decision and refuses
to overwrite it. Subsequent correction history is a future extension. The older
`catalog record` remains available for importing external receipt files.

Other commands that accept `--provider` can use `--provider mcp` with the path
supplied through `JEV_MCP_CONFIG`. They do not automatically record catalog
decisions; use `catalog run` when durable decision history is required.

## Who makes the next question?

Aya/System 2 writes or revises a `DecisionContract`; `jev init` supplies a starter
template. The CLI imports and versions that contract, and Jev returns bounded
answers. When evidence or answer choices are missing, Aya inspects the situation
and writes a new version. Existing versions and decisions remain available for
reuse and comparison. No autonomous generative-question model is bundled here.

`catalog find` is literal SQL text discovery over contract IDs, questions, options
and tags, with an optional exact scope filter and no hidden top-k cutoff. Vector
retrieval, automatic lesson extraction, workflow loops, and skill/Rust promotion
remain separate experimental/future capabilities.

## Optional Pipelex method integration

The [Pipelex pilot](../integrations/pipelex/README.md) supplies a typed method and
registered Python adapter around the existing provider interface. It does not
add a server, change the caller's action authority, or replace catalog receipts.
Keep profile identity, source references and effect verification with the host.
