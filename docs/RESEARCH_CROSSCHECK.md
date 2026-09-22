# Jev Research → CLI Cross-check

This is a point-in-time audit of the public V0 against the generalized lessons that motivated it.

## Encoded strongly

| Discovery / lesson | Public V0 status | Where |
|---|---|---|
| Choice for mutually exclusive finite identity | Encoded | models, skill, cookbook |
| Noul for one independent proposition | Encoded | models, skill, cookbook |
| Score for ordered rubrics | Encoded | models, skill |
| Explicit none/other/unknown when coverage is open | Encoded | skill, examples, cookbook |
| Informed state/evidence before judgment | Encoded | skill, informed-decision cookbook |
| Contrastive candidate descriptions | Encoded as guidance/examples | skill, cookbook |
| One question = one decision meaning | Encoded | skill, question-design cookbook |
| Avoid vague best/relevant/sufficient/ready | Encoded | skill, anti-patterns |
| Proposition + negation is a bad Noul pattern | Encoded | skill, anti-patterns |
| Separate next movement from decision reason | Encoded | decision-basis cookbook/example |
| Orthogonal Nouls only when independently useful | Encoded | skill, decision-basis example |
| Parallel questions require unchanged shared state | Encoded | skill, parallel cookbook |
| Deterministic facts stay outside Jev | Encoded | skill, architecture |
| Confidence is not authority/verification | Encoded | skill, security |
| Candidate recall before ranking | Encoded | search architecture, skill, memory/search cookbooks |
| BGE is optional ranking/retrieval evidence | Implemented optional adapter | retrieval/bge.py |
| GLiNER is optional typed extraction/evidence | Implemented optional adapter | retrieval/gliner.py |
| Specialist pruning must be explicit | Encoded in search surface | semantic-limit is explicit |
| Jev sandwich is escalation, not default | Encoded as guidance | skill/cookbook |
| SDE-style schema validity is not semantic presence | Encoded | sde-presence cookbook |
| Closed-set function routing should separate function Choice from argument/presence checks | Encoded | function-routing cookbook |
| Exact integrity/property checks precede semantic fusion | Encoded as deterministic-boundary rule | skill/architecture |
| Jev reranking is not automatically beneficial after strong retrieval | Encoded | memory-retrieval cookbook |
| Missing candidate / missing contract remains a special escalation frontier | Encoded | skill, decision-basis example |
| Broad shared workflow vocabulary is useful, but one universal all-case Choice is not the target topology | Encoded indirectly | decision-basis decomposition |
| Safe receipts should avoid raw-state persistence | Implemented | DecisionReceipt state digest |
| Contract changes invalidate prior calibration | Encoded | skill/benchmark docs |
| Development vs held-out evaluation | Encoded | benchmarking docs |
| Provider errors separated from semantic logic | Partially encoded | provider normalization + errors |

## Present, but only partially productized

### Contract fingerprinting

Receipts already contain `contract_sha256` and `state_sha256`.

That is useful reproducibility evidence, but V0 does not yet expose a dedicated `jev fingerprint` command or a richer fingerprint manifest that separately names state schema, candidate universe, composition policy, and provider assumptions.

### Decision-contract linting

The skill/cookbook teaches the lint rules, but there is no `jev lint` / `jev check` command yet.

Useful future machine checks include:
- mutually exclusive labels represented as competing Nouls;
- Choice with open coverage but no explicit no-match;
- vague criteria terms without an explicit definition;
- proposition + negation pairs;
- obvious deterministic facts delegated to Jev;
- dependent parallel questions;
- hidden candidate pruning;
- irrelevant state inflation.

Some of these require heuristics, so lint output should be advisory and evidence-backed rather than pretending to prove semantic correctness.

### Candidate-coverage status

V0 supports explicit no-match and explicit semantic search limits, but there is not yet a first-class `candidate_coverage = complete | incomplete | uncertain` field.

A future reasoner/retriever compiler should be able to report coverage separately from ranking. Incomplete or uncertain coverage should normally escalate before a relative Choice.

### Request/audit bundle

V0 receipts store contract/state digests, normalized answers, model/provider information, usage, latency, and composition without raw state by default.

There is no dedicated sanitized request-audit bundle command yet for intentionally persisting:
- exact sanitized request state;
- exact questions/criteria;
- request/contract hashes;
- full distributions;
- provider/model identity;
- latency/usage/errors;
- explicit redaction metadata.

### Jev MCP provider

The architecture documents a future generic `JevMCPProvider`, but V0 implements direct TypeSafe and mock providers only.

This is intentionally separate from publishing any private host's Jev MCP address.

### Runtime reasoner compiler vs authoring/repair mode

`ModelCallAdapter` exists as an interface.

The safer long-term split is not fully implemented yet:

- normal runtime compilation: caller/code owns the candidate universe; the reasoner compiles task-local evidence for a fixed Decision Contract;
- authoring/repair mode: a stronger reasoner may propose new candidates/questions/contracts, followed by validation, linting, and benchmark work before production use.

Keeping those modes distinct protects contract stability.

## Still intentionally outside jev-cli

These should not become Jev authority:

- permissions and authorization;
- action execution;
- independent effect verification;
- canonical identity;
- memory/publication admission;
- global capability discovery;
- global model routing;
- host Skills MCP;
- host Jev MCP deployment;
- future Models MCP deployment;
- secret storage.

## Security cross-check

The repository's own security rules cover secret handling, raw-state persistence, scanned file execution, and publication checks.

For deeper source security review, use Codex Security when available rather than pretending the Jev publication gate is a vulnerability scanner.

Recommended distinction:
- `scripts/verify_jev_cli_publication.py` — publication hygiene: tokens/private paths/forbidden material;
- Codex Security `security-scan` — repository vulnerability/security audit;
- Codex Security `security-diff-scan` — changed-code security review;
- Codex Security `assess-patch-risk` — impact/regression/merge-risk analysis for an immutable patch.

## Prioritized next product work

1. `jev lint` / `jev check` for Decision Contract design mistakes.
2. Dedicated contract fingerprint command/manifest.
3. Candidate-coverage field and escalation policy.
4. Sanitized request/audit bundle.
5. Generic Jev MCP provider adapter.
6. Explicit runtime evidence compiler interface vs contract-authoring/repair interface.
7. Matched compact-reasoner experiments through the provider-neutral model-call adapter.

V0 is already useful and faithful to the major research lessons. The remaining gaps are mostly about turning expert guidance into machine-enforced developer ergonomics.
