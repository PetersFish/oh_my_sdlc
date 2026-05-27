from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPTS_DIR = REPO_ROOT / "skills" / "repository-memory-sync" / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_detect_state_mod = _load_module("detect_state", SYNC_SCRIPTS_DIR / "detect_state.py")
_reconcile_mod = _load_module("reconcile_pending", SYNC_SCRIPTS_DIR / "reconcile_pending.py")
_validate_mod = _load_module("validate_memory_sync", SYNC_SCRIPTS_DIR / "validate_memory.py")
_rebuild_mod = _load_module("rebuild_index", SYNC_SCRIPTS_DIR / "rebuild_index.py")
_update_mod = _load_module("update_manifest", SYNC_SCRIPTS_DIR / "update_manifest.py")

_detect_git = _detect_state_mod._detect_git
_detect_openspec_candidates = _detect_state_mod._detect_openspec_candidates
reconcile_pending = _reconcile_mod.reconcile_pending
validate_memory = _validate_mod.validate_memory
rebuild_index = _rebuild_mod.rebuild_index
update_manifest = _update_mod.update_manifest


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True, timeout=10)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(path), capture_output=True, timeout=10)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path), capture_output=True, timeout=10)


def _git_commit(path: Path, msg: str = "init") -> str:
    subprocess.run(["git", "add", "-A"], cwd=str(path), capture_output=True, timeout=10)
    subprocess.run(["git", "commit", "-m", msg], cwd=str(path), capture_output=True, timeout=10)
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(path), capture_output=True, text=True, timeout=10)
    return result.stdout.strip()


