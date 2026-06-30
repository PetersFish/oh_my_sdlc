# Plan Agent Handoff — run-artifacts-unify

## Metadata

- **Agent**: plan-agent
- **Phase**: create_change
- **Flow Type**: spec-flow
- **Change ID**: run-artifacts-unify
- **Run ID**: 2026-06-29-run-artifacts-unify
- **Timestamp**: 2026-06-29T22:00:00

## Objective

Unify all run artifacts (JSON state, plans, handoffs, logs) under a single `<run_id>/` directory with `run.json` as the canonical run state file, and auto-migrate legacy top-level `handoffs/` and `logs/` directories. No backward-compatible reading of old flat JSON files (product is pre-release).

## Work Completed

### Codebase Analysis
- Analyzed `workflow.py` (2850 lines) to identify all path-related functions:
  - `_active_path()` (line 99): returns `active/<run_id>.json` → needs `active/<run_id>/run.json`
  - `_list_active_runs()` (line 120): iterates flat `.json` files → needs to iterate subdirectories
  - `save_run_state()` (line 153): writes to flat path → needs to create directory
  - `_finalize_run_to_history()` (line 163): writes JSON, removes file → needs to move directory
  - `cmd_advance()` (line 2082): done-phase handling → same directory move pattern
  - `cmd_done()` (line 2149): same pattern → directory move
  - `cmd_cancel_run()` (line 1953): removes flat file → needs rmtree
  - `cmd_governance_check()` (line 2222): reads flat history files → needs dir support
- Analyzed agent definitions (6 files): already use new-style paths, no changes needed
- Analyzed test files: `test_workflow.py` (9 path references), `test_wrapper_contracts.py` (6 path references), `test_init_foundations.py` (1 reference)
- Analyzed `init_foundations.py`: no changes needed

### OpenSpec Artifacts Created
- `openspec/changes/run-artifacts-unify/proposal.md` — Why, What Changes, Capabilities, Impact
- `openspec/changes/run-artifacts-unify/design.md` — Context, Goals/Non-Goals, Decisions (D1-D4), Risks (R1-R4)
- `openspec/changes/run-artifacts-unify/specs/run-directory-unification/spec.md` — 6 requirements, 16 scenarios
- `openspec/changes/run-artifacts-unify/specs/run-legacy-migration/spec.md` — 3 requirements, 8 scenarios
- `openspec/changes/run-artifacts-unify/specs/sdlc-workflow-engine/spec.md` — 3 MODIFIED requirements, 30+ scenarios
- `openspec/changes/run-artifacts-unify/tasks.md` — 5 task groups, 20+ tasks

### Durable Plan Artifact
- `.ai/workflows/runs/2026-06-29-run-artifacts-unify/plans/default/plan.md` — TDD-aware implementation plan with:
  - 9 test case names with expected failure modes
  - Exact verification commands
  - 15 implementation tasks with code-level detail
  - Template sync steps

## Files/Artifacts Changed

- `openspec/changes/run-artifacts-unify/proposal.md` (created)
- `openspec/changes/run-artifacts-unify/design.md` (created)
- `openspec/changes/run-artifacts-unify/specs/run-directory-unification/spec.md` (created)
- `openspec/changes/run-artifacts-unify/specs/run-legacy-migration/spec.md` (created)
- `openspec/changes/run-artifacts-unify/specs/sdlc-workflow-engine/spec.md` (created)
- `openspec/changes/run-artifacts-unify/tasks.md` (created)
- `.ai/workflows/runs/2026-06-29-run-artifacts-unify/plans/default/plan.md` (created)
- `.ai/workflows/runs/2026-06-29-run-artifacts-unify/handoffs/default/plan-agent.md` (created)

## Commands Run

None (planning only — no execution).

## Evidence Summary

- **Spec artifacts**: All 4 OpenSpec artifacts complete (proposal, design, specs, tasks)
- **Plan**: TDD-aware plan with code-level detail for all 15 implementation tasks
- **Focused tests**: 9 test cases identified with expected failure modes (1 backward-compat test removed per revision request)
- **Coverage**: All workflow.py path functions, test helpers, inline references, and legacy migration covered

## Blockers

None. All required inputs are available.

## Revision History

- **2026-06-29 (rev 1):** Removed D4 backward compatibility per user request. Simplified governance_check and _read_history to new-format only. Product is pre-release — old-format unreadability is an accepted risk.

## Assumptions

1. Agent definitions do not need path changes (verified — they already use `<run_id>/handoffs/` and `<run_id>/logs/`)
2. `shutil.move()` is atomic on the same filesystem (standard on macOS/Linux)
3. Old flat `history/<run_id>.json` files become unreadable after migration — accepted risk (product is pre-release)
4. The existing active run `2026-06-29-run-artifacts-unify.json` will be migrated to the directory format during implementation

## Risks/Follow-Ups

- **R1**: Concurrent access during migration — mitigated by atomic `os.rename()` and sentinel file
- **R2**: Active run with existing flat JSON — handled by migration logic
- **R3**: Test suite disruption — all path references updated in the same change
- **R4**: Template sync required — `sync_templates.py` must be run after implementation

## Raw Logs

None (no commands executed).
