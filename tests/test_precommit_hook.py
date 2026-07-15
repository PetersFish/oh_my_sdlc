"""Behavior tests for .githooks/pre-commit agent distribution handling and
phase-aware policy integration.

Tests that the pre-commit hook correctly allows distributed-only agent changes
when validation checks (install_agents.py --check and activate_agents_config.py --check)
pass for all three targets (.opencode/, .claude/, .cursor/), and that the
phase-aware policy integration allows attributable stale derived targets
during apply_change while rejecting manual/mixed/unrelated generated changes.
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


# ---------------------------------------------------------------------------
# Phase-aware policy integration tests (Slice 3: git-hook-integration)
# ---------------------------------------------------------------------------

import json as _json


def _write_run_state(root: str, run_id: str, phase: str = "apply_change",
                     execution_mode: str = "main_checkout",
                     worktree_path: str = "",
                     control_root: str = "") -> str:
    """Write a minimal valid workflow run state under root."""
    state = {
        "version": 1,
        "run_id": run_id,
        "workflow": "sdlc-main",
        "flow_type": "lightweight-flow",
        "status": "running",
        "current_phase": phase,
        "primary_subject": {"type": "spec_change", "id": "test-change"},
        "context": {
            "change_id": "test-change",
            "execution_mode": execution_mode,
            "control_root": control_root,
            "worktree_path": worktree_path,
        },
        "phase_readiness": {"phase": phase, "ready": True, "missing_required_inputs": []},
        "pending_hooks": [],
        "completed_hooks": [],
        "completed_phases": [],
        "gates": {},
        "evidence": {},
        "block": None,
        "updated_at": "2026-07-15T00:00:00",
    }
    run_dir = os.path.join(root, ".ai", "workflows", "runs", "active", run_id)
    os.makedirs(run_dir, exist_ok=True)
    run_json = os.path.join(run_dir, "run.json")
    with open(run_json, "w", encoding="utf-8") as f:
        _json.dump(state, f)
    return run_json


class TestPhaseAwareHookIntegration(unittest.TestCase):
    """Integration tests exercising the real .githooks/pre-commit with the
    phase-aware policy during apply_change.

    The hook must:
    - allow attributable stale derived targets during apply_change;
    - reject manual generated edits during apply_change;
    - reject generated files staged with canonical changes (mixed commit);
    - preserve existing non-workflow behavior when no active run exists.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Init git repo
        run_git(self.tmp, "init", "--initial-branch=main")
        run_git(self.tmp, "config", "user.email", "test@example.com")
        run_git(self.tmp, "config", "user.name", "Test User")
        run_git(self.tmp, "config", "core.hooksPath", ".githooks")

        # Install the pre-commit hook
        hook_dest = os.path.join(self.tmp, ".githooks", "pre-commit")
        os.makedirs(os.path.dirname(hook_dest), exist_ok=True)
        shutil.copy2(_HOOK_PATH, hook_dest)
        os.chmod(hook_dest, stat.S_IRWXU)

        # Copy the scripts the hook depends on
        scripts_dest = os.path.join(self.tmp, "scripts")
        os.makedirs(scripts_dest, exist_ok=True)
        for filename in [
            "install_agents.py",
            "activate_agents_config.py",
            "agent_config_lib.py",
            "setup_agents.py",
            "derived_sync_hook_policy.py",
        ]:
            shutil.copy2(os.path.join(_REPO_SCRIPTS, filename),
                         os.path.join(scripts_dest, filename))

        # Install stub sync_derived_artifacts.py that emits valid JSON so
        # the policy's sync-check subprocess gets evidence_ok=True.  The
        # stub also provides classify_changes for import by evaluate_policy.
        stub_src = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "support", "stub_sync_derived.py",
        )
        shutil.copy2(stub_src,
                     os.path.join(scripts_dest, "sync_derived_artifacts.py"))

        # Copy sync_templates.py (real version for stale detection)
        write_file(
            self.tmp,
            "skills/sdlc-project-bootstrap/scripts/sync_templates.py",
            open(os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "skills", "sdlc-project-bootstrap", "scripts", "sync_templates.py",
            )).read(),
        )

        # Create an empty canonical templates dir so sync_templates.py --check
        # does not fail with "templates directory not found".  When neither the
        # live governed file nor the template file exists, both hash to "" and
        # the check reports no drift.  This mirrors a real repo where the
        # templates dir exists and Rule 1 (live <-> canonical) must always run.
        os.makedirs(
            os.path.join(self.tmp, "skills", "sdlc-project-bootstrap", "templates",
                         "workflow", "workflow_runtime"),
            exist_ok=True,
        )

        # Copy check_skill_distribution.py
        os.makedirs(
            os.path.join(self.tmp, "skills",
                         "meta-skill-lifecycle-governance", "scripts"),
            exist_ok=True,
        )
        shutil.copy2(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "skills", "meta-skill-lifecycle-governance", "scripts",
                "check_skill_distribution.py",
            ),
            os.path.join(self.tmp, "skills", "meta-skill-lifecycle-governance",
                         "scripts", "check_skill_distribution.py"),
        )

        # Create canonical agents/ (source)
        write_file(self.tmp, "agents/test-agent.md", CANONICAL_AGENT)
        write_file(self.tmp, "agents/config/model-profiles.yaml", MINIMAL_CONFIG)

        # Create distributed agent targets with activated content
        for target in [".opencode/agents", ".claude/agents", ".cursor/agents"]:
            target_dir = os.path.join(self.tmp, target)
            os.makedirs(os.path.join(target_dir, "config"), exist_ok=True)
            write_file(self.tmp, f"{target}/test-agent.md", ACTIVATED_AGENT)
            write_file(self.tmp, f"{target}/config/model-profiles.yaml", MINIMAL_CONFIG)
            # Write .agent-install.json
            metadata = {
                "source_repo": self.tmp,
                "source_ref": "testref",
                "installed_at": "2025-01-01T00:00:00+00:00",
                "status": "stable",
                "files": {"test-agent.md": "abc123"},
            }
            write_file(self.tmp, f"{target}/.agent-install.json",
                       _json.dumps(metadata, indent=2) + "\n")

        # Initial commit (skip hook)
        run_git(self.tmp, "add", ".")
        run_git(self.tmp, "commit", "--no-verify", "-m", "initial")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_hook(self):
        """Run the pre-commit hook and return (rc, stdout, stderr)."""
        result = subprocess.run(
            [".githooks/pre-commit"],
            capture_output=True, text=True, cwd=self.tmp,
            env={**os.environ, "GIT_DIR": os.path.join(self.tmp, ".git")},
        )
        return result.returncode, result.stdout, result.stderr

    def test_apply_phase_allows_attributable_stale_derived_targets(self):
        """During apply_change, a canonical agent change with stale but
        untouched derived copies MUST be allowed by the hook."""
        # Create an active apply_change workflow run
        _write_run_state(self.tmp, "2026-07-15-test", phase="apply_change",
                         control_root=self.tmp)

        # Modify canonical agent (this makes distributed copies stale)
        canonical_path = os.path.join(self.tmp, "agents", "test-agent.md")
        content = open(canonical_path, encoding="utf-8").read()
        open(canonical_path, "w", encoding="utf-8").write(
            content.replace("# Test Agent", "# Updated Agent")
        )

        # Stage only the canonical change (NOT the distributed copies)
        run_git(self.tmp, "add", "agents/test-agent.md")

        rc, stdout, stderr = self._run_hook()
        self.assertEqual(rc, 0,
                         f"apply_phase should allow attributable stale drift, "
                         f"got rc={rc}\nstdout={stdout!r}\nstderr={stderr!r}")

    def test_apply_phase_rejects_manual_generated_edit(self):
        """During apply_change, a manually modified generated file MUST be
        rejected by the hook."""
        # Create an active apply_change workflow run
        _write_run_state(self.tmp, "2026-07-15-test", phase="apply_change",
                         control_root=self.tmp)

        # Modify canonical agent
        canonical_path = os.path.join(self.tmp, "agents", "test-agent.md")
        content = open(canonical_path, encoding="utf-8").read()
        open(canonical_path, "w", encoding="utf-8").write(
            content.replace("# Test Agent", "# Updated Agent")
        )

        # Also manually modify a generated copy (not staged)
        gen_path = os.path.join(self.tmp, ".opencode/agents", "test-agent.md")
        gen_content = open(gen_path, encoding="utf-8").read()
        open(gen_path, "w", encoding="utf-8").write(
            gen_content.replace("Body content here", "tampered body")
        )

        # Stage only the canonical change
        run_git(self.tmp, "add", "agents/test-agent.md")

        rc, stdout, stderr = self._run_hook()
        self.assertNotEqual(rc, 0,
                            "manual generated edit during apply should be rejected")
        # The hook output should include a stable reason and offending paths
        combined = f"{stdout}\n{stderr}"
        self.assertTrue(
            "manual_generated_artifact_change" in combined
            or "unrelated_generated_drift" in combined,
            f"output should include stable rejection reason, got: {combined!r}",
        )

    def test_apply_phase_rejects_mixed_authored_generated_commit(self):
        """During apply_change, a commit with both canonical and generated
        files staged MUST be rejected (mixed commit)."""
        # Create an active apply_change workflow run
        _write_run_state(self.tmp, "2026-07-15-test", phase="apply_change",
                         control_root=self.tmp)

        # Modify canonical agent and a generated copy
        canonical_path = os.path.join(self.tmp, "agents", "test-agent.md")
        content = open(canonical_path, encoding="utf-8").read()
        open(canonical_path, "w", encoding="utf-8").write(
            content.replace("# Test Agent", "# Updated Agent")
        )

        gen_path = os.path.join(self.tmp, ".opencode/agents", "test-agent.md")
        gen_content = open(gen_path, encoding="utf-8").read()
        open(gen_path, "w", encoding="utf-8").write(
            gen_content.replace("# Test Agent", "# Updated Agent")
        )

        # Stage BOTH canonical and generated
        run_git(self.tmp, "add",
                "agents/test-agent.md",
                ".opencode/agents/test-agent.md")

        rc, stdout, stderr = self._run_hook()
        self.assertNotEqual(rc, 0,
                            "mixed authored+generated commit should be rejected")
        combined = f"{stdout}\n{stderr}"
        self.assertTrue(
            "generated_artifact_mixed_with_authored_commit" in combined
            or "distributed" in combined.lower(),
            f"output should indicate mixed commit rejection, got: {combined!r}",
        )

    def test_apply_phase_allow_still_enforces_live_template_drift(self):
        """REMED (review block): during apply_change, when the policy allows
        attributable stale derived drift, the hook MUST still enforce Rule 1
        (live .ai/workflows/ <-> canonical template consistency).  The
        allowance bypasses ONLY generated-distribution drift (Rules 2-4
        distribution portions).  Unrelated live template drift must still
        block the commit.

        Scenario: active apply_change run, canonical agent change staged
        (attributable stale derived copies), AND unrelated live template
        drift (Rule 1 fails).  The hook must block on Rule 1, not exit 0.
        """
        # Create an active apply_change workflow run
        _write_run_state(self.tmp, "2026-07-15-test", phase="apply_change",
                         control_root=self.tmp)

        # Modify canonical agent (makes distributed copies stale = expected)
        canonical_path = os.path.join(self.tmp, "agents", "test-agent.md")
        content = open(canonical_path, encoding="utf-8").read()
        open(canonical_path, "w", encoding="utf-8").write(
            content.replace("# Test Agent", "# Updated Agent")
        )

        # Introduce UNRELATED live template drift: mutate the live
        # .ai/workflows/scripts/workflow.py without touching the canonical
        # template.  Rule 1 must catch this even when the policy allows.
        live_workflow = os.path.join(
            self.tmp, ".ai", "workflows", "scripts", "workflow.py"
        )
        os.makedirs(os.path.dirname(live_workflow), exist_ok=True)
        write_file(self.tmp, ".ai/workflows/scripts/workflow.py",
                   "# live drifted content\n")

        # Stage only the canonical agent change (attributable, policy allows)
        run_git(self.tmp, "add", "agents/test-agent.md")

        rc, stdout, stderr = self._run_hook()
        # Hook MUST block because Rule 1 (live <-> canonical) still runs.
        self.assertNotEqual(
            rc, 0,
            f"policy allowance must not bypass Rule 1 live-template drift; "
            f"got rc={rc}\nstdout={stdout!r}\nstderr={stderr!r}",
        )
        combined = f"{stdout}\n{stderr}"
        self.assertIn(
            "Template drift", combined,
            f"output should mention live template drift (Rule 1), got: {combined!r}",
        )

    def test_no_active_workflow_preserves_existing_behavior(self):
        """When no active workflow run exists, the hook MUST preserve existing
        non-workflow behavior (canonical-only changes still require
        distributed copies to be staged)."""
        # Modify canonical agent (no workflow run created)
        canonical_path = os.path.join(self.tmp, "agents", "test-agent.md")
        content = open(canonical_path, encoding="utf-8").read()
        open(canonical_path, "w", encoding="utf-8").write(
            content.replace("# Test Agent", "# Modified Agent")
        )

        # Stage only canonical (no distributed copies staged)
        run_git(self.tmp, "add", "agents/test-agent.md")

        rc, stdout, stderr = self._run_hook()
        # Existing behavior: canonical-only changes require distributed copies
        self.assertNotEqual(rc, 0,
                            "no-workflow canonical-only should require "
                            "distributed copies (existing behavior)")
        combined = f"{stdout}\n{stderr}"
        self.assertIn("distributed", combined.lower(),
                      "output should mention distributed copies")


