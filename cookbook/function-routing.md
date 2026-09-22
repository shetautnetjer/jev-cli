# Function and Tool Routing

Use Jev to choose among a **bounded, already-discovered** set of functions or tools.

Do not ask Jev to invent tools that are not in the candidate set.

## Prepare the candidates

Good descriptions say what a tool does and what nearby tools do differently.

```yaml
criteria:
  repo_status:
    purpose: Inspect clean/dirty repository state.
    excludes: Does not return changed lines.
  git_diff:
    purpose: Return actual changed lines and hunks.
    excludes: Not just a clean/dirty summary.
  literal_search:
    purpose: Find exact text or regex-like occurrences.
    excludes: Does not resolve symbol semantics.
  unknown_no_match:
    purpose: No represented tool directly satisfies the request.
```

## Separate routing from argument presence

Routing and argument extraction are different decisions.

A useful packet may ask in parallel:

- Choice: which function?
- Noul: is a required file path present?
- Noul: is a symbol name explicitly present?
- Choice: which represented mode/value applies?

Only consume the answers relevant to the selected function.

## Two-pass routing

If the first answer changes the legal argument candidates, make a second request.

Example:

```text
request -> Choice(function)
       -> deterministic discovery for that function
       -> Choice(argument among newly discovered candidates)
```

Do not pretend the second candidate set existed in the first request.

## Missing function

If no represented tool can satisfy the request, return `unknown_no_match` and escalate to capability discovery or stronger reasoning.

Do not force the “closest” tool merely because it is available.
