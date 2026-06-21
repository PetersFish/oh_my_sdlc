---
id: live-template-drift
type: pitfalls
title: Live .ai/workflows/ Files Drift from Skill Templates
summary: Editing only .ai/workflows/scripts/workflow.py without syncing to sdlc-project-bootstrap/templates/ causes new bootstrapped projects to get stale template files. Pre-commit hook now enforces sync.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_specs: []
failure_evidence: [git_history: Commit 0e4e69f touched live workflow.py but not template, later re-synced in 30562de]
linked_commits: [78d5ba3]
linked_sessions: []
updated_at: 2026-06-21T16:00:00Z
tags: [templates, drift, sync, workflow]
severity: medium
status: mitigated
---

## Symptom

Bug fixes to `.ai/workflows/scripts/workflow.py` only changed the live file. The corresponding template at `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` remained stale. New projects bootstrapped via `sdlc-project-bootstrap` received the buggy version.

## Root Cause

No automated enforcement between live `.ai/workflows/` files and their skill template sources. The original `sync_templates.py` synced live→`.opencode/` templates (wrong target), bypassing canonical `skills/`.

## Mitigation

1. `sync_templates.py` now syncs live → canonical `skills/sdlc-project-bootstrap/templates/`
2. `.githooks/pre-commit` blocks commits with drift: live must match canonical
3. Failed commits show explicit fix command: `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .`
4. Root `AGENTS.md` documents the workflow and hook installation

## Detection

`python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check`
