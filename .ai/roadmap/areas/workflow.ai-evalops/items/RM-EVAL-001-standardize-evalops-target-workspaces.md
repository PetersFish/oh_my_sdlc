---
id: RM-EVAL-001
title: Standardize EvalOps Target Workspaces
status: ready
stage: mvp
priority: p0
order: 10
depends_on: []
openspec_change: standardize-ai-evalops-target-workspaces
created_at: 2026-06-13
started_at: null
completed_at: null
patches: []
---

# Goal

Standardize AI EvalOps assets around target-scoped workspaces under `.ai/evals/`, and make `skill.sdlc-orchestrator` the reference target for canonical cases, Promptfoo exports, and eval reports.

# Scope

## In

- Migrate root `evals/` assets to `.ai/evals/`.
- Introduce `.ai/evals/manifest.yaml` as the global eval target registry and default policy surface.
- Introduce `.ai/evals/model-matrix.yaml` schema for future multi-model validation.
- Introduce `.ai/evals/templates/`, `.ai/evals/schemas/`, `.ai/evals/runners/`, and `.ai/evals/targets/<target-id>/`.
- Migrate `skill.sdlc-orchestrator` assets into `.ai/evals/targets/skill.sdlc-orchestrator/`.
- Update `sdlc-evalops` to define canonical internal cases and derived Promptfoo exports in the new layout.
- Update `sdlc-orchestrator` to make new AI skill development route through EvalOps coverage, user-approved golden cases, implementation, and final golden eval.
- Add `scripts/export-promptfoo.py` for generating Promptfoo exports from canonical golden cases.
- Add export contract tests for Promptfoo prompt injection, case count, no global assertion pollution, and no unconfigured `llm-rubric`.

## Out

- Full implementation of a multi-model matrix runner.
- CI integration.
- Changes to `skill-creator`.
- Changes to `meta-skill-lifecycle-governance`.
- Long-term dual-write compatibility between old root `evals/` and new `.ai/evals/`.

# Acceptance Criteria

- `.ai/evals/targets/skill.sdlc-orchestrator/` contains `manifest.yaml`, `coverage.yaml`, `cases/`, `exports/`, and `reports/`.
- Old root `evals/` assets are migrated to `.ai/evals/` and no long-term duplicate source of truth remains.
- `scripts/export-promptfoo.py skill.sdlc-orchestrator --check` detects stale Promptfoo exports.
- Promptfoo exports are generated from canonical golden cases and inject the target skill source.
- `sdlc-orchestrator` and `sdlc-evalops` document the new workflow boundaries and human-confirmation gates.
- Local tests pass.
- `skill.sdlc-orchestrator` Promptfoo golden eval passes 6/6 after migration.

# Promotion Notes

Generate OpenSpec change using change id: `standardize-ai-evalops-target-workspaces`.

Key decisions confirmed:
- Use `.ai/evals/` as EvalOps root.
- Keep `targets/` as the target workspace namespace.
- Use non-underscored platform directories: `templates/`, `schemas/`, `runners/`.
- Implement `export-promptfoo.py` in this batch.
- Define model matrix schema in this batch, but defer the full runner.
- Defer `skill-creator` and `meta-skill-lifecycle-governance` integration to later roadmap items.

# Completion Notes

<filled when the item is marked done>
