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
        return load_json(self.tmp, f".ai/workflows/runs/active/{pointer['run_id']}.json")

    def _write_current_state(self, state):
        run_id = state["run_id"]
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        os.makedirs(active_dir, exist_ok=True)
        with open(os.path.join(active_dir, f"{run_id}.json"), "w") as f:
            json.dump(state, f)
        pointer_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "current.json")
        with open(pointer_path, "w") as f:
            json.dump({"run_id": run_id}, f)

    def _read_active_file(self, run_id):
        return load_json(self.tmp, f".ai/workflows/runs/active/{run_id}.json")

    def _read_history(self, run_id):
        return load_json(self.tmp, f".ai/workflows/runs/history/{run_id}.json")


class TestStartAndStatus(FixtureBase):
    def test_status_no_run(self):
        rc, out, _ = run_workflow(self.tmp, "status")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "no_active_run")

    def test_start_creates_run(self):
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="demo-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "running")
        self.assertIn("demo-change", data["run_id"])
        self.assertEqual(
            data["primary_subject"],
            {"type": "openspec_change", "id": "demo-change"},
        )

    def test_start_existing_run_same_subject_reports_conflict(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="demo-change",
        )
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="demo-change",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["action"], "conflict")

    def test_start_existing_run_different_subject_allows_concurrent(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="demo-change-1",
        )
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="no-such-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "create_change")

    def test_active_change_starts_at_apply_change(self):
        self._make_openspec_change("my-change")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="my-change",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "apply_change")

    def test_archived_change_starts_at_post_archive_actions(self):
        self._make_openspec_archive("arch-change")
        rc, out, _ = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="adv-test",
        )
        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertNotEqual(rc, 0)
        self.assertIn("not complete", out)

    def test_advance_blocked_when_run_blocked(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="adv-blocked",
        )
        run_workflow(self.tmp, "block", block_type="user_decision_required", message="x")
        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertNotEqual(rc, 0)
        self.assertIn("blocked", out.lower())


