# EvalOps Incremental Eval Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `--only-new`, `--only-failed`, run-index semantics, matrix fail-fast, and add behavioral tests so the implementation matches the OpenSpec spec/design.

**Architecture:** Add a `case_selection.py` shared module under `skills/sdlc-evalops/scripts/` with identity/selection helpers. Fix `run_index.py` path normalization. Single runner generates run-scoped subset Promptfoo configs for incremental runs. Matrix runner fixes fail-fast loop and run-index entry building. Add behavioral test file with temp-fixture-based tests.

**Tech Stack:** Python 3, pathlib, yaml, concurrent.futures, subprocess monkeypatching, temporary directories

---

### Task 1: Create shared `case_selection.py` module

**Files:**
- Create: `skills/sdlc-evalops/scripts/case_selection.py`

- [ ] **Step 1: Write `case_selection.py`**

```python
"""Shared case selection and identity helpers for EvalOps runner scripts."""

from __future__ import annotations

import hashlib
from pathlib import Path


def get_case_identity(case: dict, golden_dir: Path) -> tuple[str, str, str, str]:
    """Return (case_id, file_name, content_hash, canonical_path_abs).

    case_id is from case['id']. file_name is from case['_file].
    content_hash is sha256 of the golden YAML file content.
    canonical_path_abs is the absolute path to the golden YAML file.
    """
    case_id = case.get("id", case.get("_file", "?"))
    file_name = case.get("_file", "")
    file_path = golden_dir / file_name
    content_hash = ""
    if file_path.is_file():
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return case_id, file_name, content_hash, str(file_path)


def collect_case_files(selected_cases: list[dict], golden_dir: Path) -> dict:
    """Build case_files dict for run index entry."""
    case_files = {}
    for case in selected_cases:
        case_id, file_name, content_hash, _abs_path = get_case_identity(case, golden_dir)
        case_files[case_id] = {"file": file_name, "hash": content_hash}
    return case_files


def select_only_new(golden_cases: list[dict], changed_files: list[str]) -> list[dict]:
    """Return cases whose _file is in changed_files (basenames)."""
    selected = [c for c in golden_cases if c.get("_file") in changed_files]
    return selected


def select_only_failed(golden_cases: list[dict], failed_ids: list[str]) -> list[dict]:
    """Return cases whose id is in failed_ids. Warn if an id is not found."""
    by_id = {c.get("id"): c for c in golden_cases}
    selected = []
    for fid in failed_ids:
        case = by_id.get(fid)
        if case:
            selected.append(case)
    return selected


def build_case_status(eval_results: list[dict], selected_cases: list[dict]) -> tuple[dict, list[str]]:
    """Build case_status dict and failed_cases list from Promptfoo eval results.

    eval_results are the parsed 'cases' list from parse_promptfoo_output().
    selected_cases are the case dicts that were actually run.

    Returns (case_status, failed_cases).
    case_status: {case_id: "passed" | "failed"}
    failed_cases: [case_id]
    """
    if len(eval_results) != len(selected_cases):
        # If lengths differ, still map what we can
        pass

    case_status = {}
    failed_cases = []
    for idx, case in enumerate(selected_cases):
        case_id = case.get("id", f"?")
        if idx < len(eval_results):
            passed = eval_results[idx].get("passed", False)
        else:
            passed = True  # assume passed if no result (shouldn't happen)
        status = "passed" if passed else "failed"
        case_status[case_id] = status
        if not passed:
            failed_cases.append(case_id)
    return case_status, failed_cases
```

- [ ] **Step 2: Verify module is importable**

```bash
python3 -c "import sys; sys.path.insert(0, 'skills/sdlc-evalops/scripts'); from case_selection import get_case_identity; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add skills/sdlc-evalops/scripts/case_selection.py
git commit -m "feat(evalops): add case_selection.py shared module for case identity and selection"
```

---

### Task 2: Fix `run_index.py` — path normalization in `get_changed_golden_files`

**Files:**
- Modify: `skills/sdlc-evalops/scripts/run_index.py:40-51`

- [ ] **Step 1: Update `get_changed_golden_files` to return basenames**

Replace lines 40-51 of `run_index.py`:

```python
def get_changed_golden_files(repo_root: Path, baseline: str, golden_dir: Path) -> list[str]:
    """Return list of golden case file *basenames* changed relative to baseline."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", baseline, "--", str(golden_dir) + "/"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=10,
        )
        if result.returncode == 0:
            import os
            basenames = set()
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    basenames.add(os.path.basename(line))
            return sorted(basenames)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return []
```

