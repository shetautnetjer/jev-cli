# Memory and Retrieval

Jev can judge retrieved evidence, but retrieval quality has two separate questions:

1. Did the retriever return the evidence at all?
2. Given the returned pool, can Jev rank/judge it well?

Never confuse these.

## Recall first

A semantic reranker cannot recover omitted evidence.

Improve source placement, indexing, lexical/vector recall, query projection, or candidate generation before blaming the reranker.

## When Jev helps

Jev can be useful for:
- “Does this candidate directly answer the query?”
- relation/status classification;
- choosing among a small set of already-retrieved source candidates;
- deciding whether two retained records describe the same bounded subject.

## When Jev should not own the decision

Keep outside Jev:
- source authority;
- whether a file actually exists;
- publication/admission policy;
- exact freshness timestamps;
- provenance hashes;
- permission to mutate/delete memory.

## Measure reranking per backend

A strong retriever may already have excellent top-1 ordering. Adding Jev can cost tokens/latency and can sometimes make ordering worse.

Benchmark the complete pipeline:
- candidate recall@k;
- baseline ranking;
- Jev-assisted ranking;
- end-task correctness;
- token/latency cost.
