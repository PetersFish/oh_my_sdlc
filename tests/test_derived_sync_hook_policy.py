#!/usr/bin/env python3
"""Behavioral tests for scripts/derived_sync_hook_policy.py.

Covers the phase-aware policy model that separates staged canonical scope,
actual generated changes, and stale generated targets during apply_change.

Tests use temporary directories and fake Git/workflow state to exercise:
- apply-phase allowance for attributable stale derived targets;
- apply-phase rejection for manual, mixed, unattributed, unrelated, ambiguous,
  and unsupported-skill-removal cases;
- phase resolution from workflow runtime state;
- checkout-to-run binding (main-checkout and worktree);
- path-aware classification reusing existing sync mappings.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "derived_sync_hook_policy.py",
)


def _import_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("derived_sync_hook_policy", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_file(root: str, relpath: str, content: str = "x\n") -> str:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def make_run_state(
    run_id: str = "2026-07-15-test",
    phase: str = "apply_change",
    status: str = "running",
    flow_type: str = "lightweight-flow",
    execution_mode: str = "main_checkout",
    worktree_path: str = "",
    control_root: str = "",
    change_id: str = "test-change",
) -> dict:
    """Build a minimal valid workflow run state dict."""
    return {
        "version": 1,
        "run_id": run_id,
        "workflow": "sdlc-main",
        "flow_type": flow_type,
        "status": status,
        "current_phase": phase,
        "primary_subject": {"type": "spec_change", "id": change_id},
        "context": {
            "change_id": change_id,
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


def write_run_state(root: str, state: dict) -> str:
    """Write a run state file under root/.ai/workflows/runs/active/<run_id>/run.json."""
    run_id = state["run_id"]
    run_dir = os.path.join(root, ".ai", "workflows", "runs", "active", run_id)
    os.makedirs(run_dir, exist_ok=True)
    run_json = os.path.join(run_dir, "run.json")
    with open(run_json, "w", encoding="utf-8") as f:
        json.dump(state, f)
    # Also write a pointer
    pointer_dir = os.path.join(root, ".ai", "workflows", "runs")
    os.makedirs(pointer_dir, exist_ok=True)
    with open(os.path.join(pointer_dir, "current.json"), "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id}, f)
    return run_json


class TestHookPolicyResult(unittest.TestCase):
    """HookPolicyResult shape and construction."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_result_has_required_fields(self):
        mod = _import_module()
        result = mod.HookPolicyResult(
            allowed=True,
            reason=None,
            phase="apply_change",
            run_id="test-run",
            staged_canonical_paths=["agents/foo.md"],
            actual_dirty_generated_paths=[],
            actual_staged_generated_paths=[],
            detected_stale_generated_paths=[".opencode/agents/foo.md"],
            attributable_stale_generated_paths=[".opencode/agents/foo.md"],
            unattributed_generated_paths=[],
            details={},
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.phase, "apply_change")
        self.assertEqual(result.run_id, "test-run")
        self.assertEqual(result.staged_canonical_paths, ["agents/foo.md"])
        self.assertEqual(result.attributable_stale_generated_paths, [".opencode/agents/foo.md"])
        self.assertEqual(result.unattributed_generated_paths, [])

    def test_result_to_dict_is_serializable(self):
        mod = _import_module()
        result = mod.HookPolicyResult(
            allowed=False,
            reason="manual_generated_artifact_change",
            phase="apply_change",
            run_id="test-run",
            staged_canonical_paths=[],
            actual_dirty_generated_paths=[".opencode/agents/foo.md"],
            actual_staged_generated_paths=[],
            detected_stale_generated_paths=[],
            attributable_stale_generated_paths=[],
            unattributed_generated_paths=[],
            details={"offending": [".opencode/agents/foo.md"]},
        )
        d = result.to_dict()
        # Must be JSON serializable for diagnostics output
        json.dumps(d)
        self.assertFalse(d["allowed"])
        self.assertEqual(d["reason"], "manual_generated_artifact_change")


