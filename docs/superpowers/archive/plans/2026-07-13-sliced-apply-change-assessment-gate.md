# Sliced Apply-Change Assessment Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make validated implementation slice metadata a mandatory apply-change precondition, route missing assessments through a blocked plan-agent remediation path, explicitly repair legacy active runs, and remove redundant aggregate review for single-slice work.

**Architecture:** Workflow state owns a persisted slicing-assessment gate. Apply-ready runs without a validated slice graph remain blocked; plan-agent may enter that blocked run only as `assess_implementation_slicing` remediation. Runtime code validates and atomically materializes the result before `slice-next` can select implementation work. Active legacy runs use an explicit `slice-init` migration command, while historical compatibility remains read-only.

**Tech Stack:** Python 3 standard library, modular workflow runtime, JSON run state, Git-backed slice evidence, pytest/unittest workflow fixtures, Markdown agent contracts, and the existing workflow/template distribution pipeline.

**Primary Spec:** `docs/superpowers/specs/2026-07-13-sliced-apply-change-assessment-gate-design.md`

**Execution Constraint:** Do not commit unless the user explicitly requests a commit. Do not revert or overwrite unrelated worktree changes. Keep this plan's checkboxes synchronized after each completed step.

---

## File Structure

### Runtime

| File | Responsibility | Planned change |
|---|---|---|
| `.ai/workflows/scripts/workflow_runtime/state.py` | Canonical run state, implementation state validation, pure materialization helpers | Add pending/default constructors, active-apply assessment validation, explicit-waiver validation, and atomic assessment materialization helpers |
| `.ai/workflows/scripts/workflow_runtime/lifecycle.py` | Start, resume, readiness, phase transitions, blockers | Create or enforce the slicing blocker when apply is selected without validated metadata |
| `.ai/workflows/scripts/workflow_runtime/dispatch.py` | Agent routing and before/after-dispatch state transitions | Reject apply workers before assessment, allow only blocked remediation plan-agent dispatch, persist remediation intent, materialize successful assessment, and implement single-slice review completion |
| `.ai/workflows/scripts/workflow_runtime/slices.py` | Slice query and exceptional control commands | Add `slice-init`; make `slice-status` and `slice-next` report assessment-required instead of synthesizing an active default slice |
| `.ai/workflows/scripts/workflow_runtime/cli.py` | CLI parsing and command dispatch | Register `slice-init` and `--skip-assessment` |
| `.ai/workflows/scripts/workflow.py` | Stable CLI facade | No behavior implementation; update imports/exports only if current facade inventory requires it |

### Agent Contracts

| File | Responsibility | Planned change |
|---|---|---|
| `agents/dev-orchestrator.md` | Runtime-driven lifecycle routing | Replace direct start-with-plan implementation with blocked assessment remediation and `slice-next` routing |
| `agents/plan-agent.md` | Planning and slicing assessment | Require remediation metadata and preserve approved design boundaries |
| `agents/implement-agent.md` | One-slice implementation | Require a runtime-selected slice for every apply dispatch |
| `agents/review-agent.md` | Slice and aggregate review | Document single-slice review completion and multi-slice aggregate behavior |

### Tests and Derived Artifacts

| File | Responsibility | Planned change |
|---|---|---|
| `tests/test_workflow.py` | Executable workflow CLI and state round-trip contracts | Add fresh-run gate, legacy repair, remediation routing, materialization, explicit waiver, and review behavior tests |
| `tests/test_workflow_modules.py` | Runtime module boundaries | Update import/command inventory only if new helpers or command registration require it |
| `tests/test_wrapper_contracts.py` | Canonical and distributed agent/template contracts | Assert corrected routing language and synchronized copies |
| `skills/sdlc-project-bootstrap/templates/workflow/` | Canonical bootstrap workflow templates | Synchronize from live `.ai/workflows/` implementation |
| `.opencode/`, `.claude/`, `.cursor/` | Derived agent and skill copies | Regenerate through repository sync commands, never edit first |

---

## Task 1: Capture the Fresh-Run Bypass as Executable Tests

