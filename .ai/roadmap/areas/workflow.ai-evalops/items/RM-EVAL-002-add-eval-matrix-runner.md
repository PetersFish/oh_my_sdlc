---
id: RM-EVAL-002
title: Add Eval Matrix Runner
status: done
stage: v2
priority: p1
order: 20
depends_on:
  - RM-EVAL-001
openspec_change: add-eval-matrix-runner
created_at: 2026-06-13
started_at: 2026-06-14
completed_at: 2026-06-14
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

OpenSpec change `add-eval-matrix-runner` archived 2026-06-14.

**Completed:**
- `scripts/run-eval-matrix.py` with CLI, manifest/model matrix loading, target/model resolution.
- Per-model run-scoped Promptfoo config generation under reports (canonical exports preserved).
- Per-model `summary.md`/`failures.yaml` and aggregate matrix summary with configured + observed metadata.
- `run_policy.fail_fast` honored; non-zero exit on failures.
- Matrix Eval section added to `sdlc-evalops` SKILL.md; distributed to all CLI copies.
- 12 new tests in `TestEvalMatrixRunner`; 116/116 pytest pass.
- Live matrix eval for `skill.sdlc-orchestrator`: 6/6 pass (3m7s).

**Deferred:**
- CI integration.
- Model performance analytics beyond pass/fail counts.
