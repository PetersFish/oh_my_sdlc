# Workflow Finalization Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix workflow finalization so unsliced finish-agent evidence can complete terminal movement and final tail commit includes same-run active deletion cleanup.

**Architecture:** Keep workflow finalization logic inside the modular runtime. `workflow_runtime.state` owns terminal evidence validation; `workflow_runtime.governance` owns final-commit path classification and staging. Tests exercise real workflow commands and real Git fixtures instead of checking source strings.

**Tech Stack:** Python standard library, `unittest`, temporary Git repositories, `.ai/workflows/scripts/workflow.py` CLI, existing template sync tooling.

---

## File Structure

- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
  - Responsibility: terminal movement state validation and active/history state I/O helpers.
- Modify: `.ai/workflows/scripts/workflow_runtime/governance.py`
  - Responsibility: `final-commit` Git status classification, allowlist filtering, staging, commit, and residual reporting.
- Modify: `tests/test_workflow.py`
  - Responsibility: executable behavior regression tests for terminal evidence and final-commit behavior.
- Modify after live runtime changes: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- Modify after live runtime changes: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py`
- Modify after distribution: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- Modify after distribution: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py`
- Modify after distribution: `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- Modify after distribution: `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py`
- Modify after distribution: `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- Modify after distribution: `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py`

### Task 1: Terminal Evidence Default-Slice Regression

**Files:**
- Modify: `tests/test_workflow.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`

- [ ] **Step 1: Add a failing test for unsliced default finish-agent evidence**

In `tests/test_workflow.py`, add this test inside `class TestTerminalEvidenceValidation(FixtureBase):` after `test_advance_proceeds_when_finish_agent_evidence_present`:

```python
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
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestTerminalEvidenceValidation::test_advance_accepts_default_finish_agent_evidence_when_no_dispatch_slice -v
```

Expected: FAIL with `missing_finish_agent_evidence` or an error mentioning slice `terminal-default-slice`.

- [ ] **Step 3: Implement terminal evidence candidate resolution**

In `.ai/workflows/scripts/workflow_runtime/state.py`, replace the relevant-slice block in `_missing_terminal_finish_agent_evidence()` with this logic:

```python
    dispatch_intent_slice_id = (
        state.get("evidence", {}).get("agent_phase", {}).get("slice_id", "")
    ) or ""
    change_id = state.get("context", {}).get("change_id", "") or ""

    if dispatch_intent_slice_id:
        candidate_slice_ids = [dispatch_intent_slice_id]
    else:
        candidate_slice_ids = ["default"]
        if change_id and change_id not in candidate_slice_ids:
            candidate_slice_ids.append(change_id)

    agent_results = state.get("evidence", {}).get("agent_results", {}) or {}
    for candidate_slice_id in candidate_slice_ids:
        by_agent = agent_results.get(candidate_slice_id, {}) or {}
        finish_result = by_agent.get("finish-agent") or by_agent.get("finish_agent")
        if finish_result and finish_result.get("status") == "success":
            return None

    relevant_slice_id = candidate_slice_ids[0]
```

Then update the returned blocker to include the checked candidates:

```python
        "slice_id": relevant_slice_id,
        "candidate_slice_ids": candidate_slice_ids,
```

- [ ] **Step 4: Run terminal evidence tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestTerminalEvidenceValidation -v
```

Expected: PASS, including the existing strict explicit-slice tests.

- [ ] **Step 5: Commit Task 1 if working in a branch**

Run:

```bash
git add tests/test_workflow.py .ai/workflows/scripts/workflow_runtime/state.py
git commit -m "fix(workflow): accept default finish evidence for unsliced runs"
```

Expected: commit succeeds. If this work is managed by an outer workflow that owns commits, skip this local commit and record the reason in the handoff.

### Task 2: Final Commit Active Deletion Regression

**Files:**
- Modify: `tests/test_workflow.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/governance.py`

- [ ] **Step 1: Add a helper for tracked active-run files**

In `class TestFinalCommit(FixtureBase):`, add this helper after `_make_done_history_run`:

```python
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
```

- [ ] **Step 2: Add failing final-commit deletion regression test**

In `class TestFinalCommit(FixtureBase):`, add this test after `test_final_commit_commits_allowed_history_file`:

```python
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
```

- [ ] **Step 3: Add safety test for non-deletion active files**

In `class TestFinalCommit(FixtureBase):`, add this test after the deletion regression test:

```python
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
```

- [ ] **Step 4: Run new final-commit tests and verify at least deletion test fails**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestFinalCommit::test_final_commit_commits_target_active_run_deletions tests/test_workflow.py::TestFinalCommit::test_final_commit_does_not_commit_target_active_run_non_deletions -v
```

Expected before implementation: deletion test FAILS because active deletion paths remain residual or absent from staged paths. Safety test may pass or fail depending on current classification, but must pass after implementation.

- [ ] **Step 5: Implement status-aware final-commit classification**

In `.ai/workflows/scripts/workflow_runtime/governance.py`, replace `_git_dirty_paths()` and `_classify_final_commit_paths()` with status-aware variants while keeping `_git_dirty_paths()` available for callers:

