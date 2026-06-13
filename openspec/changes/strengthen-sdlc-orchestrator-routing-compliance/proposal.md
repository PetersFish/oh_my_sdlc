## Why

The SDLC orchestrator currently classifies routes correctly but does not bind subsequent actions tightly enough to the selected route. This allows a `spec-driven-propose-flow` decision to drift into direct execution when the user says "execute plan", weakening governance for cross-skill or AI-behavior changes.

## What Changes

- Strengthen `sdlc-orchestrator` so route decisions constrain the next action, not just describe a recommendation.
- Require `spec-driven-propose-flow` to continue through `openspec-propose` unless the user explicitly opts out of OpenSpec governance.
- Require `spec-driven-incremental-flow` to continue through `openspec-new-change` unless the user explicitly opts out of OpenSpec governance.
- Add Plan Mode handoff rules so the final Plan Mode message matches the selected route.
- Add an execution-path choice rule: when mutually exclusive execution paths are available, use the `question` tool if available instead of relying only on free-text choices.
- Add a rule for ambiguous commands like "execute plan" after a prior `spec-driven-*` route decision: continue the route or ask for explicit opt-out, but do not silently direct-execute.
- Add EvalOps coverage and golden regression cases for `skill.sdlc-orchestrator` so instruction-following behavior can be regression-tested instead of relying only on manual review.

## Capabilities

### New Capabilities

### Modified Capabilities
- `sdlc-orchestrator`: Route decisions must be action-binding, Plan Mode handoffs must align with the selected route, and ambiguous execution requests after `spec-driven-*` routing must not bypass OpenSpec without explicit user opt-out.

## Impact

- Affected skill: `skills/sdlc-orchestrator/SKILL.md`
- Affected distributed copies: `.opencode/skills/sdlc-orchestrator/SKILL.md`, `.claude/skills/sdlc-orchestrator/SKILL.md`, `.cursor/skills/sdlc-orchestrator/SKILL.md`
- Affected specs/tests: `openspec/specs/sdlc-orchestrator/spec.md`, `tests/` coverage for orchestrator content if present or newly added, and EvalOps assets under `evals/`
- New EvalOps target: `skill.sdlc-orchestrator`
- New EvalOps assets: coverage matrix, target index entry, golden cases for route binding and execution-path behavior, and derived Promptfoo export/run artifacts during verification
- No runtime data model, `.ai/memory/`, OpenSpec schema, or CLI dependency changes
