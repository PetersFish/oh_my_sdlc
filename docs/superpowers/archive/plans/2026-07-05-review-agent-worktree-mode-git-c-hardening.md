# Review-Agent Worktree-Mode Git-C Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Harden review-agent so worktree-mode live change-set review always inspects the explicit implementation worktree and never accidentally reviews the main/control checkout.

**Architecture:** Keep this as a small prompt and permission hardening change. Do not redesign workflow runtime context here. Add read-only `git -C` allowlist entries, update review-agent protocol text, and add static tests proving worktree-mode review does not rely on ambient cwd.

---

## File Structure

Expected files:

- Read: `docs/superpowers/specs/2026-07-05-review-agent-worktree-mode-git-c-hardening.md`.
- Modify: `agents/review-agent.md`.
- Modify after sync: `.opencode/agents/review-agent.md`, `.claude/agents/review-agent.md`, `.cursor/agents/review-agent.md`.
- Modify: `tests/test_agent_config_lib.py` or the existing agent config tests.
- Modify: `tests/test_wrapper_contracts.py` or the existing prompt-contract tests.
- Read if needed: `AGENTS.md`.

Out of scope:

- Runtime `execution_mode` schema.
- `before-dispatch` runtime_context output.
- Workspace hydration.
- Derived artifact dry-run.
- Finish-agent branch decision or terminal ownership.

---

## Task 1: Add Failing Permission and Prompt Contract Tests

- [x] Inspect existing helpers for parsing canonical agent frontmatter and distributed agent copies.
- [x] Add a config test asserting review-agent has read-only `git -C` allowlist entries for status, diff, log, ls-files, check-ignore, rev-parse, and branch.
- [x] Add a prompt-contract test asserting review-agent contains a Worktree-Mode Live Change Review Protocol.
- [x] The prompt test must assert these concepts appear: explicit worktree path, `git -C <worktree_path>`, no shell cwd dependency, no fallback to main checkout, and blockers for missing/invalid/mismatched worktree context.
- [x] Add or reuse distributed-copy tests for `.opencode`, `.claude`, and `.cursor` review-agent copies.
- [x] Run focused tests and confirm they fail before implementation:

```bash
python3 -m pytest tests/test_agent_config_lib.py -k "review" -v
python3 -m pytest tests/test_wrapper_contracts.py -k "review_agent" -v
```

---

## Task 2: Update Review-Agent Permission Allowlist

- [x] In `agents/review-agent.md`, add read-only `git -C` bash allowlist patterns for:
  - status
  - diff
  - log
  - ls-files
  - check-ignore
  - rev-parse
  - branch
- [x] Preserve existing plain read-only Git commands for non-worktree/main-checkout mode.
- [x] Do not grant broad `cd` permissions. The source of truth must be explicit on each Git command.

---

## Task 3: Update Review-Agent Live Change Review Protocol

- [x] Add or update a Worktree-Mode Live Change Review Protocol section near the existing Live Change Review Protocol.
- [x] Require review-agent to treat `runtime_context.worktree_path`, `context.worktree_path`, or `artifacts.worktree_path` as the implementation source of truth when provided or expected.
- [x] Require live Git inspection through `git -C <worktree_path>` for root validation, status, diff, cached diff, untracked files, and diff stats.
- [x] State that review-agent must never rely on shell cwd in worktree-mode.
- [x] State that review-agent must never fallback to the main/control checkout when worktree context is expected.
- [x] Define blockers:
  - `missing_worktree_context`
  - `invalid_worktree_context`
  - `review_worktree_mismatch`
  - existing `review_change_set_missing`
  - existing `review_change_set_mismatch`
- [x] Clarify that plain Git commands are allowed only when no worktree evidence is expected and the run is main-checkout mode.

---

## Task 4: Sync Derived Agent Copies

- [x] Inspect repo sync guidance and existing scripts.
- [x] Run the established canonical-to-derived sync path.
- [x] Verify distributed review-agent copies are updated.
- [x] Run:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

---

## Task 5: Verification

- [x] Run focused agent config tests:

```bash
python3 -m pytest tests/test_agent_config_lib.py -k "review" -v
```

- [x] Run focused prompt-contract tests:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k "review_agent" -v
```

- [x] Run broader related tests:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
python3 -m pytest tests/test_agent_config_lib.py -v
```

- [x] Run derived artifact check:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

- [x] Inspect final Git state:

```bash
git status --short
```

---

## Task 6: Handoff and Acceptance Evidence

- [x] Summarize changed canonical and distributed review-agent files.
- [x] Summarize tests changed.
- [x] Confirm worktree-mode review uses explicit worktree inspection and blocks instead of reviewing main when context is missing or invalid.
- [x] Confirm non-worktree/main-checkout review behavior is preserved.
- [x] Include exact verification command/result pairs.
