# Context Capsule

This project treats Jev as a bounded semantic decision provider inside ordinary software, not as a planner, source of truth, permission system, or autonomous actor.

## Durable design principles

- Prepare an **informed decision packet**: define the one decision, the state/evidence needed to discriminate it, the legal options, the distinctions between those options, and the no-match path.
- When workflow movement and the reason for that movement are different meanings, separate them into `next_operator` Choice and `decision_basis` Choice rather than hiding both inside one vague question.
- Use **Choice** for one mutually exclusive finite decision.
- Use **Noul** for one independently meaningful yes/no proposition.
- Use **Score** for an ordered rubric with concrete level meanings.
- Include an explicit `other`, `none`, or `unknown_no_match` when candidate coverage is not guaranteed.
- Keep exact facts that code already knows out of model judgment: identifiers, hashes, arithmetic, permissions, lifecycle state, timestamps, and structural invariants.
- Questions sharing the same state can be evaluated together when they are independently answerable.
- Version the question, criteria, candidate set, state shape, composition policy, and model selection as one Decision Contract.
- Treat confidence/probability as a model output, not evidence, permission, or verification.
- Protect candidate recall before ranking or semantic pruning. A reranker cannot recover a candidate that was removed before it saw it.
- Escalation should be explicit when the candidate set or contract itself is incomplete.

## Current TypeSafe surface

The current HTTP API evaluates `state`, `model`, and a map of typed `questions` at `POST https://api.typesafe.ai/v1/systemone`.

The default provider adapter uses the `jev-latest` alias. The response can report the resolved concrete model. Choice returns the selected option, full probability distribution, and confidence. Noul returns the probability of yes. Score returns an ordered-rubric result, distribution, and confidence.

This capsule is intentionally small. The implementation should not require carrying a large research corpus in context.
