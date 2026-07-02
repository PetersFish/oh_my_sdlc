---
id: 20260702-roadmap-hook-governance-hardening
type: evolution
title: 2026-07-02 - Roadmap Hook Governance Hardening
summary: Hardened workflow roadmap hook governance by adding roadmap-agent lifecycle routing, validating ready/apply-start hook state at complete-hook time, fixing after-dispatch stale evidence promotion, and enforcing template/distribution sync.
parent_id: root
sync_status: pending_commit
evidence_mode: uncommitted_snapshot
confidence: high
linked_commits: []
linked_specs: [roadmap-hook-governance-hardening]
linked_sessions: []
updated_at: 2026-07-02T11:20:00Z
tags: [workflow, roadmap, agents, hooks, templates, governance]
---

## New Capabilities

- Added `roadmap-agent` as a thin lifecycle worker for roadmap-governed hooks.
- `cmd_complete_hook` now validates `roadmap_status_ready_if_linked` and `roadmap_apply_start_if_ready` against observed roadmap item state.
- `cmd_after_dispatch` now treats `roadmap-agent` as a hook worker, not a phase-completing worker.
- Successful worker re-dispatch can overwrite stale phase evidence instead of preserving old false values.

## Contract Changes

- `implement-agent` must return `blocked` when verification, template sync, or distribution work remains; `success + blockers` is no longer a valid completion signal for apply work.
- Roadmap-governed hook work must route through lifecycle dispatch and must not use General Task dispatch.

## Distribution / Template Sync

- Live `.ai/workflows/scripts/workflow.py` changes were synced into canonical `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`.
- Project-level distributed template copies under `.opencode/`, `.claude/`, and `.cursor/` were brought back into sync.

## Verification Evidence

- `python3 -m pytest tests/test_workflow.py -v`
- `python3 -m pytest tests/test_wrapper_contracts.py -v`
- `python3 -m pytest tests/test_sdlc_roadmap.py -v`
- `python3 -m pytest tests/ -v`
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check`
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed`
