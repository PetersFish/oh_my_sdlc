# sdlc-workflow-engine

The SDLC workflow runtime engine provides repository-local workflow definitions, run state management, phase inference, deterministic context loaders, and a CLI command API for stateful SDLC flows.

## Requirements

### Requirement: Repository Workflow Runtime Layout
The system SHALL provide a repository-local workflow runtime under `.ai/workflows/` for workflow definitions, run state, run history, and deterministic runtime scripts.

#### Scenario: Bootstrap initializes workflow runtime directories
- **WHEN** `sdlc-project-bootstrap` initializes the SDLC project foundation
- **THEN** it SHALL create `.ai/workflows/definitions/`, `.ai/workflows/runs/`, and `.ai/workflows/scripts/`

#### Scenario: Bootstrap installs workflow runtime script
- **WHEN** workflow runtime support is initialized
- **THEN** `workflow.py` SHALL be available at `.ai/workflows/scripts/workflow.py`

#### Scenario: Workflow runtime is separate from tool configuration
- **WHEN** workflow definitions or run state are stored
- **THEN** they SHALL be stored under `.ai/workflows/` rather than `.opencode/`

### Requirement: Workflow State Ownership
The system SHALL separate workflow run state, domain state, and evidence state so the workflow runtime does not become the owner of Roadmap, OpenSpec, EvalOps, or Memory data.

#### Scenario: Workflow runtime owns run state
- **WHEN** a workflow run is started, resumed, blocked, advanced, or completed
- **THEN** `workflow.py` SHALL write workflow run state under `.ai/workflows/runs/`

#### Scenario: Domain state remains domain-owned
- **WHEN** roadmap, OpenSpec, EvalOps, or Memory state must change
- **THEN** the workflow runtime SHALL NOT directly edit that domain state and SHALL rely on the owning skill or CLI to perform the mutation

#### Scenario: Evidence records observed state
- **WHEN** a phase or hook completes based on a worker result or filesystem observation
- **THEN** the workflow runtime SHALL record evidence in the workflow run without treating that evidence as the domain source of truth

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

#### Scenario: Blocked run records block details
- **WHEN** a workflow run is blocked
- **THEN** the run state SHALL include a `block` object with the block type, message, and next allowed actions

#### Scenario: Flow type defaults to spec-flow
- **WHEN** `workflow.py start` creates a new run without `--flow-type`
- **THEN** the persisted run state SHALL set `flow_type` to `spec-flow`

#### Scenario: Flow type preserves explicit choice
- **WHEN** `workflow.py start` creates a new run with `--flow-type lightweight-flow`
- **THEN** the persisted run state SHALL set `flow_type` to `lightweight-flow`

#### Scenario: Resume preserves stored flow type
- **WHEN** `workflow.py resume` reloads an existing active run
- **THEN** it SHALL preserve the stored `flow_type` instead of recomputing it from context

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

### Requirement: Gate Resolution Ledger
The workflow runtime SHALL record cross-cutting quality gate outcomes in the run state's `gates` object without owning the underlying domain state.

#### Scenario: TDD gate records deterministic evidence
- **WHEN** deterministic tests are required for a workflow run
- **THEN** the runtime SHALL record the TDD gate status and evidence reference in `gates.tdd`

#### Scenario: EvalOps gate records semantic evidence
- **WHEN** semantic EvalOps verification is required for a workflow run
- **THEN** the runtime SHALL record the EvalOps gate status, `eval_target_id`, and evidence reference in `gates.evalops`

#### Scenario: EvalOps gate fails
- **WHEN** required EvalOps verification fails
- **THEN** the runtime SHALL block with `eval_failed` and require a human decision before the workflow can proceed

#### Scenario: EvalOps exception is explicit
- **WHEN** the user accepts an EvalOps exception after semantic verification fails or cannot run
- **THEN** the runtime SHALL record `gates.evalops.status` as `user_exception` with reason and residual risk

#### Scenario: Done requires required gates resolved
- **WHEN** `workflow.py done` runs
- **THEN** every required gate SHALL have status `passed`, `not_required`, or `user_exception`

### Requirement: Workflow Status Model
The workflow runtime SHALL use a minimal status model for workflow runs.

