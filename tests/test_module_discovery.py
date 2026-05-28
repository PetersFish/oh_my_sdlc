from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPTS_DIR = REPO_ROOT / "skills" / "sdlc-repository-memory-sync" / "scripts"
INIT_SCRIPTS_DIR = REPO_ROOT / "skills" / "sdlc-repository-memory-init" / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_discover_mod = _load_module("discover_modules", SYNC_SCRIPTS_DIR / "discover_modules.py")
_init_mod = _load_module("init_memory_disc", INIT_SCRIPTS_DIR / "init_memory.py")
_rebuild_mod = _load_module("rebuild_index_disc", SYNC_SCRIPTS_DIR / "rebuild_index.py")
_validate_mod = _load_module("validate_memory_disc", SYNC_SCRIPTS_DIR / "validate_memory.py")

discover_modules = _discover_mod.discover_modules
init_memory = _init_mod.init_memory
rebuild_index = _rebuild_mod.rebuild_index
validate_memory = _validate_mod.validate_memory


class TestDiscoverModules:
    def test_rule_a_directory_with_files_is_candidate(self, tmp_path):
        skills_dir = tmp_path / "skills" / "my-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: A test skill\n---\n# My Skill\n",
            encoding="utf-8",
        )
        (skills_dir / "helper.py").write_text("", encoding="utf-8")

        result = discover_modules(tmp_path)
        candidates = [c for c in result["candidates"] if c["path"] == "skills/my-skill"]

        assert len(candidates) == 1
        c = candidates[0]
        assert c["disposition"] == "new"
        assert c["has_skill_md"] is True
        assert c["frontmatter_name"] == "my-skill"
        assert c["frontmatter_description"] == "A test skill"
        assert c["depth"] == 2
        assert ".py" in c["file_types"] or ".md" in c["file_types"]

    def test_rule_b_directory_with_two_or_more_subdirs_is_candidate(self, tmp_path):
        parent = tmp_path / "skills"
        parent.mkdir()
        (parent / "skill-a").mkdir()
        (parent / "skill-b").mkdir()

        result = discover_modules(tmp_path)
        candidates = [c for c in result["candidates"] if c["path"] == "skills"]

        assert len(candidates) == 1
        c = candidates[0]
        assert c["disposition"] == "new"
        assert c["depth"] == 1

    def test_intermediate_path_with_one_subdir_no_files_is_skipped(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main").mkdir()
        (tmp_path / "src" / "main" / "java").mkdir()
        (tmp_path / "src" / "main" / "java" / "Service.java").write_text(
            "class Service {}", encoding="utf-8"
        )

        result = discover_modules(tmp_path)
        paths = [c["path"] for c in result["candidates"]]

        assert "src" not in paths
        assert "src/main" not in paths
        assert "src/main/java" in paths

    def test_hidden_directories_are_excluded(self, tmp_path):
        (tmp_path / ".hidden-dir").mkdir()
        (tmp_path / ".hidden-dir" / "file.txt").write_text("", encoding="utf-8")
        (tmp_path / "visible-dir").mkdir()
        (tmp_path / "visible-dir" / "file.txt").write_text("", encoding="utf-8")

        result = discover_modules(tmp_path)
        paths = [c["path"] for c in result["candidates"]]

        assert ".hidden-dir" not in paths
        assert "visible-dir" in paths

    def test_exclude_patterns_respected(self, tmp_path):
        (tmp_path / "target").mkdir()
        (tmp_path / "target" / "classes").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "Main.java").write_text("", encoding="utf-8")

        result = discover_modules(tmp_path)
        paths = [c["path"] for c in result["candidates"]]

        assert "target" not in paths
        assert "src" in paths

    def test_max_depth_limits_traversal(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b").mkdir()
        (tmp_path / "a" / "b" / "c").mkdir()
        (tmp_path / "a" / "b" / "c" / "d").mkdir()
        (tmp_path / "a" / "b" / "c" / "d" / "e").mkdir()
        (tmp_path / "a" / "b" / "c" / "d" / "e" / "f").mkdir()
        (tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "leaf.txt").write_text(
            "", encoding="utf-8"
        )

        result = discover_modules(tmp_path)
        depths = [c["depth"] for c in result["candidates"]]

        assert all(d <= 5 for d in depths)

    def test_candidates_marked_by_disposition_from_prefs(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "accepted-skill").mkdir()
        (skills_dir / "accepted-skill" / "SKILL.md").write_text(
            "---\nname: ok\n---\n", encoding="utf-8"
        )
        (skills_dir / "rejected-skill").mkdir()
        (skills_dir / "rejected-skill" / "SKILL.md").write_text(
            "---\nname: nope\n---\n", encoding="utf-8"
        )
        (skills_dir / "new-skill").mkdir()
        (skills_dir / "new-skill" / "SKILL.md").write_text(
            "---\nname: fresh\n---\n", encoding="utf-8"
        )

        ai_memory = tmp_path / ".ai-memory"
        ai_memory.mkdir()
        prefs = {
            "schema_version": "1.0",
            "exclude_patterns": [],
            "scan_paths": None,
            "max_depth": 5,
            "module_map": {
                "accepted": {
                    "fs_path": "skills/accepted-skill",
                    "status": "accepted",
                    "memory_id": "accepted-skill",
                    "memory_path": "modules/accepted-skill.md",
                    "confirmed_at": "2026-01-01T00:00:00Z",
                },
                "rejected": {
                    "fs_path": "skills/rejected-skill",
                    "status": "rejected",
                    "reason_rejected": "Not a real module",
                    "rejected_at": "2026-01-01T00:00:00Z",
                },
            },
        }
        (ai_memory / "discovery-prefs.json").write_text(
            json.dumps(prefs, indent=2), encoding="utf-8"
        )

        result = discover_modules(tmp_path)
        by_path = {c["path"]: c for c in result["candidates"]}

        assert by_path["skills/accepted-skill"]["disposition"] == "known"
        assert by_path["skills/rejected-skill"]["disposition"] == "previously_rejected"
        assert by_path["skills/new-skill"]["disposition"] == "new"

    def test_java_deep_package_discovered_with_build_file(self, tmp_path):
        service_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
        service_dir.mkdir(parents=True)
        (service_dir / "StringUtils.java").write_text(
            "package org.apache.common;", encoding="utf-8"
        )
        (service_dir / "pom.xml").write_text("<project></project>", encoding="utf-8")

        result = discover_modules(tmp_path)
        candidates = [c for c in result["candidates"]
                      if c["path"] == "src/main/java/com/example"]

        assert len(candidates) == 1
        c = candidates[0]
        assert c["depth"] == 5
        assert c["has_build_file"] == "pom.xml"
        assert ".java" in c["file_types"]
        assert "pom.xml" in c["top_level_files"] or "StringUtils.java" in c["top_level_files"]

    def test_module_with_multiple_build_files_returns_first_match(self, tmp_path):
        shared_dir = tmp_path / "shared-lib"
        shared_dir.mkdir()
        (shared_dir / "package.json").write_text("{}", encoding="utf-8")
        (shared_dir / "Makefile").write_text("all:", encoding="utf-8")
        (shared_dir / "index.ts").write_text("export {}", encoding="utf-8")

        result = discover_modules(tmp_path)
        candidates = [c for c in result["candidates"] if c["path"] == "shared-lib"]

        assert len(candidates) == 1
        assert candidates[0]["has_build_file"] in ("package.json", "Makefile", "Dockerfile")

    def test_stats_counts_are_correct(self, tmp_path):
        (tmp_path / "skills").mkdir()
        (tmp_path / "skills" / "skill-a").mkdir()
        (tmp_path / "skills" / "skill-a" / "SKILL.md").write_text(
            "---\nname: a\n---\n", encoding="utf-8"
        )
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "secret.txt").write_text("", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "readme.md").write_text("", encoding="utf-8")

        result = discover_modules(tmp_path)
        stats = result["stats"]

        assert stats["candidates"] >= 2
        assert stats["new"] >= 0
        assert stats["known"] == 0
        assert stats["excluded"] >= 1

    def test_child_discovery_scans_accepted_parent_and_reports_linkage(self, tmp_path):
        parent = tmp_path / "skills"
        child = parent / "memory-sync"
        child.mkdir(parents=True)
        (child / "SKILL.md").write_text(
            "---\nname: memory-sync\ndescription: Sync memory\n---\n",
            encoding="utf-8",
        )
        (child / "scripts").mkdir()
        (child / "scripts" / "sync.py").write_text("", encoding="utf-8")
        ai_memory = tmp_path / ".ai-memory"
        ai_memory.mkdir()
        (ai_memory / "discovery-prefs.json").write_text(
            json.dumps({
                "schema_version": "1.0",
                "exclude_patterns": [],
                "scan_paths": None,
                "max_depth": 5,
                "module_map": {
                    "skills": {
                        "fs_path": "skills",
                        "status": "accepted",
                        "memory_id": "modules/skills",
                        "memory_path": "modules/skills.md",
                        "confirmed_at": "2026-01-01T00:00:00Z",
                    },
                },
            }),
            encoding="utf-8",
        )

        result = discover_modules(tmp_path)
        child_candidates = result["child_candidates"]
        by_path = {c["path"]: c for c in child_candidates}

        assert "skills/memory-sync" in by_path
        assert by_path["skills/memory-sync"]["parent_id"] == "modules/skills"
        assert by_path["skills/memory-sync"]["parent_path"] == "skills"

    def test_child_scoring_classifies_high_medium_and_low_confidence(self, tmp_path):
        parent = tmp_path / "skills"
        high = parent / "high-skill"
        medium = parent / "medium-skill"
        low = parent / "assets"
        high.mkdir(parents=True)
        medium.mkdir()
        low.mkdir()
        (high / "SKILL.md").write_text("---\nname: high\n---\n", encoding="utf-8")
        (high / "scripts").mkdir()
        (high / "scripts" / "run.py").write_text("", encoding="utf-8")
        (high / "templates").mkdir()
        (high / "templates" / "t.md").write_text("", encoding="utf-8")
        (medium / "SKILL.md").write_text("---\nname: medium\n---\n", encoding="utf-8")
        (low / "image.png").write_text("", encoding="utf-8")
        ai_memory = tmp_path / ".ai-memory"
        ai_memory.mkdir()
        (ai_memory / "discovery-prefs.json").write_text(
            json.dumps({
                "schema_version": "1.0",
                "exclude_patterns": [],
                "scan_paths": None,
                "max_depth": 5,
                "module_map": {
                    "skills": {
                        "fs_path": "skills",
                        "status": "accepted",
                        "memory_id": "modules/skills",
                        "memory_path": "modules/skills.md",
                        "confirmed_at": "2026-01-01T00:00:00Z",
                    },
                },
            }),
            encoding="utf-8",
        )

        result = discover_modules(tmp_path)
        by_path = {c["path"]: c for c in result["child_candidates"]}

        assert by_path["skills/high-skill"]["confidence_band"] == "high"
        assert by_path["skills/high-skill"]["score"] > 7
        assert by_path["skills/medium-skill"]["confidence_band"] == "medium"
        assert 5 <= by_path["skills/medium-skill"]["score"] <= 7
        assert by_path["skills/assets"]["confidence_band"] == "low"
        assert by_path["skills/assets"]["score"] < 5

    def test_accepted_child_is_not_scanned_for_grandchildren(self, tmp_path):
        child = tmp_path / "skills" / "repository-memory"
        grandchild = child / "scripts"
        grandchild.mkdir(parents=True)
        (grandchild / "sync.py").write_text("", encoding="utf-8")
        ai_memory = tmp_path / ".ai-memory"
        ai_memory.mkdir()
        (ai_memory / "discovery-prefs.json").write_text(
            json.dumps({
                "schema_version": "1.0",
                "exclude_patterns": [],
                "scan_paths": None,
                "max_depth": 5,
                "module_map": {
                    "skills": {
                        "fs_path": "skills",
                        "status": "accepted",
                        "memory_id": "modules/skills",
                        "memory_path": "modules/skills.md",
                        "confirmed_at": "2026-01-01T00:00:00Z",
                    },
                    "skills/repository-memory": {
                        "fs_path": "skills/repository-memory",
                        "status": "accepted",
                        "memory_id": "modules/skills/repository-memory",
                        "memory_path": "modules/skills/repository-memory.md",
                        "parent_id": "modules/skills",
                        "confirmed_at": "2026-01-01T00:00:00Z",
                    },
                },
            }),
            encoding="utf-8",
        )

        result = discover_modules(tmp_path)
        child_paths = [c["path"] for c in result["child_candidates"]]

        assert "skills/repository-memory/scripts" not in child_paths