**Files:**
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add a helper that starts an apply-ready lightweight run**

Reuse the existing `run_workflow` fixture and create the minimum approved-plan fixture needed for `_infer_phase` to select `apply_change`. The helper must invoke the CLI rather than constructing the final run state directly.

```python
def _start_apply_ready_run(self, subject_id="assessment-gate"):
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
```

Use the existing lightweight confirmation helper or record the required confirmation evidence through the CLI; do not edit the generated run file to simulate confirmation.

- [x] **Step 2: Add a failing test proving a fresh run is blocked for assessment**

```python
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
```

- [x] **Step 3: Add a failing test proving direct implementation is rejected**

Invoke:

```bash
python3 .ai/workflows/scripts/workflow.py --root <fixture> \
  before-dispatch --agent implement-agent --phase apply_change
```

Assert non-zero exit and blocker reason `slicing_assessment_pending`. The test must fail if the implementation merely stores the right state words but still accepts dispatch.

- [x] **Step 4: Add a failing test proving `slice-next` cannot synthesize default**

```python
def test_slice_next_reports_assessment_required_before_materialization(self):
    self._start_apply_ready_run()
    rc, out, _ = run_workflow(self.tmp, "slice-next")
    self.assertEqual(rc, 0, out)
    self.assertEqual(json.loads(out), {
        "status": "assessment_required",
        "reason": "slicing_assessment_pending",
        "recommended_next_action": "dispatch_plan_agent_for_slicing_assessment",
    })
```

- [x] **Step 5: Run the focused tests and confirm RED**

```bash
python3 -m pytest tests/test_workflow.py -k "fresh_apply_ready or assessment_required_before" -v
```

Expected: failures because `cmd_start` omits implementation state and direct dispatch remains accepted.

---

## Task 2: Add the Persisted Apply Assessment Gate

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/lifecycle.py`
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add pure pending-state and blocker constructors**

Add these focused helpers in `state.py`:

```python
def make_pending_implementation_state():
    return {
        "strategy": "sequential",
        "slicing_assessment": {
            "status": "pending",
            "decision": "",
            "assessed_by": "",
            "assessment_handoff_path": "",
            "reasons": [],
        },
        "aggregate_review_status": "pending",
        "active_slice_id": None,
        "slices": [],
    }


def make_slicing_assessment_block():
    return {
        "type": "slicing_assessment_required",
        "message": "Apply cannot continue without validated implementation slices",
        "next_allowed": ["dispatch_plan_agent"],
    }
```

Return fresh nested objects on every call.

- [x] **Step 2: Distinguish active dispatch state from historical compatibility**

Replace implicit active authorization with an explicit helper:

```python
def active_apply_slicing_errors(state):
    if state.get("current_phase") != "apply_change":
        return []
    impl = state.get("implementation")
    if impl is None:
        return [{
            "reason": "missing_slicing_assessment",
            "message": "Active apply run has no persisted implementation slicing state",
            "slice_ids": [],
        }]
    return validate_implementation_state(impl)
```

Do not remove read-only legacy normalization for terminal/history display. Ensure active readiness and dispatch paths call the persisted-state helper instead.

- [x] **Step 3: Initialize apply-ready starts with pending state**

In both lightweight and spec-flow branches of `cmd_start`, when inferred phase is `apply_change`:

```python
state["implementation"] = make_pending_implementation_state()
state["status"] = "blocked"
state["block"] = make_slicing_assessment_block()
state["phase_readiness"] = {
    "phase": "apply_change",
    "ready": False,
    "missing_required_inputs": ["validated_implementation_slices"],
}
```

Preserve the existing lightweight flow confirmation gate. When both confirmation and assessment are pending, confirmation is resolved first; resolving it must reveal or install the slicing blocker rather than mark apply running.

- [x] **Step 4: Gate transitions into apply_change**

Before a create-change run becomes executable apply work, require a valid materialized assessment. If planning completed without assessment, install the slicing blocker instead of advancing into running apply.

Do not reset user approval or regenerate approved design artifacts.

- [x] **Step 5: Update legacy validation expectations**

Replace the existing test that treats every missing implementation as valid. Add two behavior tests:

```python
def test_active_apply_missing_implementation_requires_explicit_repair(self):
    self._make_apply_run(implementation=None)
    rc, out, _ = run_workflow(self.tmp, "before-dispatch", agent="implement-agent")
    self.assertNotEqual(rc, 0)
    self.assertIn(
        "missing_slicing_assessment",
        [item["reason"] for item in json.loads(out)["blockers"]],
    )


