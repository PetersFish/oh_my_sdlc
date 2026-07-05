# Implement-Agent Handoff — Review-Agent Worktree-Mode Git-C Hardening

## Metadata

- agent: implement-agent
- phase: apply_change
- flow_type: lightweight-flow
- slice_id: default
- run_id: 2026-07-05-review-agent-worktree-mode-git-c-hardening
- primary_design_path: docs/superpowers/plans/2026-07-05-review-agent-worktree-mode-git-c-hardening.md
- design_artifact_paths:
  - docs/superpowers/plans/2026-07-05-review-agent-worktree-mode-git-c-hardening.md
  - docs/superpowers/specs/2026-07-05-review-agent-worktree-mode-git-c-hardening.md

## Objective

Harden review-agent so worktree-mode live change-set review always inspects
the explicit implementation worktree via `git -C <worktree_path>` and never
accidentally reviews the main/control checkout. Add read-only `git -C`
allowlist entries, update review-agent protocol text, and add static tests
proving worktree-mode review does not rely on ambient cwd.

## Work Completed

- Task 1: Added `TestReviewAgentWorktreeGitCPermissions` (3 tests) and
  `TestReviewAgentWorktreeModeLiveChangeReviewProtocol` (7 tests) to
  `tests/test_wrapper_contracts.py`. Confirmed all 10 fail before
  implementation (red phase).
- Task 2: Added 7 read-only `git -C * <subcmd>` bash allow rules to
  `agents/review-agent.md` frontmatter (status, diff, log, ls-files,
  check-ignore, rev-parse, branch). Existing plain read-only Git rules
  preserved for main-checkout mode. No broad `cd` permission granted.
- Task 3: Added "Worktree-Mode Live Change Review Protocol" section to
  `agents/review-agent.md` body, requiring explicit worktree path as
  source of truth, `git -C <worktree_path>` for live inspection, no
  shell cwd dependency, no fallback to main checkout, blockers for
  missing/invalid/mismatched worktree context, and explicit preservation
  of plain Git commands for main-checkout mode.
- Task 4: Ran `setup_agents.py --force` for `.opencode`, `.claude`, and
  `.cursor` agent targets. All distributed review-agent copies updated
  and activated (model/variant frontmatter written). Verified
  `python3 scripts/sync_derived_artifacts.py --check` returns
  "OK: all 6 check suites in sync".
- Task 5: Focused tests green; full regression 1049 passed;
  `sync_derived_artifacts.py --check` clean; plan checkbox validator
  exit 0.
- Task 6: Plan checkboxes synced to actual progress; handoff artifact
  written.

## Files/Artifacts Changed

Canonical:
- `agents/review-agent.md` — added 7 `git -C *` permission rules + new
  "Worktree-Mode Live Change Review Protocol" section.
- `tests/test_wrapper_contracts.py` — added 10 new test methods across
  two new test classes.
- `docs/superpowers/plans/2026-07-05-review-agent-worktree-mode-git-c-hardening.md`
  — all task checkboxes checked.

Distributed (synced from canonical via setup_agents.py):
- `.opencode/agents/review-agent.md`
- `.claude/agents/review-agent.md`
- `.cursor/agents/review-agent.md`
- `.opencode/agents/.agent-install.json` (source_ref updated)
- `.claude/agents/.agent-install.json` (source_ref updated)
- `.cursor/agents/.agent-install.json` (source_ref updated)

Runtime state (not part of implementation change set):
- `.ai/workflows/runs/current.json` — workflow pointer; reset by finish.
- `.ai/workflows/runs/active/` — active run directory; ephemeral.

## Commands Run

- `python3 -m pytest tests/test_wrapper_contracts.py -k "WorktreeGitC or WorktreeModeLiveChange" -v`
  — red phase: 10 failed. green phase: 10 passed.
- `python3 scripts/setup_agents.py --target ./.opencode/agents --force` (and .claude, .cursor) — installed + activated.
- `python3 -m pytest tests/test_wrapper_contracts.py -v` — 243 passed.
- `python3 -m pytest tests/test_agent_config_lib.py -v` — 23 passed.
- `python3 scripts/sync_derived_artifacts.py --check` — OK: all 6 check suites in sync.
- `python3 -m pytest tests/ -v` — 1049 passed, 49 subtests passed.
- `python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-05-review-agent-worktree-mode-git-c-hardening.md` — ok: all checkboxes complete.
- `git status --short` — confirms change set.

## Evidence Summary

- tasks_complete: true (all 6 plan tasks complete; checkboxes synced)
- tdd_passed: true (10 new tests red → green; full regression 1049 passed)
- Focused verification: 10/10 new tests pass; 243/243 wrapper-contract tests pass.
- Full regression: 1049 passed, 49 subtests passed, 0 failed.
- Derived artifact sync: all 6 check suites in sync.
- Plan checkbox validator: ok.

## Issues

None. The TDD red phase exposed that the permission allow-rule tests
read distributed `.opencode` copies, so they stayed red until Task 4
synced the derived copies — expected and resolved by running
`setup_agents.py --force` before re-running the focused tests.

## Learnings

- Permission-allowlist tests in `test_wrapper_contracts.py` read
  distributed agent copies (`.opencode`, `.claude`, `.cursor`), not
  canonical `agents/`. Implementation must sync derived copies before
  the green phase for permission tests; prompt-body tests read canonical
  `AGENTS_DIR` directly. Both paths were satisfied after Task 4.
- `setup_agents.py --force` is the correct sync+activate entrypoint per
  AGENTS.md. `install_agents.py` would wipe activation config.

## Suggestions

- Consider splitting `TestReviewAgentGitPermissions.REQUIRED_GIT_RULES`
  into a shared constant with the new
  `TestReviewAgentWorktreeGitCPermissions.REQUIRED_GIT_C_RULES` to
  prevent future drift if the allowlist taxonomy changes.
- The plan's "Modify: `tests/test_agent_config_lib.py` or the existing
  agent config tests" line is misleading — review-agent permission
  tests live in `test_wrapper_contracts.py`, not `test_agent_config_lib.py`.
  The latter covers model-profile resolution, not permission allowlists.

## Risks/Follow-Ups

- Glob-style `git -C *` allowlist is broad (per spec Risks section).
  Later runtime-context hardening may replace it with a controlled
  review script.
- This spec is prompt-only source-of-truth; runtime execution_mode and
  worktree metadata remain deferred to the runtime-context spec.

## Raw Logs

Stored by the bash tool under opencode's tool-output directory; key
commands and results captured in Commands Run above. No additional
raw log files written to `.ai/workflows/runs/.../logs/`.