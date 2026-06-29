---
id: RM-ORCH-007
title: "Agent-Backed Lifecycle Wrapper Architecture"
status: done
stage: v2
priority: p1
order: 47
depends_on:
  - RM-ORCH-005
openspec_change: agent-backed-lifecycle-wrapper-architecture
created_at: 2026-06-22
started_at: 2026-06-24
completed_at: 2026-06-29
---

# Goal

Introduce an agent-backed lifecycle wrapper architecture that decouples deterministic workflow governance from concrete planning, implementation, testing, review, finish, spec, roadmap, memory, and eval workers.

# Problem Context

The current orchestrator directly names concrete workers and skills such as OpenSpec, repository memory, roadmap, EvalOps, and Superpowers. This is practical for the current repository, but it couples the workflow model to today's implementation choices. Future modules may have multiple viable implementations (for example different spec systems, memory systems, evaluation runners, or AI agent harnesses). Without a wrapper boundary, replacing one module risks changing workflow phases, orchestration instructions, and governance logic together.

The desired direction is an agent-backed wrapper model: `workflow.py` remains the deterministic state machine and gatekeeper, while `dev-orchestrator` routes allowed phase actions to specialized agents. Wrappers provide stable module-level contracts for OpenSpec, Superpowers, EvalOps, Roadmap, Memory, and verification behavior, and normalize agent/tool output into workflow evidence.

The design borrows from agent-platform patterns such as harness-neutral core logic, adapter shims, specialized agents, and evidence-first execution. The goal is not to build a generic agent framework; it is to make SDLC lifecycle execution agent-backed while preserving deterministic workflow governance.

# Scope

## In

- Define agent-backed wrapper interfaces for lifecycle modules: spec, memory, roadmap, eval, planning, implementation, testing, review, finish, and verification.
- Keep `workflow.py` as the deterministic runtime and gatekeeper; wrappers and agents handle worker dispatch and evidence normalization.
- Introduce `dev-orchestrator` as the routing coordinator for phase actions, with specialized `plan-agent`, `implement-agent`, `test-agent`, `review-agent`, and `finish-agent`.
- Support two explicit flow types: `spec-flow` for OpenSpec-governed changes and `lightweight-flow` for changes that need planning, implementation, verification, review, and finish without a formal OpenSpec change.
- Map current OpenSpec, Superpowers, Roadmap, Memory, and EvalOps skills as wrapped backends behind agent-facing contracts.
- Document wrapper contract: inputs, outputs, evidence keys, exit criteria, failure modes, and remediation guidance.
- Define how wrappers and agents are selected/configured without changing workflow phase semantics.
- Define TDD as a cross-cutting discipline: `plan-agent` plans TDD tasks, `implement-agent` executes red/green loops for behavior changes, and `test-agent` performs independent verification, debugging, regression, and EvalOps capture.
- Define finish behavior for both flow types: `spec-flow` archives OpenSpec changes; `lightweight-flow` runs development-branch finishing; both flows run workflow cleanup hooks.
- Define safe parallel dispatch as a `dev-orchestrator` responsibility, not nested subagent delegation.
- Preserve current OpenSpec, Roadmap, Memory, EvalOps, and Superpowers behavior during the first migration.

## Out

- No replacement of existing skills in the first phase; they remain wrapped backends.
- No marketplace/plugin registry.
- No generic agent framework rewrite.
- No broad redesign of the workflow phase model unless the wrapper contract exposes a concrete incompatibility.
- No nested subagent delegation requirement; parallelism is owned by `dev-orchestrator` at the phase/work-package level.

# Design Notes

## Key Decisions

- Treat wrappers as module contracts, not workflow phases. A phase may call a wrapper, and a wrapper may choose the concrete worker implementation.
- Use an agent-backed wrapper model for all lifecycle execution while keeping `workflow.py` as the deterministic owner of state transitions, pending hooks, allowed actions, and completion gates.
- Use `dev-orchestrator` as a routing coordinator, not as a concrete executor. It routes the current allowed phase action to a specialized agent and collects structured evidence.
- Represent planning, implementation, testing, review, and finish as specialized agents with fixed responsibilities.
- Record `flow_type: spec-flow | lightweight-flow` in workflow run state. Agents must not infer the flow type from context.
- Route `spec-flow` through OpenSpec wrappers and `lightweight-flow` through lightweight execution wrappers, while sharing test, review, and cleanup gates across both flows.
- Keep evidence normalized at the wrapper boundary so downstream gates do not depend on tool-specific output formats.
- Require every agent-backed wrapper to return structured evidence. Natural-language summaries alone are not sufficient for phase transitions.
- Treat TDD as a cross-cutting execution discipline. `plan-agent` plans TDD tasks but does not execute them; `implement-agent` executes TDD red/green loops for behavior-changing code; `test-agent` performs independent verification, debugging, regression, and EvalOps capture.
- Move safe parallel dispatch to `dev-orchestrator` to avoid nested subagent orchestration limits. `implement-agent` handles a single bounded implementation slice and returns package-level evidence.
- Use current skills as wrapped backends to avoid a big-bang migration.
- Flow names describe governance weight, not implementation backend. `spec-flow` means a formal OpenSpec lifecycle is required; `lightweight-flow` means it is not. Superpowers remains the default backend for `lightweight-flow`, but the name must not depend on that implementation.

## Tradeoffs

