## Context

EvalOps stores canonical target assets under `.ai/evals/targets/<target-id>/`. The current `scripts/export-promptfoo.py` derives a single Promptfoo export from golden cases and the first model entry in `.ai/evals/model-matrix.yaml`, while `scripts/run-promptfoo-eval.py` runs that single generated export and writes one target-scoped report.

RM-EVAL-001 intentionally defined the model matrix schema before building the matrix runner. RM-EVAL-002 fills that deferred gap: execute target golden cases across configured model entries and write grouped reports without changing canonical case files or making CI part of the MVP.

## Goals / Non-Goals

**Goals:**

- Add `scripts/run-eval-matrix.py` for target golden evals across configured model entries.
- Support explicit target selection and default target selection from `.ai/evals/model-matrix.yaml`.
- Generate per-model run directories and summaries under each target workspace.
- Generate an aggregate matrix summary for the run.
- Preserve the existing single-model runner and export freshness behavior.
- Record provider/model metadata from generated config and available Promptfoo output to avoid label drift.

**Non-Goals:**

- CI integration.
- Advanced analytics, scoring, ranking, trend history, or dashboard output.
- Running inbox/accepted cases; only golden cases are in scope.
- Managing API keys beyond existing `apiKeyEnvar` behavior.
- Adding a long-lived `.ai/evals/templates/`, `.ai/evals/schemas/`, or `.ai/evals/runners/` runtime directory.

## Decisions

### Decision 1: Matrix runner is a separate script

Add `scripts/run-eval-matrix.py` instead of expanding `run-promptfoo-eval.py` with matrix modes.

Rationale: the single-target runner has a clear contract: export once, run once, write one report. Matrix execution needs nested loops, per-model config generation, aggregate summaries, and partial-failure handling. Keeping it separate avoids overloading the existing script and keeps RM-EVAL-001 behavior stable.

Alternative considered: add `--matrix` to `run-promptfoo-eval.py`. Rejected because it would mix two reporting contracts in one command and make failures harder to interpret.

### Decision 2: Generate ephemeral per-model Promptfoo config inside reports

For each target/model pair, the matrix runner will generate a run-scoped Promptfoo directory under `.ai/evals/targets/<target-id>/reports/<matrix-run-id>/<model-name>/promptfoo/`.

Rationale: the canonical `exports/promptfoo/` directory remains the default-model export used by `export-promptfoo.py --check`. Matrix runs should not mutate canonical exports for every model, because doing so would make freshness checks and ordinary runs noisy.

Alternative considered: rewrite `.ai/evals/targets/<target-id>/exports/promptfoo/` before each model. Rejected because it would cause label drift and interfere with default export freshness.

### Decision 3: Reuse export mapping behavior, but parameterize provider/grader

The matrix runner should reuse or mirror the existing export mapping from canonical golden cases to Promptfoo cases, while taking the provider and grader from the current model matrix entry rather than always using the first model.

Rationale: matrix runs must grade the same canonical cases as normal runs. Differences should come from provider/model config, not from different prompt or assertion generation.

Alternative considered: shell out to `export-promptfoo.py` repeatedly with a temporary edited model matrix. Rejected because it would mutate source files or require brittle temp overlays.

### Decision 4: Partial failures do not abort the whole matrix by default

The runner will honor `run_policy.fail_fast`; default behavior is to continue after a model failure and record that model as failed/error.

Rationale: the point of matrix runs is comparison. One broken provider should not prevent reports for other providers unless fail-fast is explicitly enabled.

Alternative considered: always stop on first failure. Rejected because it loses diagnostic value and conflicts with the current `fail_fast: false` matrix policy.

### Decision 5: Report both configured and observed provider metadata

Each per-model summary should include configured metadata from `model-matrix.yaml` (`name`, `provider`, `model`, `promptfoo.id`, `label`) and observed metadata when available from generated config or Promptfoo JSON output.

Rationale: provider names can drift when configs are copied or labels change. Reporting both makes it clear what was requested and what actually ran.

Alternative considered: report only configured `models[].name`. Rejected because RM-EVAL-002 explicitly calls out avoiding label drift.

## Risks / Trade-offs

- Promptfoo output JSON shape may vary by version -> parse defensively and fall back to configured metadata.
- Multiple model entries increase run time and cost -> keep sequential execution by default and report the exact model count before running.
- Reusing export logic may duplicate some code initially -> keep duplication small, and refactor shared helpers only when it reduces risk.
- Per-model report directories can grow quickly -> out of scope for this change; report retention is governed by existing EvalOps report policy.
- Provider failures may be caused by credentials or endpoint compatibility -> record stderr/stdout snippets and exit non-zero if any model fails.

## Migration Plan

1. Add the matrix runner without changing existing single-target runner behavior.
2. Add tests that validate matrix config generation and report paths without requiring live provider calls.
3. Update `sdlc-evalops` docs and distributed copies.
4. Optionally run a small live matrix using available opencode-go credentials; if unavailable, report the blocked credential dependency.

Rollback is to remove `scripts/run-eval-matrix.py` and revert documentation/tests. Existing `export-promptfoo.py` and `run-promptfoo-eval.py` remain unaffected.

## Open Questions

None for MVP. Parallel execution and CI integration remain deferred.
