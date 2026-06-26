## MODIFIED Requirements

### Requirement: Run State Schema
The system SHALL persist active workflow runs using a directory-based layout with a pointer file, supporting multiple concurrent active runs. `current.json` SHALL be a pointer-only file; full run state SHALL live only in `active/<run_id>.json`.

#### Scenario: Active run file records required fields
- **WHEN** `.ai/workflows/runs/active/<run_id>.json` exists for an active run
- **THEN** it SHALL include `version`, `run_id`, `workflow`, `flow_type`, `status`, `current_phase`, `primary_subject`, `context`, `phase_readiness`, `pending_hooks`, `completed_hooks`, `completed_phases`, `evidence`, and `updated_at`

#### Scenario: Pointer file is minimal
- **WHEN** `current.json` exists as a pointer
- **THEN** it SHALL contain ONLY `{"run_id": "<run_id>"}` and SHALL NOT duplicate fields from `active/<run_id>.json`

#### Scenario: Pointer file tracks session run
- **WHEN** a workflow entry point (start, resume, preflight) resolves a run
- **THEN** `.ai/workflows/runs/current.json` SHALL contain `{"run_id": "<run_id>"}` pointing to the resolved run

#### Scenario: Primary subject is the resume key
- **WHEN** a workflow run is associated with an OpenSpec change
- **THEN** `primary_subject` SHALL include `type: openspec_change` and the OpenSpec change id

#### Scenario: Flow type defaults to spec-flow
- **WHEN** `workflow.py start` creates a new run without `--flow-type`
- **THEN** the persisted run state SHALL set `flow_type` to `spec-flow`

#### Scenario: Flow type preserves explicit choice
- **WHEN** `workflow.py start` creates a new run with `--flow-type lightweight-flow`
- **THEN** the persisted run state SHALL set `flow_type` to `lightweight-flow`

#### Scenario: Resume preserves stored flow type
- **WHEN** `workflow.py resume` reloads an existing active run
- **THEN** it SHALL preserve the stored `flow_type` instead of recomputing it from context

#### Scenario: Blocked run records block details
- **WHEN** a workflow run is blocked
- **THEN** the run state SHALL include a `block` object with the block type, message, and next allowed actions

#### Scenario: Done run writes history
- **WHEN** a workflow run reaches `done`
- **THEN** the runtime SHALL write a copy of the completed run to `.ai/workflows/runs/history/<run_id>.json`

#### Scenario: Done run is removed from active directory
- **WHEN** a workflow run reaches `done`
- **THEN** the runtime SHALL remove `active/<run_id>.json` and clear the pointer to `{}`

#### Scenario: Eval target is required for semantic verification
- **WHEN** the orchestrator classifies a workflow path as requiring semantic EvalOps verification
- **THEN** the run context SHALL include `eval_target_id` before the EvalOps gate can run

#### Scenario: Eval target is not required for deterministic-only verification
- **WHEN** the workflow requires only deterministic tests or non-semantic checks
- **THEN** the run context SHALL NOT require `eval_target_id`

### Requirement: Flow Type Selection And Confirmation
The system SHALL support `lightweight-flow` selection when an external agent (e.g., LLM) passes `--flow-type lightweight-flow`, but SHALL block the run at creation time until the user explicitly confirms the flow type choice. The runtime SHALL NOT infer flow type from subject type or other signals — flow type selection is an external decision.

#### Scenario: Default flow type is spec-flow
- **WHEN** `workflow.py start` runs without `--flow-type`
- **THEN** the runtime SHALL set `flow_type` to `spec-flow` and create a running run

#### Scenario: Explicit lightweight-flow requires user confirmation
- **WHEN** `workflow.py start` runs with `--flow-type lightweight-flow`
- **THEN** the created run SHALL have `status: blocked`, `block.type: user_decision_required`, a block message that names the flow type, and `block.next_allowed` listing the confirmation action

#### Scenario: Confirmed lightweight-flow becomes running
- **WHEN** the required confirmation action is recorded for a run blocked on `lightweight-flow`
- **THEN** the runtime SHALL clear the block, set `status: running`, set `flow_type: lightweight-flow`, and allow the run to advance

