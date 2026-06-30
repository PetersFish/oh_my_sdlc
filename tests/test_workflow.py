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

    def _make_roadmap_item(self, item_id, status, openspec_change=None, area="area1", completed_at=None, slug=None):
        items_dir = os.path.join(
            self.tmp, ".ai", "roadmap", "areas", area, "items"
        )
        os.makedirs(items_dir, exist_ok=True)
        fm = f"id: {item_id}\nstatus: {status}\n"
        if openspec_change:
            fm += f"openspec_change: {openspec_change}\n"
        if completed_at:
            fm += f"completed_at: {completed_at}\n"
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
            self.tmp, "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("archive_change", data.get("completed_phases", []))
        self.assertIn("memory_sync", data.get("pending_hooks", []))
        self.assertIn("roadmap_done_if_relevant", data.get("pending_hooks", []))

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

    # --- no-workflow policy ---

    def test_preflight_superpowers_direct_returns_not_required(self):
        rc, data, _ = self._run_preflight("superpowers_direct")
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "not_required")

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

    # --- ensure-run superpowers_direct returns not_required ---

    def test_ensure_run_superpowers_direct_returns_not_required(self):
        rc, data, _ = self._run_ensure_run("superpowers_direct")
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "not_required")

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
        self.assertEqual(data.get("status"), "blocked")
        self.assertEqual(data.get("flow_type"), "lightweight-flow")
        # Confirm
        run_workflow(self.tmp, "record-evidence", key="lightweight_flow_confirmed", value='"true"')
        rc, out, _ = run_workflow(self.tmp, "resolve")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data.get("flow_type"), "lightweight-flow")
        self.assertEqual(data.get("status"), "running")

    def test_resume_preserves_stored_flow_type(self):
        self._make_roadmap_item("ft-resume", "idea")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="ft-resume",
            flow_type="lightweight-flow",
        )
        # Confirm so flow_type gets persisted
        run_workflow(self.tmp, "record-evidence", key="lightweight_flow_confirmed", value='"true"')
        run_workflow(self.tmp, "resolve")
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

    def test_explicit_lightweight_flow_creates_blocked_run(self):
        """Explicit --flow-type lightweight-flow creates blocked run for user confirmation."""
        self._make_roadmap_item("RM-INFER-001", "idea")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-INFER-001",
            flow_type="lightweight-flow",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data.get("flow_type"), "lightweight-flow")
        self.assertEqual(data["block"]["type"], "user_decision_required")
        self.assertIn("lightweight-flow", data["block"]["message"])
        self.assertIn("confirm_lightweight_flow", data["block"]["next_allowed"])

    def test_confirmation_unblocks_explicit_lightweight_flow(self):
        """Recording confirmation clears the block and sets flow_type to lightweight-flow."""
        self._make_roadmap_item("RM-CONFIRM-001", "idea")
        run_workflow(
            self.tmp, "start",
            subject_type="roadmap_item",
            subject_id="RM-CONFIRM-001",
            flow_type="lightweight-flow",
        )
        # Record the confirmation evidence
        run_workflow(
            self.tmp, "record-evidence",
            key="lightweight_flow_confirmed",
            value='"true"',
        )
        # Resolve should clear the block
        rc, out, _ = run_workflow(self.tmp, "resolve")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIsNone(data.get("block"))
        self.assertEqual(data["status"], "running")
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
        """Falsy JSON values (False, 0, [], {}) are treated as empty evidence."""
        falsy_cases = [
            ("bool_false", False),
            ("int_zero", 0),
            ("empty_list", []),
            ("empty_dict", {}),
        ]
        for key, value in falsy_cases:
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
                    self.assertNotEqual(rc, 0, f"expected failure for {key}={value!r}")
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
            "agent": "test-agent",
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
            slice_id="test-slice-1",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "dispatched")
        self.assertEqual(data["agent"], "implement-agent")
        self.assertEqual(data["recommended_next_action"], "execute_agent")

        state = self._read_current_state()
        agent_phase = state.get("evidence", {}).get("agent_phase", {})
        self.assertEqual(agent_phase["agent"], "implement-agent")
        self.assertEqual(agent_phase["slice_id"], "test-slice-1")

    def test_before_dispatch_defaults_phase_from_state(self):
        self._create_run()
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        self._write_current_state(state)
        rc, out, _ = run_workflow(
            self.tmp, "before-dispatch",
            agent="test-agent",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        phase = data.get("phase", "")
        self.assertNotEqual(phase, "")

    def test_before_dispatch_supports_dash_and_underscore_agents(self):
        cases = [
            ("create_change", ["plan-agent", "plan_agent"]),
            ("apply_change", ["implement-agent", "implement_agent", "test-agent", "test_agent", "review-agent", "review_agent"]),
            ("archive_change", ["finish-agent", "finish_agent"]),
        ]
        for phase, agents in cases:
            self._create_run()
            state = self._read_current_state()
            state["current_phase"] = phase
            self._write_current_state(state)
            for agent in agents:
                rc, out, _ = run_workflow(
                    self.tmp, "before-dispatch",
                    agent=agent,
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
            agent="test-agent",
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
        self.assertEqual(data["recommended_next_action"], "dispatch_test_agent")

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
            agent="test-agent",
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
            "recommended_next_action": "dispatch_test_agent",
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
            "recommended_next_action": "dispatch_test_agent",
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
            agent="test-agent",
            slice_id="slice-b",
            value=second_result,
        )
        self.assertEqual(rc, 0)

        state = self._read_current_state()
        results = state.get("evidence", {}).get("agent_results", {})
        self.assertIn("slice-a", results)
        self.assertIn("slice-b", results)
        self.assertEqual(results["slice-a"]["implement-agent"]["status"], "success")
        self.assertEqual(results["slice-b"]["test-agent"]["status"], "failed")

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

    def test_after_dispatch_implement_agent_does_not_request_review(self):
        """Task 1.9: implement-agent success recommends dispatch_test_agent, not review/complete."""
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
        self.assertNotEqual(data["recommended_next_action"], "dispatch_review_agent")
        self.assertNotEqual(data["recommended_next_action"], "complete_phase")
        self.assertEqual(data["recommended_next_action"], "dispatch_test_agent")
        self.assertEqual(data["workflow_command"], "")

    def test_after_dispatch_test_agent_success_recommends_review(self):
        """Task 1.9: test-agent success recommends dispatch_review_agent."""
        self._create_run()
        agent_result = json.dumps({
            "status": "success",
            "evidence": {"verification_passed": True, "overfit_check_passed": True, "regression_passed": True},
            "blockers": [],
            "recommended_next_action": "dispatch_review_agent",
        })
        rc, out, _ = run_workflow(
            self.tmp, "after-dispatch",
            agent="test-agent",
            value=agent_result,
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["recommended_next_action"], "dispatch_review_agent")

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

    def test_after_dispatch_blocks_success_missing_required_exit_criteria_signal(self):
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
        self.assertEqual(data["workflow_command"], "workflow.py block")
        self.assertEqual(data["blockers"][0]["reason"], "missing_exit_criteria_satisfied")
        self.assertIn("spec_artifacts_done", data["blockers"][0]["message"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
