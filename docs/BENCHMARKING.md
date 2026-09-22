# Benchmark Methodology

Benchmarks should measure the **composed application decision**, not only the largest probability.

## Separate development and evaluation sets

Keep development fixtures separate from frozen evaluation fixtures. Once a frozen set has been inspected repeatedly for failures, create a new held-out set before making a generalization claim.

## Record

For each case retain:
- contract/version/digest;
- state digest/reference;
- requested and resolved model;
- typed answers and full distributions where available;
- latency and token usage when the provider reports them;
- deterministic composition;
- expected observable outcome;
- provider/service errors.

## Useful families

Cross-domain families can include:
- software/code;
- research;
- desktop/computer-use state;
- creative/UI;
- scene/3D;
- memory/retrieval;
- missing-candidate or missing-contract cases.

## Regression themes

Include:
- explicit unknown/no-match;
- Choice vs inappropriate competing Nouls;
- precise vs vague discrimination criteria;
- parallel question equivalence;
- provider-invalid/error paths;
- candidate-recall loss;
- retrieval/extraction as features vs pruning;
- repeated-run distribution drift;
- consequence-specific thresholds.

Checked-in mock benchmarks validate the harness only. They are not claims about Jev model accuracy.
