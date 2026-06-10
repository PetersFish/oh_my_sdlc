---
id: decisions/schema-simplification
type: decision
title: Remove sdd-plus-superpowers custom schema
summary: Replaced the custom sdd-plus-superpowers OpenSpec schema with the package-provided spec-driven schema. Workflow complexity (small/medium/large) is now handled by the sdlc-orchestrator skill via interaction flow (direct, propose, incremental) instead of custom schema variation.
sync_status: synced
evidence_mode: change
linked_commits: []
linked_specs: [simplify-sdlc-routing-schemas]
linked_sessions: []
updated_at: 2026-06-10T04:00:00Z
confidence: high
tags: [schema, openspec, sdlc, orchestration]
---

# Remove sdd-plus-superpowers Custom Schema

## Decision

The `sdd-plus-superpowers` project-local OpenSpec schema was removed entirely (not deprecated) and replaced with the package-provided `spec-driven` schema.

## Rationale

`sdd-plus-superpowers` mixed artifact governance (proposal/design/specs/tasks) with Superpowers execution discipline (TDD, debugging, review, verification) in a single schema definition. This made the schema carry responsibilities that belong to runtime orchestration.

The new architecture separates:

- **Artifact governance** → `spec-driven` (package-provided)
- **Workflow routing & complexity classification** → `sdlc-orchestrator`
- **Execution discipline** → Superpowers skills
- **Quality gates** → `sdlc-evalops`
- **Long-term planning** → `sdlc-roadmap`

## Consequences

- Medium and very complex formal changes both use `spec-driven`, differing by interaction flow (propose vs. incremental continue)
- `sdlc-openspec-init` no longer installs custom schemas; recommends `spec-driven` directly
- Project schema surface is simplified from 2 schemas to 1 package-provided schema
- Archived changes retain historical `sdd-plus-superpowers` metadata as records
