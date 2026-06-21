---
id: template-sync-and-distribution
type: decisions
title: Template Sync + Canonical Distribution Workflow
summary: Live .ai/workflows/ files sync to canonical skills/ templates; git hook enforces consistency; distributed copies derived from canonical.
parent_id: root
sync_status: synced
evidence_mode: commit
linked_commits: [78d5ba3]
linked_specs: []
linked_sessions: []
updated_at: 2026-06-21T16:00:00Z
confidence: high
tags: [workflow, sync, templates, distribution, git-hooks]
deciders: [yuping]
status: accepted
---

## Context

Bug fixes to `.ai/workflows/scripts/workflow.py` and `.ai/workflows/definitions/sdlc-main.yaml` often only touched the live files, leaving `sdlc-project-bootstrap/templates/workflow/` stale. New projects bootstrapped from the skill would get buggy templates.

Additionally, distributed skill copies under `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/` could drift from canonical `skills/`.

## Decision

**Data flow**: live `.ai/workflows/` → canonical `skills/sdlc-project-bootstrap/templates/` → distributed `.opencode/.claude/.cursor/`.

**Tooling**:
- `skills/sdlc-project-bootstrap/scripts/sync_templates.py`: syncs live→canonical, checks canonical↔distributed, distributes canonical→all targets
- `.githooks/pre-commit`: two-tier enforcement — live==canonical AND canonical==distributed before commit allowed

**Governed files**: `workflow.py` and `sdlc-main.yaml` only. `.ai/workflows/AGENTS.md` intentionally excluded.

## Consequences

- No more stale templates: pre-commit hook blocks commits with drift
- Canonical `skills/` is single source of truth for all template content
- Distributed copies are mechanically derived, never hand-edited
- New `--check-distributed` and `--distribute` modes on sync_templates.py
- Root `AGENTS.md` documents the workflow and hook installation