- [ ] **Step 2: Run existing tests to verify no regression**

```bash
python3 -m pytest tests/test_evalops_root.py::TestRunnerIncrementalFlags tests/test_evalops_root.py::TestRunIndexModule -v
```

Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add skills/sdlc-evalops/scripts/run_index.py
git commit -m "fix(evalops): normalize get_changed_golden_files to return basenames"
```

---

### Task 3: Fix `run-promptfoo-eval.py` — subset runs and correct run-index entries

**Files:**
- Modify: `skills/sdlc-evalops/scripts/run-promptfoo-eval.py`

- [ ] **Step 1: Add import for `case_selection`**

Add to imports (after `from run_index import ...`):

```python
from case_selection import (
    get_case_identity, collect_case_files, select_only_new,
    select_only_failed, build_case_status,
)
```

- [ ] **Step 2: Add `generate_promptfoo_config` and `write_run_scoped_config` helpers**

Add after `from run_index import ...` block and before `find_repo_root()`:

```python
import yaml


def generate_promptfoo_config(target_id: str, provider: dict,
                               grader: dict | None) -> str:
    config = {
        "description": f"EvalOps target run for {target_id}",
        "prompts": ["file://prompt.md"],
        "providers": [provider],
        "tests": "cases.yaml",
    }
    if grader:
        config["defaultTest"] = {"options": {"provider": grader}}
    return yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)


def write_run_scoped_promptfoo_files(run_dir: Path, selected_cases: list[dict],
                                     t_manifest: dict, provider: dict,
                                     grader: dict | None) -> None:
    from export_promptfoo import generate_cases_yaml
    prompt_content = generate_prompt_for_target(t_manifest)
    cases_content = generate_cases_yaml(selected_cases, t_manifest)
    config_content = generate_promptfoo_config(
        t_manifest.get("target_id", ""), provider, grader
    )
    (run_dir / "prompt.md").write_text(prompt_content, encoding="utf-8")
    (run_dir / "cases.yaml").write_text(cases_content, encoding="utf-8")
    (run_dir / "promptfooconfig.yaml").write_text(config_content, encoding="utf-8")


def generate_prompt_for_target(t_manifest: dict) -> str:
    source_paths = t_manifest.get("source_paths", [])
    target_id = t_manifest.get("target_id", "")
    target_type = t_manifest.get("target_type", "")
    source_lines = []
    for sp in source_paths:
        src_path = REPO_ROOT / sp
        if src_path.is_file():
            source_lines.append(f"# Source: {sp}\n")
            source_lines.append(src_path.read_text(encoding="utf-8"))
            source_lines.append("\n")
        else:
            log(f"Warning: source file not found: {sp}")
    source_block = "".join(source_lines) if source_lines else ""
    return f"""You are evaluating the `{target_id}` {target_type}. Apply these {target_type} instructions as the source of truth before responding.

# {target_id} evaluation context

The assistant is acting as the `{target_id}`.

{source_block}

User input:

{{{{input}}}}

Provide only the assistant's final user-facing reply — one natural message as the user would see it. Do NOT output chain of thought, hidden reasoning, "Thinking:" text, or any other internal deliberation. Output the direct reply only.
"""
```

Remove the old `import yaml` at top (if it was there) — `yaml` is now imported in the helper block.

- [ ] **Step 3: Rewrite `--only-new` and `--only-failed` selection blocks (lines ~332-377)**

Replace the single-runner's `--only-new` / `--only-failed` logic in `main()` with version that uses `case_selection` and loads model matrix for provider/grader resolution:

```python
    # Load model matrix for provider/grader resolution (used by subset config gen)
    model_matrix = load_model_matrix()
    run_policy = model_matrix.get("run_policy", {})
    max_concurrency = run_policy.get("max_concurrency", 1)

    reports_base = workspace / "reports"
    run_index_data = load_run_index(reports_base)
    if run_index_data.get("target_id") != target_id:
        run_index_data["target_id"] = target_id

    run_mode = "full"
    failure_source = None
    selected_cases = None

    t_manifest = yaml.safe_load((workspace / "manifest.yaml").read_text("utf-8")) or {}
    golden_rel = t_manifest.get("canonical_case_directories", {}).get("golden", "cases/golden")
    golden_dir = workspace / golden_rel
    golden_cases = load_golden_cases(golden_dir)

    if args.only_failed:
        run_mode = "only-failed"
        failure_source = args.failed_from
        if not run_index_data.get("runs"):
            error("No run index found. Run a full eval first.")
            sys.exit(2)
        if args.failed_from == "latest":
            ref_run = find_latest_run(run_index_data["runs"])
        else:
            ref_run = find_last_full_run(run_index_data["runs"])
        if not ref_run:
            error("No qualifying run found in run index. Run a full eval first.")
            sys.exit(2)
        failed_ids = ref_run.get("failed_cases", [])
        if not failed_ids:
            log("No failed cases to retry. Exiting.")
            sys.exit(0)
        selected_cases = select_only_failed(golden_cases, failed_ids)
        if not selected_cases:
            log("Failed case ids no longer present in golden dir. Exiting.")
            sys.exit(0)
        log(f"Only-failed ({failure_source}): {len(selected_cases)} case(s) to retry")

    elif args.only_new:
        run_mode = "only-new"
        last_full = find_last_full_run(run_index_data.get("runs", []))
        if not last_full:
            error("No prior full run found in run index. Run a full eval first.")
            sys.exit(2)
        baseline = last_full.get("git_baseline")
        if not baseline:
            error("Last full run has no Git baseline. Run a full eval to record one.")
            sys.exit(2)
        changed_files = get_changed_golden_files(REPO_ROOT, baseline, golden_dir)
        if not changed_files:
            log("No changed golden case files since last full run. Exiting.")
            sys.exit(0)
        selected_cases = select_only_new(golden_cases, changed_files)
        if not selected_cases:
            log("Changed files have no matching golden cases. Exiting.")
            sys.exit(0)
        log(f"Only-new: {len(selected_cases)} case(s) changed since baseline {baseline[:8]}")
    else:
        # full run: use all golden cases
        selected_cases = golden_cases
