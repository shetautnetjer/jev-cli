# Unknown / no-match

An explicit unknown is not a generic low-confidence fallback. It is a represented semantic answer: the legal options do not cover the input.

Use it when:
- a capability may be missing;
- the request asks for an unrepresented action;
- evidence cannot distinguish represented candidates;
- a contract needs repair.

Deterministic code should route this answer to a defined escalation path rather than forcing another relative winner.
