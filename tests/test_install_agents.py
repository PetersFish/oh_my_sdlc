"""Behavior tests for scripts/install_agents.py."""

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

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


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
    """WP2: template-sync semantics — install copies prompts + config template."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source_root = os.path.join(self.tmp, "repo")
        self.source_agents = os.path.join(self.source_root, "agents")
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.source_agents, exist_ok=True)

        # Create a minimal config template in source
        config_dir = os.path.join(self.source_agents, "config")
        os.makedirs(config_dir, exist_ok=True)
        write_file(self.source_root, "agents/config/model-profiles.yaml",
                   "schema_version: 1\ndefaults:\n  variant: medium\nprofiles: {}\nagents: {}\n")

        write_file(self.source_root, "agents/dev-orchestrator.md", "# dev\n")
        write_file(self.source_root, "agents/review-agent.md", "# review\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    # ---- Existing tests (updated) ----

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

    # ---- WP2: new tests ----

    def test_fresh_install_copies_agent_markdown_and_config_template(self):
        rc, stdout, stderr = run_install(
            self.source_agents,
            self.target,
            "--source-ref", "TESTREF",
        )
        self.assertEqual(rc, 0, f"fresh install should succeed, stdout={stdout!r} stderr={stderr!r}")
        self.assertTrue(os.path.exists(os.path.join(self.target, "dev-orchestrator.md")))
        self.assertTrue(os.path.exists(os.path.join(self.target, "review-agent.md")))
        # Config template should be copied
        config_path = os.path.join(self.target, "config", "model-profiles.yaml")
        self.assertTrue(os.path.exists(config_path),
                        "fresh install must copy config template to target/config/model-profiles.yaml")

    def test_existing_target_config_is_preserved_on_reinstall(self):
        # First install
        rc1, _, _ = run_install(self.source_agents, self.target, "--source-ref", "FIRSTREF")
        self.assertEqual(rc1, 0)
        config_path = os.path.join(self.target, "config", "model-profiles.yaml")
        self.assertTrue(os.path.exists(config_path))

        # Modify target config
        write_file(self.target, "config/model-profiles.yaml",
                   "schema_version: 1\ndefaults:\n  variant: low\nprofiles: {}\nagents: {}\n")

        # Force reinstall
        rc2, stdout2, stderr2 = run_install(
            self.source_agents, self.target,
            "--source-ref", "SECONDREF", "--force",
        )
        self.assertEqual(rc2, 0, f"force install should succeed, stdout={stdout2!r} stderr={stderr2!r}")

        # Target config should be preserved (not overwritten by template)
        cfg_content = open(config_path, encoding="utf-8").read()
        self.assertIn("variant: low", cfg_content,
                      "existing target config must be preserved on reinstall")

    def test_install_does_not_inject_model_or_variant(self):
        """Installed markdown must NOT contain model/variant after install phase."""
        rc, stdout, stderr = run_install(
            self.source_agents, self.target,
            "--source-ref", "TESTREF",
        )
        self.assertEqual(rc, 0, f"install should succeed, stdout={stdout!r} stderr={stderr!r}")

        # Check the installed markdown files do NOT have model or variant
        for fname in ("dev-orchestrator.md", "review-agent.md"):
            content = open(os.path.join(self.target, fname), encoding="utf-8").read()
            # Source files are body-only, so no frontmatter at all
            # model/variant should not appear in the installed output
            self.assertNotIn("model:", content,
                            f"{fname} should not contain model: after pure template sync")
            self.assertNotIn("variant:", content,
                            f"{fname} should not contain variant: after pure template sync")

    def test_check_detects_prompt_drift_but_ignores_model_and_variant(self):
        # First install normally
        rc1, _, _ = run_install(self.source_agents, self.target, "--source-ref", "TESTREF")
        self.assertEqual(rc1, 0)

        # Check should pass initially
        rc2, stdout2, _ = run_install(self.source_agents, self.target, "--check")
        self.assertEqual(rc2, 0, f"check should pass after fresh install, stdout={stdout2!r}")

        # Now modify the body of a target file (simulate drift)
        target_file = os.path.join(self.target, "dev-orchestrator.md")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("# dev modified\n")

        # Check should now fail (body drift)
        rc3, stdout3, _ = run_install(self.source_agents, self.target, "--check")
        self.assertNotEqual(rc3, 0, "check must fail when body differs from canonical")

        # Now restore body but add model/variant frontmatter (activation-managed fields)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("---\nmodel: openai/gpt-5\nvariant: high\n---\n# dev\n")

        # Check should PASS (model/variant differences are activation-managed, not canonical drift)
        rc4, stdout4, _ = run_install(self.source_agents, self.target, "--check")
        self.assertEqual(rc4, 0,
                         f"check should ignore model/variant drift, stdout={stdout4!r}")

    def test_check_requires_target_config_to_exist(self):
        """Check mode should flag missing target config."""
        # Install without config template present in source
        # Remove the config dir from source
        config_dir = os.path.join(self.source_agents, "config")
        if os.path.exists(config_dir):
            shutil.rmtree(config_dir)

        rc1, _, _ = run_install(self.source_agents, self.target, "--source-ref", "TESTREF")
        self.assertEqual(rc1, 0)

        # Delete the target config (if it exists)
        tgt_cfg = os.path.join(self.target, "config", "model-profiles.yaml")
        if os.path.exists(tgt_cfg):
            os.remove(tgt_cfg)

        # Check should fail because target config is missing
        rc2, stdout2, stderr2 = run_install(self.source_agents, self.target, "--check")
        self.assertNotEqual(rc2, 0,
                            "check must fail when target config is missing")
        combined = f"{stdout2}\n{stderr2}"
        self.assertIn("config", combined.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