- Adds abstraction, agent contracts, and documentation overhead, but reduces coupling between the workflow engine and concrete tools, skills, and harnesses.
- Agent-backed wrappers are more flexible than pure Python wrappers, but they increase nondeterminism risk; `workflow.py` must retain all state and gate authority.
- Normalizing evidence at wrapper boundaries may hide tool-specific details; wrapper logs should retain raw evidence where useful.
- Full agentization improves lifecycle separation, but it increases debugging complexity unless each agent has a fixed input/output contract.
- Moving parallelism to `dev-orchestrator` avoids nested subagent limitations, but requires stricter work-package boundaries and final integration verification.

## Initial Approach

1. Inventory current phase-to-worker dependencies in `sdlc-main.yaml`, `workflow.py`, and `sdlc-orchestrator`.
2. Define the shared wrapper request/response contract, including `workflow_run_id`, `phase`, `action`, `flow_type`, relevant artifact paths, constraints, status, evidence, artifacts, blockers, and recommended next action.
3. Define `dev-orchestrator` routing responsibilities: select the specialized agent for the current allowed phase action, optionally split safe parallel work packages, collect structured evidence, and return normalized results to the workflow runtime.
4. Define `plan-agent` behavior:
   - Always use `brainstorming` for design clarification when needed.
   - For `spec-flow`, call `spec-wrapper` for OpenSpec propose, new change, or continue.
   - For `lightweight-flow`, use `writing-plans`.
   - Produce a TDD-aware plan that states required failing tests, verification commands, and EvalOps candidates, without executing tests or modifying code.
5. Define `implement-agent` behavior:
   - For `spec-flow`, call `spec-wrapper` for OpenSpec apply.
   - For `lightweight-flow`, use `executing-plans` and `using-git-worktrees`.
   - For behavior-changing code, execute the TDD red/green loop: write failing test, verify failure, implement minimally, and verify pass.
6. Define `test-agent` behavior for both flow types: systematic debugging, independent verification/regression, and EvalOps capture for durable regression cases.
7. Define `review-agent` behavior for both flow types: requesting/receiving code review and verification-before-completion evidence checks.
8. Define `finish-agent` behavior:
   - For `spec-flow`, call `spec-wrapper` to archive the OpenSpec change after verification passes.
   - For `lightweight-flow`, call `finishing-a-development-branch` after verification passes.
   - For all flows, perform workflow cleanup through roadmap, memory, and workflow hooks.
9. Define safe parallel dispatch rules owned by `dev-orchestrator`: only split independent work packages with disjoint files/modules, per-package evidence, and final integration verification.
10. Add tests or examples proving wrappers preserve current behavior and fail closed when required evidence is missing.

## Open Questions

- Where should wrapper and agent configuration live first: workflow YAML, orchestrator skill documentation, or a small module registry? The first implementation should pick the smallest option that still records `flow_type` and phase-agent mappings deterministically.
- Which evidence fields should be mandatory for each phase versus optional raw logs? The contract must be strict enough for gate validation without overfitting to a single CLI tool.

# Acceptance Criteria

- Agent-backed wrapper contract document exists for spec, memory, roadmap, eval, planning, implementation, testing, review, finish, and verification modules.
- `flow_type: spec-flow | lightweight-flow` is documented as an explicit workflow run state field, not inferred by agents.
- `dev-orchestrator` routing responsibilities are documented, including the rule that it routes and coordinates evidence but does not own workflow state transitions.
- Phase-agent mapping is documented for `plan-agent`, `implement-agent`, `test-agent`, `review-agent`, and `finish-agent`.
- `spec-flow` behavior is documented: plan uses OpenSpec propose/new/continue, implement uses OpenSpec apply, finish uses OpenSpec archive.
- `lightweight-flow` behavior is documented: plan uses `writing-plans`, implement uses `executing-plans` and `using-git-worktrees`, finish uses `finishing-a-development-branch`.
- TDD responsibility split is documented: `plan-agent` plans TDD tasks, `implement-agent` executes red/green loops, and `test-agent` performs independent verification/debug/regression/EvalOps capture.
- Evidence keys, exit criteria, blockers, artifacts, and raw-log retention are documented per wrapper and agent.
- Safe parallel dispatch is documented as a `dev-orchestrator` responsibility with constraints on independent work packages, per-package evidence, and final integration verification.
- Current OpenSpec, Roadmap, Memory, EvalOps, and Superpowers skills are mapped as wrapped backends without changing user-visible workflow behavior.
- Orchestrator documentation explains when to call a wrapper/agent vs a concrete worker.
- `workflow.py` remains the only owner of state transitions, pending hooks, allowed actions, and completion gates.
- No existing workflow path loses functionality.

# Promotion Notes

Ready for promotion.

# Completion Notes

Implemented and archived as `2026-06-29-agent-backed-lifecycle-wrapper-architecture`.

- Added the agent-backed wrapper contract and routing model across the SDLC workflow runtime.
- Recorded explicit `flow_type` handling and normalized evidence expectations for agent-backed phases.
- Landed the dev-orchestrator / plan-agent / implement-agent / test-agent / review-agent / finish-agent lifecycle split without moving workflow state ownership out of `workflow.py`.
- Follow-up roadmap work remains in RM-ORCH-008/009/010 for contract refinement and later runtime modularization.

# Design Reference

- `.ai/workflows/definitions/sdlc-main.yaml`
- `.ai/workflows/scripts/workflow.py`
- `skills/sdlc-orchestrator/SKILL.md`
- `skills/sdlc-roadmap/SKILL.md`
- `skills/sdlc-repository-memory-*`
- `skills/sdlc-evalops/`
