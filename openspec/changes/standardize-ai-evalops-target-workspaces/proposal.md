## Why

EvalOps assets currently live in a root `evals/` layout that was sufficient for one target, but it does not provide a stable namespace for multiple AI behavior targets, target-specific manifests, canonical-vs-derived artifacts, or future multi-model validation. This creates ambiguity about where golden cases, Promptfoo exports, reports, and target metadata should live.

Roadmap item `RM-EVAL-001` promotes a standardized EvalOps foundation: `.ai/evals/` becomes the EvalOps root, target-scoped workspaces live under `.ai/evals/targets/`, and `skill.sdlc-orchestrator` becomes the reference target for canonical cases, Promptfoo exports, and eval reports.

## What Changes

- Move the EvalOps source of truth from root `evals/` into `.ai/evals/` without long-term dual-write compatibility.
- Define `.ai/evals/manifest.yaml` as the global target registry and default policy surface.
- Define `.ai/evals/model-matrix.yaml` schema for future multi-model validation while deferring the full matrix runner.
- Standardize platform directories as `.ai/evals/templates/`, `.ai/evals/schemas/`, and `.ai/evals/runners/`.
- Standardize target workspaces under `.ai/evals/targets/<target-id>/` with target manifests, coverage, canonical cases, derived exports, and reports.
- Make `.ai/evals/targets/skill.sdlc-orchestrator/` the reference target workspace.
- Add `scripts/export-promptfoo.py` to generate Promptfoo exports from canonical golden cases and support freshness checks with `--check`.
- Generate Promptfoo prompts by injecting the target skill source into the prompt context instead of duplicating skill text in cases.
- Prohibit global assertion pollution: assertions belong in canonical cases or target policy, not shared global Promptfoo defaults that silently affect unrelated targets.
- Prefer deterministic assertions and prohibit unconfigured `llm-rubric` assertions.
- Update `sdlc-evalops` behavior for target workspaces, session-vs-Promptfoo eval boundaries, reports policy, and model matrix schema.
- Update `sdlc-orchestrator` behavior for new AI skill development flow, EvalOps gates, human confirmation boundaries, and final golden eval reporting.

## Capabilities

### New Capabilities

- `sdlc-evalops`: Target-scoped EvalOps workspace management, canonical case handling, Promptfoo export generation, reports policy, and model matrix schema.

### Modified Capabilities

- `sdlc-orchestrator`: AI behavior changes and new AI skill development route through EvalOps coverage, human-approved golden cases, implementation, final golden eval execution, and summary reporting.

## Impact

- Affected OpenSpec capabilities: `sdlc-evalops`, `sdlc-orchestrator`
- Affected canonical skill sources: `skills/sdlc-evalops/SKILL.md`, `skills/sdlc-orchestrator/SKILL.md`
- Affected distributed skill copies: `.opencode/skills/sdlc-evalops/`, `.claude/skills/sdlc-evalops/`, `.cursor/skills/sdlc-evalops/`, plus matching `sdlc-orchestrator` copies
- Affected EvalOps assets: root `evals/` migrated into `.ai/evals/`, especially `skill.sdlc-orchestrator`
- New script: `scripts/export-promptfoo.py`
- New schemas: `.ai/evals/schemas/` and `.ai/evals/model-matrix.yaml` schema contract
- Deferred work: full model matrix runner, CI integration, `skill-creator` integration, and `meta-skill-lifecycle-governance` integration
