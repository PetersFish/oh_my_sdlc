## 1. Workflow Runtime Foundation

- [x] 1.1 Create `.ai/workflows/definitions/`, `.ai/workflows/runs/`, `.ai/workflows/runs/history/`, and `.ai/workflows/scripts/` directory layout
- [x] 1.2 Add `sdlc-project-bootstrap` support to initialize the `.ai/workflows/` directory tree and install `workflow.py`
- [x] 1.3 Define and document the run state JSON schema for `.ai/workflows/runs/current.json` with required fields, status enums, and block types
- [x] 1.4 Define and document the `gates` ledger for TDD, EvalOps, and human-approved exceptions, including gate status values and done-time resolution rules
- [x] 1.5 Document that `context.eval_target_id` is required only when semantic EvalOps verification is required, and not required for deterministic-only verification
- [x] 1.6 Implement `workflow.py status` for read-only run state reporting
- [x] 1.7 Implement `workflow.py validate` for read-only workflow definition and run state consistency checks

## 2. Workflow Definition

- [x] 2.1 Create `.ai/workflows/definitions/sdlc-main.yaml` with the 12-phase contract and required inputs, allowed workers, exit criteria, hooks, and next transitions
- [x] 2.2 Validate the workflow definition schema: each phase SHALL have required inputs, allowed workers, exit criteria, and a next or terminal declaration
- [x] 2.3 Add branch handling for `decide_intent` and `review_decision`, including validation of declared branch labels and blocking for unknown branch decisions
- [x] 2.4 Implement OpenSpec subject phase inference for start/resume: archived changes resume at post_archive_actions, active incomplete changes resume at apply_change, complete-task changes infer verification/archive safely, and missing changes start at create_change

## 3. workflow.py Lifecycle Commands

- [x] 3.1 Implement `workflow.py start` to create a new run or detect a matching active run for resume
- [x] 3.2 Implement `workflow.py resume` to reload deterministic context, recalculate readiness, and return phase/block/next actions without executing workers
- [x] 3.3 Implement `workflow.py readiness` to compute whether current phase required inputs are present and set phase readiness/missing/blocked
- [x] 3.4 Implement `workflow.py resolve` to run deterministic loaders and fill resolvable context and evidence fields
- [x] 3.5 Implement `workflow.py record-evidence` to store externally produced worker/skill results without completing phases
- [x] 3.6 Implement `workflow.py complete-phase` to verify exit criteria, mark the phase complete, and register post hooks into pending_hooks
- [x] 3.7 Implement `workflow.py complete-hook` to verify hook completion evidence, clear resolved hooks, and enforce mandatory memory_sync resolution states
- [x] 3.8 Implement `workflow.py advance` as a guarded transition: only advance when the current phase is complete, the run is not blocked, and required hooks/readiness for the next phase are satisfied
- [x] 3.9 Implement `workflow.py block` to record a blocked state with type, message, and next allowed actions
- [x] 3.10 Implement `workflow.py done` to close the run and write history, enforcing that pending_hooks is empty, the run is not blocked, and required gates are resolved
- [x] 3.11 Ensure `workflow.py done` preserves `.ai/workflows/runs/current.json` as the latest run with `status: done` and writes an immutable history copy
- [x] 3.12 Add explicit tests for `resolve`, `record-evidence`, `complete-phase`, `complete-hook`, and `block` command side effects and non-side effects

## 4. Deterministic Loaders

- [x] 4.1 Implement `openspec_change_status` loader to classify a change as active, archived, missing, in-progress, complete, or unknown based on `openspec/changes/*` and `openspec/changes/archive/*`
- [x] 4.2 Implement `openspec_archive_path` loader to record `evidence.archive_path` only when exactly one archive path matches the change id
- [x] 4.3 Implement `roadmap_linked_item` loader to scan `.ai/roadmap/areas/*/items/*.md` frontmatter for `openspec_change` matching the change id and record zero, one, or multiple match evidence
- [x] 4.4 Implement `roadmap_item_status` loader to read the linked roadmap item status and record evidence without modifying roadmap domain files
- [x] 4.5 Enforce ambiguous-loader blocking: when a deterministic loader finds multiple high-risk matches requiring user selection, block with `user_decision_required` and return candidates

## 5. Post-Archive Hooks