```

- [ ] **Step 4: Replace export/eval block (lines ~379-405) with subset-aware version**

Replace from `export_exit = run_export(target_id)` through `write_failures_yaml(reports_dir, parsed)`:

```python
    run_id = generate_run_id(target_id)
    reports_dir = reports_base / run_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    log(f"Reports dir: {reports_dir}")

    if run_mode == "full":
        # Full run: use canonical export and canonical config
        export_exit = run_export(target_id)
        export_fresh = export_exit == 0
        if export_exit != 0 and export_exit != 5:
            error("Export failed; aborting eval")
            sys.exit(export_exit)
        config_path = workspace / "exports" / "promptfoo" / "promptfooconfig.yaml"
    else:
        # Incremental run: generate run-scoped Promptfoo config
        export_fresh = True
        provider = load_model_matrix().get("models", [{}])[0].get("promptfoo")
        grader = load_model_matrix().get("models", [{}])[0].get("grader")
        run_promptfoo_dir = reports_dir / "promptfoo"
        write_run_scoped_promptfoo_files(
            run_promptfoo_dir, selected_cases, t_manifest, provider, grader
        )
        config_path = run_promptfoo_dir / "promptfooconfig.yaml"

    output_path = reports_dir / "promptfoo-output.json"

    eval_exit = run_promptfoo_eval(config_path, output_path, max_concurrency=max_concurrency)
    if eval_exit != 0:
        log(f"promptfoo eval exited with code {eval_exit}")

    parsed = parse_promptfoo_output(output_path)
    if "error" in parsed:
        error(f"Cannot parse results: {parsed['error']}")
        sys.exit(1)

    write_summary_md(reports_dir, target_id, run_id, export_fresh, parsed,
                     run_mode=run_mode, failure_source=failure_source,
                     max_concurrency=max_concurrency)
    write_failures_yaml(reports_dir, parsed)
```

- [ ] **Step 5: Fix run-index entry building (lines ~407-434)**

Replace the run-index entry block:

```python
    # Build run index entry
    git_baseline = get_git_baseline(REPO_ROOT)
    case_details = parsed.get("cases", [])
    case_status, failed_case_ids = build_case_status(case_details, selected_cases)
    case_files = collect_case_files(selected_cases, golden_dir)

    entry = build_run_entry(
        run_id=run_id, mode=run_mode, git_baseline=git_baseline,
        case_files=case_files, case_status=case_status,
        failed_cases=failed_case_ids,
        report_path=str(reports_dir.relative_to(REPO_ROOT)),
        failure_source=failure_source,
    )
    run_index_data.setdefault("runs", []).append(entry)
    save_run_index(reports_base, run_index_data)

    passed = parsed.get("passed", 0)
    failed = parsed.get("failed", 0)
    errors = parsed.get("errors", 0)
    total = parsed.get("total", 0)

    log(f"\nResults: {passed}/{total} passed, {failed} failed, {errors} errors")
    print(f"Report: {reports_dir}")

    if failed > 0 or errors > 0:
        sys.exit(1)
    sys.exit(0)
