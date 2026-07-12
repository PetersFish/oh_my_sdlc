---
id: 20260712-remove-superpowers-direct-dead-code
type: evolution
title: 2026-07-12 — Remove superpowers-direct Dead Code
summary: >-
  Removed the retired `superpowers-direct` Plan Mode handoff route from the
  sdlc-orchestrator skill, workflow runtime policies, and dev-orchestrator
  agent prompt. The governed `spec-driven-*` routes remain the only Plan Mode
  handoff paths. Canonical spec remediation deleted the matching
  "Direct flow handoff may name direct execution" scenario from
  `openspec/specs/sdlc-orchestrator/spec.md`.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_commits: ["5f3afe3", "63be305"]
linked_specs: [sdlc-orchestrator]
linked_sessions: []
updated_at: 2026-07-12T19:00:00Z
tags: [workflow, dev-orchestrator, dead-code, spec-remediation, lightweight-flow]
---

## Removed

- `agents/dev-orchestrator.md`: dropped the `superpowers-direct` Plan Mode
  handoff branch. The orchestrator no longer emits a direct-execution
  handoff after Plan Mode; only `spec-driven-incremental-flow` and
  `spec-driven-slice-flow` handoff language remains.
- `.ai/workflows/scripts/workflow.py` and
  `.ai/workflows/scripts/workflow_runtime/policies.py`: removed the policy
  registration / dispatch surface that admitted `superpowers-direct` as a
  governed route.
- Distributed copies (`.opencode/`, `.claude/`, `.cursor/` agents and
  workflow templates) and `skills/sdlc-project-bootstrap/templates/workflow/`
  updated to match canonical.
- `openspec/specs/sdlc-orchestrator/spec.md`: deleted the
  "Direct flow handoff may name direct execution" scenario. The remaining
  Plan Mode handoff scenarios are the governed `spec-driven-*` routes.
- Test suite trimmed of `superpowers_direct` regression cases:
  `tests/test_workflow.py`, `tests/test_workflow_modules.py`,
  `tests/test_wrapper_contracts.py`.

## Contract Changes

- The orchestrator SHALL NOT name direct execution in a Plan Mode handoff.
  All Plan Mode handoffs route through `spec-driven-*`.
- Workflow runtime policies no longer register `superpowers-direct`; the
  `POLICY_REGISTRY` / `POLICY_META` surfaces reflect only live routes.

## Distribution / Template Sync

- Pre-commit hook passed: all governed files in sync with canonical; all
  distributed copies match canonical.
- Lightweight-flow Superpowers plan archived to
  `docs/superpowers/archive/plans/2026-07-12-remove-superpowers-direct-dead-code.md`.

## Verification Evidence

- Full test suite: 1201 tests + 49 subtests, zero failures (per
  implement-agent handoff `verification_passed: true`).
- Review-agent accepted: live change set matches structured implement-agent
  evidence; plan checkboxes complete; canonical spec remediation closes the
  previously identified gap.

## Skipped Memory Types

- `pitfalls`: no failure evidence (no stack trace, failing test, or observed
  misbehavior). This was planned dead-code removal, not a bug fix.
- `decisions`: no new architecture decisions; refactor follows the existing
  workflow-runtime architecture recorded in
  `architecture/workflow-runtime-architecture.md`.
- `architecture`: no new architecture candidates; module map and dependency
  direction unchanged.
- `specs`: no new spec memory; `sdlc-orchestrator` spec remediation removed
  a retired scenario without introducing a new spec ID.
- `modules`: diff-detected module memory for `agents` and `workflow-runtime`
  unchanged in structure; no new module candidates accepted.