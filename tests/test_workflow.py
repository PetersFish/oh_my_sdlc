#!/usr/bin/env python3
"""Tests for SDLC workflow runtime using temporary workspace fixtures.

Tests are isolated to temporary directories and never mutate real
.ai/roadmap, .ai/workflows, or openspec data.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


WORKFLOW_PY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", ".ai", "workflows", "scripts", "workflow.py",
)


def run_workflow(root, cmd, **kwargs):
    """Run workflow.py with --root and return (returncode, stdout, stderr)."""
    args = [sys.executable, WORKFLOW_PY, "--root", root, cmd]
    for key, val in kwargs.items():
        arg_name = "--" + key.replace("_", "-")
        if val is True:
            args.append(arg_name)
        elif val is not None and val is not False:
            args.append(arg_name)
            args.append(str(val))
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def load_json(root, relpath):
    path = os.path.join(root, relpath)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def load_yaml(root, relpath):
    path = os.path.join(root, relpath)
    with open(path) as f:
        return yaml.safe_load(f)


class FixtureBase(unittest.TestCase):
    """Base class that creates a temporary workspace with proper structure."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._setup_workflow_dirs()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _setup_workflow_dirs(self):
        src_def = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", ".ai", "workflows", "definitions",
        )
        dst_def = os.path.join(self.tmp, ".ai", "workflows", "definitions")
        if os.path.isdir(src_def):
            shutil.copytree(src_def, dst_def)

    def _make_openspec_change(self, change_id, status_yaml="schema: spec-driven\ncreated: 2026-06-18\n"):
        d = os.path.join(self.tmp, "openspec", "changes", change_id)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, ".openspec.yaml"), "w") as f:
            f.write(status_yaml)

    def _make_openspec_archive(self, change_id, date="2026-06-18"):
        d = os.path.join(
            self.tmp, "openspec", "changes", "archive", f"{date}-{change_id}"
        )
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, ".openspec.yaml"), "w") as f:
            f.write("schema: spec-driven\nstatus: archived\n")

    def _make_task_file(self, change_id, completed=True):
        tasks_dir = os.path.join(self.tmp, "openspec", "changes", change_id)
        os.makedirs(tasks_dir, exist_ok=True)
        prefix = "- [x]" if completed else "- [ ]"
        content = f"{prefix} Task 1: Do something\n{prefix} Task 2: Do something else\n"
        with open(os.path.join(tasks_dir, "tasks.md"), "w") as f:
            f.write(content)

    def _make_superpowers_plan(self, filename, content="# Plan\n"):
        plans_dir = os.path.join(self.tmp, "docs", "superpowers", "plans")
        os.makedirs(plans_dir, exist_ok=True)
        path = os.path.join(plans_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _make_roadmap_item(self, item_id, status, openspec_change=None, spec_change=None, area="area1", completed_at=None, started_at=None, slug=None):
        items_dir = os.path.join(
            self.tmp, ".ai", "roadmap", "areas", area, "items"
        )
        os.makedirs(items_dir, exist_ok=True)
        fm = f"id: {item_id}\nstatus: {status}\n"
        if spec_change:
            fm += f"spec_change: {spec_change}\n"
        if openspec_change:
            fm += f"openspec_change: {openspec_change}\n"
        if completed_at:
            fm += f"completed_at: {completed_at}\n"
        if started_at:
            fm += f"started_at: {started_at}\n"
        content = f"---\n{fm}---\n# {item_id}\n"
        fname = f"{item_id}-{slug}.md" if slug else f"{item_id}.md"
        fpath = os.path.join(items_dir, fname)
        with open(fpath, "w") as f:
            f.write(content)

    def _read_current_state(self):
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        if not pointer or not pointer.get("run_id"):
            return None
        return load_json(self.tmp, f".ai/workflows/runs/active/{pointer['run_id']}/run.json")

    def _write_current_state(self, state):
        run_id = state["run_id"]
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id)
        os.makedirs(active_dir, exist_ok=True)
        with open(os.path.join(active_dir, "run.json"), "w") as f:
            json.dump(state, f)
        pointer_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "current.json")
        with open(pointer_path, "w") as f:
            json.dump({"run_id": run_id}, f)

    def _read_active_file(self, run_id):
        return load_json(self.tmp, f".ai/workflows/runs/active/{run_id}/run.json")

    def _read_history(self, run_id):
        return load_json(self.tmp, f".ai/workflows/runs/history/{run_id}/run.json")

    def _make_active_roadmap_run(self, item_id, change_id, current_phase="apply_change"):
        runs_dir = os.path.join(self.tmp, ".ai", "workflows", "runs")
        active_dir = os.path.join(runs_dir, "active")
        run_id = f"2026-06-20-{item_id}"
        os.makedirs(os.path.join(active_dir, run_id), exist_ok=True)
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": current_phase,
            "primary_subject": {"type": "roadmap_item", "id": item_id},
            "context": {"change_id": change_id, "roadmap_item_id": item_id},
            "phase_readiness": {"phase": current_phase, "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": ["roadmap_status_ready_if_linked"],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {"roadmap_item_path": f".ai/roadmap/areas/area1/items/{item_id}.md"},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
        }
        with open(os.path.join(active_dir, run_id, "run.json"), "w") as f:
            json.dump(state, f)
        return run_id


class TestStartAndStatus(FixtureBase):
    def test_status_no_run(self):
        rc, out, _ = run_workflow(self.tmp, "status")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "no_active_run")

    def test_start_requires_subject_type(self):
        rc, _, stderr = run_workflow(
            self.tmp, "start",
            subject_id="demo-change",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("subject-type", stderr.lower())

    def test_start_rejects_legacy_subject_type(self):
        rc, _, stderr = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="demo-change",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("invalid choice", stderr.lower())

    def test_start_creates_run(self):
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="demo-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "running")
        self.assertIn("demo-change", data["run_id"])
        self.assertEqual(
            data["primary_subject"],
            {"type": "spec_change", "id": "demo-change"},
        )

    def test_start_existing_run_same_subject_reports_conflict(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="demo-change",
        )
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="demo-change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["action"], "conflict")

    def test_start_existing_run_different_subject_allows_concurrent(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="demo-change-1",
        )
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="demo-change-2",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "running")
        self.assertIn("demo-change-2", data["run_id"])


class TestPhaseInference(FixtureBase):
    def test_missing_change_starts_at_create_change(self):
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="no-such-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "create_change")

    def test_scaffold_change_starts_at_create_change(self):
        """Change dir with .openspec.yaml but no tasks.md starts at create_change."""
        self._make_openspec_change("my-change")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="my-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "create_change")

    def test_empty_change_dir_starts_at_create_change(self):
        """Change dir with no files at all starts at create_change."""
        empty_dir = os.path.join(self.tmp, "openspec", "changes", "empty-change")
        os.makedirs(empty_dir, exist_ok=True)
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="empty-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "create_change")

    def test_in_progress_change_starts_at_apply_change(self):
        """Change with incomplete tasks starts at apply_change."""
        self._make_openspec_change("wip-change")
        self._make_task_file("wip-change", completed=False)
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="wip-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "apply_change")

    def test_archived_change_starts_at_post_archive_actions(self):
        self._make_openspec_archive("arch-change")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="arch-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "post_archive_actions")

    def test_complete_tasks_change_starts_at_archive_change(self):
        self._make_openspec_change("done-change")
        self._make_task_file("done-change", completed=True)
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="done-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "archive_change")

    def test_lightweight_flow_with_matching_superpowers_plan_starts_at_apply_change(self):
        self._make_superpowers_plan("2026-07-02-start-with-plan-handoff.md")

        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="spec_change",
            subject_id="start-with-plan-handoff",
            flow_type="lightweight-flow",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["flow_type"], "lightweight-flow")
        self.assertEqual(data["current_phase"], "apply_change")

    def test_lightweight_flow_without_matching_superpowers_plan_starts_at_create_change(self):
        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="spec_change",
            subject_id="missing-plan",
            flow_type="lightweight-flow",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["flow_type"], "lightweight-flow")
        self.assertEqual(data["current_phase"], "create_change")

    def test_lightweight_flow_with_multiple_matching_superpowers_plans_does_not_guess(self):
        self._make_superpowers_plan("2026-07-02-start-with-plan-handoff.md")
        self._make_superpowers_plan("2026-07-03-start-with-plan-handoff-revision.md")

        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="spec_change",
            subject_id="start-with-plan-handoff",
            flow_type="lightweight-flow",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["flow_type"], "lightweight-flow")
        self.assertEqual(data["current_phase"], "create_change")


class TestValidate(FixtureBase):
    def test_validate_no_state_no_definition(self):
        # Remove the definition dir so validate fails cleanly
        src = os.path.join(self.tmp, ".ai", "workflows", "definitions")
        if os.path.isdir(src):
            shutil.rmtree(src)
        rc, _, stderr = run_workflow(self.tmp, "validate")
        self.assertNotEqual(rc, 0)

    def test_validate_with_definition(self):
        rc, out, _ = run_workflow(self.tmp, "validate")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["valid"])


class TestReadinessAndResolve(FixtureBase):
    def test_missing_required_input_blocks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="test-change",
            workflow="sdlc-main",
        )
        # Manually set phase to create_change which requires context.change_id
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        state["context"] = {}
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "readiness")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertFalse(data["phase_readiness"]["ready"])
        self.assertIn("context.change_id", data["phase_readiness"]["missing_required_inputs"])
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "missing_required_inputs")

    def test_resolve_fills_context(self):
        self._make_openspec_change("resolved-change")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="resolved-change",
            workflow="sdlc-main",
        )
        rc, out, _ = run_workflow(self.tmp, "resolve")
        self.assertEqual(rc, 0)
        data = json.loads(out)


class TestBlockAndUnblock(FixtureBase):
    def test_block_sets_blocked_state(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="block-test",
        )
        rc, out, _ = run_workflow(
            self.tmp, "block",
            block_type="user_decision_required",
            message="need user choice",
            next_allowed="choose_a,choose_b",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "user_decision_required")
        self.assertEqual(data["block"]["message"], "need user choice")
        self.assertEqual(data["block"]["next_allowed"], ["choose_a", "choose_b"])


class TestRecordEvidence(FixtureBase):
    def test_record_evidence_does_not_complete_phase(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="ev-test",
        )
        rc, out, _ = run_workflow(
            self.tmp, "record-evidence",
            key="test_key",
            value='"test_value"',
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["evidence"]["test_key"], "test_value")
        self.assertEqual(data["completed_phases"], [])
        self.assertEqual(data["completed_hooks"], [])


class TestAdvanceGuarded(FixtureBase):
    def test_advance_blocked_when_phase_not_complete(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="adv-test",
        )
        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertNotEqual(rc, 0)
        self.assertIn("not complete", out)

    def test_advance_blocked_when_run_blocked(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="adv-blocked",
        )
        run_workflow(self.tmp, "block", block_type="user_decision_required", message="x")
        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertNotEqual(rc, 0)
        self.assertIn("blocked", out.lower())

    def test_advance_to_done_does_not_recreate_active_run(self):
        run_id = "2026-06-20-advance-done"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "post_archive_actions",
            "primary_subject": {"type": "spec_change", "id": "advance-done"},
            "context": {"change_id": "advance-done"},
            "phase_readiness": {
                "phase": "post_archive_actions",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": ["memory_sync", "roadmap_done_if_relevant"],
            "completed_phases": [
                "create_change",
                "apply_change",
                "archive_change",
                "post_archive_actions",
            ],
            "gates": {},
            "evidence": {
                "archive_path": "openspec/changes/archive/2026-06-22-advance-done",
                "agent_phase": {"slice_id": "default"},
                "agent_results": {
                    "default": {
                        "finish-agent": {
                            "agent": "finish-agent",
                            "status": "success",
                            "phase": "post_archive_actions",
                            "slice_id": "default",
                            "flow_type": "spec-flow",
                            "evidence": {},
                            "artifacts": {},
                            "blockers": [],
                        }
                    }
                },
            },
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "advance")

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["current_phase"], "done")
        self.assertIsNone(self._read_active_file(run_id))
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertFalse(pointer.get("run_id"))
        history = self._read_history(run_id)
        self.assertIsNotNone(history)
        self.assertEqual(history["status"], "done")
        self.assertEqual(history["current_phase"], "done")


class TestSubagentOwnedLifecycleCleanup(FixtureBase):
    def _write_archive_ready_state(self, change_id="subagent-cleanup"):
        state = {
            "version": 1,
            "run_id": f"2026-07-05-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {"change_id": change_id},
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-05T00:00:00",
        }
        self._write_current_state(state)
        return state

    def test_archive_change_completion_does_not_enqueue_normal_cleanup_hooks(self):
        self._write_archive_ready_state("no-hooks")
        rc, out, _ = run_workflow(
            self.tmp,
            "record-evidence",
            key="archive_path_exists",
            value="true",
        )
        self.assertEqual(rc, 0)

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("archive_change", data.get("completed_phases", []))
        self.assertEqual(data.get("pending_hooks"), [])
        self.assertNotIn("memory_sync", data.get("pending_hooks", []))
        self.assertNotIn("roadmap_done_if_relevant", data.get("pending_hooks", []))

    def test_archive_change_advances_to_post_archive_actions_without_hooks(self):
        self._write_archive_ready_state("advance-cleanup")
        run_workflow(
            self.tmp,
            "record-evidence",
            key="archive_path_exists",
            value="true",
        )
        run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )

        rc, out, _ = run_workflow(self.tmp, "advance")

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "post_archive_actions")
        self.assertEqual(data.get("pending_hooks"), [])
        self.assertTrue(data["phase_readiness"]["ready"])

    def test_post_archive_actions_requires_cleanup_evidence(self):
        self._write_archive_ready_state("cleanup-required")
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["completed_phases"] = ["apply_change", "archive_change"]
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="cleanup_complete",
        )

        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("memory_sync_done", data["error"])
        self.assertIn("cleanup_complete", data["error"])

    def test_post_archive_actions_accepts_finish_agent_cleanup_evidence(self):
        self._write_archive_ready_state("cleanup-success")
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["completed_phases"] = ["apply_change", "archive_change"]
        self._write_current_state(state)
        finish_result = {
            "agent": "finish-agent",
            "status": "success",
            "phase": "post_archive_actions",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "memory_sync_done": True,
                "roadmap_done_checked": True,
                "derived_artifacts_synced": True,
                "post_hook_dirty_tree": False,
                "cleanup_complete": True,
                "criteria_satisfied": "cleanup_complete",
            },
            "artifacts": {},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(
            self.tmp,
            "after-dispatch",
            agent="finish-agent",
            phase="post_archive_actions",
            value=json.dumps(finish_result),
        )
        self.assertEqual(rc, 0)
        transition = json.loads(out)
        self.assertEqual(transition["workflow_command"], "workflow.py complete-phase")

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="cleanup_complete",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("post_archive_actions", data.get("completed_phases", []))
        self.assertTrue(data["evidence"]["memory_sync_done"])
        self.assertTrue(data["evidence"]["roadmap_done_checked"])
        self.assertTrue(data["evidence"]["derived_artifacts_synced"])
        self.assertFalse(data["evidence"]["post_hook_dirty_tree"])
        self.assertTrue(data["evidence"]["cleanup_complete"])

    def test_archive_change_finish_agent_cannot_claim_cleanup_complete(self):
        self._write_archive_ready_state("premature-cleanup")
        finish_result = {
            "agent": "finish-agent",
            "status": "success",
            "phase": "archive_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "archive_path_exists": True,
                "pending_hooks_empty": True,
                "cleanup_complete": True,
            },
            "artifacts": {},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(
            self.tmp,
            "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            value=json.dumps(finish_result),
        )

        self.assertEqual(rc, 0)
        transition = json.loads(out)
        self.assertEqual(transition["status"], "success")
        self.assertEqual(transition["workflow_command"], "workflow.py block")
        self.assertEqual(transition["blockers"][0]["reason"], "premature_cleanup_evidence")
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "worker_failed")

    def test_existing_pending_hooks_still_block_until_legacy_complete_hook_repairs_them(self):
        self._write_archive_ready_state("legacy-repair")
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["completed_phases"] = ["apply_change", "archive_change", "post_archive_actions"]
        state["pending_hooks"] = ["memory_sync"]
        state["evidence"] = {
            "memory_sync_done": True,
            "roadmap_done_checked": True,
            "derived_artifacts_synced": True,
            "post_hook_dirty_tree": False,
            "cleanup_complete": True,
            "agent_phase": {"slice_id": "default"},
            "agent_results": {
                "default": {
                    "finish-agent": {
                        "agent": "finish-agent",
                        "status": "success",
                        "phase": "post_archive_actions",
                        "slice_id": "default",
                        "flow_type": "lightweight-flow",
                        "evidence": {},
                        "artifacts": {},
                        "blockers": [],
                    }
                }
            },
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["block"]["type"], "hook_blocked")

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-hook",
            hook="memory_sync",
            resolution="synced",
        )
        self.assertEqual(rc, 0)
        repaired = json.loads(out)
        self.assertNotIn("memory_sync", repaired.get("pending_hooks", []))

        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")

    def test_post_archive_actions_rejects_false_positive_cleanup_evidence(self):
        """post_archive_actions: finish-agent returns cleanup_complete=True but
        one of the required positive cleanup evidence keys is False.  The phase
        must not pass because positive cleanup evidence must be true; only
        post_hook_dirty_tree may be False (clean tree)."""
        self._write_archive_ready_state("false-positive-cleanup")
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["completed_phases"] = ["apply_change", "archive_change"]
        self._write_current_state(state)
        finish_result = {
            "agent": "finish-agent",
            "status": "success",
            "phase": "post_archive_actions",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "memory_sync_done": False,
                "roadmap_done_checked": True,
                "derived_artifacts_synced": True,
                "post_hook_dirty_tree": False,
                "cleanup_complete": True,
                "criteria_satisfied": "cleanup_complete",
            },
            "artifacts": {},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(
            self.tmp,
            "after-dispatch",
            agent="finish-agent",
            phase="post_archive_actions",
            value=json.dumps(finish_result),
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        blocker_reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn(
            "invalid_phase_evidence_values",
            blocker_reasons,
            f"False positive cleanup evidence must block; got {blocker_reasons}",
        )
        self.assertEqual(data["workflow_command"], "workflow.py block")


class TestBranchPhase(FixtureBase):
    def test_branch_with_unknown_decision_blocks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="branch-test",
        )
        state = self._read_current_state()
        state["current_phase"] = "decide_intent"
        state["completed_phases"] = ["decide_intent"]
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "advance", branch="bogus")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "user_decision_required")


class TestPostArchiveHooks(FixtureBase):
    def _start_archived_workflow(self, change_id, roadmap_items=None):
        self._make_openspec_archive(change_id)
        if roadmap_items:
            for item in roadmap_items:
                self._make_roadmap_item(**item)
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id=change_id,
        )
        return json.loads(out)

    def _add_hook(self, hook_name):
        state = self._read_current_state()
        state.setdefault("pending_hooks", []).append(hook_name)
        self._write_current_state(state)

    def test_roadmap_done_hook_with_slug_filename(self):
        """roadmap_done_if_relevant hook resolves 'done' when item file has slug suffix."""
        self._start_archived_workflow("slug-test", [
            {"item_id": "RM-SLUG-001", "status": "active", "openspec_change": "slug-test"},
        ])
        items_dir = os.path.join(
            self.tmp, ".ai", "roadmap", "areas", "area1", "items"
        )
        os.remove(os.path.join(items_dir, "RM-SLUG-001.md"))
        self._make_roadmap_item(
            "RM-SLUG-001", "done", slug="my-feature-slug",
            openspec_change="slug-test", completed_at="2026-06-22",
        )
        self._add_hook("roadmap_done_if_relevant")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["evidence"]["roadmap_hook_resolution"], "done")

    def test_roadmap_done_hook_finalizes_linked_roadmap_run(self):
        """If the linked roadmap item is already done, the hook should retire its active run."""
        self._start_archived_workflow("finalize-change", [
            {"item_id": "RM-FINAL-001", "status": "done", "openspec_change": "finalize-change", "completed_at": "2026-06-22"},
        ])
        roadmap_run_id = self._make_active_roadmap_run("RM-FINAL-001", "finalize-change", current_phase="apply_change")
        self._add_hook("roadmap_done_if_relevant")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["evidence"]["roadmap_hook_resolution"], "done")
        self.assertEqual(data["evidence"]["roadmap_item_run_finalized"], roadmap_run_id)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, ".ai", "workflows", "runs", "active", roadmap_run_id)))
        self.assertIsNotNone(self._read_history(roadmap_run_id))

    def test_roadmap_done_hook_does_not_recreate_current_run_after_finalizing_itself(self):
        """Completing the roadmap-done hook on the current roadmap run must not resurrect it in active/."""
        self._make_roadmap_item(
            "RM-SELF-001",
            "done",
            openspec_change="self-finalize-change",
            completed_at="2026-06-22",
        )
        run_id = "2026-06-20-RM-SELF-001"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "roadmap_item", "id": "RM-SELF-001"},
            "context": {
                "change_id": "self-finalize-change",
                "roadmap_item_id": "RM-SELF-001",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": ["roadmap_done_if_relevant"],
            "completed_hooks": [
                "roadmap_status_ready_if_linked",
                "roadmap_apply_start_if_ready",
                "memory_sync",
            ],
            "completed_phases": ["create_change", "apply_change", "archive_change"],
            "gates": {},
            "evidence": {
                "openspec_change_id": "self-finalize-change",
                "archive_path": "openspec/changes/archive/2026-06-22-self-finalize-change",
                "roadmap_link": {
                    "count": 1,
                    "items": [
                        {
                            "item_id": "RM-SELF-001",
                            "status": "done",
                            "completed_at": "2026-06-22",
                            "file": ".ai/roadmap/areas/area1/items/RM-SELF-001.md",
                            "area": "area1",
                        }
                    ],
                },
                "roadmap_item_status": {
                    "item_id": "RM-SELF-001",
                    "status": "done",
                    "completed_at": "2026-06-22",
                },
            },
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )

        self.assertEqual(rc, 0)
        self.assertIsNone(self._read_active_file(run_id))
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertFalse(pointer.get("run_id"))
        history = self._read_history(run_id)
        self.assertIsNotNone(history)
        self.assertEqual(history["status"], "done")
        self.assertEqual(history["current_phase"], "done")

    def test_roadmap_done_hook_does_not_recreate_current_run_when_latest_status_turns_done(self):
        """Refreshing roadmap status from active->done must not resurrect the current roadmap run."""
        self._make_roadmap_item(
            "RM-SELF-002",
            "done",
            openspec_change="self-latest-done-change",
            completed_at="2026-06-22",
        )
        run_id = "2026-06-20-RM-SELF-002"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "roadmap_item", "id": "RM-SELF-002"},
            "context": {
                "change_id": "self-latest-done-change",
                "roadmap_item_id": "RM-SELF-002",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": ["roadmap_done_if_relevant"],
            "completed_hooks": [
                "roadmap_status_ready_if_linked",
                "roadmap_apply_start_if_ready",
                "memory_sync",
            ],
            "completed_phases": ["create_change", "apply_change", "archive_change"],
            "gates": {},
            "evidence": {
                "openspec_change_id": "self-latest-done-change",
                "archive_path": "openspec/changes/archive/2026-06-22-self-latest-done-change",
                "roadmap_link": {
                    "count": 1,
                    "items": [
                        {
                            "item_id": "RM-SELF-002",
                            "status": "active",
                            "file": ".ai/roadmap/areas/area1/items/RM-SELF-002.md",
                            "area": "area1",
                        }
                    ],
                },
                "roadmap_item_status": {
                    "item_id": "RM-SELF-002",
                    "status": "active",
                },
            },
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )

        self.assertEqual(rc, 0)
        self.assertIsNone(self._read_active_file(run_id))
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertFalse(pointer.get("run_id"))
        history = self._read_history(run_id)
        self.assertIsNotNone(history)
        self.assertEqual(history["status"], "done")
        self.assertEqual(history["current_phase"], "done")

    def test_archived_active_roadmap_blocks_done(self):
        self._start_archived_workflow("arch-block", [
            {"item_id": "RM-001", "status": "active", "openspec_change": "arch-block"},
        ])
        state = self._read_current_state()
        state["current_phase"] = "done"
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        state["pending_hooks"] = ["roadmap_done_if_relevant"]
        state["status"] = "running"
        state["block"] = None
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "done")
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "hook_blocked")

    def test_archived_done_roadmap_allows_done(self):
        self._start_archived_workflow("arch-done", [
            {"item_id": "RM-002", "status": "done", "openspec_change": "arch-done",
             "completed_at": "2026-06-15"},
        ])
        self._add_hook("roadmap_done_if_relevant")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["evidence"]["roadmap_hook_resolution"], "idempotent_done")

        self._add_hook("memory_sync")
        rc, out2, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="memory_sync",
            resolution="synced",
        )
        self.assertEqual(rc, 0)

        state = self._read_current_state()
        state["current_phase"] = "done"
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        state["status"] = "running"
        state["block"] = None
        state.setdefault("evidence", {}).setdefault("agent_results", {})["default"] = {
            "finish-agent": {
                "agent": "finish-agent",
                "status": "success",
                "phase": "post_archive_actions",
                "slice_id": "default",
                "flow_type": "spec-flow",
                "evidence": {},
                "artifacts": {},
                "blockers": [],
            }
        }
        state.setdefault("evidence", {}).setdefault("agent_phase", {})["slice_id"] = "default"
        self._write_current_state(state)

        rc, out3, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        data = json.loads(out3)
        self.assertEqual(data["status"], "done")

    def test_archived_no_roadmap_link_completes_hook(self):
        self._start_archived_workflow("arch-no-link")
        self._add_hook("roadmap_done_if_relevant")
        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["evidence"]["roadmap_hook_resolution"], "no_linked_item")

    def test_archived_multiple_roadmap_links_blocks(self):
        self._start_archived_workflow("arch-multi", [
            {"item_id": "RM-010", "status": "active", "openspec_change": "arch-multi"},
            {"item_id": "RM-011", "status": "active", "openspec_change": "arch-multi"},
        ])
        self._add_hook("roadmap_done_if_relevant")
        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "user_decision_required")

    def test_archived_non_active_roadmap_blocks(self):
        for status in ("idea", "ready", "cancelled"):
            with self.subTest(status=status):
                tmp = tempfile.mkdtemp()
                try:
                    src_def = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "..", ".ai", "workflows", "definitions",
                    )
                    dst_def = os.path.join(tmp, ".ai", "workflows", "definitions")
                    if os.path.isdir(src_def):
                        shutil.copytree(src_def, dst_def)

                    os.makedirs(os.path.join(
                        tmp, "openspec", "changes", "archive",
                        f"2026-06-18-arch-{status}"
                    ), exist_ok=True)
                    rdir = os.path.join(
                        tmp, ".ai", "roadmap", "areas", "a1", "items"
                    )
                    os.makedirs(rdir, exist_ok=True)
                    fm = f"id: RM-{status}\nstatus: {status}\nopenspec_change: arch-{status}\n"
                    with open(os.path.join(rdir, f"RM-{status}.md"), "w") as f:
                        f.write(f"---\n{fm}---\n# Test\n")

                    run_workflow(
                        tmp, "start",
                        subject_type="spec_change",
                        subject_id=f"arch-{status}",
                    )
                    # Register hook manually
                    pointer_path = os.path.join(tmp, ".ai/workflows/runs/current.json")
                    with open(pointer_path, "r") as f:
                        pointer = json.load(f)
                    active_path = os.path.join(tmp, ".ai/workflows/runs/active", pointer["run_id"], "run.json")
                    with open(active_path, "r") as f:
                        s = json.load(f)
                    s.setdefault("pending_hooks", []).append("roadmap_done_if_relevant")
                    with open(active_path, "w") as f:
                        json.dump(s, f)

                    rc, out, _ = run_workflow(
                        tmp, "complete-hook",
                        hook="roadmap_done_if_relevant",
                    )
                    self.assertNotEqual(rc, 0)
                    data = json.loads(out)
                    self.assertEqual(data["block"]["type"], "domain_state_mismatch")
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)


class TestMemorySyncHook(FixtureBase):
    def _setup_archived_with_memory_hook(self, change_id="mem-test"):
        self._make_openspec_archive(change_id)
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id=change_id,
        )
        state = self._read_current_state()
        state["pending_hooks"] = ["memory_sync"]
        self._write_current_state(state)

    def test_memory_sync_deferred_without_reason_fails(self):
        self._setup_archived_with_memory_hook("mem-no-reason")
        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="memory_sync",
            resolution="user_deferred",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("reason", out.lower())

    def test_memory_sync_not_needed_without_reason_fails(self):
        self._setup_archived_with_memory_hook("mem-no-reason2")
        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="memory_sync",
            resolution="not_needed",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("reason", out.lower())

    def test_memory_sync_synced_succeeds(self):
        self._setup_archived_with_memory_hook("mem-synced")
        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="memory_sync",
            resolution="synced",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn("memory_sync", data.get("pending_hooks", []))

    def test_memory_sync_deferred_with_reason_succeeds(self):
        self._setup_archived_with_memory_hook("mem-deferred")
        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="memory_sync",
            resolution="user_deferred",
            reason="Will sync later",
            residual_risk="Missing memory docs for 1 week",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn("memory_sync", data.get("pending_hooks", []))


class TestResume(FixtureBase):
    def test_same_subject_resume_reuses_run(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="resume-test",
        )
        rc, out, _ = run_workflow(
            self.tmp, "resume",
            subject_type="spec_change",
            subject_id="resume-test",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("resume-test", data["run_id"])

    def test_resume_different_subject_not_found(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="resume-1",
        )
        rc, out, _ = run_workflow(
            self.tmp, "resume",
            subject_type="spec_change",
            subject_id="resume-2",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("no active run found", data["error"])

    def test_resume_spec_change_uses_context_change_id_for_phase_inference(self):
        canonical_change_id = "canonical-change"
        self._make_openspec_change(canonical_change_id)
        self._make_task_file(canonical_change_id, completed=False)
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="original-subject",
        )
        state = self._read_current_state()
        state["context"]["change_id"] = canonical_change_id
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "resume",
            subject_type="spec_change",
            subject_id="original-subject",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "apply_change")
        self.assertEqual(
            data["evidence"]["spec_status"]["classification"],
            "in-progress",
        )

    def test_resume_without_subject_args_lists_runs(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="resume-nosub",
        )
        rc, out, _ = run_workflow(self.tmp, "resume")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("active_runs", data)
        self.assertEqual(len(data["active_runs"]), 1)


class TestDone(FixtureBase):
    def _prepare_done_state(self):
        self._make_openspec_archive("done-test")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="done-test",
        )
        run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )
        run_workflow(
            self.tmp, "complete-hook",
            hook="memory_sync",
            resolution="synced",
        )
        state = self._read_current_state()
        state["current_phase"] = "done"
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        state["status"] = "running"
        # Record finish-agent evidence so terminal validation passes.
        state.setdefault("evidence", {}).setdefault("agent_results", {})["default"] = {
            "finish-agent": {
                "agent": "finish-agent",
                "status": "success",
                "phase": "post_archive_actions",
                "slice_id": "default",
                "flow_type": "spec-flow",
                "evidence": {},
                "artifacts": {},
                "blockers": [],
            }
        }
        # Mirror before-dispatch: record the dispatch intent slice_id so
        # terminal validation resolves the relevant slice as "default".
        state.setdefault("evidence", {}).setdefault("agent_phase", {})["slice_id"] = "default"
        self._write_current_state(state)

    def test_done_clears_active_and_pointer(self):
        self._prepare_done_state()
        state = self._read_current_state()
        run_id = state["run_id"]
        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")
        # Active directory should be removed
        active_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id)
        self.assertFalse(os.path.exists(active_path))
        # Pointer should be cleared
        pointer = self._read_current_state()
        self.assertIsNone(pointer)

    def test_done_writes_history(self):
        self._prepare_done_state()
        state = self._read_current_state()
        run_id = state["run_id"]
        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        history = self._read_history(run_id)
        self.assertIsNotNone(history)
        self.assertEqual(history["status"], "done")

    def test_done_blocks_with_pending_hooks(self):
        self._make_openspec_archive("done-pending")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="done-pending",
        )
        state = self._read_current_state()
        state["current_phase"] = "done"
        state["pending_hooks"] = ["memory_sync"]
        state["status"] = "running"
        self._write_current_state(state)
        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")


class TestRootArgument(FixtureBase):
    def test_all_commands_accept_root(self):
        commands = [
            ("status", {}),
            ("validate", {}),
            ("start", {"subject_type": "spec_change", "subject_id": "rt-test"}),
            ("resume", {}),
            ("readiness", {}),
            ("resolve", {}),
            ("record-evidence", {"key": "x", "value": "\"y\""}),
            ("block", {"block_type": "user_decision_required"}),
        ]
        for cmd, extra in commands:
            with self.subTest(command=cmd):
                if "subject_id" in extra and extra["subject_id"] not in ("rt-test",):
                    extra["subject_id"] = "rt-test"
                # For commands that need a running state
                if cmd in ("status", "validate"):
                    pass  # can run without state
                elif cmd not in ("start",):
                    run_workflow(
                        self.tmp, "start",
                        subject_type="spec_change",
                        subject_id="rt-test",
                    )
                rc, _, _ = run_workflow(self.tmp, cmd, **extra)
                # We just verify it doesn't crash with a traceback
                self.assertIn(rc, (0, 1))


class TestWriteBoundary(FixtureBase):
    def test_workflow_only_writes_under_workflows_runs(self):
        self._make_openspec_archive("boundary-test")
        self._make_roadmap_item("RM-BND-001", "active", openspec_change="boundary-test")

        original_files = set()
        for root_dir, dirs, files in os.walk(self.tmp):
            for f in files:
                original_files.add(os.path.join(root_dir, f))

        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="boundary-test",
        )
        run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )

        new_files = set()
        for root_dir, dirs, files in os.walk(self.tmp):
            for f in files:
                new_files.add(os.path.join(root_dir, f))

        for nf in new_files - original_files:
            rel = os.path.relpath(nf, self.tmp)
            self.assertTrue(
                rel.startswith(".ai/workflows/runs/"),
                f"workflow.py wrote outside .ai/workflows/runs/: {rel}",
            )

        # Verify roadmap file still exists and unchanged
        rm_path = os.path.join(
            self.tmp, ".ai", "roadmap", "areas", "area1", "items", "RM-BND-001.md"
        )
        self.assertTrue(os.path.exists(rm_path))
        with open(rm_path) as f:
            content = f.read()
        self.assertIn("status: active", content)


class TestRoadmapReadyHook(FixtureBase):
    """Tests for roadmap_status_ready_if_linked hook validation (Tasks 1.1, 1.2, 1.5)."""

    def _setup_create_change_run(self, change_id, item_id, item_status, openspec_change=None):
        """Create a run in create_change phase with roadmap_link evidence."""
        self._make_openspec_change(change_id)
        if item_id:
            self._make_roadmap_item(
                item_id, item_status,
                openspec_change=openspec_change or change_id,
            )
        run_id = f"2026-06-20-{change_id}"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "create_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {"change_id": change_id},
            "phase_readiness": {
                "phase": "create_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        }
        if item_id:
            state["evidence"]["roadmap_link"] = {
                "count": 1,
                "items": [{
                    "item_id": item_id,
                    "status": item_status,
                    "file": f".ai/roadmap/areas/area1/items/{item_id}.md",
                    "area": "area1",
                }],
            }
            state["context"]["roadmap_item_id"] = item_id
        self._write_current_state(state)

    def _add_hook(self, hook_name):
        state = self._read_current_state()
        state.setdefault("pending_hooks", []).append(hook_name)
        self._write_current_state(state)

    def test_ready_hook_blocks_when_item_not_ready(self):
        """1.1: roadmap_status_ready_if_linked remains pending and blocks with
        domain_state_mismatch when a linked roadmap item is not ready."""
        self._setup_create_change_run("ready-block", "RM-RDY-001", "planned")
        self._add_hook("roadmap_status_ready_if_linked")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_status_ready_if_linked",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "domain_state_mismatch")
        self.assertIn("roadmap_status_ready_if_linked", data["pending_hooks"])

    def test_ready_hook_completes_when_item_is_ready(self):
        """1.2: roadmap_status_ready_if_linked completes only after the linked
        roadmap item is observed with status: ready."""
        self._setup_create_change_run("ready-ok", "RM-RDY-002", "ready")
        self._add_hook("roadmap_status_ready_if_linked")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_status_ready_if_linked",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn(
            "roadmap_status_ready_if_linked", data["pending_hooks"]
        )
        self.assertIn(
            "roadmap_status_ready_if_linked", data["completed_hooks"]
        )
        self.assertEqual(
            data["evidence"]["roadmap_hook_resolution"], "ready"
        )

    def test_ready_hook_completes_no_linked_item(self):
        """1.5: no-link case completes idempotently with no_linked_item evidence."""
        self._setup_create_change_run("ready-no-link", None, None)
        self._add_hook("roadmap_status_ready_if_linked")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_status_ready_if_linked",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn(
            "roadmap_status_ready_if_linked", data["pending_hooks"]
        )
        self.assertEqual(
            data["evidence"]["roadmap_hook_resolution"], "no_linked_item"
        )

    def test_ready_hook_blocks_multiple_linked_items(self):
        """1.5: multiple-link case blocks with user_decision_required."""
        self._make_roadmap_item("RM-RDY-A", "planned", openspec_change="ready-multi")
        self._make_roadmap_item("RM-RDY-B", "planned", openspec_change="ready-multi")
        self._setup_create_change_run("ready-multi", "RM-RDY-A", "planned")
        state = self._read_current_state()
        state["evidence"]["roadmap_link"] = {
            "count": 2,
            "items": [
                {"item_id": "RM-RDY-A", "status": "planned",
                 "file": ".ai/roadmap/areas/area1/items/RM-RDY-A.md", "area": "area1"},
                {"item_id": "RM-RDY-B", "status": "planned",
                 "file": ".ai/roadmap/areas/area1/items/RM-RDY-B.md", "area": "area1"},
            ],
        }
        self._write_current_state(state)
        self._add_hook("roadmap_status_ready_if_linked")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_status_ready_if_linked",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "user_decision_required")
        self.assertIn("roadmap_status_ready_if_linked", data["pending_hooks"])


class TestRoadmapSpecLinkHook(FixtureBase):
    """Tests for roadmap_spec_link_if_ready hook validation."""

    def _setup_create_change_run(self, change_id, item_id, item_status, spec_change=None):
        """Create a run in create_change phase with roadmap_link evidence."""
        self._make_openspec_change(change_id)
        if item_id:
            self._make_roadmap_item(
                item_id, item_status,
                spec_change=spec_change or change_id,
            )
        run_id = f"2026-06-20-{change_id}"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "create_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {"change_id": change_id},
            "phase_readiness": {
                "phase": "create_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        }
        if item_id:
            state["evidence"]["roadmap_link"] = {
                "count": 1,
                "items": [{
                    "item_id": item_id,
                    "status": item_status,
                    "file": f".ai/roadmap/areas/area1/items/{item_id}.md",
                    "area": "area1",
                }],
            }
            state["context"]["roadmap_item_id"] = item_id
        self._write_current_state(state)

    def _add_hook(self, hook_name):
        state = self._read_current_state()
        state.setdefault("pending_hooks", []).append(hook_name)
        self._write_current_state(state)

    def test_complete_hook_spec_link_blocks_when_item_not_ready(self):
        self._make_roadmap_item("RM-LINK-IDEA", "idea", spec_change="link-change")
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="link-change")
        state = self._read_current_state()
        state["pending_hooks"] = ["roadmap_spec_link_if_ready"]
        state["evidence"]["roadmap_link"] = {
            "count": 1,
            "items": [{"item_id": "RM-LINK-IDEA", "status": "idea"}],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "complete-hook", hook="roadmap_spec_link_if_ready")

        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "domain_state_mismatch")
        self.assertIn("expected ready", data["block"]["message"])

    def test_complete_hook_spec_link_succeeds_for_ready_item(self):
        self._make_roadmap_item("RM-LINK-READY", "ready", spec_change="link-ready")
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="link-ready")
        state = self._read_current_state()
        state["pending_hooks"] = ["roadmap_spec_link_if_ready"]
        state["evidence"]["roadmap_link"] = {
            "count": 1,
            "items": [{"item_id": "RM-LINK-READY", "status": "ready"}],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "complete-hook", hook="roadmap_spec_link_if_ready")

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("roadmap_spec_link_if_ready", data.get("completed_hooks", []))
        self.assertEqual(data["evidence"].get("roadmap_hook_resolution"), "spec_linked")


class TestRoadmapApplyStartHook(FixtureBase):
    """Tests for roadmap_apply_start_if_ready hook validation (Tasks 1.3, 1.4, 1.5)."""

    def _setup_apply_change_run(self, change_id, item_id, item_status, started_at=None,
                                 openspec_change=None):
        """Create a run in apply_change phase with roadmap_link evidence."""
        self._make_openspec_change(change_id)
        if item_id:
            self._make_roadmap_item(
                item_id, item_status,
                openspec_change=openspec_change or change_id,
                started_at=started_at,
            )
        run_id = f"2026-06-20-{change_id}"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {"change_id": change_id},
            "phase_readiness": {
                "phase": "apply_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": ["roadmap_status_ready_if_linked"],
            "completed_phases": ["create_change", "apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        }
        if item_id:
            item_entry = {
                "item_id": item_id,
                "status": item_status,
                "file": f".ai/roadmap/areas/area1/items/{item_id}.md",
                "area": "area1",
            }
            if started_at:
                item_entry["started_at"] = started_at
            state["evidence"]["roadmap_link"] = {
                "count": 1,
                "items": [item_entry],
            }
            state["context"]["roadmap_item_id"] = item_id
        self._write_current_state(state)

    def _add_hook(self, hook_name):
        state = self._read_current_state()
        state.setdefault("pending_hooks", []).append(hook_name)
        self._write_current_state(state)

    def test_apply_start_hook_blocks_when_item_still_ready(self):
        """1.3: roadmap_apply_start_if_ready remains pending and blocks with
        domain_state_mismatch when a linked roadmap item is still ready."""
        self._setup_apply_change_run("apply-block", "RM-APP-001", "ready")
        self._add_hook("roadmap_apply_start_if_ready")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_apply_start_if_ready",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "domain_state_mismatch")
        self.assertIn("roadmap_apply_start_if_ready", data["pending_hooks"])

    def test_apply_start_hook_completes_when_item_is_active(self):
        """1.4: roadmap_apply_start_if_ready completes only after the linked
        roadmap item is observed with status: active and non-empty started_at."""
        self._setup_apply_change_run(
            "apply-ok", "RM-APP-002", "active", started_at="2026-06-20"
        )
        self._add_hook("roadmap_apply_start_if_ready")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_apply_start_if_ready",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn(
            "roadmap_apply_start_if_ready", data["pending_hooks"]
        )
        self.assertIn(
            "roadmap_apply_start_if_ready", data["completed_hooks"]
        )
        self.assertEqual(
            data["evidence"]["roadmap_hook_resolution"], "active"
        )

    def test_apply_start_hook_completes_no_linked_item(self):
        """1.5: no-link case completes idempotently with no_linked_item evidence."""
        self._setup_apply_change_run("apply-no-link", None, None)
        self._add_hook("roadmap_apply_start_if_ready")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_apply_start_if_ready",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn(
            "roadmap_apply_start_if_ready", data["pending_hooks"]
        )
        self.assertEqual(
            data["evidence"]["roadmap_hook_resolution"], "no_linked_item"
        )

    def test_apply_start_hook_blocks_multiple_linked_items(self):
        """1.5: multiple-link case blocks with user_decision_required."""
        self._make_roadmap_item("RM-APP-A", "ready", openspec_change="apply-multi")
        self._make_roadmap_item("RM-APP-B", "ready", openspec_change="apply-multi")
        self._setup_apply_change_run("apply-multi", "RM-APP-A", "ready")
        state = self._read_current_state()
        state["evidence"]["roadmap_link"] = {
            "count": 2,
            "items": [
                {"item_id": "RM-APP-A", "status": "ready",
                 "file": ".ai/roadmap/areas/area1/items/RM-APP-A.md", "area": "area1"},
                {"item_id": "RM-APP-B", "status": "ready",
                 "file": ".ai/roadmap/areas/area1/items/RM-APP-B.md", "area": "area1"},
            ],
        }
        self._write_current_state(state)
        self._add_hook("roadmap_apply_start_if_ready")

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_apply_start_if_ready",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "user_decision_required")
        self.assertIn("roadmap_apply_start_if_ready", data["pending_hooks"])


class TestGateLedger(FixtureBase):
    def test_done_requires_gates_resolved(self):
        self._make_openspec_archive("gate-test")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="gate-test",
        )
        for hook in ("roadmap_done_if_relevant", "memory_sync"):
            run_workflow(
                self.tmp, "complete-hook",
                hook=hook,
                resolution="synced" if hook == "memory_sync" else None,
            )
        state = self._read_current_state()
        state["current_phase"] = "done"
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        state["gates"] = {"evalops": {"status": "required"}}
        state["status"] = "running"
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")

    def test_evalops_passed_allows_done(self):
        self._make_openspec_archive("gate-pass-test")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="gate-pass-test",
        )
        for hook in ("roadmap_done_if_relevant", "memory_sync"):
            run_workflow(
                self.tmp, "complete-hook",
                hook=hook,
                resolution="synced" if hook == "memory_sync" else None,
            )
        state = self._read_current_state()
        state["current_phase"] = "done"
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        state["gates"] = {"evalops": {"status": "passed"}}
        state["status"] = "running"
        state.setdefault("evidence", {}).setdefault("agent_results", {})["default"] = {
            "finish-agent": {
                "agent": "finish-agent",
                "status": "success",
                "phase": "post_archive_actions",
                "slice_id": "default",
                "flow_type": "spec-flow",
                "evidence": {},
                "artifacts": {},
                "blockers": [],
            }
        }
        state.setdefault("evidence", {}).setdefault("agent_phase", {})["slice_id"] = "default"
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")


class TestEvalTargetConditional(FixtureBase):
    def test_no_eval_target_for_deterministic_only(self):
        self._make_openspec_archive("no-eval")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="no-eval",
        )
        state = self._read_current_state()
        # context does not have eval_target_id, and that's fine for deterministic
        self.assertNotIn("eval_target_id", state.get("context", {}))


class TestCompletePhase(FixtureBase):
    def test_complete_phase_registers_hooks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="cp-test",
        )
        state = self._read_current_state()
        state["current_phase"] = "archive_change"
        state["evidence"]["archive_path"] = "openspec/changes/archive/2026-06-18-cp-test"
        state["evidence"]["archive_path_exists"] = True
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("archive_change", data.get("completed_phases", []))
        # Normal-flow phases no longer enqueue runtime post_hooks.
        # memory_sync and roadmap_done_if_relevant belong to post_archive_actions
        # finish-agent evidence, not to pending_hooks.
        self.assertEqual(data.get("pending_hooks"), [])
        self.assertNotIn("memory_sync", data.get("pending_hooks", []))
        self.assertNotIn("roadmap_done_if_relevant", data.get("pending_hooks", []))
    def test_apply_change_requires_execution_evidence_keys(self):
        self._make_roadmap_item("RM-APPLY-001", "active", openspec_change="apply-evidence-test")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-APPLY-001",
        )
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["evidence"]["openspec_status"] = {"classification": "in-progress", "source": "active"}
        state["evidence"]["roadmap_item_status"] = {"item_id": "RM-APPLY-001", "status": "active"}
        # Install valid completed implementation state with aggregate review
        # passed so the aggregate review gate does not fire before evidence
        # key validation.
        state["implementation"] = _make_implementation_state(
            [_make_slice("default", status="completed",
                         accepted_head_ref="head-1",
                         review_evidence={"review_passed": True})],
            assessment_status="completed",
            decision="single_slice",
        )
        state["implementation"]["aggregate_review_status"] = "passed"
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)
        self.assertIn("tasks_complete", data["error"])
        self.assertIn("tdd_passed", data["error"])
        self.assertIn("eval_passed_or_human_decision_recorded", data["error"])


class TestRoadmapHookFiltering(FixtureBase):
    """Roadmap hooks are only enqueued when primary_subject.type == roadmap_item."""
    def test_spec_change_run_does_not_enqueue_roadmap_hooks_on_archive_change(self):
        """complete-phase on archive_change for a spec_change run skips roadmap hooks."""
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="hook-filter-archive",
        )
        state = self._read_current_state()
        state["current_phase"] = "archive_change"
        state["evidence"]["archive_path"] = "openspec/changes/archive/2026-07-05-hook-filter-archive"
        state["evidence"]["archive_path_exists"] = True
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn("roadmap_done_if_relevant", data.get("pending_hooks", []),
                         "roadmap_done_if_relevant must not be enqueued for spec_change runs")
        # Normal-flow archive_change no longer enqueues memory_sync as a runtime hook.
        # Cleanup is owned by finish-agent in post_archive_actions.
        self.assertNotIn("memory_sync", data.get("pending_hooks", []),
                         "memory_sync must not be enqueued for normal-flow runs")

    def test_spec_change_run_does_not_enqueue_roadmap_hooks_on_create_change(self):
        """complete-phase on create_change for a spec_change run skips roadmap_spec_link_if_ready."""
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="hook-filter-create",
        )
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        state["evidence"]["spec_artifacts_done"] = True
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="spec_artifacts_done",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn("roadmap_spec_link_if_ready", data.get("pending_hooks", []),
                         "roadmap_spec_link_if_ready must not be enqueued for spec_change runs")

    def test_spec_change_run_does_not_enqueue_roadmap_hooks_on_apply_change(self):
        """complete-phase on apply_change for a spec_change run skips roadmap_apply_start_if_ready."""
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="hook-filter-apply",
        )
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["evidence"]["tasks_complete"] = True
        state["evidence"]["tdd_passed"] = True
        state["evidence"]["eval_passed_or_human_decision_recorded"] = True
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn("roadmap_apply_start_if_ready", data.get("pending_hooks", []),
                         "roadmap_apply_start_if_ready must not be enqueued for spec_change runs")

    def test_roadmap_item_run_can_enqueue_roadmap_hooks_on_apply_change(self):
        """complete-phase on apply_change for a roadmap_item run no longer enqueues
        roadmap_apply_start_if_ready because normal-flow phases do not use post_hooks.
        Roadmap lifecycle transitions are now owned by phase agents and finish-agent evidence."""
        self._make_roadmap_item("RM-HF-001", "active", openspec_change="hook-filter-roadmap")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-HF-001",
        )
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["evidence"]["tasks_complete"] = True
        state["evidence"]["tdd_passed"] = True
        state["evidence"]["eval_passed_or_human_decision_recorded"] = True
        state["evidence"]["openspec_status"] = {"classification": "in-progress", "source": "active"}
        state["evidence"]["roadmap_item_status"] = {"item_id": "RM-HF-001", "status": "active"}
        # Install valid completed implementation state with aggregate review
        # passed so the aggregate review gate does not block phase completion.
        state["implementation"] = _make_implementation_state(
            [_make_slice("default", status="completed",
                         accepted_head_ref="head-1",
                         review_evidence={"review_passed": True})],
            assessment_status="completed",
            decision="single_slice",
        )
        state["implementation"]["aggregate_review_status"] = "passed"
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # Normal-flow phases no longer enqueue runtime post_hooks.
        self.assertNotIn("roadmap_apply_start_if_ready", data.get("pending_hooks", []),
                         "roadmap_apply_start_if_ready must not be enqueued in normal flow")


class TestWorkflowDefinitionContracts(FixtureBase):
    def test_default_routing_phases_use_dev_orchestrator(self):
        wf = load_yaml(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml")
        phases = wf["phases"]

        for phase_name in (
            "input",
            "decide_intent",
            "review_decision",
            "create_change",
            "apply_change",
            "archive_change",
            "post_archive_actions",
            "done",
        ):
            allowed = phases[phase_name].get("allowed_workers", [])
            self.assertIn(
                "dev-orchestrator",
                allowed,
                f"{phase_name} should route through dev-orchestrator",
            )
            self.assertNotIn(
                "sdlc-orchestrator",
                allowed,
                f"{phase_name} should not route through legacy sdlc-orchestrator",
            )

    def test_change_phases_do_not_hardcode_spec_backends(self):
        wf = load_yaml(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml")
        phases = wf["phases"]

        concrete_spec_workers = {
            "openspec-propose",
            "openspec-new-change",
            "openspec-continue-change",
            "openspec-apply-change",
            "openspec-archive-change",
        }

        for phase_name in ("create_change", "apply_change", "archive_change"):
            allowed = set(phases[phase_name].get("allowed_workers", []))
            self.assertFalse(
                allowed & concrete_spec_workers,
                f"{phase_name} should not hardcode spec backends in allowed_workers",
            )

    def test_create_change_uses_provider_agnostic_spec_artifact_gate(self):
        wf = load_yaml(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml")
        create_change = wf["phases"]["create_change"]

        self.assertEqual(create_change.get("exit_criteria"), ["spec_artifacts_done"])
        self.assertEqual(create_change.get("evidence_keys"), ["spec_artifacts_done"])

    def test_review_roadmap_routes_through_dev_orchestrator(self):
        wf = load_yaml(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml")
        review_roadmap = wf["phases"]["review_roadmap"]

        self.assertEqual(review_roadmap.get("allowed_workers"), ["dev-orchestrator"])
        self.assertEqual(review_roadmap.get("exit_criteria"), ["review_decision_recorded"])

    def test_create_change_uses_spec_link_hook(self):
        wf = load_yaml(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml")
        create_change = wf["phases"]["create_change"]

        # Normal-flow create_change no longer defines post_hooks.
        # Roadmap spec link is now handled by plan-agent / dev-orchestrator evidence.
        self.assertNotIn("roadmap_spec_link_if_ready", create_change.get("post_hooks", []))
        self.assertNotIn("roadmap_status_ready_if_linked", create_change.get("post_hooks", []))


class TestGovernanceCheck(FixtureBase):
    """Tests for read-only governance-check command."""

    def _run_gc(self):
        rc, out, err = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0, f"governance-check failed: {err}")
        data = json.loads(out)
        self.assertIn("block", data)
        self.assertIn("findings", data)
        return data

    def _make_active_run(self, change_id, pending_hooks=None):
        runs_dir = os.path.join(self.tmp, ".ai", "workflows", "runs")
        os.makedirs(runs_dir, exist_ok=True)
        run_id = f"2026-06-20-{change_id}"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "input",
            "primary_subject": {
                "type": "spec_change",
                "id": change_id,
            },
            "context": {"change_id": change_id},
            "phase_readiness": {"phase": "input", "ready": True, "missing_required_inputs": []},
            "pending_hooks": pending_hooks or [],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
        }
        active_dir = os.path.join(runs_dir, "active")
        os.makedirs(os.path.join(active_dir, run_id), exist_ok=True)
        with open(os.path.join(active_dir, run_id, "run.json"), "w") as f:
            json.dump(state, f)
        pointer_path = os.path.join(runs_dir, "current.json")
        with open(pointer_path, "w") as f:
            json.dump({"run_id": run_id}, f)

    def _make_done_history_run(self, change_id):
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        state = {
            "version": 1,
            "run_id": f"2026-06-20-{change_id}",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {
                "type": "spec_change",
                "id": change_id,
            },
            "context": {"change_id": change_id},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
        }
        run_dir = os.path.join(hist_dir, state["run_id"])
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)

    def _make_done_roadmap_history_run(self, item_id, change_id):
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        state = {
            "version": 1,
            "run_id": f"2026-06-20-{item_id}",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {
                "type": "roadmap_item",
                "id": item_id,
            },
            "context": {"change_id": change_id, "roadmap_item_id": item_id},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
        }
        run_dir = os.path.join(hist_dir, state["run_id"])
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)

    # 3.2: clean state returns block=false
    def test_clean_state_returns_block_false(self):
        data = self._run_gc()
        self.assertFalse(data["block"])
        self.assertEqual(data["findings"], [])

    # 3.3: dangling archive
    def test_dangling_archive_returns_block_true(self):
        self._make_openspec_archive("demo-change", "2026-06-20")
        data = self._run_gc()
        self.assertTrue(data["block"])
        self.assertEqual(len(data["findings"]), 1)
        f = data["findings"][0]
        self.assertEqual(f["type"], "dangling_archive")
        self.assertEqual(f["change_id"], "demo-change")
        self.assertIn("2026-06-20-demo-change", f["archive_path"])
        self.assertTrue(f["message"])
        self.assertTrue(f["remediation"])
        self.assertTrue(f["hash"])
        self.assertEqual(len(f["hash"]), 12)

    # 3.4: archived change with matching active run not dangling
    def test_archived_with_active_run_not_dangling(self):
        self._make_openspec_archive("demo-change", "2026-06-20")
        self._make_active_run("demo-change")
        data = self._run_gc()
        self.assertFalse(data["block"])
        self.assertEqual(data["findings"], [])

    # 3.5: archived change with matching done history run not dangling
    def test_archived_with_done_history_not_dangling(self):
        self._make_openspec_archive("demo-change", "2026-06-20")
        self._make_done_history_run("demo-change")
        data = self._run_gc()
        self.assertFalse(data["block"])
        self.assertEqual(data["findings"], [])

    def test_archived_with_done_roadmap_history_not_dangling(self):
        self._make_openspec_archive("canonical-change", "2026-06-20")
        self._make_done_roadmap_history_run("RM-GOV-CANONICAL", "canonical-change")
        data = self._run_gc()
        self.assertFalse(data["block"])
        self.assertEqual(data["findings"], [])

    # 3.6: pending hooks return block=true
    def test_pending_hooks_returns_block_true(self):
        self._make_active_run("demo-change", pending_hooks=["memory_sync", "roadmap_done_if_relevant"])
        data = self._run_gc()
        self.assertTrue(data["block"])
        self.assertEqual(len(data["findings"]), 1)
        f = data["findings"][0]
        self.assertEqual(f["type"], "pending_hooks")
        self.assertEqual(f["run_id"], "2026-06-20-demo-change")
        self.assertEqual(f["change_id"], "demo-change")
        self.assertIn("memory_sync", f["pending_hook_names"])
        self.assertIn("roadmap_done_if_relevant", f["pending_hook_names"])
        self.assertTrue(f["message"])
        self.assertTrue(f["remediation"])
        self.assertTrue(f["hash"])

    # 3.7: combined diagnostics
    def test_combined_findings_return_both(self):
        self._make_openspec_archive("other-change", "2026-06-20")
        self._make_active_run("demo-change", pending_hooks=["memory_sync"])
        data = self._run_gc()
        self.assertTrue(data["block"])
        types = {f["type"] for f in data["findings"]}
        self.assertIn("dangling_archive", types)
        self.assertIn("pending_hooks", types)
        self.assertEqual(len(data["findings"]), 2)

    # 3.8: write boundaries
    def test_governance_check_write_boundaries(self):
        self._make_openspec_archive("write-test", "2026-06-20")
        self._make_active_run("write-test", pending_hooks=["memory_sync"])

        archive_dir = os.path.join(self.tmp, "openspec", "changes", "archive", "2026-06-20-write-test")
        runs_dir = os.path.join(self.tmp, ".ai", "workflows", "runs")
        roadmap_dir = os.path.join(self.tmp, ".ai", "roadmap")
        os.makedirs(roadmap_dir, exist_ok=True)

        before_archive = os.path.getmtime(archive_dir)
        before_runs = os.path.getmtime(runs_dir)

        data = self._run_gc()

        after_archive = os.path.getmtime(archive_dir)
        after_runs = os.path.getmtime(runs_dir)

        self.assertEqual(before_archive, after_archive, "archive directory must not be modified")
        self.assertEqual(before_runs, after_runs, "runs directory must not be modified")
        self.assertTrue(data["block"])

    # hash stability
    def test_finding_hash_is_stable(self):
        self._make_openspec_archive("hash-test", "2026-06-20")
        data1 = self._run_gc()
        data2 = self._run_gc()
        self.assertEqual(
            data1["findings"][0]["hash"],
            data2["findings"][0]["hash"],
            "hash must be stable across repeated checks",
        )

    # duplicate archives for same change_id produce different hashes
    def test_duplicate_archive_different_dates_produce_different_hashes(self):
        self._make_openspec_archive("dup-test", "2026-06-20")
        self._make_openspec_archive("dup-test", "2026-06-21")
        data = self._run_gc()
        self.assertEqual(len(data["findings"]), 2)
        self.assertNotEqual(
            data["findings"][0]["hash"],
            data["findings"][1]["hash"],
        )

    # pending hooks with no change_id still works
    def test_pending_hooks_without_change_id(self):
        runs_dir = os.path.join(self.tmp, ".ai", "workflows", "runs")
        os.makedirs(runs_dir, exist_ok=True)
        run_id = "2026-06-20-unknown"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "input",
            "primary_subject": {"type": "other", "id": "unknown"},
            "context": {},
            "phase_readiness": {"phase": "input", "ready": True, "missing_required_inputs": []},
            "pending_hooks": ["memory_sync"],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
        }
        active_dir = os.path.join(runs_dir, "active")
        os.makedirs(os.path.join(active_dir, run_id), exist_ok=True)
        with open(os.path.join(active_dir, run_id, "run.json"), "w") as f:
            json.dump(state, f)
        with open(os.path.join(runs_dir, "current.json"), "w") as f:
            json.dump({"run_id": run_id}, f)
        data = self._run_gc()
        self.assertTrue(data["block"])
        f = data["findings"][0]
        self.assertIsNone(f["change_id"])

    # Prompt contract: remediation text must contain runtime follow-up commands
    def test_pending_hooks_remediation_includes_complete_hook_and_stop_condition(self):
        self._make_active_run(
            "contract-test", pending_hooks=["memory_sync", "roadmap_done_if_relevant"]
        )
        data = self._run_gc()
        f = data["findings"][0]
        remediation = f["remediation"]
        self.assertIn("complete-hook", remediation,
                      "remediation must mention workflow.py complete-hook")
        self.assertIn("governance-check", remediation,
                      "remediation must mention re-running governance-check")
        self.assertIn("block=false", remediation,
                      "remediation must include stop condition block=false")

    # Prompt contract: dangling archive remediation includes ensure-run and stop condition
    def test_dangling_archive_remediation_includes_ensure_run_and_stop_condition(self):
        self._make_openspec_archive("contract-dangle", "2026-06-20")
        data = self._run_gc()
        f = data["findings"][0]
        self.assertIn("ensure-run", f["remediation"],
                      "remediation must mention workflow.py ensure-run")
        self.assertIn("complete-phase", f["remediation"],
                      "remediation must include complete-phase step")
        self.assertIn("pending_hooks_empty", f["remediation"],
                      "remediation must reference pending_hooks_empty exit criteria")
        self.assertIn("governance-check", f["remediation"])
        self.assertIn("block=false", f["remediation"])


class TestPreflightAndEnsureRun(FixtureBase):
    """Tests for preflight and ensure-run commands."""

    def _run_preflight(self, action, subject_type=None, subject_id=None):
        kwargs = {"action": action}
        if subject_type:
            kwargs["subject_type"] = subject_type
        if subject_id:
            kwargs["subject_id"] = subject_id
        rc, out, err = run_workflow(self.tmp, "preflight", **kwargs)
        return rc, json.loads(out), err

    def _run_ensure_run(self, action, subject_type=None, subject_id=None):
        kwargs = {"action": action}
        if subject_type:
            kwargs["subject_type"] = subject_type
        if subject_id:
            kwargs["subject_id"] = subject_id
        rc, out, err = run_workflow(self.tmp, "ensure-run", **kwargs)
        return rc, json.loads(out), err

    # --- openspec action without active run ---

    def test_preflight_openspec_create_without_active_run_blocks(self):
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="spec_change",
            subject_id="new-change",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["reason"], "missing_active_run")
        self.assertIsNotNone(data["next_action"])
        self.assertIn("start", data["next_action"].get("command", ""))

    def test_preflight_openspec_apply_without_active_run_blocks(self):
        rc, data, _ = self._run_preflight(
            "openspec_apply",
            subject_type="spec_change",
            subject_id="apply-me",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    def test_preflight_openspec_archive_without_active_run_blocks(self):
        rc, data, _ = self._run_preflight(
            "openspec_archive",
            subject_type="spec_change",
            subject_id="archive-me",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    # --- openspec action with matching active run ---

    def test_preflight_openspec_create_with_matching_active_run_allows(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="my-change",
        )
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="spec_change",
            subject_id="my-change",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "ok")

    # --- openspec action with different active run ---

    def test_preflight_openspec_create_with_different_active_run_blocks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="existing-change",
        )
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="spec_change",
            subject_id="new-change",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    # --- openspec action with done history ---

    def test_preflight_openspec_create_with_done_history_allows(self):
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        run_dir = os.path.join(hist_dir, "2026-06-20-hist-change")
        os.makedirs(run_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": "2026-06-20-hist-change",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {"type": "spec_change", "id": "hist-change"},
            "context": {"change_id": "hist-change"},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [],
            "completed_phases": [], "gates": {}, "evidence": {},
            "block": None, "updated_at": "2026-06-20T00:00:00",
        }
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="spec_change",
            subject_id="hist-change",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "ok")

    # --- dangling archive repair (preflight read-only) ---

    def test_preflight_dangling_archive_repair_without_run_blocks(self):
        self._make_openspec_archive("orphan-arch", "2026-06-20")
        rc, data, _ = self._run_preflight(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="orphan-arch",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")
        self.assertIn("ensure-run", data["next_action"].get("command", ""))

    def test_preflight_dangling_archive_repair_with_active_run_allows(self):
        self._make_openspec_archive("has-run-arch", "2026-06-20")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="has-run-arch",
        )
        rc, data, _ = self._run_preflight(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="has-run-arch",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])

    def test_preflight_dangling_archive_repair_with_done_history_allows(self):
        self._make_openspec_archive("done-arch", "2026-06-20")
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        run_dir = os.path.join(hist_dir, "2026-06-20-done-arch")
        os.makedirs(run_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": "2026-06-20-done-arch",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {"type": "spec_change", "id": "done-arch"},
            "context": {"change_id": "done-arch"},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [],
            "completed_phases": [], "gates": {}, "evidence": {},
            "block": None, "updated_at": "2026-06-20T00:00:00",
        }
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)
        rc, data, _ = self._run_preflight(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="done-arch",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])

    # --- ensure-run creates active run for dangling archive ---

    def test_ensure_run_creates_run_for_dangling_archive(self):
        self._make_openspec_archive("orphan-ens", "2026-06-20")
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="orphan-ens",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "run_created")
        self.assertIn("orphan-ens", data["run_id"])
        # next_action must name the complete-phase step
        desc = data.get("next_action", {}).get("description", "")
        self.assertIn("complete-phase", desc,
                      "next_action must include complete-phase step")
        self.assertIn("pending_hooks_empty", desc,
                      "next_action must reference pending_hooks_empty exit criteria")
        # Verify current.json was created with post_archive_actions phase
        current = self._read_current_state()
        self.assertIsNotNone(current)
        self.assertEqual(current["current_phase"], "post_archive_actions")
        self.assertEqual(
            current["primary_subject"],
            {"type": "spec_change", "id": "orphan-ens"},
        )

    # --- ensure-run skips when active run exists ---

    def test_ensure_run_skips_when_active_run_exists(self):
        self._make_openspec_archive("has-ens", "2026-06-20")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="has-ens",
        )
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="has-ens",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "ok")

    # --- ensure-run allows concurrent run for different subject ---

    def test_ensure_run_allows_concurrent_for_different_subject(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="other-change",
        )
        self._make_openspec_archive("block-me", "2026-06-20")
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="block-me",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "run_created")

    # --- ensure-run skips when done history exists ---

    def test_ensure_run_skips_when_done_history_exists(self):
        self._make_openspec_archive("done-ens", "2026-06-20")
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        run_dir = os.path.join(hist_dir, "2026-06-20-done-ens")
        os.makedirs(run_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": "2026-06-20-done-ens",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {"type": "spec_change", "id": "done-ens"},
            "context": {"change_id": "done-ens"},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [],
            "completed_phases": [], "gates": {}, "evidence": {},
            "block": None, "updated_at": "2026-06-20T00:00:00",
        }
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="done-ens",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "ok")

    # --- ensure-run dangling archive creates hooks ---

    def test_ensure_run_dangling_archive_has_pending_hooks(self):
        self._make_openspec_archive("hook-repair", "2026-06-20")
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="hook-repair",
        )
        self.assertEqual(rc, 0)
        self.assertEqual(data["status"], "run_created")
        current = self._read_current_state()
        self.assertIsNotNone(current)
        self.assertIn("memory_sync", current["pending_hooks"],
                      "dangling repair must create memory_sync hook")
        self.assertIn("roadmap_done_if_relevant", current["pending_hooks"],
                      "dangling repair must create roadmap_done_if_relevant hook")
        desc = data.get("next_action", {}).get("description", "")
        self.assertIn("complete-phase", desc,
                      "next_action must include complete-phase step")
        self.assertIn("pending_hooks_empty", desc,
                      "next_action must reference pending_hooks_empty exit criteria")

    def test_ensure_run_dangling_archive_blocks_when_linked_roadmap_run_exists(self):
        self._make_openspec_archive("block-linked", "2026-06-20")
        self._make_roadmap_item("RM-BLOCK-LINK", "done", openspec_change="block-linked", completed_at="2026-06-22")
        self._make_active_roadmap_run("RM-BLOCK-LINK", "block-linked", current_phase="apply_change")
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="spec_change",
            subject_id="block-linked",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "linked_roadmap_run_exists")
        self.assertIsNotNone(data.get("next_action"))
        self.assertIn("resume", data["next_action"].get("command", ""))

    # --- phase validation: preflight blocks when run phase doesn't match action ---

    def test_preflight_openspec_apply_in_create_phase_blocks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="phase-test",
        )
        # Run is in create_change phase (default for missing change)
        rc, data, _ = self._run_preflight(
            "openspec_apply",
            subject_type="spec_change",
            subject_id="phase-test",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "wrong_phase")

    def test_preflight_spec_apply_in_create_phase_blocks(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="phase-test")
        rc, data, _ = self._run_preflight("spec_apply", subject_type="spec_change", subject_id="phase-test")
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "wrong_phase")

    def test_preflight_openspec_archive_in_create_phase_blocks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="phase-test2",
        )
        rc, data, _ = self._run_preflight(
            "openspec_archive",
            subject_type="spec_change",
            subject_id="phase-test2",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "wrong_phase")

    def test_preflight_openspec_create_in_create_phase_allows(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="phase-ok",
        )
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="spec_change",
            subject_id="phase-ok",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "ok")

    def test_preflight_openspec_apply_in_apply_phase_allows(self):
        self._make_openspec_change("apply-ok")
        self._make_task_file("apply-ok", completed=False)
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="apply-ok",
        )
        rc, data, _ = self._run_preflight(
            "openspec_apply",
            subject_type="spec_change",
            subject_id="apply-ok",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])

    def test_preflight_openspec_archive_in_archive_phase_allows(self):
        self._make_openspec_change("archive-ok")
        self._make_task_file("archive-ok", completed=True)
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="archive-ok",
        )
        rc, data, _ = self._run_preflight(
            "openspec_archive",
            subject_type="spec_change",
            subject_id="archive-ok",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])

    # --- unknown action ---

    def test_preflight_unknown_action_returns_error(self):
        rc, data, _ = self._run_preflight("bogus_action")
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "unknown_action")

    # --- roadmap governed actions ---

    def test_preflight_roadmap_capture_recognized(self):
        rc, data, _ = self._run_preflight(
            "roadmap_capture",
            subject_type="roadmap_item",
            subject_id="RM-TEST-001",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    def test_preflight_roadmap_insert_recognized(self):
        rc, data, _ = self._run_preflight(
            "roadmap_insert",
            subject_type="roadmap_item",
            subject_id="RM-TEST-002",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    def test_preflight_roadmap_replan_recognized(self):
        rc, data, _ = self._run_preflight(
            "roadmap_replan",
            subject_type="roadmap_item",
            subject_id="RM-TEST-003",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    def test_preflight_roadmap_review_wrong_phase_blocks(self):
        # Start a run for a non-existent item → create_roadmap phase
        # create_roadmap does NOT allow roadmap_review
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-NEW-001",
        )
        rc, data, _ = self._run_preflight(
            "roadmap_review",
            subject_type="roadmap_item",
            subject_id="RM-NEW-001",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "wrong_phase")

    def test_preflight_roadmap_revise_without_run_blocks(self):
        rc, data, _ = self._run_preflight(
            "roadmap_revise",
            subject_type="roadmap_item",
            subject_id="RM-REV-002",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    def test_preflight_roadmap_revise_with_run_allows(self):
        self._make_roadmap_item("RM-REV-003", "idea")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-REV-003",
        )
        rc, data, _ = self._run_preflight(
            "roadmap_revise",
            subject_type="roadmap_item",
            subject_id="RM-REV-003",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])

    def test_preflight_roadmap_non_phase_mutating_does_not_advance(self):
        """roadmap_revise has no allowed_phases, should not check phase."""
        self._make_roadmap_item("RM-NP-001", "idea")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-NP-001",
        )
        rc, data, _ = self._run_preflight(
            "roadmap_cancel",
            subject_type="roadmap_item",
            subject_id="RM-NP-001",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["reason"], "active_run_exists")

    def _list_active_runs_support(self):
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        if not os.path.isdir(active_dir):
            return []
        results = []
        for fname in sorted(os.listdir(active_dir)):
            entry_path = os.path.join(active_dir, fname)
            if not os.path.isdir(entry_path):
                continue
            run_json = os.path.join(entry_path, "run.json")
            if not os.path.isfile(run_json):
                continue
            with open(run_json, "r") as f:
                state = json.load(f)
            results.append((state.get("run_id", fname), state))
        return results

    # --- canonical-run promotion: openspec_create finds linked roadmap_item run ---

    def test_preflight_openspec_create_finds_linked_roadmap_run_by_context(self):
        self._make_roadmap_item("RM-PROMO-001", "review", openspec_change="promo-change")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-PROMO-001",
        )
        # Write change_id into the roadmap item run's context (simulating promotion)
        active_runs = self._list_active_runs_support()
        for _run_id, state in active_runs:
            if "RM-PROMO-001" in _run_id:
                state["context"]["change_id"] = "promo-change"
                state["current_phase"] = "create_change"
                active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", _run_id)
                os.makedirs(active_dir, exist_ok=True)
                with open(os.path.join(active_dir, "run.json"), "w") as f:
                    json.dump(state, f)
                break
        # Now preflight openspec_create for the promoted change
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="spec_change",
            subject_id="promo-change",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["reason"], "linked_roadmap_run_exists")

    def test_preflight_openspec_create_finds_linked_roadmap_run_by_frontmatter(self):
        self._make_roadmap_item("RM-PROMO-002", "idea", openspec_change="promo-change-2")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-PROMO-002",
        )
        # Advance the run to create_change to match openspec_create allowed phases
        active_runs = self._list_active_runs_support()
        for _run_id, state in active_runs:
            if "RM-PROMO-002" in _run_id:
                state["current_phase"] = "create_change"
                active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", _run_id)
                os.makedirs(active_dir, exist_ok=True)
                with open(os.path.join(active_dir, "run.json"), "w") as f:
                    json.dump(state, f)
                break
        # Preflight without context.change_id set (frontmatter-only link)
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="spec_change",
            subject_id="promo-change-2",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["reason"], "linked_roadmap_run_exists")

    def test_preflight_openspec_create_direct_change_still_creates_run(self):
        """Direct openspec change without linked roadmap_item run returns missing_active_run."""
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="spec_change",
            subject_id="direct-change",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    def test_preflight_spec_create_finds_linked_roadmap_run_by_spec_change_frontmatter(self):
        self._make_roadmap_item("RM-PROMO-SPEC", "ready", spec_change="promo-spec")
        run_workflow(
            self.tmp,
            "start",
            subject_type="roadmap_item",
            subject_id="RM-PROMO-SPEC",
        )
        active_runs = self._list_active_runs_support()
        for _run_id, state in active_runs:
            if "RM-PROMO-SPEC" in _run_id:
                state["current_phase"] = "create_change"
                active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", _run_id)
                os.makedirs(active_dir, exist_ok=True)
                with open(os.path.join(active_dir, "run.json"), "w") as f:
                    json.dump(state, f)
                break

        rc, data, _ = self._run_preflight(
            "spec_create",
            subject_type="spec_change",
            subject_id="promo-spec",
        )

        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["reason"], "linked_roadmap_run_exists")

    def test_start_ready_roadmap_without_spec_change_starts_review_phase(self):
        self._make_roadmap_item("RM-READY-NOSPEC", "ready")

        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="roadmap_item",
            subject_id="RM-READY-NOSPEC",
        )

        self.assertEqual(rc, 0)
        state = json.loads(out)
        self.assertEqual(state["current_phase"], "review_roadmap")

    def test_start_ready_roadmap_with_spec_change_starts_create_change_phase(self):
        self._make_roadmap_item("RM-READY-SPEC", "ready", spec_change="ready-spec-change")

        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="roadmap_item",
            subject_id="RM-READY-SPEC",
        )

        self.assertEqual(rc, 0)
        state = json.loads(out)
        self.assertEqual(state["current_phase"], "create_change")


class TestCancelRun(FixtureBase):
    """Tests for cancel-run runtime primitive."""

    def test_cancel_run_removes_active_file(self):
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-CANCEL-001",
        )
        active_file = self._find_active_file("RM-CANCEL-001")
        self.assertIsNotNone(active_file)

        rc, out, _ = run_workflow(
            self.tmp, "cancel-run",
            subject_type="roadmap_item",
            subject_id="RM-CANCEL-001",
            reason="replanned",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "cancelled")
        self.assertEqual(data["reason"], "replanned")

        # File should be removed
        self.assertFalse(os.path.exists(active_file))

    def test_cancel_run_clears_pointer_when_pointed(self):
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-CANCEL-002",
        )
        # Verify pointer points to this run
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertTrue(pointer.get("run_id"))

        rc, out, _ = run_workflow(
            self.tmp, "cancel-run",
            subject_type="roadmap_item",
            subject_id="RM-CANCEL-002",
            reason="replanned",
        )
        self.assertEqual(rc, 0)
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertFalse(pointer.get("run_id"))

    def test_cancel_run_no_history_written(self):
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-CANCEL-003",
        )
        active_file = self._find_active_file("RM-CANCEL-003")
        run_id = os.path.basename(active_file).replace(".json", "")

        rc, out, _ = run_workflow(
            self.tmp, "cancel-run",
            subject_type="roadmap_item",
            subject_id="RM-CANCEL-003",
            reason="replanned",
        )
        self.assertEqual(rc, 0)

        # No history directory should exist for the cancelled run
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        hist_file = os.path.join(hist_dir, run_id, "run.json")
        self.assertFalse(os.path.exists(hist_file))

    def test_cancel_run_missing_run_reports_not_found(self):
        rc, out, _ = run_workflow(
            self.tmp, "cancel-run",
            subject_type="roadmap_item",
            subject_id="RM-NONEXIST",
            reason="replanned",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "not_found")

    def _find_active_file(self, subject_id):
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        for fname in sorted(os.listdir(active_dir)):
            entry_path = os.path.join(active_dir, fname)
            if not os.path.isdir(entry_path):
                continue
            run_json = os.path.join(entry_path, "run.json")
            if not os.path.isfile(run_json):
                continue
            with open(run_json) as f:
                state = json.load(f)
            ps = state.get("primary_subject", {})
            if ps.get("id") == subject_id:
                return entry_path
        return None


class TestGovernanceCheckExtended(FixtureBase):
    """Tests for governance-check extensions: roadmap items and duplicate runs."""

    def test_governance_check_ungoverned_roadmap_item(self):
        """An active roadmap item without a matching run should be flagged."""
        self._make_roadmap_item("RM-GOV-001", "ready")
        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        ungoverned = [f for f in data["findings"] if f["type"] == "ungoverned_roadmap_item"]
        self.assertGreaterEqual(len(ungoverned), 1)
        item_ids = [f["item_id"] for f in ungoverned]
        self.assertIn("RM-GOV-001", item_ids)

    def test_governance_check_ignores_done_roadmap_item(self):
        """A done roadmap item should not be flagged as ungoverned."""
        self._make_roadmap_item("RM-GOV-002", "done", completed_at="2026-06-22")
        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        ungoverned = [f for f in data["findings"] if f["type"] == "ungoverned_roadmap_item"
                      and f["item_id"] == "RM-GOV-002"]
        self.assertEqual(len(ungoverned), 0)

    def test_governance_check_ignores_idea_roadmap_item(self):
        """An idea roadmap item should not be flagged as ungoverned."""
        self._make_roadmap_item("RM-GOV-003", "idea")
        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        ungoverned = [f for f in data["findings"] if f["type"] == "ungoverned_roadmap_item"
                      and f["item_id"] == "RM-GOV-003"]
        self.assertEqual(len(ungoverned), 0)

    def test_governance_check_ignores_governed_roadmap_item(self):
        """A roadmap item with matching active run should not be flagged."""
        self._make_roadmap_item("RM-GOV-004", "ready")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-GOV-004",
        )
        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        ungoverned = [f for f in data["findings"] if f["type"] == "ungoverned_roadmap_item"
                      and f["item_id"] == "RM-GOV-004"]
        self.assertEqual(len(ungoverned), 0)

    def test_governance_check_flags_stale_active_roadmap_run(self):
        """A done roadmap item with an active run should be reported as stale."""
        self._make_roadmap_item("RM-GOV-STALE", "done", openspec_change="stale-change", completed_at="2026-06-22")
        self._make_active_roadmap_run("RM-GOV-STALE", "stale-change", current_phase="apply_change")
        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        stale = [f for f in data["findings"] if f["type"] == "stale_active_roadmap_run"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["item_id"], "RM-GOV-STALE")
        self.assertIn("cancel-run", stale[0]["remediation"])

    def test_governance_check_duplicate_promotion_runs(self):
        """Both a roadmap_item and openspec_change run for the same change should be flagged."""
        self._make_roadmap_item("RM-DUP-001", "review", openspec_change="dup-change")

        # Manually create a roadmap_item run with change_id in context
        rm_run_id = "2026-06-22-RM-DUP-001"
        rm_state = {
            "version": 1, "run_id": rm_run_id, "workflow": "sdlc-main",
            "status": "running", "current_phase": "create_change",
            "primary_subject": {"type": "roadmap_item", "id": "RM-DUP-001"},
            "context": {"change_id": "dup-change", "roadmap_item_id": "RM-DUP-001"},
            "phase_readiness": {"phase": "create_change", "ready": False, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": [],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "",
        }
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        os.makedirs(os.path.join(active_dir, rm_run_id), exist_ok=True)
        with open(os.path.join(active_dir, rm_run_id, "run.json"), "w") as f:
            json.dump(rm_state, f)

        # Manually create an openspec_change run for the same change
        oc_run_id = "2026-06-22-dup-change"
        oc_state = {
            "version": 1, "run_id": oc_run_id, "workflow": "sdlc-main",
            "status": "running", "current_phase": "create_change",
            "primary_subject": {"type": "spec_change", "id": "dup-change"},
            "context": {"change_id": "dup-change"},
            "phase_readiness": {"phase": "create_change", "ready": False, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": [],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "",
        }
        os.makedirs(os.path.join(active_dir, oc_run_id), exist_ok=True)
        with open(os.path.join(active_dir, oc_run_id, "run.json"), "w") as f:
            json.dump(oc_state, f)

        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        duplicate_findings = [f for f in data["findings"] if f["type"] == "duplicate_promotion_runs"]
        self.assertGreaterEqual(len(duplicate_findings), 1)
        self.assertIn("dup-change", duplicate_findings[0]["change_id"])

    def test_governance_check_duplicate_promotion_runs_with_spec_change(self):
        """Duplicate detection works when roadmap item uses spec_change (not openspec_change)."""
        self._make_roadmap_item("RM-DUP-SPEC", "review", spec_change="dup-spec-change")

        # roadmap_item run WITHOUT context.change_id -- forces fallback to
        # frontmatter read (which currently misses spec_change)
        rm_run_id = "2026-06-22-RM-DUP-SPEC"
        rm_state = {
            "version": 1, "run_id": rm_run_id, "workflow": "sdlc-main",
            "status": "running", "current_phase": "create_change",
            "primary_subject": {"type": "roadmap_item", "id": "RM-DUP-SPEC"},
            "context": {"roadmap_item_id": "RM-DUP-SPEC"},
            "phase_readiness": {"phase": "create_change", "ready": False, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": [],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "",
        }
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        os.makedirs(os.path.join(active_dir, rm_run_id), exist_ok=True)
        with open(os.path.join(active_dir, rm_run_id, "run.json"), "w") as f:
            json.dump(rm_state, f)

        # Manually create a spec_change run for the same change
        oc_run_id = "2026-06-22-dup-spec-change"
        oc_state = {
            "version": 1, "run_id": oc_run_id, "workflow": "sdlc-main",
            "status": "running", "current_phase": "create_change",
            "primary_subject": {"type": "spec_change", "id": "dup-spec-change"},
            "context": {"change_id": "dup-spec-change"},
            "phase_readiness": {"phase": "create_change", "ready": False, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": [],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "",
        }
        os.makedirs(os.path.join(active_dir, oc_run_id), exist_ok=True)
        with open(os.path.join(active_dir, oc_run_id, "run.json"), "w") as f:
            json.dump(oc_state, f)

        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        duplicate_findings = [f for f in data["findings"] if f["type"] == "duplicate_promotion_runs"]
        self.assertGreaterEqual(len(duplicate_findings), 1,
            "Duplicate promotion runs should be detected when roadmap item uses spec_change frontmatter")
        self.assertIn("dup-spec-change", duplicate_findings[0]["change_id"])

    def test_governance_check_linked_no_workflow_evidence_with_spec_change(self):
        """linked_item_no_workflow_evidence is generated for items with spec_change frontmatter."""
        self._make_roadmap_item("RM-LINK-SPEC", "ready", spec_change="link-spec-change")

        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        linked_findings = [f for f in data["findings"] if f["type"] == "linked_item_no_workflow_evidence"
                          and f["item_id"] == "RM-LINK-SPEC"]
        self.assertEqual(len(linked_findings), 1,
            "linked_item_no_workflow_evidence should flag roadmap item with spec_change and no workflow evidence")

    def _list_active_runs_support(self):
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        if not os.path.isdir(active_dir):
            return []
        results = []
        for fname in sorted(os.listdir(active_dir)):
            entry_path = os.path.join(active_dir, fname)
            if not os.path.isdir(entry_path):
                continue
            run_json = os.path.join(entry_path, "run.json")
            if not os.path.isfile(run_json):
                continue
            with open(run_json, "r") as f:
                state = json.load(f)
            results.append((state.get("run_id", fname), state))
        return results


class TestVerifyFoundations(FixtureBase):
    """Tests for the verify-foundations read-only command."""

    def _setup_all_foundations(self):
        """Create all files/dirs so that verify-foundations reports all present."""
        os.makedirs(os.path.join(self.tmp, ".ai", "workflows", "scripts"), exist_ok=True)
        with open(os.path.join(self.tmp, ".ai", "workflows", "scripts", "workflow.py"), "w") as f:
            f.write("# workflow\n")
        os.makedirs(os.path.join(self.tmp, ".ai", "workflows", "runs"), exist_ok=True)
        with open(os.path.join(self.tmp, "AGENTS.md"), "w") as f:
            f.write("# test\n")
        os.makedirs(os.path.join(self.tmp, "openspec"), exist_ok=True)
        with open(os.path.join(self.tmp, "openspec", "config.yaml"), "w") as f:
            f.write("schema: spec-driven\n")
        os.makedirs(os.path.join(self.tmp, ".ai", "memory"), exist_ok=True)
        with open(os.path.join(self.tmp, ".ai", "memory", "manifest.json"), "w") as f:
            f.write("{}")

    def test_all_present_exits_zero(self):
        """verify-foundations exits 0 when all foundations are present."""
        self._setup_all_foundations()
        rc, out, _ = run_workflow(self.tmp, "verify-foundations")
        self.assertEqual(rc, 0, f"all present should exit 0, got out={out!r}")

    def test_missing_reports_nonzero(self):
        """verify-foundations exits non-zero when foundations are missing."""
        # FixtureBase sets up workflow dirs but nothing else
        rc, out, _ = run_workflow(self.tmp, "verify-foundations")
        self.assertNotEqual(rc, 0,
                            f"missing foundations should exit non-zero, got out={out!r}")

    def test_json_reports_status(self):
        """verify-foundations --json returns machine-readable status per foundation."""
        self._setup_all_foundations()
        rc, out, _ = run_workflow(self.tmp, "verify-foundations", json=True)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("foundations", data)
        for k in ("workflow_py", "workflow_yaml", "workflow_runs",
                  "agents_md", "openspec_config", "memory_manifest"):
            self.assertIn(k, data["foundations"],
                          f"missing key {k!r} in foundations report")
        self.assertTrue(all(data["foundations"].values()),
                        f"all foundations should be present: {data['foundations']}")

    def test_missing_json_reports_which_are_missing(self):
        """verify-foundations --json reports which foundations are absent."""
        rc, out, _ = run_workflow(self.tmp, "verify-foundations", json=True)
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        present = {k for k, v in data["foundations"].items() if v}
        missing = {k for k, v in data["foundations"].items() if not v}
        self.assertIn("workflow_yaml", present)     # FixtureBase sets up definitions/
        self.assertIn("agents_md", missing)         # Not created


class TestRoadmapAgentRouting(FixtureBase):
    """Task 4.1: Prove roadmap-agent works through lifecycle dispatch, not General Task."""

    def _make_apply_run_with_roadmap(self, change_id, item_id, item_status, subject_type="roadmap_item"):
        """Create a run in apply_change phase with a linked roadmap item."""
        self._make_openspec_change(change_id)
        self._make_roadmap_item(
            item_id, item_status,
            openspec_change=change_id,
        )
        run_id = f"2026-06-20-{change_id}"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": subject_type, "id": item_id if subject_type == "roadmap_item" else change_id},
            "context": {"change_id": change_id, "roadmap_item_id": item_id},
            "phase_readiness": {
                "phase": "apply_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": ["roadmap_apply_start_if_ready"],
            "completed_hooks": ["roadmap_status_ready_if_linked"],
            "completed_phases": ["create_change", "apply_change"],
            "gates": {},
            "evidence": {
                "roadmap_link": {
                    "count": 1,
                    "items": [{
                        "item_id": item_id,
                        "status": item_status,
                        "file": f".ai/roadmap/areas/area1/items/{item_id}.md",
                        "area": "area1",
                    }],
                },
            },
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        }
        self._write_current_state(state)

    def test_roadmap_agent_accepted_by_before_dispatch(self):
        """roadmap-agent is accepted as a valid lifecycle agent by before-dispatch."""
        self._make_apply_run_with_roadmap("route-test", "RM-RT-001", "ready")
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="roadmap-agent",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data.get("blockers"), [])
        self.assertNotEqual(data.get("status"), "blocked")

    def test_roadmap_agent_accepted_in_apply_change_phase(self):
        """roadmap-agent is allowed in apply_change phase for roadmap hooks."""
        self._make_apply_run_with_roadmap("route-apply", "RM-RT-002", "ready")
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="roadmap-agent",
            phase="apply_change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotEqual(data.get("status"), "blocked")

    def test_roadmap_agent_blocked_when_no_active_run(self):
        """roadmap-agent dispatch blocks when there is no active run."""
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="roadmap-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data.get("status"), "blocked")
        blocker_reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertIn("no_active_run", blocker_reasons)

    def test_roadmap_agent_not_blocked_by_done_run_with_history(self):
        """roadmap-agent before-dispatch does not block when only done history exists.
        The ensure-run flow should be followed, but before-dispatch should not fail
        just because there's no active run — it should surface proper guidance."""
        self._make_openspec_change("route-done")
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="roadmap-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data.get("status"), "blocked")
        self.assertEqual(
            data.get("recommended_next_action"), "start_run"
        )

    def test_before_dispatch_blocks_roadmap_agent_for_spec_change_run(self):
        """roadmap-agent is blocked when primary_subject.type == spec_change."""
        self._make_apply_run_with_roadmap(
            "gate-block", "RM-GATE-001", "ready", subject_type="spec_change",
        )
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="roadmap-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("roadmap_not_enabled", reasons)

    def test_before_dispatch_allows_roadmap_agent_for_roadmap_item_run(self):
        """roadmap-agent is allowed when primary_subject.type == roadmap_item in review_roadmap."""
        self._make_roadmap_item("RM-GATE-002", "idea")
        run_id = "2026-06-20-gate-allow"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "review_roadmap",
            "primary_subject": {"type": "roadmap_item", "id": "RM-GATE-002"},
            "context": {"roadmap_item_id": "RM-GATE-002"},
            "phase_readiness": {
                "phase": "review_roadmap",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_roadmap"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="roadmap-agent",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")


class TestConcurrentRuns(FixtureBase):
    """Tests for multi-run concurrent support."""

    # 4.1 Two independent starts with different subject_id
    def test_two_independent_starts_create_separate_active_files(self):
        rc1, out1, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="change-a",
        )
        self.assertEqual(rc1, 0)
        data1 = json.loads(out1)
        run_id_a = data1["run_id"]

        rc2, out2, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="change-b",
        )
        self.assertEqual(rc2, 0)
        data2 = json.loads(out2)
        run_id_b = data2["run_id"]

        self.assertNotEqual(run_id_a, run_id_b)
        self.assertIsNotNone(self._read_active_file(run_id_a))
        self.assertIsNotNone(self._read_active_file(run_id_b))
        # Pointer should point to the last started run
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertEqual(pointer["run_id"], run_id_b)

    # 4.2 Duplicate subject_id start reports conflict
    def test_start_duplicate_subject_reports_conflict(self):
        rc1, _, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="dup-change",
        )
        self.assertEqual(rc1, 0)

        rc2, out2, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="dup-change",
        )
        self.assertNotEqual(rc2, 0)
        data = json.loads(out2)
        self.assertEqual(data["action"], "conflict")

    # 4.3 Resume with subject args finds correct run and sets pointer
    def test_resume_with_subject_args_finds_correct_run(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="change-a",
        )
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="change-b",
        )
        # Pointer now points to change-b
        rc, out, _ = run_workflow(
            self.tmp, "resume",
            subject_type="spec_change",
            subject_id="change-a",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("change-a", data["run_id"])
        # Pointer should now point to change-a
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertIn("change-a", pointer["run_id"])

    # 4.4 Status without subject lists all active runs
    def test_status_without_subject_lists_all_active_runs(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="change-x",
        )
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="change-y",
        )
        # Clear pointer to test listing
        pointer_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "current.json")
        with open(pointer_path, "w") as f:
            json.dump({}, f)

        rc, out, _ = run_workflow(self.tmp, "status")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "active_runs")
        self.assertEqual(len(data["runs"]), 2)
        run_ids = {r["run_id"] for r in data["runs"]}
        self.assertEqual(len(run_ids), 2)

    # 4.5 Done writes history, removes from active/, clears pointer
    def test_done_removes_active_and_clears_pointer(self):
        self._make_openspec_archive("done-concurrent", "2026-06-20")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="done-concurrent",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        run_id = data["run_id"]

        # Complete hooks and set up for done
        run_workflow(self.tmp, "complete-hook", hook="roadmap_done_if_relevant")
        run_workflow(
            self.tmp, "complete-hook",
            hook="memory_sync", resolution="synced",
        )
        state = self._read_current_state()
        state["current_phase"] = "done"
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        state["status"] = "running"
        state.setdefault("evidence", {}).setdefault("agent_results", {})["default"] = {
            "finish-agent": {
                "agent": "finish-agent",
                "status": "success",
                "phase": "post_archive_actions",
                "slice_id": "default",
                "flow_type": "spec-flow",
                "evidence": {},
                "artifacts": {},
                "blockers": [],
            }
        }
        state.setdefault("evidence", {}).setdefault("agent_phase", {})["slice_id"] = "default"
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")

        # Active directory should be removed
        active_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id)
        self.assertFalse(os.path.exists(active_path))

        # Pointer should be cleared
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertFalse(pointer.get("run_id"))

        # History should be written
        history = self._read_history(run_id)
        self.assertIsNotNone(history)
        self.assertEqual(history["status"], "done")

    # 4.6 Governance-check detects pending_hooks from ANY active run
    def test_governance_check_scans_all_active_runs(self):
        self._make_openspec_archive("gc-multi-a", "2026-06-20")
        self._make_openspec_archive("gc-multi-b", "2026-06-20")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="gc-multi-a",
        )
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="gc-multi-b",
        )
        # Add pending hook to the first run only
        active_runs = self._list_active_runs_support()
        for run_id, state in active_runs:
            if "gc-multi-a" in run_id:
                state["pending_hooks"] = ["memory_sync"]
                active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id)
                with open(os.path.join(active_dir, "run.json"), "w") as f:
                    json.dump(state, f)

        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["block"])
        pending = [f for f in data["findings"] if f["type"] == "pending_hooks"]
        self.assertGreaterEqual(len(pending), 1)

    # 4.7 Preflight searches active/ by subject and sets pointer
    def test_preflight_sets_pointer_by_subject(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="preflight-a",
        )
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="preflight-b",
        )
        # Pointer points to preflight-b. Preflight for preflight-a should switch pointer.
        rc, out, _ = run_workflow(
            self.tmp, "preflight",
            action="openspec_create",
            subject_type="spec_change",
            subject_id="preflight-a",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["allowed"])
        pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
        self.assertIn("preflight-a", pointer["run_id"])

    # 4.8 Stale pointer reports single JSON with summaries
    def test_status_stale_pointer_outputs_single_json(self):
        # Create a stale pointer (pointing to a missing run)
        pointer_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "current.json")
        os.makedirs(os.path.dirname(pointer_path), exist_ok=True)
        with open(pointer_path, "w") as f:
            json.dump({"run_id": "2026-06-22-missing-run"}, f)

        # No active runs
        rc, out, _ = run_workflow(self.tmp, "status")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "stale_pointer")
        self.assertEqual(data["pointer_run_id"], "2026-06-22-missing-run")
        self.assertIn("runs", data)
        self.assertEqual(data["runs"], [])

    def test_status_stale_pointer_with_active_runs_lists_summaries(self):
        # Create a stale pointer
        pointer_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "current.json")
        os.makedirs(os.path.dirname(pointer_path), exist_ok=True)
        with open(pointer_path, "w") as f:
            json.dump({"run_id": "2026-06-22-missing-run"}, f)

        # Create an active run via start (creates active/<run_id>.json + updates pointer)
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="stale-other",
        )

        # Overwrite pointer back to stale
        with open(pointer_path, "w") as f:
            json.dump({"run_id": "2026-06-22-missing-run"}, f)

        rc, out, _ = run_workflow(self.tmp, "status")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "stale_pointer")
        self.assertEqual(data["pointer_run_id"], "2026-06-22-missing-run")
        self.assertGreaterEqual(len(data["runs"]), 1)
        self.assertIn("stale-other", data["runs"][0]["run_id"])

    def _list_active_runs_support(self):
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        if not os.path.isdir(active_dir):
            return []
        results = []
        for fname in sorted(os.listdir(active_dir)):
            entry_path = os.path.join(active_dir, fname)
            if not os.path.isdir(entry_path):
                continue
            run_json = os.path.join(entry_path, "run.json")
            if not os.path.isfile(run_json):
                continue
            with open(run_json, "r") as f:
                state = json.load(f)
            results.append((state.get("run_id", fname), state))
        return results


class TestRoadmapPhaseInference(FixtureBase):
    """Tests for roadmap_item phase inference at start time."""

    def test_start_idea_item_goes_to_review_roadmap(self):
        self._make_roadmap_item("RM-PI-001", "idea")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-PI-001",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "review_roadmap")

    def test_start_ready_item_with_change_goes_to_create_change(self):
        self._make_roadmap_item("RM-PI-002", "ready", openspec_change="pi-change")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-PI-002",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "create_change")

    def test_start_ready_item_without_change_goes_to_review_roadmap(self):
        self._make_roadmap_item("RM-PI-003", "ready")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-PI-003",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "review_roadmap")

    def test_start_active_item_goes_to_apply_change(self):
        self._make_roadmap_item("RM-PI-004", "active")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-PI-004",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "apply_change")

    def test_start_new_item_goes_to_create_roadmap(self):
        # Item does not exist in the roadmap
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-PI-005",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "create_roadmap")

    def test_start_roadmap_item_default_is_running_not_blocked(self):
        """Default start (no --flow-type) for roadmap_item creates running spec-flow, not blocked."""
        self._make_roadmap_item("RM-PI-006", "idea")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-PI-006",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["flow_type"], "spec-flow")
        self.assertIsNone(data.get("block"))


class TestFlowType(FixtureBase):
    """Tests for flow_type persistence (spec: Run State Schema / Flow Type Inference)."""

    def test_start_without_flow_type_defaults_to_spec_flow(self):
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="ft-default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data.get("flow_type"), "spec-flow")

    def test_start_with_explicit_lightweight_flow_persists(self):
        self._make_roadmap_item("ft-lightweight", "idea")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="ft-lightweight",
            flow_type="lightweight-flow",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # Explicit flow_type is already confirmed by the caller; no confirmation gate.
        self.assertEqual(data.get("flow_type"), "lightweight-flow")
        self.assertNotEqual(data.get("status"), "blocked")
        self.assertIsNone(data.get("block"))

    def test_resume_preserves_stored_flow_type(self):
        self._make_roadmap_item("ft-resume", "idea")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="ft-resume",
            flow_type="lightweight-flow",
        )
        # Explicit flow_type starts running; no confirmation needed.
        rc, out, _ = run_workflow(
            self.tmp, "resume",
            subject_type="roadmap_item",
            subject_id="ft-resume",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data.get("flow_type"), "lightweight-flow")

    def test_validate_rejects_missing_flow_type(self):
        rdir = os.path.join(self.tmp, ".ai", "workflows", "runs")
        active_dir = os.path.join(rdir, "active")
        os.makedirs(active_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": "2026-06-26-no-ft",
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "input",
            "primary_subject": {"type": "spec_change", "id": "no-ft"},
            "context": {},
            "phase_readiness": {"phase": "input", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "",
        }
        run_dir = os.path.join(active_dir, "2026-06-26-no-ft")
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)
        pointer_path = os.path.join(rdir, "current.json")
        with open(pointer_path, "w") as f:
            json.dump({"run_id": "2026-06-26-no-ft"}, f)

        rc, _, stderr = run_workflow(self.tmp, "validate")
        self.assertNotEqual(rc, 0)
        self.assertIn("flow_type", stderr.lower())

    def test_validate_rejects_unsupported_flow_type(self):
        rdir = os.path.join(self.tmp, ".ai", "workflows", "runs")
        active_dir = os.path.join(rdir, "active")
        state = {
            "version": 1,
            "run_id": "2026-06-26-bad-ft",
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "input",
            "flow_type": "bogus-flow",
            "primary_subject": {"type": "spec_change", "id": "bad-ft"},
            "context": {},
            "phase_readiness": {"phase": "input", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "",
        }
        run_dir = os.path.join(active_dir, "2026-06-26-bad-ft")
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)
        pointer_path = os.path.join(rdir, "current.json")
        with open(pointer_path, "w") as f:
            json.dump({"run_id": "2026-06-26-bad-ft"}, f)

        rc, _, stderr = run_workflow(self.tmp, "validate")
        self.assertNotEqual(rc, 0)
        self.assertIn("flow_type", stderr.lower())

    def test_start_rejects_invalid_flow_type(self):
        """--flow-type bogus-flow is rejected by argparse."""
        rc, _, stderr = run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="ft-bogus",
            flow_type="bogus-flow",
        )
        self.assertNotEqual(rc, 0)

    def test_explicit_lightweight_flow_does_not_create_confirmation_block(self):
        """Explicit --flow-type lightweight-flow starts without a confirmation gate."""
        self._make_roadmap_item("RM-INFER-001", "idea")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-INFER-001",
            flow_type="lightweight-flow",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data.get("flow_type"), "lightweight-flow")
        # No confirmation block; explicit flow_type is treated as user-confirmed.
        self.assertNotEqual(data.get("status"), "blocked")
        self.assertIsNone(data.get("block"))

    def test_explicit_lightweight_flow_runs_directly(self):
        """Explicit --flow-type lightweight-flow starts running without confirmation."""
        self._make_roadmap_item("RM-CONFIRM-001", "idea")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-CONFIRM-001",
            flow_type="lightweight-flow",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # No confirmation gate; run is immediately usable.
        self.assertIsNone(data.get("block"))
        self.assertNotEqual(data.get("status"), "blocked")
        self.assertEqual(data.get("flow_type"), "lightweight-flow")


class TestEvidenceKeyValidation(FixtureBase):
    """Tests for evidence_keys validation (spec: Workflow Phase Evidence Contracts)."""

    def test_evidence_keys_rejects_non_list(self):
        tc = tempfile.mkdtemp()
        try:
            wf_dir = os.path.join(tc, ".ai", "workflows", "definitions")
            os.makedirs(wf_dir, exist_ok=True)
            wf_def = {
                "version": 1,
                "id": "sdlc-main",
                "phases": {
                    "input": {
                        "evidence_keys": "not_a_list",
                        "terminal": True,
                    },
                },
            }
            import yaml
            with open(os.path.join(wf_dir, "sdlc-main.yaml"), "w") as f:
                yaml.dump(wf_def, f)
            rc, _, stderr = run_workflow(tc, "validate")
            self.assertNotEqual(rc, 0)
            self.assertIn("evidence_keys", stderr.lower())
        finally:
            shutil.rmtree(tc, ignore_errors=True)

    def test_evidence_keys_rejects_empty_string_entries(self):
        tc = tempfile.mkdtemp()
        try:
            wf_dir = os.path.join(tc, ".ai", "workflows", "definitions")
            os.makedirs(wf_dir, exist_ok=True)
            wf_def = {
                "version": 1,
                "id": "sdlc-main",
                "phases": {
                    "input": {
                        "evidence_keys": ["", "valid_key"],
                        "terminal": True,
                    },
                },
            }
            import yaml
            with open(os.path.join(wf_dir, "sdlc-main.yaml"), "w") as f:
                yaml.dump(wf_def, f)
            rc, _, stderr = run_workflow(tc, "validate")
            self.assertNotEqual(rc, 0)
            self.assertIn("evidence_keys", stderr.lower())
        finally:
            shutil.rmtree(tc, ignore_errors=True)

    def test_complete_phase_fails_missing_evidence_key(self):
        """1.8: complete-phase fails when a declared evidence key is missing."""
        tc = tempfile.mkdtemp()
        try:
            src_def = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", ".ai", "workflows", "definitions",
            )
            dst_def = os.path.join(tc, ".ai", "workflows", "definitions")
            if os.path.isdir(src_def):
                shutil.copytree(src_def, dst_def)

            run_workflow(
                tc, "start",
                subject_type="spec_change",
                subject_id="evk-missing",
            )
            state = load_json(tc, ".ai/workflows/runs/current.json")
            active = load_json(tc, f".ai/workflows/runs/active/{state['run_id']}/run.json")

            # Add evidence_keys to the current phase definition and clear exit criteria
            wf_path = os.path.join(tc, ".ai", "workflows", "definitions", "sdlc-main.yaml")
            import yaml as _yaml
            with open(wf_path, "r") as f:
                wf = _yaml.safe_load(f)
            wf["phases"][active["current_phase"]]["evidence_keys"] = ["required_key"]
            wf["phases"][active["current_phase"]]["exit_criteria"] = []
            with open(wf_path, "w") as f:
                _yaml.dump(wf, f)

            rc, out, _ = run_workflow(tc, "complete-phase")
            self.assertNotEqual(rc, 0)
            self.assertIn("missing evidence", out.lower())
        finally:
            shutil.rmtree(tc, ignore_errors=True)

    def test_complete_phase_fails_empty_evidence_value(self):
        """1.9: complete-phase fails when a declared evidence key has empty value."""
        tc = tempfile.mkdtemp()
        try:
            src_def = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", ".ai", "workflows", "definitions",
            )
            dst_def = os.path.join(tc, ".ai", "workflows", "definitions")
            if os.path.isdir(src_def):
                shutil.copytree(src_def, dst_def)

            run_workflow(
                tc, "start",
                subject_type="spec_change",
                subject_id="evk-empty",
            )
            state = load_json(tc, ".ai/workflows/runs/current.json")
            active = load_json(tc, f".ai/workflows/runs/active/{state['run_id']}/run.json")

            # Record evidence with empty value
            active_path = os.path.join(tc, ".ai", "workflows", "runs", "active", f"{state['run_id']}/run.json")
            active["evidence"]["required_key"] = ""
            with open(active_path, "w") as f:
                json.dump(active, f)

            # Add evidence_keys to the current phase definition and clear exit criteria
            wf_path = os.path.join(tc, ".ai", "workflows", "definitions", "sdlc-main.yaml")
            import yaml as _yaml
            with open(wf_path, "r") as f:
                wf = _yaml.safe_load(f)
            wf["phases"][active["current_phase"]]["evidence_keys"] = ["required_key"]
            wf["phases"][active["current_phase"]]["exit_criteria"] = []
            with open(wf_path, "w") as f:
                _yaml.dump(wf, f)

            rc, out, _ = run_workflow(tc, "complete-phase")
            self.assertNotEqual(rc, 0)
            self.assertIn("empty evidence", out.lower())
        finally:
            shutil.rmtree(tc, ignore_errors=True)

    def test_complete_phase_succeeds_with_all_evidence_keys_present(self):
        """1.10: complete-phase succeeds when all evidence keys are present and non-empty."""
        tc = tempfile.mkdtemp()
        try:
            src_def = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", ".ai", "workflows", "definitions",
            )
            dst_def = os.path.join(tc, ".ai", "workflows", "definitions")
            if os.path.isdir(src_def):
                shutil.copytree(src_def, dst_def)

            # Start at create_roadmap phase (which has exit_criteria: roadmap_item_created)
            # We'll set it to a phase with just the evidence_keys
            run_workflow(
                tc, "start",
                subject_type="spec_change",
                subject_id="evk-ok",
            )
            state = load_json(tc, ".ai/workflows/runs/current.json")
            active = load_json(tc, f".ai/workflows/runs/active/{state['run_id']}/run.json")
            active_path = os.path.join(tc, ".ai", "workflows", "runs", "active", f"{state['run_id']}/run.json")

            # Use a phase with no exit_criteria (or just evidence_keys) so we can test evidence gate alone
            current = active["current_phase"]
            active["current_phase"] = current
            active["evidence"]["required_key"] = "some_value"
            with open(active_path, "w") as f:
                json.dump(active, f)

            # Modify workflow: add evidence_keys to current phase and clear exit_criteria
            wf_path = os.path.join(tc, ".ai", "workflows", "definitions", "sdlc-main.yaml")
            import yaml as _yaml
            with open(wf_path, "r") as f:
                wf = _yaml.safe_load(f)
            phase_def = wf["phases"][current]
            phase_def["evidence_keys"] = ["required_key"]
            phase_def["exit_criteria"] = []  # no exit criteria needed, just evidence check
            with open(wf_path, "w") as f:
                _yaml.dump(wf, f)

            rc, out, _ = run_workflow(tc, "complete-phase")
            self.assertEqual(rc, 0)
            data = json.loads(out)
            self.assertIn(current, data.get("completed_phases", []))
        finally:
            shutil.rmtree(tc, ignore_errors=True)

    def test_complete_phase_fails_falsy_json_evidence_values(self):
        """None and empty string evidence values are treated as empty evidence.
        Boolean False is a valid evidence value (e.g., post_hook_dirty_tree=False)."""
        # Only None and empty string are treated as missing/empty.
        # False, 0, [], {} are valid values that should be accepted.
        valid_cases = [
            ("bool_false", False),
            ("int_zero", 0),
            ("empty_list", []),
            ("empty_dict", {}),
        ]
        for key, value in valid_cases:
            with self.subTest(key=key, value=value):
                tc = tempfile.mkdtemp()
                try:
                    src_def = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "..", ".ai", "workflows", "definitions",
                    )
                    dst_def = os.path.join(tc, ".ai", "workflows", "definitions")
                    if os.path.isdir(src_def):
                        shutil.copytree(src_def, dst_def)

                    run_workflow(
                        tc, "start",
                        subject_type="spec_change",
                        subject_id=f"falsy-{key}",
                    )
                    state = load_json(tc, ".ai/workflows/runs/current.json")
                    active = load_json(tc, f".ai/workflows/runs/active/{state['run_id']}/run.json")
                    active_path = os.path.join(tc, ".ai", "workflows", "runs", "active", f"{state['run_id']}/run.json")
                    active["evidence"]["required_key"] = value
                    with open(active_path, "w") as f:
                        json.dump(active, f)

                    wf_path = os.path.join(tc, ".ai", "workflows", "definitions", "sdlc-main.yaml")
                    import yaml as _yaml
                    with open(wf_path, "r") as f:
                        wf = _yaml.safe_load(f)
                    wf["phases"][active["current_phase"]]["evidence_keys"] = ["required_key"]
                    wf["phases"][active["current_phase"]]["exit_criteria"] = []
                    with open(wf_path, "w") as f:
                        _yaml.dump(wf, f)

                    rc, _, _ = run_workflow(tc, "complete-phase")
                    self.assertEqual(rc, 0, f"expected success for {key}={value!r} — boolean/collection values are valid evidence")
                finally:
                    shutil.rmtree(tc, ignore_errors=True)


class TestResolveResolvedBlocks(FixtureBase):
    """Tests for resolve command clearing resolvable blocks."""

    def test_resolve_clears_missing_required_inputs_when_resolved(self):
        # Create a run and manually set a missing_required_inputs block
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-RES-001",
        )
        state = self._read_current_state()
        state["status"] = "blocked"
        state["block"] = {
            "type": "missing_required_inputs",
            "message": "missing: context.review_decision",
            "next_allowed": ["resolve", "block"],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "resolve")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # Should clear block and restore running since readiness is met
        self.assertIsNone(data.get("block"))
        self.assertEqual(data["status"], "running")


class TestCompletePhaseClearsBlock(FixtureBase):
    """Tests for complete-phase clearing exit_criteria_failed block on success."""

    def test_complete_phase_clears_exit_criteria_failed_block(self):
        # Create a run and set it to create_roadmap with exit_criteria_failed block
        self._make_roadmap_item("RM-CPB-001", "idea")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-CPB-001",
        )
        state = self._read_current_state()
        # Force to create_roadmap (where roadmap_item_created is the exit criteria)
        state["current_phase"] = "create_roadmap"
        state["status"] = "blocked"
        state["block"] = {
            "type": "exit_criteria_failed",
            "message": "exit criteria not satisfied",
            "next_allowed": ["resolve", "block"],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="roadmap_item_created",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIsNone(data.get("block"))
        self.assertEqual(data["status"], "running")
        self.assertIn("create_roadmap", data.get("completed_phases", []))


class TestBlockedRunNoAutoProgress(FixtureBase):
    """Blocked runs must not auto-progress; errors must explain why."""

    def test_done_not_at_done_phase_errors_no_block_written(self):
        self._make_openspec_change("d-blk")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="d-blk",
        )
        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)
        self.assertEqual(data["error"], "run is not in terminal phase")
        self.assertIn("current_phase", data)
        self.assertIn("hint", data)
        # Verify no side effects: run is not blocked or archived
        state = self._read_current_state()
        self.assertIsNone(state.get("block"))
        self.assertEqual(state["status"], "running")

    def test_advance_blocked_reports_block_details(self):
        self._make_openspec_change("adv-blk")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="adv-blk",
        )
        state = self._read_current_state()
        state["status"] = "blocked"
        state["block"] = {
            "type": "user_decision_required",
            "message": "approval needed",
            "next_allowed": ["resolve", "block", "advance"],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)
        self.assertEqual(data["error"], "run is blocked, cannot advance")
        self.assertIn("phase_complete", data)
        blk = data.get("block", {})
        self.assertEqual(blk.get("type"), "user_decision_required")
        self.assertEqual(blk.get("message"), "approval needed")
        self.assertIn("advance", blk.get("next_allowed", []))

    def test_resolve_unhandled_block_type_errors_with_explanation(self):
        self._make_openspec_change("res-blk")
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="res-blk",
        )
        state = self._read_current_state()
        state["status"] = "blocked"
        state["block"] = {
            "type": "user_decision_required",
            "message": "choose next action",
            "next_allowed": ["resolve", "block"],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "resolve")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)
        self.assertEqual(data["error"], "block cannot be automatically resolved")
        self.assertEqual(data["block_type"], "user_decision_required")
        self.assertIn("recommendation", data)


class TestDispatchHooks(FixtureBase):
    """Tests for before_dispatch and after_dispatch lifecycle hooks."""

    def _create_run(self):
        self._make_roadmap_item("RM-DH-001", "ready", openspec_change="agent-backed-lifecycle-wrapper-architecture")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-DH-001",
        )
        # Install valid single-default-slice implementation state so tests
        # that set current_phase to apply_change can dispatch implement/review
        # agents without the slicing assessment gate blocking them.
        # Use not_required status for backward-compat dispatch without --slice-id.
        state = self._read_current_state()
        state["implementation"] = _make_implementation_state(
            [_make_slice("default", status="pending")],
            assessment_status="not_required",
            decision="single_slice",
        )
        self._write_current_state(state)

    def test_before_dispatch_no_active_run_returns_blocker(self):
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(len(data["blockers"]), 1)
        self.assertEqual(data["blockers"][0]["reason"], "no_active_run")

    def test_before_dispatch_rejects_invalid_agent(self):
        self._create_run()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="garbage-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("invalid_agent", reasons)

    def test_before_dispatch_rejects_missing_flow_type(self):
        # Create a run, then remove flow_type from state
        self._create_run()
        state = self._read_current_state()
        state.pop("flow_type", None)
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("missing_flow_type", reasons)

    def test_before_dispatch_rejects_blocked_run(self):
        self._create_run()
        state = self._read_current_state()
        state["status"] = "blocked"
        state["block"] = {
            "type": "user_decision_required",
            "message": "choose next action",
            "next_allowed": ["resolve", "block"],
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("run_is_blocked", reasons)



    def test_before_dispatch_allows_plan_agent_for_apply_change_ambiguity(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["status"] = "blocked"
        state["block"] = {
            "type": "worker_failed",
            "message": "requirement ambiguity needs replanning",
            "next_allowed": ["dispatch_plan_agent"],
        }
        state.setdefault("evidence", {})["agent_result"] = {
            "agent": "implement-agent",
            "status": "failed",
            "phase": "apply_change",
            "slice_id": "slice-1",
            "flow_type": "spec-flow",
            "evidence": {},
            "blockers": [{
                "reason": "requirement_ambiguity",
                "message": "verification revealed missing requirement",
                "recommended_action": "dispatch_plan_agent",
            }],
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="plan-agent",
            slice_id="slice-1",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")

    def test_before_dispatch_allows_implement_agent_from_worker_failed_next_allowed_alias(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["status"] = "blocked"
        state["block"] = {
            "type": "worker_failed",
            "message": "review requested implementation fixes",
            "next_allowed": ["dispatch_implement_agent"],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")

    def test_before_dispatch_allows_implement_agent_from_latest_blocker_alias(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["status"] = "blocked"
        state["block"] = {
            "type": "worker_failed",
            "message": "implementation retry required",
            "next_allowed": ["resolve", "block"],
        }
        state.setdefault("evidence", {})["agent_result"] = {
            "agent": "review-agent",
            "status": "blocked",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {"review_complete": False},
            "blockers": [{
                "reason": "review_blocked",
                "message": "fix implementation issues",
                "recommended_action": "back_to_implement",
            }],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")

    def test_before_dispatch_rejects_next_allowed_agent_alias_for_unsupported_block_types(self):
        for block_type in (
            "missing_required_inputs",
            "exit_criteria_failed",
            "eval_failed",
            "user_decision_required",
        ):
            with self.subTest(block_type=block_type):
                self._create_run()
                state = self._read_current_state()
                state["current_phase"] = "apply_change"
                state["status"] = "blocked"
                state["block"] = {
                    "type": block_type,
                    "message": "dispatch-like aliases must not bypass the block",
                    "next_allowed": ["dispatch_implement_agent"],
                }
                self._write_current_state(state)

                rc, out, _ = run_workflow(
                    self.tmp, "before-dispatch",
                    agent="implement-agent",
                )

                self.assertNotEqual(rc, 0)
                data = json.loads(out)
                reasons = [b["reason"] for b in data.get("blockers", [])]
                self.assertIn("run_is_blocked", reasons)

    def test_before_dispatch_rejects_latest_blocker_agent_alias_for_unsupported_block_types(self):
        cases = [
            ("exit_criteria_failed", {"recommended_action": "back_to_implement"}),
            ("eval_failed", {"recommended_next_action": "dispatch_implement_agent"}),
            ("user_decision_required", {"recommended_action": "dispatch_implement_agent"}),
        ]
        for block_type, blocker in cases:
            with self.subTest(block_type=block_type, blocker=blocker):
                self._create_run()
                state = self._read_current_state()
                state["current_phase"] = "apply_change"
                state["status"] = "blocked"
                state["block"] = {
                    "type": block_type,
                    "message": "latest blocker alias must not bypass the block",
                    "next_allowed": ["resolve", "block"],
                }
                state.setdefault("evidence", {})["agent_result"] = {
                    "agent": "review-agent",
                    "status": "blocked",
                    "phase": "apply_change",
                    "slice_id": "slice-1",
                    "flow_type": "lightweight-flow",
                    "evidence": {"review_complete": False},
                    "blockers": [{
                        "reason": "review_blocked",
                        "message": "implementation retry requested",
                        **blocker,
                    }],
                }
                self._write_current_state(state)

                rc, out, _ = run_workflow(
                    self.tmp, "before-dispatch",
                    agent="implement-agent",
                    slice_id="slice-1",
                )

                self.assertNotEqual(rc, 0)
                data = json.loads(out)
                reasons = [b["reason"] for b in data.get("blockers", [])]
                self.assertIn("run_is_blocked", reasons)

    def test_worker_failed_round_trip_routes_back_to_implement_agent(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        self._write_current_state(state)

        agent_result = json.dumps({
            "status": "failed",
            "evidence": {"focused_tests": [{"command": "pytest -k impl", "result": "fail"}]},
            "blockers": [{
                "reason": "test_failure",
                "message": "implementation fixes required",
                "recommended_action": "back_to_implement",
            }],
            "recommended_next_action": "back_to_implement",
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="default",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        transition = json.loads(out)
        self.assertEqual(transition["workflow_command"], "workflow.py block")

        rc, _, _ = run_workflow(
            self.tmp, "block",
            block_type=transition["workflow_args"]["block_type"],
            message=transition["workflow_args"]["message"],
            next_allowed=transition["workflow_args"]["next_allowed"],
        )
        self.assertEqual(rc, 0)

        state = self._read_current_state()
        self.assertEqual(state["block"]["next_allowed"], ["back_to_implement"])

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")

    def test_before_dispatch_allows_plan_agent_from_dispatch_plan_alias(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["status"] = "blocked"
        state["block"] = {
            "type": "worker_failed",
            "message": "requirements need replanning",
            "next_allowed": ["dispatch_plan_agent"],
        }
        state.setdefault("evidence", {})["agent_result"] = {
            "agent": "review-agent",
            "status": "blocked",
            "phase": "apply_change",
            "slice_id": "slice-plan",
            "flow_type": "spec-flow",
            "evidence": {"review_complete": False},
            "blockers": [{
                "reason": "review_blocked",
                "message": "replan required",
            }],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="plan-agent",
            slice_id="slice-plan",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")

    def test_before_dispatch_allows_roadmap_agent_for_blocked_roadmap_remediation(self):
        for block_type in ("hook_blocked", "domain_state_mismatch", "user_decision_required"):
            with self.subTest(block_type=block_type):
                self._create_run()
                state = self._read_current_state()
                state["current_phase"] = "apply_change"
                state["status"] = "blocked"
                state["block"] = {
                    "type": block_type,
                    "message": "roadmap item needs remediation",
                    "next_allowed": ["resolve", "record-evidence", "block"],
                    "route_to_agent": "roadmap-agent",
                    "remediation": "Use 'roadmap-agent' (sdlc-roadmap skill) to update the roadmap item state, then re-run complete-hook.",
                }
                self._write_current_state(state)

                rc, out, _ = run_workflow(
                    self.tmp, "before-dispatch",
                    agent="roadmap-agent",
                )

                self.assertEqual(rc, 0)
                data = json.loads(out)
                self.assertEqual(data["status"], "dispatched")

    def test_before_dispatch_hook_blocked_alias_does_not_reroute_implement_agent(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["status"] = "blocked"
        state["block"] = {
            "type": "hook_blocked",
            "message": "roadmap remediation is required before implementation can continue",
            "next_allowed": ["dispatch_implement_agent"],
            "route_to_agent": "review-agent",
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
        )

        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertEqual(data["status"], "blocked")
        self.assertIn("run_is_blocked", reasons)

    def test_before_dispatch_domain_state_mismatch_latest_alias_does_not_reroute_implement_agent(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["status"] = "blocked"
        state["block"] = {
            "type": "domain_state_mismatch",
            "message": "roadmap item state must be fixed before implementation can continue",
            "next_allowed": ["resolve", "block"],
            "route_to_agent": "review-agent",
        }
        state.setdefault("evidence", {})["agent_result"] = {
            "agent": "roadmap-agent",
            "status": "blocked",
            "phase": "apply_change",
            "slice_id": "slice-1",
            "flow_type": "spec-flow",
            "evidence": {"tasks_complete": False},
            "blockers": [{
                "reason": "roadmap_blocked",
                "message": "fix roadmap state before resuming implementation",
                "recommended_action": "back_to_implement",
            }],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-1",
        )

        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertEqual(data["status"], "blocked")
        self.assertIn("run_is_blocked", reasons)

    def test_roadmap_hook_block_round_trip_routes_back_to_roadmap_agent(self):
        change_id = "route-hook-roundtrip"
        item_id = "RM-RT-ROUNDTRIP"
        self._make_openspec_change(change_id)
        self._make_roadmap_item(item_id, "ready", openspec_change=change_id)
        self._write_current_state({
            "version": 1,
            "run_id": f"2026-06-20-{change_id}",
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "roadmap_item", "id": item_id},
            "context": {"change_id": change_id, "roadmap_item_id": item_id},
            "phase_readiness": {
                "phase": "apply_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": ["roadmap_apply_start_if_ready"],
            "completed_hooks": ["roadmap_status_ready_if_linked"],
            "completed_phases": ["create_change", "apply_change"],
            "gates": {},
            "evidence": {
                "roadmap_link": {
                    "count": 1,
                    "items": [{
                        "item_id": item_id,
                        "status": "ready",
                        "file": f".ai/roadmap/areas/area1/items/{item_id}.md",
                        "area": "area1",
                    }],
                },
            },
            "block": None,
            "updated_at": "2026-06-20T00:00:00",
            "flow_type": "spec-flow",
        })

        rc, out, _ = run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_apply_start_if_ready",
        )
        self.assertNotEqual(rc, 0)
        blocked_state = json.loads(out)
        self.assertEqual(blocked_state["block"]["type"], "domain_state_mismatch")
        self.assertEqual(blocked_state["block"]["route_to_agent"], "roadmap-agent")

        state = self._read_current_state()
        self.assertEqual(state["block"]["route_to_agent"], "roadmap-agent")

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="roadmap-agent",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")

    def test_before_dispatch_rejects_mismatched_agent_while_blocked(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state["status"] = "blocked"
        state["block"] = {
            "type": "worker_failed",
            "message": "review requested implementation fixes",
            "next_allowed": ["dispatch_implement_agent"],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="review-agent",
        )

        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("run_is_blocked", reasons)

    def test_before_dispatch_finish_agent_skips_blocked_check(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "archive_change"
        state["status"] = "blocked"
        state["block"] = {
            "type": "user_decision_required",
            "message": "choose next action",
            "next_allowed": ["resolve", "block"],
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="finish-agent",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")

    def test_before_dispatch_success_records_evidence(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")
        self.assertEqual(data["agent"], "implement-agent")
        self.assertEqual(data["recommended_next_action"], "execute_agent")

        state = self._read_current_state()
        agent_phase = state.get("evidence", {}).get("agent_phase", {})
        self.assertEqual(agent_phase["agent"], "implement-agent")
        self.assertEqual(agent_phase["slice_id"], "default")

    def test_before_dispatch_defaults_phase_from_state(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="review-agent",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        phase = data.get("phase", "")
        self.assertNotEqual(phase, "")

    def test_before_dispatch_supports_dash_and_underscore_agents(self):
        cases = [
            ("create_change", ["plan-agent", "plan_agent"]),
            ("apply_change", ["implement-agent", "implement_agent", "review-agent", "review_agent"]),
            ("archive_change", ["finish-agent", "finish_agent"]),
        ]
        for phase, agents in cases:
            for agent in agents:
                self._create_run()
                state = self._read_current_state()
                state["current_phase"] = phase
                self._write_current_state(state)
                kwargs = {"agent": agent}
                if agent in ("implement-agent", "implement_agent"):
                    kwargs["slice_id"] = "default"
                rc, out, _ = run_workflow(
                    self.tmp, "before-dispatch",
                    **kwargs,
                )
                self.assertEqual(rc, 0, f"Agent {agent} should be valid in {phase}")

    def test_before_dispatch_rejects_implement_agent_outside_apply_change(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("agent_not_allowed_for_phase", reasons)

    def test_before_dispatch_rejects_agent_not_allowed_for_phase(self):
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="dispatch-phase-test",
        )
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="review-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("agent_not_allowed_for_phase", reasons)

    def test_after_dispatch_no_active_run_returns_blocker(self):
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["blockers"][0]["reason"], "no_active_run")

    def test_after_dispatch_records_agent_result(self):
        self._create_run()
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k flow_type", "result": "pass"}]},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="test-slice-2",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["agent"], "implement-agent")
        self.assertEqual(data["workflow_command"], "")
        self.assertEqual(data["recommended_next_action"], "dispatch_review_agent")

    def test_after_dispatch_with_blockers_recommends_block(self):
        self._create_run()
        agent_result = json.dumps({
            "status": "failed",
            "evidence": {"focused_tests": [{"command": "pytest", "result": "fail"}]},
            "blockers": [{"reason": "test_failure", "message": "focused tests failed",
                          "recommended_action": "back_to_implement"}],
            "recommended_next_action": "back_to_implement",
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            slice_id="test-slice-3",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["workflow_command"], "workflow.py block")

        state = self._read_current_state()
        agent_result_evidence = state.get("evidence", {}).get("agent_result", {})
        self.assertEqual(agent_result_evidence["status"], "failed")



    def test_after_dispatch_failed_without_blockers_still_blocks(self):
        self._create_run()
        agent_result = json.dumps({
            "status": "failed",
            "evidence": {},
            "blockers": [],
            "recommended_next_action": "dispatch_review_agent",
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py block")
        self.assertEqual(data["recommended_next_action"], "resolve_failure")

    def test_after_dispatch_preserves_per_slice_history(self):
        self._create_run()
        first_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k a", "result": "pass"}]},
            "blockers": [],
            "recommended_next_action": "dispatch_review_agent",
        })
        second_result = json.dumps({
            "status": "failed",
            "evidence": {"focused_tests": [{"command": "pytest -k b", "result": "fail"}]},
            "blockers": [{"reason": "test_failure", "message": "slice b failed"}],
            "recommended_next_action": "back_to_implement",
        })

        rc, _, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="slice-a",
            value=first_result,
        )
        self.assertEqual(rc, 0)
        rc, _, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            slice_id="slice-b",
            value=second_result,
        )
        self.assertEqual(rc, 0)

        state = self._read_current_state()
        results = state.get("evidence", {}).get("agent_results", {})
        self.assertIn("slice-a", results)
        self.assertIn("slice-b", results)
        self.assertEqual(results["slice-a"]["implement-agent"]["status"], "success")
        self.assertEqual(results["slice-b"]["review-agent"]["status"], "failed")

    def test_after_dispatch_preserves_artifacts_in_transition(self):
        self._create_run()
        agent_result = json.dumps({
            "status": "success",
            "evidence": {},
            "blockers": [],
            "artifacts": {
                "handoff_path": ".ai/workflows/runs/run-1/handoffs/slice-a/implement-agent.md",
                "raw_log_paths": [{"path": ".ai/workflows/runs/run-1/logs/slice-a/implement-agent/pytest.log",
                                   "kind": "pytest", "command": "pytest -k flow_type", "result": "pass"}],
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("artifacts", data)
        self.assertIn("handoff_path", data["artifacts"])
        self.assertEqual(len(data["artifacts"]["raw_log_paths"]), 1)

    def test_before_dispatch_rejects_invalid_flow_type_value(self):
        self._create_run()
        state = self._read_current_state()
        state["flow_type"] = "bogus-flow"
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("invalid_flow_type", reasons)

    def test_after_dispatch_implement_agent_success_recommends_review(self):
        """implement-agent success recommends dispatch_review_agent (no default test-agent)."""
        self._create_run()
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k x", "result": "pass"}]},
            "blockers": [],
            "recommended_next_action": "continue",
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["agent"], "implement-agent")
        self.assertEqual(data["recommended_next_action"], "dispatch_review_agent")
        self.assertNotEqual(data["recommended_next_action"], "complete_phase")
        self.assertEqual(data["workflow_command"], "")

    def test_dispatch_hooks_only_write_under_workflows_runs(self):
        """Task 1.3b: before-dispatch and after-dispatch only write under .ai/workflows/runs/."""
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        self._write_current_state(state)

        original_files = set()
        for root_dir, dirs, files in os.walk(self.tmp):
            for f in files:
                original_files.add(os.path.join(root_dir, f))

        run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-1",
        )

        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k x", "result": "pass"}]},
            "blockers": [],
            "artifacts": {"handoff_path": ".ai/workflows/runs/run-1/handoff.md"},
        })
        run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="slice-1",
            value=agent_result,
        )

        new_files = set()
        for root_dir, dirs, files in os.walk(self.tmp):
            for f in files:
                new_files.add(os.path.join(root_dir, f))

        for nf in new_files - original_files:
            rel = os.path.relpath(nf, self.tmp)
            self.assertTrue(
                rel.startswith(".ai/workflows/runs/"),
                f"dispatch hooks wrote outside .ai/workflows/runs/: {rel}",
            )

    def test_after_dispatch_handles_non_json_value(self):
        self._create_run()
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            value="plain text result",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIsNotNone(data)

    def test_after_dispatch_blocks_success_missing_required_phase_evidence(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        self._write_current_state(state)

        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "plan_produced": True,
                "criteria_satisfied": "spec_artifacts_done",
            },
            "blockers": [],
            "artifacts": {
                "plan_path": ".ai/workflows/runs/active/run-1/plans/default/plan.md",
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            value=agent_result,
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["workflow_command"], "workflow.py block")
        self.assertEqual(data["recommended_next_action"], "resolve_failure")
        self.assertEqual(data["blockers"][0]["reason"], "missing_phase_evidence_keys")
        self.assertIn("spec_artifacts_done", data["blockers"][0]["message"])

    def test_after_dispatch_allows_success_without_criteria_satisfied_when_evidence_key_truthy(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        self._write_current_state(state)

        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "plan_produced": True,
                "spec_artifacts_done": True,
            },
            "blockers": [],
            "artifacts": {
                "plan_path": ".ai/workflows/runs/active/run-1/plans/default/plan.md",
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            value=agent_result,
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py complete-phase")
        self.assertEqual(data["blockers"], [])

    def test_after_dispatch_allows_success_when_phase_evidence_and_criteria_are_present(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        self._write_current_state(state)

        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "plan_produced": True,
                "spec_artifacts_done": True,
                "criteria_satisfied": "spec_artifacts_done",
            },
            "blockers": [],
            "artifacts": {
                "plan_path": ".ai/workflows/runs/active/run-1/plans/default/plan.md",
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            value=agent_result,
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py complete-phase")
        self.assertEqual(data["workflow_args"]["exit_criteria_satisfied"], "spec_artifacts_done")
        self.assertEqual(data["recommended_next_action"], "complete_phase")
        self.assertEqual(data["blockers"], [])

    def test_after_dispatch_review_success_uses_agent_evidence_for_apply_change(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        # Add prior successful implement-agent evidence for verification basis
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "success",
            "evidence": {
                "verification_passed": True,
                "regression_passed": True,
                "tdd_passed": True,
            },
        }
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py complete-phase")
        self.assertEqual(data["recommended_next_action"], "complete_phase")

    def test_after_dispatch_review_success_can_use_existing_apply_phase_evidence(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        state.setdefault("evidence", {}).update({
            "tasks_complete": True,
            "tdd_passed": True,
            "eval_passed_or_human_decision_recorded": True,
        })
        # Add prior successful implement-agent evidence for verification basis
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "success",
            "evidence": {
                "verification_passed": True,
                "regression_passed": True,
                "tdd_passed": True,
            },
        }
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py complete-phase")

    def test_after_dispatch_review_success_without_eval_key_still_blocks(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "criteria_satisfied": "tasks_complete,tdd_passed",
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["blockers"][0]["reason"], "missing_phase_evidence_keys")

    def test_after_dispatch_review_acceptance_can_finalize_eval_key_from_implement_agent_success(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "success",
            "evidence": {
                "verification_passed": True,
                "regression_passed": True,
                "tdd_passed": True,
            },
        }
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py complete-phase")

    def test_after_dispatch_review_acceptance_without_verification_basis_blocks(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
                "review_complete": True,
                "review_decision": "accepted",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        reasons = [blocker["reason"] for blocker in data["blockers"]]
        self.assertIn("missing_verification_basis", reasons)

    def test_after_dispatch_missing_apply_phase_evidence_persists_block_state(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
                "criteria_satisfied": "tasks_complete,tdd_passed",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py block")
        self.assertEqual(data["workflow_args"]["block_type"], "worker_failed")
        self.assertIn("missing_phase_evidence_keys", data["workflow_args"]["message"])

        persisted = self._read_current_state()
        self.assertEqual(persisted["status"], "blocked")
        self.assertEqual(persisted["block"]["type"], "worker_failed")
        self.assertIn("missing_phase_evidence_keys", persisted["block"]["message"])

    def test_after_dispatch_writes_review_handoff_history_copy(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        self._write_current_state(state)

        handoff_path = ".ai/workflows/runs/active/2026-07-03-demo-change/handoffs/default/review-agent.md"
        latest_abs = os.path.join(self.tmp, handoff_path)
        os.makedirs(os.path.dirname(latest_abs), exist_ok=True)
        with open(latest_abs, "w", encoding="utf-8") as f:
            f.write("# Review Agent Handoff\n\n## Status\n\nsuccess\n")

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
            },
            "artifacts": {"handoff_path": handoff_path},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, _, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, handoff_path)))

        history_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", "2026-07-03-demo-change", "handoffs", "default", "history")
        self.assertTrue(os.path.isdir(history_dir))
        history_files = os.listdir(history_dir)
        self.assertTrue(any(name.startswith("review-agent-") for name in history_files))

        copied = os.path.join(history_dir, history_files[0])
        with open(copied, encoding="utf-8") as f:
            self.assertIn("# Review Agent Handoff", f.read())

    # --- stale evidence overwrite on successful re-dispatch ---

    def test_after_dispatch_overwrites_stale_evidence_from_prior_failed_dispatch(self):
        """Phase evidence from a prior dispatch must be overwritten when a
        subsequent successful dispatch provides a new value.

        Regression: cmd_after_dispatch only copied evidence when the key was
        absent (ek not in evidence). A prior agent result that set
        spec_artifacts_done=false (simulating old-code stale evidence) was
        never overwritten by a later successful dispatch."""
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        # Simulate stale evidence left by a prior dispatch (as the old code did)
        state.setdefault("evidence", {})["spec_artifacts_done"] = False
        self._write_current_state(state)

        # Verify stale evidence is present
        state_before = self._read_current_state()
        self.assertEqual(
            state_before["evidence"].get("spec_artifacts_done"),
            False,
            "Stale evidence must be set to false before successful dispatch",
        )

        # Now a successful dispatch corrects it
        success_result = json.dumps({
            "status": "success",
            "evidence": {
                "spec_artifacts_done": True,
                "criteria_satisfied": "spec_artifacts_done",
            },
            "blockers": [],
        })
        rc, _, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            slice_id="success-slice",
            value=success_result,
        )
        self.assertEqual(rc, 0)
        state_after_success = self._read_current_state()
        # The key assertion: stale false must be overwritten to true
        self.assertEqual(
            state_after_success["evidence"].get("spec_artifacts_done"),
            True,
            "Successful dispatch must overwrite stale phase evidence "
            "(spec_artifacts_done was false from a prior dispatch but "
            "the successful dispatch provides true)",
        )

    # --- change_id synchronization from provider-created spec artifacts ---

    def test_after_dispatch_syncs_change_id_from_agent_evidence(self):
        """Successful agent result with evidence.change_id updates context.change_id."""
        # Start a run with original subject_id as the change_id
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="subagent-model-config",
        )
        state = self._read_current_state()
        self.assertEqual(state["context"]["change_id"], "subagent-model-config")

        # After-dispatch with agent result containing normalized change_id
        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "change_id": "centralize-subagent-model-config",
                "criteria_satisfied": "spec_artifacts_done",
                "spec_artifacts_done": True,
            },
            "blockers": [],
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)

        # Verify context.change_id was synchronized to the canonical value
        updated = self._read_current_state()
        self.assertEqual(
            updated["context"].get("change_id"),
            "centralize-subagent-model-config",
            "context.change_id should be synchronized from agent evidence",
        )

    def test_after_dispatch_does_not_overwrite_change_id_when_same(self):
        """When agent returns same change_id, context remains unchanged."""
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="same-change-id",
        )
        state = self._read_current_state()
        self.assertEqual(state["context"]["change_id"], "same-change-id")
        original_updated_at = state["updated_at"]

        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "change_id": "same-change-id",
                "criteria_satisfied": "spec_artifacts_done",
                "spec_artifacts_done": True,
            },
            "blockers": [],
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)

        updated = self._read_current_state()
        self.assertEqual(updated["context"]["change_id"], "same-change-id")

    def test_after_dispatch_does_not_update_change_id_on_failed_result(self):
        """Failed agent results should not update context.change_id."""
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="fail-change-test",
        )
        state = self._read_current_state()
        self.assertEqual(state["context"]["change_id"], "fail-change-test")

        agent_result = json.dumps({
            "status": "failed",
            "evidence": {
                "change_id": "should-not-update",
            },
            "blockers": [{"reason": "spec_creation_failed", "message": "error"}],
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)

        updated = self._read_current_state()
        self.assertEqual(
            updated["context"]["change_id"],
            "fail-change-test",
            "context.change_id must not change on failed agent results",
        )

    def test_after_dispatch_syncs_change_id_from_artifacts(self):
        """Successful agent result with artifacts.change_id updates context."""
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id="artifacts-change-id",
        )
        state = self._read_current_state()
        self.assertEqual(state["context"]["change_id"], "artifacts-change-id")

        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "criteria_satisfied": "spec_artifacts_done",
                "spec_artifacts_done": True,
            },
            "blockers": [],
            "artifacts": {
                "change_id": "canonical-artifacts-change-id",
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)

        updated = self._read_current_state()
        self.assertEqual(
            updated["context"].get("change_id"),
            "canonical-artifacts-change-id",
            "context.change_id should sync from artifacts.change_id",
        )


    # --- roadmap-agent after-dispatch (lifecycle hook worker) ---

    def test_after_dispatch_roadmap_agent_does_not_complete_phase(self):
        """roadmap-agent after-dispatch must NOT produce phase-completion blockers.

        roadmap-agent is a lifecycle hook worker, not a phase-completing
        phase worker. Its after-dispatch should point to hook completion
        flow, never to phase-level evidence validation or complete-phase.
        The critical bug: after-dispatch currently evaluates roadmap-agent
        results against phase evidence_keys (e.g. spec_artifacts_done for
        create_change) and blocks the agent — that validation must be
        skipped for hook workers.
        """
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        self._write_current_state(state)

        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "roadmap_hook_resolution": "ready",
            },
            "blockers": [],
            "recommended_next_action": "complete_hooks",
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="roadmap-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # Must NOT produce a blocker for missing phase evidence keys
        blocker_reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertNotIn(
            "missing_phase_evidence_keys", blocker_reasons,
            "roadmap-agent after-dispatch must not check phase evidence_keys",
        )
        # Must NOT produce a blocker for missing exit criteria
        self.assertNotIn(
            "missing_exit_criteria_satisfied", blocker_reasons,
            "roadmap-agent after-dispatch must not check phase exit_criteria",
        )
        # Recommended next action must be hook-related, not phase-completing
        self.assertNotEqual(
            data["recommended_next_action"], "complete_phase",
            "roadmap-agent after-dispatch must not recommend complete_phase",
        )

    def test_after_dispatch_roadmap_agent_skips_evidence_key_validation(self):
        """roadmap-agent success must NOT be validated against phase evidence_keys.

        Phase evidence_keys (e.g. spec_artifacts_done for create_change,
        tasks_complete for apply_change) are for phase-completing workers
        like plan-agent and implement-agent. roadmap-agent is a hook worker
        and does not produce phase-level evidence — missing those keys
        must not cause a blocker.
        """
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "create_change"
        self._write_current_state(state)

        # roadmap-agent success with NO phase-level evidence keys
        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "roadmap_hook_resolution": "ready",
            },
            "blockers": [],
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="roadmap-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # Must NOT block — roadmap-agent does not need to supply
        # spec_artifacts_done or any phase evidence key
        self.assertEqual(
            data["blockers"], [],
            "roadmap-agent success must not block on missing phase evidence keys",
        )
        self.assertEqual(data["status"], "success")

    def test_after_dispatch_roadmap_agent_success_signals_hook_completion(self):
        """roadmap-agent success after-dispatch returns clean hook-worker result.

        After roadmap-agent transitions a roadmap item, after-dispatch
        should return success without phase-related blockers and should
        signal hook-worker completion rather than routing to another
        lifecycle phase worker.
        """
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("pending_hooks", []).append("roadmap_apply_start_if_ready")
        self._write_current_state(state)

        agent_result = json.dumps({
            "status": "success",
            "evidence": {
                "roadmap_hook_resolution": "active",
            },
            "blockers": [],
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="roadmap-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        # No blockers from phase evidence or exit criteria validation
        self.assertEqual(
            data["blockers"], [],
            "roadmap-agent success must return empty blockers",
        )
        # Must not route to another lifecycle phase worker
        self.assertNotEqual(
            data["recommended_next_action"], "dispatch_review_agent",
            "roadmap-agent success must not route to review-agent",
        )
        self.assertNotEqual(
            data["recommended_next_action"], "dispatch_implement_agent",
            "roadmap-agent success must not route to implement-agent",
        )


class TestApplyChangeHandoffHistory(FixtureBase):
    """Tests for handoff history preservation for all apply_change worker results."""

    def test_after_dispatch_preserves_handoff_history_for_failed_implement_agent(self):
        """Failed implement-agent with handoff_path must preserve history copy."""
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        self._write_current_state(state)

        run_id = state["run_id"]
        handoff_path = f".ai/workflows/runs/active/{run_id}/handoffs/default/implement-agent.md"
        latest_abs = os.path.join(self.tmp, handoff_path)
        os.makedirs(os.path.dirname(latest_abs), exist_ok=True)
        with open(latest_abs, "w", encoding="utf-8") as f:
            f.write("# Implement Agent Handoff\n\n## Status\n\nfailed\n")

        result = {
            "status": "failed",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {},
            "artifacts": {"handoff_path": handoff_path},
            "blockers": [{"reason": "implementation_failed", "message": "error"}],
            "recommended_next_action": "resolve_failure",
        }

        rc, _, _ = run_workflow(self.tmp, "after-dispatch", agent="implement-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)

        history_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id, "handoffs", "default", "history")
        self.assertTrue(os.path.isdir(history_dir), "history directory must exist for failed implement-agent")
        history_files = os.listdir(history_dir)
        self.assertTrue(any(name.startswith("implement-agent-") for name in history_files),
                        "history must contain implement-agent timestamped copy")

    def test_after_dispatch_preserves_handoff_history_for_blocked_review_agent(self):
        """Blocked review-agent with handoff_path must preserve history copy."""
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        self._write_current_state(state)

        run_id = state["run_id"]
        handoff_path = f".ai/workflows/runs/active/{run_id}/handoffs/default/review-agent.md"
        latest_abs = os.path.join(self.tmp, handoff_path)
        os.makedirs(os.path.dirname(latest_abs), exist_ok=True)
        with open(latest_abs, "w", encoding="utf-8") as f:
            f.write("# Review Agent Handoff\n\n## Status\n\nblocked\n")

        result = {
            "status": "blocked",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {},
            "artifacts": {"handoff_path": handoff_path},
            "blockers": [{"reason": "missing_verification_basis", "message": "no implement-agent evidence"}],
            "recommended_next_action": "resolve_failure",
        }

        rc, _, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)

        history_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id, "handoffs", "default", "history")
        self.assertTrue(os.path.isdir(history_dir), "history directory must exist for blocked review-agent")
        history_files = os.listdir(history_dir)
        self.assertTrue(any(name.startswith("review-agent-") for name in history_files),
                        "history must contain review-agent timestamped copy")

    def test_after_dispatch_preserves_handoff_history_for_failed_review_agent(self):
        """Failed review-agent with handoff_path must preserve history copy."""
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        # Provide implement-agent verification basis so the review-agent failure
        # is not confused with a missing_verification_basis block.
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "success",
            "evidence": {
                "verification_passed": True,
                "regression_passed": True,
                "tdd_passed": True,
            },
        }
        self._write_current_state(state)

        run_id = state["run_id"]
        handoff_path = f".ai/workflows/runs/active/{run_id}/handoffs/default/review-agent.md"
        latest_abs = os.path.join(self.tmp, handoff_path)
        os.makedirs(os.path.dirname(latest_abs), exist_ok=True)
        with open(latest_abs, "w", encoding="utf-8") as f:
            f.write("# Review Agent Handoff\n\n## Status\n\nfailed\n")

        result = {
            "status": "failed",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {},
            "artifacts": {"handoff_path": handoff_path},
            "blockers": [{"reason": "review_rejected", "message": "tests overfit"}],
            "recommended_next_action": "back_to_implement",
        }

        rc, _, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)

        history_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id, "handoffs", "default", "history")
        self.assertTrue(os.path.isdir(history_dir), "history directory must exist for failed review-agent")
        history_files = os.listdir(history_dir)
        self.assertTrue(any(name.startswith("review-agent-") for name in history_files),
                        "history must contain review-agent timestamped copy")


class TestApplyChangeHandoffMetadataValidation(FixtureBase):
    """Tests for handoff metadata mismatch blocking before history copy."""

    def _write_handoff(self, run_id, slice_id, agent, metadata_lines, body=""):
        handoff_path = f".ai/workflows/runs/active/{run_id}/handoffs/{slice_id}/{agent}.md"
        latest_abs = os.path.join(self.tmp, handoff_path)
        os.makedirs(os.path.dirname(latest_abs), exist_ok=True)
        content = f"# {agent.replace('-', ' ').title()} Handoff\n\n## Metadata\n\n"
        for line in metadata_lines:
            content += f"- {line}\n"
        if body:
            content += "\n" + body
        with open(latest_abs, "w", encoding="utf-8") as f:
            f.write(content)
        return handoff_path

    def test_after_dispatch_blocks_when_review_handoff_metadata_phase_mismatches(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        # Provide prior implement-agent verification basis so the only blocker
        # is the handoff metadata mismatch.
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "success",
            "evidence": {
                "verification_passed": True,
                "regression_passed": True,
                "tdd_passed": True,
            },
        }
        self._write_current_state(state)
        run_id = state["run_id"]

        handoff_path = self._write_handoff(
            run_id, "default", "review-agent",
            [
                "**Run ID**: demo-run",
                "**Slice ID**: default",
                "**Agent**: review-agent",
                "**Phase**: archive_change",
                "**Flow Type**: lightweight-flow",
                "**Status**: success",
            ],
        )

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
            },
            "artifacts": {"handoff_path": handoff_path},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }
        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py block",
                         f"expected workflow block, got stdout={out!r}")
        self.assertEqual(data["workflow_args"]["block_type"], "worker_failed")
        reasons = [b.get("reason") for b in data["blockers"]]
        self.assertIn("handoff_metadata_mismatch", reasons)

        # History copy must NOT be written when metadata mismatches
        history_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id, "handoffs", "default", "history")
        if os.path.isdir(history_dir):
            files = os.listdir(history_dir)
            self.assertFalse(
                any(name.startswith("review-agent-") for name in files),
                "history must NOT contain review-agent copy when metadata mismatches",
            )

    def test_after_dispatch_blocks_when_handoff_metadata_agent_mismatches(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "success",
            "evidence": {
                "verification_passed": True,
                "regression_passed": True,
                "tdd_passed": True,
            },
        }
        self._write_current_state(state)
        run_id = state["run_id"]

        # Handoff metadata says agent=implement-agent, but dispatch agent=review-agent
        handoff_path = self._write_handoff(
            run_id, "default", "review-agent",
            [
                "**Run ID**: demo-run",
                "**Slice ID**: default",
                "**Agent**: implement-agent",
                "**Phase**: apply_change",
                "**Flow Type**: lightweight-flow",
                "**Status**: success",
            ],
        )

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
            },
            "artifacts": {"handoff_path": handoff_path},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }
        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        data = json.loads(out)
        self.assertEqual(data["workflow_command"], "workflow.py block")
        self.assertEqual(data["workflow_args"]["block_type"], "worker_failed")
        reasons = [b.get("reason") for b in data["blockers"]]
        self.assertIn("handoff_metadata_mismatch", reasons)

    def test_after_dispatch_writes_history_copy_when_metadata_matches(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "success",
            "evidence": {
                "verification_passed": True,
                "regression_passed": True,
                "tdd_passed": True,
            },
        }
        self._write_current_state(state)
        run_id = state["run_id"]
        flow_type = state.get("flow_type", "lightweight-flow")

        handoff_path = self._write_handoff(
            run_id, "default", "review-agent",
            [
                f"**Run ID**: {run_id}",
                "**Slice ID**: default",
                "**Agent**: review-agent",
                "**Phase**: apply_change",
                f"**Flow Type**: {flow_type}",
                "**Status**: success",
            ],
        )

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": flow_type,
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
            },
            "artifacts": {"handoff_path": handoff_path},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }
        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0, f"valid metadata should succeed, got stdout={out!r}")

        history_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id, "handoffs", "default", "history")
        self.assertTrue(os.path.isdir(history_dir), "history directory must exist for valid metadata")
        files = os.listdir(history_dir)
        self.assertTrue(any(name.startswith("review-agent-") for name in files),
                        "history must contain review-agent copy when metadata matches")


class TestApplyChangeVerificationBasis(FixtureBase):
    """Tests for verification-basis guard requiring prior implement-agent evidence."""

    def test_after_dispatch_review_claiming_verification_without_implement_agent_blocks(self):
        """Review-agent claiming verification_passed without prior implement-agent evidence must block."""
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        # No prior implement-agent result in agent_results
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        reasons = [blocker["reason"] for blocker in data["blockers"]]
        self.assertIn("missing_verification_basis", reasons,
                       "review-agent must not self-claim verification_passed without prior implement-agent evidence")

    def test_after_dispatch_review_with_failed_implement_agent_still_blocks(self):
        """Review-agent with failed implement-agent result must still block on verification basis."""
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        # Add a FAILED implement-agent result
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "failed",
            "evidence": {
                "verification_passed": False,
                "regression_passed": False,
            },
        }
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        reasons = [blocker["reason"] for blocker in data["blockers"]]
        self.assertIn("missing_verification_basis", reasons,
                       "failed implement-agent must not satisfy verification basis")


def _import_workflow():
    """Import the workflow module for direct function testing."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("workflow", WORKFLOW_PY)
    wf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wf)
    return wf


class TestRunArtifactsUnify(FixtureBase):
    """Tests for directory-based run artifacts (run-artifacts-unify change)."""

    def test_active_path_returns_run_json_in_directory(self):
        """_active_path returns active/<run_id>/run.json"""
        wf = _import_workflow()
        result = wf._active_path(self.tmp, "test-run-123")
        expected = os.path.join(self.tmp, ".ai/workflows/runs/active/test-run-123/run.json")
        self.assertEqual(result, os.path.normpath(expected))

    def test_save_run_state_creates_directory_with_run_json(self):
        """save_run_state creates active/<run_id>/ directory and run.json inside"""
        wf = _import_workflow()
        run_id = "2026-06-29-test-save"
        state = {
            "version": 1, "run_id": run_id, "workflow": "sdlc-main",
            "flow_type": "spec-flow", "status": "running", "current_phase": "create_change",
            "primary_subject": {"type": "feature", "id": "test"},
            "context": {}, "phase_readiness": {"phase": "create_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": [],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "2026-01-01T00:00:00"
        }
        wf.save_run_state(self.tmp, state)
        run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
        run_json = os.path.join(run_dir, "run.json")
        self.assertTrue(os.path.isdir(run_dir), f"Expected directory {run_dir} to exist")
        self.assertTrue(os.path.isfile(run_json), f"Expected {run_json} to exist")
        old_path = os.path.join(self.tmp, ".ai/workflows/runs/active", f"{run_id}.json")
        self.assertFalse(os.path.isfile(old_path), f"Old flat file {old_path} should not exist")

    def test_finalize_run_to_history_moves_entire_directory(self):
        """_finalize_run_to_history moves entire active/<run_id>/ to history/<run_id>/"""
        wf = _import_workflow()
        run_id = "2026-06-29-test-move"
        run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
        os.makedirs(run_dir, exist_ok=True)
        state = {
            "version": 1, "run_id": run_id, "workflow": "sdlc-main",
            "flow_type": "spec-flow", "status": "running", "current_phase": "done",
            "primary_subject": {"type": "feature", "id": "test"},
            "context": {}, "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": ["done"],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "2026-01-01T00:00:00"
        }
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)
        os.makedirs(os.path.join(run_dir, "handoffs", "default"), exist_ok=True)
        with open(os.path.join(run_dir, "handoffs", "default", "plan-agent.md"), "w") as f:
            f.write("# Test handoff")
        with open(os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w") as f:
            json.dump({"run_id": run_id}, f)

        wf._finalize_run_to_history(self.tmp, state)

        self.assertFalse(os.path.exists(run_dir), "active directory should be removed")
        hist_dir = os.path.join(self.tmp, ".ai/workflows/runs/history", run_id)
        self.assertTrue(os.path.isdir(hist_dir), "history directory should exist")
        self.assertTrue(os.path.isfile(os.path.join(hist_dir, "run.json")), "history run.json should exist")
        self.assertTrue(os.path.isfile(os.path.join(hist_dir, "handoffs", "default", "plan-agent.md")), "handoff should be moved")
        with open(os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "r") as f:
            ptr = json.load(f)
        self.assertEqual(ptr, {}, "pointer should be cleared")

    def test_cmd_done_moves_entire_directory(self):
        """cmd_done moves entire active/<run_id>/ to history/<run_id>/ with artifacts"""
        run_id = "2026-06-29-test-done-dir"
        run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
        os.makedirs(run_dir, exist_ok=True)
        state = {
            "version": 1, "run_id": run_id, "workflow": "sdlc-main",
            "flow_type": "spec-flow", "status": "running", "current_phase": "done",
            "primary_subject": {"type": "feature", "id": "test"},
            "context": {}, "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": ["done"],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "2026-01-01T00:00:00"
        }
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)
        with open(os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w") as f:
            json.dump({"run_id": run_id}, f)

        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)

        self.assertFalse(os.path.exists(run_dir))
        hist_dir = os.path.join(self.tmp, ".ai/workflows/runs/history", run_id)
        self.assertTrue(os.path.isdir(hist_dir))
        self.assertTrue(os.path.isfile(os.path.join(hist_dir, "run.json")))

    def test_cancel_run_removes_entire_directory(self):
        """cmd_cancel_run removes entire active/<run_id>/ directory"""
        run_id = "2026-06-29-test-cancel"
        run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
        os.makedirs(run_dir, exist_ok=True)
        state = {
            "version": 1, "run_id": run_id, "workflow": "sdlc-main",
            "flow_type": "spec-flow", "status": "running", "current_phase": "create_change",
            "primary_subject": {"type": "roadmap_item", "id": "RM-CANCEL"},
            "context": {}, "phase_readiness": {"phase": "create_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": [],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "2026-01-01T00:00:00"
        }
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)
        os.makedirs(os.path.join(run_dir, "handoffs", "default"), exist_ok=True)
        with open(os.path.join(run_dir, "handoffs", "default", "test.md"), "w") as f:
            f.write("test")

        rc, out, _ = run_workflow(self.tmp, "cancel-run", subject_type="roadmap_item", subject_id="RM-CANCEL")
        data = json.loads(out)
        self.assertEqual(data["status"], "cancelled")
        self.assertFalse(os.path.exists(run_dir), "entire run directory should be removed")

    def test_list_active_runs_from_directories(self):
        """_list_active_runs discovers runs from subdirectories under active/"""
        wf = _import_workflow()
        run_id = "2026-06-29-test-list"
        run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
        os.makedirs(run_dir, exist_ok=True)
        state = {
            "version": 1, "run_id": run_id, "workflow": "sdlc-main",
            "flow_type": "spec-flow", "status": "running", "current_phase": "create_change",
            "primary_subject": {"type": "feature", "id": "test-list"},
            "context": {}, "phase_readiness": {"phase": "create_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": [],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "2026-01-01T00:00:00"
        }
        with open(os.path.join(run_dir, "run.json"), "w") as f:
            json.dump(state, f)

        active_runs = wf._list_active_runs(self.tmp)
        self.assertEqual(len(active_runs), 1)
        self.assertEqual(active_runs[0][0], run_id)

    def test_governance_check_reads_history_dir(self):
        """governance-check reads history/<run_id>/run.json (new-style only)"""
        run_id = "2026-06-29-test-gov"
        hist_dir = os.path.join(self.tmp, ".ai/workflows/runs/history", run_id)
        os.makedirs(hist_dir, exist_ok=True)
        state = {
            "version": 1, "run_id": run_id, "workflow": "sdlc-main",
            "flow_type": "spec-flow", "status": "done", "current_phase": "done",
            "primary_subject": {"type": "spec_change", "id": "arch-gov"},
            "context": {}, "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [], "completed_phases": ["done"],
            "gates": {}, "evidence": {}, "block": None, "updated_at": "2026-01-01T00:00:00"
        }
        with open(os.path.join(hist_dir, "run.json"), "w") as f:
            json.dump(state, f)

        rc, out, _ = run_workflow(self.tmp, "governance-check")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # Governance check returns {"block": bool, "findings": [...]}
        self.assertIsInstance(data, dict)
        self.assertIn("block", data)
        self.assertIn("findings", data)

    def test_legacy_migration_handoffs(self):
        """Legacy handoffs/<run_id>/ is migrated to active/<run_id>/handoffs/"""
        wf = _import_workflow()
        run_id = "2026-06-29-test-legacy"
        legacy_dir = os.path.join(self.tmp, ".ai/workflows/runs/handoffs", run_id, "default")
        os.makedirs(legacy_dir, exist_ok=True)
        with open(os.path.join(legacy_dir, "plan-agent.md"), "w") as f:
            f.write("# Legacy handoff")

        run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
        os.makedirs(run_dir, exist_ok=True)

        wf._migrate_legacy_artifacts(self.tmp, run_id)

        migrated = os.path.join(run_dir, "handoffs", "default", "plan-agent.md")
        self.assertTrue(os.path.isfile(migrated), f"Expected {migrated} to exist")
        self.assertFalse(os.path.exists(legacy_dir), "Legacy directory should be removed")

    def test_legacy_migration_logs(self):
        """Legacy logs/<run_id>/ is migrated to active/<run_id>/logs/"""
        wf = _import_workflow()
        run_id = "2026-06-29-test-legacy-logs"
        legacy_dir = os.path.join(self.tmp, ".ai/workflows/runs/logs", run_id, "default")
        os.makedirs(legacy_dir, exist_ok=True)
        with open(os.path.join(legacy_dir, "pytest.log"), "w") as f:
            f.write("test output")

        run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
        os.makedirs(run_dir, exist_ok=True)

        wf._migrate_legacy_artifacts(self.tmp, run_id)

        migrated = os.path.join(run_dir, "logs", "default", "pytest.log")
        self.assertTrue(os.path.isfile(migrated), f"Expected {migrated} to exist")
        self.assertFalse(os.path.exists(legacy_dir), "Legacy logs directory should be removed")

    def test_legacy_migration_idempotent(self):
        """Migration is safe to run twice without data loss"""
        wf = _import_workflow()
        run_id = "2026-06-29-test-idem"
        legacy_dir = os.path.join(self.tmp, ".ai/workflows/runs/handoffs", run_id, "default")
        os.makedirs(legacy_dir, exist_ok=True)
        with open(os.path.join(legacy_dir, "test.md"), "w") as f:
            f.write("content")

        run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
        os.makedirs(run_dir, exist_ok=True)

        wf._migrate_legacy_artifacts(self.tmp, run_id)
        wf._migrate_legacy_artifacts(self.tmp, run_id)

        migrated = os.path.join(run_dir, "handoffs", "default", "test.md")
        self.assertTrue(os.path.isfile(migrated))
        with open(migrated, "r") as f:
            self.assertEqual(f.read(), "content")

    def test_split_run_dir_migration_moves_plans_handoffs_and_logs(self):
        """Legacy runs/<run_id>/ artifacts are migrated into active/<run_id>/ directories."""
        wf = _import_workflow()
        run_id = "2026-06-30-test-split"
        split_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", run_id)
        os.makedirs(os.path.join(split_dir, "plans", "default"), exist_ok=True)
        os.makedirs(os.path.join(split_dir, "handoffs", "default"), exist_ok=True)
        os.makedirs(os.path.join(split_dir, "logs", "default", "plan-agent"), exist_ok=True)
        with open(os.path.join(split_dir, "plans", "default", "plan.md"), "w") as f:
            f.write("# Plan")
        with open(os.path.join(split_dir, "handoffs", "default", "plan-agent.md"), "w") as f:
            f.write("# Handoff")
        with open(os.path.join(split_dir, "logs", "default", "plan-agent", "plan.log"), "w") as f:
            f.write("log")

        run_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id)
        os.makedirs(run_dir, exist_ok=True)

        wf._migrate_legacy_artifacts(self.tmp, run_id)

        self.assertTrue(os.path.isfile(os.path.join(run_dir, "plans", "default", "plan.md")))
        self.assertTrue(os.path.isfile(os.path.join(run_dir, "handoffs", "default", "plan-agent.md")))
        self.assertTrue(os.path.isfile(os.path.join(run_dir, "logs", "default", "plan-agent", "plan.log")))
        self.assertFalse(os.path.exists(split_dir), "split run directory should be removed after migration")

    def test_split_run_dir_migration_runs_even_with_existing_sentinel(self):
        """Split-directory migration is not skipped just because .migrated already exists."""
        wf = _import_workflow()
        run_id = "2026-06-30-test-sentinel"
        run_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id)
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, ".migrated"), "w") as f:
            f.write("existing")

        split_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", run_id)
        os.makedirs(os.path.join(split_dir, "plans", "default"), exist_ok=True)
        with open(os.path.join(split_dir, "plans", "default", "plan.md"), "w") as f:
            f.write("# Plan")

        wf._migrate_legacy_artifacts(self.tmp, run_id)

        self.assertTrue(os.path.isfile(os.path.join(run_dir, "plans", "default", "plan.md")))
        self.assertFalse(os.path.exists(split_dir), "split run directory should still migrate when sentinel exists")


class TestExitCriteriaEvidenceKeySatisfaction(FixtureBase):
    """Tests that _missing_exit_criteria accepts truthy evidence key values
    as satisfaction for matching exit criteria, in addition to criteria_satisfied string.

    Tests that verify _missing_exit_criteria in isolation use post_archive_actions,
    which defines exit_criteria=[pending_hooks_empty] but NO evidence_keys.  This
    means _missing_phase_evidence_keys returns [] (no keys to check) and
    _missing_exit_criteria actually runs — allowing direct assertion on the
    missing_exit_criteria_satisfied blocker reason.

    Tests that verify the integrated path (evidence_keys + exit_criteria together)
    use archive_change and apply_change, where both gates run sequentially.
    """

    def _start_post_archive_run(self, change_id="exit-criteria-demo"):
        """Start a workflow at post_archive_actions via an archived spec_change."""
        self._make_openspec_archive(change_id)
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id=change_id,
        )

    def test_exit_criteria_satisfied_by_evidence_key_value_without_string(self):
        """archive_change: agent provides archive_path_exists=True but omits it
        from criteria_satisfied.  Should pass because the truthy evidence key
        value satisfies the exit criterion (new behavior)."""
        self._make_roadmap_item("RM-EXIT-001", "ready", openspec_change="exit-criteria-evidence-key-satisfaction")
        run_workflow(self.tmp, "start", subject_type="roadmap_item", subject_id="RM-EXIT-001")
        state = self._read_current_state()
        state["current_phase"] = "archive_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "archive_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "archive_path_exists": True,
                "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="finish-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn(
            "missing_exit_criteria_satisfied",
            str(data.get("blockers", [])),
            "Truthy evidence key should satisfy exit criteria without string declaration",
        )

    def test_exit_criteria_satisfied_by_string_only(self):
        """post_archive_actions: agent provides criteria_satisfied string but no
        matching evidence key value.  Should pass (backward compatible).

        Uses post_archive_actions (no evidence_keys) so _missing_phase_evidence_keys
        does not short-circuit, isolating the string-only satisfaction path."""
        self._start_post_archive_run()

        result = {
            "status": "success",
            "phase": "post_archive_actions",
            "slice_id": "default",
            "flow_type": "spec-flow",
            "evidence": {
                "criteria_satisfied": "pending_hooks_empty",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="finish-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn(
            "missing_exit_criteria_satisfied",
            str(data.get("blockers", [])),
            "criteria_satisfied string should still work as before (backward compatible)",
        )

    def test_exit_criteria_missing_both_value_and_string_blocks(self):
        """post_archive_actions: agent provides neither evidence value nor string
        declaration.  Should block because cleanup evidence keys are missing.

        post_archive_actions now defines evidence_keys for cleanup evidence,
        so _missing_phase_evidence_keys blocks when cleanup evidence is absent."""
        self._start_post_archive_run()

        result = {
            "status": "success",
            "phase": "post_archive_actions",
            "slice_id": "default",
            "flow_type": "spec-flow",
            "evidence": {
                "criteria_satisfied": "",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="finish-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        blocker_reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertTrue(
            any(r in blocker_reasons for r in ("missing_phase_evidence_keys", "missing_exit_criteria_satisfied")),
            f"Missing cleanup evidence should block; got {blocker_reasons}",
        )

    def test_exit_criteria_evidence_key_falsy_does_not_satisfy(self):
        """post_archive_actions: agent returns cleanup_complete=False.
        Should block because a False cleanup_complete does not satisfy the
        exit criteria.

        post_archive_actions now defines evidence_keys including cleanup_complete.
        With the new contract, boolean False is a valid evidence value (e.g.,
        post_hook_dirty_tree=False means clean tree), but cleanup_complete=False
        means cleanup is not complete and should block via missing_exit_criteria_satisfied."""
        self._start_post_archive_run()

        result = {
            "status": "success",
            "phase": "post_archive_actions",
            "slice_id": "default",
            "flow_type": "spec-flow",
            "evidence": {
                "memory_sync_done": True,
                "roadmap_done_checked": True,
                "derived_artifacts_synced": True,
                "post_hook_dirty_tree": False,
                "cleanup_complete": False,
                "criteria_satisfied": "",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="finish-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        blocker_reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn(
            "missing_exit_criteria_satisfied",
            blocker_reasons,
            "cleanup_complete=False should not satisfy exit criteria",
        )

    def test_exit_criteria_apply_change_evidence_key_satisfies_without_string(self):
        """apply_change: agent provides tasks_complete=True but omits it from
        criteria_satisfied.  Should pass via evidence key value in aggregated
        phase_evidence_view."""
        self._make_roadmap_item("RM-EXIT-001", "ready", openspec_change="exit-criteria-evidence-key-satisfaction")
        run_workflow(self.tmp, "start", subject_type="roadmap_item", subject_id="RM-EXIT-001")
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "status": "success",
            "evidence": {
                "verification_passed": True,
                "regression_passed": True,
                "tdd_passed": True,
            },
        }
        self._write_current_state(state)

        result = {
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "tasks_complete": True,
                "tdd_passed": True,
                "eval_passed_or_human_decision_recorded": True,
                "review_complete": True,
                "verification_passed": True,
                "review_decision": "accepted",
                "criteria_satisfied": "eval_passed_or_human_decision_recorded",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        blocker_reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertNotIn(
            "missing_exit_criteria_satisfied",
            blocker_reasons,
            "Truthy evidence keys in phase_evidence_view should satisfy exit criteria",
        )

    def test_post_archive_actions_both_paths_satisfy(self):
        """post_archive_actions edge case (spec line 206): agent provides both
        pending_hooks_empty=True (truthy evidence key) AND
        criteria_satisfied="pending_hooks_empty" (string).  Both paths satisfy;
        no change in behavior."""
        self._start_post_archive_run()

        result = {
            "status": "success",
            "phase": "post_archive_actions",
            "slice_id": "default",
            "flow_type": "spec-flow",
            "evidence": {
                "pending_hooks_empty": True,
                "criteria_satisfied": "pending_hooks_empty",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="finish-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn(
            "missing_exit_criteria_satisfied",
            str(data.get("blockers", [])),
            "Both truthy evidence key and string should satisfy exit criteria",
        )

    def test_empty_criteria_satisfied_with_truthy_evidence_keys_passes(self):
        """Edge case (spec line 208): empty criteria_satisfied string with truthy
        evidence keys should pass via the evidence key value path.

        Uses post_archive_actions (no evidence_keys gate) so the truthy
        pending_hooks_empty value reaches _missing_exit_criteria, which must
        accept it despite the empty string."""
        self._start_post_archive_run()

        result = {
            "status": "success",
            "phase": "post_archive_actions",
            "slice_id": "default",
            "flow_type": "spec-flow",
            "evidence": {
                "pending_hooks_empty": True,
                "criteria_satisfied": "",
            },
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="finish-agent", value=json.dumps(result))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertNotIn(
            "missing_exit_criteria_satisfied",
            str(data.get("blockers", [])),
            "Empty criteria_satisfied with truthy evidence keys should pass via evidence key path",
        )


class TestExecutionContextAndRuntimeContext(FixtureBase):
    """Tests for execution_mode context storage, validation, record-context,
    before-dispatch runtime_context output, and after-dispatch slice fallback /
    artifact persistence.

    Covers Tasks 1-3 of the workflow-runtime-execution-context plan:
    - execution_mode defaults to main_checkout for legacy runs
    - main_checkout does not require worktree fields
    - worktree mode records and exposes worktree metadata
    - base_ref is not required in new outputs; base_branch/parent_ref preferred
    - before-dispatch emits runtime_context derived from state.context
    - after-dispatch slice fallback order: CLI > agent result > dispatch intent > change_id > default
    - after-dispatch persists artifacts under evidence.agent_result and agent_results[slice][agent]
    """

    def _create_apply_change_run(self, change_id="exec-ctx-demo"):
        self._make_roadmap_item("RM-EXEC-001", "ready", openspec_change=change_id)
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-EXEC-001",
        )
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        # Ensure context.change_id is set for runtime_context output.
        state.setdefault("context", {}).setdefault("change_id", change_id)
        # Install valid single-default-slice implementation state so dispatch
        # gates pass and the tests can focus on execution context behavior.
        # Use not_required for backward-compat dispatch without --slice-id.
        state["implementation"] = _make_implementation_state(
            [_make_slice("default", status="pending")],
            assessment_status="not_required",
            decision="single_slice",
        )
        state["status"] = "running"
        state["block"] = None
        self._write_current_state(state)

    # --- Task 1: execution_mode storage and validation ---

    def test_legacy_run_without_execution_mode_defaults_to_main_checkout(self):
        """A run state without execution_mode is interpreted as main_checkout."""
        self._create_apply_change_run()
        state = self._read_current_state()
        # Legacy run has no execution_mode
        state.get("context", {}).pop("execution_mode", None)
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # before-dispatch should expose runtime_context.execution_mode == main_checkout
        self.assertIn("runtime_context", data)
        self.assertEqual(data["runtime_context"]["execution_mode"], "main_checkout")

    def test_main_checkout_run_does_not_require_worktree_fields(self):
        """main_checkout mode runs without worktree_path or feature_branch."""
        self._create_apply_change_run()
        state = self._read_current_state()
        state.setdefault("context", {})["execution_mode"] = "main_checkout"
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["runtime_context"]["execution_mode"], "main_checkout")
        # worktree fields should be absent or empty in main_checkout mode
        rt = data["runtime_context"]
        self.assertFalse(rt.get("worktree_path"))
        self.assertFalse(rt.get("feature_branch"))

    def test_worktree_mode_records_and_exposes_all_fields(self):
        """worktree mode records control_root, worktree_path, base_branch,
        feature_branch, parent_ref and exposes them in runtime_context."""
        self._create_apply_change_run()
        state = self._read_current_state()
        state.setdefault("context", {}).update({
            "execution_mode": "worktree",
            "control_root": "/path/to/control",
            "worktree_path": "/path/to/control/.worktrees/exec-ctx-demo",
            "base_branch": "main",
            "feature_branch": "feature/exec-ctx-demo",
            "parent_ref": "abc123def456",
        })
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        rt = data["runtime_context"]
        self.assertEqual(rt["execution_mode"], "worktree")
        self.assertEqual(rt["control_root"], "/path/to/control")
        self.assertEqual(rt["worktree_path"], "/path/to/control/.worktrees/exec-ctx-demo")
        self.assertEqual(rt["base_branch"], "main")
        self.assertEqual(rt["feature_branch"], "feature/exec-ctx-demo")
        self.assertEqual(rt["parent_ref"], "abc123def456")

    def test_base_ref_not_required_in_new_outputs(self):
        """New outputs use base_branch and parent_ref; base_ref is not required."""
        self._create_apply_change_run()
        state = self._read_current_state()
        state.setdefault("context", {}).update({
            "execution_mode": "worktree",
            "control_root": "/ctrl",
            "worktree_path": "/ctrl/.worktrees/x",
            "base_branch": "main",
            "feature_branch": "feature/x",
            "parent_ref": "deadbeef",
        })
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        rt = data["runtime_context"]
        self.assertIn("base_branch", rt)
        self.assertIn("parent_ref", rt)
        # base_ref is not a canonical field in new runtime_context
        self.assertNotIn("base_ref", rt)

    def test_invalid_execution_mode_is_rejected(self):
        """An invalid execution_mode value should be rejected."""
        self._create_apply_change_run()
        state = self._read_current_state()
        state.setdefault("context", {})["execution_mode"] = "bogus_mode"
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b["reason"] for b in data.get("blockers", [])]
        self.assertIn("invalid_execution_mode", reasons)

    # --- Task 6: record-context validates mode-specific requirements ---

    def test_record_context_sets_execution_mode(self):
        """record-context can set execution_mode to main_checkout."""
        self._create_apply_change_run()
        rc, out, _ = run_workflow(
            self.tmp, "record-context",
            key="execution_mode",
            value="main_checkout",
        )
        self.assertEqual(rc, 0)
        state = self._read_current_state()
        self.assertEqual(state["context"]["execution_mode"], "main_checkout")

    def test_record_context_rejects_invalid_execution_mode(self):
        """record-context rejects an invalid execution_mode value."""
        self._create_apply_change_run()
        rc, out, _ = run_workflow(
            self.tmp, "record-context",
            key="execution_mode",
            value="bogus_mode",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)

    def test_record_context_worktree_mode_requires_worktree_fields(self):
        """Setting execution_mode=worktree via record-context requires worktree_path
        and feature_branch before the context change is committed."""
        self._create_apply_change_run()
        # Setting worktree mode without required fields should be rejected
        rc, out, _ = run_workflow(
            self.tmp, "record-context",
            key="execution_mode",
            value="worktree",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)

    # --- Task 2: before-dispatch runtime_context output ---

    def test_before_dispatch_includes_runtime_context_with_change_id(self):
        """before-dispatch output includes runtime_context with change_id."""
        self._create_apply_change_run()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("runtime_context", data)
        rt = data["runtime_context"]
        self.assertEqual(rt["execution_mode"], "main_checkout")
        self.assertIn("change_id", rt)
        self.assertEqual(rt["change_id"], "exec-ctx-demo")

    def test_before_dispatch_runtime_context_includes_parent_ref_when_recorded(self):
        """parent_ref appears in runtime_context when recorded; base_branch stays branch name."""
        self._create_apply_change_run()
        state = self._read_current_state()
        state.setdefault("context", {}).update({
            "execution_mode": "worktree",
            "control_root": "/ctrl",
            "worktree_path": "/ctrl/.worktrees/x",
            "base_branch": "main",
            "feature_branch": "feature/x",
            "parent_ref": "abc123",
        })
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        rt = data["runtime_context"]
        self.assertEqual(rt["parent_ref"], "abc123")
        self.assertEqual(rt["base_branch"], "main")

    # --- Task 3: after-dispatch slice fallback and artifact persistence ---

    def test_after_dispatch_slice_fallback_uses_agent_result_slice_id(self):
        """When CLI omits --slice-id but agent result includes slice_id,
        after-dispatch uses the agent result's slice_id (fallback order 2)."""
        self._create_apply_change_run()
        agent_result = json.dumps({
            "status": "success",
            "slice_id": "from-agent-result",
            "evidence": {"focused_tests": [{"command": "pytest -k x", "result": "pass"}]},
            "blockers": [],
            "artifacts": {"handoff_path": ".ai/workflows/runs/run-1/handoffs/from-agent-result/implement-agent.md"},
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["slice_id"], "from-agent-result")
        state = self._read_current_state()
        agent_results = state.get("evidence", {}).get("agent_results", {})
        self.assertIn("from-agent-result", agent_results)
        self.assertIn("implement-agent", agent_results["from-agent-result"])

    def test_after_dispatch_slice_fallback_uses_dispatch_intent_slice_id(self):
        """When neither CLI nor agent result include slice_id, after-dispatch
        uses the dispatch intent slice_id from state evidence (fallback order 3)."""
        self._create_apply_change_run()
        # Record a dispatch intent with a slice_id
        run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="default",
        )
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k x", "result": "pass"}]},
            "blockers": [],
            "artifacts": {"handoff_path": ".ai/workflows/runs/run-1/handoffs/default/implement-agent.md"},
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["slice_id"], "default")

    def test_after_dispatch_slice_fallback_uses_change_id(self):
        """When CLI, agent result, and dispatch intent all omit slice_id,
        after-dispatch uses context.change_id (fallback order 4)."""
        self._create_apply_change_run(change_id="ctx-change-id")
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k x", "result": "pass"}]},
            "blockers": [],
            "artifacts": {"handoff_path": ".ai/workflows/runs/run-1/handoffs/ctx-change-id/implement-agent.md"},
        })
        # No before-dispatch to set dispatch_intent slice_id
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["slice_id"], "ctx-change-id")

    def test_after_dispatch_persists_artifacts_under_agent_result(self):
        """after-dispatch persists artifacts under latest evidence.agent_result."""
        self._create_apply_change_run()
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k x", "result": "pass"}]},
            "blockers": [],
            "artifacts": {
                "handoff_path": ".ai/workflows/runs/run-1/handoffs/slice-art/implement-agent.md",
                "worktree_path": "/path/to/worktree",
                "repo_root": "/path/to/repo",
                "base_branch": "main",
                "parent_ref": "abc123",
                "feature_branch": "feature/x",
                "changed_files": [{"path": "src/x.py", "status": "modified"}],
                "diff_commands": ["git diff -- src/x.py"],
                "verification_commands": [{"command": "pytest", "scope": "full_regression", "result": "pass"}],
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="slice-art",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        state = self._read_current_state()
        latest = state.get("evidence", {}).get("agent_result", {})
        self.assertIn("artifacts", latest)
        arts = latest["artifacts"]
        self.assertEqual(arts["worktree_path"], "/path/to/worktree")
        self.assertEqual(arts["base_branch"], "main")
        self.assertEqual(arts["parent_ref"], "abc123")
        self.assertEqual(arts["feature_branch"], "feature/x")
        self.assertNotIn("base_ref", arts)

    def test_after_dispatch_persists_artifacts_under_agent_results_by_slice(self):
        """after-dispatch persists artifacts under evidence.agent_results[slice][agent]."""
        self._create_apply_change_run()
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k x", "result": "pass"}]},
            "blockers": [],
            "artifacts": {
                "handoff_path": ".ai/workflows/runs/run-1/handoffs/slice-by/implement-agent.md",
                "worktree_path": "/wt",
                "base_branch": "main",
                "parent_ref": "deadbeef",
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="slice-by",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        state = self._read_current_state()
        per_slice = state.get("evidence", {}).get("agent_results", {}).get("slice-by", {}).get("implement-agent", {})
        self.assertIn("artifacts", per_slice)
        self.assertEqual(per_slice["artifacts"]["base_branch"], "main")
        self.assertEqual(per_slice["artifacts"]["parent_ref"], "deadbeef")

    def test_after_dispatch_does_not_emit_base_ref_in_new_artifacts(self):
        """New agent artifact persistence must not rely on base_ref."""
        self._create_apply_change_run()
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k x", "result": "pass"}]},
            "blockers": [],
            "artifacts": {
                "handoff_path": ".ai/workflows/runs/run-1/handoffs/no-baseref/implement-agent.md",
                "base_branch": "main",
                "parent_ref": "abc123",
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="no-baseref",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        state = self._read_current_state()
        latest = state.get("evidence", {}).get("agent_result", {})
        arts = latest.get("artifacts", {})
        self.assertNotIn("base_ref", arts)


class TestTerminalEvidenceValidation(FixtureBase):
    """Tests for Option B terminal evidence validation (Task 4/9).

    Terminal commands (advance, done) must refuse to move active runs to history
    when required final lifecycle evidence is missing.  For archive_change /
    post_archive_actions completion, the relevant finish-agent result must be
    recorded in evidence.agent_results[slice][finish-agent] before terminal movement.
    """

    def _prepare_post_archive_done_state(self, change_id="terminal-evidence-demo"):
        """Prepare a run at post_archive_actions phase ready for done."""
        self._make_openspec_archive(change_id)
        run_workflow(
            self.tmp, "start",
            subject_type="spec_change",
            subject_id=change_id,
        )
        run_workflow(
            self.tmp, "complete-hook",
            hook="roadmap_done_if_relevant",
        )
        run_workflow(
            self.tmp, "complete-hook",
            hook="memory_sync",
            resolution="synced",
        )
        state = self._read_current_state()
        state["current_phase"] = "done"
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        state["status"] = "running"
        self._write_current_state(state)

    def _record_finish_agent_result(self, slice_id="default", status="success"):
        """Record a finish-agent result in agent_results via after-dispatch.

        Preserves the done phase state by saving and restoring current_phase
        around the after-dispatch call, since after-dispatch reads the phase
        from state when --phase is not provided.

        Also records the dispatch intent slice_id in ``evidence.agent_phase``
        to mirror what ``before-dispatch`` would set for the finish-agent
        dispatch, so terminal validation can resolve the relevant slice.
        """
        state = self._read_current_state()
        saved_phase = state.get("current_phase", "done")
        # Temporarily set phase to post_archive_actions for the after-dispatch.
        state["current_phase"] = "post_archive_actions"
        state["status"] = "running"
        state["block"] = None
        # Mirror before-dispatch: record the dispatch intent slice_id.
        state.setdefault("evidence", {}).setdefault("agent_phase", {})["slice_id"] = slice_id
        self._write_current_state(state)

        result = json.dumps({
            "status": status,
            "phase": "post_archive_actions",
            "slice_id": slice_id,
            "flow_type": "spec-flow",
            "evidence": {
                "memory_sync_done": True,
                "roadmap_done_checked": True,
                "derived_artifacts_synced": True,
                "post_hook_dirty_tree": False,
                "cleanup_complete": True,
                "pending_hooks_empty": True,
                "criteria_satisfied": "pending_hooks_empty,memory_sync_done,roadmap_done_checked,derived_artifacts_synced,post_hook_dirty_tree,cleanup_complete",
            },
            "blockers": [],
            "artifacts": {"handoff_path": ".ai/workflows/runs/run-1/handoffs/default/finish-agent.md"},
            "recommended_next_action": "complete_phase",
        })
        run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            slice_id=slice_id,
            value=result,
        )

        # Restore the done phase for terminal commands.
        state = self._read_current_state()
        state["current_phase"] = saved_phase
        state["status"] = "running"
        state["block"] = None
        self._write_current_state(state)

    def test_done_refuses_terminal_move_without_finish_agent_evidence(self):
        """done must refuse to move the run to history when finish-agent evidence
        is missing from agent_results."""
        self._prepare_post_archive_done_state()
        # No finish-agent after-dispatch recorded
        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)
        self.assertIn("finish-agent", str(data))
        # Active run must remain in place
        state = self._read_current_state()
        self.assertIsNotNone(state)
        self.assertNotEqual(state.get("status"), "done")

    def test_done_proceeds_when_finish_agent_evidence_present(self):
        """done can proceed when finish-agent evidence is present in agent_results."""
        self._prepare_post_archive_done_state()
        self._record_finish_agent_result()

        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")

    def test_advance_refuses_terminal_move_without_finish_agent_evidence(self):
        """advance to done must refuse terminal movement when finish-agent
        evidence is missing."""
        self._prepare_post_archive_done_state()
        # Set up so advance will move to done (current_phase post_archive_actions
        # is terminal).  Mark the phase complete so advance reaches the
        # terminal movement path where finish-agent validation runs.
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["status"] = "running"
        state["pending_hooks"] = []
        state["block"] = None
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "advance")
        # advance to done should refuse because finish-agent evidence missing
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)
        self.assertIn("finish-agent", str(data))

    def test_advance_proceeds_when_finish_agent_evidence_present(self):
        """advance to done proceeds when finish-agent evidence is present."""
        self._prepare_post_archive_done_state()
        self._record_finish_agent_result()
        # Set up for advance: mark post_archive_actions complete.
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["status"] = "running"
        state["pending_hooks"] = []
        state["block"] = None
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")

    def test_terminal_validation_does_not_break_historical_runs(self):
        """Historical runs already in history without finish-agent evidence
        remain readable and are not re-validated."""
        self._prepare_post_archive_done_state()
        # Manually move a run to history without finish-agent evidence
        run_id = self._read_current_state()["run_id"]
        state = self._read_current_state()
        state["status"] = "done"
        state["current_phase"] = "done"
        history_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history", run_id)
        os.makedirs(history_dir, exist_ok=True)
        with open(os.path.join(history_dir, "run.json"), "w") as f:
            json.dump(state, f)
        # Reading history should work (governance-check reads history)
        history = self._read_history(run_id)
        self.assertIsNotNone(history)
        self.assertEqual(history["status"], "done")

    def test_done_refuses_when_finish_agent_evidence_only_under_unrelated_slice(self):
        """Spec Decision 9: terminal movement requires the relevant finish-agent
        result.  A successful finish-agent result recorded only under an
        unrelated slice must NOT satisfy terminal validation.

        The relevant slice is the dispatch intent slice
        (``evidence.agent_phase.slice_id``), which records the slice under which
        finish-agent was dispatched.  When finish-agent success exists only under
        a different slice, ``done`` must refuse terminal movement.
        """
        self._prepare_post_archive_done_state()
        # Record finish-agent success under an unrelated slice.
        self._record_finish_agent_result(slice_id="unrelated-slice")
        # Set the dispatch intent slice_id to the expected/relevant slice so
        # the unrelated-slice evidence does not satisfy validation.
        state = self._read_current_state()
        state.setdefault("evidence", {}).setdefault("agent_phase", {})["slice_id"] = "relevant-slice"
        state["current_phase"] = "done"
        state["status"] = "running"
        state["block"] = None
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("error", data)
        self.assertIn("finish-agent", str(data))
        # Active run must remain in place
        state = self._read_current_state()
        self.assertIsNotNone(state)
        self.assertNotEqual(state.get("status"), "done")

    def test_advance_accepts_default_finish_agent_evidence_when_no_dispatch_slice(self):
        """Unsliced lifecycle runs record finish-agent results under default.

        If no dispatch-intent slice is present, terminal validation must not
        reinterpret context.change_id as the required slice.
        """
        change_id = "terminal-default-slice"
        self._prepare_post_archive_done_state(change_id=change_id)
        self._record_finish_agent_result(slice_id="default")

        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["status"] = "running"
        state["pending_hooks"] = []
        state["block"] = None
        state.setdefault("evidence", {}).setdefault("agent_phase", {}).pop("slice_id", None)
        state["context"]["change_id"] = change_id
        state["completed_phases"] = [
            "input", "load_memory", "brainstorm", "decide_intent",
            "create_change", "apply_change", "archive_change",
            "post_archive_actions",
        ]
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "advance")

        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["current_phase"], "done")

    def test_done_proceeds_when_finish_agent_evidence_under_relevant_slice(self):
        """When finish-agent success is recorded under the dispatch-intent
        (relevant) slice, terminal movement proceeds even if an unrelated slice
        also has stale evidence."""
        self._prepare_post_archive_done_state()
        # Record finish-agent success under the relevant slice.
        self._record_finish_agent_result(slice_id="relevant-slice")
        state = self._read_current_state()
        state.setdefault("evidence", {}).setdefault("agent_phase", {})["slice_id"] = "relevant-slice"
        state["current_phase"] = "done"
        state["status"] = "running"
        state["block"] = None
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")


class TestBranchFinishDecisionGate(FixtureBase):
    """Tests for the branch_finish_decision gate (Spec Decision 1-3).

    When a run has implementation changes on a feature branch or worktree,
    finish-agent must require an explicit branch_finish_decision before
    branch-affecting actions.  The gate is enforced at before-dispatch for
    finish-agent during archive_change.
    """

    ALLOWED_DECISIONS = ("merge_local", "create_pr", "keep_branch", "discard")

    def _write_worktree_archive_ready_state(self, change_id="branch-gate"):
        """Write a run at archive_change phase with a worktree feature branch."""
        state = {
            "version": 1,
            "run_id": f"2026-07-09-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "worktree",
                "control_root": self.tmp,
                "worktree_path": os.path.join(self.tmp, "wt"),
                "feature_branch": f"feature/{change_id}",
                "base_branch": "main",
                "parent_ref": "abc123",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        self._write_current_state(state)
        return state

    def _write_main_checkout_archive_ready_state(self, change_id="main-no-gate"):
        """Write a main-checkout run at archive_change with no feature branch."""
        state = {
            "version": 1,
            "run_id": f"2026-07-09-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "main_checkout",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        self._write_current_state(state)
        return state

    def test_worktree_finish_blocked_without_branch_finish_decision(self):
        """A worktree/feature-branch finish cannot proceed without an explicit
        branch_finish_decision. before-dispatch for finish-agent must return a
        blocker with reason missing_branch_finish_decision."""
        self._write_worktree_archive_ready_state()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertIn("missing_branch_finish_decision", reasons)
        # recommended_next_action should point to user branch decision
        self.assertEqual(
            data.get("recommended_next_action"),
            "ask_user_branch_finish_decision",
        )

    def test_missing_decision_blocker_message_and_action(self):
        """The missing_branch_finish_decision blocker must carry the message
        and recommended_action per the spec."""
        self._write_worktree_archive_ready_state()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="finish-agent",
            phase="archive_change",
        )
        data = json.loads(out)
        blockers = data.get("blockers", [])
        branch_blockers = [
            b for b in blockers
            if b.get("reason") == "missing_branch_finish_decision"
        ]
        self.assertTrue(branch_blockers, "missing_branch_finish_decision blocker not emitted")
        b = branch_blockers[0]
        self.assertIn("branch_finish_decision", b.get("message", ""))
        self.assertEqual(
            b.get("recommended_action"),
            "ask_user_branch_finish_decision",
        )

    def test_allowed_branch_finish_decisions(self):
        """Each allowed decision value, when recorded in context, must allow
        finish-agent before-dispatch to proceed."""
        for decision in self.ALLOWED_DECISIONS:
            self._write_worktree_archive_ready_state(change_id=f"allowed-{decision}")
            run_workflow(
                self.tmp, "record-context",
                key="branch_finish_decision",
                value=decision,
            )
            rc, out, _ = run_workflow(
                self.tmp, "before-dispatch",
                agent="finish-agent",
                phase="archive_change",
                slice_id="default",
            )
            self.assertEqual(rc, 0, f"decision {decision} should be allowed")
            data = json.loads(out)
            self.assertEqual(data["status"], "dispatched")
            reasons = [b.get("reason") for b in data.get("blockers", [])]
            self.assertNotIn("missing_branch_finish_decision", reasons)

    def test_invalid_branch_finish_decision_blocked(self):
        """An invalid branch_finish_decision value must be rejected."""
        self._write_worktree_archive_ready_state()
        run_workflow(
            self.tmp, "record-context",
            key="branch_finish_decision",
            value="merge_into_dev",
        )
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="finish-agent",
            phase="archive_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertIn("invalid_branch_finish_decision", reasons)

    def test_no_silent_default_branch_action(self):
        """No default branch finish action is silently selected. An empty
        branch_finish_decision context must block (not default to keep_branch)."""
        self._write_worktree_archive_ready_state()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="finish-agent",
            phase="archive_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertIn("missing_branch_finish_decision", reasons)

    def test_main_checkout_without_feature_branch_does_not_require_gate(self):
        """Main-checkout mode without a feature branch does not require the
        branch_finish_decision gate by default."""
        self._write_main_checkout_archive_ready_state()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertNotIn("missing_branch_finish_decision", reasons)

    def test_main_checkout_with_feature_branch_requires_gate(self):
        """If context.feature_branch is recorded, the gate is required even
        when execution_mode is main_checkout."""
        state = self._write_main_checkout_archive_ready_state(change_id="main-with-branch")
        state["context"]["feature_branch"] = "feature/main-with-branch"
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="finish-agent",
            phase="archive_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertIn("missing_branch_finish_decision", reasons)


class TestBranchFinishDecisionBlockReconciliation(FixtureBase):
    """Tests for reconciling stale branch-decision blocks when a corrected
    valid branch_finish_decision is recorded (Spec: repair-workflow-decision-block-unlock).

    When a run is blocked due to a missing or invalid branch_finish_decision,
    recording a corrected valid decision through record-context SHALL
    reconcile the stale block: set status to running and clear the block,
    allowing normal guarded dispatch/advance to proceed.

    Unrelated blocks must be preserved. Invalid corrections must remain
    blocked. Main-checkout runs without a feature branch must not spuriously
    unblock.
    """

    ALLOWED_DECISIONS = ("merge_local", "create_pr", "keep_branch", "discard")

    def _write_worktree_blocked_state(
        self,
        change_id="repair-block",
        decision_block=None,
    ):
        """Write a worktree run at archive_change that is blocked by a
        branch-decision gate (missing or invalid decision)."""
        if decision_block is None:
            decision_block = {
                "type": "user_decision_required",
                "message": (
                    "finish requires explicit branch_finish_decision before "
                    "branch-affecting actions"
                ),
                "next_allowed": ["ask_user_branch_finish_decision"],
            }
        state = {
            "version": 1,
            "run_id": f"2026-07-11-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "blocked",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "worktree",
                "control_root": self.tmp,
                "worktree_path": os.path.join(self.tmp, "wt"),
                "feature_branch": f"feature/{change_id}",
                "base_branch": "main",
                "parent_ref": "abc123",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": decision_block,
            "updated_at": "2026-07-11T00:00:00",
        }
        self._write_current_state(state)
        return state

    def _write_main_checkout_blocked_state(self, change_id="main-nogate"):
        """Write a main-checkout run at archive_change blocked by an
        unrelated block (no feature branch, so no decision gate)."""
        unrelated_block = {
            "type": "worker_failed",
            "message": "agent failed",
            "next_allowed": ["resolve"],
        }
        state = {
            "version": 1,
            "run_id": f"2026-07-11-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "blocked",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "main_checkout",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": unrelated_block,
            "updated_at": "2026-07-11T00:00:00",
        }
        self._write_current_state(state)
        return state

    # -- Task 1.1: missing decision -> valid decision clears block ----------

    def test_corrected_valid_branch_finish_decision_clears_missing_decision_block(self):
        """A run blocked by a missing branch_finish_decision must transition to
        running with block=None when a valid decision is recorded via
        record-context. Before the fix, record-context preserves status=blocked
        and the block unchanged."""
        self._write_worktree_blocked_state(change_id="repair-missing")
        rc, out, _ = run_workflow(
            self.tmp, "record-context",
            key="branch_finish_decision",
            value="merge_local",
        )
        self.assertEqual(rc, 0)
        state = self._read_current_state()
        self.assertEqual(state["status"], "running")
        self.assertIsNone(state["block"])

    # -- Task 1.2: after reconciliation, guarded dispatch succeeds ----------

    def test_corrected_valid_branch_finish_decision_allows_dispatch(self):
        """After recording a valid decision that clears the missing-decision
        block, before-dispatch for finish-agent must succeed (status=dispatched)
        without run_is_blocked. Before the fix, the stale blocked-state guard
        rejects the run."""
        self._write_worktree_blocked_state(change_id="repair-dispatch")
        run_workflow(
            self.tmp, "record-context",
            key="branch_finish_decision",
            value="create_pr",
        )
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
        )
        self.assertEqual(rc, 0, f"dispatch should succeed after valid correction: {out}")
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertNotIn("run_is_blocked", reasons)

    # -- Task 1.3: invalid decision -> valid decision clears block ----------

    def test_corrected_valid_branch_finish_decision_clears_invalid_decision_block(self):
        """A run blocked by an invalid branch_finish_decision must transition to
        running with block=None when the decision is replaced with each
        representative allowed value. Before the fix, record-context preserves
        the blocked state."""
        for decision in self.ALLOWED_DECISIONS:
            change_id = f"repair-invalid-{decision}"
            # Block: invalid decision already in context
            block = {
                "type": "user_decision_required",
                "message": (
                    "branch_finish_decision 'merge_into_dev' is not one of: "
                    "['create_pr', 'discard', 'keep_branch', 'merge_local']"
                ),
                "next_allowed": ["ask_user_branch_finish_decision"],
            }
            state = self._write_worktree_blocked_state(change_id=change_id, decision_block=block)
            state["context"]["branch_finish_decision"] = "merge_into_dev"
            self._write_current_state(state)
            rc, out, _ = run_workflow(
                self.tmp, "record-context",
                key="branch_finish_decision",
                value=decision,
            )
            self.assertEqual(rc, 0)
            saved = self._read_current_state()
            self.assertEqual(
                saved["status"], "running",
                f"decision {decision}: status should be running",
            )
            self.assertIsNone(
                saved["block"],
                f"decision {decision}: block should be None",
            )
            # Guarded dispatch must succeed
            rc, out, _ = run_workflow(
                self.tmp, "before-dispatch",
                agent="finish-agent",
                phase="archive_change",
                slice_id="default",
            )
            self.assertEqual(rc, 0, f"dispatch failed for {decision}: {out}")
            data = json.loads(out)
            self.assertEqual(data["status"], "dispatched")

    # -- Task 1.4: invalid correction preserves block ----------------------

    def test_invalid_branch_finish_decision_correction_preserves_block(self):
        """Recording another invalid value must preserve the blocked status and
        the branch-decision block. This protects the no-silent-default contract."""
        block = {
            "type": "user_decision_required",
            "message": (
                "finish requires explicit branch_finish_decision before "
                "branch-affecting actions"
            ),
            "next_allowed": ["ask_user_branch_finish_decision"],
        }
        state = self._write_worktree_blocked_state(change_id="repair-still-invalid", decision_block=block)
        original_block = dict(state["block"])
        rc, out, _ = run_workflow(
            self.tmp, "record-context",
            key="branch_finish_decision",
            value="merge_into_dev",
        )
        self.assertEqual(rc, 0)
        saved = self._read_current_state()
        self.assertEqual(saved["status"], "blocked")
        self.assertIsNotNone(saved["block"])
        self.assertEqual(saved["block"]["type"], original_block["type"])
        self.assertEqual(saved["block"]["message"], original_block["message"])

    # -- Task 1.5: unrelated block preserved -------------------------------

    def test_valid_branch_finish_decision_preserves_unrelated_block(self):
        """Recording an allowed decision while a worker/hook/domain block is
        active must update the context but preserve the unrelated block
        byte-for-byte."""
        unrelated_blocks = [
            {
                "type": "worker_failed",
                "message": "agent failed",
                "next_allowed": ["resolve"],
            },
            {
                "type": "hook_blocked",
                "message": "pending hooks remain: ['memory_sync']",
                "next_allowed": ["resolve", "record-evidence", "block"],
            },
            {
                "type": "domain_state_mismatch",
                "message": "domain state out of sync",
                "next_allowed": ["resolve"],
            },
        ]
        for i, unrelated_block in enumerate(unrelated_blocks):
            change_id = f"repair-unrelated-{i}"
            state = self._write_worktree_blocked_state(change_id=change_id, decision_block=unrelated_block)
            original_block = dict(state["block"])
            rc, out, _ = run_workflow(
                self.tmp, "record-context",
                key="branch_finish_decision",
                value="keep_branch",
            )
            self.assertEqual(rc, 0)
            saved = self._read_current_state()
            self.assertEqual(saved["status"], "blocked")
            self.assertIsNotNone(saved["block"])
            self.assertEqual(saved["block"], original_block)
            # Context was still updated
            self.assertEqual(saved["context"]["branch_finish_decision"], "keep_branch")

    # -- Task 1.6: main checkout without gate does not spuriously unblock ----

    def test_branch_finish_decision_does_not_unblock_when_gate_not_required(self):
        """A main-checkout run without a feature branch does not require the
        branch-finish decision gate. Recording a branch_finish_decision while an
        unrelated block is active must preserve the unrelated blocked state."""
        self._write_main_checkout_blocked_state(change_id="repair-main-nogate")
        saved_before = self._read_current_state()
        original_block = dict(saved_before["block"])
        rc, out, _ = run_workflow(
            self.tmp, "record-context",
            key="branch_finish_decision",
            value="discard",
        )
        self.assertEqual(rc, 0)
        saved = self._read_current_state()
        self.assertEqual(saved["status"], "blocked")
        self.assertIsNotNone(saved["block"])
        self.assertEqual(saved["block"], original_block)
        self.assertEqual(saved["context"]["branch_finish_decision"], "discard")

    def test_unrelated_context_key_does_not_clear_branch_decision_block(self):
        """Recording a context key other than branch_finish_decision must not
        reconcile the branch-decision block, even if context.branch_finish_decision
        is already valid.  Without the key guard, any unrelated context write
        (e.g. recording change_id or execution_mode) would spuriously clear the
        block because _should_reconcile_branch_decision_block only inspected the
        tentative context, not the recorded key."""
        # Start with a run blocked by a missing branch_finish_decision.
        state = self._write_worktree_blocked_state(change_id="repair-unrelated-key")
        # Pre-populate a valid decision in context but leave the block intact.
        state["context"]["branch_finish_decision"] = "merge_local"
        self._write_current_state(state)
        original_block = dict(state["block"])
        # Record an unrelated key — must NOT trigger reconciliation.
        rc, out, _ = run_workflow(
            self.tmp, "record-context",
            key="change_id",
            value="repair-unrelated-key",
        )
        self.assertEqual(rc, 0)
        saved = self._read_current_state()
        self.assertEqual(saved["status"], "blocked")
        self.assertIsNotNone(saved["block"])
        self.assertEqual(saved["block"]["type"], original_block["type"])
        self.assertEqual(saved["block"]["message"], original_block["message"])


class TestLightweightFlowArchiveMoves(FixtureBase):
    """Tests for lightweight-flow Superpowers archive moves (Spec Decision 11).

    Completed lightweight-flow runs must move matching Superpowers plan and
    spec files into typed archive subdirectories.
    """

    def _make_superpowers_spec(self, filename, content="# Spec\n"):
        specs_dir = os.path.join(self.tmp, "docs", "superpowers", "specs")
        os.makedirs(specs_dir, exist_ok=True)
        path = os.path.join(specs_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _write_lightweight_archive_ready_state(
        self,
        change_id="lw-archive",
        with_plan=True,
        with_spec=True,
    ):
        """Write a lightweight-flow run at archive_change with design artifacts."""
        plan_filename = f"{change_id}.md"
        spec_filename = f"{change_id}.md"
        primary_design_path = None
        design_artifact_paths = []
        if with_plan:
            primary_design_path = f"docs/superpowers/plans/{plan_filename}"
            self._make_superpowers_plan(plan_filename, content=f"# Plan {change_id}\n")
        if with_spec:
            spec_path = f"docs/superpowers/specs/{spec_filename}"
            design_artifact_paths.append({"kind": "spec", "path": spec_path})
            self._make_superpowers_spec(spec_filename, content=f"# Spec {change_id}\n")
        if with_plan:
            design_artifact_paths.append({"kind": "plan", "path": primary_design_path})
        state = {
            "version": 1,
            "run_id": f"2026-07-09-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "main_checkout",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        if primary_design_path:
            state["context"]["primary_design_path"] = primary_design_path
        if design_artifact_paths:
            state["context"]["design_artifact_paths"] = design_artifact_paths
        self._write_current_state(state)
        return state

    def test_finish_agent_archive_moves_plan_to_archive_plans(self):
        """finish-agent archive execution moves plan files to
        docs/superpowers/archive/plans/."""
        self._write_lightweight_archive_ready_state(change_id="2026-07-05-move-plan")
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    "archived_design_artifact_paths": [
                        "docs/superpowers/archive/plans/2026-07-05-move-plan.md",
                        "docs/superpowers/archive/specs/2026-07-05-move-plan.md",
                    ],
                    "source_design_artifact_paths": [
                        "docs/superpowers/plans/2026-07-05-move-plan.md",
                        "docs/superpowers/specs/2026-07-05-move-plan.md",
                    ],
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        self.assertEqual(rc, 0)
        # The runtime should have performed the file moves described by finish-agent.
        archived_plan = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "plans",
            "2026-07-05-move-plan.md",
        )
        self.assertTrue(
            os.path.exists(archived_plan),
            "plan file was not moved to docs/superpowers/archive/plans/",
        )
        source_plan = os.path.join(
            self.tmp, "docs", "superpowers", "plans",
            "2026-07-05-move-plan.md",
        )
        self.assertFalse(
            os.path.exists(source_plan),
            "source plan file was not removed from docs/superpowers/plans/",
        )

    def test_finish_agent_archive_moves_spec_to_archive_specs(self):
        """finish-agent archive execution moves spec files to
        docs/superpowers/archive/specs/."""
        self._write_lightweight_archive_ready_state(change_id="2026-07-05-move-spec")
        run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    "archived_design_artifact_paths": [
                        "docs/superpowers/archive/plans/2026-07-05-move-spec.md",
                        "docs/superpowers/archive/specs/2026-07-05-move-spec.md",
                    ],
                    "source_design_artifact_paths": [
                        "docs/superpowers/plans/2026-07-05-move-spec.md",
                        "docs/superpowers/specs/2026-07-05-move-spec.md",
                    ],
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        archived_spec = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "specs",
            "2026-07-05-move-spec.md",
        )
        self.assertTrue(
            os.path.exists(archived_spec),
            "spec file was not moved to docs/superpowers/archive/specs/",
        )
        source_spec = os.path.join(
            self.tmp, "docs", "superpowers", "specs",
            "2026-07-05-move-spec.md",
        )
        self.assertFalse(
            os.path.exists(source_spec),
            "source spec file was not removed from docs/superpowers/specs/",
        )

    def test_archive_collision_not_silently_overwritten(self):
        """An existing destination file must not be overwritten silently."""
        change_id = "2026-07-05-collision"
        self._write_lightweight_archive_ready_state(change_id=change_id)
        # Pre-create the archive destination with different content.
        archive_dir = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "plans"
        )
        os.makedirs(archive_dir, exist_ok=True)
        existing = os.path.join(archive_dir, f"{change_id}.md")
        with open(existing, "w", encoding="utf-8") as f:
            f.write("# Existing archived plan\n")
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    "archived_design_artifact_paths": [
                        f"docs/superpowers/archive/plans/{change_id}.md",
                        f"docs/superpowers/archive/specs/{change_id}.md",
                    ],
                    "source_design_artifact_paths": [
                        f"docs/superpowers/plans/{change_id}.md",
                        f"docs/superpowers/specs/{change_id}.md",
                    ],
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        # The existing destination must be preserved (collision handled).
        with open(existing, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "# Existing archived plan\n")

    def test_missing_artifacts_returns_blocker(self):
        """When artifacts were expected but unavailable, finish must return a
        blocker rather than silently claiming archive success."""
        change_id = "2026-07-05-missing-artifacts"
        # Write state pointing at design paths that do not exist on disk.
        state = self._write_lightweight_archive_ready_state(change_id=change_id, with_plan=False, with_spec=False)
        state["context"]["primary_design_path"] = f"docs/superpowers/plans/{change_id}.md"
        state["context"]["design_artifact_paths"] = [
            {"kind": "plan", "path": f"docs/superpowers/plans/{change_id}.md"},
            {"kind": "spec", "path": f"docs/superpowers/specs/{change_id}.md"},
        ]
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "blocked",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": False,
                },
                "artifacts": {},
                "blockers": [
                    {"reason": "missing_lightweight_archive_artifacts",
                     "message": "Expected Superpowers design artifacts not found."},
                ],
                "recommended_next_action": "surface_error",
            }),
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")

    def test_finish_agent_success_with_missing_expected_artifacts_blocks(self):
        """When finish-agent reports success with archive_action_completed=true
        but the runtime archive move finds no expected artifacts on disk,
        after-dispatch must block with missing_lightweight_archive_artifacts
        and flip archive_action_completed to false (Spec Decision 11).

        This covers the runtime path the review blocker identified: the helper
        records skipped sources, but the caller must not discard that signal.
        """
        change_id = "2026-07-05-success-but-missing"
        # Point the runtime design contract at plan+spec paths that do NOT
        # exist on disk, but have finish-agent report success with the expected
        # archived/source paths.  finish-agent claims the move will happen;
        # the runtime must catch that the sources are absent.
        state = self._write_lightweight_archive_ready_state(
            change_id=change_id, with_plan=False, with_spec=False,
        )
        state["context"]["primary_design_path"] = (
            f"docs/superpowers/plans/{change_id}.md"
        )
        state["context"]["design_artifact_paths"] = [
            {"kind": "plan", "path": f"docs/superpowers/plans/{change_id}.md"},
            {"kind": "spec", "path": f"docs/superpowers/specs/{change_id}.md"},
        ]
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    "archived_design_artifact_paths": [
                        f"docs/superpowers/archive/plans/{change_id}.md",
                        f"docs/superpowers/archive/specs/{change_id}.md",
                    ],
                    "source_design_artifact_paths": [
                        f"docs/superpowers/plans/{change_id}.md",
                        f"docs/superpowers/specs/{change_id}.md",
                    ],
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        data = json.loads(out)
        # The runtime must block phase completion.  Per the after-dispatch
        # convention, transition["status"] mirrors the agent status, but the
        # workflow_command must be "block" and the state must be blocked.
        self.assertEqual(data["workflow_command"], "workflow.py block")
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertIn("missing_lightweight_archive_artifacts", reasons)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")
        # The runtime must have flipped the semantic evidence to false so
        # downstream phase completion cannot treat archive as completed.
        self.assertEqual(
            data["evidence"].get("archive_action_completed"), False,
        )

    def test_finish_agent_already_archived_keeps_archive_action_true(self):
        """When finish-agent has already moved plan/spec files to the archive
        directories (source absent, destination present), after-dispatch must
        treat this as idempotent success: archive_action_completed stays true
        and no missing_lightweight_archive_artifacts blocker is added.
        """
        change_id = "2026-07-05-already-archived"
        plan_filename = f"{change_id}.md"
        spec_filename = f"{change_id}.md"

        # Create archive destinations (finish-agent already moved them).
        archive_plans_dir = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "plans"
        )
        archive_specs_dir = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "specs"
        )
        os.makedirs(archive_plans_dir, exist_ok=True)
        os.makedirs(archive_specs_dir, exist_ok=True)
        with open(os.path.join(archive_plans_dir, plan_filename), "w") as f:
            f.write(f"# Plan {change_id}\n")
        with open(os.path.join(archive_specs_dir, spec_filename), "w") as f:
            f.write(f"# Spec {change_id}\n")

        # Do NOT create source files in docs/superpowers/plans/ or specs/.
        state = {
            "version": 1,
            "run_id": f"2026-07-09-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "main_checkout",
                "primary_design_path": f"docs/superpowers/plans/{plan_filename}",
                "design_artifact_paths": [
                    {"kind": "plan", "path": f"docs/superpowers/plans/{plan_filename}"},
                    {"kind": "spec", "path": f"docs/superpowers/specs/{spec_filename}"},
                ],
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    "archived_design_artifact_paths": [
                        f"docs/superpowers/archive/plans/{change_id}.md",
                        f"docs/superpowers/archive/specs/{change_id}.md",
                    ],
                    "source_design_artifact_paths": [
                        f"docs/superpowers/plans/{change_id}.md",
                        f"docs/superpowers/specs/{change_id}.md",
                    ],
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # archive_action_completed must remain true (no flip).
        self.assertEqual(
            data["evidence"].get("archive_action_completed"), True,
        )
        # No missing_lightweight_archive_artifacts blocker.
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertNotIn("missing_lightweight_archive_artifacts", reasons)
        # Run state must not be blocked.
        run_state = self._read_current_state()
        self.assertNotEqual(run_state["status"], "blocked")

    def test_deterministic_slug_date_fallback_moves_matching_spec(self):
        """When only primary_design_path points at a plan and a same-slug spec
        exists in docs/superpowers/specs/, the deterministic slug/date fallback
        must also move the matching spec (Spec Decision 11 / Task 8).
        """
        change_id = "2026-07-05-slug-fallback"
        # Only a plan is declared in the runtime contract; a matching spec
        # file with the same slug/date exists on disk but is NOT listed in
        # design_artifact_paths.
        plan_filename = f"{change_id}.md"
        spec_filename = f"{change_id}.md"
        self._make_superpowers_plan(plan_filename, content=f"# Plan {change_id}\n")
        self._make_superpowers_spec(spec_filename, content=f"# Spec {change_id}\n")
        state = {
            "version": 1,
            "run_id": f"2026-07-09-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "main_checkout",
                "primary_design_path": f"docs/superpowers/plans/{plan_filename}",
                # NOTE: no design_artifact_paths entry for the spec.
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    # finish-agent only reported the plan it knew about.
                    "archived_design_artifact_paths": [
                        f"docs/superpowers/archive/plans/{change_id}.md",
                    ],
                    "source_design_artifact_paths": [
                        f"docs/superpowers/plans/{change_id}.md",
                    ],
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        self.assertEqual(rc, 0)
        # The matching spec must have been moved by the deterministic fallback.
        archived_spec = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "specs",
            spec_filename,
        )
        self.assertTrue(
            os.path.exists(archived_spec),
            "matching spec was not moved by the slug/date fallback",
        )
        source_spec = os.path.join(
            self.tmp, "docs", "superpowers", "specs", spec_filename,
        )
        self.assertFalse(
            os.path.exists(source_spec),
            "matching spec was not removed from docs/superpowers/specs/",
        )
        # And the plan must still have been moved.
        archived_plan = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "plans",
            plan_filename,
        )
        self.assertTrue(os.path.exists(archived_plan))

    def test_absolute_runtime_design_artifact_paths_move_plan_and_spec(self):
        """When the runtime design contract provides absolute paths (as the
        governed workflow dispatch does), the archive helper must normalize
        them to repo-relative paths and still move both the plan and the spec
        into their typed archive dirs (Spec Decision 11 / review blocker).
        """
        change_id = "2026-07-05-abs-paths"
        plan_filename = f"{change_id}.md"
        spec_filename = f"{change_id}.md"
        self._make_superpowers_plan(plan_filename, content=f"# Plan {change_id}\n")
        self._make_superpowers_spec(spec_filename, content=f"# Spec {change_id}\n")
        # Governed runtime context supplies ABSOLUTE design artifact paths.
        abs_plan = os.path.join(self.tmp, "docs", "superpowers", "plans", plan_filename)
        abs_spec = os.path.join(self.tmp, "docs", "superpowers", "specs", spec_filename)
        state = {
            "version": 1,
            "run_id": f"2026-07-09-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "main_checkout",
                "primary_design_path": abs_plan,
                "design_artifact_paths": [
                    {"kind": "plan", "path": abs_plan},
                    {"kind": "spec", "path": abs_spec},
                ],
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    # finish-agent did not report explicit paths; runtime must
                    # derive them from the absolute runtime contract and move.
                    "archived_design_artifact_paths": [],
                    "source_design_artifact_paths": [],
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        self.assertEqual(rc, 0)
        # Both the plan and the spec must have been moved to archive dirs.
        archived_plan = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "plans", plan_filename,
        )
        archived_spec = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "specs", spec_filename,
        )
        self.assertTrue(
            os.path.exists(archived_plan),
            "plan from absolute primary_design_path was not moved to archive/plans/",
        )
        self.assertTrue(
            os.path.exists(archived_spec),
            "spec from absolute design_artifact_paths was not moved to archive/specs/",
        )
        # And the sources must no longer be in the active dirs.
        self.assertFalse(os.path.exists(abs_plan))
        self.assertFalse(os.path.exists(abs_spec))

    def test_absolute_runtime_path_missing_source_blocks(self):
        """When the runtime contract points at absolute Superpowers paths but
        those sources do not exist on disk, after-dispatch must block with
        missing_lightweight_archive_artifacts rather than silently claiming
        archive success (Spec Decision 11 / review blocker).

        Before the fix, absolute paths were dropped before classification, so
        no source was ever paired and the skipped-artifacts check never ran.
        """
        change_id = "2026-07-05-abs-missing"
        plan_filename = f"{change_id}.md"
        spec_filename = f"{change_id}.md"
        # Do NOT create the plan/spec files on disk.
        abs_plan = os.path.join(self.tmp, "docs", "superpowers", "plans", plan_filename)
        abs_spec = os.path.join(self.tmp, "docs", "superpowers", "specs", spec_filename)
        state = {
            "version": 1,
            "run_id": f"2026-07-09-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {
                "change_id": change_id,
                "execution_mode": "main_checkout",
                "primary_design_path": abs_plan,
                "design_artifact_paths": [
                    {"kind": "plan", "path": abs_plan},
                    {"kind": "spec", "path": abs_spec},
                ],
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    "archived_design_artifact_paths": [],
                    "source_design_artifact_paths": [],
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        data = json.loads(out)
        # The runtime must block because the expected sources are absent.
        self.assertEqual(data["workflow_command"], "workflow.py block")
        reasons = [b.get("reason") for b in data.get("blockers", [])]
        self.assertIn("missing_lightweight_archive_artifacts", reasons)
        self.assertEqual(
            data["evidence"].get("archive_action_completed"), False,
        )


class TestSemanticArchiveEvidence(FixtureBase):
    """Tests for semantic archive evidence (Spec Decision 10).

    New lightweight-flow runs must use archive_action_completed,
    archive_artifact_path, archive_not_required_reason, and
    archived_design_artifact_paths instead of misleading archive_path_exists.
    """

    def test_lightweight_flow_archive_success_accepts_semantic_evidence(self):
        """archive_change phase completion must accept semantic archive evidence
        (archive_action_completed) for lightweight-flow."""
        state = {
            "version": 1,
            "run_id": "2026-07-09-semantic-archive",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": "semantic-archive"},
            "context": {
                "change_id": "semantic-archive",
                "execution_mode": "main_checkout",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        self._write_current_state(state)
        # Record semantic archive evidence via after-dispatch.
        run_workflow(
            self.tmp, "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            slice_id="default",
            value=json.dumps({
                "agent": "finish-agent",
                "status": "success",
                "phase": "archive_change",
                "flow_type": "lightweight-flow",
                "slice_id": "default",
                "evidence": {
                    "archive_action_completed": True,
                    "archive_not_required_reason": "lightweight-flow",
                    "archive_artifact_path": None,
                    "archived_design_artifact_paths": [],
                    "source_design_artifact_paths": [],
                    "criteria_satisfied": "archive_action_completed",
                },
                "artifacts": {
                    "handoff_path": ".ai/workflows/runs/active/x/handoffs/default/finish-agent.md",
                    "worktree_path": self.tmp,
                    "feature_branch": "",
                    "branch_finish_action": "archive",
                },
                "blockers": [],
                "recommended_next_action": "complete_phase",
            }),
        )
        # complete-phase with semantic criteria should succeed.
        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="archive_action_completed",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("archive_change", data.get("completed_phases", []))

    def test_legacy_archive_path_exists_remains_readable(self):
        """Legacy archive_path_exists evidence remains accepted for backward
        compatibility during migration."""
        state = {
            "version": 1,
            "run_id": "2026-07-09-legacy-archive",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": "legacy-archive"},
            "context": {
                "change_id": "legacy-archive",
                "execution_mode": "main_checkout",
            },
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-09T00:00:00",
        }
        self._write_current_state(state)
        run_workflow(
            self.tmp, "record-evidence",
            key="archive_path_exists",
            value="true",
        )
        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("archive_change", data.get("completed_phases", []))


class TestFinalCommit(FixtureBase):
    """Tests for workflow.py final-commit command.

    final-commit runs after a workflow run reaches done. It stages
    only allowlisted governance artifacts and commits them, leaving
    unrelated dirty files unstaged.
    """

    def _init_git(self):
        subprocess.run(["git", "init"], cwd=self.tmp, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.tmp, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.tmp, capture_output=True, check=True)

    def _git_current_branch(self):
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.tmp, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()

    def _git_commit_baseline(self, msg="baseline"):
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=self.tmp, capture_output=True, check=True)

    def _git_status_porcelain(self):
        result = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=self.tmp, capture_output=True, text=True, check=True,
        )
        return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]

    def _git_show_name_only(self, commit="HEAD"):
        result = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:", commit],
            cwd=self.tmp, capture_output=True, text=True, check=True,
        )
        return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]

    def _make_done_history_run(self, run_id="2026-07-05-example"):
        """Create a done history run with run.json."""
        history_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id
        )
        os.makedirs(history_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "flow_type": "lightweight-flow",
            "primary_subject": {"type": "spec_change", "id": "example"},
            "context": {"change_id": "example", "execution_mode": "main_checkout"},
            "completed_phases": ["apply_change", "archive_change", "post_archive_actions"],
            "pending_hooks": [],
            "completed_hooks": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-05T00:00:00",
        }
        with open(os.path.join(history_dir, "run.json"), "w") as f:
            json.dump(state, f)
        return run_id

    def _make_tracked_active_run_files(self, run_id):
        active_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "active", run_id
        )
        handoff_dir = os.path.join(active_dir, "handoffs", "default")
        os.makedirs(handoff_dir, exist_ok=True)
        active_state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "post_archive_actions",
            "flow_type": "spec-flow",
            "primary_subject": {"type": "spec_change", "id": "example"},
            "context": {"change_id": "example"},
            "completed_phases": ["archive_change", "post_archive_actions"],
            "pending_hooks": [],
            "completed_hooks": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-12T00:00:00",
        }
        with open(os.path.join(active_dir, "run.json"), "w") as f:
            json.dump(active_state, f)
        with open(os.path.join(handoff_dir, "finish-agent.md"), "w") as f:
            f.write("# finish handoff\n")

    def test_final_commit_rejects_missing_run_id(self):
        rc, out, _ = run_workflow(self.tmp, "final-commit")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"], "missing_run_id")

    def test_final_commit_rejects_history_run_not_found(self):
        rc, out, _ = run_workflow(
            self.tmp, "final-commit", run_id="nonexistent-run"
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"], "history_run_not_found")

    def test_final_commit_rejects_not_done_run(self):
        run_id = "2026-07-05-active"
        history_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id
        )
        os.makedirs(history_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "status": "running",
            "current_phase": "apply_change",
            "completed_phases": [],
            "pending_hooks": [],
            "completed_hooks": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-05T00:00:00",
        }
        with open(os.path.join(history_dir, "run.json"), "w") as f:
            json.dump(state, f)
        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"], "run_not_done")

    def test_final_commit_rejects_run_id_mismatch(self):
        run_id = "2026-07-05-mismatch"
        history_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id
        )
        os.makedirs(history_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": "different-run-id",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "completed_phases": [],
            "pending_hooks": [],
            "completed_hooks": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-05T00:00:00",
        }
        with open(os.path.join(history_dir, "run.json"), "w") as f:
            json.dump(state, f)
        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"], "run_id_mismatch")

    def test_final_commit_noop_when_nothing_dirty(self):
        self._init_git()
        run_id = self._make_done_history_run()
        self._git_commit_baseline()
        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "noop")
        self.assertEqual(data["reason"], "nothing_to_commit")
        self.assertFalse(data["committed"])
        self.assertFalse(data["pushed"])
        self.assertEqual(data["staged_paths"], [])
        self.assertEqual(data["residual_dirty_paths"], [])

    def test_final_commit_commits_allowed_history_file(self):
        self._init_git()
        run_id = self._make_done_history_run()
        self._git_commit_baseline()
        # Modify the history run.json
        run_json_path = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id, "run.json"
        )
        with open(run_json_path, "w") as f:
            json.dump({"status": "done", "current_phase": "done", "run_id": run_id}, f)
        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["committed"])
        self.assertTrue(data["commit_id"])
        self.assertIn(
            f".ai/workflows/runs/history/{run_id}/run.json",
            data["staged_paths"],
        )
        # Git status should be clean
        status = self._git_status_porcelain()
        self.assertEqual(status, [])

    def test_final_commit_commits_target_active_run_deletions(self):
        self._init_git()
        run_id = "2026-07-12-active-delete"
        self._make_tracked_active_run_files(run_id)
        self._git_commit_baseline()

        active_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "active", run_id
        )
        shutil.rmtree(active_dir)
        self._make_done_history_run(run_id=run_id)

        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)

        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertIn(
            f".ai/workflows/runs/active/{run_id}/run.json",
            data["staged_paths"],
        )
        self.assertIn(
            f".ai/workflows/runs/active/{run_id}/handoffs/default/finish-agent.md",
            data["staged_paths"],
        )
        self.assertNotIn(
            f".ai/workflows/runs/active/{run_id}/run.json",
            data["residual_dirty_paths"],
        )

        commit_files = self._git_show_name_only()
        self.assertIn(
            f".ai/workflows/runs/active/{run_id}/run.json",
            commit_files,
        )
        self.assertIn(
            f".ai/workflows/runs/history/{run_id}/run.json",
            commit_files,
        )

        status = self._git_status_porcelain()
        self.assertFalse(
            any(f".ai/workflows/runs/active/{run_id}/" in s for s in status),
            status,
        )

    def test_final_commit_does_not_commit_target_active_run_non_deletions(self):
        self._init_git()
        run_id = "2026-07-12-active-dirty"
        self._make_done_history_run(run_id=run_id)
        self._git_commit_baseline()

        active_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "active", run_id
        )
        os.makedirs(active_dir, exist_ok=True)
        active_note = os.path.join(active_dir, "unexpected.txt")
        with open(active_note, "w") as f:
            f.write("unexpected active artifact\n")

        run_json_path = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id, "run.json"
        )
        with open(run_json_path, "w") as f:
            json.dump({"status": "done", "current_phase": "done", "run_id": run_id}, f)

        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)

        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertIn(
            f".ai/workflows/runs/active/{run_id}/unexpected.txt",
            data["residual_dirty_paths"],
        )
        self.assertNotIn(
            f".ai/workflows/runs/active/{run_id}/unexpected.txt",
            data["staged_paths"],
        )

        commit_files = self._git_show_name_only()
        self.assertNotIn(
            f".ai/workflows/runs/active/{run_id}/unexpected.txt",
            commit_files,
        )

    def test_final_commit_does_not_stage_unrelated_files(self):
        self._init_git()
        run_id = self._make_done_history_run()
        self._git_commit_baseline()
        # Modify history run.json
        run_json_path = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id, "run.json"
        )
        with open(run_json_path, "w") as f:
            json.dump({"status": "done", "current_phase": "done", "run_id": run_id}, f)
        # Create an unrelated dirty file
        src_dir = os.path.join(self.tmp, "src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "unrelated.py"), "w") as f:
            f.write("# unrelated change\n")
        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["committed"])
        # Unrelated file should be in residual_dirty_paths
        self.assertIn("src/unrelated.py", data["residual_dirty_paths"])
        # The commit should not include src/unrelated.py
        commit_files = self._git_show_name_only()
        self.assertNotIn("src/unrelated.py", commit_files)
        self.assertIn(
            f".ai/workflows/runs/history/{run_id}/run.json",
            commit_files,
        )
        # src/unrelated.py should still be dirty
        status = self._git_status_porcelain()
        self.assertTrue(any("src/unrelated.py" in s for s in status))

    def test_final_commit_does_not_commit_pre_staged_unrelated_file(self):
        """Regression: a pre-existing staged tracked file outside the
        allowlist must NOT be included in the final commit, and its staged
        index state must be preserved after final-commit returns.
        """
        self._init_git()
        run_id = self._make_done_history_run()
        # Create a tracked source file and commit it as baseline
        src_dir = os.path.join(self.tmp, "src")
        os.makedirs(src_dir, exist_ok=True)
        unrelated_path = os.path.join(src_dir, "unrelated.py")
        with open(unrelated_path, "w") as f:
            f.write("# original\n")
        self._git_commit_baseline()
        # Modify history run.json (allowlisted)
        run_json_path = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id, "run.json"
        )
        with open(run_json_path, "w") as f:
            json.dump({"status": "done", "current_phase": "done", "run_id": run_id}, f)
        # Pre-stage an unrelated tracked file modification BEFORE final-commit
        with open(unrelated_path, "w") as f:
            f.write("# modified by user\n")
        subprocess.run(
            ["git", "add", "--", "src/unrelated.py"],
            cwd=self.tmp, capture_output=True, check=True,
        )
        # Confirm it is staged before final-commit
        pre_status = self._git_status_porcelain()
        self.assertTrue(any("M  src/unrelated.py" in s for s in pre_status))
        # Run final-commit
        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["committed"])
        # The commit must NOT include the unrelated pre-staged file
        commit_files = self._git_show_name_only()
        self.assertNotIn("src/unrelated.py", commit_files)
        self.assertIn(
            f".ai/workflows/runs/history/{run_id}/run.json",
            commit_files,
        )
        # The unrelated file must still be staged (index state preserved)
        post_status = self._git_status_porcelain()
        self.assertTrue(
            any("M  src/unrelated.py" in s for s in post_status),
            f"src/unrelated.py staged state not preserved: {post_status}",
        )
        # It should appear in residual_dirty_paths
        self.assertIn("src/unrelated.py", data["residual_dirty_paths"])

    def test_final_commit_allowlist_scoped_to_specific_run_id(self):
        self._init_git()
        target_run = self._make_done_history_run(run_id="2026-07-05-target")
        other_run = self._make_done_history_run(run_id="2026-07-05-other")
        self._git_commit_baseline()
        # Modify both run.json files
        for rid in (target_run, other_run):
            run_json_path = os.path.join(
                self.tmp, ".ai", "workflows", "runs", "history", rid, "run.json"
            )
            with open(run_json_path, "w") as f:
                json.dump({"status": "done", "current_phase": "done", "run_id": rid}, f)
        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=target_run)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["committed"])
        # Target run should be staged
        self.assertIn(
            f".ai/workflows/runs/history/{target_run}/run.json",
            data["staged_paths"],
        )
        # Other run should NOT be staged
        self.assertNotIn(
            f".ai/workflows/runs/history/{other_run}/run.json",
            data["staged_paths"],
        )
        # Other run should appear in residual_dirty_paths
        self.assertIn(
            f".ai/workflows/runs/history/{other_run}/run.json",
            data["residual_dirty_paths"],
        )

    def test_final_commit_commits_superpowers_archive_artifacts(self):
        self._init_git()
        run_id = self._make_done_history_run()
        self._git_commit_baseline()
        # Create archived superpowers artifacts
        archive_plans_dir = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "plans"
        )
        os.makedirs(archive_plans_dir, exist_ok=True)
        with open(os.path.join(archive_plans_dir, "2026-07-05-example.md"), "w") as f:
            f.write("# Archived Plan\n")
        archive_specs_dir = os.path.join(
            self.tmp, "docs", "superpowers", "archive", "specs"
        )
        os.makedirs(archive_specs_dir, exist_ok=True)
        with open(os.path.join(archive_specs_dir, "2026-07-05-example.md"), "w") as f:
            f.write("# Archived Spec\n")
        # Also create an unrelated active plan
        active_plans_dir = os.path.join(
            self.tmp, "docs", "superpowers", "plans"
        )
        os.makedirs(active_plans_dir, exist_ok=True)
        with open(os.path.join(active_plans_dir, "2026-07-05-active.md"), "w") as f:
            f.write("# Active Plan\n")
        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["committed"])
        # Archive paths should be staged
        self.assertIn("docs/superpowers/archive/plans/2026-07-05-example.md", data["staged_paths"])
        self.assertIn("docs/superpowers/archive/specs/2026-07-05-example.md", data["staged_paths"])
        # Active plan path should NOT be staged
        self.assertNotIn("docs/superpowers/plans/2026-07-05-active.md", data["staged_paths"])
        self.assertIn("docs/superpowers/plans/2026-07-05-active.md", data["residual_dirty_paths"])

    def test_final_commit_push_after_successful_commit(self):
        self._init_git()
        run_id = self._make_done_history_run()
        self._git_commit_baseline()
        # Modify history run.json
        run_json_path = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id, "run.json"
        )
        with open(run_json_path, "w") as f:
            json.dump({"status": "done", "current_phase": "done", "run_id": run_id}, f)
        # Create a bare repo to push to
        bare_repo = os.path.join(os.path.dirname(self.tmp), f"bare-{run_id}")
        if os.path.exists(bare_repo):
            shutil.rmtree(bare_repo, ignore_errors=True)
        os.makedirs(bare_repo, exist_ok=True)
        subprocess.run(
            ["git", "init", "--bare", bare_repo],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", bare_repo],
            cwd=self.tmp, capture_output=True, check=True,
        )
        # Push the initial baseline so the remote has the branch
        branch = self._git_current_branch()
        subprocess.run(
            ["git", "push", "origin", branch],
            cwd=self.tmp, capture_output=True, check=True,
        )
        rc, out, _ = run_workflow(
            self.tmp, "final-commit", run_id=run_id, push=True
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["committed"])
        self.assertTrue(data["pushed"])

    def test_final_commit_push_not_invoked_on_noop(self):
        self._init_git()
        run_id = self._make_done_history_run()
        self._git_commit_baseline()
        # Nothing dirty — should noop
        rc, out, _ = run_workflow(
            self.tmp, "final-commit", run_id=run_id, push=True
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "noop")
        self.assertFalse(data["pushed"])

    def test_final_commit_push_failure_reports_committed_true_pushed_false(self):
        self._init_git()
        run_id = self._make_done_history_run()
        self._git_commit_baseline()
        # Modify history run.json
        run_json_path = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id, "run.json"
        )
        with open(run_json_path, "w") as f:
            json.dump({"status": "done", "current_phase": "done", "run_id": run_id}, f)
        # Set a remote URL that will fail to push (nonexistent)
        subprocess.run(
            ["git", "remote", "add", "origin", "/nonexistent/remote/path"],
            cwd=self.tmp, capture_output=True, check=True,
        )
        rc, out, _ = run_workflow(
            self.tmp, "final-commit", run_id=run_id, push=True
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "failed")
        self.assertTrue(data["committed"])
        self.assertFalse(data["pushed"])
        self.assertTrue(data["commit_id"])

    def test_final_commit_commits_target_active_run_rename_source(self):
        """Regression: active->history move reported by Git as a rename
        (R  active/... -> history/...) must surface BOTH the source
        deletion and the destination addition to final-commit. The
        parser previously kept only the destination, leaving the active
        source paths residual and the finalize tree dirty.
        """
        self._init_git()
        run_id = "2026-07-12-active-rename"
        self._make_tracked_active_run_files(run_id)
        self._git_commit_baseline()

        active_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "active", run_id
        )
        history_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id
        )
        os.makedirs(history_dir, exist_ok=True)

        # Move each tracked active file to the corresponding history path
        # using git mv so Git records rename entries in porcelain output.
        active_run_json = os.path.join(active_dir, "run.json")
        active_handoff = os.path.join(
            active_dir, "handoffs", "default", "finish-agent.md"
        )
        history_run_json = os.path.join(history_dir, "run.json")
        history_handoff_dir = os.path.join(
            history_dir, "handoffs", "default"
        )
        os.makedirs(history_handoff_dir, exist_ok=True)
        history_handoff = os.path.join(history_handoff_dir, "finish-agent.md")

        subprocess.run(
            ["git", "mv", active_run_json, history_run_json],
            cwd=self.tmp, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "mv", active_handoff, history_handoff],
            cwd=self.tmp, capture_output=True, check=True,
        )

        # Write the done history run.json (overwrites the moved file's
        # content with a valid done state so final-commit validation
        # passes).
        self._make_done_history_run(run_id=run_id)
        subprocess.run(
            ["git", "add", "--",
             f".ai/workflows/runs/history/{run_id}/run.json"],
            cwd=self.tmp, capture_output=True, check=True,
        )

        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)

        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "success", out)
        # The active source path must be staged (as a deletion).
        self.assertIn(
            f".ai/workflows/runs/active/{run_id}/run.json",
            data["staged_paths"],
        )
        # The active source path must NOT remain residual.
        self.assertNotIn(
            f".ai/workflows/runs/active/{run_id}/run.json",
            data["residual_dirty_paths"],
        )
        # No active-run paths may remain dirty after success.
        status = self._git_status_porcelain()
        self.assertFalse(
            any(f".ai/workflows/runs/active/{run_id}/" in s for s in status),
            status,
        )
        # The commit must include both the active source (deletion) and
        # the history destination (addition).
        commit_files = self._git_show_name_only()
        self.assertIn(
            f".ai/workflows/runs/active/{run_id}/run.json",
            commit_files,
        )
        self.assertIn(
            f".ai/workflows/runs/history/{run_id}/run.json",
            commit_files,
        )

    def test_final_commit_success_leaves_no_target_active_residuals(self):
        """Guard invariant: a successful final-commit must not leave any
        target-run active paths in residual_dirty_paths. This catches
        rename-source parsing regressions that let active deletions slip
        through as residual.
        """
        self._init_git()
        run_id = "2026-07-12-active-rename-guard"
        self._make_tracked_active_run_files(run_id)
        self._git_commit_baseline()

        active_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "active", run_id
        )
        history_dir = os.path.join(
            self.tmp, ".ai", "workflows", "runs", "history", run_id
        )
        os.makedirs(history_dir, exist_ok=True)

        active_run_json = os.path.join(active_dir, "run.json")
        active_handoff = os.path.join(
            active_dir, "handoffs", "default", "finish-agent.md"
        )
        history_run_json = os.path.join(history_dir, "run.json")
        history_handoff_dir = os.path.join(
            history_dir, "handoffs", "default"
        )
        os.makedirs(history_handoff_dir, exist_ok=True)
        history_handoff = os.path.join(history_handoff_dir, "finish-agent.md")

        subprocess.run(
            ["git", "mv", active_run_json, history_run_json],
            cwd=self.tmp, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "mv", active_handoff, history_handoff],
            cwd=self.tmp, capture_output=True, check=True,
        )

        self._make_done_history_run(run_id=run_id)
        subprocess.run(
            ["git", "add", "--",
             f".ai/workflows/runs/history/{run_id}/run.json"],
            cwd=self.tmp, capture_output=True, check=True,
        )

        rc, out, _ = run_workflow(self.tmp, "final-commit", run_id=run_id)
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "success", out)

        active_prefix = f".ai/workflows/runs/active/{run_id}/"
        residual_active = [
            p for p in data["residual_dirty_paths"]
            if p.startswith(active_prefix)
        ]
        self.assertEqual(
            residual_active, [],
            f"final-commit success left target active residuals: {residual_active}",
        )


# ---------------------------------------------------------------------------
# Slice 1: State Model and Validation
# ---------------------------------------------------------------------------


def _make_implementation_state(slices, strategy="sequential",
                                assessment_status="completed",
                                decision="multi_slice"):
    """Build a canonical implementation block for test fixtures."""
    return {
        "strategy": strategy,
        "slicing_assessment": {
            "status": assessment_status,
            "decision": decision,
            "assessed_by": "plan-agent",
            "assessment_handoff_path": "",
            "reasons": [],
        },
        "aggregate_review_status": "pending",
        "active_slice_id": None,
        "slices": slices,
    }


def _make_slice(slice_id, depends_on=None, required=True, status="pending",
                base_ref="", head_ref="", accepted_head_ref="",
                commit_refs=None, attempt_count=0,
                implement_evidence=None, review_evidence=None,
                block=None):
    return {
        "slice_id": slice_id,
        "depends_on": depends_on or [],
        "required": required,
        "status": status,
        "attempt_count": attempt_count,
        "block": block,
        "base_ref": base_ref,
        "head_ref": head_ref,
        "accepted_head_ref": accepted_head_ref,
        "commit_refs": commit_refs or [],
        "implement_evidence": implement_evidence or {},
        "review_evidence": review_evidence or {},
        "handoff_paths": [],
    }


class TestSliceStateAndValidation(FixtureBase):
    """Slice 1: runtime state model for implementation slices."""

    def _make_apply_run(self, implementation=None, flow_type="spec-flow"):
        run_id = "2026-07-13-slice-state"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": flow_type,
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "slice-state"},
            "context": {"change_id": "slice-state"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    # --- Legacy normalization ---

    def test_legacy_run_without_implementation_normalizes_to_default(self):
        """A legacy run without 'implementation' gets a compatibility default
        slice when loaded/validated, without mutating the persisted file."""
        run_id = self._make_apply_run(implementation=None)
        # validate should succeed and report no errors
        rc, out, _ = run_workflow(self.tmp, "validate")
        self.assertEqual(rc, 0, out)

    # --- Single slice assessment materializes 'default' ---

    def test_single_slice_assessment_materializes_default_slice(self):
        impl = _make_implementation_state(
            [_make_slice("default", depends_on=[], required=True)],
            decision="single_slice",
        )
        run_id = self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        ids = [s["slice_id"] for s in data.get("slices", [])]
        self.assertIn("default", ids)

    # --- Multi-slice state persistence across resume ---

    def test_multi_slice_state_persists_across_save_load(self):
        slices = [
            _make_slice("slice-a", depends_on=[]),
            _make_slice("slice-b", depends_on=["slice-a"]),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"]),
        ]
        impl = _make_implementation_state(slices)
        run_id = self._make_apply_run(implementation=impl)
        state = self._read_current_state()
        self.assertEqual(state["implementation"]["strategy"], "sequential")
        self.assertEqual(len(state["implementation"]["slices"]), 3)
        self.assertEqual(state["implementation"]["slices"][2]["depends_on"], ["slice-a", "slice-b"])

    # --- Validation: duplicate ids ---

    def test_duplicate_slice_ids_rejected(self):
        slices = [
            _make_slice("slice-a"),
            _make_slice("slice-a"),
        ]
        impl = _make_implementation_state(slices)
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("duplicate_slice_id", reasons)

    # --- Validation: reserved 'aggregate' id ---

    def test_reserved_aggregate_slice_id_rejected(self):
        slices = [_make_slice("aggregate")]
        impl = _make_implementation_state(slices)
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("reserved_slice_id", reasons)

    # --- Validation: unknown dependencies ---

    def test_unknown_dependency_rejected(self):
        slices = [_make_slice("slice-a", depends_on=["nonexistent"])]
        impl = _make_implementation_state(slices)
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("unknown_dependency", reasons)

    # --- Validation: self-dependencies ---

    def test_self_dependency_rejected(self):
        slices = [_make_slice("slice-a", depends_on=["slice-a"])]
        impl = _make_implementation_state(slices)
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("self_dependency", reasons)

    # --- Validation: cycles ---

    def test_cyclic_dependency_rejected(self):
        slices = [
            _make_slice("slice-a", depends_on=["slice-b"]),
            _make_slice("slice-b", depends_on=["slice-a"]),
        ]
        impl = _make_implementation_state(slices)
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("cyclic_dependency", reasons)

    # --- Validation: multiple active slices ---

    def test_multiple_active_slices_rejected(self):
        slices = [
            _make_slice("slice-a", status="in_progress"),
            _make_slice("slice-b", status="in_review"),
        ]
        impl = _make_implementation_state(slices)
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("multiple_active_slices", reasons)

    # --- Validation: completed slice requires accepted_head_ref ---

    def test_completed_slice_without_accepted_head_ref_rejected(self):
        slices = [_make_slice("slice-a", status="completed", head_ref="h1")]
        impl = _make_implementation_state(slices)
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("completed_without_accepted_head_ref", reasons)

    # --- Validation: strategy must be sequential ---

    def test_non_sequential_strategy_rejected(self):
        impl = _make_implementation_state(
            [_make_slice("default")],
            strategy="parallel",
        )
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("invalid_strategy", reasons)

    # --- Evidence strictness: one slice's evidence cannot satisfy another ---

    def test_evidence_under_one_slice_does_not_satisfy_another(self):
        slices = [
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="ref-a",
                        implement_evidence={"tasks_complete": True},
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", depends_on=["slice-a"], status="pending"),
        ]
        impl = _make_implementation_state(slices)
        run_id = self._make_apply_run(implementation=impl)
        state = self._read_current_state()
        # slice-b should NOT inherit slice-a's evidence
        slice_b = [s for s in state["implementation"]["slices"] if s["slice_id"] == "slice-b"][0]
        self.assertEqual(slice_b["implement_evidence"], {})
        self.assertEqual(slice_b["review_evidence"], {})

    # --- Validation: not_required waiver invariants (Spec Invariant 7) ---

    def _make_not_required_impl(self, assessed_by="user", reasons=None,
                                 decision="single_slice", slices=None,
                                 override_assessment=None):
        """Build a not_required implementation block for waiver validation tests."""
        assessment = {
            "status": "not_required",
            "decision": decision,
            "assessed_by": assessed_by,
            "assessment_handoff_path": "",
            "reasons": reasons if reasons is not None else ["valid reason"],
        }
        if override_assessment:
            assessment.update(override_assessment)
        return {
            "strategy": "sequential",
            "slicing_assessment": assessment,
            "aggregate_review_status": "pending",
            "active_slice_id": None,
            "slices": slices if slices is not None else [_make_slice("default")],
        }

    def test_not_required_rejects_empty_assessed_by(self):
        """not_required assessment must have non-empty assessed_by."""
        impl = self._make_not_required_impl(assessed_by="")
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("invalid_not_required_waiver", reasons)

    def test_not_required_rejects_empty_reasons(self):
        """not_required assessment must have at least one non-empty reason."""
        impl = self._make_not_required_impl(reasons=[])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("invalid_not_required_waiver", reasons)

    def test_not_required_rejects_whitespace_only_reasons(self):
        """not_required assessment must have at least one non-empty-stripped reason."""
        impl = self._make_not_required_impl(reasons=["   ", "\t\n", ""])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("invalid_not_required_waiver", reasons)

    def test_not_required_rejects_non_single_slice_decision(self):
        """not_required assessment must have decision 'single_slice'."""
        impl = self._make_not_required_impl(decision="multi_slice")
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("invalid_not_required_waiver", reasons)

    def test_not_required_rejects_no_default_slice(self):
        """not_required assessment must have a default slice."""
        impl = self._make_not_required_impl(slices=[_make_slice("other")])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("invalid_not_required_waiver", reasons)

    def test_not_required_rejects_multiple_slices(self):
        """not_required assessment must have exactly one slice (the default)."""
        impl = self._make_not_required_impl(
            slices=[_make_slice("default"), _make_slice("extra")],
        )
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("invalid_not_required_waiver", reasons)

    def test_not_required_rejects_default_not_required_slice(self):
        """not_required: the default slice must be required=True."""
        impl = self._make_not_required_impl(
            slices=[_make_slice("default", required=False)],
        )
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("invalid_not_required_waiver", reasons)

    def test_not_required_accepts_valid_state(self):
        """A valid not_required state (non-empty reason, non-empty assessed_by,
        single required default slice) must pass validation."""
        impl = self._make_not_required_impl(
            assessed_by="user",
            reasons=["User explicitly selected one governed implementation slice"],
        )
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertEqual(rc, 0, out)


# ---------------------------------------------------------------------------
# Slice 2: Runtime Slice Commands
# ---------------------------------------------------------------------------


class TestSliceNextAndCommands(FixtureBase):
    """Slice 2: slice-next, slice-block, slice-resume, slice-cancel commands."""

    def _make_apply_run(self, implementation, flow_type="spec-flow"):
        run_id = "2026-07-13-slice-cmds"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": flow_type,
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "slice-cmds"},
            "context": {"change_id": "slice-cmds"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
            "implementation": implementation,
        }
        self._write_current_state(state)
        return run_id

    # --- slice-next ---

    def test_slice_next_returns_first_ready_slice_in_declaration_order(self):
        """A and B are both ready; declaration order selects A first."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="pending"),
            _make_slice("slice-b", depends_on=[], status="pending"),
        ])
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "slice-a")

    def test_slice_next_returns_no_ready_slice_when_one_in_progress(self):
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_progress", base_ref="base-0"),
            _make_slice("slice-b", status="pending"),
        ])
        impl["active_slice_id"] = "slice-a"
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "no_ready_slice")
        self.assertEqual(data["reason"], "slice_in_progress")

    def test_slice_next_returns_dispatch_aggregate_review_when_all_completed(self):
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="ref-a",
                        review_evidence={"review_passed": True}),
        ])
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_aggregate_review")

    def test_slice_next_returns_all_complete_when_aggregate_passed(self):
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="ref-a",
                        review_evidence={"review_passed": True}),
        ])
        impl["aggregate_review_status"] = "passed"
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "all_slices_and_aggregate_complete")

    def test_slice_next_c_waits_for_accepted_a_and_b(self):
        """C depends on A and B; C is not ready until both are completed."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="ref-a",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", status="in_progress", base_ref="ref-a"),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"], status="pending"),
        ])
        impl["active_slice_id"] = "slice-b"
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "no_ready_slice")

    def test_slice_next_is_non_mutating(self):
        """slice-next must not change the persisted state."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="pending"),
        ])
        self._make_apply_run(impl)
        state_before = self._read_current_state()
        run_workflow(self.tmp, "slice-next")
        state_after = self._read_current_state()
        # Only updated_at should differ (if at all); slices unchanged.
        self.assertEqual(
            state_before["implementation"]["slices"],
            state_after["implementation"]["slices"],
        )

    # --- slice-block ---

    def test_slice_block_sets_slice_to_blocked(self):
        impl = _make_implementation_state([
            _make_slice("slice-a", status="pending"),
        ])
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(
            self.tmp, "slice-block",
            slice_id="slice-a",
            value=json.dumps({"reason": "external_dependency"}),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "blocked")
        self.assertEqual(sl["block"]["reason"], "external_dependency")

    # --- slice-resume ---

    def test_slice_resume_blocked_to_ready(self):
        impl = _make_implementation_state([
            _make_slice("slice-a", status="blocked", block={"reason": "waiting"}),
        ])
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(
            self.tmp, "slice-resume",
            slice_id="slice-a",
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "ready")
        self.assertIsNone(sl["block"])

    def test_slice_resume_rejects_non_blocked_slice(self):
        impl = _make_implementation_state([
            _make_slice("slice-a", status="pending"),
        ])
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(
            self.tmp, "slice-resume",
            slice_id="slice-a",
        )
        self.assertNotEqual(rc, 0)

    # --- slice-cancel ---

    def test_slice_cancel_requires_reason(self):
        impl = _make_implementation_state([
            _make_slice("slice-a", status="pending"),
        ])
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(
            self.tmp, "slice-cancel",
            slice_id="slice-a",
        )
        self.assertNotEqual(rc, 0)

    def test_slice_cancel_with_reason_sets_cancelled(self):
        impl = _make_implementation_state([
            _make_slice("slice-a", status="pending"),
        ])
        self._make_apply_run(impl)
        rc, out, _ = run_workflow(
            self.tmp, "slice-cancel",
            slice_id="slice-a",
            reason="user decided not needed",
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "cancelled")


# ---------------------------------------------------------------------------
# Slice 3: Dispatch Lifecycle and Git Refs
# ---------------------------------------------------------------------------


class TestSliceDispatchLifecycle(FixtureBase):
    """Slice 3: atomic slice transitions in before/after dispatch hooks."""

    def _make_apply_run(self, implementation=None, flow_type="spec-flow",
                        status="running", block=None):
        run_id = "2026-07-13-slice-dispatch"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": flow_type,
            "status": status,
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "slice-dispatch"},
            "context": {"change_id": "slice-dispatch"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": block,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    def test_before_dispatch_rejects_implement_while_assessment_pending(self):
        """Implement dispatch is rejected while slicing assessment is pending."""
        impl = _make_implementation_state(
            [_make_slice("slice-a", status="pending")],
            assessment_status="pending",
        )
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-a",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("slicing_assessment_pending", reasons)

    def test_before_dispatch_rejects_implement_while_assessment_blocked(self):
        impl = _make_implementation_state(
            [_make_slice("slice-a", status="pending")],
            assessment_status="blocked",
        )
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-a",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("slicing_assessment_blocked", reasons)

    def test_before_dispatch_implement_sets_slice_in_progress(self):
        """Before-dispatch(implement-agent, slice_id) atomically sets in_progress."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="ready"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-a",
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "in_progress")
        self.assertEqual(sl["attempt_count"], 1)
        self.assertEqual(state["implementation"]["active_slice_id"], "slice-a")

    def test_before_dispatch_rejects_second_slice_while_one_in_progress(self):
        """Another slice cannot dispatch while one is in_progress."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_progress", base_ref="base-0"),
            _make_slice("slice-b", status="pending"),
        ])
        impl["active_slice_id"] = "slice-a"
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-b",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("another_slice_active", reasons)

    def test_after_dispatch_implement_success_moves_to_in_review(self):
        """Implement success moves the same slice to in_review."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_progress", attempt_count=1,
                        base_ref="base-1"),
        ])
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k test", "result": "pass"}]},
            "artifacts": {
                "head_ref": "head-1",
                "commit_refs": ["commit-1"],
                "base_ref": "base-1",
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="slice-a",
            value=agent_result,
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "in_review")
        self.assertEqual(sl["head_ref"], "head-1")
        self.assertEqual(sl["commit_refs"], ["commit-1"])

    def test_after_dispatch_review_pass_completes_slice(self):
        """Review pass records accepted_head_ref and completes the slice."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_review", head_ref="head-1",
                        base_ref="base-1"),
        ])
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"review_passed": True},
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            slice_id="slice-a",
            value=agent_result,
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "completed")
        self.assertEqual(sl["accepted_head_ref"], "head-1")
        self.assertIsNone(state["implementation"]["active_slice_id"])

    def test_after_dispatch_review_rejection_preserves_base_ref(self):
        """Review rejection preserves original base_ref and allows head advancement."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_review", head_ref="head-1",
                        base_ref="base-1", attempt_count=1),
        ])
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "failed",
            "evidence": {},
            "blockers": [{
                "reason": "review_changes_requested",
                "message": "fix issues",
                "recommended_action": "back_to_implement",
            }],
            "recommended_next_action": "back_to_implement",
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            slice_id="slice-a",
            value=agent_result,
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        # Slice goes back to pending/ready for re-implementation
        self.assertIn(sl["status"], ("pending", "ready", "blocked"))
        self.assertEqual(sl["base_ref"], "base-1")

    def test_sequential_ab_then_c_execution(self):
        """A/B sequential execution, C depends on accepted A+B heads."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="ready", base_ref="base-0"),
            _make_slice("slice-b", depends_on=["slice-a"], status="pending"),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"], status="pending"),
        ])
        self._make_apply_run(implementation=impl)

        # Implement A
        rc, out, _ = run_workflow(self.tmp, "before-dispatch",
                                  agent="implement-agent", slice_id="slice-a")
        self.assertEqual(rc, 0, out)
        # A succeeds
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success",
                                      "evidence": {},
                                      "artifacts": {"head_ref": "head-a", "commit_refs": ["c-a"], "base_ref": "base-0"},
                                  }))
        self.assertEqual(rc, 0, out)
        # Review A passes
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="review-agent", slice_id="slice-a",
                                  value=json.dumps({"status": "success", "evidence": {"review_passed": True}}))
        self.assertEqual(rc, 0, out)

        state = self._read_current_state()
        sl_a = [s for s in state["implementation"]["slices"] if s["slice_id"] == "slice-a"][0]
        self.assertEqual(sl_a["status"], "completed")
        self.assertEqual(sl_a["accepted_head_ref"], "head-a")

        # slice-next should return slice-b
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "slice-b")


# ---------------------------------------------------------------------------
# Remediation: Review-agent blocked issues — RED tests for missing behavior
# ---------------------------------------------------------------------------


class TestSliceDispatchRemediation(FixtureBase):
    """Remediation tests for review-agent blockers.

    Covers:
    1. before-dispatch must enforce exact slice-next selection + dependency readiness.
    2. after-dispatch must reject missing/invalid Git refs.
    3. aggregate-review state transitions + completion gating.
    4. state validation: task coverage, review-evidence, aggregate, active-slice,
       sequential commit-chain invariants.
    5. negative and end-to-end scenarios.
    """

    def _make_apply_run(self, implementation=None, flow_type="spec-flow",
                        status="running", block=None):
        run_id = "2026-07-13-slice-remediation"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": flow_type,
            "status": status,
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "slice-remediation"},
            "context": {"change_id": "slice-remediation"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": block,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    # --- Issue 1: before-dispatch must enforce exact slice-next selection ---

    def test_before_dispatch_rejects_slice_that_is_not_slice_next_result(self):
        """before-dispatch(implement-agent) must accept only the exact
        slice-next result. If slice-a is ready but slice-b is requested
        and slice-b's dependencies are not completed, dispatch must be
        rejected even if slice-b is 'pending'."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="pending"),
            _make_slice("slice-b", depends_on=["slice-a"], status="pending"),
        ])
        self._make_apply_run(implementation=impl)
        # slice-next should return slice-a, NOT slice-b.
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "slice-a")
        # Requesting slice-b (whose dependency is not completed) must be rejected.
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-b",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("slice_not_ready", reasons)

    def test_before_dispatch_rejects_dependency_not_completed(self):
        """A slice whose dependencies are not completed cannot dispatch,
        even if its status is 'pending'."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="in_progress"),
            _make_slice("slice-b", depends_on=["slice-a"], status="pending"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-b",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        # Must be blocked either because another slice is active or
        # because dependencies are not completed.
        self.assertTrue(
            "another_slice_active" in reasons or "slice_not_ready" in reasons,
            f"expected another_slice_active or slice_not_ready in {reasons}",
        )

    def test_before_dispatch_rejects_dependency_completed_but_no_accepted_head(self):
        """A slice whose dependency is 'completed' but lacks accepted_head_ref
        cannot dispatch."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="completed",
                        accepted_head_ref=""),  # missing accepted head
            _make_slice("slice-b", depends_on=["slice-a"], status="pending"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            slice_id="slice-b",
        )
        self.assertNotEqual(rc, 0)

    # --- Issue 2: after-dispatch must reject missing/invalid Git refs ---

    def test_after_dispatch_implement_success_rejects_missing_head_ref(self):
        """Implement success without head_ref cannot enter review."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_progress", attempt_count=1,
                        base_ref="base-1"),
        ])
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k test", "result": "pass"}]},
            "artifacts": {
                "base_ref": "base-1",
                "commit_refs": ["commit-1"],
                # head_ref missing
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="slice-a",
            value=agent_result,
        )
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        # Must NOT have moved to in_review.
        self.assertNotEqual(sl["status"], "in_review")

    def test_after_dispatch_implement_success_rejects_missing_commit_refs(self):
        """Implement success without commit_refs cannot enter review."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_progress", attempt_count=1,
                        base_ref="base-1"),
        ])
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k test", "result": "pass"}]},
            "artifacts": {
                "base_ref": "base-1",
                "head_ref": "head-1",
                # commit_refs missing
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="slice-a",
            value=agent_result,
        )
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertNotEqual(sl["status"], "in_review")

    def test_after_dispatch_implement_success_rejects_empty_string_refs(self):
        """Implement success with empty-string refs cannot enter review."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_progress", attempt_count=1,
                        base_ref="base-1"),
        ])
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"focused_tests": [{"command": "pytest -k test", "result": "pass"}]},
            "artifacts": {
                "base_ref": "base-1",
                "head_ref": "",
                "commit_refs": [],
            },
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="implement-agent",
            slice_id="slice-a",
            value=agent_result,
        )
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertNotEqual(sl["status"], "in_review")

    def test_after_dispatch_review_pass_rejects_empty_accepted_head(self):
        """Review success cannot complete a slice with empty accepted_head_ref."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_review", head_ref="",
                        base_ref="base-1"),
        ])
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"review_passed": True},
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            slice_id="slice-a",
            value=agent_result,
        )
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        # Must NOT be completed with empty accepted_head_ref.
        self.assertNotEqual(sl["status"], "completed")

    # --- Issue 3: aggregate-review state transitions + completion gating ---

    def test_after_dispatch_review_pass_sets_aggregate_ready_when_all_complete(self):
        """When the last required slice completes, aggregate_review_status
        transitions to 'passed' for single-slice or 'ready' for multi-slice."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_review", head_ref="head-a",
                        base_ref="base-0"),
        ])
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"review_passed": True},
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            slice_id="slice-a",
            value=agent_result,
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        # Single required slice: aggregate passes directly (no aggregate review)
        self.assertEqual(
            state["implementation"]["aggregate_review_status"], "passed",
        )

    def test_after_dispatch_aggregate_review_pass_sets_passed(self):
        """Review-agent success with aggregate scope sets aggregate_review_status
        to 'passed'."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", status="completed", accepted_head_ref="head-b",
                        review_evidence={"review_passed": True}),
        ])
        impl["aggregate_review_status"] = "ready"
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"review_passed": True, "review_scope": "aggregate"},
            "artifacts": {"review_scope": "aggregate"},
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            slice_id="aggregate",
            value=agent_result,
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(
            state["implementation"]["aggregate_review_status"], "passed",
        )

    def test_after_dispatch_aggregate_review_rejection_sets_blocked(self):
        """Review-agent failure with aggregate scope sets aggregate_review_status
        to 'blocked'."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", status="completed", accepted_head_ref="head-b",
                        review_evidence={"review_passed": True}),
        ])
        impl["aggregate_review_status"] = "ready"
        self._make_apply_run(implementation=impl)
        agent_result = json.dumps({
            "status": "failed",
            "evidence": {},
            "blockers": [{"reason": "aggregate_review_failed", "message": "fail"}],
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            slice_id="aggregate",
            value=agent_result,
        )
        state = self._read_current_state()
        self.assertEqual(
            state["implementation"]["aggregate_review_status"], "blocked",
        )

    def test_complete_phase_apply_change_rejects_without_aggregate_passed(self):
        """complete-phase for apply_change must be rejected when
        aggregate_review_status is not 'passed'."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="head-a"),
        ])
        impl["aggregate_review_status"] = "ready"  # not passed
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="all_tasks_complete",
        )
        self.assertNotEqual(rc, 0)

    def test_slice_next_returns_all_complete_only_after_aggregate_passed(self):
        """slice-next must return all_slices_and_aggregate_complete only
        when aggregate_review_status is 'passed'. When it's 'ready', it
        must return dispatch_aggregate_review."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
        ])
        impl["aggregate_review_status"] = "ready"
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_aggregate_review")

    # --- Issue 4: state validation gaps ---

    def test_validation_rejects_completed_slice_without_review_evidence(self):
        """A completed slice must have non-empty review_evidence."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a",
                        review_evidence={}),  # empty
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("completed_without_review_evidence", reasons)

    def test_validation_rejects_active_slice_id_mismatch(self):
        """active_slice_id must match the slice that is in_progress/in_review."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_progress"),
        ])
        impl["active_slice_id"] = "slice-b"  # mismatch
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("active_slice_id_mismatch", reasons)

    def test_validation_rejects_in_progress_slice_without_base_ref(self):
        """An in_progress slice must have a non-empty base_ref."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_progress", base_ref=""),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        data = json.loads(out)
        if rc != 0:
            reasons = [e.get("reason", "") for e in data.get("errors", [])]
            self.assertIn("active_slice_missing_base_ref", reasons)

    def test_validation_rejects_in_review_slice_without_head_ref(self):
        """An in_review slice must have non-empty head_ref and commit_refs."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_review", base_ref="base-1",
                        head_ref=""),  # missing head_ref
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("in_review_missing_head_ref", reasons)

    def test_validation_rejects_non_empty_commit_refs_for_in_review(self):
        """An in_review slice must have non-empty commit_refs."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_review", base_ref="base-1",
                        head_ref="head-1", commit_refs=[]),  # empty
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("in_review_missing_commit_refs", reasons)

    def test_validation_rejects_sequential_commit_chain_violation(self):
        """A slice's base_ref must equal the previous accepted slice's
        accepted_head_ref when depending on it."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a"),
            _make_slice("slice-b", depends_on=["slice-a"], status="in_progress",
                        base_ref="wrong-base"),  # should be head-a
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("commit_chain_violation", reasons)

    def test_validation_accepts_correct_commit_chain(self):
        """A slice's base_ref equal to previous accepted_head_ref is valid."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a"),
            _make_slice("slice-b", depends_on=["slice-a"], status="in_progress",
                        base_ref="head-a"),  # correct chain
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        # Should not fail with commit_chain_violation.
        if rc != 0:
            data = json.loads(out)
            reasons = [e.get("reason", "") for e in data.get("errors", [])]
            self.assertNotIn("commit_chain_violation", reasons)

    # --- Issue 5: end-to-end and negative scenarios ---

    def test_e2e_single_slice_flow_assessment_to_aggregate_review(self):
        """Complete single-slice flow: implement -> review -> all complete.

        With Task 7, a single required slice auto-passes aggregate review
        when its slice review completes.  No separate aggregate review
        dispatch is needed.
        """
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref="base-0"),
        ])
        self._make_apply_run(implementation=impl)

        # Implement A
        rc, out, _ = run_workflow(self.tmp, "before-dispatch",
                                  agent="implement-agent", slice_id="slice-a")
        self.assertEqual(rc, 0, out)
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success",
                                      "evidence": {},
                                      "artifacts": {"head_ref": "head-a",
                                                    "commit_refs": ["c-a"],
                                                    "base_ref": "base-0"},
                                  }))
        self.assertEqual(rc, 0, out)
        # Review A passes
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="review-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success",
                                      "evidence": {"review_passed": True},
                                  }))
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        # Single required slice: aggregate passes directly (no aggregate review)
        self.assertEqual(
            state["implementation"]["aggregate_review_status"], "passed",
        )
        # slice-next returns all complete
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        data = json.loads(out)
        self.assertEqual(data["status"], "all_slices_and_aggregate_complete")

    def test_e2e_multi_slice_a_b_c_with_c_after_accepted_a_and_b(self):
        """Multi-slice A/B/C: A and B independently ready, C depends on both.
        C starts only after accepted A and B heads."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref="base-0"),
            _make_slice("slice-b", depends_on=[], status="ready",
                        base_ref="base-0"),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"], status="pending"),
        ])
        self._make_apply_run(implementation=impl)

        # Implement + review A
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        run_workflow(self.tmp, "after-dispatch",
                     agent="implement-agent", slice_id="slice-a",
                     value=json.dumps({
                         "status": "success", "evidence": {},
                         "artifacts": {"head_ref": "head-a",
                                       "commit_refs": ["c-a"],
                                       "base_ref": "base-0"},
                     }))
        run_workflow(self.tmp, "after-dispatch",
                     agent="review-agent", slice_id="slice-a",
                     value=json.dumps({"status": "success",
                                       "evidence": {"review_passed": True}}))

        # slice-next must return slice-b (declaration order)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "slice-b")

        # Implement + review B
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-b")
        run_workflow(self.tmp, "after-dispatch",
                     agent="implement-agent", slice_id="slice-b",
                     value=json.dumps({
                         "status": "success", "evidence": {},
                         "artifacts": {"head_ref": "head-b",
                                       "commit_refs": ["c-b"],
                                       "base_ref": "base-0"},
                     }))
        run_workflow(self.tmp, "after-dispatch",
                     agent="review-agent", slice_id="slice-b",
                     value=json.dumps({"status": "success",
                                       "evidence": {"review_passed": True}}))

        # Now C should be ready
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "slice-c")

    def test_e2e_blocked_a_independent_b_proceeds(self):
        """Blocked A with independent B proceeding sequentially."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="blocked",
                        block={"reason": "waiting"}),
            _make_slice("slice-b", depends_on=[], status="pending"),
        ])
        self._make_apply_run(implementation=impl)
        # slice-next should return slice-b (A is blocked, B is ready)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "slice-b")

    def test_e2e_review_rejection_correction_commit(self):
        """Review rejection preserves base_ref and allows re-implementation
        with a correction commit that advances head_ref."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="in_review", head_ref="head-1",
                        base_ref="base-1", attempt_count=1),
        ])
        self._make_apply_run(implementation=impl)
        # Review rejects
        run_workflow(self.tmp, "after-dispatch",
                     agent="review-agent", slice_id="slice-a",
                     value=json.dumps({
                         "status": "failed", "evidence": {},
                         "blockers": [{"reason": "review_changes_requested",
                                       "message": "fix"}],
                         "recommended_next_action": "back_to_implement",
                     }))
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["base_ref"], "base-1")
        self.assertIn(sl["status"], ("ready", "pending"))
        # Re-implement with correction commit (new head)
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        run_workflow(self.tmp, "after-dispatch",
                     agent="implement-agent", slice_id="slice-a",
                     value=json.dumps({
                         "status": "success", "evidence": {},
                         "artifacts": {"head_ref": "head-2",
                                       "commit_refs": ["c-1", "c-2"],
                                       "base_ref": "base-1"},
                     }))
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "in_review")
        self.assertEqual(sl["head_ref"], "head-2")
        self.assertEqual(sl["base_ref"], "base-1")
        self.assertEqual(sl["attempt_count"], 2)

    def test_e2e_aggregate_completion_gate_failure(self):
        """Aggregate review failure blocks apply_change completion."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", status="completed", accepted_head_ref="head-b",
                        review_evidence={"review_passed": True}),
        ])
        impl["aggregate_review_status"] = "ready"
        self._make_apply_run(implementation=impl)
        # Aggregate review fails
        run_workflow(self.tmp, "after-dispatch",
                     agent="review-agent", slice_id="aggregate",
                     value=json.dumps({
                         "status": "failed", "evidence": {},
                         "blockers": [{"reason": "aggregate_review_failed",
                                       "message": "integration broken"}],
                     }))
        state = self._read_current_state()
        self.assertEqual(
            state["implementation"]["aggregate_review_status"], "blocked",
        )
        # complete-phase must be rejected
        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="all_tasks_complete",
        )
        self.assertNotEqual(rc, 0)

    def test_e2e_aggregate_review_then_pass_allows_completion(self):
        """After aggregate review passes, complete-phase is allowed."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed", accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", status="completed", accepted_head_ref="head-b",
                        review_evidence={"review_passed": True}),
        ])
        impl["aggregate_review_status"] = "ready"
        self._make_apply_run(implementation=impl)
        # Need evidence keys for apply_change to pass; add minimal
        state = self._read_current_state()
        state.setdefault("evidence", {})["eval_passed_or_human_decision_recorded"] = True
        # Provide implement verification evidence so the missing_verification_basis
        # gate is satisfied.
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("slice-a", {})["implement-agent"] = {
            "status": "success",
            "evidence": {"verification_passed": True, "focused_tests": [{"command": "pytest", "result": "pass"}]},
        }
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("slice-b", {})["implement-agent"] = {
            "status": "success",
            "evidence": {"verification_passed": True, "focused_tests": [{"command": "pytest", "result": "pass"}]},
        }
        self._write_current_state(state)
        # Aggregate review passes
        run_workflow(self.tmp, "after-dispatch",
                     agent="review-agent", slice_id="aggregate",
                     value=json.dumps({
                         "status": "success", "evidence": {"review_passed": True,
                                                           "review_scope": "aggregate"},
                         "artifacts": {"review_scope": "aggregate"},
                     }))
        # slice-next returns all complete
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        data = json.loads(out)
        self.assertEqual(data["status"], "all_slices_and_aggregate_complete")

    def test_e2e_legacy_unsliced_default_compatibility(self):
        """Legacy unsliced run with default slice still works end-to-end."""
        impl = _make_implementation_state(
            [_make_slice("default", depends_on=[], status="ready",
                         base_ref="base-0")],
            decision="single_slice",
        )
        self._make_apply_run(implementation=impl)
        # slice-next returns default
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "default")
        # Implement default
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="default")
        run_workflow(self.tmp, "after-dispatch",
                     agent="implement-agent", slice_id="default",
                     value=json.dumps({
                         "status": "success", "evidence": {},
                         "artifacts": {"head_ref": "head-d",
                                       "commit_refs": ["c-d"],
                                       "base_ref": "base-0"},
                     }))
        run_workflow(self.tmp, "after-dispatch",
                     agent="review-agent", slice_id="default",
                      value=json.dumps({"status": "success",
                                        "evidence": {"review_passed": True}}))
        state = self._read_current_state()
        self.assertEqual(
            state["implementation"]["aggregate_review_status"], "passed",
        )


# ---------------------------------------------------------------------------
# Review-blocker remediation: aggregate review, commit-chain, slice_id
# requirement, and Git range validation contracts.
# ---------------------------------------------------------------------------


class TestReviewBlockerRemediation(FixtureBase):
    """Coverage for the four review blockers that bypassed existing contracts."""

    def _make_apply_run(self, implementation=None, flow_type="spec-flow",
                        run_id="2026-07-13-review-blockers"):
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": flow_type,
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "review-blockers"},
            "context": {"change_id": "review-blockers"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    # --- Blocker 1: aggregate review rejected as unknown_slice ---

    def test_before_dispatch_aggregate_review_not_unknown_slice(self):
        """before-dispatch(review-agent, slice_id='aggregate') must NOT be
        rejected as unknown_slice when aggregate_review_status is 'ready'."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
        ])
        impl["aggregate_review_status"] = "ready"
        self._make_apply_run(implementation=impl)

        rc, out, _ = run_workflow(self.tmp, "before-dispatch",
                                  agent="review-agent", slice_id="aggregate")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertNotIn("unknown_slice", reasons)

    def test_before_dispatch_aggregate_review_rejected_when_not_ready(self):
        """before-dispatch(review-agent, slice_id='aggregate') is rejected
        with aggregate_review_not_ready when aggregate_review_status is not
        'ready'."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
        ])
        # aggregate_review_status is 'pending' (not all slices completed path)
        impl["aggregate_review_status"] = "pending"
        self._make_apply_run(implementation=impl)

        rc, out, _ = run_workflow(self.tmp, "before-dispatch",
                                  agent="review-agent", slice_id="aggregate")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("aggregate_review_not_ready", reasons)
        self.assertNotIn("unknown_slice", reasons)

    # --- Blocker 2: commit-chain for differing dep heads (sequential model) ---

    def test_validation_differing_dep_heads_base_must_match_latest(self):
        """A slice depending on two completed slices with different
        accepted_head_ref values must have base_ref equal to the latest
        completed dependency's accepted_head_ref (the previous accepted
        sequential head).  In declaration order [A, B], B is the latest, so
        base_ref must be head-b, not head-a."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a"),
            _make_slice("slice-b", status="completed",
                        accepted_head_ref="head-b"),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"],
                        status="in_progress", base_ref="head-a"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("commit_chain_violation", reasons)

    def test_validation_accepts_multi_dep_matching_heads(self):
        """When two dependencies share the same accepted_head_ref, the
        commit-chain is satisfiable and validation passes."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="shared-head"),
            _make_slice("slice-b", status="completed",
                        accepted_head_ref="shared-head"),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"],
                        status="in_progress", base_ref="shared-head"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        if rc != 0:
            data = json.loads(out)
            reasons = [e.get("reason", "") for e in data.get("errors", [])]
            self.assertNotIn("commit_chain_violation", reasons)

    # --- Blocker 3: sliced implement dispatch without slice_id ---

    def test_implement_dispatch_without_slice_id_rejected_when_slices_exist(self):
        """before-dispatch(implement-agent) without --slice-id must be
        rejected when implementation state has explicit slices (not the
        legacy default-only case)."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref="base-0"),
            _make_slice("slice-b", depends_on=["slice-a"], status="pending"),
        ])
        self._make_apply_run(implementation=impl)

        rc, out, _ = run_workflow(self.tmp, "before-dispatch",
                                  agent="implement-agent")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("missing_slice_id", reasons)

    def test_implement_dispatch_without_slice_id_allowed_for_single_default(self):
        """before-dispatch(implement-agent) without --slice-id is REJECTED
        even for a single 'default' slice — all active implement-agent
        dispatches require --slice-id (Invariants 8 and 12)."""
        impl = _make_implementation_state(
            [_make_slice("default", depends_on=[], status="ready",
                         base_ref="base-0")],
            assessment_status="not_required",
            decision="single_slice",
        )
        self._make_apply_run(implementation=impl)

        rc, out, _ = run_workflow(self.tmp, "before-dispatch",
                                  agent="implement-agent")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("missing_slice_id", reasons)

    def test_implement_dispatch_without_slice_id_rejected_for_completed_assessment(self):
        """before-dispatch(implement-agent) without --slice-id is REJECTED
        when assessment_status is 'completed' (non-legacy persisted state)."""
        impl = _make_implementation_state(
            [_make_slice("default", depends_on=[], status="ready",
                         base_ref="base-0")],
            assessment_status="completed",
            decision="single_slice",
        )
        self._make_apply_run(implementation=impl)

        rc, out, _ = run_workflow(self.tmp, "before-dispatch",
                                  agent="implement-agent")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("missing_slice_id", reasons)

    # --- Blocker 4: Git range validation ---

    def _init_git(self):
        subprocess.run(["git", "init"], cwd=self.tmp, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=self.tmp, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=self.tmp, capture_output=True, check=True)

    def _git_commit(self, msg):
        # Write a unique file so each commit has a change.
        fname = f"file_{msg.replace(' ', '_')}_{abs(hash(msg)) % 100000}.txt"
        with open(os.path.join(self.tmp, fname), "w") as f:
            f.write(msg)
        subprocess.run(["git", "add", "-A"], cwd=self.tmp,
                       capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=self.tmp,
                       capture_output=True, check=True)
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.tmp,
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def test_after_dispatch_rejects_nonexistent_head_ref(self):
        """after-dispatch(implement-agent success) must reject a head_ref
        that does not exist in the git repo."""
        self._init_git()
        base = self._git_commit("baseline")
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        self._make_apply_run(implementation=impl)
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success",
                                      "evidence": {},
                                      "artifacts": {
                                          "head_ref": "nonexistent-sha",
                                          "commit_refs": ["nonexistent-sha"],
                                          "base_ref": base,
                                      },
                                  }))
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("invalid_git_ref", reasons)
        # Slice must NOT have transitioned to in_review
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertNotEqual(sl["status"], "in_review")

    def test_after_dispatch_rejects_head_not_descendant_of_base(self):
        """after-dispatch must reject when head_ref is not a descendant of
        base_ref (ancestry violation)."""
        self._init_git()
        base = self._git_commit("baseline")
        # Create a divergent branch head that is NOT a descendant of base.
        # Since base is the first commit, we create a second commit on the
        # main branch, then use the divergent branch's commit as head — which
        # is a sibling, not a descendant of base.
        # Actually: base IS an ancestor of everything in this repo.  We need
        # a head that is NOT a descendant of base.  Create two root commits
        # by using a separate orphan branch.
        subprocess.run(["git", "checkout", "--orphan", "orphan"],
                       cwd=self.tmp, capture_output=True, check=True)
        # Remove tracked files from index for the orphan branch
        subprocess.run(["git", "rm", "-rf", "--cached", "."],
                       cwd=self.tmp, capture_output=True, check=True)
        head = self._git_commit("orphan-commit")
        subprocess.run(["git", "checkout", "main"],
                       cwd=self.tmp, capture_output=True, check=True)
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        self._make_apply_run(implementation=impl)
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success",
                                      "evidence": {},
                                      "artifacts": {
                                          "head_ref": head,
                                          "commit_refs": [head],
                                          "base_ref": base,
                                      },
                                  }))
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("invalid_git_ref", reasons)
        # Slice must NOT have transitioned to in_review
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertNotEqual(sl["status"], "in_review")

    def test_after_dispatch_rejects_commit_refs_not_in_range(self):
        """after-dispatch must reject when commit_refs are not within the
        base..head range (contiguity violation)."""
        self._init_git()
        base = self._git_commit("baseline")
        mid = self._git_commit("middle")
        head = self._git_commit("head")
        # Create an out-of-range commit on a divergent branch
        subprocess.run(["git", "checkout", "-b", "other", base],
                       cwd=self.tmp, capture_output=True, check=True)
        outside = self._git_commit("outside-range")
        subprocess.run(["git", "checkout", "main"],
                       cwd=self.tmp, capture_output=True, check=True)
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        self._make_apply_run(implementation=impl)
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success",
                                      "evidence": {},
                                      "artifacts": {
                                          "head_ref": head,
                                          "commit_refs": [mid, outside],
                                          "base_ref": base,
                                      },
                                  }))
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("invalid_git_ref", reasons)
        # Slice must NOT have transitioned to in_review
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertNotEqual(sl["status"], "in_review")

    def test_after_dispatch_accepts_valid_git_range(self):
        """after-dispatch accepts when all refs exist, head is descendant of
        base, and all commit_refs are within the base..head range."""
        self._init_git()
        base = self._git_commit("baseline")
        mid = self._git_commit("middle")
        head = self._git_commit("head")
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        self._make_apply_run(implementation=impl)
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success",
                                      "evidence": {},
                                      "artifacts": {
                                          "head_ref": head,
                                          "commit_refs": [mid, head],
                                          "base_ref": base,
                                      },
                                  }))
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        # Slice should have transitioned to in_review
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "in_review")


# ---------------------------------------------------------------------------
# Review-blocker remediation round 2: sequential A/B/C commit-chain, linked
# worktree Git validation, exact ordered commit_refs range equality.
# ---------------------------------------------------------------------------


class TestReviewBlockerRemediation2(FixtureBase):
    """Round-2 coverage for the four review blockers returned after the first
    remediation attempt.  These tests encode the corrected invariants:

    * The sequential commit-chain requires ``base_ref`` to equal the *latest*
      accepted sequential head, and all dependency accepted heads to be
      ancestors of (or equal to) ``base_ref`` — not equal to every dep head.
    * Git validation must run in linked worktrees (``.git`` is a file).
    * ``commit_refs`` must equal ``git rev-list --reverse base..head`` exactly
      (order and completeness).
    """

    def _make_apply_run(self, implementation=None, flow_type="spec-flow",
                        run_id="2026-07-13-review-blockers-r2"):
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": flow_type,
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "review-blockers-r2"},
            "context": {"change_id": "review-blockers-r2"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    # --- Blocker 1: sequential A/B/C commit-chain ---

    def test_validation_accepts_sequential_abc_chain(self):
        """Sequential A/B/C: A completes with head-a, B starts from head-a
        and completes with head-b, C depends on both and starts from head-b
        (the latest accepted sequential head).  Validation must NOT flag this
        as commit_chain_unsatisfiable or commit_chain_violation, because
        head-a is an ancestor of head-b (the chain is contiguous)."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a"),
            _make_slice("slice-b", depends_on=["slice-a"], status="completed",
                        base_ref="head-a", accepted_head_ref="head-b"),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"],
                        status="in_progress", base_ref="head-b"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        if rc != 0:
            data = json.loads(out)
            reasons = [e.get("reason", "") for e in data.get("errors", [])]
            self.assertNotIn("commit_chain_unsatisfiable", reasons)
            self.assertNotIn("commit_chain_violation", reasons)
        # If rc == 0 the validation accepted the chain.

    def test_validation_rejects_base_not_equal_latest_sequential_head(self):
        """A slice's base_ref must equal the latest accepted sequential head
        (the last completed dependency in declaration/dependency order).  If
        C depends on A (head-a) then B (head-b) and base_ref is head-a (not
        head-b), validation must flag commit_chain_violation."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a"),
            _make_slice("slice-b", depends_on=["slice-a"], status="completed",
                        base_ref="head-a", accepted_head_ref="head-b"),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"],
                        status="in_progress", base_ref="head-a"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("commit_chain_violation", reasons)

    def test_validation_rejects_dep_head_not_ancestor_of_base(self):
        """If a dependency's accepted_head_ref is NOT an ancestor of the
        slice's base_ref (the chain is broken), validation must flag it.
        Since state.py validation is symbolic (no git), this is modeled by
        base_ref not matching the latest sequential head when deps have a
        single shared head.  The per-dep equality check catches the direct
        single-dependency break."""
        impl = _make_implementation_state([
            _make_slice("slice-a", status="completed",
                        accepted_head_ref="head-a"),
            _make_slice("slice-b", depends_on=["slice-a"], status="in_progress",
                        base_ref="wrong-base"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("commit_chain_violation", reasons)

    # --- Blocker 2: linked worktree Git validation ---

    def _init_git(self):
        subprocess.run(["git", "init"], cwd=self.tmp, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=self.tmp, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=self.tmp, capture_output=True, check=True)

    def _git_commit(self, msg):
        fname = f"file_{msg.replace(' ', '_')}_{abs(hash(msg)) % 100000}.txt"
        with open(os.path.join(self.tmp, fname), "w") as f:
            f.write(msg)
        subprocess.run(["git", "add", "-A"], cwd=self.tmp,
                       capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=self.tmp,
                       capture_output=True, check=True)
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.tmp,
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def _make_linked_worktree(self, base_branch="main"):
        """Create a linked worktree (where .git is a file, not a directory)
        and return its path.  The worktree shares the main repo's objects."""
        import tempfile
        wt = tempfile.mkdtemp(prefix="wt_")
        subprocess.run(
            ["git", "worktree", "add", "--detach", wt, base_branch],
            cwd=self.tmp, capture_output=True, check=True,
        )
        # Verify .git is a file (linked worktree), not a directory.
        git_path = os.path.join(wt, ".git")
        self.assertTrue(os.path.isfile(git_path),
                        f"expected .git to be a file in linked worktree, got {git_path}")
        return wt

    def test_validate_git_refs_works_in_linked_worktree(self):
        """_validate_git_refs must validate refs in a linked worktree where
        .git is a file, not a directory.  This exercises the worktree-mode
        contract that the review blocker identified as skipped."""
        self._init_git()
        base = self._git_commit("baseline")
        mid = self._git_commit("middle")
        head = self._git_commit("head")
        wt = self._make_linked_worktree()
        # Import and call _validate_git_refs directly against the worktree.
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                        ".ai", "workflows", "scripts"))
        from workflow_runtime.dispatch import _validate_git_refs
        blockers = _validate_git_refs(wt, base, head, [mid, head])
        self.assertEqual(blockers, [], f"expected no blockers in linked worktree, got {blockers}")

    def test_after_dispatch_validates_refs_in_linked_worktree(self):
        """after-dispatch(implement success) must run Git validation in a
        linked worktree, not skip it because .git is a file."""
        self._init_git()
        base = self._git_commit("baseline")
        head = self._git_commit("head")
        wt = self._make_linked_worktree()
        # Set up a run state inside the worktree's .ai directory so the
        # workflow runtime operates within the worktree path.
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        state = {
            "version": 1,
            "run_id": "wt-run",
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "wt-test"},
            "context": {"change_id": "wt-test"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
            "implementation": impl,
        }
        ai_dir = os.path.join(wt, ".ai/workflows/runs/active/wt-run")
        os.makedirs(ai_dir, exist_ok=True)
        with open(os.path.join(ai_dir, "run.json"), "w") as f:
            json.dump(state, f)
        with open(os.path.join(wt, ".ai/workflows/runs/current.json"), "w") as f:
            json.dump({"run_id": "wt-run"}, f)
        # before-dispatch to set slice to in_progress
        run_workflow(wt, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        # after-dispatch with valid refs — should pass Git validation
        rc, out, _ = run_workflow(wt, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success", "evidence": {},
                                      "artifacts": {
                                          "head_ref": head,
                                          "commit_refs": [head],
                                          "base_ref": base,
                                      },
                                  }))
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertNotIn("invalid_git_ref", reasons)

    def test_after_dispatch_rejects_bad_refs_in_linked_worktree(self):
        """after-dispatch must reject a nonexistent head_ref in a linked
        worktree — proving Git validation actually runs (not skipped)."""
        self._init_git()
        base = self._git_commit("baseline")
        wt = self._make_linked_worktree()
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        state = {
            "version": 1,
            "run_id": "wt-run2",
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "wt-test2"},
            "context": {"change_id": "wt-test2"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
            "implementation": impl,
        }
        ai_dir = os.path.join(wt, ".ai/workflows/runs/active/wt-run2")
        os.makedirs(ai_dir, exist_ok=True)
        with open(os.path.join(ai_dir, "run.json"), "w") as f:
            json.dump(state, f)
        with open(os.path.join(wt, ".ai/workflows/runs/current.json"), "w") as f:
            json.dump({"run_id": "wt-run2"}, f)
        run_workflow(wt, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        rc, out, _ = run_workflow(wt, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success", "evidence": {},
                                      "artifacts": {
                                          "head_ref": "nonexistent-sha",
                                          "commit_refs": ["nonexistent-sha"],
                                          "base_ref": base,
                                      },
                                  }))
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("invalid_git_ref", reasons)

    # --- Blocker 3: exact ordered commit_refs range equality ---

    def test_after_dispatch_rejects_partial_commit_refs(self):
        """after-dispatch must reject commit_refs=[head] when base..head
        contains intermediate commits — a partial list does not satisfy
        exact ordered range equality."""
        self._init_git()
        base = self._git_commit("baseline")
        mid = self._git_commit("middle")
        head = self._git_commit("head")
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        self._make_apply_run(implementation=impl)
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success", "evidence": {},
                                      "artifacts": {
                                          "head_ref": head,
                                          "commit_refs": [head],  # missing mid
                                          "base_ref": base,
                                      },
                                  }))
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("invalid_git_ref", reasons)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertNotEqual(sl["status"], "in_review")

    def test_after_dispatch_rejects_reordered_commit_refs(self):
        """after-dispatch must reject commit_refs in wrong order — the
        ordered range must match git rev-list --reverse base..head."""
        self._init_git()
        base = self._git_commit("baseline")
        mid = self._git_commit("middle")
        head = self._git_commit("head")
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        self._make_apply_run(implementation=impl)
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success", "evidence": {},
                                      "artifacts": {
                                          "head_ref": head,
                                          "commit_refs": [head, mid],  # wrong order
                                          "base_ref": base,
                                      },
                                  }))
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("invalid_git_ref", reasons)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertNotEqual(sl["status"], "in_review")

    def test_after_dispatch_accepts_exact_ordered_commit_refs(self):
        """after-dispatch accepts when commit_refs exactly equals
        git rev-list --reverse base..head (order + completeness)."""
        self._init_git()
        base = self._git_commit("baseline")
        mid = self._git_commit("middle")
        head = self._git_commit("head")
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref=base),
        ])
        self._make_apply_run(implementation=impl)
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        rc, out, _ = run_workflow(self.tmp, "after-dispatch",
                                  agent="implement-agent", slice_id="slice-a",
                                  value=json.dumps({
                                      "status": "success", "evidence": {},
                                      "artifacts": {
                                          "head_ref": head,
                                          "commit_refs": [mid, head],  # exact ordered
                                          "base_ref": base,
                                      },
                                  }))
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl = state["implementation"]["slices"][0]
        self.assertEqual(sl["status"], "in_review")


# ---------------------------------------------------------------------------
# Review-blocker remediation round 3: global acceptance-order commit boundary
# and complete live Git scope for success handoff.
# ---------------------------------------------------------------------------


class TestReviewBlockerRemediation3(FixtureBase):
    """Round-3 coverage for the two authoritative review blockers:

    * The sequential commit boundary must be **global acceptance-order** based,
      not dependency-relative.  Any later slice — including one that does NOT
      depend on A — must use the previous globally accepted slice head as
      ``base_ref``.  In an A/B/C scenario where B does NOT depend on A, B must
      still start from A's ``accepted_head_ref`` once A is accepted.
    * The success handoff must report the **complete current live Git scope**,
      not only remediation files.  The implement-agent contract must require
      deriving structured ``changed_files`` from current tracked + untracked
      Git state.
    """

    def _make_apply_run(self, implementation=None, flow_type="spec-flow",
                        run_id="2026-07-13-review-blockers-r3"):
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": flow_type,
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "review-blockers-r3"},
            "context": {"change_id": "review-blockers-r3"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    # --- Blocker 1: global acceptance-order commit boundary ---

    def test_validation_rejects_b_not_based_on_a_when_a_accepted(self):
        """B does NOT depend on A, but A was accepted first (global acceptance
        order).  B's base_ref must equal A's accepted_head_ref, not the initial
        base.  If B's base_ref is still the initial base, validation must flag
        commit_chain_violation."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="completed",
                        accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", depends_on=[], status="in_progress",
                        base_ref="base-0"),  # WRONG — should be head-a
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("commit_chain_violation", reasons)

    def test_validation_accepts_b_based_on_a_when_a_accepted(self):
        """B does NOT depend on A, but A was accepted first.  B's base_ref
        equals A's accepted_head_ref — validation must NOT flag
        commit_chain_violation."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="completed",
                        accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", depends_on=[], status="in_progress",
                        base_ref="head-a"),  # correct global acceptance order
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        if rc != 0:
            data = json.loads(out)
            reasons = [e.get("reason", "") for e in data.get("errors", [])]
            self.assertNotIn("commit_chain_violation", reasons)

    def test_e2e_b_uses_a_accepted_head_even_without_dependency(self):
        """End-to-end: A and B are independently ready (B does NOT depend on A).
        After A is implemented and reviewed (accepted_head_ref=head-a), B must
        be dispatched with base_ref=head-a (the previous globally accepted
        head), not the initial base-0."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="ready",
                        base_ref="base-0"),
            _make_slice("slice-b", depends_on=[], status="pending",
                        base_ref="base-0"),
        ])
        self._make_apply_run(implementation=impl)

        # Implement + review A
        run_workflow(self.tmp, "before-dispatch",
                     agent="implement-agent", slice_id="slice-a")
        run_workflow(self.tmp, "after-dispatch",
                     agent="implement-agent", slice_id="slice-a",
                     value=json.dumps({
                         "status": "success", "evidence": {},
                         "artifacts": {"head_ref": "head-a",
                                       "commit_refs": ["c-a"],
                                       "base_ref": "base-0"},
                     }))
        run_workflow(self.tmp, "after-dispatch",
                     agent="review-agent", slice_id="slice-a",
                     value=json.dumps({"status": "success",
                                       "evidence": {"review_passed": True}}))

        # slice-next must return slice-b (declaration order, A completed)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "slice-b")

        # before-dispatch for B must set base_ref to head-a (global acceptance)
        rc, out, _ = run_workflow(self.tmp, "before-dispatch",
                                  agent="implement-agent", slice_id="slice-b")
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        sl_b = [s for s in state["implementation"]["slices"]
                if s["slice_id"] == "slice-b"][0]
        self.assertEqual(sl_b["base_ref"], "head-a",
                         "B must use A's accepted_head_ref as base_ref "
                         "(global acceptance order), not the initial base")

    def test_validation_accepts_abc_where_b_independent_but_chained(self):
        """Full A/B/C scenario: A accepted (head-a), B independent of A but
        must chain from head-a, B accepted (head-b), C depends on both and
        must chain from head-b.  Validation must accept this as a valid
        global acceptance-order chain."""
        impl = _make_implementation_state([
            _make_slice("slice-a", depends_on=[], status="completed",
                        accepted_head_ref="head-a",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-b", depends_on=[], status="completed",
                        base_ref="head-a", accepted_head_ref="head-b",
                        review_evidence={"review_passed": True}),
            _make_slice("slice-c", depends_on=["slice-a", "slice-b"],
                        status="in_progress", base_ref="head-b"),
        ])
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(self.tmp, "slice-status")
        if rc != 0:
            data = json.loads(out)
            reasons = [e.get("reason", "") for e in data.get("errors", [])]
            self.assertNotIn("commit_chain_violation", reasons)


# ---------------------------------------------------------------------------
# Sliced Apply-Change Assessment Gate: fresh-run bypass capture (Task 1)
# ---------------------------------------------------------------------------


class TestAssessmentGateFreshRun(FixtureBase):
    """Task 1: a fresh apply-ready run must be blocked for slicing assessment."""

    def _start_apply_ready_run(self, subject_id="assessment-gate"):
        """Start an apply-ready lightweight run via the CLI.

        A matching superpowers plan causes phase inference to select
        apply_change. The helper must invoke the CLI rather than
        constructing the final run state directly.
        """
        self._make_superpowers_plan(f"2026-07-13-{subject_id}.md")
        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            workflow="sdlc-main",
            subject_type="spec_change",
            subject_id=subject_id,
            flow_type="lightweight-flow",
        )
        self.assertEqual(rc, 0, out)
        return json.loads(out)

    def test_fresh_apply_ready_run_is_blocked_for_slicing_assessment(self):
        self._start_apply_ready_run()
        state = self._read_current_state()

        self.assertEqual(state["current_phase"], "apply_change")
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "slicing_assessment_required")
        self.assertEqual(
            state["implementation"]["slicing_assessment"]["status"],
            "pending",
        )
        self.assertEqual(state["implementation"]["slices"], [])

    def test_fresh_apply_ready_run_rejects_direct_implement_dispatch(self):
        self._start_apply_ready_run()
        rc, out, _ = run_workflow(
            self.tmp,
            "before-dispatch",
            agent="implement-agent",
            phase="apply_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("slicing_assessment_pending", reasons)

    def test_fresh_apply_ready_run_rejects_direct_review_dispatch(self):
        """Review-agent is also blocked when slicing assessment is pending.
        Assessment gating is symmetric for implement-agent and review-agent."""
        self._start_apply_ready_run()
        rc, out, _ = run_workflow(
            self.tmp,
            "before-dispatch",
            agent="review-agent",
            phase="apply_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("slicing_assessment_pending", reasons)

    def test_apply_run_with_blocked_assessment_rejects_review_dispatch(self):
        """Review-agent is blocked when assessment status is 'blocked'."""
        self._start_apply_ready_run()
        state = self._read_current_state()
        state["implementation"]["slicing_assessment"]["status"] = "blocked"
        state["implementation"]["slicing_assessment"]["reasons"] = ["test block"]
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp,
            "before-dispatch",
            agent="review-agent",
            phase="apply_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("slicing_assessment_blocked", reasons)

    def test_slice_next_reports_assessment_required_before_materialization(self):
        self._start_apply_ready_run()
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(out), {
            "status": "assessment_required",
            "reason": "slicing_assessment_pending",
            "recommended_next_action": "dispatch_plan_agent_for_slicing_assessment",
        })


# ---------------------------------------------------------------------------
# Sliced Apply-Change Assessment Gate: persisted gate (Task 2)
# ---------------------------------------------------------------------------


class TestAssessmentGatePersisted(FixtureBase):
    """Task 2: active apply missing implementation requires explicit repair;
    terminal legacy runs remain readable."""

    def _make_apply_run(self, implementation=None, status="running"):
        run_id = "2026-07-13-assessment-gate"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": status,
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "assessment-gate"},
            "context": {"change_id": "assessment-gate"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    def _make_terminal_run_without_implementation(self):
        run_id = "2026-07-13-legacy-terminal"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {"type": "spec_change", "id": "legacy-terminal"},
            "context": {"change_id": "legacy-terminal"},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change", "archive_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        self._write_current_state(state)
        return run_id

    def test_active_apply_missing_implementation_requires_explicit_repair(self):
        self._make_apply_run(implementation=None)
        rc, out, _ = run_workflow(
            self.tmp,
            "before-dispatch",
            agent="implement-agent",
            phase="apply_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [item["reason"] for item in data.get("blockers", [])]
        self.assertIn("missing_slicing_assessment", reasons)

    def test_terminal_legacy_run_remains_readable(self):
        self._make_terminal_run_without_implementation()
        rc, out, _ = run_workflow(self.tmp, "status")
        self.assertEqual(rc, 0, out)


# ---------------------------------------------------------------------------
# Sliced Apply-Change Assessment Gate: slice-init legacy repair (Task 3)
# ---------------------------------------------------------------------------


class TestSliceInit(FixtureBase):
    """Task 3: explicit legacy run initialization via slice-init command."""

    def _make_apply_run(self, implementation=None, status="running", flow_type="spec-flow"):
        run_id = "2026-07-13-slice-init"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": flow_type,
            "status": status,
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "slice-init"},
            "context": {"change_id": "slice-init"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    def _make_non_apply_run(self):
        run_id = "2026-07-13-slice-init-wrong-phase"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "create_change",
            "primary_subject": {"type": "spec_change", "id": "slice-init-wrong"},
            "context": {"change_id": "slice-init-wrong"},
            "phase_readiness": {"phase": "create_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        self._write_current_state(state)
        return run_id

    def _make_valid_implementation(self):
        return _make_implementation_state(
            [_make_slice("default", status="pending")],
            assessment_status="completed",
            decision="single_slice",
        )

    def _make_malformed_implementation(self):
        return {
            "strategy": "sequential",
            "slicing_assessment": {"status": "completed", "decision": "multi_slice"},
            "aggregate_review_status": "pending",
            "active_slice_id": None,
            "slices": [],
        }

    def test_slice_init_creates_pending_state_for_missing_implementation(self):
        self._make_apply_run(implementation=None)
        rc, out, _ = run_workflow(
            self.tmp, "slice-init",
            reason="Active run was created without persisted slicing assessment",
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "slicing_assessment_required")
        self.assertEqual(state["implementation"]["slicing_assessment"]["status"], "pending")
        self.assertEqual(state["implementation"]["slices"], [])
        # Migration evidence recorded
        migrations = state.get("slicing_migrations", [])
        self.assertEqual(len(migrations), 1)
        self.assertEqual(migrations[0]["action"], "slice_init")
        self.assertEqual(migrations[0]["reason"], "Active run was created without persisted slicing assessment")
        self.assertEqual(migrations[0]["previous_implementation_present"], False)

    def test_slice_init_requires_reason(self):
        self._make_apply_run(implementation=None)
        rc, out, _ = run_workflow(self.tmp, "slice-init")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("missing_repair_reason", reasons)

    def test_slice_init_rejects_non_apply_phase(self):
        self._make_non_apply_run()
        rc, out, _ = run_workflow(
            self.tmp, "slice-init",
            reason="wrong phase",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("slice_init_wrong_phase", reasons)

    def test_slice_init_idempotent_for_valid_implementation(self):
        impl = self._make_valid_implementation()
        self._make_apply_run(implementation=impl)
        state_before = self._read_current_state()
        rc, out, _ = run_workflow(
            self.tmp, "slice-init",
            reason="already initialized",
        )
        self.assertEqual(rc, 0, out)
        state_after = self._read_current_state()
        # State should be unchanged for already-valid implementation
        self.assertEqual(
            state_after["implementation"]["slicing_assessment"]["status"],
            state_before["implementation"]["slicing_assessment"]["status"],
        )
        self.assertEqual(
            len(state_after["implementation"]["slices"]),
            len(state_before["implementation"]["slices"]),
        )

    def test_slice_init_rejects_malformed_implementation(self):
        impl = self._make_malformed_implementation()
        self._make_apply_run(implementation=impl)
        rc, out, _ = run_workflow(
            self.tmp, "slice-init",
            reason="trying to repair",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("existing_implementation_invalid", reasons)

    def test_slice_init_clears_unconsumed_implement_intent(self):
        self._make_apply_run(implementation=None)
        state = self._read_current_state()
        state.setdefault("evidence", {})["agent_phase"] = {
            "agent": "implement-agent",
            "agent_phase": "apply_change",
            "dispatched_at": "2026-07-13T00:00:00",
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "slice-init",
            reason="clearing stale intent",
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        # The stale implement-agent dispatch intent should be cleared
        agent_phase = state.get("evidence", {}).get("agent_phase")
        self.assertTrue(agent_phase is None or agent_phase.get("agent") != "implement-agent")
        # Migration evidence should record the intent clearing
        migrations = state.get("slicing_migrations", [])
        self.assertTrue(any(m.get("cleared_dispatch_intent") for m in migrations))

    def test_slice_init_refuses_destructive_repair_when_matching_result_exists(self):
        self._make_apply_run(implementation=None)
        state = self._read_current_state()
        state.setdefault("evidence", {})["agent_phase"] = {
            "agent": "implement-agent",
            "agent_phase": "apply_change",
            "dispatched_at": "2026-07-13T00:00:00",
        }
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["implement-agent"] = {
            "agent": "implement-agent",
            "status": "success",
            "phase": "apply_change",
            "slice_id": "default",
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "slice-init",
            reason="trying to clear with result",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [e.get("reason", "") for e in data.get("errors", [])]
        self.assertIn("matching_agent_result_exists", reasons)

    def test_slice_init_does_not_touch_worktree_files(self):
        """slice-init must not modify any worktree source/test/doc files."""
        import subprocess
        # Create a git repo fixture with a sentinel file
        self._make_apply_run(implementation=None)
        sentinel_path = os.path.join(self.tmp, "sentinel_source.py")
        sentinel_content = "# sentinel content\nprint('hello')\n"
        with open(sentinel_path, "w") as f:
            f.write(sentinel_content)
        # Initialize git repo and commit
        subprocess.run(["git", "init"], cwd=self.tmp, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=self.tmp, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=self.tmp, capture_output=True,
            env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
                 "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com"},
        )
        # Record porcelain status before
        r = subprocess.run(["git", "status", "--short"], cwd=self.tmp, capture_output=True, text=True)
        status_before = r.stdout.strip()
        # Read sentinel content before
        with open(sentinel_path) as f:
            content_before = f.read()

        rc, out, _ = run_workflow(
            self.tmp, "slice-init",
            reason="testing worktree preservation",
        )
        self.assertEqual(rc, 0, out)

        # Verify sentinel content unchanged
        with open(sentinel_path) as f:
            content_after = f.read()
        self.assertEqual(content_after, content_before)
        # Verify only run.json changed (workflow state), not source files
        r = subprocess.run(["git", "status", "--short"], cwd=self.tmp, capture_output=True, text=True)
        status_after = r.stdout.strip()
        # The only change should be to .ai/workflows/runs/active/.../run.json
        changed_files = [line.split(None, 1)[-1] for line in status_after.splitlines() if line.strip()]
        for f in changed_files:
            self.assertTrue(
                f.startswith(".ai/workflows/") or f == ".ai/workflows/runs/current.json",
                f"Unexpected file changed by slice-init: {f}",
            )


# ---------------------------------------------------------------------------
# Sliced Apply-Change Assessment Gate: plan-agent remediation routing (Task 4)
# ---------------------------------------------------------------------------


class TestSlicingAssessmentRemediation(FixtureBase):
    """Task 4: blocked apply accepts plan-agent only for assess_implementation_slicing."""

    def _start_blocked_apply_run(self, subject_id="remediation-test"):
        self._make_superpowers_plan(f"2026-07-13-{subject_id}.md")
        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            workflow="sdlc-main",
            subject_type="spec_change",
            subject_id=subject_id,
            flow_type="lightweight-flow",
        )
        self.assertEqual(rc, 0, out)
        return json.loads(out)

    def test_normal_plan_agent_dispatch_in_running_apply_rejected(self):
        self._start_blocked_apply_run()
        state = self._read_current_state()
        state["status"] = "running"
        state["block"] = None
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="plan-agent",
            phase="apply_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("agent_not_allowed_for_phase", reasons)

    def test_blocked_apply_accepts_plan_agent_for_assessment_remediation(self):
        self._start_blocked_apply_run()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="plan-agent",
            phase="apply_change",
            action="assess_implementation_slicing",
        )
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")

    def test_blocked_apply_rejects_plan_agent_with_wrong_action(self):
        self._start_blocked_apply_run()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="plan-agent",
            phase="apply_change",
            action="some_other_action",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("plan_agent_not_assessment_remediation", reasons)

    def test_blocked_apply_rejects_plan_agent_for_different_blocker_type(self):
        self._start_blocked_apply_run()
        state = self._read_current_state()
        state["block"] = {
            "type": "worker_failed",
            "message": "some other block",
            "next_allowed": ["dispatch_plan_agent"],
        }
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="plan-agent",
            phase="apply_change",
            action="assess_implementation_slicing",
        )
        self.assertNotEqual(rc, 0)

    def test_blocked_apply_still_rejects_implement_and_review(self):
        self._start_blocked_apply_run()
        for agent in ("implement-agent", "review-agent"):
            rc, out, _ = run_workflow(
                self.tmp, "before-dispatch",
                agent=agent,
                phase="apply_change",
            )
            self.assertNotEqual(rc, 0, f"{agent} should be blocked")

    def test_assessment_remediation_persists_intent(self):
        self._start_blocked_apply_run()
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="plan-agent",
            phase="apply_change",
            action="assess_implementation_slicing",
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        agent_phase = state.get("evidence", {}).get("agent_phase", {})
        self.assertEqual(agent_phase.get("agent"), "plan-agent")
        self.assertEqual(agent_phase.get("action"), "assess_implementation_slicing")
        self.assertEqual(agent_phase.get("remediation_for"), "slicing_assessment_required")


# ---------------------------------------------------------------------------
# Sliced Apply-Change Assessment Gate: materialization (Task 5)
# ---------------------------------------------------------------------------


class TestAssessmentMaterialization(FixtureBase):
    """Task 5: plan-agent assessment is atomically materialized into implementation state."""

    def _start_blocked_apply_run(self, subject_id="materialization-test"):
        self._make_superpowers_plan(f"2026-07-13-{subject_id}.md")
        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            workflow="sdlc-main",
            subject_type="spec_change",
            subject_id=subject_id,
            flow_type="lightweight-flow",
        )
        self.assertEqual(rc, 0, out)

    def _dispatch_remediation(self):
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="plan-agent",
            phase="apply_change",
            action="assess_implementation_slicing",
        )
        self.assertEqual(rc, 0, out)

    def _single_assessment_result(self):
        return {
            "status": "success",
            "slicing_assessment": {
                "decision": "single_slice",
                "confidence": "high",
                "reasons": ["One behavior and one verification boundary"],
                "signals": {
                    "independent_behaviors": 1,
                    "dependency_layers": 1,
                    "expected_core_files": 2,
                    "cross_module_boundaries": 0,
                    "independent_verification_boundaries": 1,
                    "migration_or_compatibility_work": False,
                    "multiple_external_integrations": False,
                    "high_debug_uncertainty": False,
                },
                "implementation_slices": [],
            },
            "evidence": {},
            "blockers": [],
            "artifacts": {"handoff_path": ".ai/workflows/runs/test/handoffs/plan-agent.md"},
        }

    def _multi_assessment_result(self):
        return {
            "status": "success",
            "slicing_assessment": {
                "decision": "multi_slice",
                "confidence": "high",
                "reasons": ["Multiple independent behaviors"],
                "signals": {
                    "independent_behaviors": 2,
                    "dependency_layers": 2,
                    "expected_core_files": 4,
                    "cross_module_boundaries": 1,
                    "independent_verification_boundaries": 2,
                    "migration_or_compatibility_work": False,
                    "multiple_external_integrations": False,
                    "high_debug_uncertainty": False,
                },
                "task_coverage": {
                    "slice-a": ["task-1"],
                    "slice-b": ["task-2"],
                },
                "implementation_slices": [
                    {
                        "slice_id": "slice-a",
                        "depends_on": [],
                        "required": True,
                        "scope": "Implement core dispatch gate logic",
                        "verification_commands": ["python3 -m pytest tests/ -k slice_a"],
                    },
                    {
                        "slice_id": "slice-b",
                        "depends_on": ["slice-a"],
                        "required": True,
                        "scope": "Implement state validation and materialization",
                        "verification_commands": ["python3 -m pytest tests/ -k slice_b"],
                    },
                ],
            },
            "evidence": {},
            "blockers": [],
            "artifacts": {"handoff_path": ".ai/workflows/runs/test/handoffs/plan-agent.md"},
        }

    def test_single_assessment_materializes_default_slice(self):
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        impl = state["implementation"]
        self.assertEqual(impl["slicing_assessment"]["status"], "completed")
        self.assertEqual(impl["slicing_assessment"]["decision"], "single_slice")
        self.assertEqual(len(impl["slices"]), 1)
        self.assertEqual(impl["slices"][0]["slice_id"], "default")
        self.assertEqual(state["status"], "running")
        self.assertIsNone(state.get("block"))

    def test_multi_assessment_preserves_order_and_dependencies(self):
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._multi_assessment_result()
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        impl = state["implementation"]
        self.assertEqual(impl["slicing_assessment"]["decision"], "multi_slice")
        self.assertEqual(len(impl["slices"]), 2)
        self.assertEqual(impl["slices"][0]["slice_id"], "slice-a")
        self.assertEqual(impl["slices"][1]["slice_id"], "slice-b")
        self.assertEqual(impl["slices"][1]["depends_on"], ["slice-a"])

    def test_invalid_decision_leaves_run_blocked(self):
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        result["slicing_assessment"]["decision"] = "invalid"
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "slicing_assessment_required")

    def test_empty_reasons_leaves_run_blocked(self):
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        result["slicing_assessment"]["reasons"] = []
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "slicing_assessment_required")

    def test_blocked_assessment_preserves_blocker(self):
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        result["slicing_assessment"]["decision"] = "blocked"
        result["slicing_assessment"]["reasons"] = ["Insufficient confidence in decomposition"]
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "slicing_assessment_required")
        impl = state["implementation"]
        self.assertEqual(impl["slicing_assessment"]["status"], "blocked")

    def test_stale_plan_agent_result_cannot_materialize(self):
        """A plan-agent result without matching dispatch intent cannot update implementation."""
        self._start_blocked_apply_run()
        # Don't dispatch remediation first; just send after-dispatch
        result = self._single_assessment_result()
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        # Should remain blocked - no matching dispatch intent
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "slicing_assessment_required")

    def test_materialization_then_slice_next(self):
        """After materialization, slice-next should select the first slice."""
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "default")

    def test_materialization_rejects_empty_reasons(self):
        """Assessment materialization must reject empty reasons array."""
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        result["slicing_assessment"]["reasons"] = []
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        # Run must remain blocked — materialization refused empty reasons
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "slicing_assessment_required")

    def test_materialization_rejects_invalid_confidence(self):
        """Assessment materialization must reject invalid confidence values."""
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        result["slicing_assessment"]["confidence"] = "unknown"
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "slicing_assessment_required")

    def test_materialization_rejects_missing_signals(self):
        """Assessment materialization must reject missing signals object."""
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        del result["slicing_assessment"]["signals"]
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")

    def test_materialization_rejects_invalid_signals_field(self):
        """Assessment materialization must reject signals with invalid field types."""
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._single_assessment_result()
        result["slicing_assessment"]["signals"]["independent_behaviors"] = "many"
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")

    def test_materialization_rejects_missing_task_coverage_for_multi_slice(self):
        """Multi-slice assessment must include task_coverage mapping."""
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._multi_assessment_result()
        # Remove task_coverage if present
        result["slicing_assessment"].pop("task_coverage", None)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")

    def test_materialization_rejects_slice_without_scope(self):
        """Slice contracts in multi-slice assessments must include scope."""
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._multi_assessment_result()
        # Remove scope from one slice
        result["slicing_assessment"]["implementation_slices"][0].pop("scope", None)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")

    def test_materialization_rejects_slice_without_verification_commands(self):
        """Slice contracts in multi-slice assessments must include verification_commands."""
        self._start_blocked_apply_run()
        self._dispatch_remediation()
        result = self._multi_assessment_result()
        # Remove verification_commands from one slice
        result["slicing_assessment"]["implementation_slices"][0].pop("verification_commands", None)
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="plan-agent",
            phase="apply_change",
            value=json.dumps(result),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")


# ---------------------------------------------------------------------------
# Sliced Apply-Change Assessment Gate: no-decomposition semantics (Task 6)
# ---------------------------------------------------------------------------


class TestNoDecomposition(FixtureBase):
    """Task 6: explicit no-decomposition requires a non-empty reason."""

    def _make_apply_run(self, implementation=None):
        run_id = "2026-07-13-no-decomp"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "no-decomp"},
            "context": {"change_id": "no-decomp"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
        }
        if implementation is not None:
            state["implementation"] = implementation
        self._write_current_state(state)
        return run_id

    def test_skip_assessment_requires_reason(self):
        self._make_apply_run(implementation=None)
        rc, out, _ = run_workflow(self.tmp, "slice-init", skip_assessment=True)
        self.assertNotEqual(rc, 0)

    def test_skip_assessment_materializes_default(self):
        self._make_apply_run(implementation=None)
        rc, out, _ = run_workflow(
            self.tmp, "slice-init",
            skip_assessment=True,
            reason="User explicitly selected one governed implementation slice",
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        impl = state["implementation"]
        self.assertEqual(impl["slicing_assessment"]["status"], "not_required")
        self.assertEqual(impl["slicing_assessment"]["decision"], "single_slice")
        self.assertEqual(impl["slicing_assessment"]["assessed_by"], "user")
        self.assertEqual(len(impl["slices"]), 1)
        self.assertEqual(impl["slices"][0]["slice_id"], "default")
        self.assertEqual(state["status"], "running")
        self.assertIsNone(state.get("block"))

    def test_explicit_default_slice_requires_slice_id_for_dispatch(self):
        """After skip-assessment, implement dispatch must use --slice-id default."""
        self._make_apply_run(implementation=None)
        run_workflow(
            self.tmp, "slice-init",
            skip_assessment=True,
            reason="User explicitly selected one governed implementation slice",
        )
        # slice-next should return dispatch_slice for default
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_slice")
        self.assertEqual(data["slice_id"], "default")
        # before-dispatch with --slice-id default should succeed
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            phase="apply_change",
            slice_id="default",
        )
        self.assertEqual(rc, 0, out)

    def test_non_legacy_default_slice_requires_slice_id_for_dispatch(self):
        """After assessment is materialized, implement-agent dispatch
        without --slice-id must be rejected even for single-default slices.
        There is no backward-compat omission for any active dispatch."""
        self._make_apply_run(implementation=None)
        # First materialize via skip_assessment, then override to completed.
        run_workflow(
            self.tmp, "slice-init",
            skip_assessment=True,
            reason="User explicitly selected one governed implementation slice",
        )
        # Now override the assessment status to "completed" via direct state write
        state = self._read_current_state()
        state["implementation"]["slicing_assessment"]["status"] = "completed"
        self._write_current_state(state)
        # Dispatch without --slice-id should be blocked (non-legacy)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            phase="apply_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("missing_slice_id", reasons)

    def test_legacy_not_required_single_default_allows_omit_slice_id(self):
        """When assessment_status is 'not_required', implement-agent dispatch
        without --slice-id is REJECTED — all active dispatches require
        --slice-id regardless of assessment status (Invariants 8, 12)."""
        self._make_apply_run(implementation=None)
        run_workflow(
            self.tmp, "slice-init",
            skip_assessment=True,
            reason="User explicitly selected one governed implementation slice",
        )
        # Dispatch without --slice-id should be rejected
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="implement-agent",
            phase="apply_change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        reasons = [b.get("reason", "") for b in data.get("blockers", [])]
        self.assertIn("missing_slice_id", reasons)


# ---------------------------------------------------------------------------
# Sliced Apply-Change Assessment Gate: single-slice review (Task 7)
# ---------------------------------------------------------------------------


class TestSingleSliceReview(FixtureBase):
    """Task 7: single-slice review pass sets aggregate to passed, no aggregate review."""

    def _make_apply_run_with_single_slice(self):
        run_id = "2026-07-13-single-review"
        impl = _make_implementation_state(
            [_make_slice("default", status="in_review", head_ref="head-1",
                         commit_refs=["commit-1"], base_ref="base-1")],
            assessment_status="completed",
            decision="single_slice",
        )
        impl["active_slice_id"] = "default"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "single-review"},
            "context": {"change_id": "single-review"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
            "implementation": impl,
        }
        self._write_current_state(state)
        return run_id

    def test_single_slice_review_pass_sets_aggregate_passed(self):
        self._make_apply_run_with_single_slice()
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            phase="apply_change",
            slice_id="default",
            value=json.dumps({
                "status": "success",
                "evidence": {"review_passed": True},
                "blockers": [],
                "artifacts": {},
            }),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        impl = state["implementation"]
        default_slice = impl["slices"][0]
        self.assertEqual(default_slice["status"], "completed")
        self.assertEqual(default_slice["accepted_head_ref"], "head-1")
        self.assertEqual(impl["aggregate_review_status"], "passed")

    def test_single_slice_slice_next_returns_all_complete(self):
        self._make_apply_run_with_single_slice()
        # First complete the review
        run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            phase="apply_change",
            slice_id="default",
            value=json.dumps({
                "status": "success",
                "evidence": {"review_passed": True},
                "blockers": [],
                "artifacts": {},
            }),
        )
        # Then slice-next should return all_slices_and_aggregate_complete
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "all_slices_and_aggregate_complete")

    def test_multi_slice_review_sets_aggregate_ready(self):
        """For multi-slice, all reviews complete sets aggregate to ready (not passed)."""
        run_id = "2026-07-13-multi-review"
        impl = _make_implementation_state(
            [
                _make_slice("slice-a", status="completed",
                            accepted_head_ref="head-a",
                            review_evidence={"review_passed": True}),
                _make_slice("slice-b", status="in_review", head_ref="head-b",
                            commit_refs=["commit-b"], base_ref="head-a"),
            ],
            assessment_status="completed",
            decision="multi_slice",
        )
        impl["active_slice_id"] = "slice-b"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "multi-review"},
            "context": {"change_id": "multi-review"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-13T00:00:00",
            "implementation": impl,
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="review-agent",
            phase="apply_change",
            slice_id="slice-b",
            value=json.dumps({
                "status": "success",
                "evidence": {"review_passed": True},
                "blockers": [],
                "artifacts": {},
            }),
        )
        self.assertEqual(rc, 0, out)
        state = self._read_current_state()
        impl = state["implementation"]
        self.assertEqual(impl["aggregate_review_status"], "ready")

        # slice-next should return dispatch_aggregate_review
        rc, out, _ = run_workflow(self.tmp, "slice-next")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatch_aggregate_review")


if __name__ == "__main__":
    unittest.main(verbosity=2)
