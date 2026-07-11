# Implement-Agent Handoff (Revision 2 — Review Blockers Addressed)

## Metadata

- **Agent:** implement-agent
- **Phase:** apply_change
- **Slice ID:** default
- **Flow Type:** spec-flow
- **Change ID:** repair-workflow-decision-block-unlock
- **Run ID:** 2026-07-11-repair-workflow-decision-block-unlock
- **Timestamp:** 2026-07-11
- **Revision:** 2 — addresses review-agent blockers (key-agnostic reconciliation + change-set mismatch)

## Objective

Implement the OpenSpec repair `repair-workflow-decision-block-unlock`: when a workflow branch decision is missing or invalid and the run is blocked, recording a corrected valid `branch_finish_decision` through `record-context` must reconcile the stale block — setting status to `running` and clearing the block — so normal guarded dispatch/advance can proceed. Unrelated blocks, invalid corrections, and unrelated context key writes must be preserved.

## Review Blockers Addressed

### Blocker 1: Restrict reconciliation to `branch_finish_decision` key

**Issue:** `_should_reconcile_branch_decision_block(state, tentative_context)` checked only that the tentative context resolved to a valid decision. If `context.branch_finish_decision` was already valid (from a prior write), recording any unrelated context key (e.g. `change_id`, `execution_mode`) would spuriously transition the run to `running` and clear the block.

**Fix:** Added `recorded_key` parameter to `_should_reconcile_branch_decision_block`. The function now returns False immediately when `recorded_key != "branch_finish_decision"`. Updated `cmd_record_context` call site to pass `args.key`.

**TDD proof:**
- RED: `test_unrelated_context_key_does_not_clear_branch_decision_block` — pre-populated valid decision in context, recorded `change_id` key, asserted block preserved. FAILED before fix (`'running' != 'blocked'`).
- GREEN: Same test PASSED after adding `recorded_key` guard.

### Blocker 2: Regenerate change-set evidence from live Git

**Issue:** The original handoff declared 7 changed files but omitted agent drift repair files, roadmap state changes, and workflow run artifacts that were present in live Git.

**Fix:** Regenerated full change-set evidence from `git status --porcelain -uall` and `git diff --stat`. All changes are now enumerated below with clear attribution.

## Work Completed

### Task 1: Behavioral Regression Tests (RED phase)

Added 7 tests in `tests/test_workflow.py` under `TestBranchFinishDecisionBlockReconciliation`:

1. `test_corrected_valid_branch_finish_decision_clears_missing_decision_block` — missing decision → valid decision clears block
2. `test_corrected_valid_branch_finish_decision_allows_dispatch` — after correction, before-dispatch succeeds
3. `test_corrected_valid_branch_finish_decision_clears_invalid_decision_block` — invalid → each allowed value clears block + dispatch succeeds
4. `test_invalid_branch_finish_decision_correction_preserves_block` — invalid correction preserves block
5. `test_valid_branch_finish_decision_preserves_unrelated_block` — valid decision preserves worker/hook/domain blocks byte-for-byte
6. `test_branch_finish_decision_does_not_unblock_when_gate_not_required` — main-checkout without feature branch preserves unrelated block
7. `test_unrelated_context_key_does_not_clear_branch_decision_block` — recording a non-`branch_finish_decision` key preserves block even when context already has a valid decision (review blocker 1 regression)

### Task 2: Minimal State Reconciliation (GREEN phase)

Added two helpers in `.ai/workflows/scripts/workflow.py`:

- `_is_branch_decision_block(block)` — recognizes the runtime-owned branch-decision block by structured type (`user_decision_required`) + next_allowed (`ask_user_branch_finish_decision`), not message substring matching.
- `_should_reconcile_branch_decision_block(state, tentative_context, recorded_key)` — returns True only when: recorded key is `branch_finish_decision`, run is blocked, persisted block is a branch-decision block, and tentative context resolves to decision status `ok`.

Updated `cmd_record_context` to call `_should_reconcile_branch_decision_block(state, context, args.key)` after writing the context value; when True, atomically sets `status: running` and `block: None` before the existing save.

### Task 3: Full Verification And Governed Sync

