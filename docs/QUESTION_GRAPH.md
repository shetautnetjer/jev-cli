# Jev question catalog and situated workflow loop

Status: local catalog slice implemented 2026-09-23; graph runner, GraphQL view, AYA MCP adapter and browser/CUA integration remain design candidates.

## Ownership and integration

- The public `jev-cli` owns portable Decision Contract authoring, lint, examples, receipts, and an optional local catalog interface. It must not require AYA paths or credentials.
- AYA's existing `aya_jev` MCP owns the deployed bounded Jev call. Its direct TypeSafe primary and optional OpenRouter fallback already exist. The CLI can use an adapter to this MCP; neither surface should fork question semantics or independently spend paid fallback.
- AYA's Kernel/Decision Gate owns admission, effect lifecycle and loop budgets; Graph IR is a versioned representation of current work, not a mandatory prewritten DAG. Cognition/attention/model routing propose missing distinctions and compile candidate sets.
- Browser ADI and CUA provide observed controls, stable references, safe effects and post-action observations. Jev selects only among current, eligible operations and targets; it never manufactures a control or grants authority.

## One transition at a time

`Aya goal -> observe current state -> deterministic freshness/eligibility check -> retrieve question/contract -> check candidate coverage -> Jev bounded choice -> Decision Gate -> ADI effect -> new observation/receipt -> compare progress -> repeat or stop`.

Aya may generate the next question from the last receipt and current goal. Record each observed transition as a run edge; a useful workflow emerges from these edges. A loop requires an explicit progress predicate, iteration/time/cost budget and stop/blocked paths. Independent Jev heads may share one state in one request; a question that depends on an answer waits for the next step.

For browser/desktop, one indexed observation contains surface/generation, element refs, supported actions, visibility/enabled status and relevant text. First choose a supported operation and a compatible target from that same observation. Browser-use/jev-ultrafast is prior art for one request carrying operation and speculative compatible target heads. Before effect, reject stale generations and invalid refs. After effect, observe again; evidence of success comes from the new state or task output, not Jev confidence. When controls are unrepresented, ask Aya to inspect/expand rather than force a choice.

## Local SQL proposal

The local catalog stores definitions and outcomes separately. Reuse the AYA Dictionary's ID/status/source vocabulary when integrating with AYA; the public CLI uses portable IDs. Suggested minimum tables:

```sql
CREATE TABLE contracts (
  contract_id TEXT NOT NULL,
  version TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  scope TEXT NOT NULL,
  source_ref TEXT,
  status TEXT NOT NULL,
  PRIMARY KEY (contract_id, version)
);
CREATE TABLE questions (
  contract_id TEXT NOT NULL,
  version TEXT NOT NULL,
  question_id TEXT NOT NULL,
  primitive TEXT NOT NULL CHECK (primitive IN ('choice','noul','score')),
  wording TEXT NOT NULL,
  criteria_json TEXT NOT NULL,
  state_schema_json TEXT NOT NULL,
  consequence_class TEXT NOT NULL,
  PRIMARY KEY (contract_id, version, question_id),
  FOREIGN KEY (contract_id, version) REFERENCES contracts(contract_id, version)
);
CREATE TABLE transitions (
  contract_id TEXT NOT NULL,
  version TEXT NOT NULL,
  question_id TEXT NOT NULL,
  answer_key TEXT NOT NULL,
  next_operator TEXT NOT NULL,
  predicate_ref TEXT,
  PRIMARY KEY (contract_id, version, question_id, answer_key),
  FOREIGN KEY (contract_id, version, question_id)
    REFERENCES questions(contract_id, version, question_id)
);
CREATE TABLE outcomes (
  run_id TEXT NOT NULL,
  step_id TEXT NOT NULL,
  contract_id TEXT NOT NULL,
  version TEXT NOT NULL,
  question_id TEXT NOT NULL,
  answer_json TEXT NOT NULL,
  state_digest TEXT NOT NULL,
  provider_receipt_ref TEXT,
  effect_receipt_ref TEXT,
  observed_result TEXT NOT NULL,
  correction_ref TEXT,
  PRIMARY KEY (run_id, step_id, question_id)
);
```

Do not put keys or raw private UI contents in the catalog. Keep runtime task/turn/trace/observation/effect IDs in AYA's existing event and source tables, with references in outcomes, rather than cloning them. A contract change gets a new fingerprint/version. `observed_result` must distinguish success, failure, unresolved and superseded; the Jev answer is not the outcome.

The CLI now provides `catalog import/list/show/record/outcomes` against its existing DecisionContract and DecisionReceipt types. Import stores the full contract, its fingerprint and each question; changed content must use a new version. Record accepts an external observed status and receipt references. That status is supplied by the caller, not independently verified by the catalog. SQL transitions remain a reserved table with no graph executor. Contract lint and an AYA MCP adapter still need qualification. GraphQL, if needed, is a read/query facade over the same SQL definitions and outcomes; it is not a second store or workflow engine. An initial SQL view or CLI query may be enough.

## Prior art to evaluate, not blindly install

- Browser: browser-use/jev-ultrafast; desktop: lahfir/agent-desktop's jev-desktop skill. Compare with AYA Browser ADI and CUA on the same tasks, including stale refs and ambiguous controls.
- MCP: itsmostafa/typesafe-mcp and jkudish/jev-mcp. Compare batching and tool design with deployed aya_jev.
- Context: tamaratran/fast-jev-compaction. Preserve exact non-reproducible evidence and constraints; measure recall after compaction.
- UI: vercel-labs/json-render is a renderer for typed UI specs, separate from Jev's decision contract.
- Other linked examples (routing, review, repo navigation, knowledge graphs, market signals, games and drones) are application-level recipes. Import a qualified decision pattern as a versioned contract, not the whole application as an AYA skill by name.

## Qualification

1. Freeze a small set of actual browser and desktop tasks with identical observations for current policy and a Jev-assisted arm.
2. Track candidate recall, semantic choice, provider errors, stale refs, authority, effect execution, progress, completion evidence, latency, input/output tokens and paid fallback calls separately.
3. Test rate-limited direct calls using provider fixtures: fallback only for documented eligible responses, no duplicate effect, and one consolidated receipt.
4. Test one missing-control case, one repeated-state loop, and one question/contract change that invalidates prior calibration.
5. Keep the stronger Aya model available to create or revise a contract when the action space is incomplete; freeze and evaluate the revised contract before routine use.

Existing evidence: AYA semantic-workflow Phase 1 found exact lifecycle decisions belong to deterministic checks; later question-design V3 improved bounded semantic decisions but did not solve candidate coverage. Those results are development evidence, not proof of end-to-end browser/CUA speedups.

## CLI catalog example

```sh
jev init route.yaml
jev catalog import route.yaml --db ./questions.sqlite
jev catalog list --db ./questions.sqlite
jev catalog show example.route 1 --db ./questions.sqlite
jev run route.yaml --state "Show the current page" > receipt.json
jev catalog record receipt.json --run-id run-1 --step-id step-1 --result unresolved --db ./questions.sqlite
jev catalog outcomes run-1 --db ./questions.sqlite
```

The example `run` call requires a configured TypeSafe credential; `catalog import/list/show` and recording an existing receipt do not. Do not pass secrets or raw sensitive task state to the catalog.
