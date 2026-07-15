# Slicing Assessment Contract Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the sliced apply-change assessment contract so plan-agent output, runtime materialization, persisted task metadata, and run rebuild behavior are aligned.

**Architecture:** Keep the existing workflow runtime structure. Update the pure materialization helpers in `state.py`, the after-dispatch behavior that consumes them, the plan-agent contract text, and the bootstrap template copies. Do not add a compatibility path for `evidence.slicing_assessment`; make the top-level payload authoritative and test the state round trip.

**Tech Stack:** Python standard library, workflow runtime JSON state, pytest/unittest, Markdown agent contracts.

---

## File Structure

- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
  - Owns slicing assessment validation, slice contract materialization, and implementation state validation.
- Modify: `.ai/workflows/scripts/workflow_runtime/dispatch.py`
  - Owns after-dispatch result consumption and blocker reporting.
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
  - Canonical template copy for bootstrapped projects.
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py`
  - Canonical template copy for bootstrapped projects.
- Modify: `agents/plan-agent.md`
  - Canonical plan-agent contract documentation.
- Modify: `tests/test_workflow.py`
  - Executable behavior coverage for assessment schema, persistence, and rejection.
- Modify: `tests/test_wrapper_contracts.py`
  - Static contract coverage for plan-agent prompt schema.
- Runtime only: cancel the bad active run through `workflow.py`; do not edit its `run.json` manually.

## Task 1: Add Failing Workflow Tests For The Contract

**Files:**
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add a test proving top-level assessment persists task metadata**

Add this test near the existing slicing assessment materialization tests:

```python
def test_multi_assessment_persists_task_refs_and_task_coverage(self):
    self._start_blocked_apply_run()
    self._dispatch_remediation()
    result = self._multi_assessment_result()
    result["slicing_assessment"]["task_coverage"] = {
        "slice-a": ["Task 1"],
        "slice-b": ["Task 2"],
    }
    result["slicing_assessment"]["implementation_slices"][0].update({
        "title": "First behavior",
        "task_refs": ["Task 1"],
        "objective": "Implement first behavior.",
        "acceptance_criteria": ["First behavior works."],
        "required_context_paths": ["docs/superpowers/specs/2026-07-15-slicing-assessment-contract-hardening.md"],
    })
    result["slicing_assessment"]["implementation_slices"][1].update({
        "title": "Second behavior",
        "task_refs": ["Task 2"],
        "objective": "Implement second behavior.",
        "acceptance_criteria": ["Second behavior works."],
        "required_context_paths": ["docs/superpowers/specs/2026-07-15-slicing-assessment-contract-hardening.md"],
    })

    rc, out, _ = run_workflow(
        self.tmp,
        "after-dispatch",
        agent="plan-agent",
        phase="apply_change",
        value=json.dumps(result),
    )

    self.assertEqual(rc, 0, out)
    state = self._read_current_state()
    assessment = state["implementation"]["slicing_assessment"]
    self.assertEqual(
        assessment["task_coverage"],
        {"slice-a": ["Task 1"], "slice-b": ["Task 2"]},
    )
    first = state["implementation"]["slices"][0]
    self.assertEqual(first["task_refs"], ["Task 1"])
    self.assertEqual(first["title"], "First behavior")
    self.assertEqual(first["objective"], "Implement first behavior.")
    self.assertEqual(first["acceptance_criteria"], ["First behavior works."])
    self.assertEqual(
        first["required_context_paths"],
        ["docs/superpowers/specs/2026-07-15-slicing-assessment-contract-hardening.md"],
    )
```

- [x] **Step 2: Add a test proving evidence.slicing_assessment is not authoritative**

Add this test near the same materialization tests:

```python
def test_slicing_assessment_under_evidence_does_not_materialize(self):
    self._start_blocked_apply_run()
    self._dispatch_remediation()
    result = self._multi_assessment_result()
    result["evidence"] = {"slicing_assessment": result.pop("slicing_assessment")}

    rc, out, _ = run_workflow(
        self.tmp,
        "after-dispatch",
        agent="plan-agent",
        phase="apply_change",
        value=json.dumps(result),
    )

    self.assertEqual(rc, 0, out)
    state = self._read_current_state()
    self.assertEqual(state["status"], "blocked")
    self.assertEqual(state["block"]["type"], "slicing_assessment_required")
    self.assertEqual(state["implementation"]["slices"], [])
