# Implement-Agent Handoff — Roadmap-Agent Primary Subject Gating

## Metadata

- **workflow_run_id:** 2026-07-05-roadmap-agent-primary-subject-gating
- **phase:** apply_change
- **slice_id:** default
- **flow_type:** lightweight-flow
- **agent:** implement-agent
- **base_ref:** 0533720 (HEAD of main)
- **worktree_path:** /Users/yuping/Documents/workspace/oh_my_skills (main checkout, no worktree)

## Objective

Implement the spec/plan at `docs/superpowers/plans/2026-07-05-roadmap-agent-primary-subject-gating.md`: prevent `roadmap-agent` from being dispatched and prevent roadmap lifecycle hooks from being enqueued unless the active workflow run has `primary_subject.type == "roadmap_item"`.

## Work Completed

All 6 plan tasks completed via TDD red/green loop:

1. **Task 1 — Runtime helpers:** Added `_roadmap_agent_enabled(state)` and `_is_roadmap_hook(hook)` to `.ai/workflows/scripts/workflow.py`.
2. **Task 2 — Hook filtering:** Added `TestRoadmapHookFiltering` (4 tests) covering `spec_change` runs (skip roadmap hooks on create/apply/archive phases) and `roadmap_item` runs (preserve roadmap hooks). Implemented the filter in `cmd_complete_phase` post-hook enqueue loop. Updated pre-existing `test_complete_phase_registers_hooks` to reflect the new gating behavior.
3. **Task 3 — Dispatch gate:** Added `test_before_dispatch_blocks_roadmap_agent_for_spec_change_run` and `test_before_dispatch_allows_roadmap_agent_for_roadmap_item_run`. Implemented the `roadmap_not_enabled` blocker in `cmd_before_dispatch`. Updated pre-existing `TestRoadmapAgentRouting._make_apply_run_with_roadmap` to default to `roadmap_item` subject type (the two "accepted" tests now exercise the allowed path). Updated `test_roadmap_hook_block_round_trip_routes_back_to_roadmap_agent` to use `roadmap_item` subject type, since the round-trip scenario is a roadmap-governed flow.
4. **Task 4 — dev-orchestrator prompt:** Added primary-subject gating rule to the Roadmap-Governed Hook Dispatch section and the review_roadmap clarification. Added `test_dev_orchestrator_documents_primary_subject_roadmap_gating` to `test_wrapper_contracts.py`.
5. **Task 5 — Sync distributed copies:** Ran `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git`. Synced `workflow.py` template copies and `dev-orchestrator.md` agent copies across `.opencode/`, `.claude/`, `.cursor/`, and `skills/sdlc-project-bootstrap/templates/workflow/`.
6. **Task 6 — Verification:** Focused roadmap tests (60 passed), workflow tests (254 passed), contract tests (244 passed), full suite (1056 passed).

Plan checkboxes synced; `python3 scripts/check_plan_checkboxes.py <plan_path>` returns `ok: all checkboxes complete`.

## Files/Artifacts Changed

Canonical implementation:
- `.ai/workflows/scripts/workflow.py` — added `_roadmap_agent_enabled`, `_is_roadmap_hook`, post-hook filter, `cmd_before_dispatch` roadmap-agent gate.
- `agents/dev-orchestrator.md` — documented primary-subject gating rule and review_roadmap clarification.
- `tests/test_workflow.py` — added `TestRoadmapHookFiltering` (4 tests), 2 new dispatch gate tests, updated 3 pre-existing tests to align with gating.
- `tests/test_wrapper_contracts.py` — added `test_dev_orchestrator_documents_primary_subject_roadmap_gating`.
- `docs/superpowers/plans/2026-07-05-roadmap-agent-primary-subject-gating.md` — all plan checkboxes checked off.

