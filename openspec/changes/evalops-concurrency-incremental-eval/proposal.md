## Why

Promptfoo golden eval currently runs all cases serially, taking 10+ minutes as case counts grow. The EvalOps workflow needs faster iteration without losing the ability to run full regression gating when required.

## What Changes

- Add `max_concurrency` and `max_parallel_models` to `.ai/evals/model-matrix.yaml` `run_policy`
- `run-promptfoo-eval.py` reads concurrency config and passes it to `promptfoo eval --max-concurrency N`
- `run-eval-matrix.py` supports parallel model entries via `concurrent.futures` when `parallel: true`
- `--only-new` flag for running only golden cases changed since the last full run (Git diff against last full run baseline)
- `--only-failed --failed-from latest|full` for retrying only previously failed cases
- Run index (`reports/run-index.json`) tracking run mode, Git baseline, per-case run status, and failures
- New defaults: `max_concurrency: 3`, `parallel: true`, `max_parallel_models: 2` in templates
- Existing configs without new fields continue working with safe fallback behavior

## Capabilities

### New Capabilities
- `evalops-run-concurrency`: Config-driven concurrency for both Promptfoo case parallelism and matrix model parallelism
- `evalops-incremental-eval`: `--only-new` and `--only-failed` incremental run modes backed by a run index tracking each run's Git baseline, case state, and failure set

### Modified Capabilities
- `sdlc-evalops`: Eval Runner Script requirement changes from hardcoded `--max-concurrency 1` to configurable concurrency; Eval Matrix Runner requirement adds parallel model execution with `max_parallel_models` cap

## Impact

- `skills/sdlc-evalops/scripts/run-promptfoo-eval.py` — concurrency config, `--only-new`, `--only-failed`, run index
- `skills/sdlc-evalops/scripts/run-eval-matrix.py` — parallel model execution via `ThreadPoolExecutor`
- `skills/sdlc-evalops/templates/model-matrix.yaml` — new `run_policy` defaults
- `.ai/evals/model-matrix.yaml` — live instance updated to new defaults
- `skills/sdlc-evalops/SKILL.md` — document new flags, config, and run index
- `tests/test_evalops_root.py`, `tests/test_evalops_skill.py` — concurrency and incremental eval coverage
