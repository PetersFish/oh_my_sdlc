# Finish-Agent Branch Decision and Terminal Ownership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Govern finish lifecycle decisions so finish-agent cannot silently choose branch outcome or terminal-finalize workflow state, while completed lightweight-flow runs archive matching Superpowers plans/specs into typed archive directories.

**Architecture:** Add branch finish decision gate, clarify implementation vs workflow commit ownership, record memory sync target refs, enforce finish-agent terminal boundaries, add semantic archive evidence, and move lightweight-flow Superpowers artifacts into `docs/superpowers/archive/plans/` and `docs/superpowers/archive/specs/`. Do not redefine post-done final Git commit; that is owned by `workflow-final-tail-commit`.

---

## File Structure

Expected files:

- Read: `docs/superpowers/specs/2026-07-05-finish-agent-branch-decision-and-terminal-ownership.md`.
- Read as dependencies:
  - `docs/superpowers/specs/2026-07-05-workflow-runtime-execution-context-and-agent-result-integrity.md`.
  - `docs/superpowers/specs/2026-07-05-workflow-final-tail-commit.md`.
- Modify: `.ai/workflows/scripts/workflow.py`.
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`.
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml` if archive criteria change.
- Modify after sync: distributed workflow runtime/template copies under `.opencode/`, `.claude/`, and `.cursor/`.
- Modify: `agents/dev-orchestrator.md`.
- Modify: `agents/finish-agent.md`.
- Modify after sync: distributed dev-orchestrator and finish-agent copies.
- Modify or create fixtures under `docs/superpowers/archive/plans/` and `docs/superpowers/archive/specs/` as needed for tests.
- Modify: `tests/test_workflow.py`.
- Modify: `tests/test_wrapper_contracts.py` or related prompt-contract tests.

Out of scope:

- Implementing `workflow.py final-commit` internals.
- Review-agent worktree `git -C` hardening.
- Worktree hydration and derived artifact dry-run.
- Forcing every run to use worktree mode.

---

## Task 1: Add Failing Tests for Branch Finish Decision Gate

- [x] Inspect workflow runtime tests and existing gate/state helpers.
- [x] Add a test proving worktree/feature-branch finish cannot proceed without `branch_finish_decision`.
- [x] Assert missing decision returns blocker/error `missing_branch_finish_decision` and recommended action `ask_user_branch_finish_decision`.
- [x] Add tests for allowed values only:
  - `merge_local`
  - `create_pr`
  - `keep_branch`
  - `discard`
- [x] Add a test proving no silent default branch action is selected.
- [x] Add a compatibility test proving main-checkout mode without feature branch does not require the gate by default.
- [x] Run focused tests and confirm expected failures.

Suggested command:

```bash
python3 -m pytest tests/test_workflow.py -k "branch_finish or finish_decision" -v
```

---

## Task 2: Add Failing Tests for Lightweight-Flow Superpowers Archive Moves

- [x] Create test fixture with active lightweight-flow plan and spec files:
  - `docs/superpowers/plans/<name>.md`
  - `docs/superpowers/specs/<name>.md`
- [x] Add runtime state or artifacts containing `primary_design_path` and `design_artifact_paths[]` with plan/spec kinds.
- [x] Assert finish archive behavior moves plan files to `docs/superpowers/archive/plans/<same-filename>.md`.
- [x] Assert finish archive behavior moves spec files to `docs/superpowers/archive/specs/<same-filename>.md`.
- [x] Assert source files are removed from active `plans/` and `specs/` locations.
- [x] Assert archive evidence records both source and destination design artifact paths.
- [x] Add a test for collision handling: existing destination file must not be overwritten silently.
- [x] Add a test for missing expected artifacts: return blocker `missing_lightweight_archive_artifacts` or explicit `archive_action_completed: false` when appropriate.
- [x] Run focused tests and confirm expected failures.

---

## Task 3: Add Failing Tests for Semantic Archive Evidence

- [x] Add tests proving new lightweight-flow evidence uses:
  - `archive_action_completed`
  - `archive_artifact_path`
  - `archive_not_required_reason`
  - `archived_design_artifact_paths`
  - `source_design_artifact_paths`
- [x] Assert new lightweight-flow runs do not rely on misleading `archive_path_exists: true`.
- [x] Add backward-compatibility tests proving legacy `archive_path_exists` runs remain readable during migration.
- [x] Add spec-flow test ensuring OpenSpec archive path behavior remains valid.

---

## Task 4: Add Failing Tests for Finish-Agent Terminal Boundary

- [x] Add prompt-contract tests asserting finish-agent must not call or claim ownership of terminal workflow state movement.
- [x] Assert finish-agent prompt forbids direct `workflow.py done`, terminal `advance` that moves active to history, manual active-to-history moves, pointer cleanup, and manual finalize operations.
- [x] Add prompt-contract tests asserting finish-agent returns final JSON evidence and records which checkout/ref was used for each operation.
- [x] Add prompt-contract tests asserting dev-orchestrator owns user branch decision collection and records the selected decision before redispatching finish-agent.

