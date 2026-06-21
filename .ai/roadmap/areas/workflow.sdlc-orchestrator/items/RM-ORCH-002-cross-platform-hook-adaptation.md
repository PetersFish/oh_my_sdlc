---
id: RM-ORCH-002
title: "Cross-Platform Hook Adaptation"
status: idea
stage: v2
priority: p3
order: 20
depends_on:
  - RM-ORCH-001
openspec_change: null
created_at: 2026-06-20
started_at: null
completed_at: null
---

# Goal

Extend SDLC orchestrator governance checks beyond OpenCode by adding platform adapters for Claude Code and Cursor where reliable hooks are available.

# Problem Context

Phase 1 validates governance behavior in OpenCode, but the skill set is distributed across multiple AI coding environments. The same deterministic `workflow.py governance-check` contract should be reused across clients so post-archive governance does not depend on one platform's plugin model. Cross-platform support must keep platform differences at the adapter layer rather than duplicating governance logic.

# Scope

## In

- Add Claude Code Stop hook integration that calls `workflow.py governance-check`.
- Add Cursor hook integration if Cursor provides reliable hook support in the target environment.
- Treat Cursor as candidate support until its hook behavior passes a target-environment verification matrix.
- Verify governance-check behavior independently on each supported platform.
- Fall back to prompt/instruction-based governance guidance if Cursor hooks are unavailable or unreliable.
- Document adapter-layer command differences such as `python3`, `python`, and `py -3`.
- Document the minimum verification evidence required before marking a platform supported.

## Out

- No redesign of `workflow.py governance-check` semantics from Phase 1.
- No new governance rules beyond the Phase 1 contract.
- No attempt to support every AI coding platform generically.
- No claim that prompt-only fallback is equivalent to enforced hooks.
- No auto-detection of Python launchers or shell behavior inside `workflow.py`.

# Design Notes

## Key Decisions

- Keep `workflow.py governance-check` as the single governance runtime entry point.
- Put platform-specific command, hook, and Python invocation differences in adapter-layer configuration and documentation.
- Treat Cursor hook support as conditional until validated in the actual target version.
- Prefer stop/idle gates as the cross-platform baseline because they catch missed archive events without depending on exact file watcher semantics.
- Treat Claude Code as the first supported Phase 2 adapter because its Stop hook semantics provide a clear governance gate.
- Mark Cursor supported only for a specific verified Cursor version, OS, and execution mode.
- Use Cursor 3.8.11 on macOS Tahoe 26.5.1 as the first Cursor supported-target candidate.

## Tradeoffs

- Platform hooks provide stronger enforcement but increase per-platform maintenance.
- Prompt/instruction fallback is weaker but avoids pretending unsupported Cursor behavior is reliable.
- Explicit per-platform command configuration is simpler than premature auto-detection logic.
- A conditional Cursor adapter avoids overstating support but requires explicit verification records before users can rely on it.

## Initial Approach

- Start from the validated Phase 1 OpenCode `governance-check` contract.
- Add a Claude Code Stop hook adapter that shells into the same runtime check and blocks with an actionable reason when needed.
- Investigate Cursor hook capability through `.cursor/hooks.json` and implement only if the behavior is reliable enough to verify.
- Document recommended invocation commands for Unix/WSL and Windows-native environments.
- Keep adapter command selection explicit per platform. Unix, macOS, and WSL adapters may use `python3`; Windows-native adapters may use `python`, `py -3`, or an explicit shell prefix such as `cmd /c` when the platform requires it.
- Use a three-state Cursor support model: `unsupported`, `candidate`, and `supported`.
- For the current user-provided Cursor target, stop-hook feedback can drive remediation rather than only appearing as logs/errors.
- For Windows-native Cursor notes, use `python3` as the adapter invocation unless later validation proves a shell prefix is required.

## Resolved Decisions

- Cursor exposes a hook mechanism via project-level `.cursor/hooks.json`, but Cursor support remains conditional. Phase 2 may implement a Cursor adapter only after verifying the target Cursor version, OS, hook event behavior, command execution behavior, and failure/block semantics. Until then, Cursor is documented as candidate support, not guaranteed support.
- Adapter command selection remains explicit per platform. The governance core does not auto-detect Python launchers or shell behavior. Each adapter documents its invocation command for Unix/WSL, macOS, and Windows-native environments.
- Cursor is marked supported only after passing a target-environment verification matrix: hook config loads, command execution works, clean state passes, `pending_hooks` blocks or reports, `dangling_archive` blocks or reports, actionable feedback reaches the agent, dedup prevents repeated prompts, and Windows command behavior is verified if Windows-native support is claimed.
- The first Cursor support target is Cursor 3.8.11 on macOS Tahoe 26.5.1. In that target, stop-hook feedback is expected to reach the agent in a remediation-driving form. Windows-native Cursor adapter documentation uses `python3` as the initial command choice.

## Validation Results

- First supported Cursor target candidate: Cursor 3.8.11 on macOS Tahoe 26.5.1.
- Cursor stop-hook feedback can drive remediation, not only logs/errors, for the target validation path.
- Windows-native Cursor adapter command choice: `python3`.

# Acceptance Criteria

- Claude Code Stop hook invokes `workflow.py governance-check` and blocks or reports according to expected governance outcomes.
- Cursor integration is either implemented and verified, or explicitly documented as prompt/instruction fallback due to unreliable or missing hook support.
- Each supported platform has documented invocation commands, including `python3`, `python`, and `py -3` differences.
- Verification notes cover OpenCode baseline, Claude Code behavior, and Cursor support decision.
- Governance logic remains centralized in `workflow.py`.
- Cursor support status is recorded as `unsupported`, `candidate`, or `supported` with target version and OS evidence.
- Cursor validation notes record Cursor 3.8.11 on macOS Tahoe 26.5.1 as the first supported-target candidate.

# Promotion Notes

Promote after `RM-ORCH-001` validates the OpenCode baseline. The OpenSpec should focus on adapter behavior, per-platform verification, and documentation updates rather than redesigning governance rules.

# Completion Notes

Not started.

# Design Reference

- `docs/manual/research/orchestrator.md`
