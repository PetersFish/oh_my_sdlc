# Run Artifacts Unify Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the post-unification artifact drift by making runtime and agent contracts agree on run artifact locations, repairing three historical runs, and removing the one-time legacy migration code that no longer matches the intended model.

**Architecture:** Treat `active/<run_id>/` and `history/<run_id>/` as the only runtime-owned run directories. Any artifact written during an active run must land under `active/<run_id>/...`, and finalization must archive the entire active directory into `history/<run_id>/`. Historical flat sibling run directories under `.ai/workflows/runs/<run_id>/...` become repair input, not a supported steady-state layout.

**Tech Stack:** Python workflow runtime, Markdown agent prompts, pytest workflow/contract tests, template sync tooling

---

## Objective

Address three follow-up issues from `run-artifacts-unify`:
1. explain why plan/implementation/tests/review/finish failed to catch the drift,
2. repair historical artifacts for three named runs so they live under matching `history/<run_id>/` directories,
3. remove `_migrate_legacy_artifacts` once the supported runtime path is made explicit and covered by tests.

## Current evidence and likely root cause

### Observed facts
- Runtime state now archives `active/<run_id>/run.json` into `history/<run_id>/run.json`.
- Three completed runs still have sibling artifact trees at `.ai/workflows/runs/<run_id>/{plans,handoffs,logs}/...`.
- Two runs still use old flat history files (`history/<run_id>.json`) instead of history directories.
- `_migrate_legacy_artifacts()` only knows how to move `.ai/workflows/runs/handoffs/<run_id>/` and `.ai/workflows/runs/logs/<run_id>/` into `active/<run_id>/...`; it does not touch `.ai/workflows/runs/<run_id>/...` and does not handle plans.
- `cmd_done()`, `cmd_advance()` when transitioning to done, and `_finalize_run_to_history()` move only `active/<run_id>/` to `history/<run_id>/` and never reconcile sibling artifact trees before finalization.
- Agent prompts and multiple tests still encode artifact paths as `.ai/workflows/runs/<run_id>/...`, which is incompatible with the runtime’s `active/` → `history/` lifecycle.

### Root-cause hypotheses to confirm during implementation
1. **Contract drift:** the approved change updated runtime paths but did not update agent prompts, normalizer assumptions, or path examples to `active/<run_id>` / `history/<run_id>` semantics.
2. **Coverage gap:** tests proved directory moves when artifacts were already inside `active/<run_id>/`, but never exercised the real worker contract that writes artifacts to sibling `.ai/workflows/runs/<run_id>/...` paths.
3. **Review gap:** review-agent re-ran tests and noted spec drift, but did not inspect actual archived filesystem state for the completed run.
4. **Finish/runtime gap:** finish could mark the run done because no exit criterion asserts “all artifacts colocated under active/history” and finalization does not fail when sibling artifact trees still exist.
5. **Spec/doc drift:** archived design said agent definitions already matched the unified model and D3 described a one-time migration, but the implementation left a persistent migration helper plus path examples that still advertise the unsupported sibling layout.

## File/area map

- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Modify: `tests/test_workflow.py`
- Modify: `tests/test_wrapper_contracts.py`
- Modify: `agents/plan-agent.md`
- Modify: `agents/implement-agent.md`
- Modify: `agents/test-agent.md`
- Modify: `agents/review-agent.md`
- Modify: `agents/finish-agent.md`
- Modify if needed for consistency: `agents/dev-orchestrator.md`
- Modify mirrored distributed agent copies via `scripts/install_agents.py`
- Update follow-up docs/specs only where current wording still claims unsupported paths or the wrong migration model
- Repair data under:
  - `.ai/workflows/runs/history/2026-06-29-run-artifacts-unify/`
  - `.ai/workflows/runs/history/2026-06-29-subagent-consistency-audit/`
  - `.ai/workflows/runs/history/2026-06-29-subagent-json-examples-followup/`
  - source sibling trees under `.ai/workflows/runs/<run_id>/...`

## Recommended implementation approach

### Task 1: Lock the intended runtime contract with failing behavior tests first

**Behavior to prove**
- Active-run artifacts belong under `active/<run_id>/...`.
- Done runs end with a single `history/<run_id>/` directory containing `run.json`, `plans/`, `handoffs/`, and `logs/` when present.
- Finalization repairs or blocks on unsupported sibling artifact trees instead of silently leaving them behind.
- Historical flat `history/<run_id>.json` records can be converted into directories during explicit repair logic for the named runs.

**Test cases to add/update**
1. `test_finalize_run_to_history_colocates_sibling_run_artifacts`
   - Fixture creates `active/<run_id>/run.json` plus sibling `.ai/workflows/runs/<run_id>/plans|handoffs|logs`.
   - Expected failure before implementation: history dir lacks those artifacts and sibling tree remains behind.
2. `test_cmd_done_repairs_or_blocks_when_sibling_artifact_tree_exists`
   - Proves CLI done-path behavior, not just helper behavior.
   - Expected failure before implementation: command succeeds while leaving sibling artifacts orphaned.
3. `test_history_repair_converts_flat_history_json_to_directory`
   - Exercises the chosen repair helper/command on a flat history JSON file plus sibling artifacts.
   - Expected failure before implementation: flat JSON remains or no colocated directory is created.
4. `test_agent_prompt_examples_use_runtime_owned_artifact_paths`
   - Static contract check for agent prompt docs/examples.
   - Expected failure before implementation: prompts still reference `.ai/workflows/runs/<run_id>/...` without `active/` or `history/` semantics.
5. Update existing tests that currently normalize/accept old path examples so they assert the new contract instead of codifying drift.