```

- [x] **Step 3: Add a test proving missing task_refs is rejected**

Add this test near existing invalid slice contract tests:

```python
def test_materialization_rejects_slice_without_task_refs(self):
    self._start_blocked_apply_run()
    self._dispatch_remediation()
    result = self._multi_assessment_result()
    for item in result["slicing_assessment"]["implementation_slices"]:
        item["task_refs"] = [item["slice_id"]]
    result["slicing_assessment"]["implementation_slices"][0].pop("task_refs")

    rc, out, _ = run_workflow(
        self.tmp,
        "after-dispatch",
        agent="plan-agent",
        phase="apply_change",
        value=json.dumps(result),
    )

    self.assertEqual(rc, 0, out)
    state = self._read_current_state()
    self.assertEqual(state["status"], "blocked")
    self.assertEqual(state["block"]["type"], "slicing_assessment_required")
```

- [x] **Step 4: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "slicing_assessment or materialization" -v
```

Expected: at least the new persistence and missing `task_refs` tests fail before implementation.

## Task 2: Persist Task Metadata In Runtime State

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`

- [x] **Step 1: Expand required slice contract fields**

In both files, change `MULTI_SLICE_REQUIRED_SLICE_FIELDS` to:

```python
MULTI_SLICE_REQUIRED_SLICE_FIELDS = {
    "slice_id",
    "task_refs",
    "depends_on",
    "required",
    "scope",
    "verification_commands",
}
```

- [x] **Step 2: Validate task_refs shape**

In `_validate_multi_slice_contract(item)`, after the missing-field check, add:

```python
    task_refs = item.get("task_refs", [])
    if not isinstance(task_refs, list) or not task_refs or not all(
        isinstance(ref, str) and ref.strip() for ref in task_refs
    ):
        raise SlicingAssessmentError(
            "invalid_slice_task_refs",
            {"slice_id": item.get("slice_id", "?")},
        )
```

- [x] **Step 3: Persist task coverage**

In `materialize_slicing_assessment(agent_result, handoff_path)`, add `task_coverage` to the persisted assessment block:

```python
        "slicing_assessment": {
            "status": "completed",
            "decision": decision,
            "assessed_by": "plan-agent",
            "assessment_handoff_path": handoff_path,
            "reasons": reasons,
            "task_coverage": dict(assessment.get("task_coverage") or {}),
        },
```

- [x] **Step 4: Persist slice planning metadata**

In `materialize_slice_contract(item)`, extend the returned dict with these fields before execution state fields:

```python
        "title": item.get("title", ""),
        "task_refs": list(item.get("task_refs", []) or []),
        "objective": item.get("objective", ""),
        "scope": dict(item.get("scope") or {}),
        "acceptance_criteria": list(item.get("acceptance_criteria", []) or []),
        "verification_commands": list(item.get("verification_commands", []) or []),
        "required_context_paths": list(item.get("required_context_paths", []) or []),
```

- [x] **Step 5: Expand persisted slice validation**

In both files, add the persisted metadata fields to `SLICE_REQUIRED_FIELDS`:

```python
SLICE_REQUIRED_FIELDS = {
    "slice_id", "title", "task_refs", "objective", "scope",
    "acceptance_criteria", "verification_commands", "required_context_paths",
    "depends_on", "required", "status", "attempt_count",
    "block", "base_ref", "head_ref", "accepted_head_ref", "commit_refs",
    "implement_evidence", "review_evidence", "handoff_paths",
}
```

- [x] **Step 6: Run focused workflow tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "slicing_assessment or materialization" -v
```

Expected: new materialization tests pass, unless dispatch-specific error reporting still needs Task 3.

## Task 3: Make After-Dispatch Error Reporting Explicit

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/dispatch.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py`
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add explicit blocker for missing top-level assessment**

In the plan-agent slicing assessment remediation block around the call to
`materialize_slicing_assessment()`, before materialization, detect the invalid
payload shape:

```python
            if "slicing_assessment" not in agent_result:
                raise SlicingAssessmentError(
                    "missing_top_level_slicing_assessment",
                    {"hint": "slicing_assessment must be a top-level result field"},
                )
```

- [x] **Step 2: Preserve existing blocker behavior**

Keep the current `SlicingAssessmentError` handling path. The observable result
must remain a blocked run with `block.type == "slicing_assessment_required"`.

- [x] **Step 3: Strengthen the evidence.slicing_assessment test**

Update `test_slicing_assessment_under_evidence_does_not_materialize` to assert
the latest plan-agent result includes reason `missing_top_level_slicing_assessment`.

Use the state structure already written by after-dispatch:

```python
latest = state["evidence"]["agent_result"]
reasons = [b.get("reason") for b in latest.get("blockers", [])]
self.assertIn("missing_top_level_slicing_assessment", reasons)
```

- [x] **Step 4: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "slicing_assessment or materialization" -v
```

