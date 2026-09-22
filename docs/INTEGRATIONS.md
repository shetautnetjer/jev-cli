# Integrations

`jev-cli` is deliberately usable without MCP. MCP is an integration boundary, not the identity of the project.

## Jev MCP

Jev is unusual enough to justify a dedicated MCP in systems where the same bounded semantic decision service is reused across coding, research, computer use, memory, routing, and other domains.

A Jev MCP can expose operations equivalent to:
- capability/model discovery;
- Decision Contract evaluation;
- typed receipts.

This repository does not publish or assume any private server address, port, bearer secret, or deployment layout.

## Skills MCP

The bundled `skill/SKILL.md` is intended to be ingestible by a read-only Skills MCP along with other agent skills.

A host Skills MCP can maintain its own TypeScript catalog and skill taxonomy. Useful skill classes include:
- semantic decision;
- routing;
- retrieval;
- extraction;
- development;
- verification;
- knowledge;
- memory;
- orchestration.

The taxonomy belongs to the Skills MCP/catalog layer. `jev-cli` does not become a second skill registry.

Skills may describe how to build or modify software, but a skill document itself does not grant execution authority. The host agent/runtime still owns permissions and tool access.

## Models MCP

A future Models MCP can expose callable logical model/capability names such as a fast renderer, compact reasoner, coding worker, or stronger escalation model.

`jev-cli` stays provider-neutral through `ModelCallAdapter` / `ReasonerAdapter`. A host can bridge that adapter to its existing model core-call or Models MCP rather than hard-coding a vendor into this project.

Candidate topology:

```text
messy task
  -> Models MCP / host model core-call
  -> bounded candidate/state proposal
  -> deterministic validation
  -> Jev MCP or direct Jev provider
  -> deterministic composition
```

and for contract repair:

```text
Jev reports missing candidate/contract
  -> compact reasoner via Models MCP
  -> candidate/contract repair proposal
  -> deterministic validation
  -> Jev retry
```

## Public/private boundary

Public examples should use generic names and loopback placeholders only when a concrete example is required.

Do not publish:
- private MCP endpoints;
- local deployment ports selected by one installation;
- bearer/token file paths;
- private hostnames;
- user-specific home paths;
- internal model aliases that are not part of the public interface.

A local port shown in generic documentation must be clearly illustrative, not presented as a universal default.
