# Implement Agent Handoff

## Metadata

- **Run ID**: 2026-07-05-lifecycle-hardening-and-derived-sync
- **Slice ID**: default
- **Agent**: implement-agent
- **Phase**: apply_change
- **Flow Type**: lightweight-flow
- **Status**: success

## Objective

Execute the approved lightweight-flow plan at `docs/superpowers/plans/2026-07-04-lifecycle-harden-and-derived-sync.md` task-by-task: harden review-agent permission ordering, add repository-scoped safe deletion, add an aggregate derived-artifact sync entrypoint, move derived-drift ownership to finish-agent, validate handoff metadata before history-copy preservation, and run final regression.

## Work Completed

All 6 tasks complete. TDD red/green loop followed for every behavior-changing change (failing test written and confirmed first, then minimal implementation, then green confirmation). Plan checkboxes synced to reflect actual progress; `scripts/check_plan_checkboxes.py` exits 0.

### Task 1 — Permission-contract ordering lock
Added `TestReviewAgentBashPermissionOrdering` to `tests/test_wrapper_contracts.py` locking the deny-first bash rule ordering (catch-all `"*": deny` first, specific allows after) for review/implement/finish agents across `.opencode`, `.claude`, `.cursor`. Existing frontmatter was already correctly ordered; no frontmatter changes were needed. Distributed-copy consistency verified via `setup_agents.py --check`.

### Task 2 — Repository-scoped safe deletion
Created `scripts/safe_delete.py` (repo-relative paths only; rejects absolute paths, path escapes, `.git/` and `.ai/memory/`; `--recursive` required for directories; JSON report with `deleted`/`skipped`/`refused`). Added 9 behavioral tests in `tests/test_safe_delete.py` (file delete, absolute-path refusal, protected-path refusal for `.git` and `.ai/memory`, path-escape refusal, missing-file skip, recursive-required guard, recursive directory delete, mixed batch). Added `python3 scripts/safe_delete.py *` allow-rule to implement-agent and finish-agent; re-distributed to all project-level targets.

### Task 3 — Aggregate derived-artifact sync entrypoint
Created `scripts/sync_derived_artifacts.py` with `--check` / `--fix` / `--json` modes. `--check` composes `sync_templates.py --check`, `sync_templates.py --check-distributed`, `setup_agents.py --check` for all three targets, and `check_skill_distribution.py`. `--fix` composes `sync_templates.py` sync + distribute, `setup_agents.py --force` for all three targets, and `install_skill.py` for every canonical skill to `.opencode/`, `.claude/`, `.cursor/`. Added 5 behavioral tests in `tests/test_sync_derived_artifacts.py` using subprocess mocking to assert command composition, failure propagation, and JSON report structure.

### Task 4 — Derived drift ownership moved to finish
Added `TestDerivedDriftBoundaryAndAggregateEntrypoint` (5 failing tests first). Updated canonical `agents/implement-agent.md` ("Do not treat distributed-copy drift as a default apply-change blocker"), `agents/review-agent.md` ("derived drift as a finish follow-up"), `agents/finish-agent.md` (new "Derived Artifact Sync" section with `sync_derived_artifacts.py --check`/`--fix`). Added a top-level "Derived Artifact Sync" section to `AGENTS.md` as the primary entrypoint, demoting the scattered lower-level commands to escape hatches. Re-distributed agents to all project-level targets.

### Task 5 — Handoff metadata validation before history copy
Added `TestApplyChangeHandoffMetadataValidation` (3 tests: phase mismatch blocks, agent mismatch blocks, valid metadata still writes history copy). Implemented `_read_handoff_metadata(path)` and `_handoff_metadata_mismatch_blocker(metadata, expected)` helpers in `workflow.py`. Before `_write_handoff_history_copy`, the runtime now parses the handoff `## Metadata` block and compares Agent/Phase/Slice ID/Flow Type against the active run context; on mismatch it appends a `handoff_metadata_mismatch` blocker and skips the history copy. Synced live workflow → canonical template → all distributed template copies.