Expected: all focused assessment tests pass.

## Task 4: Update Plan-Agent Contract Documentation

**Files:**
- Modify: `agents/plan-agent.md`
- Modify: `tests/test_wrapper_contracts.py`

- [x] **Step 1: Replace abbreviated assessment output with full schema**

In `agents/plan-agent.md`, replace the abbreviated `implementation_slices: []`
example under `### Slicing Assessment Output` with the full schema from the spec,
including `task_coverage` and an example slice containing `task_refs`.

- [x] **Step 2: Add evidence boundary language**

Add this paragraph after the JSON example:

```markdown
`slicing_assessment` is a top-level state-transition payload. Do not place it
under `evidence`. `evidence` may explain why the assessment is valid, but it is
not the authoritative source for workflow state changes.
```

- [x] **Step 3: Add discovery-only exclusion language**

Add this rule under `### Assessment Rules`:

```markdown
- Do not create implement-agent slices for discovery-only, baseline-only, or
  contract-reading work that will not produce a valid implementation commit
  range. Capture that work in assessment evidence or a handoff instead.
```

- [x] **Step 4: Add static prompt checks**

In `tests/test_wrapper_contracts.py`, add checks against canonical `agents/plan-agent.md` that assert the prompt documents:

```python
self.assertIn('"task_coverage"', body)
self.assertIn('"task_refs"', body)
self.assertIn("top-level state-transition payload", body)
self.assertIn("Do not place it under `evidence`", body)
self.assertIn("discovery-only", body)
```

- [x] **Step 5: Run prompt contract tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k plan_agent -v
```

Expected: plan-agent prompt contract tests pass.

## Task 5: Cancel The Bad Run And Rebuild Cleanly

**Files:**
- Runtime state only under `.ai/workflows/runs/`

- [x] **Step 1: Inspect active run status**

Run:

```bash
python3 .ai/workflows/scripts/workflow.py --root . status --subject-type spec_change --subject-id derived-sync-hook-phase-awareness
```

Expected: active run `2026-07-15-derived-sync-hook-phase-awareness` is still present or already cancelled by a prior operator.

- [x] **Step 2: Cancel the bad run through runtime command**

Run:

```bash
python3 .ai/workflows/scripts/workflow.py --root . cancel-run --reason "abandon invalid slicing assessment contract run"
```

Expected: the run is no longer an active apply run. Do not manually edit
`.ai/workflows/runs/active/2026-07-15-derived-sync-hook-phase-awareness/run.json`.

- [x] **Step 3: Start a clean replacement run**

Run:

```bash
python3 .ai/workflows/scripts/workflow.py --root . start --workflow sdlc-main --subject-type spec_change --subject-id derived-sync-hook-phase-awareness --flow-type lightweight-flow
```

Expected: new run starts at `apply_change` blocked on `slicing_assessment_required`.

- [x] **Step 4: Dispatch plan-agent assessment remediation**

Run:

```bash
python3 .ai/workflows/scripts/workflow.py --root . before-dispatch --agent plan-agent --phase apply_change --action assess_implementation_slicing
```

Expected: dispatch succeeds with `recommended_next_action: execute_agent`.

- [x] **Step 5: Verify the new assessment excludes discovery-only slices**

After plan-agent returns a contract-compliant top-level `slicing_assessment`,
verify the first implementation slice is a code/test-producing slice such as
`phase-aware-policy-model`, not `baseline-discovery`.

Run:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-next
```

Expected: `slice_id` is not `baseline-discovery`.

## Task 6: Verify Template And Derived Artifact Consistency

**Files:**
- Check/fix derived copies as required by repository discipline.

- [x] **Step 1: Run focused workflow tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "slicing_assessment or materialization" -v
```

Expected: pass.

- [x] **Step 2: Run prompt contract tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k plan_agent -v
```

Expected: pass.

- [x] **Step 3: Run incremental derived sync check**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

Expected: either clean, or reports expected drift for workflow templates and agent distributions.

- [x] **Step 4: Fix derived drift if reported**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
```

Expected: canonical workflow templates and project-level agent distributions are synchronized for the touched canonical files.

- [x] **Step 5: Re-run derived sync check**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

Expected: clean.

## Self-Review Notes

- Spec coverage: top-level assessment contract, evidence boundary, task metadata persistence, task coverage round trip, discovery-only exclusion, and run rebuild are all covered.
- Placeholder scan: no placeholder tasks are present.
- Type consistency: `task_refs`, `task_coverage`, `implementation_slices`, and persisted `implementation.slices[]` use the same names across spec, tests, and implementation steps.
