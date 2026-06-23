## Context

The EvalOps pipeline currently runs all golden cases serially through both `run-promptfoo-eval.py` and `run-eval-matrix.py`. `run-promptfoo-eval.py` hardcodes `--max-concurrency 1` and runs every golden case. `run-eval-matrix.py` iterates model entries in a sequential `for` loop. As the golden case corpus grows, full runs exceed 10 minutes, making iterative development slow.

The existing `model-matrix.yaml` `run_policy` block already defines `mode`, `fail_fast`, `timeout_seconds`, `retry_count`, and `parallel` fields but `parallel` is unused by the matrix runner. The single-target runner does not read `run_policy` at all.

## Goals / Non-Goals

**Goals:**
- Let `run_policy.max_concurrency` control Promptfoo per-target case parallelism
- Let `run_policy.parallel` and `run_policy.max_parallel_models` control matrix model parallelism
- Add `--only-new` that selects golden cases changed since the last full run, using Git diff against a recorded baseline stored in a run index
- Add `--only-failed --failed-from latest|full` for retrying failures from the most recent run or most recent full run
- Introduce `reports/run-index.json` as local audit state tracking each run's mode, Git baseline, case set, per-case run status, and failure set
- Adopt moderate new defaults: `max_concurrency: 3`, `parallel: true`, `max_parallel_models: 2`
- Preserve backward compatibility for existing configs that lack new `run_policy` fields

**Non-Goals:**
- Source-level impact analysis to auto-select affected cases
- Cross-target automatic case selection
- CI integration
- Modifications to the `promptfoo` tool itself
- Process-level parallelism beyond `ThreadPoolExecutor`

## Decisions

### Decision 1: Git diff for `--only-new` baseline, not mtime

**Rationale:** mtime is unreliable across `git checkout`, file copy, and tooling that touches file timestamps. Git diff against a recorded baseline commit or tree state is deterministic and reproducible.

**Alternatives considered:** mtime (rejected — noisy), content hash without Git (rejected — adds another state mechanism).

### Decision 2: Last full run snapshot as `--only-new` baseline

The run index records the Git baseline (HEAD commit or tree hash) at the time of each completed full run. `--only-new` diffs golden case files against that recorded baseline. This ties incremental eval to "last fully verified state" rather than branch topology.

**Alternative considered:** merge-base with main (rejected — not tied to eval history).

### Decision 3: `--failed-from latest|full` for `--only-failed`

`--only-failed` accepts a mandatory `--failed-from` argument with values `latest` (most recent run of any mode) and `full` (most recent full run). The run index stores the failure set per run, so both lookups are O(1) reads from the index.

### Decision 4: ThreadPoolExecutor for model parallelism

Each matrix model run is a subprocess call to `promptfoo eval` — primarily I/O-bound. `ThreadPoolExecutor` is sufficient and avoids the overhead of process pools. The `max_parallel_models` cap prevents unbounded parallelism.

**Alternative considered:** `ProcessPoolExecutor` (rejected — unnecessary for subprocess-based work).

### Decision 5: Moderate defaults over serial defaults

New templates and live instances default to `max_concurrency: 3`, `parallel: true`, `max_parallel_models: 2`. Existing configs that lack these fields use safe fallback values (concurrency 1, serial models). This gives faster out-of-box experience while keeping legacy configs unchanged.

### Decision 6: Run index schema

`reports/run-index.json` structure:

```json
{
  "target_id": "skill.sdlc-orchestrator",
  "runs": [
    {
      "run_id": "...",
      "mode": "full | only-new | only-failed",
      "git_baseline": "<commit or tree hash>",
      "case_files": {"<filename>": "<content hash>"},
      "case_status": {"<case-id>": "passed | failed | skipped | not_run"},
      "failed_cases": ["<case-id>", ...],
      "report_path": "reports/<run-id>/",
      "timestamp": "<ISO 8601>"
    }
  ]
}
```

## Risks / Trade-offs

- **Provider rate limiting:** Parallel case execution (3 concurrent) plus parallel model runs (2 models) can create up to 6 simultaneous requests to the opencode-go endpoint → Mitigation: `max_concurrency` and `max_parallel_models` are user-configurable caps.
- **Git dependency for `--only-new`:** Non-Git environments cannot use `--only-new` → Mitigation: script exits with a clear message instructing the user to run a full eval first. The run index still records full runs even without a Git baseline.
- **Run index drift:** The run index is a local file not version-controlled → Acceptable because it is audit state, not canonical source.
- **Thread safety of run index writes:** Multiple model runs finishing concurrently could race on run index updates → Mitigation: single-writer pattern — the matrix runner writes the aggregate entry after all model runs complete.
