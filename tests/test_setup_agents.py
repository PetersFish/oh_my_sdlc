"""Behavior tests for scripts/setup_agents.py — aggregate setup flow."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest


SETUP_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "setup_agents.py",
)

INSTALL_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "install_agents.py",
)


def write_file(root: str, relpath: str, content: str) -> None:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_file(root: str, relpath: str) -> str:
    with open(os.path.join(root, relpath), encoding="utf-8") as f:
        return f.read()


def run_setup(source: str, target: str, *extra_args: str):
    args = [
        sys.executable,
        SETUP_SCRIPT,
        "--source", source,
        "--target", target,
        *extra_args,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestSetupAgents(unittest.TestCase):
    """WP4: aggregate setup composes install + activation with safe verification modes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source_root = os.path.join(self.tmp, "repo")
        self.source_agents = os.path.join(self.source_root, "agents")
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.source_agents, exist_ok=True)

        # Create canonical config template
        write_file(self.source_root, "agents/config/model-profiles.yaml", """\
schema_version: 1
defaults:
  variant: medium
profiles:
  std:
    model: openai/gpt-5
agents:
  dev-orchestrator:
    profile: std
  review-agent:
    profile: std
""")

        # Create canonical agent prompts (body-only, model-agnostic)
        write_file(self.source_root, "agents/dev-orchestrator.md",
                   "---\nname: dev-orchestrator\nmode: primary\npermission:\n  edit: deny\n---\n# Dev Orchestrator\n")
        write_file(self.source_root, "agents/review-agent.md",
                   "---\nname: review-agent\nmode: subagent\npermission:\n  edit: allow\n---\n# Review Agent\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_setup_runs_install_then_activation(self):
        """A single run produces both config file and activated frontmatter."""
        rc, stdout, stderr = run_setup(
            self.source_agents, self.target,
            "--source-ref", "TESTREF",
        )
        self.assertEqual(rc, 0, f"setup should succeed, stdout={stdout!r} stderr={stderr!r}")

        # Config should exist
        cfg_path = os.path.join(self.target, "config", "model-profiles.yaml")
        self.assertTrue(os.path.exists(cfg_path), "setup must create target config")

        # Markdown files should have model/variant activated
        content = read_file(self.target, "dev-orchestrator.md")
        self.assertIn("model: openai/gpt-5", content,
                      "activation must render model into frontmatter")
        self.assertIn("variant: medium", content,
                      "activation must render variant into frontmatter")
        # Existing frontmatter should be preserved
        self.assertIn("name: dev-orchestrator", content)
        self.assertIn("mode: primary", content)

    def test_setup_check_fails_for_template_drift(self):
        """Aggregated --check surfaces install drift."""
        # First, run setup
        rc1, _, _ = run_setup(self.source_agents, self.target, "--source-ref", "TESTREF")
        self.assertEqual(rc1, 0)

        # Check should pass
        rc2, _, _ = run_setup(self.source_agents, self.target, "--check")
        self.assertEqual(rc2, 0, "check should pass after clean setup")

        # Modify canonical prompt
        write_file(self.source_root, "agents/review-agent.md",
                   "---\nname: review-agent\nmode: subagent\npermission:\n  edit: allow\n---\n# Review Agent Modified\n")

        # Check should fail (template drift)
        rc3, stdout3, _ = run_setup(self.source_agents, self.target, "--check")
        self.assertNotEqual(rc3, 0, "check must fail for template drift")
        # Should mention the drifted file
        self.assertIn("review-agent", stdout3.lower(),
                      "drift report should mention which agent drifted")

    def test_setup_check_fails_for_activation_drift(self):
        """Aggregated --check surfaces activation drift separately."""
        # First, run setup
        rc1, _, _ = run_setup(self.source_agents, self.target, "--source-ref", "TESTREF")
        self.assertEqual(rc1, 0)

        # Modify the target config
        write_file(self.target, "config/model-profiles.yaml", """\
schema_version: 1
defaults:
  variant: high
profiles:
  std:
    model: openai/gpt-5-mini
agents:
  dev-orchestrator:
    profile: std
  review-agent:
    profile: std
""")

        # Check should fail (activation drift — config changed but not rerendered)
        rc2, stdout2, _ = run_setup(self.source_agents, self.target, "--check")
        self.assertNotEqual(rc2, 0, "check must fail for activation drift after config change")
        combined = f"{stdout2}"
        self.assertTrue(
            "activation" in combined.lower() or "drift" in combined.lower(),
            f"setup check should report activation drift, got: {combined!r}"
        )

    def test_setup_dry_run_reports_actions_without_writing(self):
        """Aggregate dry-run does not mutate files."""
        rc, stdout, _ = run_setup(
            self.source_agents, self.target,
            "--source-ref", "TESTREF", "--dry-run",
        )
        self.assertEqual(rc, 0, f"dry-run should succeed, stdout={stdout!r}")
        self.assertIn("DRY-RUN", stdout.upper(),
                      "dry-run output should indicate it's a dry run")

        # Target should NOT have files (except maybe config, which wouldn't exist yet)
        target_files = os.listdir(self.target) if os.path.isdir(self.target) else []
        for f in target_files:
            if f.endswith(".md"):
                self.fail(f"dry-run must not create markdown files: found {f}")

    def test_setup_force_reinstalls_prompt_then_reapplies_effective_model_fields(self):
        """Final artifact keeps effective model/variant even after forced prompt sync."""
        # First setup
        rc1, _, _ = run_setup(self.source_agents, self.target, "--source-ref", "FIRSTREF")
        self.assertEqual(rc1, 0)

        original = read_file(self.target, "dev-orchestrator.md")
        self.assertIn("model: openai/gpt-5", original)

        # Modify canonical prompt
        write_file(self.source_root, "agents/dev-orchestrator.md",
                   "---\nname: dev-orchestrator\nmode: primary\npermission:\n  edit: deny\n---\n# Dev Orchestrator v2\n")

        # Force reinstall should overwrite prompt but re-activate model/variant
        rc2, _, stderr2 = run_setup(
            self.source_agents, self.target,
            "--source-ref", "SECONDREF", "--force",
        )
        self.assertEqual(rc2, 0, f"force setup should succeed, stderr={stderr2!r}")

        content = read_file(self.target, "dev-orchestrator.md")
        self.assertIn("# Dev Orchestrator v2", content,
                      "force setup must overwrite prompt body")
        self.assertIn("model: openai/gpt-5", content,
                      "force setup must re-apply model after prompt overwrite")
        self.assertIn("variant: medium", content,
                      "force setup must re-apply variant after prompt overwrite")


if __name__ == "__main__":
    unittest.main(verbosity=2)