#### Scenario: Spec-flow never requires confirmation
- **WHEN** `workflow.py start` creates a `spec-flow` run (explicitly or as default)
- **THEN** the runtime SHALL NOT block for flow-type confirmation

### Requirement: SDLC Main Workflow Definition
The system SHALL define `sdlc-main` as the first workflow that models the full SDLC path instead of only the OpenSpec subset.

#### Scenario: Main workflow phases are defined
- **WHEN** `.ai/workflows/definitions/sdlc-main.yaml` is created
- **THEN** it SHALL define phases for `input`, `load_memory`, `brainstorm`, `decide_intent`, `create_roadmap`, `review_roadmap`, `review_decision`, `create_change`, `apply_change`, `archive_change`, `post_archive_actions`, and `done`

#### Scenario: Archive is not terminal
- **WHEN** `archive_change` completes
- **THEN** the workflow SHALL transition to `post_archive_actions` rather than `done`

#### Scenario: Post-archive actions gate completion
- **WHEN** `post_archive_actions` has pending hooks
- **THEN** the workflow SHALL NOT transition to `done`

#### Scenario: Workflow definition uses supported phase fields
- **WHEN** `.ai/workflows/definitions/sdlc-main.yaml` is validated
- **THEN** each phase SHALL use only supported workflow fields: `required_inputs`, `context_loaders`, `allowed_workers`, `evidence_keys`, `exit_criteria`, `post_hooks`, `branches`, `next`, and `terminal`

#### Scenario: Branch phase requires branch decision
- **WHEN** `workflow.py advance` runs for a phase with `branches`
- **THEN** it SHALL require a recorded branch decision and transition only to the phase mapped by that branch

#### Scenario: Unknown branch blocks
- **WHEN** a branch decision does not match a branch declared by the current phase
- **THEN** the runtime SHALL block with `user_decision_required` and SHALL NOT advance

### Requirement: Workflow Command API
The workflow runtime SHALL provide deterministic commands for run lifecycle, readiness, evidence, phase completion, hook completion, guarded transition, blocking, completion, and validation.

#### Scenario: Status is read-only
- **WHEN** `workflow.py status` runs
- **THEN** it SHALL NOT create, modify, or delete workflow run files

#### Scenario: Status shows pointed run full state
- **WHEN** `workflow.py status` runs without subject arguments
- **AND** `.ai/workflows/runs/current.json` contains `{"run_id": "<run_id>"}`
- **AND** `.ai/workflows/runs/active/<run_id>.json` exists
- **THEN** it SHALL show the full state from `active/<run_id>.json`

#### Scenario: Status lists active summaries when pointer is empty
- **WHEN** `workflow.py status` runs without subject arguments
- **AND** `.ai/workflows/runs/current.json` is absent or contains `{}`
- **THEN** it SHALL report that there is no current run
- **AND** it SHALL list summary metadata for all runs in `active/`

#### Scenario: Status reports stale pointer and lists active summaries
- **WHEN** `workflow.py status` runs without subject arguments
- **AND** `.ai/workflows/runs/current.json` points to a missing `active/<run_id>.json`
- **THEN** it SHALL report a stale pointer
- **AND** it SHALL list summary metadata for all runs in `active/`

#### Scenario: Status shows single run when subject given
- **WHEN** `workflow.py status` runs with `--subject-type` and `--subject-id`
- **THEN** it SHALL show the full state of the matching active run

#### Scenario: Start creates new run and sets pointer
- **WHEN** `workflow.py start` runs for a subject without an existing active run for that subject
- **THEN** it SHALL create `active/<run_id>.json`
- **AND** it SHALL update `current.json` to `{"run_id": "<run_id>"}`

#### Scenario: Start defaults flow type to spec-flow
- **WHEN** `workflow.py start` runs without `--flow-type`
- **THEN** the created run SHALL persist `flow_type: spec-flow`

