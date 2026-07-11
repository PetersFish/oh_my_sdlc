# Metadata

- Agent: plan-agent
- Workflow run: `2026-07-11-RM-ORCH-009`
- Slice: `default`
- Phase: `create_change`
- Flow type: `spec-flow`
- Change: `modularize-workflow-runtime`
- Roadmap item: `RM-ORCH-009`

# Objective

Produce provider-owned OpenSpec artifacts for a behavior-preserving modularization of the workflow runtime, ready for user review and later TDD execution.

# Work Completed

- Loaded relevant repository memory, roadmap scope, workflow runtime structure, regression-suite structure, and template synchronization behavior.
- Resolved the roadmap design questions in favor of a sibling `workflow_runtime/` package and an end-to-end-authoritative test strategy with a small focused module suite.
- Created and provider-verified the OpenSpec proposal, design, capability spec, and implementation tasks.
- Included explicit failing-first expectations, named behavior tests, exact verification commands, implementation order, and EvalOps disposition.

# Files / Artifacts Changed

- `openspec/changes/modularize-workflow-runtime/.openspec.yaml`
- `openspec/changes/modularize-workflow-runtime/proposal.md`
- `openspec/changes/modularize-workflow-runtime/design.md`
- `openspec/changes/modularize-workflow-runtime/specs/workflow-runtime-modularity/spec.md`
- `openspec/changes/modularize-workflow-runtime/tasks.md`
- `.ai/workflows/runs/active/2026-07-11-RM-ORCH-009/handoffs/default/plan-agent.md`

# Design Artifacts

- Primary review entry: `openspec/changes/modularize-workflow-runtime/proposal.md`
- Proposal: `openspec/changes/modularize-workflow-runtime/proposal.md`
- Design: `openspec/changes/modularize-workflow-runtime/design.md`
- Spec: `openspec/changes/modularize-workflow-runtime/specs/workflow-runtime-modularity/spec.md`
- Tasks: `openspec/changes/modularize-workflow-runtime/tasks.md`

# Key Decisions

- Preserve `.ai/workflows/scripts/workflow.py` as a thin executable facade.
- Place extracted code in `.ai/workflows/scripts/workflow_runtime/` rather than loose sibling files or a relocated entry point.
- Split by acyclic responsibility layers: core, state, definitions, domains, policies, dispatch, lifecycle, governance, and CLI.
- Keep `tests/test_workflow.py` authoritative for observable behavior; add `tests/test_workflow_modules.py` only for extraction-specific contracts.
- Expand bootstrap initialization and template/distribution drift checks to cover the complete nested package inventory.
- Treat EvalOps as not required because the change is deterministic; retain only a future candidate for agent path-routing regressions.

# Open Questions

None. User approval or revision of the completed design package is required before implementation.

# Commands Run (none)

None recorded as implementation or test execution; planning only.

# Evidence Summary

The resolved `openspec-propose` provider path created all required artifacts. Provider status reports `isComplete: true`, with `proposal`, `design`, `specs`, and `tasks` all `done`; the apply requirement `tasks` is satisfied.

# Blockers

None.

# Assumptions

- Existing CLI behavior and persisted state are the compatibility baseline.
- No undocumented external Python imports of internal `workflow.py` symbols are contractual unless surfaced by executable tests or repository references during implementation.
- The later class-based state-machine change remains separate.

# Risks / Follow-Ups

- Circular imports and hidden module-global coupling are the primary extraction risks.
- Runtime package files must be synchronized as a complete inventory across live, canonical, and distributed locations.
- Implementation must avoid opportunistic semantic cleanup and use the named failing-first behavior tests.

# Raw Logs (none)

None.
