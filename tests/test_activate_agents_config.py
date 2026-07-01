"""Behavior tests for scripts/activate_agents_config.py."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "activate_agents_config.py",
)


def write_file(root: str, relpath: str, content: str) -> None:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def run_activate(target: str, *extra_args: str):
    args = [
        sys.executable,
        SCRIPT,
        "--target", target,
        *extra_args,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


AGENT_MD = """---
name: test-agent
mode: subagent
description: A test agent
tools:
  bash: true
---
# Test Agent

This is the body.
"""

AGENT_MD_NO_FRONTMATTER = """# Test Agent

This agent has no frontmatter.
"""

MINIMAL_CONFIG = """schema_version: 1
defaults:
  variant: medium
profiles:
  test:
    model: openai/gpt-4
    variant: medium
agents:
  test-agent:
    profile: test
"""


class TestActivateAgentsConfig(unittest.TestCase):
    """Tests for activation behavior."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.target, exist_ok=True)

        # Write config
        write_file(self.tmp, "target/config/model-profiles.yaml", MINIMAL_CONFIG)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_activation_injects_profile_model_and_default_variant(self):
        """Profile model + default variant are written to target markdown."""
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        rc, stdout, stderr = run_activate(self.target)
        self.assertEqual(rc, 0, f"activation should succeed, stderr={stderr!r}")

        content = open(os.path.join(self.target, "test-agent.md"), encoding="utf-8").read()
        self.assertIn("model: openai/gpt-4", content)
        self.assertIn("variant: medium", content)
        # Non-activation fields preserved
        self.assertIn("name: test-agent", content)
        self.assertIn("bash: true", content)
        self.assertIn("# Test Agent", content)

    def test_activation_preserves_non_managed_fields(self):
        """Activation does not alter fields other than model/variant."""
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        content = open(os.path.join(self.target, "test-agent.md"), encoding="utf-8").read()
        self.assertIn("name: test-agent", content)
        self.assertIn("mode: subagent", content)
        self.assertIn("description: A test agent", content)
        self.assertIn("bash: true", content)

    def test_activation_uses_profile_variant_override(self):
        """Profile variant overrides defaults."""
        config = """schema_version: 1
defaults:
  variant: medium
profiles:
  test:
    model: openai/gpt-4
    variant: high
agents:
  test-agent:
    profile: test
"""
        write_file(self.tmp, "target/config/model-profiles.yaml", config)
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        from support.frontmatter import read_frontmatter
        from pathlib import Path
        fm = read_frontmatter(Path(os.path.join(self.target, "test-agent.md")))
        self.assertEqual(fm.get("variant"), "high")

    def test_activation_uses_agent_variant_override(self):
        """Agent variant overrides profile/default."""
        config = """schema_version: 1
defaults:
  variant: medium
profiles:
  test:
    model: openai/gpt-4
    variant: high
agents:
  test-agent:
    profile: test
    variant: low
"""
        write_file(self.tmp, "target/config/model-profiles.yaml", config)
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        from support.frontmatter import read_frontmatter
        from pathlib import Path
        fm = read_frontmatter(Path(os.path.join(self.target, "test-agent.md")))
        self.assertEqual(fm.get("variant"), "low")

    def test_activation_uses_agent_model_override(self):
        """Agent model override wins over profile."""
        config = """schema_version: 1
defaults:
  variant: medium
profiles:
  test:
    model: openai/gpt-4
agents:
  test-agent:
    profile: test
    model: anthropic/claude-4
"""
        write_file(self.tmp, "target/config/model-profiles.yaml", config)
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        from support.frontmatter import read_frontmatter
        from pathlib import Path
        fm = read_frontmatter(Path(os.path.join(self.target, "test-agent.md")))
        self.assertEqual(fm.get("model"), "anthropic/claude-4")

    def test_activation_can_insert_frontmatter_when_missing(self):
        """Body-only markdown gets valid frontmatter inserted."""
        write_file(self.tmp, "target/test-agent.md", AGENT_MD_NO_FRONTMATTER)

        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        from support.frontmatter import read_frontmatter
        from pathlib import Path
        fm = read_frontmatter(Path(os.path.join(self.target, "test-agent.md")))
        self.assertEqual(fm.get("model"), "openai/gpt-4")
        self.assertEqual(fm.get("variant"), "medium")

        content = open(os.path.join(self.target, "test-agent.md"), encoding="utf-8").read()
        self.assertIn("This agent has no frontmatter.", content)

    def test_activation_rewrites_fields_after_template_sync_force(self):
        """Activation restores model/variant after prompt overwrite."""
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        # First activation
        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        # Simulate template sync overwrite (remove model/variant)
        content = open(os.path.join(self.target, "test-agent.md"), encoding="utf-8").read()
        # Remove model and variant lines
        lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("model:") or stripped.startswith("variant:"):
                continue
            lines.append(line)
        stripped_content = "\n".join(lines)
        with open(os.path.join(self.target, "test-agent.md"), "w", encoding="utf-8") as f:
            f.write(stripped_content)

        # Re-activate
        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        from support.frontmatter import read_frontmatter
        from pathlib import Path
        fm = read_frontmatter(Path(os.path.join(self.target, "test-agent.md")))
        self.assertEqual(fm.get("model"), "openai/gpt-4")
        self.assertEqual(fm.get("variant"), "medium")


