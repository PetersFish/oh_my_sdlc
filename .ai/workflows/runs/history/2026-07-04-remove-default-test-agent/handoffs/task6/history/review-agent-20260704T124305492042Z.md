# Handoff: review-agent — Task 6

## Metadata

- **Run ID**: 2026-07-04-remove-default-test-agent
- **Slice ID**: task6
- **Agent**: review-agent
- **Phase**: apply_change
- **Flow Type**: lightweight-flow
- **Status**: blocked
- **Recommended Next Agent**: implement-agent

## Objective

Review current repository state for the remove-default-test-agent apply_change phase, including current diffs/results, legacy `sdlc-orchestrator` retirement, agent responsibility boundaries, verification evidence, and test quality.

## Work Completed

- Loaded repository memory for agents, SDLC skills, tests, and template/distribution decisions.
- Reviewed the primary plan and spec artifacts.
- Inspected active workflow dispatch code, wrapper contracts, agent prompts, and current workflow state.
- Ran verification checks:
  - `python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-04-remove-default-test-agent.md` — pass.
  - `python3 scripts/setup_agents.py --target ./.opencode/agents --check` — pass.
  - `python3 -m pytest tests/test_workflow.py -v` — pass, 246 tests.
  - `python3 -m pytest tests/test_wrapper_contracts.py -v` — pass, 187 tests.

## Files / Artifacts Changed

- No source, test, prompt, config, or user documentation files were modified by review-agent.
- Wrote this review handoff artifact only.

## Commands Run

```bash
git status --short --branch
git diff --stat
git log --oneline -10
python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-04-remove-default-test-agent.md
python3 scripts/setup_agents.py --target ./.opencode/agents --check
python3 -m pytest tests/test_workflow.py -v
python3 -m pytest tests/test_wrapper_contracts.py -v
```

## Evidence Summary

- Plan checkbox sync is complete.
- Agent distribution activation check passes.
- The legacy `sdlc-orchestrator` skill directories and `skill.sdlc-orchestrator` EvalOps target are absent in current repo state.
- Active `agents/*test-agent*` and distributed agent `test-agent.md` files are absent.
- Targeted pytest commands pass, but the green test suite still encodes stale default `test-agent` workflow behavior.

## Issues

1. **Active workflow runtime still routes through `test-agent`.**
   - `.ai/workflows/scripts/workflow.py` still accepts `test-agent`/`test_agent`, includes `dispatch_test_agent`, allows `test-agent` in `apply_change`, recommends `dispatch_test_agent` after `implement-agent` success, and requires prior successful `test-agent` evidence before accepting `eval_passed_or_human_decision_recorded`.
   - The same stale dispatch map remains in `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` and distributed workflow templates under `.opencode/`, `.claude/`, and `.cursor/`.
2. **Tests still assert stale behavior.**
   - `tests/test_workflow.py` includes passing tests such as `test_after_dispatch_test_agent_success_recommends_review`, `test_after_dispatch_review_acceptance_can_finalize_eval_key_from_test_agent_success`, and test-agent handoff-history cases.
   - These tests are executable behavior tests and currently protect the old default runtime path.
3. **Review pre-check skill availability gap.**
   - Required review skills `requesting-code-review`, `receiving-code-review`, and `verification-before-completion` were not available in this runtime’s skill registry. Review proceeded only far enough to diagnose executable blockers.

## Learnings

- The legacy `sdlc-orchestrator` retirement appears complete in current state, but the earlier `test-agent` default was only removed from agent prompt/docs and wrapper-contract library, not from the live workflow runtime/template implementation.
- Passing tests are not sufficient here because the workflow tests still encode `test-agent` as the expected bridge from implementation to review.
- `skills/_lib/wrapper_contracts.py` has the desired phase-agent mapping, but `.ai/workflows/scripts/workflow.py` and bootstrap workflow templates did not receive the equivalent change.

## Suggestions

- Update `.ai/workflows/scripts/workflow.py` and all workflow templates so `implement-agent` success recommends `dispatch_review_agent`, review acceptance can use implement-agent verification evidence, and `test-agent` is not accepted as an `apply_change` lifecycle worker.
- Sync workflow templates after live workflow changes using the repository’s template-sync procedure.
- Rewrite workflow tests to assert the new executable behavior and add guards that fail if `test-agent` appears in active dispatch maps or canonical runtime agent names.
- Remove stale test-agent workflow round-trip tests or explicitly move them behind a future non-default independent verification wrapper contract.

## Blockers

- Active workflow dispatch still requires and routes through `test-agent`, so apply_change acceptance cannot be approved.

## Assumptions

- Historical/archive references are intentionally out of scope.
- Optional independent verification is allowed only as a future non-default wrapper, not as an active phase worker named `test-agent`.

## Risks / Follow-Ups

- If only prompt/docs are updated, `workflow.py after-dispatch` will continue returning `dispatch_test_agent` after implementation and block review acceptance without prior test-agent evidence.
- Generated project workflow templates would reintroduce the stale lifecycle unless synced after fixing the live runtime.

## Raw Logs

- No separate raw log files were written.
