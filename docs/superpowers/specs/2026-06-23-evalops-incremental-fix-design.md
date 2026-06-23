# Fix: evalops-concurrency-incremental-eval 实现对齐 spec/design

## Context

Review of commit `e4bd5aa` (evalops-concurrency-incremental-eval) found 6 issues where
implementation diverges from the OpenSpec specs and design:

1. `--only-new` path comparison broken: `get_changed_golden_files()` returns absolute
   paths, compared against filename-only `_file`.
2. `--only-failed` can't replay: run index stores synthetic keys (`case-0`) or input
   preview snippets, not canonical case ids.
3. `run-index.json` content doesn't match design schema: `case_files` is empty, `case_status`
   uses `model_name:input_preview` keys, `failed_cases` has input previews.
4. Single runner ignores `selected_cases` after computing it; always runs full canonical
   export and full `promptfooconfig.yaml`.
5. Matrix parallel fail-fast can crash on cancelled-future `result()` and doesn't write
   aggregate summary for cancelled runs.
6. Tests are string-presence checks only; no behavioral coverage of incremental paths.

## Goals / Non-Goals

**Goals:**
- Make `--only-new` actually select changed golden cases and run only those.
- Make `--only-failed --failed-from latest|full` replay by canonical case ids.
- Make `run-index.json` persistent, replayable, and match the design schema.
- Make parallel fail-fast write summaries for all completed/cancelled runs without crash.
- Add behavioral tests covering the new selection and index paths.
- Keep changes minimal: no new dependencies, no layout changes.

**Non-Goals:**
- Full library extraction of EvalOps runtime.
- CI integration.
- Cross-target case selection.
- Source-level impact analysis beyond `git diff`.

## Decisions

### Case identity

Golden YAML files already have `id` fields. Treat `id` as the stable canonical case identity.

`case_files` in run index maps `case_id -> {file, hash}` where:
- `file` is the golden YAML filename (not path).
- `hash` is `sha256` of the file content.

`case_status` maps `case_id -> passed|failed|skipped|not_run`.

`failed_cases` is `[case_id]`.

### Only-new: path normalization

`get_changed_golden_files()` normalizes `git diff --name-only` output to filenames only
by extracting `os.path.basename`. The comparison against `_file` then matches.

### Only-failed: id-based lookup

`failed_cases` stores real case ids. `--only-failed` filters golden cases by `case["id"] in failed_ids`.
If a failed id no longer exists in golden/, skip it with a warning.

### Single runner subset export

For `--only-new` and `--only-failed`, the single runner generates a run-scoped Promptfoo
config under `reports/<run-id>/promptfoo/` containing only the selected cases. The
canonical `exports/promptfoo/` is NOT modified for incremental runs.

For full runs (no `--only-*` flags), canonical export path is used as before.

### Matrix runner

The matrix runner already generates per-model-per-run Promptfoo configs under
`reports/<matrix-run-id>/<model-name>/promptfoo/`. It needs only:
- Fixed `selected_cases` propagation (case selection already feeds into `run_single_model`).
- Fixed run-index entry building (use case ids, not input previews).

### Fail-fast with ThreadPoolExecutor

- Submit all futures.
- On first failure with `fail_fast`, collect results from already-completed futures,
  then cancel remaining (unstarted) futures.
- Handle `CancelledError` from cancelled futures: do NOT call `result()`; instead record
  them as "cancelled" in model results. This means the aggregation loop needs to
  distinguish done vs cancelled futures differently than `as_completed()`.

Implementation: iterate `concurrent.futures.as_completed()` with a timeout placeholder,
or use a two-phase gather: collect done, cancel rest, then process only done.

### Matrix `case_status` aggregation

When the same case runs against N model entries, aggregate status:
- If ALL model runs pass: `passed`
- If ANY model run fails: `failed`
- If no model runs exercised this case: `not_run`

This avoids ambiguous per-model status keys in the run index.

### Shared selection module

Add `case_selection.py` under `skills/sdlc-evalops/scripts/` containing:
- `prepare_only_new()` — returns selected cases or exits with message.
- `prepare_only_failed()` — returns selected cases or exits with message.
- `get_case_identity()` — returns `(case_id, file_name, content_hash)` for a case dict.
- `collect_case_files()` — builds the `case_files` dict from selected cases.

Imported by both `run-promptfoo-eval.py` and `run-eval-matrix.py` to avoid drift.

### Tests

New behavioral tests, in a new file or an existing test file, that:
1. Create a temporary `.ai/evals/targets/<test-target>/` with golden cases, run index, and
   fake Promptfoo output JSON.
2. Monkeypatch `subprocess.run` to return pre-canned output.
3. Exercise `prepare_only_new()`, `prepare_only_failed()`, `build_run_entry()`,
   `get_changed_golden_files()` path normalization.
4. Exercise matrix fail-fast: submit 3 model futures, make first fail, verify remaining
   are cancelled and aggregate summary is written.
5. Verify run-index entries contain real `case_files`, `case_status`, `failed_cases`.

Existing string-presence tests remain but are not the primary acceptance criteria.

## Data Flow

```
--only-new:
  run-index.json --(last full baseline)--> git diff --name-only
  --(changed filenames)--> case_selection.prepare_only_new()
  --(selected case dicts)--> generate run-scoped promptfoo config
  --(promptfoo eval)--> parse output
  --(case_status, failed_cases)--> build_run_entry() --> save_run_index()

--only-failed:
  run-index.json --(last run's failed_cases[])--> case_selection.prepare_only_failed()
  --(selected case dicts by id)--> generate run-scoped promptfoo config
  --(promptfoo eval)--> parse output
  --(case_status, failed_cases)--> build_run_entry() --> save_run_index()
```

## Files to Modify

| File | Change |
|------|--------|
| `skills/sdlc-evalops/scripts/case_selection.py` | NEW: shared selection + identity helpers |
| `skills/sdlc-evalops/scripts/run_index.py` | Fix `get_changed_golden_files()` to return basenames |
| `skills/sdlc-evalops/scripts/run-promptfoo-eval.py` | Use case_selection; generate run-scoped subset config for incremental runs; fix run-index entry |
| `skills/sdlc-evalops/scripts/run-eval-matrix.py` | Fix fail-fast loop; fix run-index entry building; use case_selection for identity |
| `tests/test_evalops_incremental.py` | NEW: behavioral tests for selection, run-index content, fail-fast |
| `tests/test_evalops_root.py` | Existing; no changes needed (string-presence tests remain valid but not sufficient) |
| `skills/sdlc-evalops/SKILL.md` | Document `case_selection.py` in script list (if needed) |

## Risks

- `case["id"]` must exist in all golden YAML files for `--only-failed` replay. If missing,
  `prepare_only_failed()` will skip and warn. Existing golden cases all have `id`.
- Fail-fast still cannot kill already-started Promptfoo subprocesses; this is consistent
  with the design doc's acceptance of `ThreadPoolExecutor` limitations.
- Path normalization by basename only works if golden case filenames are unique across
  the repository. Current layout satisfies this.