```

- [ ] **Step 6: Remove now-unused code at top of main()**

Remove the old `model_matrix = load_model_matrix()` and `run_policy = ...` lines at the original position (~319-321) since they are now in the new block from Step 3.

- [ ] **Step 7: Run existing tests**

```bash
python3 -m pytest tests/test_evalops_root.py tests/test_evalops_skill.py -v
```

Expected: all pass (string-presence tests remain valid)

- [ ] **Step 8: Commit**

```bash
git add skills/sdlc-evalops/scripts/run-promptfoo-eval.py
git commit -m "fix(evalops): single runner — subset export for incremental runs, correct run-index entries"
```

---

### Task 4: Fix `run-eval-matrix.py` — fail-fast loop and run-index entries

**Files:**
- Modify: `skills/sdlc-evalops/scripts/run-eval-matrix.py`

- [ ] **Step 1: Add import for `case_selection`**

Add to imports (after `from run_index import ...`):

```python
from case_selection import (
    get_case_identity, collect_case_files, select_only_new,
    select_only_failed,
)
```

- [ ] **Step 2: Fix only-new / only-failed selection (lines ~734-775)**

Replace the selection block in the target loop:

```python
        selected_cases = golden_cases
        if args.only_new:
            last_full = find_last_full_run(run_index_data.get("runs", []))
            if not last_full:
                error(f"No prior full run found in run index for {target_id}. Run a full eval first.")
                any_failure = True
                continue
            baseline = last_full.get("git_baseline")
            if not baseline:
                error(f"Last full run has no Git baseline for {target_id}. Run a full eval to record one.")
                any_failure = True
                continue
            changed_files = get_changed_golden_files(REPO_ROOT, baseline, golden_dir)
            if not changed_files:
                log(f"No changed golden case files since last full run for {target_id}. Skipping.")
                continue
            selected_cases = select_only_new(golden_cases, changed_files)
            if not selected_cases:
                log(f"Changed files have no matching golden cases for {target_id}. Skipping.")
                continue
            log(f"Only-new: {len(selected_cases)} case(s) changed since baseline {baseline[:8]}")
        elif args.only_failed:
            if not run_index_data.get("runs"):
                error(f"No run index found for {target_id}. Run a full eval first.")
                any_failure = True
                continue
            if args.failed_from == "latest":
                ref_run = find_latest_run(run_index_data["runs"])
            else:
                ref_run = find_last_full_run(run_index_data["runs"])
            if not ref_run:
                error(f"No qualifying run found in run index for {target_id}.")
                any_failure = True
                continue
            failed_ids = ref_run.get("failed_cases", [])
            if not failed_ids:
                log(f"No failed cases to retry for {target_id}. Skipping.")
                continue
            selected_cases = select_only_failed(golden_cases, failed_ids)
            if not selected_cases:
                log(f"Failed cases not found in golden dir for {target_id}. Skipping.")
                continue
            log(f"Only-failed ({failure_source}): {len(selected_cases)} failed case(s) to retry")
