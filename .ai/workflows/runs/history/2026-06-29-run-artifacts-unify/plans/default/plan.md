# Run Artifacts Unify — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify all run artifacts (JSON state, plans, handoffs, logs) under a single `<run_id>/` directory with `run.json` as the canonical run state file, and auto-migrate legacy top-level handoffs/ and logs/ directories.

**Architecture:** The change is concentrated in `workflow.py`'s path helpers (`_active_path`, `_list_active_runs`, `save_run_state`, `_finalize_run_to_history`, `cmd_done`, `cmd_advance`, `cmd_cancel_run`, `cmd_governance_check`) and a new migration helper. Test files need path updates to match. Agent definitions already use the new path convention and require no changes.

**Tech Stack:** Python 3, `shutil` for directory operations, `json` for state files, `pytest` for testing.

---

## TDD Strategy

Each task group follows test-first discipline:
1. Write the failing test proving the new behavior contract
2. Run the test to verify it fails (proving the old behavior is wrong)
3. Implement the minimal change to make the test pass
4. Run the test to verify it passes
5. Commit

### Test Case Map

| Test Name | What It Verifies | Expected Failure Before Implementation |
|---|---|---|
| `test_active_path_returns_run_json_in_directory` | `_active_path()` returns `active/<run_id>/run.json` | Returns `active/<run_id>.json` |
| `test_save_run_state_creates_directory_with_run_json` | `save_run_state()` creates `active/<run_id>/` + `run.json` | Writes flat `active/<run_id>.json` |
| `test_done_moves_entire_directory_to_history` | `cmd_done()` moves directory with all artifacts | Only moves JSON file |
| `test_cancel_removes_entire_directory` | `cmd_cancel_run()` removes entire dir | Only removes single file |
| `test_list_active_runs_from_directories` | `_list_active_runs()` reads from subdirectories | Reads flat `.json` files |
| `test_governance_check_reads_history_dir` | `governance-check` reads `history/<run_id>/run.json` (new-style only) | Only reads `history/<run_id>.json` |
| `test_legacy_migration_handoffs` | Migrates `runs/handoffs/<run_id>/` to `active/<run_id>/handoffs/` | No migration |
| `test_legacy_migration_logs` | Migrates `runs/logs/<run_id>/` to `active/<run_id>/logs/` | No migration |
| `test_legacy_migration_idempotent` | Migration is safe to run twice | No sentinel check |

### Verification Commands
```bash
python3 -m pytest tests/test_workflow.py -v -k "active_path or save_run_state or done or cancel or list_active or governance_check or legacy_migration"
python3 -m pytest tests/test_init_foundations.py tests/test_wrapper_contracts.py -v
python3 -m pytest tests/ -v  # Full suite
```

### EvalOps Candidates
- `run-directory-unification`: Full-chain verification (create → handoff → log → plan → archive → verify unified directory)
- `run-legacy-migration`: Migration of existing `runs/handoffs/` and `runs/logs/` directories

---

## Task 1: Core Path Changes in workflow.py

### Task 1.1: Change `_active_path()` to return directory-based path

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:99-100`

- [ ] **Step 1: Write the failing test**

```python
def test_active_path_returns_run_json_in_directory(self):
    """_active_path returns active/<run_id>/run.json"""
    from .ai.workflows.scripts.workflow import _active_path
    result = _active_path(self.tmp, "test-run-123")
    expected = os.path.join(self.tmp, ".ai/workflows/runs/active/test-run-123/run.json")
    self.assertEqual(result, os.path.normpath(expected))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_workflow.py::TestActivePath::test_active_path_returns_run_json_in_directory -v`
Expected: FAIL — current code returns `active/test-run-123.json`

- [ ] **Step 3: Change _active_path implementation**

```python
def _active_path(root, run_id):
    return _resolve_path(root, f".ai/workflows/runs/active/{run_id}/run.json")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_workflow.py::TestActivePath::test_active_path_returns_run_json_in_directory -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .ai/workflows/scripts/workflow.py tests/test_workflow.py
git commit -m "feat: change _active_path to return active/<run_id>/run.json"
```

### Task 1.2: Change `save_run_state()` to create directory and write run.json

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:153-160`

- [ ] **Step 1: Write the failing test**

