---
id: RM-ORCH-007
title: "Workflow Wrapper Abstraction"
status: idea
stage: v2
priority: p1
order: 45
depends_on:
  - RM-ORCH-005
openspec_change: null
created_at: 2026-06-22
started_at: null
completed_at: null
---

# Goal

Decouple SDLC workflow orchestration from concrete worker implementations by introducing a wrapper/adaptor layer, so each lifecycle module (spec, memory, roadmap, eval, implementation) can be backed by different tools or implementations without changing the workflow engine contract.

# Problem Context

The current orchestrator directly names concrete workers and skills such as OpenSpec, repository memory, roadmap, EvalOps, and Superpowers. This is practical for the current repository, but it couples the workflow model to today's implementation choices. Future modules may have multiple viable implementations (for example different spec systems, memory systems, or evaluation runners). Without a wrapper boundary, replacing one module risks changing workflow phases, orchestration instructions, and governance logic together.

The desired direction is a wrapper model: `workflow.py` remains the deterministic state machine, while wrappers provide stable module-level contracts for dispatching implementation-specific workers and recording evidence.

# Scope

## In

- Define wrapper interfaces for lifecycle modules: spec, memory, roadmap, eval, and implementation.
- Keep `workflow.py` as the deterministic runtime and gatekeeper; wrappers handle worker dispatch and evidence normalization.
- Map current skills as the first adapter implementation for each module.
- Document wrapper contract: inputs, outputs, evidence keys, exit criteria, failure modes, and remediation guidance.
- Define how wrappers are selected/configured without changing workflow phase semantics.
- Preserve current OpenSpec, Roadmap, Memory, EvalOps, and Superpowers behavior during the first migration.

## Out

- No replacement of existing skills in the first phase.
- No marketplace/plugin registry.
- No generic agent framework rewrite.
- No broad redesign of the workflow phase model unless the wrapper contract exposes a concrete incompatibility.

# Design Notes

## Key Decisions

- Treat wrappers as module contracts, not workflow phases. A phase may call a wrapper, and a wrapper may choose the concrete worker implementation.
- Keep evidence normalized at the wrapper boundary so downstream gates do not depend on tool-specific output formats.
- Use current skills as default adapters to avoid a big-bang migration.
- Defer external implementation selection until the current governance loop is stable.

## Tradeoffs

- Adds abstraction and documentation overhead, but reduces coupling between the workflow engine and external tool choices.
- Normalizing evidence at wrapper boundaries may hide tool-specific details; wrapper logs should retain raw evidence where useful.
- Delaying implementation replacement avoids scope creep but means the first phase mainly creates an architectural seam.

## Initial Approach

1. Inventory current phase-to-worker dependencies in `sdlc-main.yaml` and `sdlc-orchestrator`.
2. Define wrapper contracts for spec, memory, roadmap, eval, and implementation modules.
3. Map current skills to wrapper adapters.
4. Define evidence normalization rules for each wrapper.
5. Update orchestrator documentation to dispatch via wrappers where appropriate.
6. Add tests or examples proving wrappers preserve current behavior.

## Open Questions

- Should wrapper configuration live in workflow YAML, a separate module registry, or orchestrator skill documentation?
- Should wrappers be implemented as Python commands, skill instructions, or both?

# Acceptance Criteria

- Wrapper contract document exists for spec, memory, roadmap, eval, and implementation modules.
- Current skills are mapped as default adapters without changing user-visible workflow behavior.
- Evidence keys and exit criteria are documented per wrapper.
- Orchestrator documentation explains when to call a wrapper vs a concrete worker.
- No existing workflow path loses functionality.

# Promotion Notes

Promote after RM-ORCH-005 closes the current governance lifecycle gap. This item is architecture evolution, not a blocker for the immediate governance fixes.

# Completion Notes

Not started.

# Design Reference

- `.ai/workflows/definitions/sdlc-main.yaml`
- `.ai/workflows/scripts/workflow.py`
- `skills/sdlc-orchestrator/SKILL.md`
- `skills/sdlc-roadmap/SKILL.md`
- `skills/sdlc-repository-memory-*`
- `skills/sdlc-evalops/`
