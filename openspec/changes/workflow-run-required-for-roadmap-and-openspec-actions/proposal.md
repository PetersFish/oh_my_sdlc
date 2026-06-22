## Why

Roadmap mutations currently bypass the SDLC workflow runtime even though they create, revise, cancel, replan, and complete stateful project work. This breaks the orchestrator's stateful SDLC contract and leaves roadmap operations without preflight, run evidence, or governance-check detection.

## What Changes

- Register Roadmap lifecycle mutations as governed workflow actions: `roadmap_capture`, `roadmap_insert`, `roadmap_review`, `roadmap_revise`, `roadmap_cancel`, `roadmap_reorder`, `roadmap_replan`, and `roadmap_done`.
- Update `sdlc-orchestrator` so roadmap-first operations run workflow preflight before delegating to `sdlc-roadmap` workers.
- Keep `sdlc-roadmap` as a worker only; it records roadmap mutations but does not start, preflight, advance, or complete workflow runs.
- Add runtime support for `roadmap_item` subjects, including deterministic phase inference and a single-subject run invalidation primitive for replanned items.
- Define `roadmap_replan` as a governed batch mutation whose evidence drives orchestrator loops over existing single-subject runtime primitives.
- Extend governance-check to detect roadmap state that lacks matching workflow evidence.
- Preserve bootstrap/read-only exceptions: `roadmap_init` remains ungoverned and `roadmap list` remains read-only.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `sdlc-orchestrator`: require runtime preflight and evidence handling for roadmap-first actions before dispatching roadmap workers.
- `sdlc-roadmap`: clarify roadmap lifecycle boundary and require mutation evidence suitable for orchestrator/runtime coordination.
- `sdlc-workflow-engine`: add governed roadmap actions, `roadmap_item` phase inference, run invalidation for replanned items, and governance-check coverage for roadmap mutations.

## Impact

- Affected files: `.ai/workflows/scripts/workflow.py`, `.ai/workflows/definitions/sdlc-main.yaml` if phase metadata needs adjustment, `skills/sdlc-orchestrator/SKILL.md`, `skills/sdlc-roadmap/SKILL.md`, `openspec/specs/**`, `tests/test_workflow.py`, and workflow templates under `skills/sdlc-project-bootstrap/templates/workflow/` plus distributed copies.
- Behavioral impact: roadmap mutations become governed stateful actions and may be blocked until a matching workflow run is created or positioned correctly.
- Compatibility: existing roadmap items remain valid. Legacy ungoverned items are reported by governance-check and are not auto-repaired.
