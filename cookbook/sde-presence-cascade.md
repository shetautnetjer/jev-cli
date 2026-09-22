# Presence Checks and SDE-Style Cascades

Typed structure is not the same as semantic completeness.

A parsed object can be schema-valid while a required value is absent, unsupported, or inferred from the wrong evidence.

## Pattern

```text
source
 -> deterministic parsing/schema validation
 -> concrete semantic presence questions
 -> source-grounded value selection
 -> deterministic validation
 -> accept or escalate
```

## Presence question

Use a Noul only when the proposition is independently meaningful:

> Does the supplied source explicitly contain a value for the requested field?

Define true/false when “present” could be ambiguous.

Do not ask a vague “is extraction sufficient?” question.

## Value selection

When candidate values are pre-parsed from source, use Choice to select among them plus `none_of_these` if extraction may have missed the target.

The model cannot select a value omitted from the candidate set.

## Escalation

Escalate when:
- no explicit source support exists;
- candidate extraction produced no legal value;
- multiple candidates remain indistinguishable;
- a stronger source-reading step is needed.

A valid schema should never be treated as proof that the semantic field is correct.