class TestInitMemoryDiscoveryPrefs:
    def test_init_creates_discovery_prefs_with_defaults(self, tmp_path):
        result = init_memory(tmp_path)

        prefs_path = tmp_path / ".ai-memory" / "discovery-prefs.json"
        assert prefs_path.exists()

        prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
        assert prefs["schema_version"] == "1.0"
        assert prefs["max_depth"] == 5
        assert prefs["scan_paths"] is None
        assert isinstance(prefs["exclude_patterns"], list)
        assert "node_modules" in prefs["exclude_patterns"]
        assert ".git" in prefs["exclude_patterns"]
        assert prefs["module_map"] == {}

    def test_reinit_does_not_overwrite_existing_discovery_prefs(self, tmp_path):
        init_memory(tmp_path)

        prefs_path = tmp_path / ".ai-memory" / "discovery-prefs.json"
        prefs_path.write_text(
            json.dumps({
                "schema_version": "1.0",
                "exclude_patterns": ["custom"],
                "scan_paths": None,
                "max_depth": 3,
                "module_map": {
                    "test": {
                        "fs_path": "skills/test",
                        "status": "accepted",
                        "memory_id": "test",
                        "memory_path": "modules/test.md",
                        "confirmed_at": "2026-01-01T00:00:00Z",
                    },
                },
            }, indent=2),
            encoding="utf-8",
        )

        init_memory(tmp_path)

        prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
        assert prefs["exclude_patterns"] == ["custom"]
        assert prefs["max_depth"] == 3
        assert "test" in prefs["module_map"]