### Task 6 — Final regression and derived sync
Focused regression: 477 tests pass (test_wrapper_contracts, test_safe_delete, test_sync_derived_artifacts, test_sync_templates, test_sync_all_distributed, test_workflow). Ran `sync_derived_artifacts.py --fix` (80 fix suites) then `--check --json` (6 suites, all OK). Broader regression: precommit_hook, install_agents, setup_agents — 31 tests pass. Full repository regression: **989 tests pass, 49 subtests pass, 0 failures**.

## Files/Artifacts Changed

### Created
- `scripts/safe_delete.py`
- `scripts/sync_derived_artifacts.py`
- `tests/test_safe_delete.py`
- `tests/test_sync_derived_artifacts.py`

### Modified (canonical source)
- `agents/implement-agent.md` (safe_delete allow-rule + drift-not-default-blocker line)
- `agents/review-agent.md` (derived-drift-as-finish-followup line)
- `agents/finish-agent.md` (safe_delete allow-rule + Derived Artifact Sync section)
- `AGENTS.md` (new top-level Derived Artifact Sync section as primary entrypoint)
- `.ai/workflows/scripts/workflow.py` (`_read_handoff_metadata`, `_handoff_metadata_mismatch_blocker`, history-copy gating)
- `tests/test_wrapper_contracts.py` (2 new test classes: permission ordering, derived drift boundary)
- `tests/test_workflow.py` (new `TestApplyChangeHandoffMetadataValidation` class)
- `docs/superpowers/plans/2026-07-04-lifecycle-hardening-and-derived-sync.md` (all checkboxes checked)