---

## Task 5: Implement Branch Finish Decision Gate

- [x] Add runtime representation for `branch_finish_decision` gate or context field.
- [x] Add validation that worktree/feature-branch finish requires explicit decision.
- [x] Add command support or extend existing context/gate recording command so dev-orchestrator can record the selected decision.
- [x] Validate allowed values exactly:
  - `merge_local`
  - `create_pr`
  - `keep_branch`
  - `discard`
- [x] Return structured blocker/error when missing or invalid.
- [x] Preserve main-checkout/non-feature-branch compatibility.
- [x] Run focused tests.

---

## Task 6: Implement Branch Action Semantics and Evidence

- [x] For `merge_local`, define required checks and evidence for local merge into base branch.
- [x] For `create_pr`, define PR-ready or PR-created evidence without assuming remote PR tooling is always available.
- [x] For `keep_branch`, preserve/push feature branch without implying implementation commits are in main.
- [x] For `discard`, require explicit confirmation and record discard evidence/residual risk.
- [x] Record `branch_finish_action` in finish artifacts.
- [x] Keep implementation commits and workflow commits conceptually separate in evidence.
- [x] Do not silently merge, keep, PR, or discard.

---

## Task 7: Implement Memory Sync Target Rules

- [x] Update runtime/prompt behavior so memory sync records target ref type, target ref, target commit, and resolution.
- [x] For `merge_local`, target the merged base/main commit.
- [x] For `create_pr`, target the feature branch commit unless PR merge is completed in-flow.
- [x] For `keep_branch`, target the feature branch commit.
- [x] For `discard`, record `not_needed` or a control ref with explicit reason.
- [x] Add tests or prompt-contract assertions for these rules.

---

## Task 8: Implement Lightweight-Flow Superpowers Archive Moves

- [x] Add helper to identify matching Superpowers artifacts using this priority:
  1. `primary_design_path`
  2. `design_artifact_paths[]` with kind `plan` or `spec`
  3. deterministic slug/date matching only as fallback
- [x] Move plan files from `docs/superpowers/plans/` to `docs/superpowers/archive/plans/`.
- [x] Move spec files from `docs/superpowers/specs/` to `docs/superpowers/archive/specs/`.
- [x] Preserve filenames.
- [x] Create typed archive directories when needed.
- [x] Avoid silent overwrite on collisions; use deterministic suffix or return blocker per implementation choice.
- [x] Record source and destination paths in finish evidence.
- [x] Run focused archive tests.

---

## Task 9: Implement Semantic Archive Evidence and Migration

- [x] Update lightweight-flow archive evidence to use semantic fields from the spec.
- [x] Include `archive_artifact_path: null` when there is no single archive artifact.
- [x] Include `archived_design_artifact_paths` for moved plan/spec files.
- [x] Keep legacy `archive_path_exists` readable during migration.
- [x] Update `sdlc-main.yaml` criteria if needed, with backward compatibility.
- [x] Run workflow tests covering new and legacy criteria.

---

## Task 10: Update Dev-Orchestrator and Finish-Agent Prompts

- [x] Update dev-orchestrator prompt to ask user for branch decision when finish blocks with `missing_branch_finish_decision`.
- [x] Include allowed options and concise consequence explanation.
- [x] Update dev-orchestrator prompt to record selected decision before redispatching finish-agent.
- [x] Update finish-agent prompt to require branch decision before branch-affecting actions.
- [x] Update finish-agent prompt to archive lightweight-flow plan/spec files into typed archive subdirectories.
- [x] Update finish-agent prompt to forbid silent branch outcome and terminal workflow finalization.
- [x] Add or update prompt-contract tests.

---

## Task 11: Sync Runtime Templates and Derived Agents

- [x] Propagate runtime changes to bootstrap/distributed workflow templates.
- [x] Propagate canonical dev-orchestrator and finish-agent prompts to distributed copies.
- [x] Run established sync command.
- [x] Run:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

---

## Task 12: Full Verification

- [x] Run focused workflow tests:

```bash
python3 -m pytest tests/test_workflow.py -k "finish or archive or branch" -v
```

- [x] Run full workflow tests:

```bash
python3 -m pytest tests/test_workflow.py -v
```

- [x] Run prompt-contract tests:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
```

- [x] Run full test suite:

```bash
python3 -m pytest tests/ -v
```

- [x] Run derived artifact check:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

- [x] Inspect final Git state:

```bash
git status --short
```

Expected:

- archive moves are intentional workflow/governance changes;
- no unintended source/test changes are staged by finish behavior;
- derived prompts/templates are in sync.

---

## Task 13: Handoff and Acceptance Evidence

- [x] Summarize branch decision gate behavior.
- [x] Summarize branch action evidence and memory sync target rules.
- [x] Summarize lightweight-flow archive move behavior with source/destination examples.
- [x] Confirm final workflow artifact commit remains owned by `workflow-final-tail-commit`, not this plan.
- [x] Include exact verification command/result pairs.
- [x] Confirm all acceptance criteria from the spec.
