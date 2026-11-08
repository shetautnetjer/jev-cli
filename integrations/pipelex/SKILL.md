---
name: pipelex
description: Run typed Jev decision methods through Pipelex.
metadata:
  version: 0.1.0
  author: Khamani (shetautnetjer), Codex
---

# Typed Jev Methods Skill

Use this guide to validate and run an existing Jev DecisionContract as a typed
Pipelex method. It returns an advisory receipt and a declared result branch.

## When to Use

Use when a caller needs reusable typed question/answer steps, method composition,
or an explicit ready/evidence-needed/no-match branch. For one isolated judgment,
the ordinary Jev CLI avoids Pipelex startup overhead.

## Prerequisites

Read [the integration guide](README.md) for the pinned optional environment and
commands. The host must already provide a direct Jev credential route or a
compatible Jev MCP. Check the MCP's advertised limits before sending a batch.

## How to Run

Inspect [the executable method](decision.mthds), then select the existing
contract and exact source state. Use the bundled runner through `terminal` in
the integration guide. Mock mode qualifies plumbing; it is not semantic evidence.
Use a live provider only for the authorized task and keep its real receipt.

## Quick Reference

- Input: existing DecisionContract plus StatePacket with a source reference.
- Output: unchanged DecisionReceipt plus routing disposition.
- [Example contract](contract.yaml): demonstration criteria, not universal thresholds.
- [Fixture state](state.json): synthetic evidence and deterministic mock answers.
- `ready`: the contract's composition matched; the host still verifies any effect.
- `needs_evidence`: retrieve additional relevant evidence before a new judgment.
- `unknown_no_match`: the represented composition does not select a supported branch.

## Procedure

Reuse a matching versioned contract. Include a no-match path when candidate
coverage is incomplete. Batch independent questions over unchanged state; a
dependent follow-up needs new state and a separate call.

The host binds the provider, profile, capabilities, and actual execution path.
Preserve the receipt with the existing catalog/hook mechanism and record the
observed outcome separately. A replay should reopen its retained receipt rather
than spend inference again.

## Rust projection and replay

The [qualified projection](projection.json) is derived from this guide, the
method, and the pinned adapter. Use the existing Skills MCP to discover/read
these resources; Skills-rs is a local projector/replay executable, not another
catalog server. Follow the integration guide's Rust commands and verify current
source before replay. It validates an existing receipt and follows its branch;
it does not call Jev, select a skill, execute actions, or grant permission.

## Pitfalls

Pipelex collection batching is not an adaptive reasoning loop. The host owns
progress, new evidence, stopping, and restart recovery. A script name or a skill
description does not establish that an action or provider exists. Unknown
observations remain unknown; a probability is not a completion receipt.

## Verification

Run the integration tests and documented mock command first. Check actual
provider/model, complete answer IDs, source hash, disposition, and usage on a
bounded live run. Compare total workflow time and useful outcomes with the plain
CLI before claiming a speed or quality improvement.
