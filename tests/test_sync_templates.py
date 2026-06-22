"""Tests for sync_templates.py using temporary workspace fixtures."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


SKILL_SCRIPTS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", ".opencode", "skills", "sdlc-project-bootstrap", "scripts",
)
SYNC_TEMPLATES = os.path.join(SKILL_SCRIPTS, "sync_templates.py")
TEMPLATES_WORKFLOW = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", ".opencode", "skills", "sdlc-project-bootstrap", "templates",
    "workflow",
)

DISTRIBUTED_DIRS = [".opencode", ".claude", ".cursor"]


def run_sync(root, *extra_args):
    """Run sync_templates.py --root <root> and return (returncode, stdout, stderr)."""
    args = [sys.executable, SYNC_TEMPLATES, "--root", root] + list(extra_args)
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def read_file(root, relpath):
    path = os.path.join(root, relpath)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read()


def write_file(root, relpath, content):
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _make_canonical_templates(tmp):
    """Create canonical templates dir with known content."""
    write_file(tmp, "skills/sdlc-project-bootstrap/templates/workflow/workflow.py",
               "# canonical workflow\n")
    write_file(tmp, "skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml",
               "# canonical yaml\n")


def _make_distributed_copies(tmp, wf_content="# canonical workflow\n",
                              yaml_content="# canonical yaml\n"):
    """Create matching distributed copies for all three CLI targets."""
    for d in DISTRIBUTED_DIRS:
        write_file(tmp, f"{d}/skills/sdlc-project-bootstrap/templates/workflow/workflow.py",
                   wf_content)
        write_file(tmp, f"{d}/skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml",
                   yaml_content)


def run_sync(root, *extra_args):
    """Run sync_templates.py --root <root> and return (returncode, stdout, stderr)."""
    args = [sys.executable, SYNC_TEMPLATES, "--root", root] + list(extra_args)
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def read_file(root, relpath):
    path = os.path.join(root, relpath)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read()


def write_file(root, relpath, content):
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


class TestSyncTemplates(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Create live files
        write_file(self.tmp, ".ai/workflows/scripts/workflow.py", "# live workflow\n")
        write_file(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml", "# live yaml\n")
        # Create template directories and seed with different content (drift)
        write_file(self.tmp, "templates/workflow/workflow.py", "# template workflow\n")
        write_file(self.tmp, "templates/workflow/sdlc-main.yaml", "# template yaml\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_check_detects_drift(self):
        """--check exits non-zero when live differs from template."""
        rc, stdout, stderr = run_sync(self.tmp, "--check", "--templates",
                                      os.path.join(self.tmp, "templates"))
        self.assertNotEqual(rc, 0, f"--check should exit non-zero on drift, got stdout={stdout!r} stderr={stderr!r}")
        # Must report which files drifted (not just a missing-file error)
        combined = stdout + stderr
        self.assertIn("drift", combined.lower(),
                      f"Expected drift report, got stdout={stdout!r} stderr={stderr!r}")

    def test_check_passes_when_identical(self):
        """--check exits zero when live and template are identical."""
        # Make templates identical to live
        write_file(self.tmp, "templates/workflow/workflow.py", "# live workflow\n")
        write_file(self.tmp, "templates/workflow/sdlc-main.yaml", "# live yaml\n")
        rc, stdout, stderr = run_sync(self.tmp, "--check", "--templates",
                                      os.path.join(self.tmp, "templates"))
        self.assertEqual(rc, 0, f"--check should exit 0 when identical, got stdout={stdout!r} stderr={stderr!r}")

    def test_sync_copies_live_to_template(self):
        """Sync (without --check) copies live files to template."""
        rc, stdout, stderr = run_sync(self.tmp, "--templates",
                                      os.path.join(self.tmp, "templates"))
        self.assertEqual(rc, 0, f"sync should succeed, got stdout={stdout!r} stderr={stderr!r}")
        # After sync, template should match live
        template_wf = read_file(self.tmp, "templates/workflow/workflow.py")
        template_yaml = read_file(self.tmp, "templates/workflow/sdlc-main.yaml")
        self.assertEqual(template_wf, "# live workflow\n")
        self.assertEqual(template_yaml, "# live yaml\n")

    def test_sync_idempotent(self):
        """Running sync twice produces same result, second run reports already-in-sync."""
        # First sync: make template match live
        rc1, stdout1, _ = run_sync(self.tmp, "--templates",
                                   os.path.join(self.tmp, "templates"))
        self.assertEqual(rc1, 0)
        # Second sync: should report already-in-sync / no changes
        rc2, stdout2, _ = run_sync(self.tmp, "--templates",
                                   os.path.join(self.tmp, "templates"))
        self.assertEqual(rc2, 0)
        # Template should still match live
        template_wf = read_file(self.tmp, "templates/workflow/workflow.py")
        self.assertEqual(template_wf, "# live workflow\n")

    def test_sync_report_json(self):
        """Sync with --json returns machine-readable report."""
        rc, stdout, _ = run_sync(self.tmp, "--json", "--templates",
                                 os.path.join(self.tmp, "templates"))
        self.assertEqual(rc, 0)
        report = json.loads(stdout)
        self.assertIn("synced", report)
        self.assertIn("unchanged", report)
        # At least one file should be synced (since we seeded with drift)
        self.assertGreaterEqual(len(report["synced"]), 1)

    def test_sync_ignores_unmanaged_files(self):
        """Files not in the governed set are not synced or checked."""
        # Create an unmanaged file in templates that differs from nothing
        write_file(self.tmp, "templates/workflow/AGENTS.md", "# unmanaged\n")
        rc, stdout, _ = run_sync(self.tmp, "--check", "--templates",
                                 os.path.join(self.tmp, "templates"))
        # Should still exit non-zero because managed files have drift
        self.assertNotEqual(rc, 0)
        # But the unmanaged file should not be mentioned as drift source
        report_str = stdout.lower()
        self.assertNotIn("unmanaged", report_str)

    def test_check_json_with_drift(self):
        """--check --json exits non-zero and returns drifted list as JSON."""
        rc, stdout, _ = run_sync(self.tmp, "--check", "--json", "--templates",
                                 os.path.join(self.tmp, "templates"))
        self.assertNotEqual(rc, 0,
                            f"--check --json with drift should exit non-zero, got rc={rc}")
        data = json.loads(stdout)
        self.assertIn("drifted", data)
        self.assertGreaterEqual(len(data["drifted"]), 1)
        self.assertIn("in_sync", data)

    def test_nonexistent_templates_dir(self):
        """--templates <missing> exits 2."""
        rc, _, stderr = run_sync(self.tmp, "--check", "--templates",
                                 os.path.join(self.tmp, "nonexistent"))
        self.assertEqual(rc, 2,
                         f"nonexistent templates dir should exit 2, got rc={rc} stderr={stderr!r}")


class TestSyncTemplatesDistributed(unittest.TestCase):
    """Tests for --check-distributed and --distribute modes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Create canonical templates
        _make_canonical_templates(self.tmp)
        # Create distributed copies matching canonical
        _make_distributed_copies(self.tmp)
        # Create live files matching canonical (for sync tests)
        write_file(self.tmp, ".ai/workflows/scripts/workflow.py",
                   "# canonical workflow\n")
        write_file(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml",
                   "# canonical yaml\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_check_distributed_passes_when_identical(self):
        """--check-distributed exits 0 when canonical and all distributed match."""
        rc, stdout, _ = run_sync(self.tmp, "--check-distributed")
        self.assertEqual(rc, 0,
                         f"identical distributed should exit 0, got stdout={stdout!r}")

    def test_check_distributed_detects_drift(self):
        """--check-distributed exits non-zero when distributed differs from canonical."""
        write_file(self.tmp,
                   ".opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py",
                   "# drifted content\n")
        rc, stdout, _ = run_sync(self.tmp, "--check-distributed")
        self.assertNotEqual(rc, 0,
                            f"drifted distributed should exit non-zero, got stdout={stdout!r}")
        combined = stdout.lower()
        self.assertIn("drift", combined, f"should mention drift, got {stdout!r}")

    def test_distribute_pushes_to_all_targets(self):
        """--distribute copies canonical to all distributed copies."""
        # Make distributed copies stale
        for d in DISTRIBUTED_DIRS:
            write_file(self.tmp,
                       f"{d}/skills/sdlc-project-bootstrap/templates/workflow/workflow.py",
                       "# stale\n")
        rc, stdout, _ = run_sync(self.tmp, "--distribute")
        self.assertEqual(rc, 0,
                         f"distribute should succeed, got stdout={stdout!r}")
        # All distributed copies should now match canonical
        for d in DISTRIBUTED_DIRS:
            content = read_file(self.tmp,
                                f"{d}/skills/sdlc-project-bootstrap/templates/workflow/workflow.py")
            self.assertEqual(content, "# canonical workflow\n",
                             f"distributed copy in {d} should match canonical after distribute")

    def test_distribute_json_reports_synced(self):
        """--distribute --json returns machine-readable report."""
        # Make distributed copies stale
        for d in DISTRIBUTED_DIRS:
            write_file(self.tmp,
                       f"{d}/skills/sdlc-project-bootstrap/templates/workflow/workflow.py",
                       "# stale\n")
        rc, stdout, _ = run_sync(self.tmp, "--distribute", "--json")
        self.assertEqual(rc, 0)
        report = json.loads(stdout)
        self.assertIn("synced", report)
        self.assertGreaterEqual(len(report["synced"]), 1)

    def test_distribute_idempotent(self):
        """Running --distribute twice is safe."""
        run_sync(self.tmp, "--distribute")
        rc, stdout, _ = run_sync(self.tmp, "--distribute")
        self.assertEqual(rc, 0)
        # Content should still be correct
        content = read_file(self.tmp,
                            ".cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py")
        self.assertEqual(content, "# canonical workflow\n")


CHECK_SKILL_DIST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "skills", "meta-skill-lifecycle-governance", "scripts",
    "check_skill_distribution.py",
)


