# Workflow Runtime Execution Context and Agent Result Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make workflow execution context explicit for both main-checkout and worktree execution, preserve agent result slice/artifact evidence in `run.json`, and prevent terminal movement when required final lifecycle evidence is missing.

**Architecture:** Keep workflow run state in the control checkout. Add `execution_mode`, optional worktree metadata, `before-dispatch` runtime_context output, after-dispatch slice fallback/artifact persistence, and Option B terminal validation in existing terminal commands. Preserve backward compatibility for legacy/main-checkout runs.

---

## File Structure

Expected files:

- Read: `docs/superpowers/specs/2026-07-05-workflow-runtime-execution-context-and-agent-result-integrity.md`.
- Modify: `.ai/workflows/scripts/workflow.py`.
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`.
- Modify after sync: distributed workflow runtime templates under `.opencode/`, `.claude/`, and `.cursor/`.
- Modify: `agents/dev-orchestrator.md`.
- Modify: `agents/implement-agent.md`.
- Modify: `agents/review-agent.md`.
- Modify: `agents/finish-agent.md`.
- Modify after sync: distributed agent copies under `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`.
- Modify: `tests/test_workflow.py`.
- Modify: `tests/test_wrapper_contracts.py` or related prompt-contract tests.
- Read if needed: `AGENTS.md` and existing sync scripts.

Out of scope:

- Branch finish decision gate implementation.
- Workspace hydration.
- Derived artifact dry-run.
- Final post-done Git commit command.
- Moving workflow run state into worktrees.

---

## Task 1: Add Failing Runtime Tests for Execution Context

- [x] Inspect existing workflow test helpers for temporary roots, run state creation, command invocation, and JSON output assertions.
- [x] Add tests proving legacy runs without `execution_mode` are interpreted as `main_checkout`.
- [x] Add tests proving `main_checkout` runs do not require `worktree_path` or `feature_branch`.
- [x] Add tests proving worktree-mode context can record and expose:
  - `execution_mode`
  - `control_root`
  - `worktree_path`
  - `base_branch`
  - `feature_branch`
  - `parent_ref`
- [x] Add tests proving `base_ref` is not required in new outputs and legacy `base_ref` remains readable as historical evidence.
- [x] Run focused tests and confirm expected failures before implementation.

Suggested command:

```bash
python3 -m pytest tests/test_workflow.py -k "execution_context or runtime_context" -v
```

---

## Task 2: Add Failing Tests for `before-dispatch` Runtime Context

- [x] Add a test where run context is `main_checkout`; assert `before-dispatch` output includes `runtime_context.execution_mode == main_checkout`.
- [x] Add a test where run context is `worktree`; assert `before-dispatch` output includes worktree metadata.
- [x] Assert `runtime_context` includes `change_id` and does not require agents to infer paths from prose.
- [x] Assert `parent_ref` appears when recorded and `base_branch` remains the branch name.
- [x] Run focused tests and confirm expected failures before implementation.

---

## Task 3: Add Failing Tests for after-dispatch Slice and Artifact Persistence

- [x] Add a test proving `after-dispatch` slice resolution uses this order:
  1. CLI slice id
  2. agent result slice id
  3. dispatch intent slice id from state evidence
  4. context change id
  5. default
- [x] Add tests proving agent artifacts are persisted under latest `evidence.agent_result`.
- [x] Add tests proving agent artifacts are persisted under `evidence.agent_results[<slice_id>][<agent>]`.
- [x] Include implement-agent artifact examples with `worktree_path`, `repo_root`, `base_branch`, `parent_ref`, `feature_branch`, `changed_files`, `diff_commands`, `verification_commands`, `handoff_path`, and `design_artifact_paths`.
- [x] Add tests proving `base_ref` is not emitted by new artifact examples.
- [x] Run focused tests and confirm expected failures.

---

## Task 4: Add Failing Tests for Option B Terminal Evidence Validation

- [x] Identify existing terminal movement paths that can move active runs to history, including `advance`, `done`, or helper functions used by those commands.
- [x] Add a test where archive/post-archive terminal movement is attempted without required finish-agent evidence.
- [x] Assert terminal command returns a structured error/blocker and leaves the active run in place.
- [x] Add a test where required finish-agent evidence exists in `agent_results`; assert terminal movement can proceed.
- [x] Ensure validation applies to active terminal movement and does not break reading historical runs already in history.
- [x] Run focused tests and confirm expected failures.

Suggested command:

```bash
python3 -m pytest tests/test_workflow.py -k "terminal or finish_agent or evidence" -v
```

---

## Task 5: Implement Execution Context Storage and Validation

- [x] Add or update helpers in `workflow.py` for reading and validating `state.context.execution_mode`.
- [x] Default missing `execution_mode` to `main_checkout` for legacy compatibility.
- [x] Add validation for allowed values:
  - `main_checkout`
  - `worktree`
- [x] For worktree mode, validate required fields when terminal or dispatch paths need them:
  - `control_root`
  - `worktree_path`
  - `feature_branch`
- [x] Record `base_branch` and `parent_ref` when available; treat them as recommended metadata unless a specific command requires them.
- [x] Ensure workflow run state remains in the control root and is not copied into worktree paths.

---

## Task 6: Add Controlled Context Recording Path

- [x] Add or extend a runtime command to record context fields, such as `record-context` or an aggregate equivalent.
- [x] Support recording:
  - `execution_mode`
  - `control_root`
  - `worktree_path`
  - `base_branch`
  - `feature_branch`
  - `parent_ref`
- [x] Validate mode-specific requirements before committing context changes.
- [x] Return structured JSON for success/failure.
- [x] Add parser wiring and tests.

---

## Task 7: Implement `before-dispatch` Runtime Context Output

- [x] Update `cmd_before_dispatch` to emit `runtime_context` derived from `state.context`.
- [x] Include `execution_mode` for both main-checkout and worktree runs.
- [x] Include worktree fields only when available/relevant.
- [x] Include `change_id`.
- [x] Ensure existing before-dispatch output remains backward compatible for consumers.
- [x] Run focused tests.

---

## Task 8: Implement after-dispatch Slice Fallback and Artifact Persistence

- [x] Update `cmd_after_dispatch` slice resolution to use CLI, agent result, dispatch intent, context change id, then default.
- [x] Persist agent artifacts under latest `evidence.agent_result`.
- [x] Persist agent artifacts under `evidence.agent_results[<slice_id>][<agent>]`.
- [x] Preserve existing evidence fields and blockers.
- [x] Ensure old records without artifacts remain readable.
- [x] Run focused tests.

---

## Task 9: Implement Option B Terminal Evidence Validation

- [x] Add a helper that determines when final lifecycle evidence is required before terminal movement.
- [x] For archive/post-archive completion, require relevant finish-agent evidence in `agent_results` before active-to-history movement.
- [x] Modify existing terminal commands and helper paths rather than adding a new atomic finalize command.
- [x] If evidence is missing, return structured error/blocker and keep active run in place.
- [x] Ensure roadmap/hook agents can still run without hiding preserved finish-agent evidence.
- [x] Run focused terminal validation tests.

---

## Task 10: Update Agent Prompt Contracts

- [x] Update dev-orchestrator prompt to forward `runtime_context` and avoid path inference from prose.
- [x] Update implement-agent prompt to return artifacts using `base_branch` and `parent_ref`, not ambiguous `base_ref`.
- [x] Update review-agent prompt to prefer runtime_context and artifact worktree fields for source-of-truth selection.
- [x] Update finish-agent prompt to return final artifacts and not rely on prose-only handoff evidence.
- [x] Add or update prompt-contract tests for the artifact envelope and `base_branch`/`parent_ref` naming.

---

## Task 11: Sync Runtime Templates and Derived Agents

- [x] Propagate `.ai/workflows/scripts/workflow.py` changes to bootstrap and distributed runtime templates.
- [x] Propagate canonical agent prompt changes to `.opencode`, `.claude`, and `.cursor` distributed copies.
- [x] Run the repo's established sync command.
- [x] Run:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

---

## Task 12: Full Verification

- [x] Run focused workflow tests:

```bash
python3 -m pytest tests/test_workflow.py -k "execution_context or runtime_context or after_dispatch or terminal" -v
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

- [x] Run final derived sync check:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

- [x] Inspect final Git state:

```bash
git status --short
```

---

## Task 13: Handoff and Acceptance Evidence

- [x] Summarize runtime context fields and compatibility behavior.
- [x] Summarize `before-dispatch` runtime_context output.
- [x] Summarize after-dispatch slice fallback and artifact persistence.
- [x] Summarize Option B terminal evidence validation.
- [x] Confirm `base_ref` is not used in new contracts and `base_branch`/`parent_ref` are used instead.
- [x] Include exact verification command/result pairs.
- [x] Confirm acceptance criteria from the spec.
