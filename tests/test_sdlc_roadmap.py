"""Tests for sdlc-roadmap skill: SKILL.md, templates, scripts, and distribution."""

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
ROADMAP_SKILL = REPO_ROOT / "skills" / "sdlc-roadmap"
OPENCODE_SKILL = REPO_ROOT / ".opencode" / "skills" / "sdlc-roadmap"
SCRIPTS_DIR = ROADMAP_SKILL / "scripts"


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    raw = text[3:end].strip()
    result = {}
    for line in raw.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _run_script(script: str, cwd: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _make_item(roadmap_dir: Path, item_id: str, **overrides) -> Path:
    frontmatter = {
        "id": item_id,
        "title": f"Test {item_id}",
        "status": "planned",
        "stage": "v1",
        "priority": "p0",
        "order": 10,
        "depends_on": [],
        "openspec_change": None,
        "created_at": "2026-06-09",
        "started_at": None,
        "completed_at": None,
        "patches": [],
    }
    frontmatter.update(overrides)

    lines = ["---"]
    for k, v in frontmatter.items():
        if isinstance(v, list):
            if v:
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{k}: []")
        elif v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append(f"\n# Goal\n\nTest goal for {item_id}.\n")
    lines.append("# Scope\n\n## In\n\n- Test scope\n\n## Out\n\n- Excluded\n")
    lines.append("# Acceptance Criteria\n\n- Test AC\n")
    lines.append("# Promotion Notes\n\nTest promotion notes.\n")
    lines.append("# Completion Notes\n\nNone yet.\n")

    path = roadmap_dir / "items" / f"{item_id}-test.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class TestRoadmapSkillFrontmatter(unittest.TestCase):
    def test_skill_md_exists(self) -> None:
        self.assertTrue(
            (ROADMAP_SKILL / "SKILL.md").exists(),
            "sdlc-roadmap/SKILL.md must exist",
        )

    def test_skill_md_has_valid_frontmatter(self) -> None:
        fm = _read_frontmatter(ROADMAP_SKILL / "SKILL.md")
        self.assertEqual(fm.get("name"), "sdlc-roadmap")
        self.assertIn("description", fm)
        self.assertGreater(len(fm["description"]), 20, "description too short")

    def test_skill_md_description_contains_keywords(self) -> None:
        fm = _read_frontmatter(ROADMAP_SKILL / "SKILL.md")
        desc = fm["description"].lower()
        self.assertIn("roadmap", desc)
        self.assertTrue(
            "mvp" in desc or "v2" in desc or "v3" in desc,
            "description should contain version keywords like MVP/V2/V3",
        )

    def test_skill_md_describes_state_machine(self) -> None:
        content = (ROADMAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("idea", content.lower())
        self.assertIn("planned", content.lower())
        self.assertIn("ready", content.lower())
        self.assertIn("active", content.lower())
        self.assertIn("done", content.lower())

    def test_skill_md_describes_boundary_rules(self) -> None:
        content = (ROADMAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("openspec", content.lower())
        self.assertIn("memory", content.lower())

    def test_skill_md_references_scripts(self) -> None:
        content = (ROADMAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("validate.py", content)
        self.assertIn("rebuild_index.py", content)
        self.assertIn("list.py", content)


class TestTemplates(unittest.TestCase):
    def test_roadmap_template_exists(self) -> None:
        self.assertTrue(
            (ROADMAP_SKILL / "templates" / "roadmap.md").exists(),
        )

    def test_item_template_exists(self) -> None:
        self.assertTrue(
            (ROADMAP_SKILL / "templates" / "item.md").exists(),
        )

    def test_item_template_has_required_frontmatter_fields(self) -> None:
        content = (ROADMAP_SKILL / "templates" / "item.md").read_text(encoding="utf-8")
        for field in ["id:", "title:", "status:", "stage:", "priority:", "order:", "depends_on:", "openspec_change:", "patches:"]:
            self.assertIn(field, content, f"item template missing field: {field}")

    def test_decisions_template_exists(self) -> None:
        self.assertTrue(
            (ROADMAP_SKILL / "templates" / "decisions.md").exists(),
        )


class TestValidateScript(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.roadmap_dir = Path(self.tmpdir) / ".roadmap"
        (self.roadmap_dir / "items").mkdir(parents=True)
        (self.roadmap_dir / "revisions").mkdir(parents=True)
        (self.roadmap_dir / "patches").mkdir(parents=True)
        (self.roadmap_dir / "roadmap.md").write_text("# Test Roadmap\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_invalid_status_detected(self) -> None:
        _make_item(self.roadmap_dir, "RM-001", status="unknown-status")
        result = _run_script("validate.py", self.tmpdir)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid status", result.stdout)

    def test_dangling_depends_on_detected(self) -> None:
        _make_item(self.roadmap_dir, "RM-001", depends_on=["RM-999"])
        result = _run_script("validate.py", self.tmpdir)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stdout)

    def test_index_item_mismatch_detected(self) -> None:
        _make_item(self.roadmap_dir, "RM-001", status="ready")
        index_path = self.roadmap_dir / "index.json"
        index_path.write_text(
            json.dumps({"version": 1, "items": [{"id": "RM-001", "status": "active"}]})
        )
        result = _run_script("validate.py", self.tmpdir)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mismatch", result.stdout)

    def test_valid_no_errors(self) -> None:
        _make_item(self.roadmap_dir, "RM-001", status="planned", order=10)
        _make_item(self.roadmap_dir, "RM-002", status="done", order=20, depends_on=["RM-001"])
        # Generate index via rebuild first
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "rebuild_index.py")],
            cwd=self.tmpdir,
            capture_output=True,
        )
        result = _run_script("validate.py", self.tmpdir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK", result.stdout)

    def test_missing_required_fields_detected(self) -> None:
        # Create item with missing 'order'
        item_path = self.roadmap_dir / "items" / "RM-001-test.md"
        content = """---
id: RM-001
title: Test Item
status: planned
stage: v1
priority: p0
depends_on: []
openspec_change: null
patches: []
---
# Goal
Missing order field."""
        item_path.write_text(content)
        result = _run_script("validate.py", self.tmpdir)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required fields", result.stdout)


class TestRebuildIndexScript(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.roadmap_dir = Path(self.tmpdir) / ".roadmap"
        (self.roadmap_dir / "items").mkdir(parents=True)
        (self.roadmap_dir / "revisions").mkdir(parents=True)
        (self.roadmap_dir / "patches").mkdir(parents=True)
        (self.roadmap_dir / "roadmap.md").write_text("# Test Roadmap\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_generate_from_items(self) -> None:
        _make_item(self.roadmap_dir, "RM-001", status="planned", order=10)
        _make_item(self.roadmap_dir, "RM-002", status="done", order=20)
        result = _run_script("rebuild_index.py", self.tmpdir)
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.roadmap_dir / "index.json").exists())
        data = json.loads((self.roadmap_dir / "index.json").read_text())
        self.assertEqual(len(data["items"]), 2)
        ids = [item["id"] for item in data["items"]]
        self.assertEqual(ids, ["RM-001", "RM-002"])  # sorted by order

    def test_empty_items_directory(self) -> None:
        result = _run_script("rebuild_index.py", self.tmpdir)
        self.assertEqual(result.returncode, 0)
        data = json.loads((self.roadmap_dir / "index.json").read_text())
        self.assertEqual(data["items"], [])

    def test_backup_existing_index(self) -> None:
        index_path = self.roadmap_dir / "index.json"
        original = json.dumps({"version": 1, "items": [{"id": "RM-OLD"}]})
        index_path.write_text(original)

        _make_item(self.roadmap_dir, "RM-001")
        result = _run_script("rebuild_index.py", self.tmpdir)
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.roadmap_dir / "index.json.bak").exists())
        self.assertEqual(
            (self.roadmap_dir / "index.json.bak").read_text(),
            original,
        )


class TestListScript(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.roadmap_dir = Path(self.tmpdir) / ".roadmap"
        (self.roadmap_dir / "items").mkdir(parents=True)
        (self.roadmap_dir / "revisions").mkdir(parents=True)
        (self.roadmap_dir / "patches").mkdir(parents=True)
        (self.roadmap_dir / "roadmap.md").write_text("# Test Roadmap\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_list_output(self) -> None:
        _make_item(self.roadmap_dir, "RM-001", status="ready", order=10)
        _make_item(self.roadmap_dir, "RM-002", status="planned", order=20)
        result = _run_script("list.py", self.tmpdir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("RM-001", result.stdout)
        self.assertIn("RM-002", result.stdout)
        self.assertIn("ready", result.stdout)
        self.assertIn("planned", result.stdout)
        # RM-001 should come before RM-002
        pos1 = result.stdout.index("RM-001")
        pos2 = result.stdout.index("RM-002")
        self.assertLess(pos1, pos2)

    def test_empty_items_directory(self) -> None:
        result = _run_script("list.py", self.tmpdir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("No roadmap items", result.stdout)


class TestDistribution(unittest.TestCase):
    def test_opencode_copy_exists(self) -> None:
        self.assertTrue(
            (OPENCODE_SKILL / "SKILL.md").exists(),
            ".opencode/skills/sdlc-roadmap/SKILL.md must exist",
        )

    def test_opencode_copy_matches_source(self) -> None:
        source = (ROADMAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        copy = (OPENCODE_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(source, copy, "opencode copy must match canonical source")


if __name__ == "__main__":
    unittest.main()
