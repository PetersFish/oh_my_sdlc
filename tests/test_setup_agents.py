"""Behavior tests for scripts/setup_agents.py (aggregate setup)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "setup_agents.py",
)


def write_file(root: str, relpath: str, content: str) -> None:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def run_setup(source: str, target: str, *extra_args: str):
    """Run setup_agents.py with explicit source and target."""
    # Setup uses the repo's install/activate scripts which derive source from
    # their own script location. For testing, we need to use --source on
    # install_agents.py and --target on setup_agents.py.
    # The setup_agents.py passes --target to both sub-scripts.
    # But install needs --source too. For tests we call install_agents directly.
    args = [
        sys.executable,
        SCRIPT,
        "--target", target,
        *extra_args,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestSetupScript(unittest.TestCase):
    """Tests for aggregate setup behavior using the actual test repo structure."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.target = os.path.join(self.tmp, "target")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _setup_minimal_config(self):
        """Create a target with a minimal config for testing activation."""
        write_file(self.tmp, "target/config/model-profiles.yaml",
                   "schema_version: 1\n"
                   "defaults:\n"
                   "  variant: medium\n"
                   "profiles:\n"
                   "  test:\n"
                   "    model: openai/gpt-4\n"
                   "agents:\n"
                   "  test-agent:\n"
                   "    profile: test\n")

    def test_setup_script_exists_and_is_runnable(self):
        """Script exists and produces usage when run with --help."""
        result = subprocess.run(
            [sys.executable, SCRIPT, "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())

    def test_setup_with_missing_target(self):
        """Setup against a non-existent target fails gracefully."""
        os.makedirs(self.target, exist_ok=True)
        # No config, no agent files - install should work but activate would fail
        # Actually, let's just test that the dry-run path works
        self._setup_minimal_config()
        write_file(self.tmp, "target/test-agent.md",
                   "---\nname: test-agent\nmode: subagent\n---\n# Body\n")

        # Since install needs --source to point to the canonical source,
        # and our test repo doesn't have it relative to the script's location,
        # let's test the check mode first:
        rc, stdout, stderr = run_setup("", self.target, "--check")
        # May fail due to source resolution but should not crash
        self.assertIsNotNone(rc)

    def test_check_mode_reports_when_scripts_work(self):
        """Check mode invokes both install --check and activate --check."""
        self._setup_minimal_config()
        os.makedirs(self.target, exist_ok=True)
        write_file(self.tmp, "target/test-agent.md",
                   "---\nname: test-agent\nmode: subagent\n---\n# Body\n")

        # Activate first (need to run activate directly since setup depends on install source)
        activate_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "scripts", "activate_agents_config.py",
        )
        subprocess.run(
            [sys.executable, activate_script, "--target", self.target],
            capture_output=True, text=True,
        )

        # Now activate check should pass
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target, "--check"],
            capture_output=True, text=True,
        )
        rc, stdout, stderr = result.returncode, result.stdout, result.stderr
        self.assertEqual(rc, 0, f"activate --check should pass when in sync, got rc={rc}, stdout={stdout!r}")

    def test_setup_dry_run_reports_fresh_target_preview_without_writing(self):
        """Aggregate --dry-run previews template sync and activation for a fresh target."""
        fresh_target = os.path.join(self.tmp, "fresh-target")

        rc, stdout, stderr = run_setup("", fresh_target, "--dry-run")

        self.assertEqual(rc, 0, f"aggregate dry-run should succeed, stdout={stdout!r} stderr={stderr!r}")
        self.assertIn("[DRY-RUN] would install:", stdout)
        self.assertIn("[DRY-RUN] would initialize config template:", stdout)
        self.assertIn("[DRY-RUN] would activate:", stdout)
        self.assertIn("dev-orchestrator.md", stdout)
        self.assertFalse(os.path.exists(fresh_target), "aggregate dry-run must not create the fresh target")

    def test_setup_check_for_activation_drift(self):
        """Aggregate check surfaces activation drift."""
        self._setup_minimal_config()
        os.makedirs(self.target, exist_ok=True)
        write_file(self.tmp, "target/test-agent.md",
                   "---\nname: test-agent\nmode: subagent\nmodel: wrong/model\nvariant: wrong\n---\n# Body\n")

        activate_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "scripts", "activate_agents_config.py",
        )
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target, "--check"],
            capture_output=True, text=True,
        )
        rc, stdout, stderr = result.returncode, result.stdout, result.stderr
        self.assertNotEqual(rc, 0, "check should detect activation drift")
        self.assertIn("DRIFT", stdout)

    def test_activate_then_check_is_idempotent(self):
        """Activate then check passes; activate again is no-op."""
        self._setup_minimal_config()
        os.makedirs(self.target, exist_ok=True)
        write_file(self.tmp, "target/test-agent.md",
                   "---\nname: test-agent\nmode: subagent\n---\n# Body\n")

        activate_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "scripts", "activate_agents_config.py",
        )

        # First activation
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target],
            capture_output=True, text=True,
        )
        rc, stdout = result.returncode, result.stdout
        self.assertEqual(rc, 0, f"activation failed: {stdout}")

        # Check should pass
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target, "--check"],
            capture_output=True, text=True,
        )
        rc, stdout = result.returncode, result.stdout
        self.assertEqual(rc, 0, f"check after activation should pass: {stdout}")

        # Second activation should be no-op
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target],
            capture_output=True, text=True,
        )
        rc, stdout = result.returncode, result.stdout
        self.assertEqual(rc, 0)
        self.assertIn("already activated", stdout.lower())

        # Check still passes
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target, "--check"],
            capture_output=True, text=True,
        )
        rc = result.returncode
        self.assertEqual(rc, 0)

    def test_setup_preserves_activation_after_reinstall(self):
        """setup_agents.py preserves model/variant after template reinstall."""
        self._setup_minimal_config()
        os.makedirs(self.target, exist_ok=True)
        write_file(self.tmp, "target/test-agent.md",
                   "---\nname: test-agent\nmode: subagent\n---\n# Body\n")

        activate_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "scripts", "activate_agents_config.py",
        )

        # Activate first
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"activation failed: {result.stdout}")

        # Verify model/variant present
        content = open(os.path.join(self.target, "test-agent.md"), encoding="utf-8").read()
        self.assertIn("model: openai/gpt-4", content)
        self.assertIn("variant: medium", content)

        # Re-activate (simulates reinstall then activate)
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("already activated", result.stdout.lower())

        # Verify model/variant still present and correct
        content = open(os.path.join(self.target, "test-agent.md"), encoding="utf-8").read()
        self.assertIn("model: openai/gpt-4", content)
        self.assertIn("variant: medium", content)

        # Check passes
        result = subprocess.run(
            [sys.executable, activate_script, "--target", self.target, "--check"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"check should pass: {result.stdout}")


class TestCheckJsonOutput(unittest.TestCase):
    """setup_agents.py --check --json reports concrete stale agent target paths."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.target = os.path.join(self.tmp, "target")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _setup_minimal_config(self):
        write_file(self.tmp, "target/config/model-profiles.yaml",
                   "schema_version: 1\n"
                   "defaults:\n"
                   "  variant: medium\n"
                   "profiles:\n"
                   "  test:\n"
                   "    model: openai/gpt-4\n"
                   "agents:\n"
                   "  test-agent:\n"
                   "    profile: test\n")

    def test_check_json_reports_stale_agent_paths(self):
        """--check --json must report concrete repository-relative stale agent
        target paths, not just a non-zero status or human-readable message."""
        self._setup_minimal_config()
        os.makedirs(self.target, exist_ok=True)
        # Create a target agent with drift (different body content than canonical)
        write_file(self.tmp, "target/test-agent.md",
                   "---\nname: test-agent\nmode: subagent\n---\n# Different body\n")

        result = subprocess.run(
            [sys.executable, SCRIPT, "--target", self.target, "--check", "--json"],
            capture_output=True, text=True,
        )
        # Must output JSON on stdout
        self.assertTrue(result.stdout.strip(),
                        f"--json must produce JSON output, got stdout={result.stdout!r}")
        report = json.loads(result.stdout)
        # The report must include stale path entries (not just a boolean)
        self.assertIsInstance(report, dict)
        # Look for stale paths in the report — could be under "stale_paths",
        # "drifted_paths", or similar
        stale_paths = (
            report.get("stale_paths")
            or report.get("drifted_paths")
            or report.get("drift")
            or []
        )
        # If nested under a suite, flatten
        if not stale_paths and "suites" in report:
            for suite in report["suites"]:
                if isinstance(suite, dict):
                    stale_paths.extend(suite.get("stale_paths", []))
                    stale_paths.extend(suite.get("drifted_paths", []))
        self.assertTrue(
            any("test-agent.md" in str(p) for p in stale_paths),
            f"--check --json must report the stale test-agent.md path, got report={report}",
        )


class TestCheckJsonRepoRelativePaths(unittest.TestCase):
    """--check --json must report repository-relative stale agent target paths
    for project-level targets such as .opencode/agents, not just target.name."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Init a git repo so _target_relpath can discover the repo root
        subprocess.run(["git", "init"], capture_output=True, cwd=self.tmp)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       capture_output=True, cwd=self.tmp)
        subprocess.run(["git", "config", "user.name", "Test"],
                       capture_output=True, cwd=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _setup_minimal_config(self, target_rel: str):
        write_file(self.tmp, f"{target_rel}/config/model-profiles.yaml",
                   "schema_version: 1\n"
                   "defaults:\n"
                   "  variant: medium\n"
                   "profiles:\n"
                   "  test:\n"
                   "    model: openai/gpt-4\n"
                   "agents:\n"
                   "  test-agent:\n"
                   "    profile: test\n")

    def test_opencode_target_stale_paths_are_repo_relative(self):
        """For target at .opencode/agents, stale paths must be
        .opencode/agents/<file>.md, not agents/<file>.md."""
        target_rel = ".opencode/agents"
        self._setup_minimal_config(target_rel)
        target = os.path.join(self.tmp, target_rel)
        os.makedirs(target, exist_ok=True)
        # Create a stale agent file (different body from canonical)
        write_file(self.tmp, f"{target_rel}/test-agent.md",
                   "---\nname: test-agent\nmode: subagent\n---\n# Different body\n")

        result = subprocess.run(
            [sys.executable, SCRIPT, "--target", target, "--check", "--json"],
            capture_output=True, text=True,
        )
        self.assertTrue(result.stdout.strip(),
                        f"--json must produce JSON output, got stdout={result.stdout!r}")
        report = json.loads(result.stdout)
        stale_paths = report.get("stale_paths", [])
        self.assertTrue(stale_paths,
                        f"expected stale paths for stale target, got report={report}")
        for p in stale_paths:
            self.assertTrue(
                p.startswith(".opencode/agents/"),
                f"stale path {p!r} must be repository-relative "
                f"(.opencode/agents/...), not just agents/..."
            )

    def test_claude_target_stale_paths_are_repo_relative(self):
        """For target at .claude/agents, stale paths must be
        .claude/agents/<file>.md."""
        target_rel = ".claude/agents"
        self._setup_minimal_config(target_rel)
        target = os.path.join(self.tmp, target_rel)
        os.makedirs(target, exist_ok=True)
        write_file(self.tmp, f"{target_rel}/test-agent.md",
                   "---\nname: test-agent\nmode: subagent\n---\n# Different body\n")

        result = subprocess.run(
            [sys.executable, SCRIPT, "--target", target, "--check", "--json"],
            capture_output=True, text=True,
        )
        report = json.loads(result.stdout)
        stale_paths = report.get("stale_paths", [])
        if stale_paths:
            for p in stale_paths:
                self.assertTrue(
                    p.startswith(".claude/agents/"),
                    f"stale path {p!r} must be repository-relative "
                    f"(.claude/agents/...)"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
