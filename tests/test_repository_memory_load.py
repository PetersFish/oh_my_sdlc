from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "sdlc-repository-memory-load"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from select_memory import select_memory, _score_entry, _is_excluded  # noqa: E402
from validate_memory import (  # noqa: E402
    validate_memory,
    VALID_SYNC_STATUSES,
    VALID_MEMORY_TYPES,
    REQUIRED_INDEX_FIELDS,
    REQUIRED_MANIFEST_FIELDS,
    REQUIRED_QUEUE_ITEM_FIELDS,
)

TEST_ROOT = Path(__file__).resolve().parent / "_test_repo_load"


class TestSelectMemoryMissingIndex(unittest.TestCase):
    def setUp(self) -> None:
        import shutil
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)
        TEST_ROOT.mkdir(parents=True)

    def tearDown(self) -> None:
        import shutil
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)

    def _memory_dir(self) -> Path:
        return TEST_ROOT / ".ai" / "memory"

    def _init(self) -> None:
        memory_dir = self._memory_dir()
        memory_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": "1.0", "memory_version": 1, "git": {"available": False}}
        (memory_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        index = {"schema_version": "1.0", "entries": []}
        (memory_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    def test_missing_manifest_returns_reason(self) -> None:
        result = select_memory(TEST_ROOT)
        self.assertEqual(result["entries"], [])
        self.assertIn("manifest", result["reason"])

    def test_missing_index_returns_reason(self) -> None:
        memory_dir = self._memory_dir()
        memory_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": "1.0", "memory_version": 1, "git": {"available": False}}
        (memory_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = select_memory(TEST_ROOT)
        self.assertEqual(result["entries"], [])
        self.assertIn("index", result["reason"])

    def test_empty_index_returns_no_entries(self) -> None:
        self._init()
        result = select_memory(TEST_ROOT)
        self.assertEqual(result["entries"], [])

    def test_legacy_ai_memory_is_read_as_fallback(self) -> None:
        legacy_dir = TEST_ROOT / ".ai-memory"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": "1.0", "memory_version": 1, "git": {"available": False}}
        (legacy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        index = {"schema_version": "1.0", "entries": [
            {"title": "Legacy Auth", "summary": "Legacy memory", "path": "modules/auth.md", "type": "module", "sync_status": "synced", "tags": ["auth"]},
        ]}
        (legacy_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

        result = select_memory(TEST_ROOT, query="auth")

        assert result["entries"][0]["title"] == "Legacy Auth"

    def test_query_selects_by_tag(self) -> None:
        self._init()
        entries = [
            {"title": "Auth Module", "summary": "Authentication logic", "path": "modules/auth.md", "type": "module", "sync_status": "synced", "tags": ["auth", "security"]},
            {"title": "Logger", "summary": "Logging utility", "path": "modules/logger.md", "type": "module", "sync_status": "synced", "tags": ["logging", "observability"]},
        ]
        index = {"schema_version": "1.0", "entries": entries}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")
        result = select_memory(TEST_ROOT, query="auth")
        paths = [e["path"] for e in result["entries"]]
        self.assertIn("modules/auth.md", paths)
        self.assertNotIn("modules/logger.md", paths)

    def test_query_selects_by_title(self) -> None:
        self._init()
        entries = [
            {"title": "Authentication Module", "summary": "Auth logic", "path": "modules/auth.md", "type": "module", "sync_status": "synced", "tags": []},
            {"title": "Database Layer", "summary": "DB access", "path": "modules/db.md", "type": "module", "sync_status": "synced", "tags": []},
        ]
        index = {"schema_version": "1.0", "entries": entries}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")
        result = select_memory(TEST_ROOT, query="database")
        paths = [e["path"] for e in result["entries"]]
        self.assertIn("modules/db.md", paths)
        self.assertNotIn("modules/auth.md", paths)

    def test_excluded_paths_filtered(self) -> None:
        self._init()
        entries = [
            {"title": "Session Data", "summary": "Session info", "path": "sessions/abc.md", "type": "sessions", "sync_status": "synced", "tags": ["session"]},
            {"title": "Sync Audit", "summary": "Sync history", "path": "sync-history/2024.md", "type": "module", "sync_status": "synced", "tags": ["sync"]},
            {"title": "Valid Module", "summary": "A module", "path": "modules/auth.md", "type": "module", "sync_status": "synced", "tags": ["auth"]},
        ]
        index = {"schema_version": "1.0", "entries": entries}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")
        result = select_memory(TEST_ROOT)
        paths = [e["path"] for e in result["entries"]]
        self.assertIn("modules/auth.md", paths)
        self.assertNotIn("sessions/abc.md", paths)
        self.assertNotIn("sync-history/2024.md", paths)

    def test_max_result_limit_enforced(self) -> None:
        self._init()
        entries = [
            {"title": f"Module {i}", "summary": f"Module {i} summary", "path": f"modules/mod{i}.md", "type": "module", "sync_status": "synced", "tags": []}
            for i in range(10)
        ]
        index = {"schema_version": "1.0", "entries": entries}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")
        result = select_memory(TEST_ROOT, max_results=3)
        self.assertEqual(len(result["entries"]), 3)
        self.assertEqual(result["loaded"], 3)

    def test_context_pack_format(self) -> None:
        self._init()
        entries = [
            {"title": "Auth", "summary": "Auth module", "path": "modules/auth.md", "type": "module", "sync_status": "synced", "tags": ["auth"]},
        ]
        index = {"schema_version": "1.0", "entries": entries}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")
        result = select_memory(TEST_ROOT)
        self.assertIn("entries", result)
        self.assertIn("loaded", result)
        self.assertIn("total_eligible", result)
        self.assertIn("skipped_paths", result)

    def test_enriched_metadata_ranks_child_above_parent(self) -> None:
        self._init()
        parent = {
            "id": "modules/skills",
            "title": "Skills Collection",
            "summary": "All skills including repository memory skills",
            "path": "modules/skills.md",
            "type": "module",
            "sync_status": "synced",
            "tags": ["skills", "memory"],
        }
        child = {
            "id": "modules/skills/repository-memory",
            "parent_id": "modules/skills",
            "title": "Repository Memory Skills",
            "summary": "Focused child module for repository memory implementation",
            "path": "modules/skills/repository-memory.md",
            "type": "module",
            "sync_status": "synced",
            "tags": ["memory"],
            "owned_paths": ["skills/sdlc-repository-memory-sync"],
            "path_hints": ["skills/sdlc-repository-memory-sync/scripts/discover_modules.py"],
            "keywords": ["child-module", "discovery", "memory-sync"],
            "test_paths": ["tests/test_module_discovery.py"],
            "spec_paths": ["openspec/specs/module-discovery/spec.md"],
        }
        index = {"schema_version": "1.0", "entries": [parent, child]}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")

        result = select_memory(TEST_ROOT, query="discover_modules child-module")

        self.assertEqual(result["entries"][0]["path"], "modules/skills/repository-memory.md")


class TestIsExcluded(unittest.TestCase):
    def test_sessions_excluded(self) -> None:
        self.assertTrue(_is_excluded("sessions/abc.md"))

    def test_sync_history_excluded(self) -> None:
        self.assertTrue(_is_excluded("sync-history/2024.md"))

    def test_snapshots_excluded(self) -> None:
        self.assertTrue(_is_excluded("snapshots/v1.md"))

    def test_tmp_excluded(self) -> None:
        self.assertTrue(_is_excluded("tmp/draft.md"))

    def test_cache_excluded(self) -> None:
        self.assertTrue(_is_excluded("cache/data.json"))

    def test_review_queue_excluded(self) -> None:
        self.assertTrue(_is_excluded("review-queue.json"))

    def test_modules_not_excluded(self) -> None:
        self.assertFalse(_is_excluded("modules/auth.md"))

    def test_specs_not_excluded(self) -> None:
        self.assertFalse(_is_excluded("specs/api.md"))


class TestScoreEntry(unittest.TestCase):
    def test_empty_query_gets_base_score(self) -> None:
        entry = {"title": "Test", "summary": "Summary", "path": "modules/test.md", "type": "module", "tags": []}
        score = _score_entry(entry, set())
        self.assertEqual(score, 1)

    def test_title_match_scores_higher(self) -> None:
        entry = {"title": "Authentication Module", "summary": "Core logic", "path": "modules/auth.md", "type": "module", "tags": []}
        score = _score_entry(entry, {"authentication"})
        self.assertGreater(score, 0)

    def test_tag_match(self) -> None:
        entry = {"title": "Module", "summary": "Logic", "path": "modules/mod.md", "type": "module", "tags": ["auth", "security"]}
        score = _score_entry(entry, {"auth"})
        self.assertGreater(score, 0)

    def test_enriched_fields_contribute_to_score(self) -> None:
        entry = {
            "title": "Repository Memory",
            "summary": "Module",
            "path": "modules/skills/repository-memory.md",
            "type": "module",
            "tags": [],
            "path_hints": ["skills/sdlc-repository-memory-sync/scripts/discover_modules.py"],
            "keywords": ["child-module"],
            "test_paths": ["tests/test_module_discovery.py"],
            "spec_paths": ["openspec/specs/module-discovery/spec.md"],
        }

        score = _score_entry(entry, {"discover_modules", "child-module"})

        self.assertGreaterEqual(score, 5)


class TestValidateMemory(unittest.TestCase):
    def setUp(self) -> None:
        import shutil
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)
        TEST_ROOT.mkdir(parents=True)

    def tearDown(self) -> None:
        import shutil
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)

    def _memory_dir(self) -> Path:
        return TEST_ROOT / ".ai" / "memory"

    def _init_valid(self) -> None:
        memory_dir = self._memory_dir()
        memory_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": "1.0", "memory_version": 1, "git": {"available": False, "has_commits": False, "head": None, "last_synced_commit": None, "worktree_state": "unknown"}, "pending_snapshots": [], "last_sync": None}
        (memory_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        index = {"schema_version": "1.0", "entries": [
            {"id": "auth", "title": "Auth", "summary": "Auth module", "path": "modules/auth.md", "type": "module", "status": "synced", "tags": ["auth"], "updated_at": "2026-01-01T00:00:00Z", "confidence": "high"},
        ]}
        (memory_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    def test_accepts_valid_samples(self) -> None:
        self._init_valid()
        result = validate_memory(TEST_ROOT)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_rejects_unsupported_memory_type(self) -> None:
        self._init_valid()
        index = {"schema_version": "1.0", "entries": [
            {"title": "Bad", "summary": "Bad type", "path": "modules/bad.md", "type": "invalid_type", "sync_status": "synced", "tags": []},
        ]}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")
        result = validate_memory(TEST_ROOT)
        self.assertFalse(result["valid"])
        has_type_error = any("invalid type" in e for e in result["errors"])
        self.assertTrue(has_type_error)

    def test_rejects_unsupported_sync_status(self) -> None:
        self._init_valid()
        index = {"schema_version": "1.0", "entries": [
            {"id": "bad", "title": "Bad", "summary": "Bad status", "path": "modules/bad.md", "type": "module", "status": "unknown_status", "tags": [], "updated_at": "2026-01-01T00:00:00Z", "confidence": "high"},
        ]}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")
        result = validate_memory(TEST_ROOT)
        self.assertFalse(result["valid"])
        has_status_error = any("invalid status" in e for e in result["errors"])
        self.assertTrue(has_status_error)

    def test_missing_manifest_reported(self) -> None:
        result = validate_memory(TEST_ROOT)
        self.assertFalse(result["valid"])
        has_manifest_error = any("manifest" in e.lower() for e in result["errors"])
        self.assertTrue(has_manifest_error)

    def test_missing_index_fields_reported(self) -> None:
        memory_dir = self._memory_dir()
        memory_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": "1.0", "memory_version": 1, "git": {"available": False}}
        (memory_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        index = {"schema_version": "1.0", "entries": [
            {"title": "Incomplete"},
        ]}
        (memory_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")
        result = validate_memory(TEST_ROOT)
        self.assertFalse(result["valid"])
        has_missing = any("missing fields" in e for e in result["errors"])
        self.assertTrue(has_missing)

    def test_accepts_child_module_enriched_index_fields(self) -> None:
        self._init_valid()
        index = {"schema_version": "1.0", "entries": [
            {
                "title": "Repository Memory",
                "summary": "Child module",
                "path": "modules/skills/repository-memory.md",
                "type": "module",
                "status": "synced",
                "tags": ["memory"],
                "id": "modules/skills/repository-memory",
                "updated_at": "2026-01-01T00:00:00Z",
                "confidence": "high",
                "parent_id": "modules/skills",
                "owned_paths": ["skills/sdlc-repository-memory-sync"],
                "path_hints": ["skills/sdlc-repository-memory-sync/scripts/discover_modules.py"],
                "keywords": ["child-module"],
                "test_paths": ["tests/test_module_discovery.py"],
                "spec_paths": ["openspec/specs/module-discovery/spec.md"],
            },
        ]}
        (self._memory_dir() / "index.json").write_text(json.dumps(index), encoding="utf-8")

        result = validate_memory(TEST_ROOT)

        self.assertTrue(result["valid"], result["errors"])


if __name__ == "__main__":
    unittest.main()