**Verification commands**
- `python3 -m pytest tests/test_workflow.py -k "colocates_sibling_run_artifacts or sibling_artifact_tree or flat_history_json_to_directory" -v`
- `python3 -m pytest tests/test_wrapper_contracts.py -k "artifact_paths" -v`

## Task 2: Simplify runtime behavior and remove `_migrate_legacy_artifacts`

**Implementation intent**
- Replace the old handoffs/logs-only migration helper with a single supported rule: runtime-owned artifacts are under `active/<run_id>/...` while active, then under `history/<run_id>/...` when done.
- Update finalization path(s) so they reconcile sibling `.ai/workflows/runs/<run_id>/` trees before archiving, or fail loudly if repair cannot be completed safely.
- Remove `_migrate_legacy_artifacts` and the `.migrated` sentinel once equivalent supported behavior exists.
- Keep the same fix in live runtime and bootstrap template copy.

**Likely implementation shape**
- Introduce one explicit reconciliation helper for sibling per-run directories (including `plans`, `handoffs`, `logs`) used by finalization and by one-time historical repair logic.
- Ensure `save_run_state()` / `load_run_state()` no longer carry perpetual migration logic.
- Reuse a single finalization path instead of duplicating directory-move logic in `_finalize_run_to_history()`, `cmd_advance()`, and `cmd_done()`.

**Expected pre-implementation failure mode**
- Focused finalization tests fail because sibling artifacts are not moved and legacy migration logic does not touch plans or sibling run dirs.

## Task 3: Repair the three named historical runs

**Repair targets**
1. `2026-06-29-run-artifacts-unify`
   - Existing history dir already exists; move sibling `plans/`, `handoffs/`, `logs/` into it.
   - Remove stale `.migrated` only if it is no longer part of the supported model.
2. `2026-06-29-subagent-consistency-audit`
   - Convert `history/...json` into `history/.../run.json`.
   - Create the target history directory if missing.
   - Move sibling `plans/`, `handoffs/`, `logs/` into that history directory.
3. `2026-06-29-subagent-json-examples-followup`
   - Same flat-history-to-directory repair as above.
   - Preserve partial logs exactly as-is while colocating them.

**Repair strategy**
- Prefer a deterministic repo-local repair path implemented in runtime code or a small governed maintenance helper, not manual shell-only moves hidden from tests.
- Make repair idempotent: rerun should not duplicate or overwrite existing artifacts.
- Preserve timestamps/content; move directories whole where possible.
- After repair, source sibling `.ai/workflows/runs/<run_id>/...` trees and old `history/<run_id>.json` files should be gone.

**Behavior tests**
- `test_named_history_repair_is_idempotent`
- `test_named_history_repair_preserves_existing_history_directory_contents`

## Task 4: Align prompts, contracts, and docs with the supported artifact model

**Update scope**
- Agent prompts that instruct workers where to place plans, handoffs, and logs.
- Wrapper/normalizer tests that currently bless old paths.
- Any design/spec/doc text still claiming agent definitions already match the unified model or that `_migrate_legacy_artifacts` is the steady-state answer.

**Desired wording direction**
- During an active run: write to `.ai/workflows/runs/active/<run_id>/...`.
- After completion: evidence should point at `.ai/workflows/runs/history/<run_id>/...` if the artifact survives completion.
- Historical sibling `.ai/workflows/runs/<run_id>/...` trees are repair-only legacy state.

**Spec/doc consistency check**
- Confirm whether the archived `run-artifacts-unify` delta spec or design still needs a follow-up note documenting that the original D3 migration scope was wrong/incomplete for sibling run dirs and plans.
- For lightweight-flow, update only the docs needed to keep runtime/agent contracts consistent; do not create new OpenSpec artifacts.

## Task 5: End-to-end verification and recurrence prevention

**Focused verification commands**
- `python3 -m pytest tests/test_workflow.py -v`
- `python3 -m pytest tests/test_wrapper_contracts.py -v`
- `python3 -m pytest tests/test_init_foundations.py -v`
- `python3 -m pytest tests/ -v`
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check`

**Manual spot checks after tests**
- Inspect the three repaired runs and confirm each ends as:
  - `history/<run_id>/run.json`
  - `history/<run_id>/plans/...` when plans existed
  - `history/<run_id>/handoffs/...` when handoffs existed
  - `history/<run_id>/logs/...` when logs existed
- Confirm no sibling `.ai/workflows/runs/<run_id>/` directories remain for those runs.
- Confirm no flat `history/<run_id>.json` remains for the two lightweight-flow runs.

## TDD execution order

1. Add the failing workflow behavior tests for sibling artifact colocation and flat-history repair.
2. Add/update prompt-contract tests so old path examples fail.
3. Implement the runtime reconciliation/finalization simplification in live workflow.py.
4. Mirror the same runtime change into the bootstrap template.
5. Update agent prompts/docs and regenerate distributed copies.
6. Run focused tests until green.
7. Repair the three named runs using the now-tested repair path.
8. Run full verification and template drift checks.

## Recurrence-prevention checklist

- Add at least one executable workflow test that starts from the real old path shape the agents/docs described, not an already-correct `active/<run_id>/...` fixture.
- Make review expectations explicit: completed-run filesystem state is part of review scope for workflow-runtime changes.
- Make finalization assert artifact colocation before reporting done.
- Remove tests and prompt examples that codify unsupported artifact paths.

## EvalOps candidates

- None likely required for model behavior; this is deterministic workflow/runtime behavior.
- If the team still wants durable regression tracking, treat these as workflow regression fixtures rather than AI evals.