#### Scenario: Valid run statuses
- **WHEN** a run state is validated
- **THEN** `status` SHALL be one of `running`, `blocked`, `done`, or `cancelled`

#### Scenario: Valid block types
- **WHEN** a blocked run state is validated
- **THEN** `block.type` SHALL be one of `missing_required_inputs`, `user_decision_required`, `worker_failed`, `exit_criteria_failed`, `eval_failed`, `hook_blocked`, or `domain_state_mismatch`

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

### Requirement: Phase Inference
The workflow runtime SHALL infer a safe current phase from observable state when starting or resuming an OpenSpec change subject.

#### Scenario: Archived change starts at post archive actions
- **WHEN** `workflow.py start` or `workflow.py resume` runs for an OpenSpec change whose archive path exists
- **THEN** the runtime SHALL set or keep `current_phase` as `post_archive_actions`

#### Scenario: Active change with incomplete tasks starts at apply
- **WHEN** an active OpenSpec change exists and its tasks are incomplete
- **THEN** the runtime SHALL infer `apply_change`

#### Scenario: Active change with complete tasks requires verification or archive
- **WHEN** an active OpenSpec change exists and its tasks are complete
- **THEN** the runtime SHALL infer the next phase from verification evidence and block for user decision if the safe phase cannot be determined

#### Scenario: Missing change starts at create change
- **WHEN** no active or archived OpenSpec change exists for the subject id
- **THEN** the runtime SHALL infer `create_change`

### Requirement: Phase Readiness
The workflow runtime SHALL compute phase readiness before any worker skill is invoked.

#### Scenario: Missing input blocks worker execution
- **WHEN** the current phase has required inputs that are not present in run state or evidence
- **THEN** the runtime SHALL set `phase_readiness.ready` to `false`, record `missing_required_inputs`, and block the run with `missing_required_inputs`

#### Scenario: Ready phase may run worker
- **WHEN** all current phase required inputs are present
- **THEN** the runtime SHALL set `phase_readiness.ready` to `true` and allow the orchestrator to dispatch an allowed worker

#### Scenario: Blocked readiness allows only input resolution
- **WHEN** `phase_readiness.ready` is `false`
- **THEN** the orchestrator SHALL NOT dispatch the phase worker and SHALL only resolve missing inputs or ask for required user decisions

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

#### Scenario: Start defaults flow type to spec-flow
- **WHEN** `workflow.py start` runs without `--flow-type`
- **THEN** the created run SHALL persist `flow_type: spec-flow`

#### Scenario: Start accepts explicit lightweight-flow
- **WHEN** `workflow.py start` runs with `--flow-type lightweight-flow`
- **THEN** the created run SHALL have `status: blocked`, `block.type: user_decision_required`, a block message naming the flow type, and `block.next_allowed` containing the confirmation action

#### Scenario: Confirmation unblocks lightweight-flow run
- **WHEN** the confirmation action is recorded for a run blocked on `lightweight-flow`
- **THEN** the runtime SHALL clear the block, set `status: running`, set `flow_type: lightweight-flow`, and allow the run to advance

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

### Requirement: Deterministic Context Loaders
The workflow runtime SHALL provide deterministic loaders for observable workflow inputs and evidence.

#### Scenario: OpenSpec change status loader
- **WHEN** `openspec_change_status` runs for an OpenSpec change subject
- **THEN** it SHALL classify the change as active, archived, missing, in-progress, complete, or unknown based on files under `openspec/changes/` and `openspec/changes/archive/`

#### Scenario: Archive path loader
- **WHEN** `openspec_archive_path` runs with a change id
- **THEN** it SHALL record `evidence.archive_path` only when exactly one archive path matches the change id

#### Scenario: Roadmap linked item loader
- **WHEN** `roadmap_linked_item` runs with a change id
- **THEN** it SHALL scan roadmap item frontmatter for `openspec_change` matching the change id and record zero, one, or multiple match evidence without modifying roadmap files

#### Scenario: Ambiguous loader blocks
- **WHEN** a deterministic loader finds multiple high-risk matches that require user selection
- **THEN** the runtime SHALL block with `user_decision_required` and return candidates rather than guessing

#### Scenario: Loader outcome is deterministic
- **WHEN** a loader can derive exactly one safe value from repository state
- **THEN** the runtime SHALL classify the outcome as deterministic and may record it