```python
def test_save_run_state_creates_directory_with_run_json(self):
    """save_run_state creates active/<run_id>/ directory and run.json inside"""
    run_id = f"2026-06-29-test-save"
    state = {
        "version": 1, "run_id": run_id, "workflow": "sdlc-main",
        "flow_type": "spec-flow", "status": "running", "current_phase": "create_change",
        "primary_subject": {"type": "feature", "id": "test"},
        "context": {}, "phase_readiness": {"phase": "create_change", "ready": True, "missing_required_inputs": []},
        "pending_hooks": [], "completed_hooks": [], "completed_phases": [],
        "gates": {}, "evidence": {}, "block": None, "updated_at": "2026-01-01T00:00:00"
    }
    save_run_state(self.tmp, state)
    run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
    run_json = os.path.join(run_dir, "run.json")
    self.assertTrue(os.path.isdir(run_dir), f"Expected directory {run_dir} to exist")
    self.assertTrue(os.path.isfile(run_json), f"Expected {run_json} to exist")
    # Verify the old flat file path does NOT exist
    old_path = os.path.join(self.tmp, ".ai/workflows/runs/active", f"{run_id}.json")
    self.assertFalse(os.path.isfile(old_path), f"Old flat file {old_path} should not exist")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_workflow.py -k "test_save_run_state_creates" -v`
Expected: FAIL — directory not created, run.json not found

- [ ] **Step 3: Change save_run_state implementation**

```python
def save_run_state(root, state):
    run_id = state["run_id"]
    path = _active_path(root, run_id)
    _ensure_dir(os.path.dirname(path))
    state["updated_at"] = _ts()
    with open(path, "w") as f:
        json.dump(state, f, indent=2, default=_json_default)
    _set_pointer(root, run_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_workflow.py -k "test_save_run_state_creates" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .ai/workflows/scripts/workflow.py tests/test_workflow.py
git commit -m "feat: save_run_state creates directory and writes run.json inside"
```

### Task 1.3: Change `_finalize_run_to_history()` to move entire directory

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:163-193`

- [ ] **Step 1: Write the failing test**

```python
def test_finalize_run_to_history_moves_entire_directory(self):
    """_finalize_run_to_history moves entire active/<run_id>/ to history/<run_id>/"""
    run_id = "2026-06-29-test-move"
    run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
    os.makedirs(run_dir, exist_ok=True)
    # Create run.json
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
    # Create a handoffs subdirectory
    os.makedirs(os.path.join(run_dir, "handoffs", "default"), exist_ok=True)
    with open(os.path.join(run_dir, "handoffs", "default", "plan-agent.md"), "w") as f:
        f.write("# Test handoff")
    
    # Set pointer
    with open(os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "w") as f:
        json.dump({"run_id": run_id}, f)
    
    _finalize_run_to_history(self.tmp, state)
    
    # Verify active directory is gone
    self.assertFalse(os.path.exists(run_dir), "active directory should be removed")
    # Verify history directory exists with run.json and handoffs
    hist_dir = os.path.join(self.tmp, ".ai/workflows/runs/history", run_id)
    self.assertTrue(os.path.isdir(hist_dir), "history directory should exist")
    self.assertTrue(os.path.isfile(os.path.join(hist_dir, "run.json")), "history run.json should exist")
    self.assertTrue(os.path.isfile(os.path.join(hist_dir, "handoffs", "default", "plan-agent.md")), "handoff should be moved")
    # Verify pointer is cleared
    with open(os.path.join(self.tmp, ".ai/workflows/runs/current.json"), "r") as f:
        ptr = json.load(f)
    self.assertEqual(ptr, {}, "pointer should be cleared")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_workflow.py -k "test_finalize_run_to_history_moves" -v`
Expected: FAIL — directory not moved, handoffs lost

- [ ] **Step 3: Change _finalize_run_to_history implementation**

```python
def _finalize_run_to_history(root, state):
    """Mark an active run done, move it to history, and remove the active directory."""
    state = dict(state)
    state["status"] = "done"
    state["current_phase"] = "done"
    state["phase_readiness"] = {
        "phase": "done",
        "ready": True,
        "missing_required_inputs": [],
    }
    state["pending_hooks"] = []
    state["block"] = None
    state["updated_at"] = _ts()

    run_id = state["run_id"]
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    history_dir = _resolve_path(root, f".ai/workflows/runs/history/{run_id}")

    # Write updated state to run.json inside active directory
    _ensure_dir(active_dir)
    with open(os.path.join(active_dir, "run.json"), "w") as f:
        json.dump(state, f, indent=2)

    # Ensure history parent exists
    _ensure_dir(os.path.dirname(history_dir))

    # Move entire directory
    import shutil
    if os.path.exists(history_dir):
        shutil.rmtree(history_dir)
    shutil.move(active_dir, history_dir)

    pointer = _read_pointer(root)
    if pointer and pointer.get("run_id") == state["run_id"]:
        _clear_pointer(root)

    return state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_workflow.py -k "test_finalize_run_to_history_moves" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .ai/workflows/scripts/workflow.py tests/test_workflow.py
