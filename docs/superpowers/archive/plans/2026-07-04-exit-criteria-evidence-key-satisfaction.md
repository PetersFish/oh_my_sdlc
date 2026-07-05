# Exit Criteria Evidence-Key Satisfaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow `_missing_exit_criteria` to accept a truthy evidence key value as satisfaction for the matching exit criterion, in addition to the existing `criteria_satisfied` string path. Eliminate redundant blocks where evidence keys are already truthy but the string declaration is incomplete.

**Architecture:** Single function change in `_missing_exit_criteria` in `workflow.py`, mirrored to the canonical template. The function already receives `phase_evidence_view`; it will check both the string field and the evidence key values. No phase definition, agent prompt, or aggregation logic changes.

**Tech Stack:** Python workflow runtime, YAML workflow definition (unchanged), pytest/unittest, project-level workflow template sync.

**Repository Policy Note:** Do not commit during execution of this plan unless the user explicitly asks. Use `git status`/`git diff` checkpoints instead of commit steps.

---

## File Structure

- `.ai/workflows/scripts/workflow.py`: `_missing_exit_criteria` function (live runtime).
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`: canonical workflow runtime template that must stay byte-synced with the live runtime.
- `tests/test_workflow.py`: executable workflow runtime behavior tests.
- Distributed copies under `.opencode/`, `.claude/`, `.cursor/`: workflow-template copies that must stay in sync with canonical files.

---

### Task 1: Add Failing Tests For Evidence-Key Satisfaction

**Files:**
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Add behavior tests for evidence-key-value satisfaction**

Add tests near the existing `after_dispatch` coverage in `tests/test_workflow.py`. Use the `TestApplyChangeEvidenceContract` test class or a new `TestExitCriteriaEvidenceKeySatisfaction` class:

```python
class TestExitCriteriaEvidenceKeySatisfaction(unittest.TestCase):
    """Tests that _missing_exit_criteria accepts truthy evidence key values
    as satisfaction for matching exit criteria, in addition to criteria_satisfied string."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _read_current_state(self):
        run_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        for name in os.listdir(run_dir):
            path = os.path.join(run_dir, name, "run.json")
            if os.path.isfile(path):
                with open(path) as f:
                    return json.load(f)
        return None

    def _write_current_state(self, state):
        run_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active")
        for name in os.listdir(run_dir):
            path = os.path.join(run_dir, name, "run.json")
            if os.path.isfile(path):
                with open(path, "w") as f:
                    json.dump(state, f)
                return

    def test_exit_criteria_satisfied_by_evidence_key_value_without_string(self):
        """Agent provides archive_path_exists=true but omits it from criteria_satisfied.
        Should pass because evidence key value is truthy."""
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
        """Agent provides criteria_satisfied string but no matching evidence key value.
        Should pass (backward compatible)."""
        state = self._read_current_state()
        state["current_phase"] = "archive_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        self._write_current_state(state)

        # Create archive file so loader can find it if needed
        archive_dir = os.path.join(self.tmp, "openspec", "changes", "demo-change", "archive")
        os.makedirs(archive_dir, exist_ok=True)
        with open(os.path.join(archive_dir, "summary.md"), "w") as f:
            f.write("# Archive\n")

        result = {
            "status": "success",
            "phase": "archive_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "archive_path_exists": True,
                "criteria_satisfied": "archive_path_exists",
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
            "criteria_satisfied string should still work as before",
        )

    def test_exit_criteria_missing_both_value_and_string_blocks(self):
        """Agent provides neither evidence value nor string declaration.
        Should block with missing_exit_criteria_satisfied."""
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
            "Missing both evidence value and string should block",
        )

    def test_exit_criteria_evidence_key_falsy_does_not_satisfy(self):
        """Agent returns archive_path_exists=false.
        Should block because falsy values do not satisfy exit criteria."""
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
                "archive_path_exists": False,
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
            "Falsy evidence value should not satisfy exit criteria",
        )

    def test_exit_criteria_apply_change_evidence_key_satisfies_without_string(self):
        """apply_change agent provides tasks_complete=true but omits it from criteria_satisfied.
        Should pass via evidence key value in aggregated phase_evidence_view."""
        state = self._read_current_state()
        state["current_phase"] = "apply_change"
        state.setdefault("context", {})["change_id"] = "demo-change"
        state.setdefault("evidence", {}).setdefault("agent_results", {}).setdefault("default", {})["test-agent"] = {
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
```

- [ ] **Step 2: Run focused tests to verify red phase**

Run: `python3 -m pytest tests/test_workflow.py -k "TestExitCriteriaEvidenceKeySatisfaction" -v`

Expected: FAIL because `_missing_exit_criteria` currently only checks the `criteria_satisfied` string, not evidence key values.

---

### Task 2: Fix `_missing_exit_criteria` To Accept Evidence Key Values

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`

- [ ] **Step 1: Update `_missing_exit_criteria` in live runtime**

In `.ai/workflows/scripts/workflow.py`, replace the `_missing_exit_criteria` function:

Current:

```python
def _missing_exit_criteria(agent_evidence: Dict[str, Any], phase_def: Dict[str, Any]) -> List[str]:
    raw = agent_evidence.get("criteria_satisfied", "")
    satisfied = {item for item in str(raw).split(",") if item}
    required = set(phase_def.get("exit_criteria", []))
    return sorted(required - satisfied)
```

New:

```python
def _missing_exit_criteria(phase_evidence_view: Dict[str, Any], phase_def: Dict[str, Any]) -> List[str]:
    raw = phase_evidence_view.get("criteria_satisfied", "")
    satisfied = {item for item in str(raw).split(",") if item}
    required = set(phase_def.get("exit_criteria", []))
    for key in list(required - satisfied):
        value = phase_evidence_view.get(key)
        if value is not None and value != "" and value is not False:
            satisfied.add(key)
    return sorted(required - satisfied)
```

The parameter rename from `agent_evidence` to `phase_evidence_view` reflects the actual call site (line 1953), which already passes `phase_evidence_view`.

- [ ] **Step 2: Mirror the change into the canonical workflow template**

Apply the identical function replacement to:

- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`

Keep the template byte-aligned with the live runtime for this change.

- [ ] **Step 3: Run focused behavior tests again**

Run: `python3 -m pytest tests/test_workflow.py -k "TestExitCriteriaEvidenceKeySatisfaction" -v`

Expected: PASS — all five new tests should pass.

- [ ] **Step 4: Run existing after-dispatch regression tests**

Run: `python3 -m pytest tests/test_workflow.py -k "after_dispatch" -v`

Expected: PASS — no existing test should break. Existing tests that provide correct `criteria_satisfied` strings continue to pass via the string path. Existing block tests that provide neither value nor string continue to block.

---

### Task 3: Sync And Final Regression Verification

**Files:**
- Distributed workflow template copies under `.opencode/`, `.claude/`, `.cursor/`
- Test: `tests/test_workflow.py`
- Test: `tests/test_wrapper_contracts.py`
- Test: drift/sync suites under `tests/`

- [ ] **Step 1: Sync canonical workflow template to distributed copies**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute
```

Then verify:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed
```

Expected: both checks pass (no drift).

- [ ] **Step 2: Run full workflow and wrapper-contract suites**

Run:

```bash
python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py -v
```

Expected: PASS.

- [ ] **Step 3: Run drift/sync regression tests**

Run:

```bash
python3 -m pytest tests/test_sync_template.py tests/test_sync_all_distributed.py tests/test_template_sync.py tests/test_sync_templates.py -v
```

Expected: PASS.

- [ ] **Step 4: Run full test regression**

Run:

```bash
python3 -m pytest tests/ -v
```

Expected: PASS.

- [ ] **Step 5: Inspect final diff for scope control**

Run:

```bash
git status --short
git diff -- .ai/workflows/scripts/workflow.py skills/sdlc-project-bootstrap/templates/workflow/workflow.py tests/test_workflow.py docs/superpowers/specs/2026-07-04-exit-criteria-evidence-key-satisfaction-design.md docs/superpowers/plans/2026-07-04-exit-criteria-evidence-key-satisfaction.md
```

Expected: only `_missing_exit_criteria` function change, template mirror, new test class, and the spec/plan files. No agent prompt changes. No phase definition changes. No aggregation logic changes.

---

## Self-Review

**Spec coverage:** Covered the core decision (evidence key value OR string satisfaction), all-phases scope, `criteria_satisfied` backward compatibility, falsy-value rejection, and edge cases for `post_archive_actions` (no evidence_keys) and `apply_change` (aggregated view).

**Placeholder scan:** No TODO/TBD placeholders. Commands, file paths, runtime snippets, and test targets are explicit.

**Type consistency:** Uses `phase_evidence_view`, `exit_criteria`, `evidence_keys`, `criteria_satisfied`, `missing_exit_criteria_satisfied`, and `complete_phase` consistently across spec and plan. The parameter rename from `agent_evidence` to `phase_evidence_view` aligns with the actual call site.