- Full workflow runtime suite: 322 passed, 25 subtests passed (36.44s)
- Template sync: live → canonical → all distributed copies (`.opencode`, `.claude`, `.cursor`)
- Drift check: `OK: all governed files in sync with canonical`, `OK: all distributed copies match canonical`
- Incremental derived-artifact check: `OK: all 6 check suites in sync`
- `git diff --check`: no whitespace errors

### Task 4: EvalOps Assessment

Recorded EvalOps as `not_required` — deterministic CLI/state-machine behavior, no AI behavior target.

## Complete Live Git Change-Set

Discovered via `git status --porcelain -uall` and `git diff --stat` after all implementation and sync commands.

### Changes Attributable To This Work (implementation + template sync + OpenSpec artifacts)

| File | Status | Source | Reason |
|------|--------|--------|--------|
| `.ai/workflows/scripts/workflow.py` | modified | `git diff` | Added `_is_branch_decision_block`, `_should_reconcile_branch_decision_block` (with `recorded_key` guard), updated `cmd_record_context` |
| `tests/test_workflow.py` | modified | `git diff` | Added `TestBranchFinishDecisionBlockReconciliation` with 7 behavioral tests |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | modified | `git diff` | Canonical template sync from live runtime |
| `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | modified | `git diff` | Distributed copy sync |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | modified | `git diff` | Distributed copy sync |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | modified | `git diff` | Distributed copy sync |
| `openspec/changes/repair-workflow-decision-block-unlock/tasks.md` | untracked | `git ls-files --others` | OpenSpec change tasks file with all checkboxes checked |
| `openspec/changes/repair-workflow-decision-block-unlock/proposal.md` | untracked | `git ls-files --others` | OpenSpec change proposal |
| `openspec/changes/repair-workflow-decision-block-unlock/design.md` | untracked | `git ls-files --others` | OpenSpec change design |
| `openspec/changes/repair-workflow-decision-block-unlock/specs/sdlc-workflow-engine/spec.md` | untracked | `git ls-files --others` | OpenSpec delta spec |
| `openspec/changes/repair-workflow-decision-block-unlock/.openspec.yaml` | untracked | `git ls-files --others` | OpenSpec change metadata |
| `.ai/workflows/runs/active/2026-07-11-repair-workflow-decision-block-unlock/run.json` | untracked | `git ls-files --others` | Active workflow run state |
| `.ai/workflows/runs/active/2026-07-11-repair-workflow-decision-block-unlock/.migrated` | untracked | `git ls-files --others` | Migration sentinel |
| `.ai/workflows/runs/active/2026-07-11-repair-workflow-decision-block-unlock/handoffs/default/implement-agent.md` | untracked | `git ls-files --others` | This handoff artifact |
| `.ai/workflows/runs/active/2026-07-11-repair-workflow-decision-block-unlock/handoffs/default/plan-agent.md` | untracked | `git ls-files --others` | Plan-agent handoff |
| `.ai/workflows/runs/active/2026-07-11-repair-workflow-decision-block-unlock/handoffs/default/review-agent.md` | untracked | `git ls-files --others` | Review-agent handoff |
| `.ai/workflows/runs/active/2026-07-11-repair-workflow-decision-block-unlock/handoffs/default/history/*.md` | untracked | `git ls-files --others` | Handoff history copies |

### Changes Attributable To Derived-Artifact Repair (agent drift closure during this work)

| File | Status | Source | Reason |
|------|--------|--------|--------|
| `agents/dev-orchestrator.md` | modified | `git diff` | Canonical agent — pre-existing permission drift repaired by `setup_agents.py` |
| `.opencode/agents/dev-orchestrator.md` | modified | `git diff` | Distributed agent copy — synced via `setup_agents.py` |
| `.opencode/agents/.agent-install.json` | modified | `git diff` | Agent install manifest — updated by `setup_agents.py` |
| `.claude/agents/dev-orchestrator.md` | modified | `git diff` | Distributed agent copy — synced via `setup_agents.py` |
| `.claude/agents/.agent-install.json` | modified | `git diff` | Agent install manifest — updated by `setup_agents.py` |
| `.cursor/agents/dev-orchestrator.md` | modified | `git diff` | Distributed agent copy — synced via `setup_agents.py` |
| `.cursor/agents/.agent-install.json` | modified | `git diff` | Agent install manifest — updated by `setup_agents.py` |

### Unrelated Pre-Existing Changes (NOT attributable to this work)

| File | Status | Reason |
|------|--------|--------|
| `.ai/roadmap/areas/workflow.sdlc-orchestrator/items/RM-ORCH-009-workflow-runtime-modularization.md` | modified | Pre-existing roadmap state from prior run |
| `.ai/roadmap/areas/workflow.sdlc-orchestrator/revisions/changelog.md` | modified | Pre-existing roadmap changelog from prior run |
| `.ai/roadmap/index.json` | modified | Pre-existing roadmap index from prior run |
| `.ai/workflows/runs/current.json` | modified | Workflow pointer updated by active run lifecycle |
| `.ai/workflows/runs/active/2026-07-11-RM-ORCH-009/run.json` | untracked | Prior unrelated workflow run |
| `.ai/workflows/runs/active/2026-07-11-RM-ORCH-009/.migrated` | untracked | Prior unrelated run migration sentinel |

## Commands Run

| Command | Result |
|---------|--------|
| `python3 -m pytest tests/test_workflow.py -v -k "test_unrelated_context_key_does_not_clear_branch_decision_block"` (RED) | 1 failed |
| Same command (GREEN) | 1 passed |
| `python3 -m pytest tests/test_workflow.py -v -k "corrected_valid_branch_finish_decision or invalid_branch_finish_decision_correction or valid_branch_finish_decision_preserves_unrelated_block or branch_finish_decision_does_not_unblock or unrelated_context_key_does_not_clear"` | 7 passed |
| `python3 -m pytest tests/test_workflow.py -v` (full suite) | 322 passed, 25 subtests passed |
| `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .` | SYNCED |
| `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute` | DISTRIBUTED |
| `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` | OK |
| `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed` | OK |
| `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git` | OK: all 6 check suites in sync |
| `openspec instructions apply --change repair-workflow-decision-block-unlock --json` | state: all_done, 17/17 complete |
| `git diff --check` | no errors |

## Evidence Summary

- **tasks_complete:** true — all 17 tasks complete
- **tdd_passed:** true — RED phase confirmed for both original tests and review-blocker regression
- **focused_tests:** 7/7 pass
- **full_regression:** 322/322 pass, 25 subtests pass
- **template_sync:** canonical and distributed copies in sync
- **derived_artifacts:** all 6 check suites in sync
- **provider_verification:** openspec.apply state=all_done, 17/17 complete

## Issues

- Pre-existing agent drift in `agents/dev-orchestrator.md` (permission entries for `provider_verifiers.py` and `result_contracts.py`) was repaired during this work via `setup_agents.py` to satisfy the derived-artifact check. These agent changes are included in the change-set as derived-artifact repair.
- Pre-existing roadmap state changes (`.ai/roadmap/`, `.ai/workflows/runs/current.json`, prior run artifacts) are NOT attributable to this work and are clearly distinguished above.

## Learnings

- The review correctly identified that `_should_reconcile_branch_decision_block` was key-agnostic: it only inspected the tentative context, not the recorded key. Adding `recorded_key` as a first-class parameter fixed the spurious-unblock path. The TDD regression test proved the bug existed before the fix and is now covered.
- Live Git change-set discovery must be performed after all sync/repair commands to capture the full review scope, including derived-artifact repair.

## Suggestions

- Add a runtime-owned block `reason` or `gate_id` field for more precise identification rather than relying on `next_allowed` containing `ask_user_branch_finish_decision`.
- Generate `artifacts.changed_files` from `git status --porcelain -uall` rather than maintaining it manually.

## Risks/Follow-Ups

- None. The repair is narrow, preserves unrelated blocks, restricts reconciliation to `branch_finish_decision` key writes only, and all 322 tests pass.

## Raw Logs

- Focused test output (RED and GREEN) captured inline in Commands Run section.
- Full suite output: 322 passed, 25 subtests passed.