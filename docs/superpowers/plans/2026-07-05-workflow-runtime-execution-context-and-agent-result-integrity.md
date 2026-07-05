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

- [ ] Inspect existing workflow test helpers for temporary roots, run state creation, command invocation, and JSON output assertions.
- [ ] Add tests proving legacy runs without `execution_mode` are interpreted as `main_checkout`.
- [ ] Add tests proving `main_checkout` runs do not require `worktree_path` or `feature_branch`.
- [ ] Add tests proving worktree-mode context can record and expose:
  - `execution_mode`
  - `control_root`
  - `worktree_path`
  - `base_branch`
  - `feature_branch`
  - `parent_ref`
- [ ] Add tests proving `base_ref` is not required in new outputs and legacy `base_ref` remains readable as historical evidence.
- [ ] Run focused tests and confirm expected failures before implementation.

Suggested command:

```bash
python3 -m pytest tests/test_workflow.py -k "execution_context or runtime_context" -v
```

---

## Task 2: Add Failing Tests for `before-dispatch` Runtime Context

- [ ] Add a test where run context is `main_checkout`; assert `before-dispatch` output includes `runtime_context.execution_mode == main_checkout`.
- [ ] Add a test where run context is `worktree`; assert `before-dispatch` output includes worktree metadata.
- [ ] Assert `runtime_context` includes `change_id` and does not require agents to infer paths from prose.
- [ ] Assert `parent_ref` appears when recorded and `base_branch` remains the branch name.
- [ ] Run focused tests and confirm expected failures before implementation.

---

## Task 3: Add Failing Tests for after-dispatch Slice and Artifact Persistence

- [ ] Add a test proving `after-dispatch` slice resolution uses this order:
  1. CLI slice id
  2. agent result slice id
  3. dispatch intent slice id from state evidence
  4. context change id
  5. default
- [ ] Add tests proving agent artifacts are persisted under latest `evidence.agent_result`.
- [ ] Add tests proving agent artifacts are persisted under `evidence.agent_results[<slice_id>][<agent>]`.
- [ ] Include implement-agent artifact examples with `worktree_path`, `repo_root`, `base_branch`, `parent_ref`, `feature_branch`, `changed_files`, `diff_commands`, `verification_commands`, `handoff_path`, and `design_artifact_paths`.
- [ ] Add tests proving `base_ref` is not emitted by new artifact examples.
- [ ] Run focused tests and confirm expected failures.

---

## Task 4: Add Failing Tests for Option B Terminal Evidence Validation

- [ ] Identify existing terminal movement paths that can move active runs to history, including `advance`, `done`, or helper functions used by those commands.
- [ ] Add a test where archive/post-archive terminal movement is attempted without required finish-agent evidence.
- [ ] Assert terminal command returns a structured error/blocker and leaves the active run in place.
- [ ] Add a test where required finish-agent evidence exists in `agent_results`; assert terminal movement can proceed.
- [ ] Ensure validation applies to active terminal movement and does not break reading historical runs already in history.
- [ ] Run focused tests and confirm expected failures.

Suggested command:

```bash
python3 -m pytest tests/test_workflow.py -k "terminal or finish_agent or evidence" -v
```

---

## Task 5: Implement Execution Context Storage and Validation

- [ ] Add or update helpers in `workflow.py` for reading and validating `state.context.execution_mode`.
- [ ] Default missing `execution_mode` to `main_checkout` for legacy compatibility.
- [ ] Add validation for allowed values:
  - `main_checkout`
  - `worktree`
- [ ] For worktree mode, validate required fields when terminal or dispatch paths need them:
  - `control_root`
  - `worktree_path`
  - `feature_branch`
- [ ] Record `base_branch` and `parent_ref` when available; treat them as recommended metadata unless a specific command requires them.
- [ ] Ensure workflow run state remains in the control root and is not copied into worktree paths.

---

## Task 6: Add Controlled Context Recording Path