def run_skill_check(root, *extra_args):
    args = [sys.executable, CHECK_SKILL_DIST, "--root", root] + list(extra_args)
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestCheckSkillDistribution(unittest.TestCase):
    """Tests for check_skill_distribution.py — full-tree skill copy drift detection."""

    SKILL = "test-skill"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Canonical skill: SKILL.md + scripts/
        skill_dir = os.path.join(self.tmp, "skills", self.SKILL)
        os.makedirs(os.path.join(skill_dir, "scripts"))
        write_file(self.tmp, f"skills/{self.SKILL}/SKILL.md", "# skill content\n")
        write_file(self.tmp, f"skills/{self.SKILL}/scripts/do.py", "# do script\n")

        # Matching distributed copies
        for dist in [".opencode", ".claude", ".cursor"]:
            d = os.path.join(self.tmp, dist, "skills", self.SKILL)
            os.makedirs(os.path.join(d, "scripts"))
            write_file(self.tmp, f"{dist}/skills/{self.SKILL}/SKILL.md", "# skill content\n")
            write_file(self.tmp, f"{dist}/skills/{self.SKILL}/scripts/do.py", "# do script\n")
            # Distribution install metadata (should be ignored by check)
            write_file(self.tmp, f"{dist}/skills/{self.SKILL}/.skill-install.json",
                       '{"source_ref":"HEAD"}\n')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_all_match_exits_zero(self):
        rc, stdout, _ = run_skill_check(self.tmp)
        self.assertEqual(rc, 0, f"identical copies should exit 0, got stdout={stdout!r}")

    def test_drift_in_script_detected(self):
        write_file(self.tmp, "skills/test-skill/scripts/do.py", "# modified script\n")
        rc, stdout, _ = run_skill_check(self.tmp)
        self.assertNotEqual(rc, 0, f"script drift should exit non-zero, got stdout={stdout!r}")
        self.assertIn("do.py", stdout)

    def test_file_only_in_canonical_detected(self):
        write_file(self.tmp, "skills/test-skill/scripts/new.py", "# new file\n")
        rc, stdout, _ = run_skill_check(self.tmp)
        self.assertNotEqual(rc, 0, f"extra canonical file should exit non-zero, got stdout={stdout!r}")
        self.assertIn("new.py", stdout)

    def test_skills_filter_skips_unrelated_drift(self):
        write_file(self.tmp, "skills/test-skill/scripts/do.py", "# modified script\n")
        write_file(self.tmp, "skills/other-skill/SKILL.md", "# other\n")
        os.makedirs(os.path.join(self.tmp, ".opencode", "skills", "other-skill"))
        write_file(self.tmp, ".opencode/skills/other-skill/SKILL.md", "# different\n")
        rc, stdout, _ = run_skill_check(self.tmp, "--skills", "test-skill")
        self.assertNotEqual(rc, 0, f"should detect test-skill drift")
        self.assertIn("do.py", stdout)
        self.assertNotIn("other-skill", stdout, "unrelated skill should be skipped")


if __name__ == "__main__":
    unittest.main(verbosity=2)
