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

        (self.evals_root / "manifest.yaml").write_text(
            "schema_version: '1.0'\n"
            "targets:\n"
            "  - id: test-target\n"
            "    workspace: targets/test-target\n"
            "model_matrix_path: model-matrix.yaml\n"
            "default_export_policy: {}\n"
            "default_assertion_policy: {}\n"
            "report_policy: {}\n"
            "platform_directories: {}\n",
            encoding="utf-8"
        )

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
        self.assertEqual(len(content_hash), 64)
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
        (golden_dir / "case-new.yaml").write_text("id: case-new\ninput: 'new'\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(self.tmp), capture_output=True)
        subprocess.run(["git", "commit", "-m", "add case"], cwd=str(self.tmp), capture_output=True)

        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            capture_output=True, text=True, cwd=str(self.tmp)
        ).stdout.strip()

        changed = get_changed_golden_files(self.tmp, baseline, golden_dir)
        self.assertIn("case-new.yaml", changed)
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

        futures_to_name = {}
        fail_fast = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
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

        self.assertTrue(any(r["name"] == "a" for r in results))
        self.assertIn("c", cancelled)
