# Remove superpowers_direct Dead Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the unused `superpowers_direct` workflow action and its `_policy_no_workflow` helper from the SDLC workflow runtime, along with the corresponding runtime constraint documentation and tests, because dev-orchestrator now routes all development through the governed `spec-flow` and `lightweight-flow` paths.

**Architecture:** `superpowers_direct` was a no-workflow escape hatch registered via `@register_policy("superpowers_direct")` that returned `allowed=true, status=not_required` and created no workflow run. A full-repo audit found zero CLI callers (`--action superpowers_direct` never appears) and the only semantic reference in `agents/dev-orchestrator.md:198` is a negative assertion distancing the orchestrator from this path. The `lightweight-flow` start-with-plan handoff fully covers the "externally generated superpowers plan/spec then execute" use case. Removal touches the canonical policy module, the re-exporting `workflow.py`, two test files, two agent/constraint docs, and four derived template copies synced via the standard derived-artifact sync script.

**Tech Stack:** Python 3, pytest, the SDLC workflow runtime (`workflow_runtime/policies.py`, `workflow.py`), the derived-artifact sync pipeline (`scripts/sync_derived_artifacts.py`), and the workflow template sync script (`skills/sdlc-project-bootstrap/scripts/sync_templates.py`).

---

## File Structure

### Canonical source files (edited first)

| File | Responsibility | Change |
|---|---|---|
| `.ai/workflows/scripts/workflow_runtime/policies.py` | Policy registry; defines `_policy_no_workflow` and registers `superpowers_direct` | Delete the `@register_policy("superpowers_direct")` block and the `_policy_no_workflow` function; update the `cmd_ensure_run` comment to drop the `superpowers_direct` example |
| `.ai/workflows/scripts/workflow.py` | Re-exports policy symbols for the CLI entrypoint | Remove `_policy_no_workflow` from the `from workflow_runtime.policies import (...)` block |
| `agents/dev-orchestrator.md` | Orchestrator routing rules | Remove the negative `superpowers-direct` reference in the Start-With-Plan Handoff paragraph |
| `.ai/workflows/AGENTS.md` | Workflow runtime constraints for agents | Delete section "## 4. Superpowers Direct Flow" (lines 27-30) |
| `tests/test_workflow.py` | End-to-end CLI tests | Delete `test_preflight_superpowers_direct_returns_not_required` and `test_ensure_run_superpowers_direct_returns_not_required`, plus their section comment |
| `tests/test_workflow_modules.py` | Module-level policy registry tests | Delete the `meta4` block inside `test_stacked_policy_decorators_keep_per_action_metadata` and delete the entire `test_policy_evaluation_preserves_status_reason_and_next_action` method |

### Derived artifacts (synced, never edited directly)

Synced by `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git`:

| File | Change |
|---|---|
| `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py` | mirrored from canonical |
| `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | mirrored from canonical |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py` | mirrored from canonical |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | mirrored from canonical |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py` | mirrored from canonical |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | mirrored from canonical |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py` | mirrored from canonical |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | mirrored from canonical |

---

## Task 1: Remove `superpowers_direct` policy and `_policy_no_workflow` from canonical `policies.py`

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/policies.py:204-208`
- Modify: `.ai/workflows/scripts/workflow_runtime/policies.py:521`

- [ ] **Step 1: Delete the `superpowers_direct` registration and `_policy_no_workflow` function**

In `.ai/workflows/scripts/workflow_runtime/policies.py`, remove lines 206-208 (the decorator, function definition, and return statement). The `# --- Policies ---` header comment at line 204 stays, followed directly by the `@register_policy("spec_create", ...)` decorator that was previously at line 211.

Before (lines 204-209):
```python
# --- Policies ---

@register_policy("superpowers_direct")
def _policy_no_workflow(root, action, subject_type, subject_id):
    return _make_preflight_decision(True, "not_required")


@register_policy(
```

After:
```python
# --- Policies ---

@register_policy(
```