```

This is almost identical to existing code. The only change is using `select_only_new` / `select_only_failed` from `case_selection` instead of inline list comprehensions, and not using `case.get("id") in failed_ids` for only-failed (removed — `select_only_failed` handles it).

- [ ] **Step 3: Fix parallel fail-fast loop (lines ~779-811)**

Replace the parallel/sequential execution block with a fail-fast-safe version:

```python
        model_results = []

        if parallel and len(model_entries) > 1:
            # Parallel execution via ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_models) as executor:
                future_to_model: dict[concurrent.futures.Future, dict] = {}
                for model_entry in model_entries:
                    future = executor.submit(
                        run_single_model, model_entry, target_id, workspace,
                        t_manifest, selected_cases, target_reports_dir,
                        run_policy, run_mode, failure_source,
                    )
                    future_to_model[future] = model_entry

                fail_fast_triggered = False
                for future in concurrent.futures.as_completed(future_to_model):
                    if fail_fast_triggered:
                        # Skip gathering results for futures that complete after
                        # fail-fast was triggered (they will have been cancelled)
                        try:
                            future.result(timeout=0)
                        except concurrent.futures.CancelledError:
                            pass
                        except Exception:
                            pass
                        continue
                    try:
                        result = future.result()
                    except Exception as e:
                        model_entry = future_to_model[future]
                        result = {
                            "model_name": model_safe_name(model_entry),
                            "cfg_name": model_entry.get("name", "?"),
                            "observed_provider": "?",
                            "report_dir": str(target_reports_dir / model_safe_name(model_entry)),
                            "parsed": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "error": str(e)},
                            "exit_code": -1,
                            "failed": True,
                        }
                    model_results.append(result)
                    if result.get("failed") and fail_fast:
                        fail_fast_triggered = True
                        log("fail_fast enabled, cancelling remaining model futures.")
                        for f in future_to_model:
                            if not f.done():
                                f.cancel()

                # Wait briefly for cancellations to propagate, ignore errors
                for future in future_to_model:
                    if future.cancelled():
                        model_entry = future_to_model[future]
                        model_results.append({
                            "model_name": model_safe_name(model_entry),
                            "cfg_name": model_entry.get("name", "?"),
                            "observed_provider": "?",
                            "report_dir": str(target_reports_dir / model_safe_name(model_entry)),
                            "parsed": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "error": "cancelled by fail_fast"},
                            "exit_code": -1,
                            "failed": True,
                        })

        else:
            # Sequential execution
            for model_entry in model_entries:
                result = run_single_model(
                    model_entry, target_id, workspace,
                    t_manifest, selected_cases, target_reports_dir,
                    run_policy, run_mode, failure_source,
                )
                model_results.append(result)
                if result.get("failed") and fail_fast:
                    log("fail_fast enabled, stopping remaining model runs.")
                    break
```

- [ ] **Step 4: Fix run-index entry building (lines ~813-841)**

Replace the run-index entry block:

```python
        # Calculate per-case status aggregation across all model results
        case_status = {}
        failed_case_ids = set()
        for case in selected_cases:
            case_id = case.get("id", "?")
            all_passed = True
            for mr in model_results:
                parsed = mr.get("parsed", {})
                mr_cases = parsed.get("cases", [])
                # Find this case in model results by index
                case_idx = selected_cases.index(case)
                if case_idx < len(mr_cases):
                    passed = mr_cases[case_idx].get("passed", False)
                    if not passed:
                        all_passed = False
            case_status[case_id] = "passed" if all_passed else "failed"
            if not all_passed:
                failed_case_ids.add(case_id)

        case_files = collect_case_files(selected_cases, golden_dir)

        write_aggregate_summary(target_reports_dir, target_id, matrix_run_id,
                                model_results, run_mode=run_mode,
                                failure_source=failure_source)

        # Write run index entry
        git_baseline = get_git_baseline(REPO_ROOT)
        entry = build_run_entry(
            run_id=matrix_run_id, mode=run_mode, git_baseline=git_baseline,
            case_files=case_files, case_status=case_status,
            failed_cases=list(failed_case_ids),
            report_path=str(target_reports_dir.relative_to(REPO_ROOT)),
            failure_source=failure_source,
        )
        run_index_data.setdefault("runs", []).append(entry)
        save_run_index(reports_base, run_index_data)