def test_terminal_legacy_run_remains_readable(self):
    self._make_terminal_run_without_implementation()
    rc, out, _ = run_workflow(self.tmp, "status")
    self.assertEqual(rc, 0, out)
```

- [x] **Step 6: Run focused tests and confirm GREEN**

```bash
python3 -m pytest tests/test_workflow.py -k "fresh_apply_ready or active_apply_missing or terminal_legacy" -v
```

---

## Task 3: Add Explicit Legacy Run Initialization

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/cli.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/slices.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add failing `slice-init` behavior tests**

Cover these executable cases:

| Scenario | Expected result |
|---|---|
| active apply run missing implementation plus non-empty reason | pending state persisted, blocker installed |
| missing reason | non-zero, `missing_repair_reason` |
| non-apply active run | non-zero, `slice_init_wrong_phase` |
| already valid implementation | success no-op, state unchanged |
| malformed partial implementation | non-zero, `existing_implementation_invalid` |
| unconsumed implement dispatch intent and no matching result | intent cleared and audit evidence recorded |
| matching agent result exists | command refuses destructive repair |
| unrelated worktree files exist | contents and status remain unchanged |

- [x] **Step 2: Register the command and flag**

Add `slice-init` to command registration and add a boolean `--skip-assessment` option. Reuse the existing global `--reason` option.

```text
workflow.py slice-init --reason <audit reason> [--skip-assessment]
```

- [x] **Step 3: Implement narrow initialization behavior**

Add `cmd_slice_init(root, args)` in `slices.py`. It must:

```python
if state.get("current_phase") != "apply_change":
    emit_error("slice_init_wrong_phase")
if not (args.reason or "").strip():
    emit_error("missing_repair_reason")
if state.get("implementation") is not None:
    validate_or_noop_without_overwrite()
```

For normal repair, persist `make_pending_implementation_state()` and
`make_slicing_assessment_block()` through `save_run_state`.

- [x] **Step 4: Record auditable migration evidence**

Append a structured record without replacing prior evidence:

```json
{
  "slicing_migrations": [{
    "action": "slice_init",
    "reason": "...",
    "migrated_at": "...",
    "previous_implementation_present": false,
    "cleared_dispatch_intent": true
  }]
}
```

Clear `evidence.agent_phase` only when it names implement-agent and no matching result exists under `evidence.agent_results`. Never clear completed evidence.

- [x] **Step 5: Prove the command does not touch worktree files**

In a temporary Git fixture, create and modify a sentinel source file before running `slice-init`. Assert byte-for-byte content and porcelain status are unchanged afterward.

- [x] **Step 6: Run focused tests**

```bash
python3 -m pytest tests/test_workflow.py -k "slice_init" -v
```

---

## Task 4: Route Blocked Apply to Plan-Agent Remediation

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/dispatch.py`
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add failing routing tests**

Add behavior tests proving:

- normal plan-agent dispatch in a running apply phase is rejected;
- blocked apply with `slicing_assessment_required` accepts plan-agent only with
  `--action assess_implementation_slicing`;
- a different action is rejected with `plan_agent_not_assessment_remediation`;
- a different blocker type cannot use this exception;
- implement-agent and review-agent remain blocked;
- successful `before-dispatch` persists action and assessment context in the dispatch intent.

- [x] **Step 2: Keep the normal phase map unchanged**

Do not add plan-agent here:

```python
PHASE_AGENT_MAP = {
    "create_change": {"plan-agent", "roadmap-agent"},
    "apply_change": {"implement-agent", "review-agent", "roadmap-agent"},
}
```

- [x] **Step 3: Add a narrow remediation predicate**