class TestPhaseResolution(unittest.TestCase):
    """Phase resolution from workflow runtime state."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _resolve(self, mod, root=None):
        root = root or self.tmp
        return mod.resolve_phase(root)

    def test_no_active_workflow_returns_none(self):
        """No active run -> existing non-workflow behavior."""
        mod = _import_module()
        phase, run_id = self._resolve(mod)
        self.assertIsNone(phase)
        self.assertIsNone(run_id)

    def test_active_apply_change_run_resolves(self):
        """Active run in apply_change phase is resolved from runtime state."""
        mod = _import_module()
        state = make_run_state(phase="apply_change")
        write_run_state(self.tmp, state)
        phase, run_id = self._resolve(mod)
        self.assertEqual(phase, "apply_change")
        self.assertEqual(run_id, "2026-07-15-test")

    def test_active_finish_phase_resolves(self):
        """Active run in a non-apply phase resolves to that phase."""
        mod = _import_module()
        state = make_run_state(phase="post_archive_actions")
        write_run_state(self.tmp, state)
        phase, run_id = self._resolve(mod)
        self.assertEqual(phase, "post_archive_actions")
        self.assertEqual(run_id, "2026-07-15-test")

    def test_unreadable_phase_fails(self):
        """Active run with unreadable phase -> explicit context failure."""
        mod = _import_module()
        state = make_run_state(phase="")
        write_run_state(self.tmp, state)
        with self.assertRaises(Exception) as ctx:
            self._resolve(mod)
        # The failure should mention phase or context
        self.assertIn("phase", str(ctx.exception).lower() or "context")


class TestCheckoutToRunBinding(unittest.TestCase):
    """Checkout-to-run binding for main-checkout and worktree runs."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_main_checkout_run_binds_by_control_root(self):
        """Main-checkout run binds when control_root matches the current root."""
        mod = _import_module()
        state = make_run_state(
            execution_mode="main_checkout",
            control_root=self.tmp,
        )
        write_run_state(self.tmp, state)
        phase, run_id = mod.resolve_phase(self.tmp)
        self.assertEqual(phase, "apply_change")
        self.assertEqual(run_id, "2026-07-15-test")

    def test_worktree_run_binds_by_worktree_path(self):
        """Worktree-mode run binds through normalized context.worktree_path."""
        mod = _import_module()
        worktree = "/tmp/test-worktree-feature"
        state = make_run_state(
            execution_mode="worktree",
            worktree_path=worktree,
            control_root=self.tmp,
        )
        # State stored under the control root
        write_run_state(self.tmp, state)
        # The policy should bind the worktree checkout to this run
        phase, run_id = mod.resolve_phase(worktree, control_root=self.tmp)
        self.assertEqual(phase, "apply_change")
        self.assertEqual(run_id, "2026-07-15-test")

    def test_unrelated_worktree_run_does_not_bind(self):
        """Active run belonging to another worktree must not affect current checkout."""
        mod = _import_module()
        other_worktree = "/tmp/other-worktree"
        state = make_run_state(
            execution_mode="worktree",
            worktree_path=other_worktree,
            control_root=self.tmp,
        )
        write_run_state(self.tmp, state)
        # A different worktree checkout should not bind to this run
        phase, run_id = mod.resolve_phase("/tmp/my-worktree", control_root=self.tmp)
        self.assertIsNone(phase)
        self.assertIsNone(run_id)

    def test_ambiguous_matching_runs_fail_closed(self):
        """Two matching active runs -> explicit ambiguous-context failure."""
        mod = _import_module()
        state1 = make_run_state(run_id="run-1", control_root=self.tmp)
        state2 = make_run_state(run_id="run-2", control_root=self.tmp)
        write_run_state(self.tmp, state1)
        # Write second run manually
        run_dir2 = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", "run-2")
        os.makedirs(run_dir2, exist_ok=True)
        with open(os.path.join(run_dir2, "run.json"), "w") as f:
            json.dump(state2, f)
        with self.assertRaises(Exception) as ctx:
            mod.resolve_phase(self.tmp)
        self.assertIn("ambig", str(ctx.exception).lower())


