# Apply Change Evidence Contract Tightening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `apply_change` complete deterministically by aligning review success evidence, runtime phase validation, and handoff/history behavior for the implement -> test -> review chain.

**Architecture:** Keep the existing multi-agent `apply_change` pipeline, but tighten the contract at the boundaries. `review-agent` becomes the final phase-evidence emitter, `workflow.py after-dispatch` validates against aggregated apply-phase evidence, and handoff writes preserve both latest and per-attempt history without changing other phases.

**Tech Stack:** Python workflow runtime, YAML workflow definition, Markdown agent prompts, pytest/unittest, project-level workflow template sync.

**Repository Policy Note:** Do not commit during execution of this plan unless the user explicitly asks. Use `git status`/`git diff` checkpoints instead of commit steps.

---

## File Structure

- `.ai/workflows/scripts/workflow.py`: runtime evidence-envelope validation, phase evidence aggregation, and handoff/history writing logic.
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`: canonical workflow runtime template that must stay byte-synced with the live runtime.
- `agents/dev-orchestrator.md`: dispatch contract source for review routing and phase requirement handoff.
- `agents/implement-agent.md`: apply-change implementation worker contract; must stop treating verification handoff as blocked.
- `agents/review-agent.md`: final acceptance worker contract; must emit apply-phase evidence keys on success.
- `tests/test_workflow.py`: executable workflow runtime behavior tests.
- `tests/test_wrapper_contracts.py`: prompt/static contract tests for agent prompts.
- Distributed copies under `.opencode/`, `.claude/`, `.cursor/`: generated/activated agent and workflow-template copies that must stay in sync with canonical files.

---

### Task 1: Tighten Agent Prompt Contracts For Apply Change

**Files:**
- Modify: `agents/review-agent.md`
- Modify: `agents/implement-agent.md`
- Modify: `agents/dev-orchestrator.md`
- Test: `tests/test_wrapper_contracts.py`

- [ ] **Step 1: Add failing prompt-contract tests for review success evidence and implement success semantics**

Add prompt assertions near the existing agent contract tests in `tests/test_wrapper_contracts.py`:

```python
class TestApplyChangeEvidencePromptContracts(unittest.TestCase):
    def test_review_agent_success_example_includes_apply_phase_evidence(self):
        body = (AGENTS_DIR / "review-agent.md").read_text(encoding="utf-8")

        self.assertIn('"tasks_complete": true', body)
        self.assertIn('"tdd_passed": true', body)
        self.assertIn('"eval_passed_or_human_decision_recorded": true', body)
        self.assertIn('"criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded"', body)

    def test_implement_agent_no_longer_marks_verification_handoff_as_blocked(self):
        body = (AGENTS_DIR / "implement-agent.md").read_text(encoding="utf-8")

        self.assertIn('"recommended_next_action": "dispatch_test_agent"', body)
        self.assertNotIn('"reason": "verification_pending"', body)

    def test_dev_orchestrator_documents_phase_requirements_for_review_dispatch(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")

        self.assertIn("evidence_keys", body)
        self.assertIn("exit_criteria", body)
        self.assertIn("eval_passed_or_human_decision_recorded", body)
```

- [ ] **Step 2: Run prompt-contract tests to verify they fail first**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -k "ApplyChangeEvidencePromptContracts" -v`

Expected: FAIL because current prompt examples and dispatch guidance do not fully match the new contract.

- [ ] **Step 3: Update `agents/review-agent.md` success contract and evidence emission guidance**

Replace the success example and evidence-emission section so `apply_change` review success includes phase-completion keys:

```json
{
  "agent": "review-agent",
  "status": "success",
  "phase": "apply_change",
  "slice_id": "default",
  "flow_type": "lightweight-flow",
  "evidence": {
    "tasks_complete": true,
    "tdd_passed": true,
    "eval_passed_or_human_decision_recorded": true,
    "review_complete": true,
    "verification_passed": true,
    "review_decision": "accepted",
    "criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded"
  },
  "artifacts": {
    "handoff_path": ".ai/workflows/runs/active/<run_id>/handoffs/default/review-agent.md"
  },
  "blockers": [],
  "recommended_next_action": "complete_phase"
}
```

Also add explicit guidance that `review-agent` must mirror the active phase contract when it is the final acceptance worker for `apply_change`.

- [ ] **Step 4: Update `agents/implement-agent.md` to treat downstream verification as success**

Change the success criteria and examples so implementation-complete handoff to test-agent uses `success`, not `blocked`:

```json
{
  "agent": "implement-agent",
  "status": "success",
  "phase": "apply_change",
  "slice_id": "default",
  "flow_type": "lightweight-flow",
  "evidence": {
    "tasks_complete": true,
    "tdd_passed": true,
    "focused_tests": [
      {"command": "python3 -m pytest tests/test_workflow.py -k apply_change -v", "result": "pass"}
    ]
  },
  "blockers": [],
  "recommended_next_action": "dispatch_test_agent"
}
```

Remove or rewrite the `verification_pending` blocked example so it only covers real execution blockers, not normal lifecycle progression.

- [ ] **Step 5: Update `agents/dev-orchestrator.md` review dispatch guidance**

Add a dispatch requirement under the `apply_change` loop stating that review dispatch must include the current phase contract:

```markdown
When dispatching `review-agent` for `apply_change`, include:
- current phase `evidence_keys`
- current phase `exit_criteria`
- latest successful test-agent verification summary

The review-agent must return an acceptance envelope that satisfies the `apply_change` phase contract.
```

- [ ] **Step 6: Run prompt-contract tests again**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -k "ApplyChangeEvidencePromptContracts" -v`

Expected: PASS.

---

### Task 2: Make `after-dispatch` Validate Aggregated Apply-Phase Evidence

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Add failing workflow tests for aggregated apply-change evidence**

Add runtime tests near the existing `after-dispatch` coverage in `tests/test_workflow.py`:

```python
def test_after_dispatch_review_success_uses_agent_evidence_for_apply_change(self):
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
```

- [ ] **Step 2: Run focused runtime tests to verify red phase**

Run: `python3 -m pytest tests/test_workflow.py -k "after_dispatch_review_success" -v`

Expected: FAIL because `after-dispatch` currently checks only the current worker evidence for required phase keys.

- [ ] **Step 3: Add apply-change aggregation helper in live workflow runtime**

In `.ai/workflows/scripts/workflow.py`, add a helper that builds the evidence view used for `apply_change` completion checks:

```python
def _build_phase_evidence_view(state, phase, slice_id, agent_evidence):
    merged = {}
    if phase == "apply_change":
        prior = state.get("evidence", {}).get("agent_results", {}).get(slice_id, {})
        for result in prior.values():
            if result.get("status") == "success":
                merged.update(result.get("evidence", {}))
        merged.update(state.get("evidence", {}))
        merged.update(agent_evidence)
        return merged
    merged.update(agent_evidence)
    return merged
```

Then change the validation path in `cmd_after_dispatch` from:

```python
missing_evidence_keys = _missing_phase_evidence_keys(agent_evidence, phase_def)
missing_exit_criteria = _missing_exit_criteria(agent_evidence, phase_def)
```

to:

```python
phase_evidence_view = _build_phase_evidence_view(state, phase, slice_id, agent_evidence)
missing_evidence_keys = _missing_phase_evidence_keys(phase_evidence_view, phase_def)
missing_exit_criteria = _missing_exit_criteria(phase_evidence_view, phase_def)
```

Keep the scope explicitly limited to `apply_change`.

- [ ] **Step 4: Promote aggregated apply-phase evidence back into state**

When validation succeeds for `apply_change`, promote the resolved evidence keys into `state["evidence"]` so the runtime remains the source of truth:

```python
if phase == "apply_change" and agent_status == "success" and not agent_blockers:
    for ek in phase_def.get("evidence_keys", []):
        if ek in phase_evidence_view:
            evidence[ek] = phase_evidence_view[ek]
```

Do not generalize this writeback beyond the current phase in this change.

- [ ] **Step 5: Mirror the runtime change into the canonical workflow template**

Apply the same helper and validation edits to:

- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`

Keep the template byte-aligned with the live runtime implementation for this change.

- [ ] **Step 6: Run focused runtime tests again**

Run: `python3 -m pytest tests/test_workflow.py -k "after_dispatch_review_success" -v`

Expected: PASS.

---

### Task 3: Make `eval_passed_or_human_decision_recorded` Explicit At Final Review

**Files:**
- Modify: `agents/review-agent.md`
- Modify: `.ai/workflows/scripts/workflow.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Add failing behavior tests for eval evidence ownership**

Add focused tests showing that review acceptance can use successful test-agent evidence but still blocks when no verification basis exists:

```python
def test_after_dispatch_review_acceptance_can_finalize_eval_key_from_test_agent_success(self):
    run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
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
```

Add the inverse case where `review-agent` tries to claim acceptance without verification basis and must still block.

- [ ] **Step 2: Run focused eval-ownership tests**

Run: `python3 -m pytest tests/test_workflow.py -k "eval_key_from_test_agent_success or acceptance_without_verification_basis" -v`

Expected: FAIL until the runtime/prompt contract is aligned.

- [ ] **Step 3: Document explicit eval ownership in `review-agent.md`**

Add guidance such as:

```markdown
For `apply_change`, emit `eval_passed_or_human_decision_recorded: true` only when:
- test-agent evidence shows successful verification for the slice, and
- final review accepts the change.
```

Do not assign this responsibility to implement-agent.

- [ ] **Step 4: Add minimal runtime guard for unverifiable acceptance**

In `workflow.py`, before accepting aggregated `apply_change` completion, ensure the phase evidence view includes a real verification basis:

```python
if phase == "apply_change" and phase_evidence_view.get("eval_passed_or_human_decision_recorded"):
    verified = phase_evidence_view.get("verification_passed") or phase_evidence_view.get("regression_passed")
    if not verified:
        agent_blockers.append({
            "reason": "missing_verification_basis",
            "message": "apply_change acceptance cannot record eval_passed_or_human_decision_recorded without successful verification evidence",
            "recommended_action": "resolve_failure",
        })
```

Keep the check narrow and phase-specific.

- [ ] **Step 5: Run focused tests again**

Run: `python3 -m pytest tests/test_workflow.py -k "eval_key_from_test_agent_success or acceptance_without_verification_basis" -v`

Expected: PASS.

---

### Task 4: Make After-Dispatch Block State Consistent

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Add failing behavior test for persisted block state after phase-evidence rejection**

Add this test near the existing `after-dispatch` blocker tests in `tests/test_workflow.py`:

```python
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
```

- [ ] **Step 2: Run the block-state test to verify it fails first**

Run: `python3 -m pytest tests/test_workflow.py -k "missing_apply_phase_evidence_persists_block_state" -v`

Expected: FAIL if `after-dispatch` reports a block transition but does not persist `state.status` / `state.block` consistently.

- [ ] **Step 3: Persist worker-failure blocks from `after-dispatch`**

In `.ai/workflows/scripts/workflow.py`, when `cmd_after_dispatch` determines `should_block`, persist a matching block before saving final state:

```python
if should_block:
    state["status"] = "blocked"
    state["block"] = {
        "type": "worker_failed",
        "message": block_message,
        "next_allowed": [item for item in next_allowed.split(",") if item],
    }
else:
    if state.get("block") and state.get("block", {}).get("type") == "worker_failed":
        state["block"] = None
    if state.get("status") == "blocked":
        state["status"] = "running"
```

Keep this scoped to `after-dispatch` worker-result blocks. Do not change readiness or hook block semantics.

- [ ] **Step 4: Mirror the block-state persistence change into the workflow template**

Apply the same change to:

- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`

- [ ] **Step 5: Run focused block-state tests again**

Run: `python3 -m pytest tests/test_workflow.py -k "missing_apply_phase_evidence_persists_block_state" -v`

Expected: PASS.

---

### Task 5: Preserve Latest And Historical Handoffs For Apply-Change Workers

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Add failing tests for latest + history handoff copy behavior**

Add behavior tests in `tests/test_workflow.py` that create an existing latest handoff file, invoke `after-dispatch`, and assert a history copy exists. The runtime must not be assumed to generate handoff prose; agents create latest handoffs, and the runtime preserves a history copy when the latest file exists:

```python
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
```

Add parallel coverage for implement-agent and test-agent if shared logic is introduced.

- [ ] **Step 2: Run focused handoff-history tests to verify red phase**

Run: `python3 -m pytest tests/test_workflow.py -k "handoff_history_copy" -v`

Expected: FAIL because current behavior does not preserve a timestamped history copy of an existing latest handoff.

- [ ] **Step 3: Add handoff dual-write helper in runtime**

In `.ai/workflows/scripts/workflow.py`, add a helper that preserves latest plus a timestamped history copy:

```python
def _write_handoff_history_copy(root, handoff_path):
    abs_latest = _resolve_path(root, handoff_path)
    if not os.path.exists(abs_latest):
        return None
    history_dir = os.path.join(os.path.dirname(abs_latest), "history")
    os.makedirs(history_dir, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(abs_latest))
    history_name = f"{stem}-{datetime.utcnow().strftime('%Y%m%dT%H%M%S%fZ')}{ext}"
    history_path = os.path.join(history_dir, history_name)
    shutil.copyfile(abs_latest, history_path)
    return history_path
```

Call it in `cmd_after_dispatch` after recording an apply-change worker result when `artifacts.handoff_path` points to an existing latest handoff file.

- [ ] **Step 4: Mirror the same helper into the workflow template**

Apply the same dual-write logic to:

- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`

- [ ] **Step 5: Run focused handoff-history tests again**

Run: `python3 -m pytest tests/test_workflow.py -k "handoff_history_copy" -v`

Expected: PASS.

---

### Task 6: Final Sync And Regression Verification

**Files:**
- Modify: distributed copies generated from canonical agent/runtime template files
- Test: `tests/test_workflow.py`
- Test: `tests/test_wrapper_contracts.py`
- Test: drift/sync suites under `tests/`

- [ ] **Step 1: Sync canonical workflow template to distributed copies**

Run the repo-approved sync command if permitted:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
```

If command policy blocks it during execution, apply the same content update to the project-level distributed workflow template copies and verify with drift tests.

- [ ] **Step 2: Sync canonical agent prompts to project-level distributed copies**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
```

If command policy blocks direct execution, use the repo-approved fallback for this workspace and prove parity with tests.

- [ ] **Step 3: Run focused workflow and wrapper suites**

Run:

```bash
python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py -v
```

Expected: PASS.

- [ ] **Step 4: Run drift/sync regression tests**

Run:

```bash
python3 -m pytest tests/test_sync_template.py tests/test_sync_all_distributed.py tests/test_template_sync.py tests/test_sync_templates.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full test regression**

Run:

```bash
python3 -m pytest tests/ -v
```

Expected: PASS.

- [ ] **Step 6: Inspect final diff for scope control**

Run:

```bash
git status --short
git diff -- .ai/workflows/scripts/workflow.py skills/sdlc-project-bootstrap/templates/workflow/workflow.py agents/dev-orchestrator.md agents/implement-agent.md agents/review-agent.md tests/test_workflow.py tests/test_wrapper_contracts.py docs/superpowers/specs/2026-07-03-apply-change-evidence-contract-tightening-design.md docs/superpowers/plans/2026-07-03-apply-change-evidence-contract-tightening.md
```

Expected: only apply-change evidence-contract, handoff-history, prompt, test, and sync/distribution changes.

---

## Self-Review

**Spec coverage:** Covered review-agent phase evidence emission, dev-orchestrator review dispatch contract, apply-change evidence aggregation, explicit eval ownership, after-dispatch block-state consistency, handoff history retention, and implement-agent success semantics.

**Placeholder scan:** No TODO/TBD placeholders. Commands, file paths, runtime snippets, and test targets are explicit.

**Type consistency:** Uses `tasks_complete`, `tdd_passed`, `eval_passed_or_human_decision_recorded`, `criteria_satisfied`, `dispatch_test_agent`, `dispatch_review_agent`, and `complete_phase` consistently across prompt and runtime tasks.