```python
def _allows_slicing_assessment_remediation(state, canonical_agent, action):
    block = state.get("block") or {}
    assessment = (state.get("implementation") or {}).get(
        "slicing_assessment", {}
    )
    return (
        state.get("current_phase") == "apply_change"
        and state.get("status") == "blocked"
        and canonical_agent == "plan-agent"
        and action == "assess_implementation_slicing"
        and block.get("type") == "slicing_assessment_required"
        and "dispatch_plan_agent" in (block.get("next_allowed") or [])
        and assessment.get("status") in {"pending", "blocked"}
    )
```

Use this predicate as an explicit exception to blocked-run and phase-map rejection.

- [x] **Step 4: Persist the remediation intent**

Include these values in `evidence.agent_phase`:

```json
{
  "agent": "plan-agent",
  "agent_phase": "apply_change",
  "action": "assess_implementation_slicing",
  "remediation_for": "slicing_assessment_required"
}
```

- [x] **Step 5: Run focused routing tests**

```bash
python3 -m pytest tests/test_workflow.py -k "slicing_assessment_remediation or plan_agent_not_assessment" -v
```

---

## Task 5: Validate and Materialize Plan-Agent Assessment

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/dispatch.py`
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add assessment fixture builders**

Use test-only builders for valid single and multi results. A valid multi result must include independent verification fields rather than only ids and dependencies.

```python
def _single_assessment_result():
    return {
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
        }
    }
```

- [x] **Step 2: Add failing atomic-materialization tests**

Exercise the full hook sequence:

```text
before-dispatch plan-agent remediation
→ after-dispatch plan-agent structured result
→ reload run.json
→ inspect implementation
→ call slice-next
```

Assert a single decision creates only `default`. Assert a multi decision preserves declaration order, dependencies, task refs, scope, criteria, verification commands, and required context paths.

- [x] **Step 3: Add failing rejection tests**

The run must remain blocked and preserve its prior pending state for:

- missing assessment;
- invalid decision;
- empty reasons;
- invalid confidence;
- duplicate slice ids;
- reserved `aggregate` id;
- unknown dependency;
- cyclic dependency;
- empty required task coverage;
- task covered by two non-cross-cutting slices;
- malformed scope or verification commands;
- stale plan-agent result with no matching dispatch intent;
- plan-agent result from a different action.

- [x] **Step 4: Implement pure materialization helpers**

Add a helper with no file I/O:

```python
def materialize_slicing_assessment(agent_result, handoff_path):
    assessment = agent_result.get("slicing_assessment") or {}
    decision = assessment.get("decision")
    if decision == "single_slice":
        slices = [_make_default_slice()]
    elif decision == "multi_slice":
        slices = [
            materialize_slice_contract(item)
            for item in assessment.get("implementation_slices", [])
        ]
    else:
        raise SlicingAssessmentError("invalid_assessment_decision")

    impl = {
        "strategy": "sequential",
        "slicing_assessment": {
            "status": "completed",
            "decision": decision,
            "assessed_by": "plan-agent",
            "assessment_handoff_path": handoff_path,
            "reasons": list(assessment.get("reasons") or []),
        },
        "aggregate_review_status": "pending",
        "active_slice_id": None,
        "slices": slices,
    }
    errors = validate_implementation_state(impl)
    if errors:
        raise SlicingAssessmentError("invalid_slicing_assessment", errors)
    return impl
```

Use the repository's existing error style rather than introducing a public exception type if a structured return value is the established pattern.

- [x] **Step 5: Integrate materialization into `after-dispatch`**

Only process the result when the stored dispatch intent matches plan-agent,
`apply_change`, `assess_implementation_slicing`, and the slicing blocker.

Construct the complete replacement state in memory, validate it, then save once. On success:

```python
state["implementation"] = materialized
state["block"] = None
state["status"] = "running"
state["phase_readiness"] = {
    "phase": "apply_change",
    "ready": True,
    "missing_required_inputs": [],
}
recommended_next_action = "call_slice_next"
```

- [x] **Step 6: Preserve blocked assessment results**

If plan-agent returns `decision=blocked` or status blocked, persist only validated blocker evidence and assessment reasons. Keep the run blocked and recommend user clarification or plan-agent retry. Do not create slices.

- [x] **Step 7: Run focused tests**

```bash
python3 -m pytest tests/test_workflow.py -k "materialize_assessment or invalid_slicing_assessment or assessment_result" -v
```

---

## Task 6: Enforce Explicit No-Decomposition Semantics

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/slices.py`
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add failing waiver validation tests**

