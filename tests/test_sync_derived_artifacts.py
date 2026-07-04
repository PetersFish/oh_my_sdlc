#!/usr/bin/env python3
"""Behavioral tests for scripts/sync_derived_artifacts.py — aggregate check/fix."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from subprocess import CompletedProcess
from unittest import mock

SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "sync_derived_artifacts.py",
)


def _import_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("sync_derived_artifacts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_file(root: str, relpath: str, content: str = "x\n") -> str:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestSyncDerivedArtifacts(unittest.TestCase):
    """Aggregate entrypoint composes existing sync/distribution scripts."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_check(self, monkeypatch_subprocess):
        mod = _import_module()
        rc = mod.run_aggregate(self.tmp, mode="check", json_output=True)
        out = sys.stdout.getvalue() if hasattr(sys.stdout, "getvalue") else ""
        return rc, out

    def test_check_runs_workflow_template_and_agent_and_skill_checks(self):
        calls = []

        def fake_run(args, capture_output, text):
            calls.append(args)
            return CompletedProcess(args, 0, "OK", "")

        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(self.tmp, mode="check", json_output=False)

        self.assertEqual(rc, 0)
        # workflow template check
        self.assertTrue(
            any("sync_templates.py" in " ".join(cmd) and "--check" in cmd for cmd in calls),
            f"expected sync_templates.py --check in calls: {calls}",
        )
        # workflow distributed check
        self.assertTrue(
            any("sync_templates.py" in " ".join(cmd) and "--check-distributed" in cmd for cmd in calls),
            f"expected sync_templates.py --check-distributed in calls: {calls}",
        )
        # agent checks
        self.assertTrue(
            any("setup_agents.py" in " ".join(cmd) and "--check" in cmd for cmd in calls),
            f"expected setup_agents.py --check in calls: {calls}",
        )
        # skill distribution check
        self.assertTrue(
            any("check_skill_distribution.py" in " ".join(cmd) for cmd in calls),
            f"expected check_skill_distribution.py in calls: {calls}",
        )

    def test_check_propagates_failure_from_any_suite(self):
        def fake_run(args, capture_output, text):
            # workflow --check fails
            if "--check" in args and "sync_templates.py" in " ".join(args):
                return CompletedProcess(args, 1, "drift", "")
            return CompletedProcess(args, 0, "OK", "")

        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(self.tmp, mode="check", json_output=False)

        self.assertNotEqual(rc, 0, "check must propagate failure")

    def test_fix_runs_sync_templates_distribute_and_agent_force(self):
        calls = []

        def fake_run(args, capture_output, text):
            calls.append(args)
            return CompletedProcess(args, 0, "OK", "")

        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(self.tmp, mode="fix", json_output=False)

        self.assertEqual(rc, 0)
        # sync (live -> canonical)
        self.assertTrue(
            any("sync_templates.py" in " ".join(cmd) and "--root" in cmd
                and "--check" not in cmd and "--distribute" not in cmd for cmd in calls),
            f"expected sync_templates.py sync (no --check/--distribute) in calls: {calls}",
        )
        # distribute
        self.assertTrue(
            any("--distribute" in cmd for cmd in calls),
            f"expected --distribute in calls: {calls}",
        )
        # agent force install for all three targets
        for target_suffix in (".opencode/agents", ".claude/agents", ".cursor/agents"):
            self.assertTrue(
                any("setup_agents.py" in " ".join(cmd) and "--force" in cmd
                    and target_suffix in " ".join(cmd) for cmd in calls),
                f"expected setup_agents.py --force for {target_suffix} in calls: {calls}",
            )

    def test_fix_installs_all_canonical_skills_to_each_target(self):
        # Create two canonical skills
        write_file(self.tmp, "skills/demo-skill/SKILL.md", "# demo\n")
        write_file(self.tmp, "skills/other-skill/SKILL.md", "# other\n")

        calls = []

        def fake_run(args, capture_output, text):
            calls.append(args)
            return CompletedProcess(args, 0, "OK", "")

        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(self.tmp, mode="fix", json_output=False)

        self.assertEqual(rc, 0)
        install_cmds = [cmd for cmd in calls if "install_skill.py" in " ".join(cmd)]
        self.assertGreaterEqual(len(install_cmds), 6,
                                f"expected at least 6 install_skill.py calls (2 skills x 3 targets), got {len(install_cmds)}")
        # Each skill must be installed to each of the three targets
        for skill in ("demo-skill", "other-skill"):
            for target_suffix in (".opencode/skills", ".claude/skills", ".cursor/skills"):
                self.assertTrue(
                    any(skill in " ".join(cmd) and target_suffix in " ".join(cmd) for cmd in install_cmds),
                    f"expected install_skill.py for {skill} -> {target_suffix}",
                )

    def test_json_output_emits_structured_report(self):
        def fake_run(args, capture_output, text):
            return CompletedProcess(args, 0, "OK", "")

        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, report = mod.run_aggregate(self.tmp, mode="check", json_output=True)

        self.assertEqual(rc, 0)
        self.assertIsInstance(report, dict)
        self.assertIn("suites", report)
        self.assertIn("status", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)