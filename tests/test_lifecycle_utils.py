from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "meta-skill-lifecycle-governance" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from lifecycle_utils import build_install_metadata, classify_backport_candidate  # noqa: E402


class LifecycleUtilsTest(unittest.TestCase):
    def test_build_install_metadata_marks_stable_install(self) -> None:
        metadata = build_install_metadata(
            skill_name="meta-skill-lifecycle-governance",
            source_repo="/Users/yuping/Documents/workspace/oh_my_skills",
            source_ref="meta-skill-lifecycle-governance@1.0.0",
            status="stable",
            target="/Users/yuping/Documents/workspace/demo-project/.claude/skills/meta-skill-lifecycle-governance",
        )

        self.assertEqual(metadata["skill"], "meta-skill-lifecycle-governance")
        self.assertEqual(metadata["status"], "stable")
        self.assertEqual(metadata["source_ref"], "meta-skill-lifecycle-governance@1.0.0")
        self.assertEqual(
            metadata["target"],
            "/Users/yuping/Documents/workspace/demo-project/.claude/skills/meta-skill-lifecycle-governance",
        )

    def test_classify_backport_candidate_detects_project_overlay(self) -> None:
        result = classify_backport_candidate(
            "This change hardcodes a project-specific vault path and depends on the current project naming scheme.\n"
        )

        self.assertEqual(result, "project-overlay")


if __name__ == "__main__":
    unittest.main()
