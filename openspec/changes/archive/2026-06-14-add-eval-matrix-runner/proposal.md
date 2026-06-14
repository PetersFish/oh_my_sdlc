## Why

EvalOps now has target-scoped workspaces and a model matrix schema, but the current runner executes one target against only the default model provider. RM-EVAL-002 needs a matrix runner so golden evals can compare configured models without hand-editing Promptfoo exports or report paths.

## What Changes

- Add `scripts/run-eval-matrix.py` to execute one or more EvalOps targets across configured entries in `.ai/evals/model-matrix.yaml`.
- Generate per-model Promptfoo configs/reports without mutating the canonical model matrix or canonical case files.
- Store matrix run reports under target workspaces with per-target and per-model summaries.
- Record observed provider/model metadata from Promptfoo output or generated config to avoid report label drift.
- Update `sdlc-evalops` documentation and tests to describe the matrix runner boundary.
- No CI integration in this change.
- No analytics beyond pass/fail/error counts and basic run metadata.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sdlc-evalops`: Add matrix runner requirements for executing golden evals across configured model matrix entries and writing grouped reports.

## Impact

- Adds `scripts/run-eval-matrix.py`.
- May refactor small shared helpers from `scripts/export-promptfoo.py` or `scripts/run-promptfoo-eval.py` only if needed to avoid duplicated fragile logic.
- Reads `.ai/evals/manifest.yaml`, `.ai/evals/model-matrix.yaml`, and target workspace manifests.
- Writes matrix reports under `.ai/evals/targets/<target-id>/reports/`.
- Updates `skills/sdlc-evalops/SKILL.md` plus distributed `.opencode/`, `.claude/`, and `.cursor/` copies.
- Updates tests in `tests/test_evalops_root.py` and/or `tests/test_evalops_skill.py`.
