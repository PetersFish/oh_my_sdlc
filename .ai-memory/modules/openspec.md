---
id: modules/openspec
type: module
title: OpenSpec Framework
summary: Specification-driven development framework with changes/, specs/, and schemas/ directories. Uses an artifact workflow (proposal → design → specs → tasks → verify). All changes are in archived state.
sync_status: synced
evidence_mode: discovery
linked_commits: ["72272fb8c448292dd985d7ee35f160de9e5c94bc"]
linked_specs: []
linked_sessions: ["20260529-01"]
updated_at: 2026-05-29T00:00:00Z
confidence: high
tags: [openspec, specs, workflow, changes]
---

# OpenSpec Framework

## Current Understanding

This repo embeds an OpenSpec workflow for managing changes to skills and memory infrastructure. Structure:
- **changes/archive/**: 6 archived changes covering memory sync, multimodal routing, module discovery, and skill cleanup
- **schemas/**: SDD+Superpowers schema templates for artifact generation
- **specs/**: 10 active specs that define behavior of individual skills/modules (clipboard-routing, module-discovery, openspec-memory-sync, etc.)

The artifact workflow follows: proposal → design → specs → tasks → verify → archive.

## Evidence

- `openspec/changes/archive/` contains 6 completed change directories with full artifact sets
- `openspec/specs/` contains 10 spec directories, each with a spec.md
- `openspec/schemas/sdd-plus-superpowers/` provides artifact templates
- Module discovery confirmed 52 .md and 2 .yaml files in the openspec tree

## Operational Guidance

- Active changes should go in `openspec/changes/<id>/`, not directly in archive/
- Specs in `openspec/specs/` are the source of truth for skill behavior
- Archived changes provide evidence history for memory sync
- When creating new specs, follow the SDD+Superpowers template

## Update Notes

Initial discovery during first repository memory sync (2026-05-29).