class TestActivateCheck(unittest.TestCase):
    """Tests for activation --check behavior."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.target, exist_ok=True)
        write_file(self.tmp, "target/config/model-profiles.yaml", MINIMAL_CONFIG)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_check_reports_drift_when_config_changes_without_rerender(self):
        """--check fails after editing target config but before rerender."""
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        # Activate first
        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        # Change config
        new_config = MINIMAL_CONFIG.replace("variant: medium", "variant: high")
        write_file(self.tmp, "target/config/model-profiles.yaml", new_config)

        # Check should now fail
        rc, stdout, _ = run_activate(self.target, "--check")
        self.assertNotEqual(rc, 0, "check should fail after config changes")

    def test_check_passes_when_in_sync(self):
        """--check passes when rendered matches config."""
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        # Activate first
        rc, _, _ = run_activate(self.target)
        self.assertEqual(rc, 0)

        # Check should pass
        rc, stdout, _ = run_activate(self.target, "--check")
        self.assertEqual(rc, 0, f"check should pass when in sync, got rc={rc}, stdout={stdout!r}")

    def test_check_fails_when_config_missing(self):
        """--check fails when target config doesn't exist."""
        os.remove(os.path.join(self.target, "config", "model-profiles.yaml"))
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        rc, stdout, _ = run_activate(self.target, "--check")
        self.assertNotEqual(rc, 0, "check should fail when config is missing")


class TestActivateDryRun(unittest.TestCase):
    """Tests for --dry-run behavior."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.target, exist_ok=True)
        write_file(self.tmp, "target/config/model-profiles.yaml", MINIMAL_CONFIG)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_dry_run_reports_without_writing(self):
        """--dry-run reports planned changes but does not mutate files."""
        write_file(self.tmp, "target/test-agent.md", AGENT_MD_NO_FRONTMATTER)

        rc, stdout, _ = run_activate(self.target, "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("[DRY-RUN]", stdout)
        self.assertIn("test-agent.md", stdout)

        # File should be unchanged
        content = open(os.path.join(self.target, "test-agent.md"), encoding="utf-8").read()
        self.assertEqual(content, AGENT_MD_NO_FRONTMATTER)

    def test_dry_run_noop_when_in_sync(self):
        """--dry-run reports nothing to change when already activated."""
        write_file(self.tmp, "target/test-agent.md", AGENT_MD)

        # Activate first
        run_activate(self.target)

        rc, stdout, _ = run_activate(self.target, "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("already activated", stdout.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