- [ ] **Step 2: Update the `cmd_ensure_run` passthrough comment**

In the same file, change the comment at line 521 to drop the `superpowers_direct` example. Keep the passthrough branch itself intact because `post_archive_actions` (registered with the default `creates_run=False`) also relies on it.

Before (line 521):
```python
    # Non-governed actions (e.g., superpowers_direct) pass through
```

After:
```python
    # Non-governed actions (creates_run=False) pass through
```

- [ ] **Step 3: Verify the canonical module still imports**

Run:
```bash
python3 -c "import sys; sys.path.insert(0, '.ai/workflows/scripts'); from workflow_runtime import policies; print(sorted(policies.POLICY_REGISTRY.keys()))"
```

Expected: a sorted list of action names that does NOT include `superpowers_direct`. The list should still include `spec_create`, `spec_continue`, `spec_apply`, `spec_archive`, `openspec_create`, `openspec_continue`, `openspec_apply`, `openspec_archive`, `post_archive_actions`, `dangling_archive_repair`, `roadmap_item`.

## Task 2: Remove `_policy_no_workflow` re-export from canonical `workflow.py`

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:115`

- [ ] **Step 1: Delete the `_policy_no_workflow` import line**

In `.ai/workflows/scripts/workflow.py`, remove line 115 (`    _policy_no_workflow,`) from the `from workflow_runtime.policies import (...)` block.

Before (lines 114-116):
```python
    _load_done_history_run_ids,
    _policy_no_workflow,
    _policy_openspec_change,
```

After (lines 114-115):
```python
    _load_done_history_run_ids,
    _policy_openspec_change,
```

- [ ] **Step 2: Verify `workflow.py` still imports cleanly**

Run:
```bash
python3 -c "import sys; sys.path.insert(0, '.ai/workflows/scripts'); import workflow; print('workflow.py imports ok')"
```

Expected: `workflow.py imports ok` with exit code 0.

## Task 3: Remove the `superpowers_direct` runtime constraint section from `.ai/workflows/AGENTS.md`

**Files:**
- Modify: `.ai/workflows/AGENTS.md:27-30`

- [ ] **Step 1: Delete section "## 4. Superpowers Direct Flow"**

Remove lines 27-30 inclusive. The section header, both bullet points, and the trailing blank line before "## 5. Test Discipline" should be deleted so that "## 3. Dangling Archive Repair" is followed directly by "## 5. Test Discipline".

Before (lines 26-33):
```markdown

## 4. Superpowers Direct Flow

- `superpowers_direct` action MUST NOT create a workflow run or write any workflow state.
- The `_policy_no_workflow` function MUST return `allowed=true, status=not_required` without any side effects.

## 5. Test Discipline
```

After (lines 26-29):
```markdown

## 5. Test Discipline
```

- [ ] **Step 2: Verify the file no longer references `superpowers_direct`**

Run:
```bash
python3 -c "content = open('.ai/workflows/AGENTS.md').read(); assert 'superpowers_direct' not in content and '_policy_no_workflow' not in content, 'still referenced'; print('AGENTS.md clean')"
```

Expected: `AGENTS.md clean` with exit code 0.

## Task 4: Remove the negative `superpowers-direct` reference from `agents/dev-orchestrator.md`

**Files:**
- Modify: `agents/dev-orchestrator.md:198`

- [ ] **Step 1: Rewrite the Start-With-Plan paragraph to drop the `superpowers-direct` reference**

Replace line 198 only. Keep the rest of the paragraph (the governance requirement) intact, just drop the negative-assertion clause.

Before (line 198):
```
This branch is governed workflow execution, not `superpowers-direct`. It MUST still use workflow start/resume, `before-dispatch`, `implement-agent`, and `review-agent`. It only needs to skip `plan-agent` after existing design artifacts are selected.
```

After (line 198):
```
This branch is governed workflow execution. It MUST still use workflow start/resume, `before-dispatch`, `implement-agent`, and `review-agent`. It only needs to skip `plan-agent` after existing design artifacts are selected.
```

- [ ] **Step 2: Verify the agent file no longer references `superpowers-direct`**

Run:
```bash
python3 -c "content = open('agents/dev-orchestrator.md').read(); assert 'superpowers-direct' not in content, 'still referenced'; print('dev-orchestrator.md clean')"
```

Expected: `dev-orchestrator.md clean` with exit code 0.

## Task 5: Remove the two `superpowers_direct` tests from `tests/test_workflow.py`

**Files:**
- Modify: `tests/test_workflow.py:2452-2458`
- Modify: `tests/test_workflow.py:2749-2755`

- [ ] **Step 1: Delete the `test_preflight_superpowers_direct_returns_not_required` test and its section comment**

Remove lines 2452-2458 inclusive (the `# --- no-workflow policy ---` section comment, the blank line before it if it is the only separator, the test method definition, and its body).

