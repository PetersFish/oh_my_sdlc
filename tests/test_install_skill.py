#!/usr/bin/env python3
"""Behavioral tests for install_skill.py no-op-on-unchanged-payload behavior."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL_SKILL = REPO_ROOT / "skills" / "meta-skill-lifecycle-governance" / "scripts" / "install_skill.py"


def _run_install(source_repo, skill_name, target, source_ref="HEAD", status="stable"):
    result = subprocess.run(
        [
            sys.executable, str(INSTALL_SKILL),
            "--source-repo", str(source_repo),
            "--skill-name", skill_name,
            "--source-ref", source_ref,
            "--target", str(target),
            "--status", status,
        ],
        capture_output=True, text=True,
    )
    return result


class TestInstallSkillNoOp(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="install-skill-test-")
        self.source_repo = tempfile.mkdtemp(prefix="source-repo-")
        skill_dir = pathlib.Path(self.source_repo) / "skills" / "demo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Demo Skill\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        shutil.rmtree(self.source_repo, ignore_errors=True)

    def test_second_install_with_unchanged_payload_is_noop(self):
        target = pathlib.Path(self.tmpdir) / "demo-skill"
        r1 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r1.returncode, 0)
        metadata_path = target / ".skill-install.json"
        original_metadata = metadata_path.read_text()
        original_mtime = metadata_path.stat().st_mtime_ns

        r2 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r2.returncode, 0)
        new_metadata = metadata_path.read_text()
        new_mtime = metadata_path.stat().st_mtime_ns

        self.assertEqual(original_metadata, new_metadata,
                         "metadata file must be byte-identical on no-op install")
        self.assertEqual(original_mtime, new_mtime,
                         "metadata file mtime must not change on no-op install")

    def test_install_with_changed_payload_updates_metadata(self):
        target = pathlib.Path(self.tmpdir) / "demo-skill"
        r1 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r1.returncode, 0)
        original_metadata = (target / ".skill-install.json").read_text()

        skill_md = pathlib.Path(self.source_repo) / "skills" / "demo-skill" / "SKILL.md"
        skill_md.write_text("# Demo Skill v2\nMore content.\n")

        r2 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r2.returncode, 0)
        new_metadata = (target / ".skill-install.json").read_text()

        self.assertNotEqual(original_metadata, new_metadata,
                            "metadata must change when payload changes")

    def test_noop_preserves_target_file_mtime(self):
        target = pathlib.Path(self.tmpdir) / "demo-skill"
        r1 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r1.returncode, 0)
        skill_md = target / "SKILL.md"
        original_mtime = skill_md.stat().st_mtime_ns

        r2 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r2.returncode, 0)
        new_mtime = skill_md.stat().st_mtime_ns

        self.assertEqual(original_mtime, new_mtime,
                         "target file mtime must not change on no-op install")


if __name__ == "__main__":
    unittest.main()