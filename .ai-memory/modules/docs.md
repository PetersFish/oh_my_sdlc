---
id: modules/docs
type: module
title: Documentation
summary: Supporting documentation organized into decisions/, modules/, and superpowers/ subdirectories. Contains architectural decisions, module documentation, and superpowers reference material.
sync_status: synced
evidence_mode: discovery
linked_commits: ["72272fb8c448292dd985d7ee35f160de9e5c94bc"]
linked_specs: []
linked_sessions: ["20260529-01"]
updated_at: 2026-05-29T00:00:00Z
confidence: medium
tags: [docs, decisions, architecture, superpowers]
---

# Documentation

## Current Understanding

The docs/ directory provides supplementary documentation outside of OpenSpec artifacts:
- **decisions/**: Architecture Decision Records (ADRs)
- **modules/**: Per-module documentation
- **superpowers/**: Superpowers framework reference material

This is a lightweight documentation layer; primary specs live in `openspec/specs/`.

## Evidence

- Module discovery indicates 3 subdirectories (decisions/, modules/, superpowers/)
- No direct files at docs/ level — content is nested
- AGENTS.md at repo root provides behavioral guidelines

## Operational Guidance

- ADRs should go in docs/decisions/
- Module-specific docs go in docs/modules/
- Do not duplicate what's already in openspec/specs/

## Update Notes

Initial discovery during first repository memory sync (2026-05-29).
