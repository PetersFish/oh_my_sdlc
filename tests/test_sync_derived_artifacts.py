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


class TestIncrementalSync(unittest.TestCase):
    """Changed-file aware incremental check/fix behavior."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _capture_calls(self):
        calls = []

        def fake_run(args, capture_output, text):
            calls.append(args)
            return CompletedProcess(args, 0, "OK", "")

        return calls, fake_run

    def test_incremental_fix_docs_only_runs_no_suites(self):
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, report = mod.run_aggregate(
                self.tmp, mode="fix", json_output=True,
                changed_files=["docs/superpowers/specs/example.md"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [], "no subprocess commands should run for docs-only changes")
        self.assertEqual(report["scope"], "skipped")
        self.assertEqual(report["affected"]["skills"], [])
        self.assertFalse(report["affected"]["agents"])
        self.assertFalse(report["affected"]["workflows"])

    def test_incremental_check_docs_only_runs_no_suites(self):
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, report = mod.run_aggregate(
                self.tmp, mode="check", json_output=True,
                changed_files=["docs/superpowers/specs/example.md"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])
        self.assertEqual(report["scope"], "skipped")
        # No workflow, agent, or skill checks
        self.assertFalse(any("sync_templates.py" in " ".join(c) for c in calls))
        self.assertFalse(any("setup_agents.py" in " ".join(c) for c in calls))
        self.assertFalse(any("check_skill_distribution.py" in " ".join(c) for c in calls))

    def test_incremental_fix_single_skill_installs_only_that_skill(self):
        write_file(self.tmp, "skills/demo-skill/SKILL.md", "# demo\n")
        write_file(self.tmp, "skills/other-skill/SKILL.md", "# other\n")
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(
                self.tmp, mode="fix", json_output=False,
                changed_files=["skills/demo-skill/SKILL.md"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        demo_install_cmds = [
            cmd for cmd in calls
            if "install_skill.py" in " ".join(cmd) and "demo-skill" in " ".join(cmd)
        ]
        other_install_cmds = [
            cmd for cmd in calls
            if "install_skill.py" in " ".join(cmd) and "other-skill" in " ".join(cmd)
        ]
        self.assertEqual(len(demo_install_cmds), 3,
                         f"expected exactly 3 install_skill.py commands for demo-skill, got {demo_install_cmds}")
        self.assertEqual(other_install_cmds, [], "other-skill must not be installed")
        self.assertFalse(any("setup_agents.py" in " ".join(cmd) for cmd in calls),
                         "agent setup must not run for skill-only changes")
        self.assertFalse(any("sync_templates.py" in " ".join(cmd) for cmd in calls),
                         "workflow sync must not run for skill-only changes")

    def test_incremental_fix_multi_skill_installs_only_affected_skills(self):
        write_file(self.tmp, "skills/demo-skill/SKILL.md", "# demo\n")
        write_file(self.tmp, "skills/other-skill/SKILL.md", "# other\n")
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(
                self.tmp, mode="fix", json_output=False,
                changed_files=[
                    "skills/demo-skill/SKILL.md",
                    "skills/other-skill/templates/foo.md",
                ],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        for skill in ("demo-skill", "other-skill"):
            skill_cmds = [
                cmd for cmd in calls
                if "install_skill.py" in " ".join(cmd) and f"--skill-name" in " ".join(cmd)
                and skill in " ".join(cmd)
            ]
            self.assertEqual(len(skill_cmds), 3,
                             f"expected 3 install commands for {skill}, got {skill_cmds}")
        # No unrelated skill
        for cmd in calls:
            if "install_skill.py" in " ".join(cmd):
                # Ensure the skill-name arg is one of the affected ones
                idx = cmd.index("--skill-name")
                self.assertIn(cmd[idx + 1], ("demo-skill", "other-skill"))

    def test_incremental_check_single_skill_passes_skills_filter(self):
        write_file(self.tmp, "skills/demo-skill/SKILL.md", "# demo\n")
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(
                self.tmp, mode="check", json_output=False,
                changed_files=["skills/demo-skill/scripts/tool.py"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        skill_check_cmds = [
            cmd for cmd in calls if "check_skill_distribution.py" in " ".join(cmd)
        ]
        self.assertEqual(len(skill_check_cmds), 1,
                         f"expected exactly one skill distribution check, got {skill_check_cmds}")
        self.assertIn("--skills", skill_check_cmds[0])
        self.assertIn("demo-skill", skill_check_cmds[0])
        self.assertFalse(any("setup_agents.py" in " ".join(cmd) for cmd in calls))
        self.assertFalse(any("sync_templates.py" in " ".join(cmd) for cmd in calls))

    def test_incremental_fix_agent_only_runs_agent_setup(self):
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(
                self.tmp, mode="fix", json_output=False,
                changed_files=["agents/implement-agent.md"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        force_cmds = [
            cmd for cmd in calls
            if "setup_agents.py" in " ".join(cmd) and "--force" in cmd
        ]
        self.assertEqual(len(force_cmds), 3,
                         f"expected 3 setup_agents.py --force commands, got {force_cmds}")
        self.assertFalse(any("install_skill.py" in " ".join(cmd) for cmd in calls))
        self.assertFalse(any("sync_templates.py" in " ".join(cmd) for cmd in calls))

    def test_incremental_check_agent_only_runs_agent_checks(self):
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(
                self.tmp, mode="check", json_output=False,
                changed_files=["agents/config/model-profiles.yaml"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        check_cmds = [
            cmd for cmd in calls
            if "setup_agents.py" in " ".join(cmd) and "--check" in cmd
        ]
        self.assertEqual(len(check_cmds), 3,
                         f"expected 3 setup_agents.py --check commands, got {check_cmds}")
        self.assertFalse(any("check_skill_distribution.py" in " ".join(cmd) for cmd in calls))
        self.assertFalse(any("sync_templates.py" in " ".join(cmd) for cmd in calls))

    def test_incremental_fix_workflow_only_runs_workflow_sync(self):
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(
                self.tmp, mode="fix", json_output=False,
                changed_files=[".ai/workflows/scripts/workflow.py"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        sync_cmds = [
            cmd for cmd in calls
            if "sync_templates.py" in " ".join(cmd) and "--root" in " ".join(cmd)
            and "--check" not in cmd and "--distribute" not in cmd
        ]
        dist_cmds = [cmd for cmd in calls if "--distribute" in cmd]
        self.assertEqual(len(sync_cmds), 1, f"expected one workflow sync command, got {sync_cmds}")
        self.assertEqual(len(dist_cmds), 1, f"expected one workflow distribute command, got {dist_cmds}")
        self.assertFalse(any("setup_agents.py" in " ".join(cmd) for cmd in calls))
        self.assertFalse(any("install_skill.py" in " ".join(cmd) for cmd in calls))

    def test_incremental_check_workflow_only_runs_workflow_checks(self):
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, _ = mod.run_aggregate(
                self.tmp, mode="check", json_output=False,
                changed_files=[".ai/workflows/definitions/sdlc-main.yaml"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        check_cmds = [cmd for cmd in calls if "sync_templates.py" in " ".join(cmd) and "--check" in cmd and "--check-distributed" not in cmd]
        check_dist_cmds = [cmd for cmd in calls if "--check-distributed" in cmd]
        self.assertEqual(len(check_cmds), 1, f"expected one --check command, got {check_cmds}")
        self.assertEqual(len(check_dist_cmds), 1, f"expected one --check-distributed command, got {check_dist_cmds}")
        self.assertFalse(any("setup_agents.py" in " ".join(cmd) for cmd in calls))
        self.assertFalse(any("check_skill_distribution.py" in " ".join(cmd) for cmd in calls))

    def test_incremental_fix_sync_rule_change_falls_back_to_full(self):
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, report = mod.run_aggregate(
                self.tmp, mode="fix", json_output=True,
                changed_files=["scripts/sync_derived_artifacts.py"],
                incremental=True,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(report["scope"], "full")
        # Full-mode command categories present: workflow sync, distribute, agent force, skill install
        self.assertTrue(any("sync_templates.py" in " ".join(cmd) and "--root" in " ".join(cmd)
                            and "--check" not in cmd and "--distribute" not in cmd for cmd in calls))
        self.assertTrue(any("--distribute" in cmd for cmd in calls))
        self.assertTrue(any("setup_agents.py" in " ".join(cmd) and "--force" in cmd for cmd in calls))

    def test_changed_files_from_git_collects_tracked_and_untracked(self):
        mod = _import_module()
        git_diff_output = "docs/foo.md\nskills/demo-skill/SKILL.md\n"
        git_lsfiles_output = "agents/new-agent.md\nskills/demo-skill/SKILL.md\n"

        def fake_run(args, capture_output, text):
            if "diff" in " ".join(args) and "--name-only" in args:
                return CompletedProcess(args, 0, git_diff_output, "")
            if "ls-files" in " ".join(args) and "--others" in args:
                return CompletedProcess(args, 0, git_lsfiles_output, "")
            return CompletedProcess(args, 0, "", "")

        with mock.patch.object(subprocess, "run", fake_run):
            changed = mod.discover_changed_files_from_git(self.tmp)
        # Deduplicated and deterministic
        self.assertEqual(changed, sorted(set(changed)))
        self.assertIn("docs/foo.md", changed)
        self.assertIn("skills/demo-skill/SKILL.md", changed)
        self.assertIn("agents/new-agent.md", changed)
        # Duplicate skill path appears only once
        self.assertEqual(changed.count("skills/demo-skill/SKILL.md"), 1)

    def test_changed_files_from_git_error_when_discovery_fails(self):
        mod = _import_module()

        def fake_run(args, capture_output, text):
            return CompletedProcess(args, 1, "", "git error")

        with mock.patch.object(subprocess, "run", fake_run):
            with self.assertRaises(Exception):
                mod.discover_changed_files_from_git(self.tmp)

    def test_incremental_fix_deleted_skill_returns_error_no_install(self):
        """Task 3 Step 3: deleted/renamed skill directory must not blindly call
        install_skill.py. The preflight must return a non-zero report listing
        the missing skill name and must not run any install_skill.py subprocess
        for that missing skill."""
        # No skills/deleted-skill/ directory exists on disk.
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, report = mod.run_aggregate(
                self.tmp, mode="fix", json_output=True,
                changed_files=["skills/deleted-skill/SKILL.md"],
                incremental=True,
            )
        # Non-zero return: missing canonical skill is a blocked/error state.
        self.assertNotEqual(rc, 0,
                            "incremental fix must not silently succeed for a "
                            "deleted canonical skill directory")
        # No install_skill.py subprocess calls for the missing skill.
        install_cmds = [
            cmd for cmd in calls
            if "install_skill.py" in " ".join(cmd)
            and "deleted-skill" in " ".join(cmd)
        ]
        self.assertEqual(install_cmds, [],
                         f"expected no install_skill.py calls for missing "
                         f"deleted-skill, got {install_cmds}")
        # The missing skill name must appear in the JSON report.
        self.assertIsNotNone(report, "JSON report must be emitted on error")
        missing_skills = report.get("missing_skills", [])
        self.assertIn("deleted-skill", missing_skills,
                      f"deleted-skill must be listed in report.missing_skills, "
                      f"got report={report}")

    def test_incremental_fix_mixed_present_and_missing_skills_installs_only_present(self):
        """When a change set contains both a present and a missing skill,
        the present skill is installed normally and the missing skill is
        reported without any install calls for it."""
        write_file(self.tmp, "skills/present-skill/SKILL.md", "# present\n")
        calls, fake_run = self._capture_calls()
        with mock.patch.object(subprocess, "run", fake_run):
            mod = _import_module()
            rc, report = mod.run_aggregate(
                self.tmp, mode="fix", json_output=True,
                changed_files=[
                    "skills/present-skill/SKILL.md",
                    "skills/gone-skill/SKILL.md",
                ],
                incremental=True,
            )
        # Missing skill detected -> non-zero.
        self.assertNotEqual(rc, 0)
        # present-skill install commands exist (3 targets).
        present_cmds = [
            cmd for cmd in calls
            if "install_skill.py" in " ".join(cmd)
            and "present-skill" in " ".join(cmd)
        ]
        self.assertEqual(len(present_cmds), 3,
                         f"expected 3 install commands for present-skill, "
                         f"got {present_cmds}")
        # gone-skill install commands must not exist.
        gone_cmds = [
            cmd for cmd in calls
            if "install_skill.py" in " ".join(cmd)
            and "gone-skill" in " ".join(cmd)
        ]
        self.assertEqual(gone_cmds, [],
                         f"expected no install commands for missing gone-skill, "
                         f"got {gone_cmds}")
        self.assertIn("gone-skill", report.get("missing_skills", []))


if __name__ == "__main__":
    unittest.main(verbosity=2)