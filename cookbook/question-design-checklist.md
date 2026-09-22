# Question Design Checklist

Question wording is part of the Decision Contract.

## One question, one meaning

Bad:

> Is the evidence sufficient and is it safe to act?

This combines at least two judgments.

Better:

- Choice: which evidence condition applies?
- Noul: is a specific effect already prepared?
- deterministic policy: may this action execute?

## Name the referent

Bad:

> Is this ready?

Better:

> Does `state.observation` contain the current value required to discriminate the represented options?

## Avoid hidden ranking criteria

Bad:

> Which option is most relevant?

Better:

> Which represented operation directly satisfies the user’s stated request?

## Describe contrasts

If two candidates are easy to confuse, make the difference explicit in criteria.

For example:

- `inspect_status`: current state summary only.
- `inspect_diff`: actual changed lines/hunks.

## YAML note for Noul criteria

If you write Noul criteria in YAML, quote the keys `"true"` and `"false"`. Unquoted YAML boolean-looking keys may be parsed as booleans instead of the literal strings expected by the contract schema.

## Preserve no-match

If coverage is not guaranteed, include:
- `unknown_no_match`;
- `other`;
- `none_of_the_above`.

This is a semantic answer, not merely an abstention threshold.

## Test the boundary cases

Freeze examples for:
- exact match;
- near-neighbor confusion;
- ambiguous/underspecified state;
- missing candidate;
- contradictory evidence;
- extra distractors;
- out-of-set requests;
- model/service error.

Judge the composed application behavior, not only whether the top label “looks reasonable.”
