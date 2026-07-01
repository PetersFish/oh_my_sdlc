"""Behavior tests for scripts/activate_agents_config.py."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "activate_agents_config.py",
)


def write_file(root: str, relpath: str, content: str) -> None:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_file(root: str, relpath: str) -> str:
    with open(os.path.join(root, relpath), encoding="utf-8") as f:
        return f.read()


def run_activate(target: str, *extra_args: str):
    args = [
        sys.executable,
        SCRIPT,
        "--target", target,
        *extra_args,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestActivateAgentsConfig(unittest.TestCase):
    """WP3: activation renders effective model/variant from target config."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.target, exist_ok=True)

        # Create target config
        write_file(self.target, "config/model-profiles.yaml", """\
schema_version: 1
defaults:
  variant: medium
profiles:
  deep:
    model: opencode-go/deepseek-v4
    variant: high
  standard:
    model: openai/gpt-5
agents:
  implement-agent:
    profile: deep
  review-agent:
    profile: standard
""")

        # Create target agent markdown files (body-only, no frontmatter)
        write_file(self.target, "implement-agent.md", "# Implement Agent\n\nImplement things.\n")
        write_file(self.target, "review-agent.md", "# Review Agent\n\nReview things.\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    # ---- WP3 tests ----

    def test_activation_injects_profile_model_and_default_variant(self):
        """Profile model + default variant: medium are written."""
        rc, stdout, stderr = run_activate(self.target)
        self.assertEqual(rc, 0, f"activation should succeed, stdout={stdout!r} stderr={stderr!r}")

        content = read_file(self.target, "review-agent.md")
        self.assertIn("model: openai/gpt-5", content,
                      "activation must inject profile model")
        self.assertIn("variant: medium", content,
                      "activation must use defaults.variant when profile has none")

        # implement-agent has profile "deep" with model deepseek-v4 and variant high
        content2 = read_file(self.target, "implement-agent.md")
        self.assertIn("model: opencode-go/deepseek-v4", content2)
        self.assertIn("variant: high", content2)

    def test_activation_uses_profile_variant_override(self):
        """Profile variant overrides defaults."""
        write_file(self.target, "config/model-profiles.yaml", """\
schema_version: 1
defaults:
  variant: low
profiles:
  p1:
    model: openai/gpt-5
    variant: high
agents:
  review-agent:
    profile: p1
""")
        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        content = read_file(self.target, "review-agent.md")
        self.assertIn("variant: high", content, "profile variant should override defaults")

    def test_activation_uses_agent_variant_override(self):
        """Agent variant overrides profile/default."""
        write_file(self.target, "config/model-profiles.yaml", """\
schema_version: 1
defaults:
  variant: low
profiles:
  p1:
    model: openai/gpt-5
    variant: high
agents:
  review-agent:
    profile: p1
    variant: turbo
""")
        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        content = read_file(self.target, "review-agent.md")
        self.assertIn("variant: turbo", content, "agent variant should override profile")

    def test_activation_uses_agent_model_override(self):
        """Agent model override wins over profile."""
        write_file(self.target, "config/model-profiles.yaml", """\
schema_version: 1
defaults:
  variant: medium
profiles:
  p1:
    model: openai/gpt-5
agents:
  review-agent:
    profile: p1
    model: openai/gpt-6
""")
        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        content = read_file(self.target, "review-agent.md")
        self.assertIn("model: openai/gpt-6", content, "agent model override must win")

    def test_activation_check_reports_drift_when_config_changes_without_rerender(self):
        """--check fails after editing target config but before rerender."""
        # First activation
        rc1, _, _ = run_activate(self.target)
        self.assertEqual(rc1, 0)

        # Check should pass
        rc2, stdout2, _ = run_activate(self.target, "--check")
        self.assertEqual(rc2, 0, f"check should pass after activation, stdout={stdout2!r}")

        # Change config (change model for review-agent)
        write_file(self.target, "config/model-profiles.yaml", """\
schema_version: 1
defaults:
  variant: medium
profiles:
  standard:
    model: openai/gpt-5-mini
agents:
  review-agent:
    profile: standard
""")

        # Check should now fail (drift)
        rc3, stdout3, _ = run_activate(self.target, "--check")
        self.assertNotEqual(rc3, 0, "check must fail after config change without rerender")
        self.assertIn("review-agent", stdout3.lower(),
                      "drift report should mention the drifted agent")

    def test_activation_can_insert_frontmatter_when_missing(self):
        """Body-only markdown gets valid frontmatter inserted."""
        write_file(self.target, "config/model-profiles.yaml", """\
schema_version: 1
defaults:
  variant: medium
profiles:
  p1:
    model: openai/gpt-5
agents:
  review-agent:
    profile: p1
""")
        # Body-only file (no frontmatter)
        write_file(self.target, "review-agent.md", "# No Frontmatter\n\nJust a body.\n")

        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        content = read_file(self.target, "review-agent.md")
        self.assertTrue(content.startswith("---"), "frontmatter must be inserted")
        self.assertIn("model: openai/gpt-5", content)
        self.assertIn("variant: medium", content)
        self.assertIn("# No Frontmatter", content, "body preserved")
        self.assertIn("Just a body.", content, "body preserved")

    def test_activation_rewrites_fields_after_template_sync_force(self):
        """Activation restores model/variant after prompt overwrite."""
        # First activation
        rc1, _, _ = run_activate(self.target)
        self.assertEqual(rc1, 0)

        # Simulate template-sync force — overwrite markdown without model/variant
        write_file(self.target, "review-agent.md", "# Review Agent (force overwritten)\n")
        # Check should detect drift
        rc2, stdout2, _ = run_activate(self.target, "--check")
        self.assertNotEqual(rc2, 0, "should detect missing model/variant after force overwrite")

        # Re-activate should restore fields
        rc3, _, _ = run_activate(self.target)
        self.assertEqual(rc3, 0)
        content = read_file(self.target, "review-agent.md")
        self.assertIn("model: openai/gpt-5", content)
        self.assertIn("variant: medium", content)
        self.assertIn("Review Agent (force overwritten)", content, "body preserved after activation")

    def test_activation_dry_run_reports_actions_without_writing(self):
        """--dry-run reports what would change but does not modify files."""
        # Capture original file content
        original_content = read_file(self.target, "review-agent.md")

        rc, stdout, _ = run_activate(self.target, "--dry-run")
        self.assertEqual(rc, 0, f"dry-run should succeed, stdout={stdout!r}")
        self.assertIn("review-agent", stdout.lower(),
                      "dry-run should mention affected agent")

        # File should be unchanged
        after_content = read_file(self.target, "review-agent.md")
        self.assertEqual(after_content, original_content,
                         "dry-run must NOT modify target files")


if __name__ == "__main__":
    unittest.main(verbosity=2)