- [x] 5.1 Define `roadmap_done_if_relevant` hook behavior: no linked item completes with no_linked_item evidence; one active item blocks until roadmap done; one done item completes idempotently; one idea/ready/cancelled item blocks with domain_state_mismatch; multiple linked items block with user_decision_required and allowed decisions
- [x] 5.2 Define `memory_sync` hook behavior: must resolve as synced, not_needed with explicit reason, or user_deferred with explicit reason and residual risk before being removed from pending_hooks
- [x] 5.3 Implement hook registration: when `archive_change` completes and `archive_path_exists` is satisfied, register `memory_sync` and `roadmap_done_if_relevant` in pending_hooks
- [x] 5.4 Enforce that `done` cannot be reached while post-archive hooks or any required hook remains pending
- [x] 5.5 Implement `roadmap_status_ready_if_linked` for create_change completion so linked roadmap items can become ready through roadmap-owned mutation
- [x] 5.6 Implement `roadmap_apply_start_if_ready` for apply_change start so linked ready roadmap items can become active through roadmap-owned mutation

## 6. Orchestrator Integration

- [x] 6.1 Update `sdlc-orchestrator` skill guidance to use `workflow.py start/resume` for SDLC runs and `workflow.py readiness` before dispatching phase workers
- [x] 6.2 Update orchestrator guidance to call `workflow.py complete-phase` or `workflow.py complete-hook` after worker completion and use `workflow.py advance` exclusively for phase transitions
- [x] 6.3 Update orchestrator guidance to detect blocked states from workflow.py and explain block reasons with next allowed actions to the user
- [x] 6.4 Update orchestrator guidance to never claim lifecycle completion before `workflow.py` confirms the run can reach `done`

## 7. Roadmap Integration

- [x] 7.1 Update `sdlc-roadmap` skill guidance to clarify that roadmap item files remain the domain source of truth and workflow hooks invoke `sdlc-roadmap done` mutations
- [x] 7.2 Update roadmap guidance to note that `roadmap_done_if_relevant` hook coordination is owned by `sdlc-orchestrator` and the workflow runtime; roadmap only executes mutations when invoked
- [x] 7.3 Verify that `sdlc-roadmap sync.py` still works as a diagnostic-only tool and does not attempt to auto-trigger post-archive transitions

## 8. Memory Sync Integration

- [x] 8.1 Update `sdlc-openspec-memory-sync` spec and guidance so post-archive memory sync produces workflow evidence when the active change directory is no longer available
- [x] 8.2 Update memory sync skill guidance to accept workflow-provided change context (archive path, evidence) for post-archive runs
- [x] 8.3 Remove the mandatory pre-archive gate expectation from memory sync guidance; keep the skill as the durable worker

## 9. Tests and Fixtures

- [x] 9.1 Set up temporary-workspace test fixtures that create minimal `openspec/changes/archive/<date>-demo-change/` and `.ai/roadmap/areas/<area>/items/*.md` with frontmatter under a tmp root
- [x] 9.2 Archived change + active roadmap blocks workflow done
- [x] 9.3 Archived change + done roadmap completes hook idempotently and allows done
- [x] 9.4 Archived change + no roadmap link completes hook with no_linked_item
- [x] 9.5 Archived change + multiple roadmap links blocks with user_decision_required and candidates
- [x] 9.6 Archived change + non-active non-done roadmap (idea/ready/cancelled) blocks with domain_state_mismatch
- [x] 9.7 Missing required input blocks readiness with missing_required_inputs
- [x] 9.8 Same-subject resume reuses run_id, recalculates readiness, and creates no new run
- [x] 9.9 Different-subject resume returns conflict/user decision without overwriting the active run
- [x] 9.10 Memory sync deferred without reason fails or blocks
- [x] 9.11 Semantic EvalOps-required workflow without `eval_target_id` blocks before EvalOps gate runs
- [x] 9.12 Deterministic-only workflow does not require `eval_target_id`
- [x] 9.13 EvalOps failure blocks with `eval_failed` and requires a human decision before proceeding
- [x] 9.14 EvalOps exception with reason and residual risk records `gates.evalops.status=user_exception` and allows progress
- [x] 9.15 Branch phase with unknown decision blocks with user_decision_required
- [x] 9.16 Done preserves current.json as status done and writes a history copy
- [x] 9.17 Write-boundary test: workflow.py writes only `.ai/workflows/runs/*` and does not modify fixture roadmap or OpenSpec domain files
- [x] 9.18 Test that all commands accepting filesystem inspection support an explicit `--root` argument

## 10. Validation and Docs

- [x] 10.1 Run `workflow.py validate` on the completed workflow definition and run state to confirm schema compliance
- [x] 10.2 Confirm that `openspec status --change add-sdlc-workflow-engine` reports all artifacts complete after tasks are done
- [x] 10.3 Verify the full post-archive regression: starting an SDLC run for an archived change with active roadmap leaves hooks pending and prevents done
