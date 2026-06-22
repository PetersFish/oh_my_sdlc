## MODIFIED Requirements

### Requirement: Run State Schema
The system SHALL persist active workflow runs using a directory-based layout with a pointer file, supporting multiple concurrent active runs. `current.json` SHALL be a pointer-only file; full run state SHALL live only in `active/<run_id>.json`.

#### Scenario: Active run file records required fields
- **WHEN** `.ai/workflows/runs/active/<run_id>.json` exists for an active run
- **THEN** it SHALL include `version`, `run_id`, `workflow`, `status`, `current_phase`, `primary_subject`, `context`, `phase_readiness`, `pending_hooks`, `completed_hooks`, `completed_phases`, `evidence`, and `updated_at`

#### Scenario: Pointer file is minimal
- **WHEN** `current.json` exists as a pointer
- **THEN** it SHALL contain ONLY `{"run_id": "<run_id>"}` and SHALL NOT duplicate fields from `active/<run_id>.json`

#### Scenario: Pointer file tracks session run
- **WHEN** a workflow entry point (start, resume, preflight) resolves a run
- **THEN** `.ai/workflows/runs/current.json` SHALL contain `{"run_id": "<run_id>"}` pointing to the resolved run

#### Scenario: Primary subject is the resume key
- **WHEN** a workflow run is associated with an OpenSpec change
- **THEN** `primary_subject` SHALL include `type: openspec_change` and the OpenSpec change id

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

### Requirement: Resume Semantics
The workflow runtime SHALL support session continuity for multiple concurrent runs without automatically hijacking unrelated new work.

#### Scenario: Explicit resume resumes active run
- **WHEN** the user explicitly asks to resume a workflow with `--subject-type` and `--subject-id` and a matching active run exists
- **THEN** the orchestrator SHALL call `workflow.py resume` and report the current phase, block state, pending hooks, and next allowed actions

#### Scenario: Subject match resumes active run
- **WHEN** a user request references the same subject as an active run
- **THEN** the orchestrator SHALL resume the matching run rather than starting a duplicate run

#### Scenario: Unrelated request does not auto-resume
- **WHEN** a user request is unrelated to any active workflow subject
- **THEN** the orchestrator SHALL NOT automatically resume the workflow and MAY briefly report that active runs remain pending for other subjects

#### Scenario: Session switching via preflight
- **WHEN** the user starts work on a different change while another run is active
- **THEN** the next `preflight` call SHALL search `active/` for the matching run and update the pointer, making session switching transparent

### Requirement: Governance-Check Scanning
The governance-check command SHALL scan all active runs in `active/` for pending hooks, not just the pointed run.

#### Scenario: Governance-check scans all active runs
- **WHEN** `workflow.py governance-check` runs
- **THEN** it SHALL iterate all `active/*.json` files and check each for `pending_hooks`

#### Scenario: Governance-check reports pending hooks from any active run
- **WHEN** any active run has non-empty `pending_hooks`
- **THEN** `governance-check` SHALL include a finding for each such run

#### Scenario: Governance-check continues history scan for dangling archives
- **WHEN** `workflow.py governance-check` runs
- **THEN** it SHALL continue to scan `history/` for done runs and compare with archive paths to detect dangling archives
