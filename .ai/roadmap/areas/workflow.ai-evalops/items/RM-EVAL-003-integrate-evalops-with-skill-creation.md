---
id: RM-EVAL-003
title: Integrate EvalOps With Skill Creation
status: planned
stage: v2
priority: p2
order: 30
depends_on:
  - RM-EVAL-001
openspec_change: null
created_at: 2026-06-13
started_at: null
completed_at: null
patches: []
---

# Goal

Ensure new skill creation workflows create or prompt for EvalOps target workspaces before treating a skill as ready.

# Scope

## In

- Update `skill-creator` behavior to mention `.ai/evals/targets/skill.<name>/`.
- Prompt for coverage draft creation during new skill creation.
- Generate candidate eval cases after user-reviewed coverage.
- Preserve the rule that golden promotion requires explicit user confirmation.

## Out

- Automatic golden promotion.
- Promptfoo full eval on every small skill draft iteration.

# Acceptance Criteria

- Creating a new skill no longer only creates `SKILL.md`; it also routes or prompts for EvalOps assets.
- Generated cases enter inbox first.
- User confirmation is required before any golden case is created.

# Promotion Notes

Promote after RM-EVAL-001 stabilizes EvalOps target workspace contracts.

# Completion Notes

<filled when the item is marked done>
