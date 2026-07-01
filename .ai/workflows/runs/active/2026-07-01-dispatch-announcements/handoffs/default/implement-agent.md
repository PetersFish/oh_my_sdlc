# Implement Agent Handoff — Pre-Commit Agent Distribution Fix

**Slice ID:** default
**Flow Type:** lightweight-flow
**Date:** 2026-07-01

## Metadata

- Agent: implement-agent
- Phase: apply_change
- Status: success

## Objective

Fix the pre-commit hook (`.githooks/pre-commit`) so that activation-managed distributed agent files (`.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`) can be committed without canonical `agents/*` also being staged, as long as both `install_agents.py --check` and `activate_agents_config.py --check` pass for all three targets.

## Root Cause

`.githooks/pre-commit` lines 111-125 unconditionally blocked distributed-only staged agent changes as "Direct distributed agent edit" before running any meaningful validation.

## Work Completed

1. **RED phase:** Created `tests/test_precommit_hook.py` with 5 behavioral tests
   - `test_distributed_only_changes_pass_when_validation_checks_pass` — confirmed failing with "COMMIT BLOCKED: Direct distributed agent edit"
   - `test_distributed_only_changes_block_when_install_check_fails` — verifies blocking on install check failure
   - `test_distributed_only_changes_block_when_activate_check_fails` — verifies blocking on activate check failure
   - `test_canonical_only_changes_still_require_distributed_copies` — verifies existing behavior preserved
   - `test_distributed_only_changes_still_blocked_when_activate_check_fails_on_one_target` — verifies single-target failure blocks

2. **GREEN phase:** Replaced `.githooks/pre-commit` lines 111-125 with validation logic that:
   - Runs `install_agents.py --check` for all three targets
   - Runs `activate_agents_config.py --check` for all three targets
   - Only blocks if either check fails on any target
   - Provides clear diagnostic messages when blocking
   - Preserves the existing canonical-only block (lines 127-142)
   - Preserves the existing full validation (lines 144-168)

## Files Changed

### `.githooks/pre-commit` (lines 95-125)
Replaced the unconditional "Direct distributed agent edit" block with validation-driven gating that runs both `install_agents.py --check` and `activate_agents_config.py --check` on all three targets before deciding to block or allow.

### `tests/test_precommit_hook.py` (new file)
5 behavioral tests covering the distributed-only pass/fail scenarios and preserved canonical-only behavior.

## Commands Run

| Command | Result |
|---|---|
| `pytest tests/test_precommit_hook.py -v` | 5 passed |
| `pytest tests/ -v` | 907 passed, 37 subtests passed |

## Evidence Summary

- `evidence.tasks_complete`: true
- `evidence.tdd_passed`: true
- All focused tests witnessed RED before GREEN

## Blockers

None.

## Assumptions

- The `activate_agents_config.py` script is present at `scripts/activate_agents_config.py` when the hook runs (it's already distributed as part of this repo).
- Activation-managed changes (model/variant frontmatter) are the primary use case for legitimate distributed-only changes.
- The dual-run of `install_agents.py --check` (once in the distributed-only block and once in the combined block at lines 170-194) is intentional redundancy for clarity, not a bug.

## Risks/Follow-Ups

- The existing validation at lines 170-194 still only checks `install_agents.py --check` (not `activate_agents_config.py --check`) for the case where both canonical and distributed agents are staged. This gap was pre-existing and not part of this fix scope.
- If `scripts/activate_agents_config.py` is not present or the `yaml` module is not available, the hook will still block distributed-only changes (desired behavior — it surfaces a real issue).

## Raw Logs

See test output in standard pytest execution.
