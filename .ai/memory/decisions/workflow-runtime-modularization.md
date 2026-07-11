---
id: workflow-runtime-modularization
type: decisions
title: Workflow Runtime Modularization — sibling package behind script facade
summary: Split the monolithic workflow.py into a sibling workflow_runtime/ package while keeping workflow.py as the executable CLI facade. Modules follow a strict dependency direction; state writes confined to state.py.
parent_id: root
sync_status: synced
evidence_mode: commit
linked_commits: [f04a9d6]
linked_specs: [workflow-runtime-modularity]
linked_sessions: []
updated_at: 2026-07-12T00:00:00Z
confidence: high
tags: [workflow, runtime, modularization, architecture, refactor, cli-facade]
deciders: [yuping]
status: accepted
---

## Context

`workflow.py` had grown to ~4,300 lines mixing path helpers, run-state persistence, workflow-definition interpretation, OpenSpec/roadmap/memory loaders, policy registry, preflight, lifecycle commands, governance diagnostics, parser construction, and process dispatch. Future wrapper and state-machine work (RM-ORCH-010) would otherwise keep accumulating in one file.

## Decision

**Layout:** Keep `.ai/workflows/scripts/workflow.py` as a thin executable facade (shebang + short docstring + delegation to `workflow_runtime.cli.main()`). Move cohesive responsibilities into a sibling package `.ai/workflows/scripts/workflow_runtime/`.

**Module responsibilities (stable):**
- `core.py` — constants, pure helpers (timestamps, hashes, path resolution, decision factories)
- `state.py` — run pointer discovery, active/history run load/save/validate, context/state derivation. **Only module that writes workflow run-state files.**
- `definitions.py` — YAML definition loading, phase/transition interpretation, exit criteria, definition validation
- `domains.py` — read-only OpenSpec, archive, roadmap, memory, EvalOps loaders
- `policies.py` — policy registry metadata, decorators, policy functions, preflight, ensure-run
- `dispatch.py` — runtime-context assembly, before/after-dispatch validation + storage
- `lifecycle.py` — status/start/resume/readiness/resolve/record/complete/advance/block/cancel/done handlers and transition helpers
- `governance.py` — governance findings, foundation verification, archive diagnostics, final-commit support
- `cli.py` — parser construction, command registration, root resolution, handler dispatch, output, exit codes

**Dependency direction:** `core` → `state`/`definitions`/`domains` → `policies`/`dispatch` → `lifecycle`/`governance` → `cli`. Higher-level modules must not be imported by lower-level modules.

**Bootstrap parity:** The package tree mirrors into `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/` and is distributed to `.opencode/`, `.claude/`, `.cursor/` as one governed inventory. `init_foundations.py` and `sync_templates.py` enumerate the complete module set.

## Consequences

- Future state-machine OO work (RM-ORCH-010) has a clean seam; it can replace `lifecycle.py`/`definitions.py` internals without touching CLI or state I/O.
- All command names, arguments, exit codes, JSON outputs, and run-file layout are preserved — no data migration needed; rollback is a source revert.
- `tests/test_workflow.py` remains the authoritative CLI regression suite (subprocess level). `tests/test_workflow_modules.py` covers extraction-specific contracts (import-all smoke, state round trips, definition validation, policy metadata, read-only loaders, facade delegation).
- Template/sync tooling must recognize every runtime module, not just `workflow.py`.
- State writes must stay confined to `state.py`; repository search during review confirms no other extracted module opens `.ai/workflows/runs/` for writing.

## Non-Goals

- No class-based state machine, no phase/transition redesign, no command renames, no public script move, no domain ownership changes, no third-party runtime deps.

## References

- `openspec/changes/archive/2026-07-11-modularize-workflow-runtime/design.md`
- `openspec/specs/workflow-runtime-modularity/spec.md`
- Roadmap item: RM-ORCH-009