class TestPolicyCliExitCodes(unittest.TestCase):
    """The derived_sync_hook_policy CLI exit codes must be:
    - 0: policy allows the commit (apply_phase with attributable drift or
      ordinary commit)
    - 1: policy blocks the commit (manual/mixed/unrelated/unattributed)
    - 2: no active workflow phase (defer to existing hook checks)
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        run_git(self.tmp, "init", "--initial-branch=main")
        run_git(self.tmp, "config", "user.email", "test@example.com")
        run_git(self.tmp, "config", "user.name", "Test User")
        # Copy the policy script
        os.makedirs(os.path.join(self.tmp, "scripts"), exist_ok=True)
        shutil.copy2(
            os.path.join(_REPO_SCRIPTS, "derived_sync_hook_policy.py"),
            os.path.join(self.tmp, "scripts", "derived_sync_hook_policy.py"),
        )
        shutil.copy2(
            os.path.join(_REPO_SCRIPTS, "setup_agents.py"),
            os.path.join(self.tmp, "scripts", "setup_agents.py"),
        )
        # Install stub sync_derived_artifacts.py that emits valid JSON so
        # the policy's sync-check subprocess gets evidence_ok=True.
        stub_src = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "support", "stub_sync_derived.py",
        )
        shutil.copy2(stub_src,
                     os.path.join(self.tmp, "scripts", "sync_derived_artifacts.py"))
        # Initial commit
        write_file(self.tmp, "README.md", "init\n")
        run_git(self.tmp, "add", "README.md")
        run_git(self.tmp, "commit", "--no-verify", "-m", "init")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_policy(self, *extra_args):
        cmd = [sys.executable, "scripts/derived_sync_hook_policy.py",
               "--root", self.tmp] + list(extra_args)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.tmp)

    def test_no_workflow_returns_exit_2(self):
        """No active workflow run -> exit 2 (defer to existing checks)."""
        result = self._run_policy("--json")
        self.assertEqual(result.returncode, 2,
                         f"no-workflow should exit 2 (defer), got rc={result.returncode}\n"
                         f"stdout={result.stdout!r}\nstderr={result.stderr!r}")

    def test_apply_phase_allow_returns_exit_0(self):
        """Apply_phase with attributable stale drift and no generated edits
        -> exit 0 (allow)."""
        _write_run_state(self.tmp, "2026-07-15-allow", phase="apply_change",
                         control_root=self.tmp)
        # No staged files, no generated changes -> allow
        result = self._run_policy("--json")
        self.assertEqual(result.returncode, 0,
                         f"apply_phase allow should exit 0, got rc={result.returncode}\n"
                         f"stdout={result.stdout!r}\nstderr={result.stderr!r}")

    def test_apply_phase_reject_returns_exit_1(self):
        """Apply_phase with a manually modified generated file -> exit 1
        (block)."""
        _write_run_state(self.tmp, "2026-07-15-reject", phase="apply_change",
                         control_root=self.tmp)
        # Create and modify a generated file
        gen_path = os.path.join(self.tmp, ".opencode", "agents", "test.md")
        write_file(self.tmp, ".opencode/agents/test.md", "manual\n")
        # Stage it
        run_git(self.tmp, "add", ".opencode/agents/test.md")
        result = self._run_policy("--json")
        self.assertEqual(result.returncode, 1,
                         f"apply_phase reject should exit 1, got rc={result.returncode}\n"
                         f"stdout={result.stdout!r}\nstderr={result.stderr!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