```python
def _git_dirty_paths(root):
    """Return list of dirty paths (relative, POSIX-style) from git status."""
    entries = _git_status_porcelain(root)
    return [path for _, path in entries]


def _is_delete_status(status_code):
    return "D" in (status_code or "")


def _classify_final_commit_entries(entries, run_id):
    """Split dirty status entries into allowed and residual path lists."""
    prefixes = _final_commit_allowed_prefixes(run_id)
    active_run_prefix = f".ai/workflows/runs/active/{run_id}/"
    allowed = []
    residual = []
    for status_code, path in entries:
        if any(path.startswith(prefix) or path == prefix.rstrip("/") for prefix in prefixes):
            allowed.append(path)
        elif path.startswith(active_run_prefix) and _is_delete_status(status_code):
            allowed.append(path)
        else:
            residual.append(path)
    return allowed, residual


def _classify_final_commit_paths(dirty_paths, run_id):
    """Split dirty paths into (allowed, residual) based on the allowlist.

    Path-only classification is retained for existing tests and callers. It
    does not allow active-run cleanup because active paths require Git status
    information to prove they are deletions.
    """
    prefixes = _final_commit_allowed_prefixes(run_id)
    allowed = []
    residual = []
    for path in dirty_paths:
        if any(path.startswith(prefix) or path == prefix.rstrip("/") for prefix in prefixes):
            allowed.append(path)
        else:
            residual.append(path)
    return allowed, residual
```

Then change `cmd_final_commit()` step 2-3 from path-only classification to:

```python
    dirty_entries = _git_status_porcelain(root)
    dirty_paths = [path for _, path in dirty_entries]

    allowed_dirty, residual_dirty = _classify_final_commit_entries(dirty_entries, run_id)
```

Leave the existing post-commit `residual_after = _git_dirty_paths(root)` behavior intact so returned residual paths stay path-only.

- [ ] **Step 6: Run final-commit focused tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestFinalCommit -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2 if working in a branch**

Run:

```bash
git add tests/test_workflow.py .ai/workflows/scripts/workflow_runtime/governance.py
git commit -m "fix(workflow): commit target active run deletions in final tail"
```

Expected: commit succeeds. If this work is managed by an outer workflow that owns commits, skip this local commit and record the reason in the handoff.

### Task 3: Sync Runtime Templates And Distributed Copies

**Files:**
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py`
- Modify: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- Modify: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py`
- Modify: `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- Modify: `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py`
- Modify: `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- Modify: `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py`

- [ ] **Step 1: Sync live workflow runtime to canonical templates**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
```

Expected: command exits 0 and copies live `.ai/workflows/scripts/workflow_runtime/state.py` and `governance.py` into `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/`.

- [ ] **Step 2: Distribute canonical workflow templates**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute
```

Expected: command exits 0 and updates `.opencode/`, `.claude/`, and `.cursor/` workflow template copies.

- [ ] **Step 3: Verify template parity**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed
```

Expected: both commands PASS with no drift.

- [ ] **Step 4: Verify aggregate derived artifact check**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3 if working in a branch**

Run:

```bash
git add skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py \
  skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py \
  .opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py \
  .opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py \
  .claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py \
  .claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py \
  .cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py \
  .cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py
git commit -m "chore(workflow): sync finalization runtime templates"
```

Expected: commit succeeds. If this work is managed by an outer workflow that owns commits, skip this local commit and record the reason in the handoff.

### Task 4: Final Verification

**Files:**
- Verify: `tests/test_workflow.py`
- Verify: `.ai/workflows/scripts/workflow.py`
- Verify: `skills/sdlc-project-bootstrap/scripts/sync_templates.py`

- [ ] **Step 1: Run focused workflow tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestTerminalEvidenceValidation tests/test_workflow.py::TestFinalCommit -v
```

Expected: PASS.

- [ ] **Step 2: Run full workflow test file**

Run:

```bash
python3 -m pytest tests/test_workflow.py -v
```

Expected: PASS.

- [ ] **Step 3: Run full regression suite**

Run:

```bash
python3 -m pytest tests/ -v
```

Expected: PASS.

- [ ] **Step 4: Run final derived artifact check**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

Expected: PASS.

- [ ] **Step 5: Smoke-test workflow CLI**

Run:

```bash
python3 .ai/workflows/scripts/workflow.py --help
```

Expected: exits 0 and lists `final-commit` among commands.

- [ ] **Step 6: Inspect Git status**

Run:

```bash
git status --short
```

Expected: only intended workflow runtime, template, distributed copy, test, spec, and plan files are dirty. No unrelated user files are staged or modified by this plan.

- [ ] **Step 7: Final commit if working in a branch**

Run:

```bash
git add .ai/workflows/scripts/workflow_runtime/state.py \
  .ai/workflows/scripts/workflow_runtime/governance.py \
  tests/test_workflow.py \
  skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py \
  skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py \
  .opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py \
  .opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py \
  .claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py \
  .claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py \
  .cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py \
  .cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py \
  docs/superpowers/specs/2026-07-12-workflow-finalization-repair-design.md \
  docs/superpowers/plans/2026-07-12-workflow-finalization-repair.md
git commit -m "fix(workflow): repair finalization evidence and tail commit cleanup"
```

Expected: commit succeeds. If this work is managed by an outer workflow that owns commits, skip this local commit and record the reason in the handoff.

## Self-Review

- Spec coverage: Task 1 covers default-slice terminal evidence while preserving explicit-slice strictness. Task 2 covers same-run active deletion cleanup and safety for non-deletion active files. Task 3 covers canonical and distributed template sync. Task 4 covers focused and full verification.
- Placeholder scan: no placeholders or deferred implementation steps remain.
- Type consistency: helper names and command names match existing runtime/test conventions: `_missing_terminal_finish_agent_evidence`, `_git_status_porcelain`, `_git_dirty_paths`, `_classify_final_commit_paths`, `cmd_final_commit`, `run_workflow`.