Reject each state independently:

- `not_required` with no reason;
- whitespace-only reason;
- empty `assessed_by`;
- decision other than `single_slice`;
- no default slice;
- multiple slices;
- non-default slice id.

- [x] **Step 2: Add a no-decomposition constructor**

```python
def make_no_decomposition_implementation_state(reason, assessed_by="user"):
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("missing_no_decomposition_reason")
    return {
        "strategy": "sequential",
        "slicing_assessment": {
            "status": "not_required",
            "decision": "single_slice",
            "assessed_by": assessed_by,
            "assessment_handoff_path": "",
            "reasons": [reason],
        },
        "aggregate_review_status": "pending",
        "active_slice_id": None,
        "slices": [_make_default_slice()],
    }
```

- [x] **Step 3: Implement `slice-init --skip-assessment`**

Require a non-empty reason, materialize the explicit state, validate it, clear the slicing blocker, and record audit evidence identifying an explicit user decision.

Do not infer this mode from task count, plan length, or missing metadata.

- [x] **Step 4: Prove the default slice remains governed**

After explicit initialization:

```text
slice-next -> dispatch_slice(default)
before-dispatch implement-agent without exact runtime-selected slice -> rejected
before-dispatch implement-agent --slice-id default -> accepted
```

If backward compatibility currently permits omitting `--slice-id` for default, update the contract so all new persisted implementation states require the explicit id. Limit any omission compatibility to historical runs that cannot execute new work.

- [x] **Step 5: Run focused tests**

```bash
python3 -m pytest tests/test_workflow.py -k "no_decomposition or skip_assessment or explicit_default_slice" -v
```

---

## Task 7: Remove Redundant Aggregate Review for Single Slice

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/dispatch.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/slices.py`
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Add failing single-slice lifecycle test**

Exercise the complete state transition:

```text
default pending
→ before-dispatch implement
→ after-dispatch implement success
→ before-dispatch review
→ after-dispatch review pass
→ slice-next
```

Assert:

```python
self.assertEqual(default_slice["status"], "completed")
self.assertEqual(default_slice["accepted_head_ref"], head_ref)
self.assertEqual(impl["aggregate_review_status"], "passed")
self.assertEqual(slice_next["status"], "all_slices_and_aggregate_complete")
```

- [x] **Step 2: Add a multi-slice regression test**

After all required slice reviews pass, assert aggregate status is `ready` and
`slice-next` returns `dispatch_aggregate_review`.

- [x] **Step 3: Add a required-slice counting helper**

```python
def required_slices(impl):
    return [sl for sl in impl.get("slices", []) if sl.get("required", True)]
```

After slice review pass:

```python
if all_required_slices_completed(impl):
    impl["aggregate_review_status"] = (
        "passed" if len(required_slices(impl)) == 1 else "ready"
    )