git commit -m "feat: _finalize_run_to_history moves entire directory to history"
```

### Task 1.4: Change `cmd_done()` to move entire directory

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:2149-2219`

- [ ] **Step 1: Write the failing test**

```python
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
    
    # Verify active directory is gone
    self.assertFalse(os.path.exists(run_dir))
    # Verify history directory exists
    hist_dir = os.path.join(self.tmp, ".ai/workflows/runs/history", run_id)
    self.assertTrue(os.path.isdir(hist_dir))
    self.assertTrue(os.path.isfile(os.path.join(hist_dir, "run.json")))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_workflow.py -k "test_cmd_done_moves" -v`
Expected: FAIL

- [ ] **Step 3: Change cmd_done implementation**

```python
def cmd_done(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)

    # ... (existing pending hooks and gates checks remain unchanged) ...

    if state.get("current_phase") != "done":
        print(json.dumps({"error": "run is not in terminal phase", ...}, indent=2))
        sys.exit(1)

    if state.get("status") == "blocked":
        print(json.dumps({"error": "run is blocked, cannot complete"}, indent=2))
        sys.exit(1)

    state["status"] = "done"
    state["updated_at"] = _ts()

    run_id = state["run_id"]
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    history_dir = _resolve_path(root, f".ai/workflows/runs/history/{run_id}")

    # Write final state to run.json
    _ensure_dir(active_dir)
    with open(os.path.join(active_dir, "run.json"), "w") as f:
        json.dump(state, f, indent=2)

    _ensure_dir(os.path.dirname(history_dir))
    import shutil
    if os.path.exists(history_dir):
        shutil.rmtree(history_dir)
    shutil.move(active_dir, history_dir)
    _clear_pointer(root)

    print(json.dumps(state, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_workflow.py -k "test_cmd_done_moves" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .ai/workflows/scripts/workflow.py tests/test_workflow.py
git commit -m "feat: cmd_done moves entire directory to history"
```

### Task 1.5: Change `cmd_advance()` done-phase handling

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:2082-2121`

- [ ] **Step 1: Update the same code path as Task 1.4**

The `cmd_advance()` function at lines 2082-2121 has the same "advance to done" logic. Apply the same change: replace the file-write-then-remove pattern with `shutil.move()` of the entire directory.

- [ ] **Step 2: Run tests to verify**

Run: `python3 -m pytest tests/test_workflow.py -k "advance" -v`
Expected: All advance-related tests pass

- [ ] **Step 3: Commit**

```bash
git add .ai/workflows/scripts/workflow.py
git commit -m "feat: cmd_advance to done moves entire directory"
```

### Task 1.6: Change `cmd_cancel_run()` to remove entire directory

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:1953-1977`

- [ ] **Step 1: Write the failing test**

```python
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
    # Also create an artifact subdirectory
    os.makedirs(os.path.join(run_dir, "handoffs", "default"), exist_ok=True)
    with open(os.path.join(run_dir, "handoffs", "default", "test.md"), "w") as f:
        f.write("test")
    
    rc, out, _ = run_workflow(self.tmp, "cancel-run", subject_type="roadmap_item", subject_id="RM-CANCEL")
    data = json.loads(out)
    self.assertEqual(data["status"], "cancelled")
    self.assertFalse(os.path.exists(run_dir), "entire run directory should be removed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_workflow.py -k "test_cancel_run_removes" -v`
Expected: FAIL — only removes file, directory remains

- [ ] **Step 3: Change cmd_cancel_run implementation**