Distributed copies (synced via `sync_derived_artifacts.py --fix`):
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.opencode/agents/dev-orchestrator.md`
- `.claude/agents/dev-orchestrator.md`
- `.cursor/agents/dev-orchestrator.md`
- `.opencode/agents/.agent-install.json`
- `.claude/agents/.agent-install.json`
- `.cursor/agents/.agent-install.json`

Pre-existing incidental change (not from this work):
- `.ai/workflows/runs/current.json` — was already modified before dispatch.

## Commands Run

- `python3 -m pytest tests/test_workflow.py -k "RoadmapHookFiltering" -v` → 4 passed (after implementation)
- `python3 -m pytest tests/test_workflow.py -k "before_dispatch_blocks_roadmap_agent_for_spec_change or before_dispatch_allows_roadmap_agent_for_roadmap_item" -v` → 2 passed
- `python3 -m pytest tests/test_workflow.py -k "roadmap_agent or roadmap_hook or roadmap" -v` → 60 passed
- `python3 -m pytest tests/test_workflow.py --tb=short -q` → 254 passed
- `python3 -m pytest tests/test_wrapper_contracts.py -v` → 244 passed
- `python3 -m pytest tests/ --tb=short -q` → 1056 passed (full regression)
- `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git` → OK (after fix)
- `python3 scripts/check_plan_checkboxes.py <plan_path>` → ok: all checkboxes complete

## Evidence Summary

- **tasks_complete:** true — all 6 plan tasks completed.
- **tdd_passed:** true — every behavior change started with a failing test (3 hook-filtering tests, 1 dispatch-block test), then went green after implementation.
- **focused_tests:** all green (see Commands Run).
- **full_regression:** 1056 passed, 0 failed.
- **acceptance criteria:** all 8 criteria from the spec verified by the test suite:
  1. `spec_change` runs no longer enqueue roadmap hooks — `TestRoadmapHookFiltering` (3 tests).
  2. `spec_change` runs cannot dispatch roadmap-agent — `test_before_dispatch_blocks_roadmap_agent_for_spec_change_run`.
  3. `roadmap_item` runs can still dispatch roadmap-agent — `test_before_dispatch_allows_roadmap_agent_for_roadmap_item_run` + existing `TestRoadmapAgentRouting` accepted tests.
  4. `review_roadmap` still works — `test_review_roadmap_routes_through_dev_orchestrator` + `test_roadmap_agent_allowed_in_review_roadmap`.
  5. `memory_sync` not affected — `test_spec_change_run_does_not_enqueue_roadmap_hooks_on_archive_change` asserts `memory_sync` still enqueued.
  6. Existing non-roadmap tests still pass — 254 workflow tests green.
  7. Existing roadmap tests still pass — 60 roadmap-focused tests green.
  8. No new run.json top-level schema field introduced — only `primary_subject.type` (existing field) used.

## Blockers

None.

## Assumptions

- The pre-existing `TestRoadmapAgentRouting` tests that used `spec_change` with a linked roadmap item were exercising a scenario that the spec explicitly classifies as invalid (roadmap-agent dispatched for non-roadmap runs). They were updated to use `roadmap_item` subject type to exercise the allowed path, preserving their original intent (proving roadmap-agent works through lifecycle dispatch).
- `test_roadmap_hook_block_round_trip_routes_back_to_roadmap_agent` was updated to use `roadmap_item` subject type because the roadmap hook block round-trip is a roadmap-governed flow by definition.
- No git worktree was created; implementation was done in the main checkout per the dispatch context.

## Risks/Follow-Ups

- None identified. The gating is intentionally minimal and uses the existing `primary_subject.type` field as the single source of truth.

## Issues

None encountered during implementation.

## Learnings

- The existing test suite had three tests that implicitly assumed `spec_change` runs could dispatch `roadmap-agent` (pre-gating behavior). The plan did not explicitly call these out, but they were straightforward to migrate to `roadmap_item` subject type since their scenarios were roadmap-governed by intent.

## Suggestions

- Future specs that change gating behavior should enumerate existing tests that contradict the new behavior, so the implementer knows upfront which tests need migration vs. which are pure additions.

## Raw Logs

No separate raw log files retained; all test output was captured inline via pytest stdout and is summarized in Commands Run.