```

Cancelled optional slices must not force aggregate review. A malformed implementation with zero required slices must fail validation rather than auto-pass.

- [x] **Step 4: Update aggregate validation invariants**

Allow `passed` directly after the only required slice review. Continue requiring explicit aggregate review evidence before `passed` when there are multiple required slices.

- [x] **Step 5: Run focused tests**

```bash
python3 -m pytest tests/test_workflow.py -k "single_slice and aggregate or multi_slice and aggregate" -v
```

---

## Task 8: Correct Agent Routing Contracts

**Files:**
- Modify: `agents/dev-orchestrator.md`
- Modify: `agents/plan-agent.md`
- Modify: `agents/implement-agent.md`
- Modify: `agents/review-agent.md`
- Modify: `tests/test_wrapper_contracts.py`

- [x] **Step 1: Add failing contract assertions**

Static assertions are appropriate here because the subject is agent prompt copy. Assert the canonical prompts require these exact behavioral concepts:

- start-with-plan skips redesign, not slicing assessment;
- missing metadata blocks apply;
- plan-agent is remediation-only in blocked apply;
- `slice-next` owns slice selection;
- implement-agent always receives an exact slice id;
- single slice has no second aggregate review;
- multi-slice work retains aggregate review.

Do not use these prompt tests as substitutes for the executable runtime tests from Tasks 1-7.

- [x] **Step 2: Rewrite start-with-plan routing**

Replace the direct sequence:

```text
start/resume -> before-dispatch implement-agent
```

with:

```text
start/resume
-> inspect blocker and slicing status
-> dispatch plan-agent remediation when required
-> after-dispatch persists assessment
-> slice-next
-> implement exact returned slice
```

- [x] **Step 3: Constrain plan-agent remediation**

Document that `planning_action=assess_implementation_slicing`:

- reads all approved artifacts;
- reorganizes work without redesigning behavior;
- returns the structured assessment contract;
- returns blocked on insufficient confidence;
- never edits source or tests.

- [x] **Step 4: Tighten implement and review contracts**

Implement-agent must reject dispatch without a runtime-selected `slice_id`, including `default` for new runs. Review-agent must treat one-slice review as final apply review and use aggregate scope only when the runtime returns `dispatch_aggregate_review`.

- [x] **Step 5: Run canonical contract tests**

```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
```

---

## Task 9: Synchronize Workflow Templates and Derived Agent Copies

**Files:**
- Derived from live runtime: `skills/sdlc-project-bootstrap/templates/workflow/`
- Derived from canonical agents: `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`
- Derived skill copies as selected by incremental sync

- [x] **Step 1: Run focused tests before generation**

```bash
python3 -m pytest tests/test_workflow.py -k "slicing_assessment or slice_init or single_slice" -v
python3 -m pytest tests/test_workflow_modules.py -v
python3 -m pytest tests/test_wrapper_contracts.py -v
```

Stop and fix canonical sources if any command fails.

- [x] **Step 2: Synchronize changed canonical artifacts**

Use the aggregate entrypoint:

```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
```

Do not manually edit any distributed copy.

- [x] **Step 3: Verify incremental drift closure**

```bash
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

Expected: exit 0 and no affected-suite drift.

- [x] **Step 4: Run template-specific checks**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed
```

Expected: both exit 0.

---

## Task 10: Repair and Reassess the Current Active Run

**Files:**
- Modify through runtime only: `.ai/workflows/runs/active/2026-07-13-repository-memory-structural-reconciliation/run.json`
- Do not modify as part of repair: repository source, tests, or plan files

- [x] **Step 1: Inspect current run and worktree without changing either**

```bash
python3 .ai/workflows/scripts/workflow.py --root . status \
  --subject-type spec_change \
  --subject-id repository-memory-structural-reconciliation
git status --short
```

Record the existing unconsumed implement dispatch intent and current unrelated changes. Do not revert the cancelled worker's files without explicit user instruction.

- [x] **Step 2: Initialize the run explicitly**

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-init \
  --reason "Active run was created without persisted slicing assessment"
```

Expected: pending assessment, `slicing_assessment_required` blocker, migration evidence, and no active implementation slice.

- [x] **Step 3: Verify worktree preservation**

Run `git status --short` again and compare source/test/doc entries with Step 1. Only workflow run-state changes attributable to `slice-init` are allowed.

- [x] **Step 4: Dispatch plan-agent through the remediation gate**

```bash
python3 .ai/workflows/scripts/workflow.py --root . before-dispatch \
  --agent plan-agent \
  --phase apply_change \
  --action assess_implementation_slicing
```

Dispatch plan-agent with:

- `docs/superpowers/specs/2026-07-12-repository-memory-structural-reconciliation-design.md`;
- `docs/superpowers/plans/2026-07-12-repository-memory-structural-reconciliation.md`;
- `planning_action=assess_implementation_slicing`;
- the current run id and blocker evidence.