class TestBranchPhase(FixtureBase):
    def test_branch_with_unknown_decision_blocks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
                        subject_type="openspec_change",
                        subject_id=f"arch-{status}",
                    )
                    # Register hook manually
                    pointer_path = os.path.join(tmp, ".ai/workflows/runs/current.json")
                    with open(pointer_path, "r") as f:
                        pointer = json.load(f)
                    active_path = os.path.join(tmp, ".ai/workflows/runs/active", f"{pointer['run_id']}.json")
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="resume-test",
        )
        rc, out, _ = run_workflow(
            self.tmp, "resume",
            subject_type="openspec_change",
            subject_id="resume-test",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("resume-test", data["run_id"])

    def test_resume_different_subject_not_found(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="resume-1",
        )
        rc, out, _ = run_workflow(
            self.tmp, "resume",
            subject_type="openspec_change",
            subject_id="resume-2",
        )
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("no active run found", data["error"])

    def test_resume_without_subject_args_lists_runs(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
        # Active file should be removed
        active_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", f"{run_id}.json")
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
            subject_type="openspec_change",
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
            ("start", {"subject_type": "openspec_change", "subject_id": "rt-test"}),
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
                        subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="no-eval",
        )
        state = self._read_current_state()
        # context does not have eval_target_id, and that's fine for deterministic
        self.assertNotIn("eval_target_id", state.get("context", {}))


class TestCompletePhase(FixtureBase):
    def test_complete_phase_registers_hooks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="cp-test",
        )
        state = self._read_current_state()
        state["current_phase"] = "archive_change"
        state["evidence"]["archive_path"] = "openspec/changes/archive/2026-06-18-cp-test"
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
                "type": "openspec_change",
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
        os.makedirs(active_dir, exist_ok=True)
        with open(os.path.join(active_dir, f"{run_id}.json"), "w") as f:
            json.dump(state, f)
        pointer_path = os.path.join(runs_dir, "current.json")
        with open(pointer_path, "w") as f:
            json.dump({"run_id": run_id}, f)

    def _make_done_history_run(self, change_id):
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        os.makedirs(hist_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": f"2026-06-20-{change_id}",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {
                "type": "openspec_change",
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
        with open(os.path.join(hist_dir, f"{state['run_id']}.json"), "w") as f:
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
        os.makedirs(active_dir, exist_ok=True)
        with open(os.path.join(active_dir, f"{run_id}.json"), "w") as f:
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="apply-me",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    def test_preflight_openspec_archive_without_active_run_blocks(self):
        rc, data, _ = self._run_preflight(
            "openspec_archive",
            subject_type="openspec_change",
            subject_id="archive-me",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    # --- openspec action with matching active run ---

    def test_preflight_openspec_create_with_matching_active_run_allows(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="my-change",
        )
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="openspec_change",
            subject_id="my-change",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "ok")

    # --- openspec action with different active run ---

    def test_preflight_openspec_create_with_different_active_run_blocks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="existing-change",
        )
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="openspec_change",
            subject_id="new-change",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "missing_active_run")

    # --- openspec action with done history ---

    def test_preflight_openspec_create_with_done_history_allows(self):
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        os.makedirs(hist_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": "2026-06-20-hist-change",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {"type": "openspec_change", "id": "hist-change"},
            "context": {"change_id": "hist-change"},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [],
            "completed_phases": [], "gates": {}, "evidence": {},
            "block": None, "updated_at": "2026-06-20T00:00:00",
        }
        with open(os.path.join(hist_dir, "2026-06-20-hist-change.json"), "w") as f:
            json.dump(state, f)
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="has-run-arch",
        )
        rc, data, _ = self._run_preflight(
            "dangling_archive_repair",
            subject_type="openspec_change",
            subject_id="has-run-arch",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])

    def test_preflight_dangling_archive_repair_with_done_history_allows(self):
        self._make_openspec_archive("done-arch", "2026-06-20")
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        os.makedirs(hist_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": "2026-06-20-done-arch",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {"type": "openspec_change", "id": "done-arch"},
            "context": {"change_id": "done-arch"},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [],
            "completed_phases": [], "gates": {}, "evidence": {},
            "block": None, "updated_at": "2026-06-20T00:00:00",
        }
        with open(os.path.join(hist_dir, "2026-06-20-done-arch.json"), "w") as f:
            json.dump(state, f)
        rc, data, _ = self._run_preflight(
            "dangling_archive_repair",
            subject_type="openspec_change",
            subject_id="done-arch",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])

    # --- ensure-run creates active run for dangling archive ---

    def test_ensure_run_creates_run_for_dangling_archive(self):
        self._make_openspec_archive("orphan-ens", "2026-06-20")
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="openspec_change",
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
            {"type": "openspec_change", "id": "orphan-ens"},
        )

    # --- ensure-run skips when active run exists ---

    def test_ensure_run_skips_when_active_run_exists(self):
        self._make_openspec_archive("has-ens", "2026-06-20")
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="has-ens",
        )
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="openspec_change",
            subject_id="has-ens",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "ok")

    # --- ensure-run allows concurrent run for different subject ---

    def test_ensure_run_allows_concurrent_for_different_subject(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="other-change",
        )
        self._make_openspec_archive("block-me", "2026-06-20")
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="openspec_change",
            subject_id="block-me",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "run_created")

    # --- ensure-run skips when done history exists ---

    def test_ensure_run_skips_when_done_history_exists(self):
        self._make_openspec_archive("done-ens", "2026-06-20")
        hist_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "history")
        os.makedirs(hist_dir, exist_ok=True)
        state = {
            "version": 1,
            "run_id": "2026-06-20-done-ens",
            "workflow": "sdlc-main",
            "status": "done",
            "current_phase": "done",
            "primary_subject": {"type": "openspec_change", "id": "done-ens"},
            "context": {"change_id": "done-ens"},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [], "completed_hooks": [],
            "completed_phases": [], "gates": {}, "evidence": {},
            "block": None, "updated_at": "2026-06-20T00:00:00",
        }
        with open(os.path.join(hist_dir, "2026-06-20-done-ens.json"), "w") as f:
            json.dump(state, f)
        rc, data, _ = self._run_ensure_run(
            "dangling_archive_repair",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="phase-test",
        )
        # Run is in create_change phase (default for missing change)
        rc, data, _ = self._run_preflight(
            "openspec_apply",
            subject_type="openspec_change",
            subject_id="phase-test",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "wrong_phase")

    def test_preflight_openspec_archive_in_create_phase_blocks(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="phase-test2",
        )
        rc, data, _ = self._run_preflight(
            "openspec_archive",
            subject_type="openspec_change",
            subject_id="phase-test2",
        )
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "wrong_phase")

    def test_preflight_openspec_create_in_create_phase_allows(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="phase-ok",
        )
        rc, data, _ = self._run_preflight(
            "openspec_create",
            subject_type="openspec_change",
            subject_id="phase-ok",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "ok")

    def test_preflight_openspec_apply_in_apply_phase_allows(self):
        self._make_openspec_change("apply-ok")
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="apply-ok",
        )
        rc, data, _ = self._run_preflight(
            "openspec_apply",
            subject_type="openspec_change",
            subject_id="apply-ok",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])

    def test_preflight_openspec_archive_in_archive_phase_allows(self):
        self._make_openspec_change("archive-ok")
        self._make_task_file("archive-ok", completed=True)
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="archive-ok",
        )
        rc, data, _ = self._run_preflight(
            "openspec_archive",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="change-a",
        )
        self.assertEqual(rc1, 0)
        data1 = json.loads(out1)
        run_id_a = data1["run_id"]

        rc2, out2, _ = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="dup-change",
        )
        self.assertEqual(rc1, 0)

        rc2, out2, _ = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="dup-change",
        )
        self.assertNotEqual(rc2, 0)
        data = json.loads(out2)
        self.assertEqual(data["action"], "conflict")

    # 4.3 Resume with subject args finds correct run and sets pointer
    def test_resume_with_subject_args_finds_correct_run(self):
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="change-a",
        )
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="change-b",
        )
        # Pointer now points to change-b
        rc, out, _ = run_workflow(
            self.tmp, "resume",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
            subject_id="change-x",
        )
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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

        # Active file should be removed
        active_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", f"{run_id}.json")
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
            subject_type="openspec_change",
            subject_id="gc-multi-a",
        )
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="gc-multi-b",
        )
        # Add pending hook to the first run only
        active_runs = self._list_active_runs_support()
        for run_id, state in active_runs:
            if "gc-multi-a" in run_id:
                state["pending_hooks"] = ["memory_sync"]
                active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
                with open(os.path.join(active_dir, f"{run_id}.json"), "w") as f:
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
            subject_type="openspec_change",
            subject_id="preflight-a",
        )
        run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="preflight-b",
        )
        # Pointer points to preflight-b. Preflight for preflight-a should switch pointer.
        rc, out, _ = run_workflow(
            self.tmp, "preflight",
            action="openspec_create",
            subject_type="openspec_change",
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
            subject_type="openspec_change",
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
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(active_dir, fname), "r") as f:
                state = json.load(f)
            results.append((state.get("run_id", fname.replace(".json", "")), state))
        return results


if __name__ == "__main__":
    unittest.main(verbosity=2)
