# Review-Agent Worktree-Mode Git-C Hardening

## Context

The `2026-07-05-incremental-derived-artifact-sync-filtering` run exposed a worktree-mode review hazard: workflow state may remain in the main/control checkout while implementation changes live in a feature worktree. If `review-agent` runs plain `git status`, `git diff`, or file inspection from the main checkout, it can review the wrong source of truth and produce false `review_change_set_missing` or `review_change_set_mismatch` blockers.

This spec implements the lowest-risk first hardening step: keep the current workflow architecture, but require `review-agent` to use `git -C <worktree_path> ...` for live Git inspection whenever a worktree path is available or expected.

This spec intentionally does not redesign workflow runtime context. It makes review safer immediately while later specs make worktree context first-class in the runtime.

## Goals / Non-Goals

**Goals:**

- Allow `review-agent` to inspect an explicit implementation worktree without relying on shell `cd` or the ambient cwd.
- In worktree-mode, require all live Git change-set commands to use `git -C <worktree_path> ...`.
- Prevent fallback to the main/control checkout when implementation worktree evidence is expected.
- Preserve non-worktree/main-checkout review behavior.
- Keep `review-agent` read-only for source code; this spec only expands observational Git commands.

**Non-Goals:**

- Do not introduce runtime `context.execution_mode` yet; that belongs to the runtime context spec.
- Do not change `finish-agent` behavior.
- Do not add workspace hydration or derived artifact dry-run behavior.
- Do not make `review-agent` a primary test executor.
- Do not grant broad shell navigation such as unrestricted `cd *`.

## Covered Optimization Points

This spec covers or partially covers these optimization points from the 2026-07-05 run analysis:

- **2. Worktree path is not workflow first-class context** — partial mitigation by requiring review to consume provided `worktree_path`; full runtime context is deferred.
- **3. Review-agent defaults to current cwd and can mix main/worktree** — directly fixed for review live Git inspection.
- **7. Main/worktree commit responsibilities are confused** — partial prevention by making review observe the implementation worktree explicitly.
- **16. before-dispatch should carry canonical runtime context** — deferred, but this spec defines the review-side consumption contract.
- **20. implement/review evidence should include changed_files and worktree_path** — review prompt should require these artifacts when worktree-mode is used; runtime persistence is deferred.

## Decisions

### Decision 1: Use `git -C`, not `cd`

`review-agent` must not rely on `cd` to enter the implementation worktree. `cd` is shell-session local and may not persist across independent bash tool calls. It also makes the active source of truth implicit.

In worktree-mode, every live Git command must bind directly to the worktree path:

```bash
 git -C <worktree_path> rev-parse --show-toplevel
 git -C <worktree_path> status --short --branch
 git -C <worktree_path> diff --name-status
 git -C <worktree_path> diff --cached --name-status
 git -C <worktree_path> ls-files --others --exclude-standard
 git -C <worktree_path> diff --stat
 git -C <worktree_path> diff --cached --stat
```

### Decision 2: Expand Review-Agent Observational Git Allowlist

Add read-only `git -C` patterns to `review-agent` permission allowlist:

```yaml
permission:
  bash:
    "git -C * status*": allow
    "git -C * diff*": allow
    "git -C * log*": allow
    "git -C * ls-files*": allow
    "git -C * check-ignore*": allow
    "git -C * rev-parse*": allow
    "git -C * branch*": allow
```

Keep existing plain Git read commands for non-worktree/main-checkout reviews, but the prompt must state that plain `git status` / `git diff` are forbidden in worktree-mode.

### Decision 3: Define Worktree-Mode Review Source-of-Truth Rules

When `artifacts.worktree_path`, `context.worktree_path`, or a handoff-provided worktree path exists, `review-agent` must treat it as the implementation source of truth.

Before reviewing implementation changes, `review-agent` must:

1. Validate the worktree exists using permitted read/file inspection or `git worktree list`.
2. Run `git -C <worktree_path> rev-parse --show-toplevel`.
3. Confirm the returned top-level path matches the expected worktree path or a normalized equivalent.
4. Run the live change-set commands using `git -C <worktree_path>`.
5. Compare live changed files with implement-agent evidence.

### Decision 4: Missing or Invalid Worktree Context Blocks Review

If worktree-mode is expected but no valid worktree path is available, `review-agent` must not inspect the main checkout. It must return a structured blocker.

Allowed blocker reasons:

- `missing_worktree_context` — implementation evidence indicates worktree-mode, but no worktree path is available.
- `invalid_worktree_context` — provided worktree path does not exist or is not a Git worktree.
- `review_worktree_mismatch` — live worktree root or branch contradicts implement-agent handoff/runtime evidence.
- `review_change_set_missing` — no live changed files are found in the expected worktree while implement-agent reported changes.
- `review_change_set_mismatch` — live changed files contradict implement-agent handoff evidence.

### Decision 5: Preserve Non-Worktree Review Behavior

If no worktree evidence is expected and the workflow is explicitly operating in main-checkout mode, `review-agent` may continue to use existing plain Git read commands:

```bash
git status --short --branch
git diff --name-status
git diff --cached --name-status
git ls-files --others --exclude-standard
```

This preserves compatibility for small changes and non-worktree execution.

## Flow

```text
dev-orchestrator dispatches review-agent
  |
  v
review-agent receives implement-agent evidence
  |
  |- if worktree_path present or worktree-mode expected:
  |    |- use git -C <worktree_path> for all live Git inspection
  |    |- never fallback to main checkout
  |    |- block if path/root/change set is invalid
  |
  |- else:
       |- use existing main-checkout live Git protocol
```

## Affected Files

| File | Change |
|---|---|
| `agents/review-agent.md` | Add worktree-mode `git -C` protocol and blockers. |
| `.opencode/agents/review-agent.md` | Distributed copy generated from canonical agent. |
| `.claude/agents/review-agent.md` | Distributed copy generated from canonical agent. |
| `.cursor/agents/review-agent.md` | Distributed copy generated from canonical agent. |
| `tests/test_agent_config_lib.py` or related agent config tests | Assert review-agent allowlist includes required `git -C` read-only commands. |
| `tests/test_wrapper_contracts.py` or related prompt contract tests | Assert worktree-mode protocol forbids cwd fallback and requires `git -C <worktree_path>`. |

## Acceptance Criteria

- `review-agent` permission allowlist includes the required read-only `git -C * ...` patterns.
- Prompt contract says worktree-mode live Git inspection must use `git -C <worktree_path>`.
- Prompt contract says review must block instead of falling back to main when worktree context is missing or invalid.
- Existing non-worktree/main-checkout review commands remain available.
- Static tests verify distributed agent copies remain in sync with canonical review-agent content.

## Risks / Trade-offs

**Glob-style `git -C *` allowlist is broad:** This is accepted as a simple first step. Later runtime context hardening can replace it with a controlled review script if needed.

**Prompt-only source-of-truth is imperfect:** This spec mitigates immediate review misrouting. The later runtime context spec must make execution mode and worktree metadata first-class.

**Read tool cwd remains ambient:** This spec governs Git change-set discovery. Review-agent should use changed file paths from the worktree-aware Git output when reading files, and must avoid treating main checkout files as authoritative for uncommitted changes.