- [ ] Add or extend a runtime command to record context fields, such as `record-context` or an aggregate equivalent.
- [ ] Support recording:
  - `execution_mode`
  - `control_root`
  - `worktree_path`
  - `base_branch`
  - `feature_branch`
  - `parent_ref`
- [ ] Validate mode-specific requirements before committing context changes.
- [ ] Return structured JSON for success/failure.
- [ ] Add parser wiring and tests.

---

## Task 7: Implement `before-dispatch` Runtime Context Output

- [ ] Update `cmd_before_dispatch` to emit `runtime_context` derived from `state.context`.
- [ ] Include `execution_mode` for both main-checkout and worktree runs.
- [ ] Include worktree fields only when available/relevant.
- [ ] Include `change_id`.
- [ ] Ensure existing before-dispatch output remains backward compatible for consumers.
- [ ] Run focused tests.

---

## Task 8: Implement after-dispatch Slice Fallback and Artifact Persistence

- [ ] Update `cmd_after_dispatch` slice resolution to use CLI, agent result, dispatch intent, context change id, then default.
- [ ] Persist agent artifacts under latest `evidence.agent_result`.
- [ ] Persist agent artifacts under `evidence.agent_results[<slice_id>][<agent>]`.
- [ ] Preserve existing evidence fields and blockers.
- [ ] Ensure old records without artifacts remain readable.
- [ ] Run focused tests.

---

## Task 9: Implement Option B Terminal Evidence Validation

- [ ] Add a helper that determines when final lifecycle evidence is required before terminal movement.
- [ ] For archive/post-archive completion, require relevant finish-agent evidence in `agent_results` before active-to-history movement.
- [ ] Modify existing terminal commands and helper paths rather than adding a new atomic finalize command.
- [ ] If evidence is missing, return structured error/blocker and keep active run in place.
- [ ] Ensure roadmap/hook agents can still run without hiding preserved finish-agent evidence.
- [ ] Run focused terminal validation tests.

---

## Task 10: Update Agent Prompt Contracts

- [ ] Update dev-orchestrator prompt to forward `runtime_context` and avoid path inference from prose.
- [ ] Update implement-agent prompt to return artifacts using `base_branch` and `parent_ref`, not ambiguous `base_ref`.
- [ ] Update review-agent prompt to prefer runtime_context and artifact worktree fields for source-of-truth selection.
- [ ] Update finish-agent prompt to return final artifacts and not rely on prose-only handoff evidence.
- [ ] Add or update prompt-contract tests for the artifact envelope and `base_branch`/`parent_ref` naming.

---

## Task 11: Sync Runtime Templates and Derived Agents

- [ ] Propagate `.ai/workflows/scripts/workflow.py` changes to bootstrap and distributed runtime templates.
- [ ] Propagate canonical agent prompt changes to `.opencode`, `.claude`, and `.cursor` distributed copies.
- [ ] Run the repo's established sync command.
- [ ] Run:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

---

## Task 12: Full Verification

- [ ] Run focused workflow tests:

```bash
python3 -m pytest tests/test_workflow.py -k "execution_context or runtime_context or after_dispatch or terminal" -v
```

- [ ] Run full workflow tests:

```bash
python3 -m pytest tests/test_workflow.py -v
```

- [ ] Run prompt-contract tests:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
```

- [ ] Run full test suite:

```bash
python3 -m pytest tests/ -v
```

- [ ] Run final derived sync check:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

- [ ] Inspect final Git state:

```bash
git status --short
```

---

## Task 13: Handoff and Acceptance Evidence

- [ ] Summarize runtime context fields and compatibility behavior.
- [ ] Summarize `before-dispatch` runtime_context output.
- [ ] Summarize after-dispatch slice fallback and artifact persistence.
- [ ] Summarize Option B terminal evidence validation.
- [ ] Confirm `base_ref` is not used in new contracts and `base_branch`/`parent_ref` are used instead.
- [ ] Include exact verification command/result pairs.
- [ ] Confirm acceptance criteria from the spec.
