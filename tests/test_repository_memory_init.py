from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "repository-memory-init"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from init_memory import init_memory, SUBDIRS, GITIGNORE_CONTENT  # noqa: E402


class TestRepositoryMemoryInit(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(__file__).resolve().parent / "_test_repo_init"
        self.tmp_dir.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        import shutil
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    def _memory_dir(self) -> Path:
        return self.tmp_dir / ".ai-memory"

    def test_init_creates_full_directory_structure(self) -> None:
        result = init_memory(self.tmp_dir)
        memory_dir = self._memory_dir()
        for subdir in SUBDIRS:
            self.assertTrue((memory_dir / subdir).is_dir(), f"Missing subdirectory: {subdir}")
        self.assertTrue(len(result["created"]) > 0)

    def test_init_is_idempotent(self) -> None:
        result1 = init_memory(self.tmp_dir)
        result2 = init_memory(self.tmp_dir)
        self.assertEqual(len(result2["skipped"]), len(result1["created"]))
        self.assertEqual(len(result2["created"]), 0)

    def test_init_preserves_existing_manifest(self) -> None:
        init_memory(self.tmp_dir)
        manifest_path = self._memory_dir() / "manifest.json"
        original = manifest_path.read_text(encoding="utf-8")
        modified = original.replace('"memory_version": 1', '"memory_version": 42')
        manifest_path.write_text(modified, encoding="utf-8")
        init_memory(self.tmp_dir)
        current = manifest_path.read_text(encoding="utf-8")
        self.assertIn('"memory_version": 42', current)
        self.assertEqual(current, modified)

    def test_init_reports_missing_agents_md(self) -> None:
        result = init_memory(self.tmp_dir)
        self.assertEqual(result["agents_md_status"], "missing")

    def test_init_reports_present_agents_md(self) -> None:
        (self.tmp_dir / "AGENTS.md").write_text("# Test\n", encoding="utf-8")
        result = init_memory(self.tmp_dir)
        self.assertEqual(result["agents_md_status"], "present")

    def test_init_writes_expected_gitignore(self) -> None:
        init_memory(self.tmp_dir)
        gitignore_path = self._memory_dir() / ".gitignore"
        self.assertTrue(gitignore_path.exists())
        content = gitignore_path.read_text(encoding="utf-8")
        self.assertEqual(content, GITIGNORE_CONTENT)
        self.assertIn("sessions/", content)
        self.assertIn("*.local.json", content)

    def test_init_json_output_is_valid(self) -> None:
        result = init_memory(self.tmp_dir)
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        self.assertIn("created", parsed)
        self.assertIn("skipped", parsed)
        self.assertIn("agents_md_status", parsed)

    def test_init_creates_all_required_subdirectories(self) -> None:
        init_memory(self.tmp_dir)
        memory_dir = self._memory_dir()
        expected = set(SUBDIRS)
        actual = {d.name for d in memory_dir.iterdir() if d.is_dir()}
        self.assertTrue(expected.issubset(actual), f"Missing dirs: {expected - actual}")

    def test_init_creates_template_files(self) -> None:
        init_memory(self.tmp_dir)
        memory_dir = self._memory_dir()
        manifest = json.loads((memory_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["memory_version"], 1)
        index = json.loads((memory_dir / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], "1.0")
        self.assertIsInstance(index["entries"], list)
        rq = json.loads((memory_dir / "review-queue.json").read_text(encoding="utf-8"))
        self.assertIsInstance(rq["items"], list)
        self.assertEqual(len(rq["items"]), 0)

    def test_init_preserves_existing_gitignore(self) -> None:
        init_memory(self.tmp_dir)
        gitignore_path = self._memory_dir() / ".gitignore"
        gitignore_path.write_text("custom_rule/\n", encoding="utf-8")
        result = init_memory(self.tmp_dir)
        content = gitignore_path.read_text(encoding="utf-8")
        self.assertEqual(content, "custom_rule/\n")


REPO_ROOT = Path(__file__).resolve().parents[1]

class TestEndToEndIntegration(unittest.TestCase):
    @staticmethod
    def _load_module(name: str, path: Path):
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_no_ai_memory_triggers_init_suggestion(self, tmp_path=None):
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp()) if tmp_path is None else tmp_path
        try:
            select_mod = self._load_module(
                "select_memory_e2e",
                REPO_ROOT / "skills" / "repository-memory-load" / "scripts" / "select_memory.py",
            )
            result = select_mod.select_memory(tmp_dir)
            assert result["entries"] == []
            assert "reason" in result
            assert "init" in result["reason"].lower()
        finally:
            if tmp_path is None:
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_init_creates_structure_idempotently(self):
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            init_mod = self._load_module(
                "init_memory_e2e",
                REPO_ROOT / "skills" / "repository-memory-init" / "scripts" / "init_memory.py",
            )
            result1 = init_mod.init_memory(tmp_dir)
            memory_dir = tmp_dir / ".ai-memory"
            for subdir in init_mod.SUBDIRS:
                assert (memory_dir / subdir).is_dir(), f"Missing subdirectory: {subdir}"
            assert (memory_dir / "manifest.json").exists()
            assert (memory_dir / "index.json").exists()
            assert (memory_dir / "review-queue.json").exists()
            assert (memory_dir / ".gitignore").exists()
            manifest_before = (memory_dir / "manifest.json").read_text(encoding="utf-8")
            index_before = (memory_dir / "index.json").read_text(encoding="utf-8")
            rq_before = (memory_dir / "review-queue.json").read_text(encoding="utf-8")
            gitignore_before = (memory_dir / ".gitignore").read_text(encoding="utf-8")
            result2 = init_mod.init_memory(tmp_dir)
            assert len(result2["created"]) == 0
            assert len(result2["skipped"]) > 0
            assert (memory_dir / "manifest.json").read_text(encoding="utf-8") == manifest_before
            assert (memory_dir / "index.json").read_text(encoding="utf-8") == index_before
            assert (memory_dir / "review-queue.json").read_text(encoding="utf-8") == rq_before
            assert (memory_dir / ".gitignore").read_text(encoding="utf-8") == gitignore_before
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_later_commit_reconciles_pending_memory(self):
        import subprocess
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            subprocess.run(["git", "init"], cwd=str(tmp_dir), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_dir), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_dir), capture_output=True, check=True)
            init_mod = self._load_module(
                "init_memory_reconcile",
                REPO_ROOT / "skills" / "repository-memory-init" / "scripts" / "init_memory.py",
            )
            init_mod.init_memory(tmp_dir)
            modules_dir = tmp_dir / ".ai-memory" / "modules"
            modules_dir.mkdir(parents=True, exist_ok=True)
            module_content = (
                "---\n"
                "id: auth-module\n"
                "type: module\n"
                "title: Authentication Module\n"
                "sync_status: pending_commit\n"
                "evidence_mode: uncommitted_snapshot\n"
                "linked_commits: []\n"
                "---\n"
                "\n"
                "# Authentication Module\n"
                "\n"
                "Handles user authentication.\n"
            )
            module_file = modules_dir / "auth-module.md"
            module_file.write_text(module_content, encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=str(tmp_dir), capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=str(tmp_dir), capture_output=True, check=True)
            reconcile_mod = self._load_module(
                "reconcile_pending_e2e",
                REPO_ROOT / "skills" / "repository-memory-sync" / "scripts" / "reconcile_pending.py",
            )
            result = reconcile_mod.reconcile_pending(tmp_dir, write=True)
            assert len(result["reconciled"]) == 1
            rec = result["reconciled"][0]
            assert rec["new_status"] == "synced"
            assert "matched_commits" in rec
            updated_content = module_file.read_text(encoding="utf-8")
            assert "sync_status: synced" in updated_content
            assert "evidence_mode: commit" in updated_content
            rq = json.loads((tmp_dir / ".ai-memory" / "review-queue.json").read_text(encoding="utf-8"))
            has_reconcile_item = any(
                item.get("id", "").startswith("review-auth-module") or item.get("reason") in ("partial_reconcile", "no_matching_commit")
                for item in rq.get("items", [])
            )
            assert not has_reconcile_item
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestSyncHistoryAndReviewQueue:
    REPO_ROOT = Path(__file__).resolve().parents[1]

    def _load_module(self, path: Path, module_name: str):
        import importlib.util
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_sync_history_committed_but_not_indexed(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        memory_dir.mkdir()
        (memory_dir / "modules").mkdir()
        (memory_dir / "sync-history").mkdir()

        manifest = {"schema_version": "1.0", "memory_version": 1}
        (memory_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        index_data = {"schema_version": "1.0", "entries": []}
        (memory_dir / "index.json").write_text(json.dumps(index_data), encoding="utf-8")

        module_content = (
            "---\n"
            "id: test-module-001\n"
            "type: module\n"
            "title: Test Module\n"
            "summary: A test module\n"
            "sync_status: synced\n"
            "updated_at: 2026-01-01T00:00:00Z\n"
            "---\n"
            "\n"
            "Module body content.\n"
        )
        (memory_dir / "modules" / "test-module.md").write_text(module_content, encoding="utf-8")

        sync_history_content = (
            "---\n"
            "id: sync-2026-01-01-001\n"
            "type: sync\n"
            "title: Old Sync Record\n"
            "sync_status: synced\n"
            "---\n"
            "\n"
            "Old sync history content.\n"
        )
        (memory_dir / "sync-history" / "sync-2026-01-01-001.md").write_text(sync_history_content, encoding="utf-8")

        rebuild_path = self.REPO_ROOT / "skills" / "repository-memory-sync" / "scripts" / "rebuild_index.py"
        rebuild_mod = self._load_module(rebuild_path, "rebuild_index_test_8_9")
        result = rebuild_mod.rebuild_index(tmp_path, write=False)

        assert result["status"] == "ok"
        assert len(result["entries"]) == 1
        assert result["entries"][0]["id"] == "test-module-001"
        paths = [e["path"] for e in result["entries"]]
        assert "sync-history/sync-2026-01-01-001.md" not in paths

    def test_review_queue_committed_but_only_sync_reads_it(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        memory_dir.mkdir()
        (memory_dir / "modules").mkdir()

        manifest = {"schema_version": "1.0", "memory_version": 1}
        (memory_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        module_content = (
            "---\n"
            "id: auth-module\n"
            "type: module\n"
            "title: Auth Module\n"
            "summary: Authentication module\n"
            "sync_status: synced\n"
            "updated_at: 2026-01-01T00:00:00Z\n"
            "---\n"
            "\n"
            "Auth module body.\n"
        )
        (memory_dir / "modules" / "auth-module.md").write_text(module_content, encoding="utf-8")

        index_data = {
            "schema_version": "1.0",
            "entries": [
                {
                    "id": "auth-module",
                    "type": "module",
                    "path": "modules/auth-module.md",
                    "title": "Auth Module",
                    "summary": "Authentication module",
                    "tags": [],
                    "updated_at": "2026-01-01T00:00:00Z",
                    "confidence": "medium",
                    "status": "synced",
                },
            ],
        }
        (memory_dir / "index.json").write_text(json.dumps(index_data), encoding="utf-8")

        review_item = {
            "id": "rq-001",
            "type": "module",
            "source_sync_id": "sync-2026-01-01-001",
            "reason": "conflict",
            "title": "Conflicting module update",
            "source_refs": ["modules/auth-module.md"],
            "status": "pending",
            "created_at": "2026-01-01T00:00:00Z",
        }
        review_queue = {"items": [review_item]}
        (memory_dir / "review-queue.json").write_text(json.dumps(review_queue), encoding="utf-8")

        select_path = self.REPO_ROOT / "skills" / "repository-memory-load" / "scripts" / "select_memory.py"
        select_mod = self._load_module(select_path, "select_memory_test_8_10")
        result = select_mod.select_memory(tmp_path, query="", max_results=5)

        result_paths = [e.get("path", "") for e in result["entries"]]
        assert "review-queue.json" not in result_paths
        auth_entries = [e for e in result["entries"] if e.get("id") == "auth-module"]
        assert len(auth_entries) >= 1

        assert "id" in review_item
        assert "type" in review_item
        assert "source_sync_id" in review_item
        assert "reason" in review_item
        assert "title" in review_item
        assert "source_refs" in review_item
        assert "status" in review_item
        assert "created_at" in review_item


if __name__ == "__main__":
    unittest.main()