# Decision Basis + Next Operator

For workflow decisions, asking only “what should happen next?” often makes one question carry too many meanings.

A stronger pattern separates:

1. **next_operator** — the represented movement;
2. **decision_basis** — the concrete reason why that movement is justified.

## Contract shape

```yaml
questions:
  next_operator:
    type: choice
    instructions: Which represented next operation directly follows from the current state?
    criteria:
      Observe: Acquire fresh external state.
      Retrieve: Reopen retained/source evidence.
      Act: Perform the represented effect.
      Verify: Check whether a prior effect actually occurred.
      Infer: Derive a bounded semantic conclusion from sufficient current evidence.
      unknown_no_match: The required movement is not represented.

  decision_basis:
    type: choice
    instructions: Which evidence condition determines the workflow disposition?
    criteria:
      state_ready: Current state contains what is needed for the represented semantic decision.
      fresh_observation_needed: Current external state must be observed before deciding.
      retained_lookup_needed: Previously retained or source evidence must be reopened.
      effect_verification_needed: A claimed or attempted effect must be independently checked.
      wait_for_running: A known operation is still running and should not be duplicated.
      missing_candidate_or_contract: The legal action/candidate/contract needed for this case is absent.
      unresolved_distinction: The represented options cannot yet be discriminated from current evidence.
```

## Deterministic composition

Do not let confidence silently choose the workflow.

A caller can compose:

```text
state_ready                  -> use next_operator
fresh_observation_needed     -> Observe
retained_lookup_needed       -> Retrieve
effect_verification_needed   -> Verify
wait_for_running             -> Wait
missing_candidate_or_contract-> repair/escalate
unresolved_distinction       -> gather specific evidence or escalate
```

This is especially useful for agent loops, computer use, research, coding, and memory workflows.

## Why it works

`next_operator` answers **movement**.

`decision_basis` answers **reason class**.

Keeping them distinct prevents one vague “sufficient/ready/uncertain?” question from conflating completion, evidence needs, ambiguity, and action selection.