#### Scenario: Start accepts explicit lightweight-flow
- **WHEN** `workflow.py start` runs with `--flow-type lightweight-flow`
- **THEN** the created run SHALL have `status: blocked`, `block.type: user_decision_required`, a block message naming the flow type, and `block.next_allowed` containing the confirmation action

#### Scenario: Confirmation unblocks lightweight-flow run
- **WHEN** the confirmation action is recorded for a run blocked on `lightweight-flow`
- **THEN** the runtime SHALL clear the block, set `status: running`, set `flow_type: lightweight-flow`, and allow the run to advance

#### Scenario: Start rejects same-subject duplicate
- **WHEN** `workflow.py start` runs for a subject that already has an active run
- **THEN** it SHALL report conflict and exit with code 1

#### Scenario: Start allows different-subject concurrent run
- **WHEN** `workflow.py start` runs for a different subject while another active run exists
- **THEN** it SHALL create a new `active/<run_id>.json` without conflict
- **AND** it SHALL update `current.json` to `{"run_id": "<run_id>"}`

#### Scenario: Resume recalculates without executing
- **WHEN** `workflow.py resume` runs with `--subject-type` and `--subject-id` matching an active run
- **THEN** it SHALL reload deterministic context, recalculate readiness, update the pointer, and SHALL NOT execute phase workers or hooks

#### Scenario: Resume requires subject arguments
- **WHEN** `workflow.py resume` runs without `--subject-type` and `--subject-id`
- **THEN** it SHALL report an error
- **AND** it SHALL list summary metadata for all runs in `active/`
- **AND** it SHALL prompt the user to re-run with the correct `--subject-type` and `--subject-id`

#### Scenario: Preflight switches current pointer by subject
- **WHEN** `workflow.py preflight` runs with `--subject-type` and `--subject-id`
- **AND** a matching active run exists
- **THEN** it SHALL update `current.json` to point to the matching run before evaluating the policy

#### Scenario: Resolve records deterministic loader results
- **WHEN** `workflow.py resolve` runs and a loader has a deterministic single result
- **THEN** it SHALL record the resolved context or evidence without executing workers

#### Scenario: Record evidence does not complete phase
- **WHEN** `workflow.py record-evidence` records external evidence
- **THEN** it SHALL update evidence and SHALL NOT mark a phase or hook complete

#### Scenario: Complete phase verifies exit criteria
- **WHEN** `workflow.py complete-phase` runs
- **THEN** it SHALL verify the current phase exit criteria before adding the phase to `completed_phases`

#### Scenario: Complete phase requires declared evidence keys
- **WHEN** `workflow.py complete-phase` runs for a phase that declares `evidence_keys`
- **THEN** it SHALL fail unless every declared evidence key is present and non-empty in the run evidence

#### Scenario: Complete hook verifies hook evidence
- **WHEN** `workflow.py complete-hook` runs
- **THEN** it SHALL verify the hook completion evidence before removing the hook from `pending_hooks`

#### Scenario: Block records allowed next actions
- **WHEN** `workflow.py block` runs
- **THEN** it SHALL set `status: blocked` and record block type, message, and next allowed actions

#### Scenario: Advance is guarded
- **WHEN** `workflow.py advance` runs
- **THEN** it SHALL transition only if the current phase is complete, the run is not blocked, and required hooks or gates for the phase do not prevent the transition

#### Scenario: Done requires no pending hooks
- **WHEN** `workflow.py done` runs
- **THEN** it SHALL fail or block unless the current phase is `done`, the run is not blocked, required gates are resolved, and `pending_hooks` is empty

#### Scenario: Done writes history and cleans up active
- **WHEN** `workflow.py done` succeeds
- **THEN** it SHALL write history, remove `active/<run_id>.json`, and clear the pointer to `{}`

#### Scenario: Validate is read-only
- **WHEN** `workflow.py validate` runs
- **THEN** it SHALL validate workflow definitions and run state without modifying files

#### Scenario: Validate rejects unknown flow type
- **WHEN** `workflow.py validate` runs against run state with a missing or unsupported `flow_type`
- **THEN** it SHALL report validation failure