Before (lines 2450-2460):
```python
        return rc, json.loads(out), err

    # --- no-workflow policy ---

    def test_preflight_superpowers_direct_returns_not_required(self):
        rc, data, _ = self._run_preflight("superpowers_direct")
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "not_required")

    # --- openspec action without active run ---

    def test_preflight_openspec_create_without_active_run_blocks(self):
```

After (lines 2450-2454):
```python
        return rc, json.loads(out), err

    # --- openspec action without active run ---

    def test_preflight_openspec_create_without_active_run_blocks(self):
```

- [ ] **Step 2: Delete the `test_ensure_run_superpowers_direct_returns_not_required` test and its section comment**

Remove lines 2749-2755 inclusive.

Before (lines 2748-2758):
```python
        self.assertIn("resume", data["next_action"].get("command", ""))

    # --- ensure-run superpowers_direct returns not_required ---

    def test_ensure_run_superpowers_direct_returns_not_required(self):
        rc, data, _ = self._run_ensure_run("superpowers_direct")
        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "not_required")

    # --- phase validation: preflight blocks when run phase doesn't match action ---

    def test_preflight_openspec_apply_in_create_phase_blocks(self):
```

After (lines 2748-2752):
```python
        self.assertIn("resume", data["next_action"].get("command", ""))

    # --- phase validation: preflight blocks when run phase doesn't match action ---

    def test_preflight_openspec_apply_in_create_phase_blocks(self):
```

- [ ] **Step 3: Verify no `superpowers_direct` references remain in the test file**

Run:
```bash
python3 -c "content = open('tests/test_workflow.py').read(); assert 'superpowers_direct' not in content, 'still referenced'; print('test_workflow.py clean')"
```

Expected: `test_workflow.py clean` with exit code 0.

## Task 6: Remove the `superpowers_direct` module tests from `tests/test_workflow_modules.py`

**Files:**
- Modify: `tests/test_workflow_modules.py:313-315` (the `meta4` block)
- Modify: `tests/test_workflow_modules.py:317-329` (the `test_policy_evaluation_preserves_status_reason_and_next_action` method)

- [ ] **Step 1: Delete the `meta4` assertions inside `test_stacked_policy_decorators_keep_per_action_metadata`**

Remove lines 313-315 inclusive (the comment and two assertions). The preceding `meta3` block (lines 307-311) becomes the last assertion block in the test method.

Before (lines 307-317):
```python
        # dangling_archive_repair has creates_run=True and repair_hooks
        meta3 = pol_mod.POLICY_META.get("dangling_archive_repair")
        self.assertIsNotNone(meta3, "dangling_archive_repair must be registered")
        self.assertTrue(meta3["creates_run"])
        self.assertIn("memory_sync", meta3["repair_hooks"])

        # superpowers_direct has no allowed_phases restriction
        meta4 = pol_mod.POLICY_META.get("superpowers_direct")
        self.assertIsNotNone(meta4, "superpowers_direct must be registered")

    def test_policy_evaluation_preserves_status_reason_and_next_action(self):
```

