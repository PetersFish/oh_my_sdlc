# Implement-Agent Handoff (Remediation Pass)

## Metadata

- **agent:** implement-agent
- **phase:** apply_change
- **slice_id:** remove-superpowers-direct-dead-code
- **flow_type:** lightweight-flow
- **workflow_run_id:** 2026-07-12-remove-superpowers-direct-dead-code
- **execution_mode:** main_checkout
- **worktree_path:** /Users/yuping/Documents/workspace/oh_my_skills
- **repo_root:** /Users/yuping/Documents/workspace/oh_my_skills
- **base_branch:** main
- **parent_ref:** 40b4f9f351b606a5387d9ddeb432fccc3573e899

## Objective

Apply the approved remediation from review-agent: remove the live
`superpowers-direct` Plan Mode handoff scenario from
`openspec/specs/sdlc-orchestrator/spec.md` so the canonical live
specification no longer advertises the retired route. The prior
implement-agent pass completed the runtime/code/test/derived-artifact
removal (commit 5f3afe3) but left this live spec scenario in place,
which contradicted the plan's Task 9 Step 1 stop condition.

## Work Completed

- Deleted the `#### Scenario: Direct flow handoff may name direct
  execution` block (formerly lines 183-185 plus its trailing blank line)
  from `openspec/specs/sdlc-orchestrator/spec.md`. The `Plan Mode
  Handoff Compliance` requirement now lists only the two `spec-driven-*`
  scenarios.
- Confirmed via repo-wide grep that no live references to
  `superpowers-direct`, `superpowers_direct`, or `_policy_no_workflow`
  remain outside the Task 9 allowlist (history, memory, sync-history,
  archived OpenSpec changes).
- Ran targeted verification on `tests/test_wrapper_contracts.py` (the
  suite that asserts dev-orchestrator doc content and wrapper
  contracts): 288 tests, 2 subtests passed, 0 failures.
- Ran full regression on `tests/`: 1201 tests, 49 subtests passed, 0
  failures.

## Files/Artifacts Changed

| Path | Status | Source | Reason | Covered By |
|---|---|---|---|---|
| `openspec/specs/sdlc-orchestrator/spec.md` | modified | `git diff -- openspec/specs/sdlc-orchestrator/spec.md` | Remove live spec scenario advertising the retired `superpowers-direct` route | `python3 -m pytest tests/test_wrapper_contracts.py -v` and `python3 -m pytest tests/ -v` |

Notes:
- `.ai/workflows/runs/current.json` and the untracked
  `.ai/workflows/runs/active/...` tree are workflow-managed run/handoff
  artifacts, not implementation change-set files.
- `docs/superpowers/plans/2026-07-12-remove-superpowers-direct-dead-code.md`
  shows modified from the prior implement-agent pass (checkbox sync);
  no checkbox changes were made in this remediation pass because the
  plan's tasks were already complete and this remediation addresses a
  Task 9 Step 1 stop condition, not a new plan step.

## Commands Run

| Command | Result |
|---|---|
| `git diff -- openspec/specs/sdlc-orchestrator/spec.md` | 4 lines deleted, 0 inserted |
| `grep -rn` (via Grep tool) for `superpowers-direct\|superpowers_direct\|_policy_no_workflow` across `openspec/specs`, `openspec/changes`, `tests`, `skills`, `.opencode/skills`, `.claude/skills`, `.cursor/skills`, `.ai/workflows/scripts`, `agents` | only allowlisted matches in `openspec/changes/archive/` remain |
| `python3 -m pytest tests/test_wrapper_contracts.py -v` | 288 passed, 2 subtests passed, 0 failures |
| `python3 -m pytest tests/ -v` | 1201 passed, 49 subtests passed, 0 failures |

## Evidence Summary

- **tasks_complete:** true — the approved remediation is applied and verified.
- **tdd_passed:** true — this is a surgical spec-doc cleanup with no new behavior; verification is regression-based per the tests/AGENTS.md guidance (string-presence assertions are acceptable for static spec docs).
- **verification_summary.status:** pass — full regression green with no accepted pre-existing failures.
- **focused_tests:** `python3 -m pytest tests/test_wrapper_contracts.py -v` → pass (covers dev-orchestrator doc and wrapper contract assertions most likely to be affected by a spec-doc change).
- **full_regression:** `python3 -m pytest tests/ -v` → 1201 passed, 49 subtests passed, 0 failures.

## Issues

- None. The remediation was a 4-line surgical deletion with no test
  fallout and no derived-artifact propagation needed (OpenSpec live
  specs under `openspec/specs/` are canonical source, not distributed
  artifacts synced by `sync_derived_artifacts.py`).

## Learnings

- The prior implement-agent pass correctly identified the spec drift
  but misclassified it as a non-blocking follow-up. The review-agent
  correctly enforced the plan's explicit Task 9 Step 1 stop condition:
  any non-allowlisted remaining reference must be cleaned before
  completion. Lesson: when a plan has an explicit repo-wide cleanup
  stop condition, the implement-agent must treat every match outside
  the allowlist as in-scope, not as a follow-up, regardless of whether
  the match is code or documentation.
- OpenSpec live specs under `openspec/specs/` are canonical source
  files, not derived artifacts. The `sync_derived_artifacts.py` pipeline
  does not touch them, so no `--fix --changed-files-from-git` run was
  needed for this change.

## Suggestions

- Future removal plans should include `openspec/specs/**/spec.md` in
  the initial semantic-reference audit (Task 9 Step 1 grep targets)
  so that live spec scenarios are caught in the same pass as code,
  agents, tests, and derived templates, rather than surfaced by
  review-agent after implementation.
- Consider adding a `tests/` assertion that the live
  `openspec/specs/sdlc-orchestrator/spec.md` does not reference
  `superpowers-direct`, to lock in the cleanup and catch future drift.
  (Not added here to keep this remediation surgical; recommend as a
  separate follow-up.)

## Blockers

None.

## Assumptions

- The approved remediation is limited to removing the live spec
  scenario; no code, test, or derived-artifact changes are required
  because the runtime removal was completed in the prior pass.
- Archive references under `openspec/changes/archive/` remain
  allowlisted per Task 9 Step 1 and are intentionally left untouched.
- No commit is performed by implement-agent; staging/commit is owned
  by the workflow runtime (`final-commit`) or a later phase.

## Risks/Follow-Ups

- A follow-up test assertion locking the live spec clean could prevent
  future drift. See Suggestions.
- If a future change re-introduces a direct-execution route, the
  `Plan Mode Handoff Compliance` requirement may need a new scenario;
  this remediation simply removes the retired scenario.

## Raw Logs

No separate raw log files were written for this remediation pass; the
full regression output was captured inline in the tool-output buffer.
The commands and results are recorded in the Commands Run table above.