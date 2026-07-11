# Implement-Agent Handoff

## Metadata

- Run ID: 2026-07-08-worktree-verification-hygiene-and-derived-artifact-dry-run
- Slice ID: default
- Agent: implement-agent
- Phase: apply_change
- Flow Type: lightweight-flow
- Status: success
- Recommended Next Agent: dispatch_review_agent

## Objective

Implement the worktree verification hygiene and derived artifact dry-run plan:
- Add `--dry-run` non-mutating mode to `sync_derived_artifacts.py`
- Add worktree hydration script for required runtime fixture directories
- Standardize verification summary evidence schema
- Add producer-owned cleanup guidance and constrained git restore boundary
- Sync derived agent copies
- Full verification

## Work Completed

All 8 tasks from the plan completed:

1. **Failing tests added** — 27 new tests across `test_sync_derived_artifacts.py` and `test_wrapper_contracts.py` covering dry-run behavior, CLI acceptance, prompt contracts, and hydration.
2. **`--dry-run` implemented** — `run_aggregate()` accepts `dry_run=True`, skips subprocess execution, reports `planned_suites`, `skipped_writes: true`, and `dry_run: true`. CLI `--dry-run` flag added.
3. **Hydration script created** — `.ai/workflows/scripts/hydrate_workspace.py` discovers eval target manifests and creates required `cases/inbox`, `cases/accepted`, `cases/rejected` directories. Idempotent, does not create workflow run state.
4. **Verification summary schema documented** — implement-agent prompt now documents `verification_summary.status` values (`pass`, `fail`, `pass_with_accepted_preexisting_failures`) with required evidence fields.
5. **Producer-owned cleanup guidance added** — implement-agent prompt states cleanup contract at unit test, smoke test, and agent levels. Constrained `git restore -- <known-safe-derived-path>` documented.
6. **Derived agent copies synced** — `setup_agents.py --force` run for `.opencode/agents`, `.claude/agents`, `.cursor/agents`.
7. **Full verification** — 1094 passed, 1 pre-existing failure (`test_workspace_has_required_directories` — worktree lacks empty `cases/inbox`/`cases/rejected` dirs, solved by hydration script).
8. **Handoff and acceptance evidence** — This document.

## Files/Artifacts Changed

| File | Status | Reason |
|---|---|---|
| `scripts/sync_derived_artifacts.py` | modified | Added `--dry-run` mode, `dry_run` parameter to `run_aggregate()`, planned suites reporting, dry-run plain text printer |
| `tests/test_sync_derived_artifacts.py` | modified | Added `TestDryRunMode` class with 11 tests proving non-mutation, report fields, backward compat |
| `tests/test_wrapper_contracts.py` | modified | Added `TestWorktreeVerificationHygienePromptContracts` (11 tests), `TestSyncDerivedArtifactsDryRunCLI` (2 tests), `TestWorktreeHydrationScript` (5 tests) |
| `.ai/workflows/scripts/hydrate_workspace.py` | added | New idempotent hydration script for eval target fixture directories |
| `agents/implement-agent.md` | modified | Added Verification Summary Schema, Producer-Owned Cleanup, Constrained Restore, Workspace Hydration sections |
| `agents/review-agent.md` | modified | Added Verification Summary Acceptance section with hygiene evidence acceptance rules |
| `.opencode/agents/implement-agent.md` | modified | Distributed copy synced from canonical |
| `.opencode/agents/review-agent.md` | modified | Distributed copy synced from canonical |
| `.opencode/agents/.agent-install.json` | modified | Agent install metadata updated by setup_agents.py |
| `.claude/agents/implement-agent.md` | modified | Distributed copy synced from canonical |
| `.claude/agents/review-agent.md` | modified | Distributed copy synced from canonical |
| `.claude/agents/.agent-install.json` | modified | Agent install metadata updated by setup_agents.py |
| `.cursor/agents/implement-agent.md` | modified | Distributed copy synced from canonical |
| `.cursor/agents/review-agent.md` | modified | Distributed copy synced from canonical |
| `.cursor/agents/.agent-install.json` | modified | Agent install metadata updated by setup_agents.py |
| `docs/superpowers/plans/2026-07-05-worktree-verification-hygiene-and-derived-artifact-dry-run.md` | modified | Plan checkboxes synced to reflect completion |

## Commands Run

| Command | Result |
|---|---|
| `python3 -m pytest tests/test_sync_derived_artifacts.py -k "dry_run" -v` | pass (11/11) |
| `python3 -m pytest tests/test_wrapper_contracts.py -k "WorktreeVerificationHygiene" -v` | pass (11/11) |
| `python3 -m pytest tests/test_wrapper_contracts.py -k "DryRunCLI" -v` | pass (2/2) |
| `python3 -m pytest tests/test_wrapper_contracts.py -k "WorktreeHydration" -v` | pass (5/5) |
| `python3 -m pytest tests/ -v` | 1094 passed, 1 pre-existing failure |
| `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git` | OK: all 6 check suites in sync |
| `python3 scripts/check_plan_checkboxes.py <plan_path>` | ok: all checkboxes complete |

## Evidence Summary

- **tasks_complete**: true — all 8 plan tasks completed
- **tdd_passed**: true — all focused tests passed red→green
- **focused_tests**: 29 new tests, all passing
- **full_regression**: 1094 passed, 1 accepted pre-existing failure
- **verification_summary.status**: `pass_with_accepted_preexisting_failures`

### Accepted Pre-Existing Failure

- **test**: `tests/test_evalops_root.py::TestTargetWorkspace::test_workspace_has_required_directories`
- **reason**: worktree lacks generated evalops fixture dirs (`cases/inbox`, `cases/rejected` are empty directories not tracked by git)
- **confirmation**: passes on main checkout; passes after running `hydrate_workspace.py`
- **owner**: `environment_fixture`

## Blockers

None.

## Assumptions

- The `hydrate_workspace.py` script path `.ai/workflows/scripts/` is the correct location per the spec.
- The `--dry-run` mode does not need a separate `--plan` mode (explicitly out of scope per spec).
- Distributed agent copies are synced via `setup_agents.py --force` which is the established canonical path.

## Risks/Follow-Ups

- The hydration script could be integrated as a worktree creation hook in the future.
- The `--dry-run` mode could be extended to simulate subprocess return codes for more comprehensive smoke testing.
- The verification summary schema is documented in agent prompts but not yet enforced programmatically in the evidence envelope validator.

## Issues

- The pre-existing `test_workspace_has_required_directories` failure in worktrees is caused by empty directories not being tracked by git. This is exactly the problem the hydration script solves, but the test itself does not call the hydration script. A follow-up could integrate hydration into the test fixture setup or call hydration from the test directly.

## Learnings

- Git worktrees do not preserve empty directories. The `cases/inbox` and `cases/rejected` directories under evalops targets are empty in the clean state and thus missing from worktrees. The hydration script solves this by creating them on demand.
- The `--dry-run` implementation needed to handle the preflight check for missing canonical skill directories even in dry-run mode, since the preflight is a filesystem check (not a subprocess).

## Suggestions

- Consider adding `.ai/workflows/scripts/hydrate_workspace.py --root .` to worktree creation hooks in `using-git-worktrees` skill.
- Consider making the evalops test `test_workspace_has_required_directories` call `hydrate_workspace.py` in its setup to avoid the pre-existing failure in worktrees.
- Consider adding a programmatic validator for `verification_summary` in the evidence envelope validator.

## Raw Logs

Full test suite output stored in pytest output cache.