After (lines 307-312):
```python
        # dangling_archive_repair has creates_run=True and repair_hooks
        meta3 = pol_mod.POLICY_META.get("dangling_archive_repair")
        self.assertIsNotNone(meta3, "dangling_archive_repair must be registered")
        self.assertTrue(meta3["creates_run"])
        self.assertIn("memory_sync", meta3["repair_hooks"])

    def test_policy_evaluation_preserves_status_reason_and_next_action(self):
```

- [ ] **Step 2: Delete the entire `test_policy_evaluation_preserves_status_reason_and_next_action` method**

Remove lines 317-329 inclusive (the method definition, docstring, body, and the blank line that precedes the next method at line 331). This test exercises `_policy_no_workflow`, which no longer exists.

Before (lines 312-332):
```python

    def test_policy_evaluation_preserves_status_reason_and_next_action(self):
        """The _policy_no_workflow function must return allowed=True, status=not_required
        with empty reason, through the extracted policies API."""
        pol_mod = _import_policies()
        import tempfile
        tmp = tempfile.mkdtemp()
        try:
            decision = pol_mod._policy_no_workflow(tmp, "superpowers_direct", None, None)
            self.assertTrue(decision["allowed"])
            self.assertEqual(decision["status"], "not_required")
            self.assertEqual(decision["reason"], "")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _import_dispatch():
```

After (lines 312-314):
```python


def _import_dispatch():
```

- [ ] **Step 3: Verify no `superpowers_direct` or `_policy_no_workflow` references remain in the module test file**

Run:
```bash
python3 -c "content = open('tests/test_workflow_modules.py').read(); assert 'superpowers_direct' not in content and '_policy_no_workflow' not in content, 'still referenced'; print('test_workflow_modules.py clean')"
```

Expected: `test_workflow_modules.py clean` with exit code 0.

- [ ] **Step 4: Check that `shutil` import is still needed in `tests/test_workflow_modules.py`**

Run:
```bash
python3 -c "content = open('tests/test_workflow_modules.py').read(); assert 'shutil' in content, 'shutil may be orphaned'; print('shutil still used')"
```

If the output says `shutil still used`, do nothing. If it says `shutil may be orphaned`, run this to find remaining usages:
```bash
grep -n "shutil" tests/test_workflow_modules.py
```

Only remove the `import shutil` line if every remaining `shutil` reference is the import itself and nothing else in the file uses `shutil`. If any other test method uses `shutil.rmtree`, leave the import.

## Task 6a: Fix `test_wrapper_contracts.py` test asserting the removed string

**Files:**
- Modify: `tests/test_wrapper_contracts.py:419-421`

This task was added after Task 7 surfaced an additional test asserting the removed `superpowers-direct` string.

- [ ] **Step 1: Remove the `assertIn("not \`superpowers-direct\"`)" line**

In `tests/test_wrapper_contracts.py`, the method `test_start_with_plan_is_governed_not_direct_execution` asserts that `dev-orchestrator.md` contains `not \`superpowers-direct\``. That clause was removed in Task 4. Delete the assertion line; keep the remaining assertions (`before-dispatch`, `implement-agent`, `skip \`plan-agent\``, `design_artifact_paths`, the `plan_path` checks) which still validate the governance intent.

Before (lines 419-422):
```python
    def test_start_with_plan_is_governed_not_direct_execution(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("not `superpowers-direct`", content)
        self.assertIn("before-dispatch", content)
```

After (lines 419-421):
```python
    def test_start_with_plan_is_governed_not_direct_execution(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("before-dispatch", content)
```

- [ ] **Step 2: Verify the test passes**

Run:
```bash
python3 -m pytest tests/test_wrapper_contracts.py::TestDevOrchestratorStartWithPlanHandoff::test_start_with_plan_is_governed_not_direct_execution -v
```

Expected: PASS.

## Task 7: Run the full test suite and verify no regressions

**Files:**
- None (verification only)

- [ ] **Step 1: Run the workflow test suite**

