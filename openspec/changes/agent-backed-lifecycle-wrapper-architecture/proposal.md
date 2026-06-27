## Why

The current `sdlc-orchestrator` directly names concrete workers (OpenSpec, Superpowers, Roadmap, Memory, EvalOps), coupling the workflow model to today's implementation choices. Without a wrapper boundary, replacing any module risks changing workflow phases, orchestration instructions, and governance logic together. A stable agent-backed wrapper layer lets implementations evolve independently of lifecycle governance.

## What Changes

- Introduce `dev-orchestrator` as a routing coordinator that dispatches phase actions to specialized agents (`plan-agent`, `implement-agent`, `test-agent`, `review-agent`, `finish-agent`) via stable module-level wrapper contracts
- Define two explicit flow types: `spec-flow` for OpenSpec-governed changes and `lightweight-flow` for changes that need planning, implementation, verification, review, and finish without a formal OpenSpec change
- Define TDD as a cross-cutting discipline: `plan-agent` plans TDD tasks, `implement-agent` executes red/green loops, `test-agent` performs independent verification/debug/regression/EvalOps capture
- Keep `workflow.py` as the deterministic owner of state transitions, hooks, and gates; agents handle worker dispatch and evidence normalization
- Map current OpenSpec, Superpowers, Roadmap, Memory, and EvalOps skills as wrapped backends behind agent-facing contracts
- Add provider-configurable wrapper routing so spec and memory backends can be selected from configuration rather than hardcoded in prompts or workflow phases
- Move safe parallel dispatch to `dev-orchestrator` to avoid nested subagent orchestration limits
- Preserve current user-visible workflow behavior during the first migration

## Capabilities

### New Capabilities

- `dev-orchestrator-agent-routing`: Routing coordinator that selects the specialized agent for the current allowed phase action, optionally splits safe parallel work packages, collects structured evidence, and returns normalized results to the workflow runtime
- `agent-contracts`: Fixed input/output contracts for plan-agent, implement-agent, test-agent, review-agent, and finish-agent, including phase-agent mappings, evidence keys, exit criteria, and failure modes
- `flow-type-routing`: Explicit `flow_type: spec-flow | lightweight-flow` field in workflow run state with per-flow agent routing rules and behavior differences
- `wrapper-contracts`: Module-level wrapper contracts for spec, memory, roadmap, eval, and verification modules that normalize agent/tool output into workflow evidence
- `provider-configurable-wrapper-routing`: Configurable provider selection for wrapper-backed modules, including `spec.provider` and `memory.provider`, defaults, capability mapping, and fail-closed behavior for unknown or unsupported providers

### Modified Capabilities

- `sdlc-orchestrator`: Orchestrator SHALL route phase actions through dev-orchestrator agent system instead of directly invoking concrete workers; orchestrator remains the policy and user-interaction layer

## Impact

- Affected code: `skills/sdlc-orchestrator/SKILL.md`, `.ai/workflows/definitions/sdlc-main.yaml`, `.ai/workflows/scripts/workflow.py`
- Affected specs: `openspec/specs/sdlc-orchestrator/spec.md` (delta), `openspec/specs/sdlc-workflow-engine/spec.md` (delta)
- New dependencies: wrapper contract document, phase-agent mapping configuration, provider configuration schema/registry for wrapper-backed modules
- No changes to: `skills/sdlc-roadmap/`, `skills/sdlc-repository-memory-*`, `skills/sdlc-evalops/`, OpenSpec skills, Superpowers skills (they remain wrapped backends)
