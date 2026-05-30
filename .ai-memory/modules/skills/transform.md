---
id: skills/transform
type: module
title: Content Transformation Skills
summary: Markdown content transformation skills for rendering diagrams, math formulas, algorithm blocks, and XMind mind maps.
parent_id: skills
sync_status: synced
evidence_mode: discovery
linked_commits: []
linked_specs: []
linked_sessions: []
updated_at: 2026-05-30T11:47:00Z
confidence: high
tags: [transform, rendering, markdown]
owned_paths:
  - skills/transform-algo-render
  - skills/transform-markdown-svg
  - skills/transform-math-formula
  - skills/transform-xmind
path_hints:
  - skills/transform-algo-render
  - skills/transform-markdown-svg
  - skills/transform-math-formula
  - skills/transform-xmind
keywords: [transform, svg, math, algorithm, xmind, markdown]
test_paths: []
spec_paths: []
---

# Content Transformation Skills

## Current Understanding

Grouped child module for 4 transform-related skills sharing the `transform-*` prefix. These skills handle rendering special content blocks in Markdown output.

- **transform-algo-render** — Algorithm section templates with pseudocode and complexity analysis
- **transform-markdown-svg** — SVG diagram generation from text descriptions
- **transform-math-formula** — Markdown math delimiter enforcement
- **transform-xmind** — PDF to XMind markdown mind map conversion

## Evidence

Prefix-based semantic grouping of 4 sibling skill directories under `skills/`.

## Operational Guidance

Invoke the relevant transform skill when output requires algorithm blocks, diagrams, math formulas, or mind maps.

## Key Files

- skills/transform-markdown-svg/scripts/generate-svg.py
- skills/transform-algo-render/SKILL.md
- skills/transform-math-formula/SKILL.md

## Entry Points

## Tests

## Related Specs

## Known Pitfalls

## Update Notes

First sync after memory reset. Created from prefix-based child module discovery.