```python
def cmd_cancel_run(root, args):
    """Remove an active run without writing history. Used for replanned roadmap items."""
    subject_type = args.subject_type or "roadmap_item"
    subject_id = args.subject_id
    reason = args.reason or "cancelled"

    if not subject_id:
        print(json.dumps({"error": "subject-id required for cancel-run"}))
        sys.exit(1)

    active = _find_active_run_by_subject(root, subject_type, subject_id)
    if not active:
        print(json.dumps({"status": "not_found", "message": f"no active run for {subject_type}/{subject_id}"}))
        return

    run_id = active["run_id"]
    pointer = _read_pointer(root)
    if pointer and pointer.get("run_id") == run_id:
        _clear_pointer(root)

    import shutil
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    if os.path.exists(active_dir):
        shutil.rmtree(active_dir)

    print(json.dumps({"status": "cancelled", "run_id": run_id, "reason": reason}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_workflow.py -k "test_cancel_run_removes" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .ai/workflows/scripts/workflow.py tests/test_workflow.py
git commit -m "feat: cmd_cancel_run removes entire directory"
```

### Task 1.7: Change `_list_active_runs()` to iterate subdirectories

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:120-135`

- [ ] **Step 1: Write the failing test**

```python
def test_list_active_runs_from_directories(self):
    """_list_active_runs discovers runs from subdirectories under active/"""
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
    
    active_runs = _list_active_runs(self.tmp)
    self.assertEqual(len(active_runs), 1)
    self.assertEqual(active_runs[0][0], run_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_workflow.py -k "test_list_active_runs_from" -v`
Expected: FAIL — finds 0 runs (looking for `.json` files, not directories)

- [ ] **Step 3: Change _list_active_runs implementation**

```python
def _list_active_runs(root):
    active_dir = _resolve_path(root, ".ai/workflows/runs/active")
    if not os.path.isdir(active_dir):
        return []
    results = []
    for entry in _list_dirs(active_dir):
        entry_path = os.path.join(active_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        run_json_path = os.path.join(entry_path, "run.json")
        if not os.path.isfile(run_json_path):
            continue
        try:
            with open(run_json_path, "r") as f:
                state = json.load(f)
            results.append((state.get("run_id", entry), state))
        except Exception:
            continue
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_workflow.py -k "test_list_active_runs_from" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .ai/workflows/scripts/workflow.py tests/test_workflow.py
git commit -m "feat: _list_active_runs discovers from subdirectories"
```

### Task 1.8: Change `cmd_governance_check()` for new-style paths only

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:2222-2260`

- [ ] **Step 1: Write the failing test**

```python
def test_governance_check_reads_history_dir(self):
    """governance-check reads history/<run_id>/run.json (new-style only)"""
    run_id = "2026-06-29-test-gov"
    hist_dir = os.path.join(self.tmp, ".ai/workflows/runs/history", run_id)
    os.makedirs(hist_dir, exist_ok=True)
    state = {
        "version": 1, "run_id": run_id, "workflow": "sdlc-main",
        "flow_type": "spec-flow", "status": "done", "current_phase": "done",
        "primary_subject": {"type": "openspec_change", "id": "arch-gov"},
        "context": {}, "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
        "pending_hooks": [], "completed_hooks": [], "completed_phases": ["done"],
        "gates": {}, "evidence": {}, "block": None, "updated_at": "2026-01-01T00:00:00"
    }
    with open(os.path.join(hist_dir, "run.json"), "w") as f:
        json.dump(state, f)
    
    rc, out, _ = run_workflow(self.tmp, "governance-check")
    self.assertEqual(rc, 0)
    data = json.loads(out)
    # The governance check should find the done run in history
    self.assertIn("status", data)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_workflow.py -k "test_governance_check_reads_history_dir" -v`
Expected: FAIL — only looks for `history/*.json`, not `history/<run_id>/run.json`

- [ ] **Step 3: Change cmd_governance_check to scan new-style directories only**

```python
# In the history scan loop, replace the flat file iteration with:
if os.path.isdir(history_dir):
    for entry in _list_dirs(history_dir):
        entry_path = os.path.join(history_dir, entry)
        if os.path.isdir(entry_path):
            # New-style: history/<run_id>/run.json
            run_json_path = os.path.join(entry_path, "run.json")
            if os.path.isfile(run_json_path):
                try:
                    with open(run_json_path, "r") as f:
                        hist = json.load(f)
                except Exception:
                    continue
                if hist.get("status") in ("done",):
                    # ... process same as before ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_workflow.py -k "test_governance_check_reads_history_dir" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .ai/workflows/scripts/workflow.py tests/test_workflow.py
git commit -m "feat: governance-check reads new-style history directories"
```

---

## Task 2: Legacy Migration

### Task 2.1: Add `_migrate_legacy_artifacts()` function

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py` (new function near existing helpers)

- [ ] **Step 1: Write the failing test**

```python
def test_legacy_migration_handoffs(self):
    """Legacy handoffs/<run_id>/ is migrated to active/<run_id>/handoffs/"""
    run_id = "2026-06-29-test-legacy"
    # Create legacy handoffs directory
    legacy_dir = os.path.join(self.tmp, ".ai/workflows/runs/handoffs", run_id, "default")
    os.makedirs(legacy_dir, exist_ok=True)
    with open(os.path.join(legacy_dir, "plan-agent.md"), "w") as f:
        f.write("# Legacy handoff")
    
    # Create active run directory (simulating a run that already exists via new path)
    run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    _migrate_legacy_artifacts(self.tmp, run_id)
    
    # Verify migration
    migrated = os.path.join(run_dir, "handoffs", "default", "plan-agent.md")
    self.assertTrue(os.path.isfile(migrated), f"Expected {migrated} to exist")
    # Verify legacy is gone
    self.assertFalse(os.path.exists(legacy_dir), "Legacy directory should be removed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_workflow.py -k "test_legacy_migration_handoffs" -v`
Expected: FAIL — `_migrate_legacy_artifacts` not defined

- [ ] **Step 3: Implement _migrate_legacy_artifacts**

```python
def _migrate_legacy_artifacts(root, run_id):
    """Migrate legacy top-level handoffs/ and logs/ into the run directory."""
    import shutil
    
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    runs_dir = _resolve_path(root, ".ai/workflows/runs")
    
    # Sentinel to prevent re-migration
    sentinel = os.path.join(active_dir, ".migrated")
    if os.path.exists(sentinel):
        return
    
    # Migrate handoffs
    legacy_handoffs = os.path.join(runs_dir, "handoffs", run_id)
    target_handoffs = os.path.join(active_dir, "handoffs")
    if os.path.isdir(legacy_handoffs):
        _ensure_dir(target_handoffs)
        for item in os.listdir(legacy_handoffs):
            src = os.path.join(legacy_handoffs, item)
            dst = os.path.join(target_handoffs, item)
            if not os.path.exists(dst):
                shutil.move(src, dst)
        # Remove empty legacy directory
        try:
            os.rmdir(legacy_handoffs)
        except OSError:
            pass  # Not empty, leave it
    
    # Migrate logs
    legacy_logs = os.path.join(runs_dir, "logs", run_id)
    target_logs = os.path.join(active_dir, "logs")
    if os.path.isdir(legacy_logs):
        _ensure_dir(target_logs)
        for item in os.listdir(legacy_logs):
            src = os.path.join(legacy_logs, item)
            dst = os.path.join(target_logs, item)
            if not os.path.exists(dst):
                shutil.move(src, dst)
        try:
            os.rmdir(legacy_logs)
        except OSError:
            pass
    
    # Create sentinel
    with open(sentinel, "w") as f:
        f.write(_ts())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_workflow.py -k "test_legacy_migration_handoffs" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .ai/workflows/scripts/workflow.py tests/test_workflow.py
git commit -m "feat: add legacy artifact migration for handoffs and logs"
```

### Task 2.2: Add migration idempotency test

**Files:**
- Modify: `tests/test_workflow.py` (add test)

- [ ] **Step 1: Write the test**

```python
def test_legacy_migration_idempotent(self):
    """Migration is safe to run twice without data loss"""
    run_id = "2026-06-29-test-idem"
    legacy_dir = os.path.join(self.tmp, ".ai/workflows/runs/handoffs", run_id, "default")
    os.makedirs(legacy_dir, exist_ok=True)
    with open(os.path.join(legacy_dir, "test.md"), "w") as f:
        f.write("content")
    
    run_dir = os.path.join(self.tmp, ".ai/workflows/runs/active", run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    # First migration
    _migrate_legacy_artifacts(self.tmp, run_id)
    # Second migration should be a no-op
    _migrate_legacy_artifacts(self.tmp, run_id)
    
    # Verify content is still there
    migrated = os.path.join(run_dir, "handoffs", "default", "test.md")
    self.assertTrue(os.path.isfile(migrated))
    with open(migrated, "r") as f:
        self.assertEqual(f.read(), "content")
```

- [ ] **Step 2: Run test**

Run: `python3 -m pytest tests/test_workflow.py -k "test_legacy_migration_idem" -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_workflow.py
git commit -m "test: add idempotency test for legacy migration"
```

### Task 2.3: Call migration from save_run_state and load_run_state

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:153-160` (save_run_state), `:103-117` (load_run_state)

- [ ] **Step 1: Add migration call to save_run_state**

```python
def save_run_state(root, state):
    run_id = state["run_id"]
    path = _active_path(root, run_id)
    _ensure_dir(os.path.dirname(path))
    _migrate_legacy_artifacts(root, run_id)  # <-- ADD THIS
    state["updated_at"] = _ts()
    with open(path, "w") as f:
        json.dump(state, f, indent=2, default=_json_default)
    _set_pointer(root, run_id)
```

- [ ] **Step 2: Add migration call to load_run_state**

```python
def load_run_state(root, run_id=None):
    if run_id is not None:
        path = _active_path(root, run_id)
        if not os.path.exists(path):
            return None
        _migrate_legacy_artifacts(root, run_id)  # <-- ADD THIS
        with open(path, "r") as f:
            return json.load(f)
    # ... rest unchanged
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest tests/test_workflow.py -k "legacy_migration" -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add .ai/workflows/scripts/workflow.py
git commit -m "feat: call legacy migration on save_run_state and load_run_state"
```

---

## Task 3: Test Suite Updates

### Task 3.1: Update test helpers

**Files:**
- Modify: `tests/test_workflow.py:110-130`

- [ ] **Step 1: Update _read_current_state**

```python
def _read_current_state(self):
    pointer = load_json(self.tmp, ".ai/workflows/runs/current.json")
    if not pointer or not pointer.get("run_id"):
        return None
    return load_json(self.tmp, f".ai/workflows/runs/active/{pointer['run_id']}/run.json")
```

- [ ] **Step 2: Update _write_current_state**

```python
def _write_current_state(self, state):
    run_id = state["run_id"]
    active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id)
    os.makedirs(active_dir, exist_ok=True)
    with open(os.path.join(active_dir, "run.json"), "w") as f:
        json.dump(state, f)
    pointer_path = os.path.join(self.tmp, ".ai", "workflows", "runs", "current.json")
    with open(pointer_path, "w") as f:
        json.dump({"run_id": run_id}, f)
```

- [ ] **Step 3: Update _read_active_file**

```python
def _read_active_file(self, run_id):
    return load_json(self.tmp, f".ai/workflows/runs/active/{run_id}/run.json")
```

- [ ] **Step 4: Update _read_history for new-style only**

```python
def _read_history(self, run_id):
    return load_json(self.tmp, f".ai/workflows/runs/history/{run_id}/run.json")
```
- [ ] **Step 5: Run tests to verify**

Run: `python3 -m pytest tests/test_workflow.py -v --timeout=120 2>&1 | head -50`
Expected: Many tests still fail (pending remaining path updates)

- [ ] **Step 6: Commit**

```bash
git add tests/test_workflow.py
git commit -m "test: update helpers for new directory-based paths"
```

### Task 3.2: Update all inline path references in tests

**Files:**
- Modify: `tests/test_workflow.py` (lines 792, 2904, 2940, 2984, 3038, 3523-3524, 3616)

- [ ] **Step 1: Update line 792**

```python
# Old:
active_path = os.path.join(tmp, ".ai/workflows/runs/active", f"{pointer['run_id']}.json")
# New:
active_path = os.path.join(tmp, ".ai/workflows/runs/active", pointer["run_id"], "run.json")
```

- [ ] **Step 2: Update lines 2904, 2940, 2984, 3038**

```python
# Old:
active = load_json(tc, f".ai/workflows/runs/active/{state['run_id']}.json")
# New:
active = load_json(tc, f".ai/workflows/runs/active/{state['run_id']}/run.json")
```

- [ ] **Step 3: Update line 3039**

```python
# Old:
active_path = os.path.join(tc, ".ai", "workflows", "runs", "active", f"{state['run_id']}.json")
# New:
active_path = os.path.join(tc, ".ai", "workflows", "runs", "active", state["run_id"], "run.json")
```

- [ ] **Step 4: Update lines 3523-3524, 3616 (search for remaining `.json` references)**

```bash
grep -n 'active/.*\.json\|\.json"' tests/test_workflow.py
```

- [ ] **Step 5: Verify all references updated**

Run: `python3 -m pytest tests/test_workflow.py -v --timeout=120 2>&1 | tail -30`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add tests/test_workflow.py
git commit -m "test: update all inline path references to directory-based paths"
```

### Task 3.3: Update test_wrapper_contracts.py

**Files:**
- Modify: `tests/test_wrapper_contracts.py` (lines 813, 818, 832, 1188, 1197)

- [ ] **Step 1: Verify path assertions**

The path assertions in test_wrapper_contracts already use `.ai/workflows/runs/run-1/logs/...` and `.ai/workflows/runs/run-1/handoffs/...` which are the new-style paths. Verify they still pass.

Run: `python3 -m pytest tests/test_wrapper_contracts.py -v`
Expected: All pass (no changes needed)

- [ ] **Step 2: Commit if any changes needed**

```bash
git add tests/test_wrapper_contracts.py
git commit -m "test: verify wrapper contract paths with new directory structure"
```

### Task 3.4: Update test_init_foundations.py

**Files:**
- Modify: `tests/test_init_foundations.py` (line 42)

- [ ] **Step 1: Verify the test**

The test at line 42 checks for `runs/history` directory. No change needed.

Run: `python3 -m pytest tests/test_init_foundations.py -v`
Expected: All pass

---

## Task 4: Verification

### Task 4.1: Run full test suite

- [ ] **Step 1: Run workflow tests**

```bash
python3 -m pytest tests/test_workflow.py -v --timeout=120 2>&1
```
Expected: All tests pass

- [ ] **Step 2: Run all tests**

```bash
python3 -m pytest tests/ -v --timeout=120 2>&1
```
Expected: All tests pass (or only pre-existing failures)

### Task 4.2: Handle existing active run

- [ ] **Step 1: Migrate the current active run**

The existing `active/2026-06-29-run-artifacts-unify.json` flat file needs to be migrated to `active/2026-06-29-run-artifacts-unify/run.json`. Run:

```bash
mkdir -p .ai/workflows/runs/active/2026-06-29-run-artifacts-unify
mv .ai/workflows/runs/active/2026-06-29-run-artifacts-unify.json .ai/workflows/runs/active/2026-06-29-run-artifacts-unify/run.json
```

- [ ] **Step 2: Verify the run is still accessible**

```bash
python3 .ai/workflows/scripts/workflow.py --root . status 2>&1
```

### Task 4.3: Verify agent definitions

- [ ] **Step 1: Confirm no agent definition changes needed**

The agent definitions (plan-agent, implement-agent, test-agent, review-agent, finish-agent, dev-orchestrator) already use `.ai/workflows/runs/<run_id>/handoffs/` and `.ai/workflows/runs/<run_id>/logs/` paths. No changes needed.

---

## Task 5: Template Sync

### Task 5.1: Sync to bootstrap templates

- [ ] **Step 1: Run template sync**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
```

- [ ] **Step 2: Check for drift**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
```

- [ ] **Step 3: Commit synced templates**

```bash
git add skills/sdlc-project-bootstrap/templates/workflow/
git commit -m "chore: sync workflow.py changes to bootstrap templates"
```

### Task 5.2: Distribute agent definitions

- [ ] **Step 1: Distribute to project-level targets**

```bash
python3 scripts/install_agents.py --target ./.opencode/agents --force
python3 scripts/install_agents.py --target ./.claude/agents --force
python3 scripts/install_agents.py --target ./.cursor/agents --force
```

- [ ] **Step 2: Commit**

```bash
git add .opencode/agents/ .claude/agents/ .cursor/agents/
git commit -m "chore: distribute agent definitions"
```
