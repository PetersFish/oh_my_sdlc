---
id: workflow-runtime-architecture
type: architecture
title: Workflow Runtime Module Architecture
summary: >-
  The workflow runtime is a sibling package workflow_runtime/ behind a thin workflow.py CLI facade.
  Modules follow a strict dependency direction: core -> state/definitions/domains -> policies/dispatch -> lifecycle/governance -> cli.
  state.py is the sole writer of run-state files; domains.py is read-only.
parent_id: root
sync_status: synced
evidence_mode: commit
linked_commits: [f04a9d6]
linked_specs: [workflow-runtime-modularity]
updated_at: 2026-07-12T00:00:00Z
confidence: high
tags: [workflow, runtime, architecture, modules, cli-facade, state-io]
status: synced
---

# Workflow Runtime Module Architecture

## Entry Point

`.ai/workflows/scripts/workflow.py` — executable CLI facade. Shebang + short docstring + `workflow_runtime.cli.main()`. All documented commands, arguments, exit codes, and JSON output contracts preserved.

## Module Map

| Module | Responsibility | May write run-state? |
|---|---|---|
| `core.py` | constants, timestamps, hashes, path resolution, decision factories | no |
| `state.py` | run pointer, active/history load/save/validate, context derivation | **yes (sole writer)** |
| `definitions.py` | YAML loading, phase/transition interpretation, exit criteria, validation | no |
| `domains.py` | read-only OpenSpec/archive/roadmap/memory/EvalOps loaders | no (read-only) |
| `policies.py` | policy registry, decorators, preflight, ensure-run | no |
| `dispatch.py` | runtime-context assembly, before/after-dispatch validation+storage | no |
| `lifecycle.py` | command handlers (status/start/resume/.../done), transition helpers | via state |
| `governance.py` | findings, foundation verification, archive diagnostics, final-commit | no |
| `cli.py` | parser construction, command registration, handler dispatch, output, exit codes | no |

## Dependency Direction

```
core -> state, definitions, domains
state, definitions, domains -> policies, dispatch
policies, dispatch -> lifecycle, governance
lifecycle, governance -> cli
```

Higher-level modules MUST NOT import lower-level modules. Shared behavior moves downward only when it has a single stable meaning.

## Invariants

1. `workflow.py` remains executable at `.ai/workflows/scripts/workflow.py` with the same command surface.
2. Only `state.py` writes to `.ai/workflows/runs/`.
3. `domains.py` is read-only — never mutates OpenSpec/roadmap/memory state.
4. Bootstrap templates + distributed copies (`.opencode/`, `.claude/`, `.cursor/`) include the same module layout.
5. No third-party runtime dependencies.

## Tests

- `tests/test_workflow.py` — authoritative CLI regression suite (subprocess level against temp workspaces).
- `tests/test_workflow_modules.py` — extraction contracts (import smoke, state round trips, definition validation, policy metadata, read-only loaders, facade delegation).

## Bootstrap Sync

Package tree mirrors to `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/`. `init_foundations.py` installs the full tree into new projects. `sync_templates.py` enumerates the complete module inventory for live↔canonical and canonical↔distributed checks. Aggregate `scripts/sync_derived_artifacts.py` remains top-level verification entrypoint.

## References

- Decision memory: `decisions/workflow-runtime-modularization.md`
- Spec: `openspec/specs/workflow-runtime-modularity/spec.md`
- Archived change: `openspec/changes/archive/2026-07-11-modularize-workflow-runtime/`
- Roadmap: RM-ORCH-009 (done), RM-ORCH-010 (next: class-based state machine)