---
id: RM-EVAL-002
title: Add Eval Matrix Runner
status: planned
stage: v2
priority: p1
order: 20
depends_on:
  - RM-EVAL-001
openspec_change: null
created_at: 2026-06-13
started_at: null
completed_at: null
patches: []
---

# Goal

Add a runner that executes target golden evals across a configured model matrix and records per-model reports.

# Scope

## In

- Implement `scripts/run-eval-matrix.py`.
- Read `.ai/evals/model-matrix.yaml`.
- Run Promptfoo for each configured provider/model.
- Record observed provider/model from raw outputs to avoid label drift.
- Generate per-target and per-model summaries.

## Out

- CI integration.
- Model performance analytics beyond pass/fail and basic counts.

# Acceptance Criteria

- Runner can execute `skill.sdlc-orchestrator` against multiple opencode model configurations.
- Reports are grouped by target and model.
- Summary shows pass/fail/error counts per model.

# Promotion Notes

Promote after RM-EVAL-001 establishes `.ai/evals/model-matrix.yaml` and target workspace layout.

# Completion Notes

<filled when the item is marked done>