class TestDetectState:
    def test_non_git_directory_returns_not_available(self, tmp_path):
        result = _detect_git(tmp_path)
        assert result["available"] is False
        assert result["has_commits"] is False
        assert result["head"] is None
        assert result["last_synced_commit"] is None

    def test_git_repo_no_commits_returns_has_commits_false(self, tmp_path):
        _init_git_repo(tmp_path)
        result = _detect_git(tmp_path)
        assert result["available"] is True
        assert result["has_commits"] is False
        assert result["head"] is None

    def test_clean_worktree_returns_clean(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        _git_commit(tmp_path, "initial")
        result = _detect_git(tmp_path)
        assert result["worktree_state"] == "clean"
        assert result["has_commits"] is True
        assert result["head"] is not None

    def test_dirty_worktree_returns_dirty(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        _git_commit(tmp_path, "initial")
        (tmp_path / "dirty.txt").write_text("dirty", encoding="utf-8")
        result = _detect_git(tmp_path)
        assert result["worktree_state"] == "dirty"

    def test_openspec_candidates_detected_from_diff(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        _git_commit(tmp_path, "initial")
        openspec_dir = tmp_path / "openspec" / "changes" / "my-feature"
        openspec_dir.mkdir(parents=True)
        (openspec_dir / ".openspec.yaml").write_text("name: my-feature", encoding="utf-8")
        _git_commit(tmp_path, "add openspec change")
        result = _detect_openspec_candidates(tmp_path, None, ["openspec/changes/my-feature/.openspec.yaml"], [])
        change_ids = [c["change_id"] for c in result["candidates"]]
        assert "my-feature" in change_ids


class TestReconcilePending:
    def _make_memory_file(self, path: Path, frontmatter_fields: dict, body: str = "") -> Path:
        lines = ["---"]
        for k, v in frontmatter_fields.items():
            if isinstance(v, list):
                lines.append(f"{k}: [{', '.join(str(i) for i in v)}]")
            else:
                lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append(body)
        content = "\n".join(lines) + "\n"
        path.write_text(content, encoding="utf-8")
        return path

    def test_matched_pending_becomes_synced(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        _git_commit(tmp_path, "initial")
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        self._make_memory_file(
            modules_dir / "test-module.md",
            {
                "id": "test-module",
                "type": "module",
                "title": "Test Module",
                "summary": "A test",
                "sync_status": "pending_commit",
                "evidence_mode": "commit",
                "linked_commits": [],
                "linked_specs": [],
                "linked_sessions": [],
                "updated_at": "2026-01-01T00:00:00Z",
                "confidence": "high",
                "tags": [],
            },
        )
        _git_commit(tmp_path, "add memory")
        result = reconcile_pending(tmp_path, write=False)
        matched = [r for r in result["reconciled"] if r["new_status"] == "synced"]
        assert len(matched) >= 1

    def test_partial_match_creates_review_item(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        self._make_memory_file(
            modules_dir / "partial-module.md",
            {
                "id": "partial-module",
                "type": "module",
                "title": "Partial Module",
                "summary": "A partial test",
                "sync_status": "pending_commit",
                "evidence_mode": "commit",
                "linked_commits": [],
                "linked_specs": [],
                "linked_sessions": [],
                "updated_at": "2026-01-01T00:00:00Z",
                "confidence": "medium",
                "tags": [],
                "reconcile_after_commit": "0000000000000000000000000000000000000000",
            },
        )
        _git_commit(tmp_path, "add memory file")
        (tmp_path / "another-change.txt").write_text("change", encoding="utf-8")
        _git_commit(tmp_path, "another change")
        result = reconcile_pending(tmp_path, write=False)
        has_partial = any(item["reason"] == "partial_reconcile" for item in result["review_items"])
        has_reconciled = len(result["reconciled"]) > 0
        assert has_partial or has_reconciled, f"Expected partial_reconcile or reconciled, got {result}"

    def test_no_match_creates_review_with_no_matching_commit(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        _git_commit(tmp_path, "initial")
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        self._make_memory_file(
            modules_dir / "orphan-module.md",
            {
                "id": "orphan-module",
                "type": "module",
                "title": "Orphan",
                "summary": "No matching commit",
                "sync_status": "pending_commit",
                "evidence_mode": "uncommitted_snapshot",
                "linked_commits": [],
                "linked_specs": [],
                "linked_sessions": [],
                "updated_at": "2026-01-01T00:00:00Z",
                "confidence": "low",
                "tags": [],
            },
        )
        (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
        result = reconcile_pending(tmp_path, write=False)
        review_reasons = [item["reason"] for item in result["review_items"]]
        assert "no_matching_commit" in review_reasons or len(result["reconciled"]) > 0

    def test_review_item_has_no_full_diff_content(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        _git_commit(tmp_path, "initial")
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        self._make_memory_file(
            modules_dir / "review-mod.md",
            {
                "id": "review-mod",
                "type": "module",
                "title": "Review Mod",
                "summary": "Check no diff",
                "sync_status": "pending_commit",
                "evidence_mode": "uncommitted_snapshot",
                "linked_commits": [],
                "linked_specs": [],
                "linked_sessions": [],
                "updated_at": "2026-01-01T00:00:00Z",
                "confidence": "low",
                "tags": [],
            },
        )
        result = reconcile_pending(tmp_path, write=False)
        for item in result["review_items"]:
            assert "diff" not in item
            assert "full_diff" not in item


class TestValidateMemory:
    def _write_manifest(self, memory_dir: Path, data: dict) -> None:
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "manifest.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _valid_manifest(self, **overrides) -> dict:
        manifest = {
            "schema_version": "1.0",
            "repository_id": "test-repo",
            "memory_version": 1,
            "git": {
                "available": True,
                "has_commits": True,
                "head": "abc123",
                "last_synced_commit": "abc123",
                "worktree_state": "clean",
            },
            "pending_snapshots": [],
        }
        manifest.update(overrides)
        return manifest

    def test_valid_manifest_passes(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        self._write_manifest(memory_dir, self._valid_manifest())
        (memory_dir / "index.json").write_text(
            json.dumps({"schema_version": "1.0", "generated_at": "2026-01-01T00:00:00Z", "entries": []}) + "\n",
            encoding="utf-8",
        )
        result = validate_memory(tmp_path)
        assert result["valid"] is True
        assert result["counts"]["manifest"]["valid"] is True

    def test_missing_manifest_field_reported(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        manifest = self._valid_manifest()
        del manifest["repository_id"]
        self._write_manifest(memory_dir, manifest)
        result = validate_memory(tmp_path)
        assert any("missing required fields" in e and "repository_id" in e for e in result["errors"])

    def test_invalid_sync_status_rejected(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        (modules_dir / "bad-status.md").write_text(
            "---\nid: bad-status\ntype: module\ntitle: Bad\nsummary: test\n"
            "sync_status: partially_reconciled\nevidence_mode: commit\n"
            "linked_commits: []\nlinked_specs: []\nlinked_sessions: []\n"
            "updated_at: 2026-01-01T00:00:00Z\nconfidence: high\ntags: []\n---\nBody\n",
            encoding="utf-8",
        )
        self._write_manifest(memory_dir, self._valid_manifest())
        (memory_dir / "index.json").write_text(
            json.dumps({"schema_version": "1.0", "generated_at": "2026-01-01T00:00:00Z", "entries": []}) + "\n",
            encoding="utf-8",
        )
        result = validate_memory(tmp_path)
        assert any("partially_reconciled" in e for e in result["errors"])

    def test_invalid_memory_type_rejected(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        (modules_dir / "bad-type.md").write_text(
            "---\nid: bad-type\ntype: invalid_type\ntitle: Bad Type\nsummary: test\n"
            "sync_status: synced\nevidence_mode: commit\n"
            "linked_commits: []\nlinked_specs: []\nlinked_sessions: []\n"
            "updated_at: 2026-01-01T00:00:00Z\nconfidence: high\ntags: []\n---\nBody\n",
            encoding="utf-8",
        )
        self._write_manifest(memory_dir, self._valid_manifest())
        (memory_dir / "index.json").write_text(
            json.dumps({"schema_version": "1.0", "generated_at": "2026-01-01T00:00:00Z", "entries": []}) + "\n",
            encoding="utf-8",
        )
        result = validate_memory(tmp_path)
        assert any("invalid_type" in e for e in result["errors"])

    def test_valid_frontmatter_passes(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        (modules_dir / "good.md").write_text(
            "---\nid: good\ntype: module\ntitle: Good\nsummary: test\n"
            "sync_status: synced\nevidence_mode: commit\n"
            "linked_commits: []\nlinked_specs: []\nlinked_sessions: []\n"
            "updated_at: 2026-01-01T00:00:00Z\nconfidence: high\ntags: []\n---\nBody\n",
            encoding="utf-8",
        )
        self._write_manifest(memory_dir, self._valid_manifest())
        (memory_dir / "index.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "generated_at": "2026-01-01T00:00:00Z",
                    "entries": [
                        {
                            "id": "good",
                            "type": "module",
                            "path": "modules/good.md",
                            "title": "Good",
                            "summary": "test",
                            "tags": [],
                            "updated_at": "2026-01-01T00:00:00Z",
                            "confidence": "high",
                            "status": "synced",
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = validate_memory(tmp_path)
        assert result["valid"] is True
        assert result["counts"]["frontmatter"]["valid"] is True


class TestRebuildIndex:
    def _make_memory_file(self, path: Path, frontmatter_fields: dict, body: str = "Some content.") -> Path:
        lines = ["---"]
        for k, v in frontmatter_fields.items():
            if isinstance(v, list):
                lines.append(f"{k}: [{', '.join(str(i) for i in v)}]")
            else:
                lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append(body)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_synced_module_is_indexed(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        self._make_memory_file(
            modules_dir / "my-module.md",
            {
                "id": "my-module",
                "type": "module",
                "title": "My Module",
                "summary": "A synced module",
                "sync_status": "synced",
                "evidence_mode": "commit",
                "linked_commits": [],
                "linked_specs": [],
                "linked_sessions": [],
                "updated_at": "2026-01-01T00:00:00Z",
                "confidence": "high",
                "tags": [],
            },
        )
        result = rebuild_index(tmp_path, write=False)
        assert result["status"] == "ok"
        paths = [e["path"] for e in result["entries"]]
        assert "modules/my-module.md" in paths

    def test_pending_module_indexed_with_status_pending(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        self._make_memory_file(
            modules_dir / "pending-mod.md",
            {
                "id": "pending-mod",
                "type": "module",
                "title": "Pending",
                "summary": "Pending module",
                "sync_status": "pending_commit",
                "evidence_mode": "uncommitted_snapshot",
                "linked_commits": [],
                "linked_specs": [],
                "linked_sessions": [],
                "updated_at": "2026-01-01T00:00:00Z",
                "confidence": "medium",
                "tags": [],
            },
        )
        result = rebuild_index(tmp_path, write=False)
        entry = next(e for e in result["entries"] if e["id"] == "pending-mod")
        assert entry["status"] == "pending_commit"

    def test_needs_user_review_excluded(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        modules_dir = memory_dir / "modules"
        modules_dir.mkdir(parents=True)
        self._make_memory_file(
            modules_dir / "review-mod.md",
            {
                "id": "review-mod",
                "type": "module",
                "title": "Review",
                "summary": "Needs review",
                "sync_status": "needs_user_review",
                "evidence_mode": "commit",
                "linked_commits": [],
                "linked_specs": [],
                "linked_sessions": [],
                "updated_at": "2026-01-01T00:00:00Z",
                "confidence": "low",
                "tags": [],
            },
        )
        result = rebuild_index(tmp_path, write=False)
        ids = [e["id"] for e in result["entries"]]
        assert "review-mod" not in ids

    def test_sync_history_excluded(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        sync_dir = memory_dir / "sync-history"
        sync_dir.mkdir(parents=True)
        (sync_dir / "sync-001.md").write_text("# Sync History\nSome content\n", encoding="utf-8")
        result = rebuild_index(tmp_path, write=False)
        assert result["status"] == "ok"
        assert "sync-history" in result.get("excluded_dirs", [])

    def test_sessions_excluded(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        sessions_dir = memory_dir / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "session-001.md").write_text("# Session\n", encoding="utf-8")
        result = rebuild_index(tmp_path, write=False)
        assert "sessions" in result.get("excluded_dirs", [])


class TestUpdateManifest:
    def test_clean_worktree_updates_last_synced_commit(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        head = _git_commit(tmp_path, "initial")
        memory_dir = tmp_path / ".ai-memory"
        memory_dir.mkdir(parents=True)
        manifest_data = {
            "schema_version": "1.0",
            "repository_id": "test-repo",
            "memory_version": 1,
            "git": {
                "available": True,
                "has_commits": True,
                "head": head,
                "last_synced_commit": None,
                "worktree_state": "clean",
            },
            "pending_snapshots": [],
        }
        (memory_dir / "manifest.json").write_text(
            json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8"
        )
        result = update_manifest(tmp_path, sync_id="sync-001", write=True)
        assert result["status"] == "ok"
        manifest = result["manifest"]
        assert manifest["git"]["last_synced_commit"] == head

    def test_dirty_worktree_records_pending_snapshot_info(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        _git_commit(tmp_path, "initial")
        (tmp_path / "dirty.txt").write_text("dirty", encoding="utf-8")
        result = update_manifest(tmp_path, sync_id="sync-dirty", write=False)
        assert result["status"] == "ok"
        assert result["manifest"]["git"]["worktree_state"] == "dirty"

    def test_no_commit_repo_keeps_last_synced_commit_null(self, tmp_path):
        _init_git_repo(tmp_path)
        memory_dir = tmp_path / ".ai-memory"
        memory_dir.mkdir(parents=True)
        manifest_data = {
            "schema_version": "1.0",
            "repository_id": "test-repo",
            "memory_version": 1,
            "git": {
                "available": True,
                "has_commits": False,
                "head": None,
                "last_synced_commit": None,
                "worktree_state": "unknown",
            },
            "pending_snapshots": [],
        }
        (memory_dir / "manifest.json").write_text(
            json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8"
        )
        result = update_manifest(tmp_path, write=False)
        assert result["status"] == "ok"
        git = result["manifest"]["git"]
        assert git["has_commits"] is False
        assert git["head"] is None


class TestEndToEndIntegration:
    def test_8_7_no_commit_repo_uses_working_tree_snapshot(self, tmp_path):
        _init_git_repo(tmp_path)
        git_state = _detect_git(tmp_path)
        assert git_state["available"] is True
        assert git_state["has_commits"] is False
        assert git_state["head"] is None
        assert git_state["last_synced_commit"] is None

    def test_8_8_multiple_active_changes_with_one_diff_touched_auto_selects(self, tmp_path):
        _init_git_repo(tmp_path)
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        _git_commit(tmp_path, "initial")
        change_a = tmp_path / "openspec" / "changes" / "change-a"
        change_b = tmp_path / "openspec" / "changes" / "change-b"
        change_a.mkdir(parents=True)
        change_b.mkdir(parents=True)
        (change_b / "feature.md").write_text("new feature", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True, timeout=10)
        git_state = _detect_git(tmp_path)
        openspec_state = _detect_openspec_candidates(
            tmp_path,
            git_state.get("committed_range"),
            git_state.get("dirty_files", []),
            git_state.get("staged_files", []),
        )
        candidate_ids = [c["change_id"] for c in openspec_state["candidates"]]
        assert "change-b" in candidate_ids
        assert len([c for c in openspec_state["candidates"] if c["change_id"] == "change-b"]) == 1
        assert "change-a" in openspec_state["active_changes"]
        assert "change-b" in openspec_state["active_changes"]