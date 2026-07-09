# Worktree Verification Hygiene and Derived Artifact Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Reduce high-frequency review noise by making worktree verification deterministic, adding `sync_derived_artifacts.py --dry-run`, and enforcing producer-owned cleanup for transient test artifacts.

**Architecture:** Add idempotent worktree hydration for required runtime fixture directories, implement a non-mutating derived-artifact smoke mode, standardize verification summary evidence, and update agent guidance so tests or smoke commands that create garbage must isolate or clean it before returning success.

---

## File Structure

Expected files:

- Read: `docs/superpowers/specs/2026-07-05-worktree-verification-hygiene-and-derived-artifact-dry-run.md`.
- Modify or add: `.ai/workflows/scripts/hydrate_workspace.py`.
- Modify or add: `.ai/workflows/scripts/validate_workspace.py` if validation is split from hydration.
- Modify: `scripts/sync_derived_artifacts.py`.
- Modify: `tests/test_sync_derived_artifacts.py`.
- Modify: `tests/test_evalops_root.py` or relevant evalops fixture tests.
- Modify: `agents/implement-agent.md`.
- Modify: `agents/review-agent.md`.
- Modify after sync: distributed agent copies under `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`.
- Modify: `tests/test_wrapper_contracts.py` or related prompt-contract tests.
- Read if needed: `AGENTS.md` and existing sync scripts.

Out of scope:

- Runtime execution context schema.
- Branch finish decision gates.
- Final tail commit implementation.
- Moving workflow run state into worktrees.
- Adding a separate `--plan` mode.
- Adding a new `safe_restore.py` script.

---

## Task 1: Add Failing Tests for Dry-Run and Cleanup Ownership

- [x] Inspect existing `tests/test_sync_derived_artifacts.py` helpers and fixture patterns.
- [x] Add tests proving `scripts/sync_derived_artifacts.py --dry-run --changed-file <skill-file> --json` does not write distributed agent/skill files or `.skill-install.json`.
- [x] Add tests proving dry-run output reports selected suites, affected domains, skipped writes, and dry-run status.
- [x] Add tests proving existing `--check` and `--fix` behavior remains backward compatible.
- [x] Add tests or assertions that changed-file classification tests use temporary fixtures, stubs, or cleanup so repository state is clean after passing tests.
- [x] Add prompt-contract tests requiring implement-agent to prefer `--dry-run` for derived sync smoke checks and to own cleanup for any transient artifacts it creates.
- [x] Add review-agent prompt-contract tests requiring review-agent to accept structured hygiene evidence and not bounce known hydration/dry-run noise when evidence is complete.
- [x] Run focused tests and confirm expected failures before implementation:

```bash
python3 -m pytest tests/test_sync_derived_artifacts.py -k "dry_run or cleanup" -v
python3 -m pytest tests/test_wrapper_contracts.py -k "dry_run or verification_summary" -v
```

---

## Task 2: Implement `sync_derived_artifacts.py --dry-run`

- [x] Inspect current `sync_derived_artifacts.py` classification, command construction, `--check`, and `--fix` flow.
- [x] Add CLI flag `--dry-run`.
- [x] Ensure `--dry-run` exercises classification, suite selection, command planning, and JSON report construction.
- [x] Ensure `--dry-run` performs no writes to distributed outputs or `.skill-install.json`.
- [x] Ensure mutating subprocesses are not invoked in dry-run; replace them with command-plan records or dry-run-safe stubs.
- [x] Ensure JSON output reports:
  - `dry_run: true`
  - changed files considered
  - affected domains
  - selected suites or commands
  - skipped writes
  - whether the planned operation would have succeeded
- [x] Ensure return codes are compatible with smoke-check usage.
- [x] Preserve existing `--check` and `--fix` behavior.
- [x] Run focused tests:

```bash
python3 -m pytest tests/test_sync_derived_artifacts.py -k "dry_run" -v
```

---

## Task 3: Implement Worktree Hydration

- [x] Inspect evalops tests and fixture requirements for `.ai/evals/targets/.../cases/...` directories.
- [x] Add an idempotent hydration script, for example `.ai/workflows/scripts/hydrate_workspace.py`.
- [x] The script should accept `--root <worktree_path>` and create only required non-Git runtime fixture directories.
- [x] Initial required directories should include case inbox/accepted/rejected directories under relevant eval target roots.
- [x] Do not copy or create workflow run state under worktree paths:
  - `.ai/workflows/runs/active`
  - `.ai/workflows/runs/current.json`
  - `.ai/workflows/runs/history`
- [x] Add or update validation behavior, either in a separate `validate_workspace.py` or a `--validate` flag.
- [x] Make hydration idempotent and log/report created paths.
- [x] Add focused tests proving hydration creates only expected fixture directories and does not create workflow run state.
- [x] Run focused tests:

```bash
python3 -m pytest tests/test_evalops_root.py -k "hydrate or workspace" -v
```

---

## Task 4: Standardize Verification Summary Evidence

- [x] Update implement-agent prompt to use `verification_summary.status` values:
  - `pass`
  - `fail`
  - `pass_with_accepted_preexisting_failures`
- [x] Require accepted pre-existing failures to include exact test id, reason, confirmation method, and owner/category.
- [x] Update review-agent prompt to accept `pass_with_accepted_preexisting_failures` only when the failure is clearly scoped, named, and confirmed unrelated to the implementation.
- [x] Add prompt-contract tests for the verification summary schema.
- [x] Ensure broad statements like `all tests passed except environment` are not acceptable evidence.

---

## Task 5: Add Producer-Owned Cleanup Guidance and Restore Boundary

- [x] Update implement-agent prompt to state that tests, scripts, and smoke commands that create transient artifacts must isolate or clean them before returning success.
- [x] Update guidance so smoke tests use `--dry-run` unless the task explicitly intends to repair generated artifact drift.
- [x] Add or update permission/prompt guidance for constrained restore of known safe derived paths with `git restore -- <known-safe-derived-path>`.
- [x] Do not add a new `safe_restore.py` script.
- [x] Add tests or prompt-contract checks confirming producer-owned cleanup language exists.

---

## Task 6: Sync Derived Agent Copies

- [x] Run the repo's established canonical-to-derived sync path.
- [x] Sync implement-agent and review-agent distributed copies.
- [x] Run:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

If drift is expected and safe, run the established fix command and re-check.

---

## Task 7: Full Verification

- [x] Run focused dry-run tests:

```bash
python3 -m pytest tests/test_sync_derived_artifacts.py -k "dry_run" -v
```

- [x] Run hydration/evalops tests:

```bash
python3 -m pytest tests/test_evalops_root.py -v
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

Expected:

- no `.skill-install.json` churn from tests or smoke commands;
- no unexpected generated drift;
- hydration only creates intended fixture directories in test/worktree roots.

---

## Task 8: Handoff and Acceptance Evidence

- [x] Summarize changed runtime scripts, sync script, tests, and prompts.
- [x] Summarize `--dry-run` behavior and prove it is non-mutating.
- [x] Summarize hydration behavior and prove workflow run state is not copied into worktrees.
- [x] Summarize verification summary schema.
- [x] Include exact verification command/result pairs.
- [x] Confirm acceptance criteria from the spec, especially producer-owned cleanup and no `--plan` mode.
