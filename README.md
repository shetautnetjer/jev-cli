# jev-cli

A clean-room, file-layout-agnostic CLI for defining, running, searching with, and benchmarking **TypeSafe System One / Jev Decision Contracts**.

`jev-cli` keeps ordinary code in control. Jev supplies bounded semantic judgments; the caller owns candidate construction, permissions, effects, and verification.

> Status: early V0. Contract and receipt formats may evolve before 1.0.

## Core idea

```text
state
  -> deterministic preparation
  -> DecisionContract
  -> Jev
  -> typed Choice / Noul / Score answers
  -> deterministic composition
  -> caller-owned action or escalation
```

The **Decision Contract** is the reusable capability. Jev is one execution provider for it.

A good Jev call is an **informed decision packet**: one precise decision, the evidence needed to discriminate it, a valid set of options, clear contrasts between those options, and an explicit no-match path when coverage is incomplete. See [Informed Decision Packet](cookbook/informed-decision-packet.md).

## Install

Requires Python 3.11+.

```bash
python -m pip install .
```

Development:

```bash
python -m pip install -e '.[dev]'
pytest
```

Optional local specialists:

```bash
python -m pip install -e '.[retrieval]'
python -m pip install -e '.[extraction]'
```

For a source checkout, the repository also provides uniquely named helpers:

```bash
python scripts/install_jev_decision_cli.py --editable --dev
python scripts/run_jev_decision_cli.py doctor
```

The installed `jev` console command remains the normal user interface.

## Credentials

Never put API keys in command arguments.

Use either:

```bash
export TYPESAFE_API_KEY='...'
```

or:

```bash
export TYPESAFE_API_KEY_FILE=/run/secrets/typesafe_api_key
```

See [Security](docs/SECURITY.md).

## Quick start

Scaffold a contract:

```bash
jev init route.yaml
```

Run it:

```bash
jev run route.yaml --state-file examples/request.txt
```

Ask one ad-hoc Choice:

```bash
jev ask choice \
  --instructions "Which represented action matches this request?" \
  --option inspect="Read without changing state" \
  --option change="Make a represented change" \
  --option unknown_no_match="None safely match" \
  --state "Show me what changed."
```

Search arbitrary text/code locally:

```bash
jev search "decision contract unknown option" .
```

Add Jev semantic judging only with an explicit candidate pool:

```bash
jev search "decision contract unknown option" . \
  --semantic --semantic-limit 30
```

The explicit limit makes recall/cost pruning visible instead of hiding a universal top-k.

## Commands

| Command | Purpose |
| --- | --- |
| `jev init` | scaffold a Decision Contract |
| `jev ask` | run one Choice/Noul/Score question |
| `jev run` | run a saved contract |
| `jev batch` | run a contract over JSONL states |
| `jev search` | discover/chunk/rank arbitrary text, optionally with Jev |
| `jev bench` | run frozen benchmark cases |
| `jev cookbook` | list bundled recipes |
| `jev doctor` | inspect provider/extras configuration without exposing secrets |

Graph execution and an MCP/HTTP server are intentionally deferred from V0.

## MCP integration

This repository does **not** invent a new MCP registry.

It can be used in several deployment shapes:

- **standalone CLI** — direct TypeSafe System One / Jev calls;
- **Jev MCP** — a host may expose Jev as its own MCP because bounded semantic judgment is broadly reusable;
- **Skills MCP** — a host may catalog this repository's `skill/SKILL.md` alongside its other skills;
- **Models MCP** — a host may expose callable model/capability names and bridge them into the provider-neutral `ModelCallAdapter` for compact-reasoner experiments.

Those are integration roles, not required local addresses. This public repository intentionally contains no private MCP endpoints, bearer-token locations, hostnames, or deployment ports.

See [Integrations](docs/INTEGRATIONS.md).

## Search design

Search keeps these stages separate:

1. file discovery;
2. text extraction/chunking;
3. candidate recall;
4. ranking/features;
5. optional Jev judgment;
6. result composition.

BGE and GLiNER are optional helpers. They do not silently remove legal semantic possibilities.

## Design rules

- Prepare an informed decision packet before inference: decision, state, options, discriminators, and no-match path.
- Separate workflow movement (`next_operator`) from the concrete reason/evidence class (`decision_basis`) when one question would otherwise carry both meanings.
- Choice for one mutually exclusive finite decision.
- Noul for one independently meaningful proposition.
- Score for an ordered rubric with concrete level meanings.
- Include `other`, `none`, or `unknown_no_match` when candidate coverage may be incomplete.
- Exact IDs, hashes, arithmetic, permissions, and known lifecycle facts stay deterministic.
- Probability/confidence is not truth, permission, or verification.
- Question, criteria, candidate set, state shape, composition policy, and model selection form one versioned contract.

## Documentation

- [Context capsule](docs/CONTEXT_CAPSULE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Integrations](docs/INTEGRATIONS.md)
- [Security](docs/SECURITY.md)
- [Prior art](docs/PRIOR_ART.md)
- [Benchmark methodology](docs/BENCHMARKING.md)
- [Agent Bootstrap — copy/paste setup prompt](docs/AGENT_BOOTSTRAP.md)
- [Research → CLI Cross-check](docs/RESEARCH_CROSSCHECK.md)
- [Informed Decision Packet](cookbook/informed-decision-packet.md)
- [Decision Basis + Next Operator](cookbook/decision-basis-routing.md)
- [Question Design Checklist](cookbook/question-design-checklist.md)

## Clean-room policy

`caio0452/jev_search` was inspected as behavioral prior art. No compatible repository-root license was visible at the inspected revision, so no source code was copied.

## License

Licensed under the [MIT License](LICENSE).

Copyright (c) 2026 shetautnetjer.
