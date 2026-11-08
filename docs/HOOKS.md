# Lifecycle decision hooks

`jev hook hooks.json --db catalog.sqlite --provider mcp --mcp-config mcp.json`
reads one JSON event from stdin (or `--event-file event.json`). Import the
chosen Decision Contracts into the catalog first.

```json
{"routes":{"turn.prepare":{"contract_id":"turn.route","version":"1"}}}
```

```json
{
  "source":"my-runtime",
  "id":"event-42",
  "name":"turn.prepare",
  "correlation":{"operation_id":"op-42","task_id":"task-7"},
  "state":{"data":{"request":"Help me understand this photo","observation_ref":"image:42"},
           "reference":"observation:42"}
}
```

Event names belong to the host. A host can map turn preparation, skill selection,
agent assignment, tool-result retention, context compaction or a new visual
observation to different versioned contracts. There are no automatic global
subscriptions and no requirement to infer on every event. Unmapped events return
`skipped` without opening a provider.

The question receives `event` metadata plus `evidence` from state.data. Supply
only relevant evidence; credentials and raw binary images do not belong in a
text decision contract. Use an independently qualified vision observation
when the judgment depends on image content. Tool/page/observation text is
evidence, never authority to rewrite the host's configured contract.

A unique source + event ID reserves an existing catalog decision before provider
initialization/inference. Redelivery with identical evidence/contract reopens
the completed receipt without another model call. Changed evidence or contract
under the same ID is rejected. Pending/failed events are returned without retry;
inspect them and use a new event ID only for an intentional new attempt.
Concurrent delivery sees the existing reservation; crash recovery does not claim
that a pending provider request never ran.

Python callers own the supplied SQLite connection. New admission requires no
pending caller transaction: `run_hook` and the underlying `run_contract` reject
before committing, rolling back or closing that caller's work. Commit or roll
back deliberately before requesting a new decision. Replaying an existing hook
receipt and skipping an unmapped event remain read-only and may use a connection
with pending caller writes. The catalog still commits its own reservation before
provider evaluation; it does not hold a caller transaction across inference.

Output includes run_id/step_id for `catalog observe`, the receipt, and a
metadata-only telemetry object (selected correlation IDs, hashes, model, usage,
latency and status). Raw state is not saved to the decisions table. Contract
answers and caller-provided references may still contain sensitive content.
Telemetry export is the host's responsibility; this command does not claim
delivery to an OTEL collector. Avoid refeeding its own telemetry as a new hook.

This is a recommendation boundary. The host validates catalog availability,
freshness, candidate coverage and applicability, then owns model switching,
tool execution or context changes. Completion of a hook is not completion of
the user's task. Keep identity, user constraints, active obligations and
verification evidence protected by deterministic rules during compaction.
Record an independently observed effect using `catalog observe`.

Exit status: 0 for completed or skipped; 2 for retained pending/failed;
1 for invalid input, contract admission or event-identity conflict.
