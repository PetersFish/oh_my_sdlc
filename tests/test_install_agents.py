"""Behavior tests for scripts/install_agents.py (template sync only)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "install_agents.py",
)


def write_file(root: str, relpath: str, content: str) -> None:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_install(source: str, target: str, *extra_args: str):
    args = [
        sys.executable,
        SCRIPT,
        "--source", source,
        "--target", target,
        *extra_args,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestInstallAgents(unittest.TestCase):
    """Existing install behavior tests (still valid for template sync)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source_root = os.path.join(self.tmp, "repo")
        self.source_agents = os.path.join(self.source_root, "agents")
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.source_agents, exist_ok=True)

        write_file(self.source_root, "agents/dev-orchestrator.md", "# dev\n")
        write_file(self.source_root, "agents/review-agent.md", "# review\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_fresh_install_writes_files_and_repo_root_metadata(self):
        rc, stdout, stderr = run_install(
            self.source_agents,
            self.target,
            "--source-ref", "TESTREF",
        )
        self.assertEqual(rc, 0, f"fresh install should succeed, stdout={stdout!r} stderr={stderr!r}")
        self.assertTrue(os.path.exists(os.path.join(self.target, "dev-orchestrator.md")))
        self.assertTrue(os.path.exists(os.path.join(self.target, "review-agent.md")))

        metadata = read_json(os.path.join(self.target, ".agent-install.json"))
        self.assertEqual(metadata["source_ref"], "TESTREF")
        self.assertEqual(
            os.path.realpath(metadata["source_repo"]),
            os.path.realpath(self.source_root),
            "source_repo should default to the repo root, not agents/ itself",
        )
        self.assertEqual(sorted(metadata["files"].keys()), ["dev-orchestrator.md", "review-agent.md"])

    def test_second_install_without_force_fails_and_does_not_refresh_metadata(self):
        rc1, stdout1, stderr1 = run_install(
            self.source_agents,
            self.target,
            "--source-ref", "FIRSTREF",
        )
        self.assertEqual(rc1, 0, f"first install should succeed, stdout={stdout1!r} stderr={stderr1!r}")
        original_metadata = read_json(os.path.join(self.target, ".agent-install.json"))

        write_file(self.source_root, "agents/review-agent.md", "# review updated\n")

        rc2, stdout2, stderr2 = run_install(
            self.source_agents,
            self.target,
            "--source-ref", "SECONDREF",
        )
        self.assertNotEqual(rc2, 0, "install without --force must fail when target files already exist")
        combined = f"{stdout2}\n{stderr2}"
        self.assertIn("--force", combined)

        current_review = open(os.path.join(self.target, "review-agent.md"), encoding="utf-8").read()
        self.assertEqual(current_review, "# review\n", "target content must remain unchanged on failed install")

        metadata = read_json(os.path.join(self.target, ".agent-install.json"))
        self.assertEqual(metadata["source_ref"], original_metadata["source_ref"])
        self.assertEqual(metadata["installed_at"], original_metadata["installed_at"])


class TestInstallConfigTemplate(unittest.TestCase):
    """Tests for config template handling during install."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source_root = os.path.join(self.tmp, "repo")
        self.source_agents = os.path.join(self.source_root, "agents")
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.source_agents, exist_ok=True)
        os.makedirs(os.path.join(self.source_agents, "config"), exist_ok=True)

        write_file(self.source_root, "agents/dev-orchestrator.md", "# dev\n")
        write_file(self.source_root, "agents/review-agent.md", "# review\n")
        write_file(self.source_root, "agents/config/model-profiles.yaml",
                   "schema_version: 1\ndefaults:\n  variant: medium\nprofiles: {}\nagents: {}\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_fresh_install_copies_config_template(self):
        """First install creates markdown files AND target config template."""
        rc, stdout, stderr = run_install(self.source_agents, self.target)
        self.assertEqual(rc, 0, f"fresh install should succeed, stdout={stdout!r} stderr={stderr!r}")

        target_config = os.path.join(self.target, "config", "model-profiles.yaml")
        self.assertTrue(os.path.exists(target_config),
                        f"target config template should be created at {target_config}")
        self.assertIn("config template initialized", stdout)

    def test_existing_target_config_is_preserved_on_reinstall(self):
        """Reinstall does NOT overwrite target effective config."""
        # First install
        rc1, stdout1, stderr1 = run_install(self.source_agents, self.target)
        self.assertEqual(rc1, 0)

        # Modify the target config
        target_config = os.path.join(self.target, "config", "model-profiles.yaml")
        with open(target_config, "w", encoding="utf-8") as f:
            f.write("schema_version: 1\ndefaults:\n  variant: high\nprofiles: {}\nagents: {}\n")

        # Force reinstall
        rc2, stdout2, stderr2 = run_install(self.source_agents, self.target, "--force")
        self.assertEqual(rc2, 0)

        # Config should be preserved
        content = open(target_config, encoding="utf-8").read()
        self.assertIn("variant: high", content,
                      "target config should be preserved on reinstall")


class TestInstallCheckNormalized(unittest.TestCase):
    """Tests for normalized check behavior."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source_root = os.path.join(self.tmp, "repo")
        self.source_agents = os.path.join(self.source_root, "agents")
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.source_agents, exist_ok=True)
        os.makedirs(os.path.join(self.source_agents, "config"), exist_ok=True)

        self.canonical = (
            "---\n"
            "name: test-agent\n"
            "mode: subagent\n"
            "description: A test agent\n"
            "---\n"
            "# Body content\n"
        )
        write_file(self.source_root, "agents/test-agent.md", self.canonical)
        write_file(self.source_root, "agents/config/model-profiles.yaml",
                   "schema_version: 1\ndefaults:\n  variant: medium\nprofiles: {}\nagents: {}\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _setup_identical_target_with_different_model_variant(self) -> None:
        """Install canonical, then mutate target to have different model/variant only."""
        # Install first
        run_install(self.source_agents, self.target, "--force")

        # Read target, inject model/variant
        target_file = os.path.join(self.target, "test-agent.md")
        content = open(target_file, encoding="utf-8").read()
        # Insert model/variant after mode line
        modified = content.replace(
            "mode: subagent\n",
            "mode: subagent\nmodel: different/model\nvariant: high\n",
        )
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(modified)

    def test_check_detects_prompt_drift_but_ignores_model_and_variant(self):
        """Check mode ignores model/variant differences but catches real drift."""
        # First install
        rc, _, _ = run_install(self.source_agents, self.target, "--force")
        self.assertEqual(rc, 0)

        # Inject model/variant only — should still pass check
        target_file = os.path.join(self.target, "test-agent.md")
        content = open(target_file, encoding="utf-8").read()
        modified = content.replace(
            "mode: subagent\n",
            "mode: subagent\nmodel: different/model\nvariant: high\n",
        )
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(modified)

        rc, stdout, stderr = run_install(self.source_agents, self.target, "--check")
        self.assertEqual(rc, 0, f"check should pass when only model/variant differ, got rc={rc}, stdout={stdout!r}")

    def test_check_fails_for_real_frontmatter_drift(self):
        """Check mode fails when non-activation frontmatter differs."""
        run_install(self.source_agents, self.target, "--force")

        # Change mode field
        target_file = os.path.join(self.target, "test-agent.md")
        content = open(target_file, encoding="utf-8").read()
        modified = content.replace("mode: subagent", "mode: primary")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(modified)

        rc, stdout, stderr = run_install(self.source_agents, self.target, "--check")
        self.assertNotEqual(rc, 0, "check should fail when mode differs")

    def test_check_fails_for_body_drift(self):
        """Check mode fails when body content differs."""
        run_install(self.source_agents, self.target, "--force")

        # Change body
        target_file = os.path.join(self.target, "test-agent.md")
        content = open(target_file, encoding="utf-8").read()
        modified = content.replace("# Body content", "# Modified body")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(modified)

        rc, stdout, stderr = run_install(self.source_agents, self.target, "--check")
        self.assertNotEqual(rc, 0, "check should fail when body differs")

    def test_check_requires_target_config_to_exist(self):
        """Check mode fails when target config has never been initialized."""
        # Install WITHOUT config template (source has no config template)
        src_no_config = os.path.join(self.tmp, "repo_no_config", "agents")
        os.makedirs(src_no_config, exist_ok=True)
        write_file(self.tmp, "repo_no_config/agents/test-agent.md", self.canonical)
        tgt_no_config = os.path.join(self.tmp, "target_no_config")

        run_install(src_no_config, tgt_no_config, "--force")

        # Check should fail because target config doesn't exist
        rc, stdout, stderr = run_install(src_no_config, tgt_no_config, "--check")
        self.assertNotEqual(rc, 0,
                            "check should fail when target config is missing")

    def test_check_passes_when_in_sync(self):
        """Check mode passes when canonical and target are identical."""
        run_install(self.source_agents, self.target, "--force")
        rc, stdout, stderr = run_install(self.source_agents, self.target, "--check")
        self.assertEqual(rc, 0, f"check should pass when synced, got rc={rc}")


class TestInstallDoesNotInjectModelVariant(unittest.TestCase):
    """Install (template sync) never injects model/variant fields."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source_root = os.path.join(self.tmp, "repo")
        self.source_agents = os.path.join(self.source_root, "agents")
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.source_agents, exist_ok=True)

        write_file(self.source_root, "agents/test-agent.md",
                   "---\nname: test\nmode: subagent\n---\n# Body\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_install_does_not_inject_model_or_variant(self):
        """Installed markdown contains no activation fields from install phase."""
        rc, stdout, stderr = run_install(self.source_agents, self.target)
        self.assertEqual(rc, 0)

        target_file = os.path.join(self.target, "test-agent.md")
        content = open(target_file, encoding="utf-8").read()
        self.assertIn("name: test", content)
        self.assertNotIn("model:", content)
        self.assertNotIn("variant:", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
