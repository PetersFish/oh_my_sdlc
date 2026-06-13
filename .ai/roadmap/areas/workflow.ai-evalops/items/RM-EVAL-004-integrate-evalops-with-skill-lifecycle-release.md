---
id: RM-EVAL-004
title: Integrate EvalOps With Skill Lifecycle Release
status: planned
stage: v3
priority: p2
order: 40
depends_on:
  - RM-EVAL-001
openspec_change: null
created_at: 2026-06-13
started_at: null
completed_at: null
patches: []
---

# Goal

Make skill lifecycle release and distribution workflows enforce EvalOps release gates for AI behavior targets.

# Scope

## In

- Update `meta-skill-lifecycle-governance` to reference `.ai/evals/targets/<target-id>/`.
- Require golden eval during EVALUATE-IN-REPO.
- Require critical golden pass before RELEASE.
- Check release summaries before DISTRIBUTE.

## Out

- CI provider-specific implementation.
- Full model matrix runner implementation if not already completed by RM-EVAL-002.

# Acceptance Criteria

- Release-bound skills cannot skip critical golden evals silently.
- Release summaries are traceable to `.ai/evals/targets/<target-id>/reports/`.
- Distribution guidance reports eval status and unresolved failures.

# Promotion Notes

Promote after RM-EVAL-001 and, ideally, RM-EVAL-002 provide stable target workspace and matrix runner primitives.

# Completion Notes

<filled when the item is marked done>