- [x] **Step 5: Record the result and select the first slice**

Pass the structured result through `after-dispatch`, then run:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-status
python3 .ai/workflows/scripts/workflow.py --root . slice-next
```

Expected: valid persisted slice graph, run status `running`, no slicing blocker, and exactly one runtime-selected next slice.

---

## Task 11: Run Full Verification and Record Evidence

**Files:**
- Modify only if failures expose a defect in this change

- [x] **Step 1: Run focused workflow suites**

```bash
python3 -m pytest tests/test_workflow.py -k "slicing_assessment or slice_init or slice_next or aggregate_review" -v
python3 -m pytest tests/test_workflow_modules.py -v
python3 -m pytest tests/test_wrapper_contracts.py -v
```

- [x] **Step 2: Run the full workflow suite**

```bash
python3 -m pytest tests/test_workflow.py -v
```

- [x] **Step 3: Run the full repository suite**

```bash
python3 -m pytest -v
```

- [x] **Step 4: Run full derived-artifact verification**

```bash
python3 scripts/sync_derived_artifacts.py --check
```

- [x] **Step 5: Verify the behavior end to end**

In a temporary fixture, execute and assert this sequence:

```text
fresh apply-ready start
-> blocked pending assessment
-> direct implement rejected
-> plan-agent remediation accepted
-> valid assessment persisted
-> blocker cleared
-> slice-next selects exact slice
-> implement and slice review complete
-> single slice returns all_slices_and_aggregate_complete
```

Also execute the multi-slice path through aggregate review.

- [x] **Step 6: Inspect final diff and runtime outputs**

```bash
git status --short
git diff -- .ai/workflows/scripts agents tests \
  skills/sdlc-project-bootstrap/templates/workflow \
  docs/superpowers/specs/2026-07-13-sliced-apply-change-assessment-gate-design.md \
  docs/superpowers/plans/2026-07-13-sliced-apply-change-assessment-gate.md
```

Confirm no unrelated run history, roadmap data, memory snapshots, or cancelled-worker files were altered by this implementation.

- [x] **Step 7: Verify durable plan progress**

```bash
python3 scripts/check_plan_checkboxes.py \
  docs/superpowers/plans/2026-07-13-sliced-apply-change-assessment-gate.md
```

Expected: exit 0 after all actual work and verification steps are complete.

---

## Acceptance Criteria

- [x] Fresh apply-ready runs persist pending assessment state and remain blocked.
- [x] Active apply runs missing `implementation` cannot dispatch apply workers.
- [x] `slice-next` never synthesizes an executable default slice for missing or pending active state.
- [x] Plan-agent is not in the normal apply phase map.
- [x] Plan-agent can enter blocked apply only for `assess_implementation_slicing` remediation.
- [x] Valid plan-agent output is atomically materialized and clears the blocker.
- [x] Invalid or blocked assessment output cannot partially update state or unblock apply.
- [x] Explicit no-decomposition requires a non-empty reason and materializes `default`.
- [x] Every new implementation dispatch includes the exact runtime-selected slice id.
- [x] Legacy active runs require explicit `slice-init` repair with audit evidence.
- [x] Repair does not modify source, tests, plans, or unrelated worktree state.
- [x] Historical and terminal runs remain readable without authorizing active dispatch.
- [x] Single-slice work receives one slice review and no aggregate review.
- [x] Multi-slice work receives per-slice reviews and final aggregate review.
- [x] Start-with-plan orchestration skips redesign but never skips slicing assessment.
- [x] The current repository-memory run can be repaired and routed to assessment.
- [x] Focused and full tests pass.
- [x] Canonical workflow templates and distributed agent copies have no drift.

## Rollback

Rollback must revert runtime gate code, CLI registration, tests, canonical agent prompts,
workflow templates, and distributed copies together. If the current active run has
already been initialized, restore its prior run-state file from version control or a
captured pre-migration copy only as an explicit user-approved operation. Never roll
back source code while leaving a run that depends on the new assessment state contract,
and never delete unrelated worktree files while rolling back workflow state.
