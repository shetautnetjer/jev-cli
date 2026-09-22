---
name: jev-decision-contracts
description: Design, run, search with, and benchmark bounded TypeSafe System One / Jev Decision Contracts. Use when software needs fast typed semantic judgment over a prepared state and explicit answer space.
---

# Jev Decision Contracts

Jev is strongest when the caller gives it the equivalent of an **informed decision packet**: enough relevant evidence, a precise question, a valid answer space, and a defined way to say that the represented choices do not fit.

Jev is a bounded semantic judge. It is not a planner, truth source, permission system, verifier, or substitute for deterministic facts.

## Build an informed decision packet first

Before asking Jev, be able to state all five:

1. **Decision** — exactly what one semantic decision is being made?
2. **State** — what evidence/facts does Jev need to discriminate the answers?
3. **Options** — what answers are actually legal?
4. **Discriminators** — what distinguishes each option from the others?
5. **No-match path** — what happens if the true answer is not represented or the distinction cannot yet be made?

More context is not automatically better. Give the smallest state that preserves the distinctions the decision depends on.

Keep observed facts separate from inferred/model-produced features.

## Keep exact facts outside Jev

Do not ask Jev to re-decide values code already knows exactly, such as:

- canonical IDs and hashes;
- arithmetic;
- exact timestamps;
- permissions/authority;
- known freshness or lifecycle state;
- whether an operation is already running;
- known pending effects;
- exact structural/schema invariants;
- verified acceptance results.

Use those facts to prepare the state or deterministically gate the decision.

## Choose the primitive by answer meaning

### Choice — one mutually exclusive finite answer

Use Choice when one represented alternative should win.

Examples:
- which handler should receive this request?
- which known action should happen next?
- which reason class explains the next workflow disposition?

If candidate coverage may be incomplete, include an explicit `unknown_no_match`, `other`, or `none`.

Do not use forced relative Choice to prove that the candidate set is complete.

### Noul — one independently meaningful proposition

Use Noul for a single yes/no proposition that remains meaningful by itself.

Good:
- “Does the state contain a prepared external side effect?”
- “Does the source explicitly contain the requested identifier?”

Avoid using several competing Nouls to simulate one mutually exclusive category. Multiple answers may all look plausible because the questions are independent.

Never ask both a proposition and its negation as separate Nouls.

### Score — one ordered dimension

Use Score when levels form a real ordered rubric.

Each level should describe a concrete situation. A Noul probability is not a substitute for intensity or degree.

## Prefer explicit discrimination over vague neutrality

Neutral means non-leading **and explicit**, not vague.

Avoid words like:
- best;
- most relevant;
- appropriate;
- ready;
- sufficient;
- uncertain.

These words can hide several different judgments.

Instead name the operational distinction:
- “Which represented operation is required by the request?”
- “What evidence condition determines the workflow disposition?”
- “Does the current state contain direct evidence for this exact claim?”

## Separate action from decision basis

For workflow/agent decisions, a strong reusable pattern is:

1. **next_operator** — Choice over represented legal movements plus `unknown_no_match`;
2. **decision_basis** — Choice over concrete reason classes;
3. optional orthogonal Nouls only when independently useful.

Useful decision-basis classes include:

- `state_ready`
- `fresh_observation_needed`
- `retained_lookup_needed`
- `effect_verification_needed`
- `wait_for_running`
- `missing_candidate_or_contract`
- `unresolved_distinction`

Then deterministic code composes the result.

Example composition:

- `state_ready` -> consume the represented next operator;
- `fresh_observation_needed` -> Observe;
- `retained_lookup_needed` -> Retrieve;
- `effect_verification_needed` -> Verify;
- `wait_for_running` -> deterministic Wait when known;
- `missing_candidate_or_contract` -> repair/escalate; do not force a listed fallback;
- `unresolved_distinction` -> collect the specific missing evidence or escalate.

This decomposition prevents one vague question from carrying action selection, evidence sufficiency, ambiguity, and completion at the same time.

## Parallel questions

Questions can share one request when they:

- use the same unchanged state;
- are independently answerable;
- do not depend on another answer to construct their own candidate set.

If answer A changes the state or legal options for question B, issue a second request.

Speculative branch questions are fine when the premise is explicit and code ignores unused answers.

## Protect candidate recall before ranking

Retrieval and semantic ranking solve different problems:

1. **candidate recall** — did the true evidence/candidate enter the pool?
2. **candidate ranking** — how should the available pool be ordered/judged?

A reranker cannot recover something removed before it sees the pool.

BGE can add retrieval/ranking features. GLiNER can add typed entities/features. Neither should silently delete legal semantic possibilities by default.

If you prune to top-k before Jev, make that k explicit and qualify the pruning behavior separately.

Use a two-stage “Jev family -> specialist preparation -> Jev exact decision/UNKNOWN” pattern only as an escalation scaffold when measurement shows it helps. It costs additional inference and is not the default.

## Confidence is not authority

Choice/Score confidence describes concentration of the model distribution. Noul returns the yes probability directly.

Do not turn one generic threshold into universal workflow policy.

Thresholds belong to:
- the exact Decision Contract;
- the data distribution;
- the consequence of false yes / false no;
- the chosen fallback or human/escalation path.

A high-confidence model answer still does not prove an external effect occurred.

## Version the whole Decision Contract

Treat these as one versioned unit:

- state schema;
- question type;
- instructions;
- criteria/rubric;
- candidate set;
- model/provider choice;
- composition policy;
- consequence/threshold policy.

Changing one can invalidate previous calibration.

## CLI workflow

Start with a saved contract:

```bash
jev init contract.yaml
```

Run it against state:

```bash
jev run contract.yaml --state-file state.json
```

Use `jev ask` for small experiments, not as an excuse to skip contract design.

Use `jev batch` for frozen JSONL cases.

Use `jev search` for discovery/chunking/ranking. If semantic judging is enabled, provide an explicit `--semantic-limit`; that number is a visible recall/cost decision.

Use `jev bench` to compare the **composed application result**, not only the top probability.

## MCP roles

This skill can be served by a host **Skills MCP**.

Jev itself may be exposed through a dedicated **Jev MCP** because bounded semantic decisions are reusable across many domains.

Generative models used for candidate/contract repair can remain behind a host model core-call or future **Models MCP**.

Do not place private MCP endpoints, credentials, or installation-specific ports in reusable skill material.

## Pre-flight checklist

Before calling Jev:

- [ ] Is the decision one coherent meaning?
- [ ] Is the primitive correct for that meaning?
- [ ] Are exact deterministic facts already resolved outside Jev?
- [ ] Does the state contain the evidence needed to distinguish the answers?
- [ ] Are the candidate descriptions contrastive rather than redundant?
- [ ] Can the true answer be outside the represented set?
- [ ] If yes, is no-match/other explicit?
- [ ] Are parallel questions independently answerable from this same state?
- [ ] Is composition deterministic and outside the model?
- [ ] Is uncertainty handled according to consequence rather than a universal threshold?
- [ ] Will effects be independently verified?

If the answer space is wrong, repair the contract. Do not ask Jev to make an uninformed decision.
