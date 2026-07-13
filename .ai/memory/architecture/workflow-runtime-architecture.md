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
linked_commits: [f04a9d6, db18359, a4a3fb4]
linked_specs: [workflow-runtime-modularity]
linked_sessions: []
updated_at: 2026-07-13T13:10:00Z
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
| `slices.py` | implementation slice lifecycle: status/next/block/resume/cancel | via state |
| `cli.py` | parser construction, command registration, handler dispatch, output, exit codes | no |

## Dependency Direction

```
core -> state, definitions, domains
state, definitions, domains -> policies, dispatch
policies, dispatch -> lifecycle, governance, slices
lifecycle, governance, slices -> cli
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

## Refinements (2026-07-12, commit db18359)

Two contract refinements to `governance.py` and `state.py` (lightweight-flow `workflow-finalization-repair`):

### governance.py — status-aware final-commit path classification

`final-commit` previously classified dirty paths by prefix allowlist only, using `_classify_final_commit_paths`. That path-only view could not distinguish an active-run directory **deletion** (the expected move-to-history cleanup) from an unexpected dirty active-run artifact. As a result, active-run deletions stayed residual and the finalized tree never became clean.

Added `_classify_final_commit_entries` which consumes `git status --porcelain` entries (status code + path) and admits active-run paths whose status code indicates deletion (`D`). The path-only `_classify_final_commit_paths` is retained for existing callers/tests. `cmd_final_commit` now uses the status-aware classifier and filters staged paths against the resulting allowed set, preventing pre-existing staged files outside the commit scope from being swept in.

Tests: `test_final_commit_commits_target_active_run_deletions`, `test_final_commit_does_not_commit_target_active_run_non_deletions` in `tests/test_workflow.py`.

### state.py — finish-agent evidence slice-id resolution

`_missing_terminal_finish_agent_evidence` previously derived a single `relevant_slice_id` as `dispatch_intent_slice_id or change_id or "default"`. For unsliced lifecycle runs that recorded finish-agent results under `"default"` while `context.change_id` was set, the validator looked under `change_id`, failed to find success evidence, and blocked terminal movement to `done`.

The validator now builds a `candidate_slice_ids` list: when a dispatch-intent slice is present, only that slice is checked; otherwise both `"default"` and `change_id` are checked. A success under any candidate clears the gate. The returned finding (if any) reports the candidate list for diagnostics.

Tests: `test_advance_accepts_default_finish_agent_evidence_when_no_dispatch_slice` in `tests/test_workflow.py`.

## Refinements (2026-07-13, commit a4a3fb4)

### slices.py — P0 implementation slice lifecycle

New module `workflow_runtime/slices.py` (sibling of `lifecycle.py`/`governance.py`)
introducing the implementation slice lifecycle for the `apply_change` phase.
Commands: read-only `slice-status`, deterministic `slice-next`, and exceptional
`slice-block` / `slice-resume` / `slice-cancel`. Slice state is normalized and
validated by `state.validate_implementation_state`; slices write run-state
only through `state.save_run_state`. P0 is sequential single-slice-next only;
parallelism and remediation re-dispatch are deferred to later phases.

### dispatch.py — slice-aware dispatch and evidence discipline

`dispatch.py` after-dispatch now classifies evidence keys by phase:
`ARCHIVE_PHASE_CLEANUP_ONLY_EVIDENCE` rejects cleanup-only keys in
`archive_change`; `POSITIVE_CLEANUP_EVIDENCE_KEYS` requires them to be `True`
in `post_archive_actions`. `PHASE_AGENT_MAP` registers the agents valid per
phase. Branch-affecting finish actions now require an explicit
`branch_finish_decision` before execution.

### state.py — implementation block and archive helpers

`state.py` gained `normalize_implementation_state`,
`validate_implementation_state`, `slice_is_ready`, and
`_archive_lightweight_superpowers_artifacts` for lightweight finish-agent
archive moves (plans → `docs/superpowers/archive/plans/`, specs →
`docs/superpowers/archive/specs/`).

Tests: ~2300 new lines in `tests/test_workflow.py` (slice lifecycle, dispatch
contract, evidence discipline); ~60 new lines in
`tests/test_wrapper_contracts.py` (prompt contract assertions).