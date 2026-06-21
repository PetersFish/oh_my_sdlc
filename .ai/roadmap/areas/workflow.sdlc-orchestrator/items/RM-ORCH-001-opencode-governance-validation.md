---
id: RM-ORCH-001
title: "OpenCode Governance Validation"
status: done
stage: mvp
priority: p0
order: 10
depends_on: []
openspec_change: "opencode-governance-validation"
created_at: 2026-06-20
started_at: 2026-06-20
completed_at: 2026-06-21
---

# Goal

Validate Phase 1 of the SDLC orchestrator governance plan in OpenCode by adding runtime governance diagnostics and an OpenCode plugin that surfaces actionable follow-up work.

# Problem Context

The SDLC workflow runtime can enforce post-archive hooks once active, but the activation layer is still fragile when OpenSpec actions are invoked outside the orchestrator path. In particular, an OpenSpec change may be archived without a matching workflow run, or an active run may retain unresolved `pending_hooks` without the assistant noticing. Phase 1 closes that gap for the primary CLI, OpenCode, without modifying upstream OpenSpec skills.

# Scope

## In

- Add `workflow.py governance-check` as a cross-platform Python subcommand.
- Detect dangling archives: archived OpenSpec changes with no matching active or historical workflow run.
- Detect unresolved `pending_hooks` in active workflow runs.
- Add tests for clean state, dangling archive, pending hooks, and combined diagnostics.
- Add `.opencode/plugins/sdlc-governance.ts` as a thin OpenCode adapter.
- Use `session.idle` as the primary safe-time trigger for governance checks.
- Defer `file.watcher.updated` until idle-only behavior is proven stable.
- Inject actionable remediation prompts through OpenCode prompt/UI mechanisms such as `tui.prompt.append`.

## Out

- No automatic mutation of roadmap, OpenSpec, memory, or workflow state.
- No Claude Code or Cursor adapter implementation in Phase 1.
- No replacement of existing OpenSpec or roadmap lifecycle commands.
- No broad governance policy engine beyond dangling archives and pending hooks.
- No guarantee that OS/process exit or manual session switching will synchronously run governance remediation.

# Design Notes

## Key Decisions

- Keep governance detection in `workflow.py` so the logic is portable, testable, and independent of OpenCode-specific plugin APIs.
- Keep the OpenCode plugin thin: trigger the check, parse the result, and append an actionable prompt.
- Report governance issues rather than fixing them automatically; the assistant still performs judgment-heavy work such as memory sync and roadmap completion.
- Treat `workflow.py` as the single deterministic governance core.
- Count both matching active workflow runs and matching done history runs as valid evidence for archived changes.
- Treat `session.idle` as a turn-end / agent-loop-end reconciliation gate: the OpenCode agent and tool execution loop has finished, and the session is waiting for the next user action. It is not an `exit` hook and does not rely on session switching semantics.
- Use finding-specific remediation prompts with an explicit stop condition: re-run `workflow.py governance-check` and continue remediation only until `block=false`.

## Tradeoffs

- `session.idle` minimizes interference but may surface issues later than file watching.
- `file.watcher.updated` improves responsiveness but may produce repeated or noisy prompts unless throttled.
- Structured JSON output is better for adapters and tests, while the prompt text must remain readable enough for manual diagnosis.
- Idle gating is more reliable for Phase 1 than exit/session-switch detection because it runs at the end of the assistant turn, before control fully returns to the user.

## Initial Approach

- Implement `governance-check` in `.ai/workflows/scripts/workflow.py`.
- Return structured findings for `dangling_archive` and `pending_hooks`.
- Parse archived change IDs from `openspec/changes/archive/` and compare them to workflow run history.
- Add unit tests using temporary OpenSpec and workflow fixtures.
- Implement `.opencode/plugins/sdlc-governance.ts` to run the command on idle and inject a deduplicated prompt when `block` is true.
- Classify archived changes with matching active runs as resumable lifecycle state, and archived changes with matching done history runs as already completed lifecycle state.
- Classify archived changes with neither matching active run nor matching done history run as `dangling_archive`.
- For `pending_hooks`, emit an actionable prompt that names the hooks, the responsible worker categories, the required `complete-hook` follow-up, and the stop condition.
- Deduplicate repeated prompt injection by finding hash, including at least finding type, change ID, run ID, archive path, and pending hook names.

## Resolved Decisions

- A valid archived-change run may be either a matching active run, which means the lifecycle can still be resumed and checked for `pending_hooks`, or a matching done history run, which proves the lifecycle has already completed. If neither exists, `governance-check` reports `dangling_archive`.
- Phase 1 uses `session.idle` as the primary trigger. Idle means the OpenCode agent/tool execution loop has finished and the session is waiting for the next user action. It does not depend on the user running `exit` or switching sessions. `file.watcher.updated` is deferred until idle-only behavior is proven stable.
- Prompt wording is finding-specific, actionable, and includes an explicit stop condition: re-run `workflow.py governance-check` and continue only until `block=false`. The plugin deduplicates repeated prompts by finding hash to avoid loops.

## Validation Questions

These are not unresolved design decisions. They are implementation-time validation checks for the OpenCode adapter.

- Does OpenCode `session.idle` reliably fire after assistant turn completion in both TUI and non-TUI modes?
- Which OpenCode mechanism is best for prompt injection: `tui.prompt.append`, session message injection, or another SDK client method?
- What deduplication scope should be used: current process only, current session, or persisted session state?

# Acceptance Criteria

- `workflow.py governance-check` runs through Python and exits predictably on supported development environments.
- Dangling archived OpenSpec changes are detected with change ID and archive path context.
- Pending hooks are detected with hook name and related run/change context where available.
- Tests cover clean state, dangling archive, pending hooks, and combined findings.
- OpenCode plugin runs governance checks on `session.idle`.
- Plugin appends clear actionable prompts when governance checks block completion.
- Plugin avoids repeatedly injecting the same prompt in a tight loop.
- Verification proves `session.idle` fires after assistant turn completion for the target OpenCode mode.

# Promotion Notes

Promote this item to OpenSpec when ready to implement Phase 1. The OpenSpec should define the `governance-check` output contract, fixture layout for tests, plugin trigger behavior, and prompt deduplication rules.

# Completion Notes

Implemented Phase 1 governance diagnostics in workflow.py and OpenCode plugin. Archived under `openspec/changes/archive/2026-06-21-opencode-governance-validation/`.

# Design Reference

- `docs/manual/research/orchestrator.md`