class TestRebuildIndexNestedModules:
    def _make_memory_file(self, path: Path, frontmatter_fields: dict, body: str = "Some content.") -> Path:
        lines = ["---"]
        for k, v in frontmatter_fields.items():
            if isinstance(v, list):
                lines.append(f"{k}: [{', '.join(str(i) for i in v)}]")
            else:
                lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append(body)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_nested_module_directories_are_scanned(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        self._make_memory_file(
            memory_dir / "modules" / "group-a" / "sub-module.md",
            {
                "id": "sub-module",
                "type": "module",
                "title": "Sub Module",
                "summary": "A nested module",
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
        paths = [e["path"] for e in result["entries"]]

        assert "modules/group-a/sub-module.md" in paths
        assert any(e["id"] == "sub-module" for e in result["entries"])

    def test_flat_module_directories_still_work(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        self._make_memory_file(
            memory_dir / "modules" / "flat-module.md",
            {
                "id": "flat-module",
                "type": "module",
                "title": "Flat Module",
                "summary": "A flat module",
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
        paths = [e["path"] for e in result["entries"]]

        assert "modules/flat-module.md" in paths


class TestValidateDiscoveryPrefsSchema:
    def _write_manifest(self, memory_dir: Path) -> None:
        memory_dir.mkdir(parents=True, exist_ok=True)
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
        (memory_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    def test_valid_discovery_prefs_validates(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        self._write_manifest(memory_dir)
        (memory_dir / "index.json").write_text(
            json.dumps(
                {"schema_version": "1.0", "generated_at": "2026-01-01T00:00:00Z", "entries": []}
            ) + "\n",
            encoding="utf-8",
        )
        (memory_dir / "discovery-prefs.json").write_text(
            json.dumps({
                "schema_version": "1.0",
                "exclude_patterns": [],
                "scan_paths": None,
                "max_depth": 5,
                "module_map": {},
            }, indent=2) + "\n",
            encoding="utf-8",
        )

        result = validate_memory(tmp_path)
        assert result["valid"] is True

    def test_invalid_discovery_prefs_missing_status_reports_error(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        self._write_manifest(memory_dir)
        (memory_dir / "index.json").write_text(
            json.dumps(
                {"schema_version": "1.0", "generated_at": "2026-01-01T00:00:00Z", "entries": []}
            ) + "\n",
            encoding="utf-8",
        )
        (memory_dir / "discovery-prefs.json").write_text(
            json.dumps({
                "schema_version": "1.0",
                "exclude_patterns": [],
                "scan_paths": None,
                "max_depth": 5,
                "module_map": {
                    "bad-entry": {
                        "fs_path": "skills/bad",
                        "memory_id": "bad",
                        "memory_path": "modules/bad.md",
                    },
                },
            }, indent=2) + "\n",
            encoding="utf-8",
        )

        result = validate_memory(tmp_path)
        assert result["valid"] is False

    def test_legacy_discovery_prefs_path_and_reason_validate(self, tmp_path):
        memory_dir = tmp_path / ".ai-memory"
        self._write_manifest(memory_dir)
        (memory_dir / "index.json").write_text(
            json.dumps({"schema_version": "1.0", "generated_at": "2026-01-01T00:00:00Z", "entries": []}) + "\n",
            encoding="utf-8",
        )
        (memory_dir / "discovery-prefs.json").write_text(
            json.dumps({
                "schema_version": "1.0",
                "exclude_patterns": [],
                "scan_paths": None,
                "max_depth": 5,
                "module_map": {
                    "accepted": {"path": "skills", "status": "accepted", "memory_id": "modules/skills"},
                    "rejected": {"path": "skills/old", "status": "rejected", "reason": "contained"},
                },
            }) + "\n",
            encoding="utf-8",
        )

        result = validate_memory(tmp_path)

        assert result["valid"] is True