Run:
```bash
python3 -m pytest tests/test_workflow.py tests/test_workflow_modules.py -v
```

Expected: all remaining tests PASS. Specifically:
- No test with `superpowers_direct` in its name runs (they were deleted).
- No test fails with `ImportError: cannot import name '_policy_no_workflow'`.
- No test fails with `KeyError: 'superpowers_direct'` or `AssertionError: superpowers_direct must be registered`.
- The test count should drop by 3 (two from `test_workflow.py`, one from `test_workflow_modules.py`).

If any test fails with an import error for `_policy_no_workflow`, re-check Task 2 Step 1 and Task 6 Step 2 — you may have left a reference to the deleted function.

- [ ] **Step 2: Run the broader test suite to catch cross-module regressions**

Run:
```bash
python3 -m pytest tests/ -v
```

Expected: all tests PASS. If a test outside `test_workflow.py` and `test_workflow_modules.py` fails and references `superpowers_direct` or `_policy_no_workflow`, that test also needs cleanup — inspect the failure, find the file, and add a Task to remove the same pattern.

## Task 8: Sync derived artifacts to all project-level copies

**Files:**
- Synced: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py`
- Synced: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Synced: `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py`
- Synced: `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Synced: `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py`
- Synced: `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Synced: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py`
- Synced: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`

- [ ] **Step 1: Run the incremental derived-artifact fix**

Run:
```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
```

Expected: the script detects the changed canonical files (`.ai/workflows/scripts/workflow_runtime/policies.py` and `.ai/workflows/scripts/workflow.py`) and re-syncs the matching template copies in `.opencode/`, `.claude/`, `.cursor/`, and `skills/sdlc-project-bootstrap/templates/`. Exit code 0.

- [ ] **Step 2: Run the incremental derived-artifact check to confirm no drift**

Run:
```bash
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

Expected: exit code 0, no drift reported.

- [ ] **Step 3: Verify the derived copies no longer contain `superpowers_direct` or `_policy_no_workflow`**

Run:
```bash
python3 -c "
targets = [
    '.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py',
    '.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py',
    '.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py',
    '.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py',
    '.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py',
    '.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py',
    'skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py',
    'skills/sdlc-project-bootstrap/templates/workflow/workflow.py',
]
for t in targets:
    content = open(t).read()
    assert 'superpowers_direct' not in content, f'{t} still has superpowers_direct'
    assert '_policy_no_workflow' not in content, f'{t} still has _policy_no_workflow'
print('all derived copies clean')
"
```

Expected: `all derived copies clean` with exit code 0.

- [ ] **Step 4: Run the workflow template distributed-copy check**

Run:
```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed
```

Expected: exit code 0, no distributed drift reported. If this reports drift, the `--fix` step in Step 1 may not have covered a distributed copy; re-run with `--distribute`:
```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute
```
then re-run `--check-distributed`.

## Task 9: Final repo-wide grep verification and commit

**Files:**
- None (verification and commit only)

- [ ] **Step 1: Confirm no live references to `superpowers_direct` or `_policy_no_workflow` remain outside history/memory**

Run:
```bash
grep -rn "superpowers_direct\|_policy_no_workflow" \
  --include='*.py' \
  --include='*.md' \
  .ai/workflows/scripts \
  agents \
  tests \
  skills/sdlc-project-bootstrap/templates/workflow \
  .opencode/skills/sdlc-project-bootstrap/templates/workflow \
  .claude/skills/sdlc-project-bootstrap/templates/workflow \
  .cursor/skills/sdlc-project-bootstrap/templates/workflow
```

Expected: zero matches. Acceptable remaining matches are ONLY in:
- `.ai/workflows/runs/history/` (run history records — immutable, do not edit)
- `.ai/memory/modules/agents.md` (repository memory snapshot — do not edit)
- `.ai/memory/modules/skills/sdlc.md` (repository memory snapshot — do not edit)
- `.ai/memory/sync-history/` (sync history log — do not edit)
- `openspec/changes/archive/` (archived change tasks.md — do not edit)

