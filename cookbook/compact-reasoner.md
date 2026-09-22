# Compact reasoner pairing

The CLI defines a provider-neutral `ModelCallAdapter` so host runtimes can connect an existing model core-call or Models MCP.

Candidate experiment:

```text
messy task
 -> compact reasoner proposes bounded state + candidate space
 -> deterministic validation
 -> Jev Decision Contract
 -> deterministic composition
```

A second experiment handles contract gaps:

```text
Jev -> missing candidate / missing contract
 -> compact reasoner proposes repair
 -> deterministic validation
 -> Jev retry
```

Measure task correctness, candidate coverage, Jev/model tokens, latency, escalation frequency, and consequential errors. Do not assume a cheaper model is sufficient without matched evaluation.
