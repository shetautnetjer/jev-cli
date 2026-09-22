# Anti-patterns

## Forced Choice without unknown

A Choice compares represented alternatives. If none may fit, include an explicit no-match option.

## Many Nouls for one exclusive identity

Independent yes/no probabilities do not enforce mutual exclusivity. If exactly one represented category should win, use Choice.

## Proposition plus its negation

Do not ask both “is X true?” and “is X false?” as independent questions. Ask one directional proposition.

## Vague criteria

“Most relevant”, “best”, “appropriate”, “ready”, and “sufficient” can hide several different judgments. State the exact discrimination criterion.

## One universal confidence threshold

Thresholds belong to a contract and consequence model. A harmless preference and a consequential effect should not inherit the same default.

## Semantic models deciding deterministic facts

Do not ask a model to re-decide IDs, hashes, arithmetic, exact timestamps, known permissions, or already-known lifecycle state.

## Premature retrieval pruning

A reranker cannot recover a candidate removed before it sees the candidate set. Separate recall from ranking and make pruning visible.

## Probability as verification

A high probability is still a model judgment. Verification requires evidence appropriate to the claim or effect.
