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
    os.path.dirname(os.path.abspath(__file__)), "workflow.py"
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
            os.path.dirname(os.path.abspath(__file__)), "..", "definitions"
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

    def _make_roadmap_item(self, item_id, status, openspec_change=None, area="area1", completed_at=None):
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
        fpath = os.path.join(items_dir, f"{item_id}.md")
        with open(fpath, "w") as f:
            f.write(content)

    def _read_current_state(self):
        return load_json(self.tmp, ".ai/workflows/runs/current.json")

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

    def test_start_existing_run_same_subject_suggests_resume(self):
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
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["action"], "resume")

    def test_start_existing_run_different_subject_conflict(self):
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
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["action"], "conflict")


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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

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
                        "..", "definitions"
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
                    state_path = os.path.join(tmp, ".ai/workflows/runs/current.json")
                    with open(state_path, "r") as f:
                        s = json.load(f)
                    s.setdefault("pending_hooks", []).append("roadmap_done_if_relevant")
                    with open(state_path, "w") as f:
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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

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
        rc, out, _ = run_workflow(self.tmp, "resume")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("resume-test", data["run_id"])

    def test_resume_different_subject_conflict(self):
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
        self.assertEqual(data["action"], "conflict")


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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

    def test_done_preserves_current_json(self):
        self._prepare_done_state()
        rc, out, _ = run_workflow(self.tmp, "done")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")
        # current.json should still be there with status done
        current = self._read_current_state()
        self.assertIsNotNone(current)
        self.assertEqual(current["status"], "done")

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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)
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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

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
        with open(
            os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w"
        ) as f:
            json.dump(state, f)

        rc, out, _ = run_workflow(
            self.tmp, "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("archive_change", data.get("completed_phases", []))
        self.assertIn("memory_sync", data.get("pending_hooks", []))
        self.assertIn("roadmap_done_if_relevant", data.get("pending_hooks", []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