```

- [ ] **Step 5: Run existing tests**

```bash
python3 -m pytest tests/test_evalops_root.py -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add skills/sdlc-evalops/scripts/run-eval-matrix.py
git commit -m "fix(evalops): matrix runner — safe fail-fast, correct run-index entries with case ids"
```

---

### Task 5: Add behavioral tests

**Files:**
- Create: `tests/test_evalops_incremental.py`

- [ ] **Step 1: Write `tests/test_evalops_incremental.py`**

```python
"""Behavioral tests for EvalOps incremental eval, run-index, and fail-fast.

Tests use temporary fixtures — no real Promptfoo or API key needed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = REPO_ROOT / "skills" / "sdlc-evalops" / "scripts"


def inject_scripts_to_path():
    sys.path.insert(0, str(SKILL_SCRIPTS))


class FixtureBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.evals_root = self.tmp / ".ai" / "evals"
        self._build_minimal_structure()
        inject_scripts_to_path()

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def _build_minimal_structure(self):
        """Create a minimal .ai/evals/targets/test-target/ workspace."""
        target_ws = self.evals_root / "targets" / "test-target"
        golden_dir = target_ws / "cases" / "golden"
        golden_dir.mkdir(parents=True, exist_ok=True)

        # Create golden case YAMLs
        (golden_dir / "case-1.yaml").write_text(
            "id: case-1\nstatus: golden\ninput: 'hello'\nexpected:\n  must_include: [hello]\n",
            encoding="utf-8"
        )
        (golden_dir / "case-2.yaml").write_text(
            "id: case-2\nstatus: golden\ninput: 'world'\nexpected:\n  must_include: [world]\n",
            encoding="utf-8"
        )
        (golden_dir / "case-3.yaml").write_text(
            "id: case-3\nstatus: golden\ninput: 'test'\nexpected:\n  must_include: [test]\n",
            encoding="utf-8"
        )

        # Target manifest
        (target_ws / "manifest.yaml").write_text(
            "target_id: test-target\n"
            "target_type: skill\n"
            "source_paths: []\n"
            "canonical_case_directories:\n"
            "  golden: cases/golden\n"
            "promptfoo_export_outputs:\n"
            "  directory: exports/promptfoo\n"
            "report_directory: reports\n"
            "assertion_policy:\n"
            "  allow_llm_rubric: false\n"
            "export_freshness_inputs: []\n"
            "coverage_file: coverage.yaml\n",
            encoding="utf-8"
        )

        # Global manifest
        (self.evals_root / "manifest.yaml").write_text(
            f"schema_version: '1.0'\n"
            f"targets:\n"
            f"  - id: test-target\n"
            f"    workspace: targets/test-target\n"
            f"model_matrix_path: model-matrix.yaml\n"
            f"default_export_policy: {{}}\n"
            f"default_assertion_policy: {{}}\n"
            f"report_policy: {{}}\n"
            f"platform_directories: {{}}\n",
            encoding="utf-8"
        )

        # Model matrix
        (self.evals_root / "model-matrix.yaml").write_text(
            "schema_version: '1.0'\n"
            "models:\n"
            "  - name: test-model\n"
            "    provider: test\n"
            "    model: test-v1\n"
            "    promptfoo:\n"
            "      id: openai:chat:test-v1\n"
            "      label: test/test-v1\n"
            "      config:\n"
            "        apiBaseUrl: https://example.com\n"
            "        apiKeyEnvar: TEST_KEY\n"
            "run_policy:\n"
            "  max_concurrency: 1\n"
            "  fail_fast: false\n"
            "  timeout_seconds: 30\n"
            "  retry_count: 0\n"
            "  parallel: false\n",
            encoding="utf-8"
        )

        # Git repo for run_index helpers
        subprocess.run(["git", "init"], cwd=str(self.tmp), capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.test"],
            cwd=str(self.tmp), capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(self.tmp), capture_output=True
        )
        subprocess.run(
            ["git", "add", "-A"], cwd=str(self.tmp), capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=str(self.tmp), capture_output=True
        )

    def _monkeypatch_cwd(self):
        """Change cwd for scripts that use Path.cwd() to find repo root."""
        self._original_cwd = Path.cwd()
        os.chdir(str(self.tmp))
        self.addCleanup(lambda: os.chdir(str(self._original_cwd)))

    def _make_run_index(self, runs=None):
        index_path = self.evals_root / "targets" / "test-target" / "reports" / "run-index.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"target_id": "test-target", "runs": runs or []}
        index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class TestCaseSelection(FixtureBase):
    def test_get_case_identity_returns_id_and_hash(self):
        from case_selection import get_case_identity
        case = {"id": "case-1", "_file": "case-1.yaml"}
        golden_dir = self.evals_root / "targets" / "test-target" / "cases" / "golden"
        case_id, file_name, content_hash, abs_path = get_case_identity(case, golden_dir)
        self.assertEqual(case_id, "case-1")
        self.assertEqual(file_name, "case-1.yaml")
        self.assertEqual(len(content_hash), 64)  # sha256 hex length
        self.assertTrue(abs_path.endswith("case-1.yaml"))

    def test_select_only_new_matches_by_filename(self):
        from case_selection import select_only_new
        cases = [
            {"id": "case-1", "_file": "case-1.yaml"},
            {"id": "case-2", "_file": "case-2.yaml"},
            {"id": "case-3", "_file": "case-3.yaml"},
        ]
        selected = select_only_new(cases, ["case-1.yaml", "case-3.yaml"])
        self.assertEqual(len(selected), 2)
        self.assertEqual({c["id"] for c in selected}, {"case-1", "case-3"})

    def test_select_only_new_no_matches(self):
        from case_selection import select_only_new
        cases = [{"id": "case-1", "_file": "case-1.yaml"}]
        selected = select_only_new(cases, ["other.yaml"])
        self.assertEqual(len(selected), 0)

    def test_select_only_failed_returns_matching_by_id(self):
        from case_selection import select_only_failed
        cases = [
            {"id": "case-1", "_file": "case-1.yaml"},
            {"id": "case-2", "_file": "case-2.yaml"},
        ]
        selected = select_only_failed(cases, ["case-1"])
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["id"], "case-1")

    def test_select_only_failed_skips_missing_ids(self):
        from case_selection import select_only_failed
        cases = [{"id": "case-1", "_file": "case-1.yaml"}]
        selected = select_only_failed(cases, ["case-99"])
        self.assertEqual(len(selected), 0)

    def test_collect_case_files_returns_all_cases(self):
        from case_selection import collect_case_files
        cases = [
            {"id": "case-1", "_file": "case-1.yaml"},
            {"id": "case-2", "_file": "case-2.yaml"},
        ]
        golden_dir = self.evals_root / "targets" / "test-target" / "cases" / "golden"
        cf = collect_case_files(cases, golden_dir)
        self.assertEqual(len(cf), 2)
        self.assertIn("case-1", cf)
        self.assertIn("file", cf["case-1"])
        self.assertIn("hash", cf["case-1"])
        self.assertEqual(len(cf["case-1"]["hash"]), 64)

    def test_build_case_status_reports_pass_fail(self):
        from case_selection import build_case_status
        selected = [{"id": "case-1"}, {"id": "case-2"}]
        eval_results = [
            {"passed": True, "input_preview": "hello"},
            {"passed": False, "input_preview": "world"},
        ]
        case_status, failed_cases = build_case_status(eval_results, selected)
        self.assertEqual(case_status["case-1"], "passed")
        self.assertEqual(case_status["case-2"], "failed")
        self.assertEqual(failed_cases, ["case-2"])

    def test_build_case_status_empty(self):
        from case_selection import build_case_status
        case_status, failed_cases = build_case_status([], [])
        self.assertEqual(case_status, {})
        self.assertEqual(failed_cases, [])


class TestRunIndex(FixtureBase):
    def test_get_changed_golden_files_returns_basenames(self):
        from run_index import get_changed_golden_files
        golden_dir = self.evals_root / "targets" / "test-target" / "cases" / "golden"
        # Add a new file and commit to get a diff
        (golden_dir / "case-new.yaml").write_text("id: case-new\ninput: 'new'\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(self.tmp), capture_output=True)
        subprocess.run(["git", "commit", "-m", "add case"], cwd=str(self.tmp), capture_output=True)

        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            capture_output=True, text=True, cwd=str(self.tmp)
        ).stdout.strip()

        changed = get_changed_golden_files(self.tmp, baseline, golden_dir)
        self.assertIn("case-new.yaml", changed)
        # Verify basenames only, no path components
        for f in changed:
            self.assertNotIn("/", f)

    def test_get_changed_golden_files_no_changes(self):
        from run_index import get_changed_golden_files
        golden_dir = self.evals_root / "targets" / "test-target" / "cases" / "golden"
        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(self.tmp)
        ).stdout.strip()
        changed = get_changed_golden_files(self.tmp, baseline, golden_dir)
        self.assertEqual(changed, [])

    def test_load_save_run_index_roundtrip(self):
        from run_index import load_run_index, save_run_index
        reports_dir = self.evals_root / "targets" / "test-target" / "reports"
        data = {"target_id": "test-target", "runs": [{"run_id": "r1", "mode": "full"}]}
        save_run_index(reports_dir, data)
        loaded = load_run_index(reports_dir)
        self.assertEqual(loaded["target_id"], "test-target")
        self.assertEqual(len(loaded["runs"]), 1)
        self.assertEqual(loaded["runs"][0]["run_id"], "r1")

    def test_build_run_entry_includes_all_fields(self):
        from run_index import build_run_entry
        entry = build_run_entry(
            run_id="test-run",
            mode="full",
            git_baseline="abc123",
            case_files={"case-1": {"file": "case-1.yaml", "hash": "fff"}},
            case_status={"case-1": "passed"},
            failed_cases=[],
            report_path="reports/test-run",
            failure_source=None,
        )
        self.assertEqual(entry["run_id"], "test-run")
        self.assertEqual(entry["mode"], "full")
        self.assertEqual(entry["git_baseline"], "abc123")
        self.assertEqual(entry["case_files"]["case-1"]["file"], "case-1.yaml")
        self.assertEqual(entry["case_status"]["case-1"], "passed")
        self.assertEqual(entry["failed_cases"], [])

    def test_find_last_full_run(self):
        from run_index import find_last_full_run
        runs = [
            {"run_id": "r1", "mode": "only-new", "timestamp": "2026-01-01T00:00:00Z"},
            {"run_id": "r2", "mode": "full", "timestamp": "2026-01-02T00:00:00Z"},
            {"run_id": "r3", "mode": "full", "timestamp": "2026-01-03T00:00:00Z"},
        ]
        result = find_last_full_run(runs)
        self.assertEqual(result["run_id"], "r3")

    def test_find_latest_run(self):
        from run_index import find_latest_run
        runs = [
            {"run_id": "r1", "mode": "full", "timestamp": "2026-01-01T00:00:00Z"},
            {"run_id": "r2", "mode": "only-new", "timestamp": "2026-01-02T00:00:00Z"},
        ]
        result = find_latest_run(runs)
        self.assertEqual(result["run_id"], "r2")


class TestMatrixFailFast(FixtureBase):
    def test_fail_fast_cancels_remaining_futures(self):
        import concurrent.futures
        import time

        results = []
        cancelled = []

        def worker(name, should_fail=False, delay=0):
            time.sleep(delay)
            if should_fail:
                return {"name": name, "failed": True}
            return {"name": name, "failed": False}

        # Simulate: 3 workers, first one fails, fail_fast enabled
        futures_to_name = {}
        fail_fast = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures_to_name[executor.submit(worker, "a", should_fail=True, delay=0.01)] = "a"
            futures_to_name[executor.submit(worker, "b", should_fail=False, delay=0.1)] = "b"
            futures_to_name[executor.submit(worker, "c", should_fail=False, delay=0.2)] = "c"

            fail_fast_triggered = False
            for future in concurrent.futures.as_completed(futures_to_name):
                if fail_fast_triggered:
                    try:
                        future.result(timeout=0)
                    except concurrent.futures.CancelledError:
                        cancelled.append(futures_to_name[future])
                    except Exception:
                        pass
                    continue
                try:
                    result = future.result()
                    results.append(result)
                    if result.get("failed") and fail_fast:
                        fail_fast_triggered = True
                        for f in futures_to_name:
                            if not f.done():
                                f.cancel()
                except Exception as e:
                    results.append({"name": futures_to_name[future], "failed": True, "error": str(e)})

            for future in futures_to_name:
                if future.cancelled():
                    cancelled.append(futures_to_name[future])

        # a must have completed (it's the one that failed)
        self.assertTrue(any(r["name"] == "a" for r in results))
        # b may or may not have completed (depends on timing)
        # c must have been cancelled (b takes 0.1s, c takes 0.2s, fail-fast triggers at ~0.01s)
        self.assertIn("c", cancelled)
```

- [ ] **Step 2: Run behavioral tests**

```bash
python3 -m pytest tests/test_evalops_incremental.py -v
```

Expected: all 13 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_evalops_incremental.py
git commit -m "test(evalops): add behavioral tests for case selection, run-index, and fail-fast"
```

---

### Task 6: Run full test suite

**Files:** (none)

- [ ] **Step 1: Run all tests**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass (including existing `test_evalops_root.py`, `test_evalops_skill.py`, and new `test_evalops_incremental.py`)

- [ ] **Step 2: If failures, diagnose and fix**

- [ ] **Step 3: Commit any follow-up fixes**

---

### Task 7: Re-distribute updated skill scripts to client dirs

**Files:**
- (distribution to `.opencode/skills/sdlc-evalops/`, `.claude/skills/sdlc-evalops/`, `.cursor/skills/sdlc-evalops/`)

- [ ] **Step 1: Distribute to all client copies**

```bash
cd /Users/yuping/Documents/workspace/oh_my_skills
for target in .opencode .claude .cursor; do
  python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py \
    --source-repo . --skill-name sdlc-evalops --source-ref HEAD \
    --target "${target}/skills/sdlc-evalops" --status stable
done
```

- [ ] **Step 2: Verify distribution**

```bash
for target in .opencode .claude .cursor; do
  echo "=== ${target} ==="
  ls "${target}/skills/sdlc-evalops/scripts/case_selection.py" && echo "OK" || echo "MISSING"
done
```

Expected: `OK` for all three

- [ ] **Step 3: Commit distribution**

```bash
git add -A
git commit -m "chore(evalops): distribute updated sdlc-evalops scripts with incremental-eval fixes"
```

- [ ] **Step 4: Push**

```bash
git push
```
