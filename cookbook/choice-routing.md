# Choice routing

Use Choice when exactly one represented route should be selected.

```yaml
id: example.route
version: "1"
model: jev-latest
questions:
  route:
    type: choice
    instructions: Which represented route matches the request?
    criteria:
      inspect: Read or inspect without changing state.
      change: Make a represented change.
      unknown_no_match: None of the represented routes safely match.
```

The no-match outcome protects the boundary of the represented action space.