class TestPolicyAllowance(unittest.TestCase):
    """Apply-phase allowance: attributable stale targets are allowed."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _eval_policy(self, mod, staged_entries, worktree_entries, stale_paths,
                    phase="apply_change", run_id="test-run", root=None):
        root = root or self.tmp
        return mod.evaluate_policy(
            root=root,
            staged_entries=staged_entries,
            worktree_entries=worktree_entries,
            detected_stale_generated_paths=stale_paths,
            phase=phase,
            run_id=run_id,
        )

    def test_canonical_agent_change_with_attributable_stale_allows(self):
        """Canonical Agent change; derived copies stale but untouched -> allow."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[],
            stale_paths=[".opencode/agents/implement-agent.md",
                          ".claude/agents/implement-agent.md",
                          ".cursor/agents/implement-agent.md"],
        )
        self.assertTrue(result.allowed, f"expected allow, got reason={result.reason}")
        self.assertEqual(result.reason, None)
        self.assertIn("agents/implement-agent.md", result.staged_canonical_paths)
        self.assertEqual(result.actual_staged_generated_paths, [])
        self.assertEqual(result.actual_dirty_generated_paths, [])

    def test_canonical_skill_change_with_attributable_stale_allows(self):
        """Canonical Skill change; derived copies stale but untouched -> allow."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "skills/demo-skill/SKILL.md")],
            worktree_entries=[],
            stale_paths=[".opencode/skills/demo-skill/SKILL.md",
                          ".claude/skills/demo-skill/SKILL.md",
                          ".cursor/skills/demo-skill/SKILL.md"],
        )
        self.assertTrue(result.allowed, f"expected allow, got reason={result.reason}")

    def test_workflow_runtime_module_change_allows(self):
        """Governed workflow_runtime/*.py canonical change -> allow when attributable."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", ".ai/workflows/scripts/workflow_runtime/state.py")],
            worktree_entries=[],
            stale_paths=[
                ".opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py",
                ".claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py",
                ".cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py",
            ],
        )
        self.assertTrue(result.allowed, f"expected allow, got reason={result.reason}")
        self.assertIn(
            ".ai/workflows/scripts/workflow_runtime/state.py",
            result.staged_canonical_paths,
        )

    def test_generated_not_staged_and_not_modified_allows(self):
        """Generated targets not staged and not manually modified -> allow."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[],  # generated files not dirty
            stale_paths=[".opencode/agents/implement-agent.md"],
        )
        self.assertTrue(result.allowed)

    def test_no_canonical_change_no_stale_allows(self):
        """No canonical change and no stale paths -> allow (ordinary commit)."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "README.md")],
            worktree_entries=[],
            stale_paths=[],
        )
        self.assertTrue(result.allowed)


class TestPolicyRejection(unittest.TestCase):
    """Apply-phase rejection: manual, mixed, unattributed, unrelated, ambiguous,
    and unsupported skill removal cases."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _eval_policy(self, mod, staged_entries, worktree_entries, stale_paths,
                    phase="apply_change", run_id="test-run", root=None):
        root = root or self.tmp
        return mod.evaluate_policy(
            root=root,
            staged_entries=staged_entries,
            worktree_entries=worktree_entries,
            detected_stale_generated_paths=stale_paths,
            phase=phase,
            run_id=run_id,
        )

    def test_manual_generated_artifact_change_rejects(self):
        """Generated file manually modified in the worktree -> reject."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[("M", ".opencode/agents/implement-agent.md")],
            stale_paths=[".opencode/agents/implement-agent.md"],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "manual_generated_artifact_change")
        self.assertIn(".opencode/agents/implement-agent.md", result.actual_dirty_generated_paths)

    def test_generated_staged_with_canonical_rejects(self):
        """Generated file staged in the authored commit -> reject (mixed)."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[
                ("M", "agents/implement-agent.md"),
                ("M", ".opencode/agents/implement-agent.md"),
            ],
            worktree_entries=[],
            stale_paths=[".opencode/agents/implement-agent.md"],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "generated_artifact_mixed_with_authored_commit")
        self.assertIn(".opencode/agents/implement-agent.md", result.actual_staged_generated_paths)

    def test_unattributed_generated_drift_rejects(self):
        """Stale generated path not attributable to any staged canonical -> reject."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[],
            stale_paths=[".opencode/agents/review-agent.md"],  # different agent
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "unattributed_generated_drift")
        self.assertIn(".opencode/agents/review-agent.md", result.unattributed_generated_paths)

    def test_same_domain_unrelated_drift_rejects(self):
        """Stage one canonical Skill change while a different generated target in
        the same domain is dirty -> reject (unrelated drift within same domain)."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "skills/skill-a/SKILL.md")],
            worktree_entries=[("M", ".opencode/skills/skill-b/SKILL.md")],
            stale_paths=[".opencode/skills/skill-b/SKILL.md"],
        )
        self.assertFalse(result.allowed)
        # skill-b is dirty and not attributable to skill-a
        self.assertEqual(result.reason, "unrelated_generated_drift")

    def test_unrelated_preexisting_drift_rejects(self):
        """Unrelated pre-existing generated drift -> reject."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[("M", ".claude/agents/review-agent.md")],
            stale_paths=[".claude/agents/review-agent.md"],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "unrelated_generated_drift")

    def test_unsupported_canonical_skill_removal_rejects(self):
        """Canonical Skill directory deletion/rename -> reject as unsupported."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("D", "skills/deleted-skill/SKILL.md")],
            worktree_entries=[],
            stale_paths=[],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "unsupported_canonical_skill_removal")

    def test_missing_workflow_phase_context_rejects(self):
        """Phase-specific policy required but phase is None -> reject."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[],
            stale_paths=[".opencode/agents/implement-agent.md"],
            phase=None,
            run_id=None,
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "missing_workflow_phase_context")


class TestPolicyCompatibility(unittest.TestCase):
    """Compatibility cases: non-apply phase, partial staging, porcelain visibility."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _eval_policy(self, mod, staged_entries, worktree_entries, stale_paths,
                    phase="apply_change", run_id="test-run", root=None):
        root = root or self.tmp
        return mod.evaluate_policy(
            root=root,
            staged_entries=staged_entries,
            worktree_entries=worktree_entries,
            detected_stale_generated_paths=stale_paths,
            phase=phase,
            run_id=run_id,
        )

    def test_non_apply_phase_does_not_allow_stale(self):
        """Active workflow in a non-apply phase -> do not apply the apply allowance."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[],
            stale_paths=[".opencode/agents/implement-agent.md"],
            phase="post_archive_actions",
        )
        # Non-apply phase: stale targets are NOT allowed
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "unattributed_generated_drift")

    def test_partial_staging_uses_staged_scope_only(self):
        """Partial staged canonical edit + additional unstaged canonical edit ->
        policy uses only the staged path/status as authored scope."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            # Additional unstaged canonical edit should NOT broaden allowance
            worktree_entries=[("M", "agents/review-agent.md")],
            stale_paths=[".opencode/agents/implement-agent.md",
                         ".opencode/agents/review-agent.md"],
        )
        # implement-agent.md is attributable; review-agent.md is not staged
        # review-agent is a canonical file that's dirty (unstaged) — not a generated file
        # So stale .opencode/agents/review-agent.md is unattributed to staged scope
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "unattributed_generated_drift")

    def test_generated_untracked_visible_in_porcelain(self):
        """Generated file untracked -> visible through porcelain status parsing."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[("??", ".opencode/agents/new-agent.md")],
            stale_paths=[],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "manual_generated_artifact_change")

    def test_generated_renamed_visible_in_porcelain(self):
        """Generated file renamed -> visible through porcelain status parsing."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[("R", ".opencode/agents/implement-agent.md")],
            stale_paths=[".opencode/agents/implement-agent.md"],
        )
        self.assertFalse(result.allowed)

    def test_generated_deleted_visible_in_porcelain(self):
        """Generated file deleted -> visible through porcelain status parsing."""
        mod = _import_module()
        result = self._eval_policy(
            mod,
            staged_entries=[("M", "agents/implement-agent.md")],
            worktree_entries=[("D", ".opencode/agents/implement-agent.md")],
            stale_paths=[],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "manual_generated_artifact_change")


class TestStagedAndWorktreeEntryCollection(unittest.TestCase):
    """Staged-index and worktree entry collection from Git."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Init a git repo
        subprocess.run(["git", "init"], capture_output=True, cwd=self.tmp)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       capture_output=True, cwd=self.tmp)
        subprocess.run(["git", "config", "user.name", "Test"],
                       capture_output=True, cwd=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_discover_staged_entries_uses_diff_cached(self):
        """discover_staged_entries reads from git diff --cached --name-status -z."""
        mod = _import_module()
        # Create and stage a file
        write_file(self.tmp, "agents/foo.md", "content\n")
        subprocess.run(["git", "add", "agents/foo.md"], capture_output=True, cwd=self.tmp)

        entries = mod.discover_staged_entries(self.tmp)
        self.assertTrue(any(path == "agents/foo.md" for status, path in entries))

    def test_discover_worktree_entries_uses_porcelain(self):
        """discover_worktree_entries reads from git status --porcelain=v1 -z."""
        mod = _import_module()
        # Create an untracked file
        write_file(self.tmp, "agents/bar.md", "content\n")

        entries = mod.discover_worktree_entries(self.tmp)
        statuses = {path: status for status, path in entries}
        self.assertIn("agents/bar.md", statuses)

    def test_staged_and_unstaged_are_separate(self):
        """A partially staged file appears in both staged and worktree entries."""
        mod = _import_module()
        write_file(self.tmp, "agents/baz.md", "initial\n")
        subprocess.run(["git", "add", "agents/baz.md"], capture_output=True, cwd=self.tmp)
        subprocess.run(
            ["git", "commit", "-m", "init", "--no-verify"],
            capture_output=True, cwd=self.tmp,
        )
        # Modify and stage
        with open(os.path.join(self.tmp, "agents/baz.md"), "w") as f:
            f.write("staged\n")
        subprocess.run(["git", "add", "agents/baz.md"], capture_output=True, cwd=self.tmp)
        # Further unstaged modification
        with open(os.path.join(self.tmp, "agents/baz.md"), "w") as f:
            f.write("unstaged\n")

        staged = mod.discover_staged_entries(self.tmp)
        worktree = mod.discover_worktree_entries(self.tmp)
        self.assertTrue(any(path == "agents/baz.md" for _, path in staged))
        self.assertTrue(any(path == "agents/baz.md" for _, path in worktree))


if __name__ == "__main__":
    unittest.main(verbosity=2)