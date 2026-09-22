# Informed Decision Packet

Jev should not be handed a vague request and asked to “figure it out.” Prepare the decision the way you would prepare a human reviewer to make a fast, informed choice.

Every decision packet should answer five questions before inference:

1. **Decision** — What one judgment is being requested?
2. **State** — What evidence is needed to make that judgment?
3. **Options** — What answers are legal?
4. **Discriminators** — What distinguishes one answer from another?
5. **No-match path** — What if the real answer is missing or the evidence cannot distinguish the represented options?

## Example

Poor packet:

```text
State: "The user wants help with Git."
Question: "What is the best tool?"
Options: status, diff, search
```

The state does not preserve the distinction that matters, and “best” is underspecified.

Better packet:

```json
{
  "request": "Show me the exact changed lines in the current worktree.",
  "known_facts": {
    "repository_exists": true,
    "worktree_is_dirty": true
  }
}
```

Question:

> Which represented operation directly satisfies the request?

Criteria:

- `repo_status` — inspect whether a worktree is clean/dirty; does not return diff hunks.
- `git_diff` — inspect actual changed lines/hunks.
- `literal_search` — search exact text occurrences.
- `unknown_no_match` — none of the represented operations directly satisfies the request.

Now Jev has the information and contrasts needed for a bounded decision.

## State quality

Include facts that discriminate the options. Exclude unrelated history.

Prefer named structured fields when the decision depends on different kinds of evidence:

```json
{
  "request": "...",
  "observed_state": {...},
  "known_constraints": {...},
  "available_candidates": [...]
}
```

Do not mix verified facts and model guesses in one unlabeled blob.

## Candidate quality

Candidate descriptions should be contrastive. Each should explain what it covers and, when useful, what it does **not** cover.

If the candidate set is open or incomplete, add `unknown_no_match`.

A high-quality answer requires a high-quality decision surface.