#### Scenario: Loader outcome requires confirmation
- **WHEN** a loader finds multiple candidates or a high-risk inferred value
- **THEN** the runtime SHALL classify the outcome as user-confirmed and block for orchestrator-mediated confirmation

#### Scenario: Loader outcome requires manual input
- **WHEN** no deterministic source can provide a required input
- **THEN** the runtime SHALL classify the outcome as manual-required and block until the orchestrator obtains the input from the user

### Requirement: Roadmap Lifecycle Hooks
The workflow runtime SHALL coordinate linked roadmap state transitions at OpenSpec workflow boundaries without directly modifying roadmap item files. Hook completion for roadmap lifecycle hooks SHALL validate the observed roadmap item frontmatter state before removing the hook from `pending_hooks`.

#### Scenario: Create change can make linked roadmap item ready
- **WHEN** `create_change` completes OpenSpec artifacts for a linked roadmap item
- **THEN** the workflow SHALL register or run `roadmap_status_ready_if_linked` so the roadmap worker can make the item `ready` when applicable

#### Scenario: Ready hook requires observed ready state
- **WHEN** `roadmap_status_ready_if_linked` is pending for exactly one linked roadmap item
- **AND** the linked roadmap item status is `ready`
- **THEN** `complete-hook roadmap_status_ready_if_linked` SHALL remove the hook from `pending_hooks` and record roadmap hook evidence showing `ready`

#### Scenario: Ready hook blocks stale state
- **WHEN** `roadmap_status_ready_if_linked` is pending for exactly one linked roadmap item
- **AND** the linked roadmap item status is not `ready`
- **THEN** `complete-hook roadmap_status_ready_if_linked` SHALL keep the hook pending and block with `domain_state_mismatch`

#### Scenario: Ready hook handles no linked item idempotently
- **WHEN** `roadmap_status_ready_if_linked` is pending and the change has no linked roadmap item
- **THEN** `complete-hook roadmap_status_ready_if_linked` SHALL complete with `no_linked_item` evidence

#### Scenario: Ready hook blocks multiple linked items
- **WHEN** `roadmap_status_ready_if_linked` is pending and the change has multiple linked roadmap items
- **THEN** `complete-hook roadmap_status_ready_if_linked` SHALL keep the hook pending, block with `user_decision_required`, and report the candidate items

#### Scenario: Apply change can make linked roadmap item active
- **WHEN** `apply_change` starts for a linked roadmap item with `status: ready`
- **THEN** the workflow SHALL register or run `roadmap_apply_start_if_ready` so the roadmap worker can make the item `active` and set `started_at`

#### Scenario: Apply-start hook requires observed active state
- **WHEN** `roadmap_apply_start_if_ready` is pending for exactly one linked roadmap item
- **AND** the linked roadmap item status is `active`
- **AND** the linked roadmap item has a non-empty `started_at`
- **THEN** `complete-hook roadmap_apply_start_if_ready` SHALL remove the hook from `pending_hooks` and record roadmap hook evidence showing `active`

#### Scenario: Apply-start hook blocks stale ready state
- **WHEN** `roadmap_apply_start_if_ready` is pending for exactly one linked roadmap item
- **AND** the linked roadmap item status is `ready`
- **THEN** `complete-hook roadmap_apply_start_if_ready` SHALL keep the hook pending and block with `domain_state_mismatch`

#### Scenario: Apply-start hook handles no linked item idempotently
- **WHEN** `roadmap_apply_start_if_ready` is pending and the change has no linked roadmap item
- **THEN** `complete-hook roadmap_apply_start_if_ready` SHALL complete with `no_linked_item` evidence

#### Scenario: Apply-start hook blocks multiple linked items
- **WHEN** `roadmap_apply_start_if_ready` is pending and the change has multiple linked roadmap items
- **THEN** `complete-hook roadmap_apply_start_if_ready` SHALL keep the hook pending, block with `user_decision_required`, and report the candidate items

#### Scenario: Workflow does not mutate roadmap lifecycle directly
- **WHEN** roadmap ready, active, or done state must change
- **THEN** the workflow runtime SHALL rely on `sdlc-roadmap` or orchestrator-routed roadmap behavior rather than editing roadmap files directly

