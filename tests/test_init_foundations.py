"""Tests for init_foundations.py using temporary workspace fixtures."""

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
INIT_FOUNDATIONS = os.path.join(SKILL_SCRIPTS, "init_foundations.py")


def run_init(root, *extra_args):
    args = [sys.executable, INIT_FOUNDATIONS, "--root", root] + list(extra_args)
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def exists(root, relpath):
    return os.path.exists(os.path.join(root, relpath))


class TestInitFoundations(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_creates_directories(self):
        """init_foundations creates the .ai/workflows/ dir layout."""
        rc, stdout, stderr = run_init(self.tmp)
        self.assertEqual(rc, 0, f"init should succeed, got stderr={stderr!r}")
        for d in (".ai/workflows/definitions", ".ai/workflows/runs",
                  ".ai/workflows/runs/history", ".ai/workflows/scripts"):
            self.assertTrue(exists(self.tmp, d),
                            f"directory should exist: {d}")

    def test_copies_workflow_files(self):
        """init_foundations copies workflow.py and sdlc-main.yaml to live locations."""
        rc, _, stderr = run_init(self.tmp)
        self.assertEqual(rc, 0, f"init should succeed, got stderr={stderr!r}")
        self.assertTrue(exists(self.tmp, ".ai/workflows/scripts/workflow.py"))
        self.assertTrue(exists(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml"))
        # Verify content is not empty
        wf = os.path.join(self.tmp, ".ai/workflows/scripts/workflow.py")
        yaml = os.path.join(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml")
        self.assertGreater(os.path.getsize(wf), 100, "workflow.py should have content")
        self.assertGreater(os.path.getsize(yaml), 10, "sdlc-main.yaml should have content")

    def test_idempotent(self):
        """Running init_foundations twice succeeds, second run reports already-present."""
        rc1, stdout1, _ = run_init(self.tmp)
        self.assertEqual(rc1, 0)
        rc2, stdout2, _ = run_init(self.tmp)
        self.assertEqual(rc2, 0)
        # Second run should not overwrite or error
        self.assertTrue(exists(self.tmp, ".ai/workflows/scripts/workflow.py"))

    def test_report_json(self):
        """init_foundations --json returns machine-readable report."""
        rc, stdout, _ = run_init(self.tmp, "--json")
        self.assertEqual(rc, 0)
        report = json.loads(stdout)
        self.assertIn("created", report)
        self.assertIn("already_present", report)
        # Should have created at least 2 files
        self.assertGreaterEqual(len(report["created"]), 2)
        self.assertEqual(len(report["already_present"]), 0)

    def test_json_idempotent(self):
        """Second run with --json shows files as already_present."""
        run_init(self.tmp)
        rc, stdout, _ = run_init(self.tmp, "--json")
        self.assertEqual(rc, 0)
        report = json.loads(stdout)
        self.assertEqual(len(report["created"]), 0)
        self.assertGreaterEqual(len(report["already_present"]), 2)

    def test_init_foundations_installs_executable_modular_workflow_runtime(self):
        """init_foundations installs the workflow_runtime package directory
        with all module files, and the bootstrapped workflow.py status or
        validate invocation succeeds."""
        rc, _, stderr = run_init(self.tmp)
        self.assertEqual(rc, 0, f"init should succeed, got stderr={stderr!r}")
        # The workflow_runtime package directory must exist.
        pkg_dir = os.path.join(self.tmp, ".ai", "workflows", "scripts", "workflow_runtime")
        self.assertTrue(os.path.isdir(pkg_dir),
                        "workflow_runtime package directory must be installed")
        # All expected module files must be present.
        for mod in ["__init__.py", "core.py", "state.py", "definitions.py",
                     "domains.py", "policies.py", "dispatch.py", "lifecycle.py",
                     "governance.py", "cli.py", "slices.py"]:
            self.assertTrue(os.path.isfile(os.path.join(pkg_dir, mod)),
                            f"workflow_runtime/{mod} must be installed")
        # The bootstrapped workflow.py must be executable.
        result = subprocess.run(
            [sys.executable, os.path.join(self.tmp, ".ai", "workflows", "scripts", "workflow.py"),
             "--root", self.tmp, "validate"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0,
                         f"validate should succeed, got stderr={result.stderr!r}")

    def test_missing_template_source(self):
        """--templates <nonexistent> exits 2."""
        rc, _, stderr = run_init(self.tmp, "--templates",
                                 os.path.join(self.tmp, "nonexistent"))
        self.assertEqual(rc, 2,
                         f"missing templates should exit 2, got rc={rc} stderr={stderr!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