If a match appears anywhere else, add a Task to clean it up before committing.

- [ ] **Step 2: Confirm `dev-orchestrator.md` no longer contains `superpowers-direct`**

Run:
```bash
python3 -c "content = open('agents/dev-orchestrator.md').read(); assert 'superpowers-direct' not in content, 'still referenced'; print('dev-orchestrator.md verified')"
```

Expected: `dev-orchestrator.md verified` with exit code 0.

- [ ] **Step 3: Stage the changed canonical and derived files**

Stage only the files this plan touched. Do NOT stage run history, memory, or archive files.

```bash
git add \
  .ai/workflows/scripts/workflow_runtime/policies.py \
  .ai/workflows/scripts/workflow.py \
  .ai/workflows/AGENTS.md \
  agents/dev-orchestrator.md \
  tests/test_workflow.py \
  tests/test_workflow_modules.py \
  .opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py \
  .opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py \
  .claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py \
  .claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py \
  .cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py \
  .cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py \
  skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/policies.py \
  skills/sdlc-project-bootstrap/templates/workflow/workflow.py
```

- [ ] **Step 4: Commit the removal**

```bash
git commit -m "refactor: remove superpowers_direct dead code

The superpowers_direct workflow action and its _policy_no_workflow
helper are unused: dev-orchestrator routes all development through the
governed spec-flow and lightweight-flow paths. A full-repo audit found
zero CLI callers (--action superpowers_direct never appears) and the
only semantic reference in dev-orchestrator.md was a negative assertion
distancing the orchestrator from this path.

Remove the policy registration, the helper function, the re-export in
workflow.py, the runtime constraint section in .ai/workflows/AGENTS.md,
the negative reference in dev-orchestrator.md, and the three tests that
covered the deleted policy. Sync derived template copies via the
standard derived-artifact sync pipeline."
```

- [ ] **Step 5: Verify the commit contains only intended files**

```bash
git show --stat HEAD
```

Expected: the commit touches exactly the 14 files staged in Step 3 (6 canonical + 8 derived). No run history, memory, or archive files should appear in the stat output.

---

## Self-Review Notes

### Spec coverage

The original evaluation identified every `superpowers_direct` / `_policy_no_workflow` occurrence in the repo. This plan covers:

- **Canonical source**: policies.py registration + helper (Task 1), workflow.py re-export (Task 2) ✓
- **Runtime constraint doc**: .ai/workflows/AGENTS.md §4 (Task 3) ✓
- **Agent doc negative reference**: dev-orchestrator.md:198 (Task 4) ✓
- **CLI tests**: test_workflow.py two tests (Task 5) ✓
- **Module tests**: test_workflow_modules.py meta4 block + full method (Task 6) ✓
- **Derived artifacts**: 4 template pairs synced (Task 8) ✓
- **History/memory/archive**: explicitly left untouched (Task 9 Step 1 lists the acceptable remaining locations) ✓

### Placeholder scan

No "TBD", "implement later", or "similar to Task N" patterns. Every step contains the exact before/after code or the exact command with expected output.

### Type consistency

`_policy_no_workflow` is the only symbol being removed. The `creates_run=False` passthrough branch in `cmd_ensure_run` is preserved (Task 1 Step 2 only updates the comment) because `post_archive_actions` still relies on the default `creates_run=False`. No other symbols are renamed or repurposed.

### Tradeoffs considered

- **Preserving the `creates_run=False` passthrough branch**: chose to keep it. Rationale: `post_archive_actions` is registered with the default `creates_run=False` and the branch is generic infrastructure per AGENTS.md §1 ("extend via `@register_policy`"). Removing it would couple the runtime to `creates_run=True`-only actions and violate the extension contract.
- **Not touching history/memory/archive**: these are immutable time-snapshots. Editing them would rewrite history that is no longer accurate to the time it was recorded.