### Synced derived copies
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` (canonical template synced from live)
- `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.opencode/agents/*.md`, `.claude/agents/*.md`, `.cursor/agents/*.md` (re-activated)
- `.opencode/skills/*`, `.claude/skills/*`, `.cursor/skills/*` (re-installed via aggregate --fix)

## Commands Run

| Command | Result |
|---|---|
| `python3 -m pytest tests/test_wrapper_contracts.py -k "review_agent_bash or implement_agent_bash_catch or finish_agent_bash_catch" -v` | pass (5) |
| `python3 scripts/setup_agents.py --target ./.opencode/agents --check` (and .claude, .cursor) | pass |
| `python3 -m pytest tests/test_safe_delete.py -v` | pass (9) |
| `python3 -m pytest tests/test_safe_delete.py tests/test_wrapper_contracts.py -k "safe_delete or finish_agent or implement_agent" -v` | pass (28) |
| `python3 -m pytest tests/test_sync_derived_artifacts.py -v` | pass (5) |
| `python3 -m pytest tests/test_sync_derived_artifacts.py tests/test_sync_templates.py -v` | pass (22) |
| `python3 -m pytest tests/test_wrapper_contracts.py -k "sync_derived_artifacts or distributed_drift or finish_agent or implement_agent or review_agent" -v` | pass (34) |
| `python3 -m pytest tests/test_wrapper_contracts.py -k "agents_md or DerivedDriftBoundary" -v` | pass (5) |
| `python3 -m pytest tests/test_workflow.py -k "handoff_metadata or history_copy" -v` | pass (4) |
| `python3 -m pytest tests/test_sync_all_distributed.py tests/test_sync_templates.py -v` | pass (18) |
| `python3 -m pytest tests/test_wrapper_contracts.py tests/test_safe_delete.py tests/test_sync_derived_artifacts.py tests/test_sync_templates.py tests/test_sync_all_distributed.py tests/test_workflow.py -v` | pass (477) |
| `python3 scripts/sync_derived_artifacts.py --fix` | OK: all 80 fix suites in sync |
| `python3 scripts/sync_derived_artifacts.py --check --json` | status=ok, 6 suites, returncode=0 |
| `python3 -m pytest tests/test_precommit_hook.py tests/test_install_agents.py tests/test_setup_agents.py -v` | pass (31) |
| `python3 -m pytest tests/ -v` | pass (989, 49 subtests) |
| `python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-04-lifecycle-hardening-and-derived-sync.md` | ok: all checkboxes complete |

## Evidence Summary

- `tasks_complete`: true — all 6 plan tasks done, all checkboxes synced.
- `tdd_passed`: true — every behavior change followed red/green: failing test written and confirmed first, then minimal implementation, then green. Red phases captured: safe_delete (9 tests failed before script existed), sync_derived_artifacts (5 tests failed before script existed), derived-drift boundary (4 prompt-contract tests failed before prompt edits), handoff metadata (2 mismatch tests failed before workflow.py change).
- `focused_tests`: all green (see Commands Run).
- Derived state: `sync_derived_artifacts.py --check --json` reports `status=ok` across all 6 suites.

## Issues

- One test (`test_safe_delete_rejects_absolute_path`) initially over-asserted `assertFalse(os.path.exists(target))` for a refused path; the file should still exist after refusal. Fixed the assertion to `assertTrue` before claiming green. No production-code change was needed — the script correctly refused to delete.
- The handoff-metadata mismatch tests initially asserted on `data["status"] == "blocked"`. The `after-dispatch` transition's `status` field is the raw `agent_status` ("success"), while the workflow block state is reflected in `workflow_command`/`workflow_args`/`blockers`. Corrected the assertions to check `workflow_command == "workflow.py block"`, `block_type == "worker_failed"`, and the `handoff_metadata_mismatch` reason in `blockers` — matching the established contract used by other `after-dispatch` blocked tests. No production-code change was needed.
- The first handoff-metadata-mismatch test run revealed the runtime was already blocking on `missing_verification_basis` (no prior implement-agent evidence). Added prior implement-agent evidence to the test fixtures so the metadata mismatch became the sole blocker, isolating the new behavior.

## Learnings

- The `after-dispatch` transition dict distinguishes raw agent status from workflow block state. New tests for blocked dispatch outcomes should assert on `workflow_command`/`workflow_args`/`blockers`, not on the top-level `status` field. This is consistent with every existing `after-dispatch` blocked test.
- Handoff metadata validation must tolerate missing metadata fields (e.g., handoffs without a `## Metadata` block) and only block on present-but-mismatched fields. The existing `test_after_dispatch_writes_review_handoff_history_copy` test uses a handoff with only a `## Status` section and still expects a history copy — that test continued to pass because missing fields are tolerated.
- The `sync_derived_artifacts.py` test pattern of importing the module via `importlib.util.spec_from_file_location` and mocking `subprocess.run` works cleanly and avoids needing real child scripts in the test environment.

## Suggestions

- Consider documenting the `after-dispatch` transition contract (raw `status` vs `workflow_command`/`workflow_args`/`blockers`) explicitly in the workflow runtime constraints AGENTS.md. New tests repeatedly get this wrong.
- The aggregate `sync_derived_artifacts.py --fix` re-installs every canonical skill (80 suites) on every run. A future optimization could scope skill re-install to changed skills only when used outside the finish flow, as raised in the spec's Review Question 2.
- The handoff metadata parser currently only inspects the structured `## Metadata` section. Review Question 4 asks whether to also guard against misleading top-level titles when they conflict with metadata — left as a follow-up.

## Assumptions

- Per the implement-agent dispatch contract and the executing-plans skill, plan steps that say "commit" are deferred to finish-agent at archive phase. No intermediate git commits were made during this apply_change dispatch; the working tree contains the full change set ready for finish-agent to commit/push. The plan's per-task "commit" steps were treated as checkpoint markers, and the plan checkboxes were checked to reflect that the work those steps describe is complete.
- Work was performed directly on `main` because this was a dispatched apply_change subagent invocation (no worktree isolation requested by the orchestrator). The full change set is present in the working tree.

## Risks/Follow-Ups

- The handoff metadata validation only checks Agent/Phase/Slice ID/Flow Type. Run ID is parsed but not currently compared (the handoff path itself encodes the run id). If cross-run handoff contamination becomes a risk, extend `_handoff_metadata_mismatch_blocker` to compare Run ID against `state["run_id"]`.
- `sync_derived_artifacts.py` does not yet support a `--skills <list>` scoping flag for partial re-install. This is acceptable for finish-phase closure (full sync) but could be optimized for other use cases.
- Raw `rm` is still technically available to agents that have broad bash allow-rules, but the canonical workflow path now routes through `safe_delete.py`. Review Question 3 asked whether to remove raw `rm` entirely — left as a policy decision.

## Raw Logs

Focused test outputs were captured inline in the Commands Run table above. No separate raw log files were retained because the test runs were observed directly in the session and all passed; no failures required log preservation for diagnosis.