#### Scenario: Runtime remediation names roadmap worker
- **WHEN** a roadmap lifecycle hook blocks because the linked roadmap item state has not changed
- **THEN** the block or finding SHALL direct the next action to the existing `sdlc-roadmap` worker and SHALL NOT direct users to hand-edit `.roadmap/` files

### Requirement: Eval Failure Handling
The workflow runtime SHALL block apply completion when required semantic EvalOps verification fails until a human decision is recorded.

#### Scenario: Eval failure blocks apply
- **WHEN** required EvalOps cases fail during `apply_change`
- **THEN** the runtime SHALL block with `eval_failed`

#### Scenario: Eval failure exposes allowed next actions
- **WHEN** the runtime blocks with `eval_failed`
- **THEN** the block SHALL include next allowed actions to revise implementation, revise eval cases, revise spec, or accept an EvalOps exception with reason and residual risk

#### Scenario: Eval exception allows progress
- **WHEN** the user accepts an EvalOps exception with reason and residual risk
- **THEN** the runtime SHALL record the EvalOps gate as `user_exception` and MAY allow the workflow to continue

### Requirement: Post-Archive Hooks
The workflow runtime SHALL treat post-archive actions as mandatory hooks that must be resolved before workflow completion.

#### Scenario: Post-archive hooks are registered after archive
- **WHEN** `archive_change` completes and `archive_path_exists` is satisfied
- **THEN** the runtime SHALL register `memory_sync` and `roadmap_done_if_relevant` in `pending_hooks`

#### Scenario: Memory sync is mandatory
- **WHEN** `post_archive_actions` runs
- **THEN** `memory_sync` SHALL be resolved as `synced`, `not_needed` with explicit reason, or `user_deferred` with explicit reason and residual risk before it can be removed from `pending_hooks`

#### Scenario: Roadmap hook handles no linked item
- **WHEN** an archived change has no linked roadmap item
- **THEN** `roadmap_done_if_relevant` SHALL complete with `no_linked_item` evidence

#### Scenario: Roadmap hook handles active linked item
- **WHEN** an archived change has exactly one linked roadmap item with `status: active`
- **THEN** `roadmap_done_if_relevant` SHALL remain pending until `sdlc-roadmap done <item-id>` is invoked and the item is verified as `done` with non-null `completed_at`

#### Scenario: Roadmap hook handles already done item
- **WHEN** an archived change has exactly one linked roadmap item with `status: done` and non-null `completed_at`
- **THEN** `roadmap_done_if_relevant` SHALL complete idempotently

#### Scenario: Roadmap hook blocks mismatched state
- **WHEN** an archived change has exactly one linked roadmap item with `status: idea`, `ready`, or `cancelled`
- **THEN** `roadmap_done_if_relevant` SHALL block with `domain_state_mismatch`

#### Scenario: Roadmap hook blocks multiple linked items
- **WHEN** an archived change has multiple linked roadmap items
- **THEN** `roadmap_done_if_relevant` SHALL block with `user_decision_required`, return candidates, and allow user decisions to choose one item, repair links manually, mark all active matches done with reason, or skip with reason

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

### Requirement: Temporary Workspace Testing
The workflow runtime SHALL be tested with isolated temporary workspaces and explicit root paths.

#### Scenario: Tests use explicit root
- **WHEN** workflow runtime tests execute filesystem operations
- **THEN** they SHALL pass an explicit `--root <tmp-workspace>` path

#### Scenario: Tests do not mutate domain state
- **WHEN** `workflow.py` runs in tests
- **THEN** it SHALL write only under `<root>/.ai/workflows/runs/` and SHALL NOT modify fixture roadmap, OpenSpec, EvalOps, or Memory domain files

#### Scenario: Archived active roadmap regression
- **WHEN** a temporary workspace contains an archived OpenSpec change linked to an active roadmap item
- **THEN** starting or resuming the workflow SHALL enter `post_archive_actions`, leave `roadmap_done_if_relevant` pending, and prevent `done`

#### Scenario: Archived done roadmap regression
- **WHEN** a temporary workspace contains an archived OpenSpec change linked to a done roadmap item with non-null `completed_at`
- **THEN** `roadmap_done_if_relevant` SHALL complete idempotently and the workflow MAY reach `done` after remaining hooks are resolved
