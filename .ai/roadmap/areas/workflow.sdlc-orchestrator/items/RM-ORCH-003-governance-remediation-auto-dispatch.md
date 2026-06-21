---
id: RM-ORCH-003
title: "Governance Remediation Auto-Dispatch"
status: idea
stage: v2
priority: p1
order: 50
depends_on:
  - RM-ORCH-001
  - RM-ORCH-005
openspec_change: null
created_at: 2026-06-21
started_at: null
completed_at: null
---

# Goal

When `governance-check` returns `block=true`, the system SHALL automatically dispatch the remediation to the LLM assistant for processing, instead of only appending a prompt to the input box that requires manual user intervention.

# Problem Context

Phase 1 (RM-ORCH-001) established the `governance-check` read-only diagnostic and an OpenCode plugin adapter that surfaces findings via `tui.appendPrompt`. This works for detection, but the user experience is broken: remediation text appears in the chat input box, requiring the user to manually send it. This creates a perceived system split where governance blocks are detected but the user must act as a relay between the runtime and the LLM.

The goal is to eliminate this manual relay. The plugin should either automatically submit the remediation task to the LLM, or the archive/orchestrator paths should handle governance remediation inline before returning control to the user.

# Scope

## In

- Probe OpenCode plugin/client API for a stable mechanism to submit a message or create an assistant turn programmatically from a plugin hook.
- If a stable auto-submit API exists: the `sdlc-governance` plugin SHALL automatically dispatch remediation when `governance-check` returns `block=true`.
- If no stable auto-submit API exists: the plugin SHALL keep `appendPrompt` as fallback, and the archive/orchestrator paths SHALL be updated to run governance remediation inline after archive before returning control to the user.
- Loop protection: the same finding hash SHALL only auto-trigger remediation once per session.
- The remediation stop condition SHALL remain `governance-check block=false`.
- `governance-check` SHALL remain read-only; the plugin SHALL NOT directly mutate workflow, roadmap, memory, or OpenSpec state.

## Out

- No direct state mutation from the plugin side.
- No attempt to auto-heal findings without LLM mediation.
- No removal of `appendPrompt` as fallback when auto-submit is unavailable.
- No cross-platform auto-submit claims before Phase 2 adapter validation (RM-ORCH-002).

# Design Notes

## Key Decisions

- Keep `governance-check` read-only. The plugin triggers LLM processing, not direct repair.
- Prioritize detecting OpenCode's auto-submit API capability first. Design decisions about workarounds depend on what the platform supports.
- If auto-submit is unavailable, fix the archive path first (archive -> governance remediation inline) before addressing idle-only surfacing.
- Loop protection via finding hash deduplication, same hash that already prevents duplicate `appendPrompt` injection.
- The orchestrator SHALL coordinate governance remediation as a post-archive workflow step when the plugin cannot auto-submit.

## Tradeoffs

- Auto-submit from plugin is the cleanest UX but depends on OpenCode API availability.
- Archive/orchestrator inline remediation covers the most common governance gap (dangling archive) but requires archiving skills to be governance-aware.
- Doing both (auto-submit when available, inline remediation as deterministic fallback) provides the best coverage at the cost of implementation complexity.

## Initial Approach

1. Probe OpenCode plugin `client` or event API for a stable method to submit a chat message or trigger an assistant turn. Candidate APIs to investigate: `client.chat.send`, `client.session.submit`, `experimental.chat.messages.transform`, or equivalent.
2. If an API is found: implement auto-dispatched remediation in `.opencode/plugins/sdlc-governance.ts` using the discovered API, with finding-hash deduplication to prevent loops.
3. If no API is found: update `openspec-archive-change` skill to run governance remediation inline. After archiving, run `governance-check`, and if blocked, automatically perform the remediation steps (ensure-run, resolve, complete-hooks, advance, done) before returning.
4. Regardless of auto-submit availability, improve the orchestrator to verify `block=false` before claiming lifecycle completion.
5. Document the chosen approach and its limitations.

## Open Questions

- Does OpenCode provide a stable `client.chat.send()` or equivalent API for programmatic message submission?
- Does `session.idle` fire reliably before or after the TUI input box accepts new input?
- Can the plugin distinguish between "idle after user turn" and "idle after assistant turn" to avoid auto-submitting during user interaction?

# Acceptance Criteria

- When a dangling archive is detected, the user does NOT need to manually send the governance prompt from the input box.
- The remediation loop runs automatically (via plugin auto-submit or orchestrator inline path) and reaches `governance-check block=false`.
- If OpenCode lacks a stable auto-submit API, the system SHALL explicitly document the fallback path and the archive path SHALL handle governance inline.
- Repeated idle events do NOT trigger duplicate auto-remediation for the same finding hash.
- `workflow.py governance-check` remains read-only and does not mutate domain state.
- `tests/test_workflow.py` passes for any `workflow.py` changes.

# Promotion Notes

Promote after RM-ORCH-001 (OpenCode baseline) is validated in production. The OpenSpec change should start with API capability probing before committing to a specific implementation path.

# Completion Notes

Not started.

# Design Reference

- `docs/opencode/sdlc-governance-plugin-install.md`
- `openspec/changes/archive/2026-06-21-opencode-governance-validation/design.md` (Decision 5: OpenCode plugin as thin idle adapter)
- `openspec/specs/opencode-governance-adapter/spec.md`
