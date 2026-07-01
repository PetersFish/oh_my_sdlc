"""Behavior tests for .githooks/pre-commit agent distribution handling.

Tests that the pre-commit hook correctly allows distributed-only agent changes
when validation checks (install_agents.py --check and activate_agents_config.py --check)
pass for all three targets (.opencode/, .claude/, .cursor/).
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest


_REPO_SCRIPTS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "scripts"
)
_HOOK_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".githooks", "pre-commit"
)


def write_file(root: str, relpath: str, content: str) -> None:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def run_git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=repo,
    )


CANONICAL_AGENT = textwrap.dedent("""\
---
name: test-agent
mode: subagent
description: A test agent
---
# Test Agent

Body content here.
""")

MINIMAL_CONFIG = textwrap.dedent("""\
schema_version: 1
defaults:
  variant: medium
profiles:
  test:
    model: openai/gpt-4
    variant: medium
agents:
  test-agent:
    profile: test
""")

# After activation, the agent markdown in targets will include model + variant
ACTIVATED_AGENT = textwrap.dedent("""\
---
name: test-agent
mode: subagent
description: A test agent
model: openai/gpt-4
variant: medium
---
# Test Agent

Body content here.
""")


class TestPreCommitDistributedAgents(unittest.TestCase):
    """Tests that the pre-commit hook correctly handles distributed-only agent changes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Init git repo
        run_git(self.tmp, "init", "--initial-branch=main")
        run_git(self.tmp, "config", "user.email", "test@example.com")
        run_git(self.tmp, "config", "user.name", "Test User")

        # Set hooks path
        run_git(self.tmp, "config", "core.hooksPath", ".githooks")

        # Install the pre-commit hook
        hook_dest = os.path.join(self.tmp, ".githooks", "pre-commit")
        os.makedirs(os.path.dirname(hook_dest), exist_ok=True)
        shutil.copy2(_HOOK_PATH, hook_dest)
        os.chmod(hook_dest, stat.S_IRWXU)

        # Copy the scripts the hook depends on
        scripts_dest = os.path.join(self.tmp, "scripts")
        os.makedirs(scripts_dest, exist_ok=True)
        for filename in ["install_agents.py", "activate_agents_config.py", "agent_config_lib.py"]:
            shutil.copy2(os.path.join(_REPO_SCRIPTS, filename), os.path.join(scripts_dest, filename))

        # Create dummy sync_templates.py (Rule 1 and 2 need it to exist and pass)
        dummy_sync = os.path.join(
            self.tmp, "skills", "sdlc-project-bootstrap", "scripts", "sync_templates.py"
        )
        write_file(self.tmp,
                   "skills/sdlc-project-bootstrap/scripts/sync_templates.py",
                   textwrap.dedent("""\
                       import sys
                       # Dummy for testing - always passes
                       sys.exit(0)
                   """))

        # Create canonical agents/ (source)
        write_file(self.tmp, "agents/test-agent.md", CANONICAL_AGENT)

        # Create canonical config template in agents/config/
        write_file(self.tmp, "agents/config/model-profiles.yaml", MINIMAL_CONFIG)

        # Create a dummy agents/config directory for each target (needed by
        # install_agents.py --check which checks for target config existence)
        self._setup_target(".opencode/agents")
        self._setup_target(".claude/agents")
        self._setup_target(".cursor/agents")

        # Make an initial commit with everything (--no-verify to skip pre-commit)
        run_git(self.tmp, "add", ".")
        run_git(self.tmp, "commit", "--no-verify", "-m", "initial")

    def _setup_target(self, target_rel: str):
        """Set up a distributed target with activated agent and config."""
        target_dir = os.path.join(self.tmp, target_rel)
        os.makedirs(os.path.join(target_dir, "config"), exist_ok=True)

        # Write the agent markdown with activation fields
        write_file(self.tmp, f"{target_rel}/test-agent.md", ACTIVATED_AGENT)

        # Write the target config
        write_file(self.tmp, f"{target_rel}/config/model-profiles.yaml", MINIMAL_CONFIG)

        # Write .agent-install.json (needed for install check)
        import json
        metadata = {
            "source_repo": self.tmp,
            "source_ref": "testref",
            "installed_at": "2025-01-01T00:00:00+00:00",
            "status": "stable",
            "files": {"test-agent.md": "abc123"},
        }
        write_file(
            self.tmp,
            f"{target_rel}/.agent-install.json",
            json.dumps(metadata, indent=2) + "\n",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run_hook(self) -> int:
        """Run the pre-commit hook and return its exit code."""
        result = subprocess.run(
            [".githooks/pre-commit"],
            capture_output=True, text=True, cwd=self.tmp,
            env={**os.environ, "GIT_DIR": os.path.join(self.tmp, ".git")},
        )
        return result.returncode, result.stdout, result.stderr

    def test_distributed_only_changes_pass_when_validation_checks_pass(self):
        """Distributed-only staged changes should pass when both --check
        validations succeed on all three targets."""
        # Simulate a legitimate activation-managed update: change target config
        # and re-render matching frontmatter in all three distributed targets.
        for target in [".opencode/agents", ".claude/agents", ".cursor/agents"]:
            config_path = os.path.join(self.tmp, target, "config", "model-profiles.yaml")
            config = open(config_path, encoding="utf-8").read()
            open(config_path, "w", encoding="utf-8").write(
                config.replace("variant: medium", "variant: high")
            )

            agent_path = os.path.join(self.tmp, target, "test-agent.md")
            agent = open(agent_path, encoding="utf-8").read()
            open(agent_path, "w", encoding="utf-8").write(
                agent.replace("variant: medium", "variant: high")
            )

        # Stage ONLY the distributed agent files (not canonical agents/)
        run_git(
            self.tmp,
            "add",
            ".opencode/agents/config/model-profiles.yaml",
            ".opencode/agents/test-agent.md",
            ".claude/agents/config/model-profiles.yaml",
            ".claude/agents/test-agent.md",
            ".cursor/agents/config/model-profiles.yaml",
            ".cursor/agents/test-agent.md",
        )

        # Run the hook - should pass after our fix (blocked before fix)
        rc, stdout, stderr = self._run_hook()
        self.assertEqual(rc, 0,
                         f"distributed-only changes should pass validation, got rc={rc}\n"
                         f"stdout={stdout!r}\nstderr={stderr!r}")

    def test_mixed_canonical_and_distributed_changes_pass_when_both_checks_pass(self):
        """Mixed canonical+distributed staging should pass when sync and activation are both valid."""
        canonical_path = os.path.join(self.tmp, "agents", "test-agent.md")
        canonical = open(canonical_path, encoding="utf-8").read()
        open(canonical_path, "w", encoding="utf-8").write(
            canonical.replace("# Test Agent", "# Updated Test Agent")
        )

        for target in [".opencode/agents", ".claude/agents", ".cursor/agents"]:
            target_path = os.path.join(self.tmp, target, "test-agent.md")
            target_content = open(target_path, encoding="utf-8").read()
            open(target_path, "w", encoding="utf-8").write(
                target_content.replace("# Test Agent", "# Updated Test Agent")
            )

        run_git(
            self.tmp,
            "add",
            "agents/test-agent.md",
            ".opencode/agents/test-agent.md",
            ".claude/agents/test-agent.md",
            ".cursor/agents/test-agent.md",
        )

        rc, stdout, stderr = self._run_hook()
        self.assertEqual(rc, 0,
                         f"mixed staged changes should pass when validation succeeds, got rc={rc}\n"
                         f"stdout={stdout!r}\nstderr={stderr!r}")

    def test_distributed_only_changes_block_when_install_check_fails(self):
        """Distributed-only staged changes should be blocked when
        install_agents.py --check fails on any target."""
        # Corrupt the target agent to make install check fail
        for target in [".opencode/agents", ".claude/agents", ".cursor/agents"]:
            target_md = os.path.join(self.tmp, target, "test-agent.md")
            content = open(target_md, encoding="utf-8").read()
            # Change the body content to trigger drift
            modified = content.replace("Body content here", "corrupted body")
            open(target_md, "w", encoding="utf-8").write(modified)

        # Stage ONLY the distributed agent files
        run_git(self.tmp, "add",
                ".opencode/agents/test-agent.md",
                ".claude/agents/test-agent.md",
                ".cursor/agents/test-agent.md")

        rc, stdout, stderr = self._run_hook()
        self.assertNotEqual(rc, 0,
                            "distributed-only changes should fail when install check fails")
        combined = f"{stdout}\n{stderr}"
        self.assertIn("DRIFT", combined,
                      "output should mention drift on install check failure")

    def test_distributed_only_changes_block_when_activate_check_fails(self):
        """Distributed-only staged changes should be blocked when
        activate_agents_config.py --check fails on any target."""
        # Change the target config without re-activating
        for target in [".opencode/agents", ".claude/agents", ".cursor/agents"]:
            config_path = os.path.join(self.tmp, target, "config", "model-profiles.yaml")
            content = open(config_path, encoding="utf-8").read()
            modified = content.replace("variant: medium", "variant: high")
            open(config_path, "w", encoding="utf-8").write(modified)

        # Stage ONLY the distributed agent files (config changes)
        run_git(self.tmp, "add",
                ".opencode/agents/config/model-profiles.yaml",
                ".claude/agents/config/model-profiles.yaml",
                ".cursor/agents/config/model-profiles.yaml")

        rc, stdout, stderr = self._run_hook()
        self.assertNotEqual(rc, 0,
                            "distributed-only changes should fail when activate check fails")
        combined = f"{stdout}\n{stderr}"
        self.assertIn("DRIFT", combined,
                      "output should mention drift on activate check failure")

    def test_canonical_only_changes_still_require_distributed_copies(self):
        """When canonical agents/ are staged without distributed copies,
        the hook should still block."""
        # Change canonical agent
        target_md = os.path.join(self.tmp, "agents", "test-agent.md")
        content = open(target_md, encoding="utf-8").read()
        modified = content.replace("# Test Agent", "# Modified Test Agent")
        open(target_md, "w", encoding="utf-8").write(modified)

        # Stage only canonical
        run_git(self.tmp, "add", "agents/test-agent.md")

        rc, stdout, stderr = self._run_hook()
        self.assertNotEqual(rc, 0,
                            "canonical-only changes should require distributed copies")
        combined = f"{stdout}\n{stderr}"
        self.assertIn("distributed", combined.lower(),
                      "output should mention distributed copies")

    def test_distributed_only_changes_block_when_activate_check_fails_on_one_target(self):
        """A single-target activation drift should still block distributed-only commits."""
        config_path = os.path.join(self.tmp, ".cursor/agents", "config", "model-profiles.yaml")
        content = open(config_path, encoding="utf-8").read()
        modified = content.replace("variant: medium", "variant: high")
        open(config_path, "w", encoding="utf-8").write(modified)

        run_git(self.tmp, "add", ".cursor/agents/config/model-profiles.yaml")

        rc, stdout, stderr = self._run_hook()
        self.assertNotEqual(rc, 0,
                            "should block when any one target fails activate check")
        combined = f"{stdout}\n{stderr}"
        self.assertIn("DRIFT", combined)

    def test_mixed_canonical_and_distributed_changes_block_when_activate_check_fails(self):
        """Mixed canonical+distributed staging should also enforce activation validity."""
        canonical_path = os.path.join(self.tmp, "agents", "test-agent.md")
        canonical = open(canonical_path, encoding="utf-8").read()
        updated_canonical = canonical.replace("# Test Agent", "# Updated Test Agent")
        open(canonical_path, "w", encoding="utf-8").write(updated_canonical)

        # Keep template sync valid by updating all distributed prompt bodies to match.
        for target in [".opencode/agents", ".claude/agents", ".cursor/agents"]:
            target_path = os.path.join(self.tmp, target, "test-agent.md")
            target_content = open(target_path, encoding="utf-8").read()
            open(target_path, "w", encoding="utf-8").write(
                target_content.replace("# Test Agent", "# Updated Test Agent")
            )

        # Introduce activation drift on just one target by changing config without
        # re-activating the prompt frontmatter.
        config_path = os.path.join(self.tmp, ".opencode/agents", "config", "model-profiles.yaml")
        content = open(config_path, encoding="utf-8").read()
        open(config_path, "w", encoding="utf-8").write(content.replace("variant: medium", "variant: high"))

        run_git(
            self.tmp,
            "add",
            "agents/test-agent.md",
            ".opencode/agents/test-agent.md",
            ".claude/agents/test-agent.md",
            ".cursor/agents/test-agent.md",
            ".opencode/agents/config/model-profiles.yaml",
        )

        rc, stdout, stderr = self._run_hook()
        self.assertNotEqual(rc, 0,
                            "mixed staged changes should fail when activate check fails")
        combined = f"{stdout}\n{stderr}"
        self.assertIn("DRIFT", combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
