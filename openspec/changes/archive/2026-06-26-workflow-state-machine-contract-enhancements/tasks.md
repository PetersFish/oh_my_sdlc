## 1. Failing Behavior Tests

- [x] 1.1 Add behavior test proving `workflow.py start` without `--flow-type` persists `flow_type: spec-flow` in active run state
- [x] 1.2 Add behavior test proving `workflow.py start --flow-type lightweight-flow` creates blocked run requiring user confirmation
- [x] 1.3 Add behavior test proving `workflow.py resume` preserves the stored `flow_type` instead of recomputing it
- [x] 1.4 Add behavior test proving `workflow.py validate` rejects a run state with missing or unsupported `flow_type`
- [x] 1.5 Add behavior test proving explicit `--flow-type lightweight-flow` creates a blocked run with `block.type: user_decision_required`, names the flow type in the message, and lists the confirmation action in `next_allowed`
- [x] 1.6 Add behavior test proving recording the confirmation action clears the block, sets `status: running`, sets `flow_type: lightweight-flow`, and allows the run to advance
- [x] 1.7 Add behavior test proving `evidence_keys` rejects non-list or empty-string entries during workflow definition validation
- [x] 1.8 Add behavior test proving `complete-phase` fails when a declared evidence key is missing from run evidence
- [x] 1.9 Add behavior test proving `complete-phase` fails when a declared evidence key exists but has an empty value
- [x] 1.10 Add behavior test proving `complete-phase` succeeds when all declared evidence keys are present and non-empty
- [x] 1.11 Add behavior test proving `record-evidence` still does not complete a phase or trigger evidence-key validation by itself
- [x] 1.12 Add behavior test proving default `roadmap_item` start (no `--flow-type`) creates running `spec-flow` run, not blocked
- [x] 1.13 Add behavior test proving `--flow-type bogus-flow` is rejected by argparse
- [x] 1.14 Add behavior test proving falsy JSON evidence values (`False`, `0`, `[]`, `{}`) are treated as empty evidence and fail `complete-phase`

## 2. Flow Type Runtime Contract

- [x] 2.1 Add `flow_type` to `RUN_STATE_KEYS` and `validate_run_state` so missing `flow_type` is a validation error
- [x] 2.2 Persist `flow_type: spec-flow` when `workflow.py start` creates a run without `--flow-type`
- [x] 2.3 Reject invalid `--flow-type` values via argparse `choices`
- [x] 2.4 Preserve stored `flow_type` in `cmd_resume` instead of recomputing from context
- [x] 2.5 Implement confirmation-gated `lightweight-flow`: when `--flow-type lightweight-flow` is passed (by external LLM/orchestrator), create a blocked run with `user_decision_required` block; user confirms via evidence + resolve to unblock

## 3. Evidence Key Runtime Contract

- [x] 3.1 Add `evidence_keys` to `SUPPORTED_PHASE_FIELDS` and `validate_workflow` so it is accepted as a valid phase field
- [x] 3.2 Validate that `evidence_keys` on a phase is a list of non-empty strings and report errors for non-list or empty-string entries
- [x] 3.3 Update `cmd_complete_phase` to check declared `evidence_keys` against run `evidence` before marking the phase complete
- [x] 3.4 Fail `complete-phase` with a descriptive error when a declared evidence key is missing or has an empty value
- [x] 3.5 Allow `complete-phase` to succeed when all declared evidence keys are present and non-empty, and all existing exit criteria also pass
- [x] 3.6 Preserve existing `record-evidence`, hook registration, block clearing, and phase-completion behavior outside the new evidence-key validation gate

## 4. Template Sync And Verification

- [x] 4.1 Sync `.ai/workflows/scripts/workflow.py` and `.ai/workflows/definitions/sdlc-main.yaml` changes to `skills/sdlc-project-bootstrap/templates/workflow/`
- [x] 4.2 Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` to verify no live-to-canonical drift
- [x] 4.3 Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed` to verify no distributed drift
- [x] 4.4 Run `python3 -m pytest tests/test_workflow.py -v` and confirm all existing tests still pass
- [x] 4.5 Run `python3 .ai/workflows/scripts/workflow.py --root . validate`
- [x] 4.6 Run `openspec validate --changes workflow-state-machine-contract-enhancements`
