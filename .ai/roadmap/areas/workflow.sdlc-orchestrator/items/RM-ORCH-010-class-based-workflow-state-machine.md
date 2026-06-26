---
id: RM-ORCH-010
title: "Class-Based Workflow State Machine"
status: idea
stage: v2
priority: p1
order: 48
depends_on:
  - RM-ORCH-009
openspec_change: null
created_at: 2026-06-26
started_at: null
completed_at: null
---

# Goal

Introduce a standard class-based workflow state machine core for phase transitions, transition legality, readiness, exit criteria, blockers, and user-facing invalid-transition guidance.

# Problem Context

The current workflow runtime is primarily procedural. That has worked for the initial SDLC governance model, but the state model is becoming more complex: roadmap-backed flows, OpenSpec-backed flows, lightweight flows, agent-backed wrappers, evidence gates, review loops, finalize hooks, and future auto-remediation loops all need clearer state and transition boundaries.

Once the runtime is modularized, a focused class-based state machine can improve correctness and extensibility without combining behavior changes with file splitting.

# Scope

## In

- Model workflow run state, workflow definition, phases, transitions, readiness, blockers, and exit criteria with explicit classes or equivalent objects.
- Provide a transition validator that rejects illegal transitions and reports legal next transitions plus required conditions.
- Support the current phase graph and future plan/implement/review/finalize/done lifecycle shape.
- Preserve `workflow.py` as the CLI facade over the new state-machine core.
- Keep domain state ownership external: roadmap files, OpenSpec artifacts, memory, and eval assets remain owned by their domain modules.
- Use existing behavior tests plus new transition-focused tests to prove compatibility.

## Out

- No generic workflow framework or plugin marketplace.
- No migration of roadmap domain state into the workflow runtime.
- No replacement of agent wrappers or concrete lifecycle skills.
- No change to run file layout unless separately justified by a compatibility plan.

# Design Notes

## Key Decisions

- Implement the class-based model only after the runtime has been modularized.
- Treat classes as state-machine boundaries, not as a reason to move all domain logic into objects.
- Keep domain loaders/adapters outside the core state machine.
- Make invalid transitions explicit and actionable: include current phase, attempted transition, legal transitions, and unmet conditions.

## Tradeoffs

- A class-based model improves conceptual clarity but is higher risk than contract enhancement or modularization.
- Deferring this until after modularization avoids mixing semantic changes with mechanical file movement.
- The runtime may still need procedural CLI glue, but transition behavior becomes easier to reason about and test.

## Initial Approach

1. Define a small state-machine core around existing phase YAML semantics.
2. Wrap existing transition logic behind the new core without changing CLI behavior.
3. Add tests for legal and illegal transitions, branch handling, blocked runs, pending hooks, required gates, and evidence-backed exit criteria.
4. Migrate command handlers to call the state-machine core.
5. Remove duplicated transition checks only after behavior parity is proven.

## Open Questions

- Should the state-machine core model sub-phases directly, or continue using the existing phase names as the canonical state identifiers?
- Should roadmap state transitions be represented as a separate domain state machine with adapters, or only validated through existing roadmap loaders?
- How configurable should review loop limits be before they become over-engineered?

# Acceptance Criteria

- A class-based state-machine core owns transition validation and readiness/exit checks.
- Illegal transitions produce structured errors with legal next transitions and unmet conditions.
- Existing workflow CLI commands still work through `workflow.py`.
- Existing workflow behavior tests pass.
- New transition-focused tests cover review loops, finalize failure loops, branch decisions, blocked runs, hooks, gates, and evidence-backed exits.
- Roadmap and OpenSpec domain state remain external to the workflow state-machine core.

# Promotion Notes

Promote after workflow runtime modularization is complete and stable. This is the deeper design cleanup following the minimal contract and module boundary work.

# Completion Notes

Not started.

# Design Reference

- `docs/manual/design/state_machine_design.md`
- `docs/manual/plans/workflow-py-state-machine-contract.md`
- `.ai/workflows/scripts/workflow.py`
- `.ai/workflows/definitions/sdlc-main.yaml`
