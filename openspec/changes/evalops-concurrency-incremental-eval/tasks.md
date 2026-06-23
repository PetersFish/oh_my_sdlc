## 1. Model-Matrix Config Updates

- [x] 1.1 Add `max_concurrency` and `max_parallel_models` fields to `skills/sdlc-evalops/templates/model-matrix.yaml` `run_policy` with defaults (`max_concurrency: 3`, `parallel: true`, `max_parallel_models: 2`)
- [x] 1.2 Update `.ai/evals/model-matrix.yaml` live instance `run_policy` with same new defaults
- [x] 1.3 Verify existing tests (`test_model_matrix_template_has_required_sections`, `test_model_matrix_has_required_fields`) still pass after template changes

## 2. Single-Target Runner Concurrency

- [x] 2.1 Add `model-matrix.yaml` loading to `run-promptfoo-eval.py` to read `run_policy.max_concurrency`
- [x] 2.2 Replace hardcoded `--max-concurrency 1` with the config value (default 1 when absent)
- [x] 2.3 Update `--max-concurrency` assertion in `test_runner_script_uses_max_concurrency` to verify config-driven behavior

## 3. Matrix Runner Parallel Execution

- [x] 3.1 Add `concurrent.futures.ThreadPoolExecutor` import and logic to `run-eval-matrix.py`
- [x] 3.2 When `run_policy.parallel` is true, submit model runs to `ThreadPoolExecutor(max_workers=run_policy.max_parallel_models)` instead of serial loop
- [x] 3.3 Handle fail-fast cancellation: when a model run fails and `fail_fast` is true, cancel remaining futures
- [x] 3.4 Preserve sequential execution path when `parallel` is false or absent
- [x] 3.5 Write aggregate run index entry after all parallel model runs complete (single-writer)

## 4. Run Index

- [x] 4.1 Define `run-index.json` schema: `target_id`, `runs[]` with `run_id`, `mode`, `git_baseline`, `case_files`, `case_status`, `failed_cases`, `report_path`, `timestamp`
- [x] 4.2 Implement `load_run_index()` and `save_run_index()` helpers shared between both runner scripts
- [x] 4.3 On each full run completion, append run entry with Git baseline (HEAD commit), case file set, per-case run status, and failure set
- [x] 4.4 On each `--only-new` or `--only-failed` run completion, append corresponding entry with selected case set, per-case run status, and failure set
- [x] 4.5 Run index lives at `.ai/evals/targets/<target-id>/reports/run-index.json` (local audit, not versioned)

## 5. Only-New Incremental Eval

- [x] 5.1 Add `--only-new` CLI flag to `run-promptfoo-eval.py`
- [x] 5.2 Add `--only-new` CLI flag to `run-eval-matrix.py`
- [x] 5.3 On `--only-new`, read last full run Git baseline from run index; exit with message if no baseline exists
- [x] 5.4 Run `git diff --name-only <baseline> -- <golden-dir>/` to identify changed golden case YAML files
- [x] 5.5 Export and run only the subset of golden cases whose files appear in the diff
- [x] 5.6 Exit cleanly with message when no changed golden case files are found
- [x] 5.7 Mark generated report summary with run mode "only-new"

## 6. Only-Failed Retry Eval

- [x] 6.1 Add `--only-failed` and `--failed-from` CLI flags to `run-promptfoo-eval.py`
- [x] 6.2 Add `--only-failed` and `--failed-from` CLI flags to `run-eval-matrix.py`
- [x] 6.3 Validate `--failed-from` accepts only `latest` or `full`; reject other values with clear error
- [x] 6.4 `--failed-from latest`: read most recent run entry from run index, rerun its `failed_cases`
- [x] 6.5 `--failed-from full`: read most recent full run entry, rerun its `failed_cases`
- [x] 6.6 Exit cleanly with message when referenced run has no failures or run index is missing
- [x] 6.7 Mark generated report summary with run mode "only-failed" and failure source (`latest` or `full`)

## 7. Report Summary Updates

- [x] 7.1 Add `Run Mode` field to `summary.md` output in `run-promptfoo-eval.py` and `run-eval-matrix.py`
- [x] 7.2 For `--only-failed` runs, also include `Failure Source` field (`latest` or `full`)

## 8. SKILL.md Documentation

- [x] 8.1 Document new `run_policy` fields (`max_concurrency`, `max_parallel_models`) in `sdlc-evalops` SKILL.md Promptfoo Provider Configuration section
- [x] 8.2 Document `--only-new` and `--only-failed --failed-from latest|full` flags in run steps
- [x] 8.3 Document run index at `reports/run-index.json` in directory structure and reports policy
- [x] 8.4 Distribute updated SKILL.md to all CLI copies (`.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`)

## 9. Tests

- [x] 9.1 Add test for `max_concurrency` and `max_parallel_models` fields in template and live model-matrix
- [x] 9.2 Add test for `--only-new` flag presence and behavior in runner scripts
- [x] 9.3 Add test for `--only-failed` and `--failed-from` flag presence in runner scripts
- [x] 9.4 Add test for run index creation and append on run completion, including per-case run status
- [x] 9.5 Add test for report summary including `Run Mode` field
- [x] 9.6 Add test verifying serial fallback when `parallel` is false
- [x] 9.7 Run full test suite: `python3 -m pytest tests/ -v` and verify all pass
- [ ] 9.8 Run live golden eval for `skill.sdlc-orchestrator` and verify pass/concurrency behavior
