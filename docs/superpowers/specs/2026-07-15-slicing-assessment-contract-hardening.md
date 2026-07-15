# Slicing Assessment Contract Hardening

## Context

The `derived-sync-hook-phase-awareness` lightweight-flow run exposed several
contract gaps in the sliced `apply_change` assessment path:

- plan-agent output was manually wrapped with `slicing_assessment` under
  `evidence`, but the documented and implemented contract requires a top-level
  `slicing_assessment` object;
- the runtime accepted multi-slice entries for materialization but discarded
  planning metadata such as `task_refs`, `title`, `objective`, `scope`, and
  verification commands when writing `run.json`;
- plan-agent documentation names required multi-slice fields but does not show
  a complete authoritative JSON schema;
- a discovery-only slice was materialized as an implementation slice, which then
  failed the implement-agent Git ref contract because it had no implementation
  commit range.

This change hardens the contract before rebuilding the affected run. The current
active run for `derived-sync-hook-phase-awareness` is not repaired in place; it
is intentionally abandoned and replaced after the contract is fixed.

## Goals

- Make the authoritative plan-agent slicing assessment payload unambiguous.
- Persist task-to-slice metadata in `run.json` so later agents can see which
  plan tasks each slice owns.
- Reject malformed multi-slice contracts before implementation dispatch.
- Keep `evidence` as supporting proof, not the source of workflow state
  transitions.
- Prevent discovery-only or baseline-only work from entering the implement/review
  commit chain.
- Rebuild the affected workflow run from clean contract-compliant state.

## Non-Goals

- Do not add compatibility for `evidence.slicing_assessment` as an authoritative
  input.
- Do not patch the existing bad run state by hand.
- Do not weaken implement-agent requirements for `base_ref`, `head_ref`, and
  ordered `commit_refs[]`.
- Do not redesign the whole sliced apply-change runtime.
- Do not create a new workflow phase.

## Decisions

### 1. Top-Level Slicing Assessment Is Authoritative

plan-agent assessment results MUST use this top-level shape:

```json
{
  "agent": "plan-agent",
  "status": "success",
  "phase": "apply_change",
  "slice_id": "default",
  "flow_type": "lightweight-flow",
  "slicing_assessment": {
    "decision": "single_slice|multi_slice|blocked",
    "confidence": "high|medium|low",
    "reasons": [],
    "signals": {
      "independent_behaviors": 0,
      "dependency_layers": 0,
      "expected_core_files": 0,
      "cross_module_boundaries": 0,
      "independent_verification_boundaries": 0,
      "migration_or_compatibility_work": false,
      "multiple_external_integrations": false,
      "high_debug_uncertainty": false
    },
    "task_coverage": {},
    "implementation_slices": []
  },
  "evidence": {},
  "artifacts": {},
  "blockers": [],
  "recommended_next_action": "persist_slicing_assessment"
}
```

`evidence.slicing_assessment` is not a valid authoritative payload. Runtime
should reject or ignore it unless a future spec explicitly changes this
contract.

### 2. Evidence Supports Decisions But Does Not Drive State Transitions

`evidence` may contain supporting facts such as `focused_tests`,
`verification_summary`, `criteria_satisfied`, and rationale fields. It MUST NOT
be the source for fields that mutate workflow state, such as slice graphs,
branch finish decisions, terminal movement, or archive actions.

Any field that changes workflow state MUST be a documented top-level typed
payload or a documented typed artifact.

### 3. Multi-Slice Entries Must Carry Task Metadata

Each `implementation_slices[]` entry MUST include:

```json
{
  "slice_id": "phase-aware-policy-model",
  "title": "Reusable phase and drift policy model",
  "task_refs": ["Task 3", "Task 4"],
  "depends_on": [],
  "objective": "One independently verifiable behavior.",
  "scope": {"expected_paths": []},
  "acceptance_criteria": [],
  "verification_commands": [],
  "required_context_paths": [],
  "required": true
}
```

`task_refs` must refer to stable task labels from the approved plan. Every
required plan task must be covered exactly once unless it is explicitly
cross-cutting in `task_coverage`.

### 4. Runtime Must Persist Slice Planning Metadata

When materializing `implementation.slices[]`, the runtime MUST preserve planning
metadata needed by implement-agent, review-agent, and later audit:

- `title`
- `task_refs`
- `objective`
- `scope`
- `acceptance_criteria`
- `verification_commands`
- `required_context_paths`

The runtime MUST continue preserving execution fields:

- `status`
- `attempt_count`
- `block`
- `base_ref`
- `head_ref`
- `accepted_head_ref`
- `commit_refs`
- `implement_evidence`
- `review_evidence`
- `handoff_paths`

### 5. Task Coverage Must Round Trip Through Run State

`implementation.slicing_assessment.task_coverage` MUST be written during
materialization and readable later from `run.json`. This proves the assessment
can drive later slice selection, handoff generation, review scoping, and audit
without rereading the original plan.

### 6. Discovery-Only Work Is Not An Implementation Slice

Discovery-only, baseline-only, or contract-reading work that produces no
source/test implementation commit MUST NOT be modeled as an implement-agent
slice. That work belongs in plan-agent assessment evidence or a durable handoff.

An implement-agent slice must be expected to produce a valid Git range:

```text
base_ref -> ordered commit_refs[] -> head_ref
```

### 7. Current Bad Run Is Abandoned, Not Repaired

The active run `2026-07-15-derived-sync-hook-phase-awareness` should be closed
or cancelled through the workflow runtime and replaced after this contract fix.
Do not manually edit its `run.json` to fabricate refs or patch slice metadata.

## Acceptance Scenarios

### Scenario 1: Top-Level Assessment Materializes

Given a blocked apply run with `slicing_assessment_required`, when plan-agent
returns a successful result with top-level `slicing_assessment`, the runtime
materializes `implementation.slices[]`, clears the blocker, and makes the first
valid implementation slice selectable.

### Scenario 2: Assessment Under Evidence Does Not Materialize

Given the same blocked run, when plan-agent returns `evidence.slicing_assessment`
without top-level `slicing_assessment`, the runtime does not materialize slices
and reports a contract violation or invalid assessment.

### Scenario 3: Task Metadata Persists

Given a multi-slice assessment with `task_refs` and `task_coverage`, after
materialization `run.json` contains the same task metadata on each slice and the
same coverage map under `implementation.slicing_assessment.task_coverage`.

### Scenario 4: Missing Task Refs Are Rejected

Given a multi-slice assessment where one slice omits `task_refs`, after-dispatch
keeps the run blocked and reports a slice contract error.

### Scenario 5: Discovery-Only Slice Is Rejected By Assessment Policy

Given an assessment that classifies a baseline-only task as an implement-agent
slice with no expected implementation commit, review of the assessment should
reject it before implementation dispatch.

## Verification

- Add executable workflow tests in `tests/test_workflow.py` for materialization,
  persistence, and rejection behavior.
- Static prompt checks may verify that plan-agent documents the schema, but they
  are not sufficient for runtime behavior.
- The final implementation must run focused workflow tests and then derived
  artifact sync checks because canonical workflow runtime and agent prompt files
  are affected.
