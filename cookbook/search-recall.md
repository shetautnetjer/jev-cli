# Search: recall before ranking

`jev search` separates discovery, chunking, retrieval, optional semantic judging, and output.

Start with local lexical recall:

```bash
jev search "target phrase" path/to/project
```

Use BGE as an optional ranking adapter:

```bash
jev search "semantic query" path/to/project --retriever bge
```

If you ask Jev to judge chunks, state an explicit candidate pool:

```bash
jev search "semantic query" path/to/project --semantic --semantic-limit 40
```

That limit is a recall/cost tradeoff and is surfaced in output. GLiNER labels may annotate returned chunks; they do not silently delete candidates.
