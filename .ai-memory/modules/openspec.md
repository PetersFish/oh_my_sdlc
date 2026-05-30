---
id: openspec
type: module
title: OpenSpec
summary: OpenSpec workflow artifacts: change proposals, designs, specs, tasks, and verification reports. Structured as changes/ (active), changes/archive/ (completed), and specs/ (master specs). Load when working with OpenSpec workflow steps.
parent_id: null
sync_status: synced
evidence_mode: discovery
linked_commits: []
linked_specs: []
linked_sessions: ["20260529-000001"]
updated_at: 2026-05-29T00:00:00Z
confidence: high
tags: [openspec, specifications, workflow, changes, proposals]
owned_paths: ["openspec/"]
path_hints: ["openspec/"]
keywords: [openspec, change, proposal, design, spec, task, verify, brainstorm]
test_paths: []
spec_paths: ["openspec/specs/"]
---

# OpenSpec

## Current Understanding

The `openspec/` directory stores all OpenSpec workflow artifacts. Active changes live in `openspec/changes/`, completed/archived changes in `openspec/changes/archive/`, and master specifications in `openspec/specs/`. Each change has a standardized set of artifacts: proposal, design, specs (delta), tasks, and optionally brainstorm/plan.

## Evidence

Initial discovery scan: 61 files (59 .md, 2 .yaml). 2 active changes (`generic-child-module-discovery`), 6 archived changes. Config in `config.yaml`.

## Operational Guidance

- Active changes follow `openspec/changes/<change-id>/` convention.
- Each change contains proposal.md, design.md, specs/, and tasks.md.
- Archive completed changes under `openspec/changes/archive/<date>-<change-id>/`.
- Master specs live in `openspec/specs/<spec-name>/spec.md`.

## Child Modules

Not applicable — this is a storage/convention module, not a code module.

## Key Files

- `openspec/config.yaml` — workflow configuration
- `openspec/schemas/sdd-plus-superpowers/` — schema definitions and templates

## Entry Points

Changes are created/advanced through OpenSpec skills (`openspec-new-change`, `openspec-propose`, etc.).

## Tests

No dedicated test files for OpenSpec artifacts.

## Related Specs

Master specs under `openspec/specs/` define the formal specifications for clipboard-routing, module-discovery, openspec-memory-sync, repository-memory-init/load/sync, skill-boundary-cleanup, and others.

## Update Notes

First sync after repository memory initialization.
