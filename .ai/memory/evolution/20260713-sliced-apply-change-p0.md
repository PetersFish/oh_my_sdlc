---
id: 20260713-sliced-apply-change-p0
type: evolution
title: "2026-07-13 — P0 Sliced Apply-Change Workflow Runtime"
summary: >-
  Introduced implementation slice lifecycle to the workflow runtime: a new
  workflow_runtime/slices.py module plus dispatch.py + state.py extensions
  that add read-only slice-status, deterministic slice-next, and exceptional
  slice-block / slice-resume / slice-cancel commands. The apply_change phase
  can now drive multiple implementation slices with explicit readiness,
  accept/block/cancel transitions, and review-remediation per slice.
  dev-orchestrator, implement-agent, review-agent, plan-agent, and
  finish-agent prompts were updated with slice-aware contract additions
  and the new branch_finish_decision enforcement.
parent_id: root
sync_status: synced
evidence_mode: commit
linked_commits: ["a4a3fb4ecd074f9e283279fc04e00c4cef70a555"]
linked_specs: []
linked_sessions: ["2026-07-13-sliced-apply-change-p0"]
updated_at: 2026-07-13T13:10:00Z
confidence: high
tags: [workflow, runtime, slices, apply-change, dispatch, plan-agent, implement-agent, review-agent, finish-agent, dev-orchestrator]
status: synced
---

# P0 Sliced Apply-Change Workflow Runtime

## Scope

Adds slice lifecycle support to the `apply_change` phase of the SDLC
workflow runtime. Work can now be split into ordered implementation slices,
each with its own implement → review → accept/block/cancel cycle. P0
delivers the read-only and deterministic subset (slice-status, slice-next,
slice-block, slice-resume, slice-cancel); later phases will add
parallelism and remediation re-dispatch.

## Key Changes

- `workflow_runtime/slices.py` (new, 365 lines): slice-status, slice-next,
  slice-block, slice-resume, slice-cancel command handlers. Delegates run
  state validation to `state.validate_implementation_state`.
- `workflow_runtime/state.py` (expanded): implementation block
  normalization, slice readiness evaluation, acceptance/blocking state
  transitions, `_archive_lightweight_superpowers_artifacts` for lightweight
  finish-agent archive moves, finish-agent evidence slice-id resolution
  refinements.
- `workflow_runtime/dispatch.py` (expanded): runtime-context assembly,
  slice-aware dispatch, after-dispatch result-contract validation,
  `POSITIVE_CLEANUP_EVIDENCE_KEYS` / `ARCHIVE_PHASE_CLEANUP_ONLY_EVIDENCE`
  sets, archive-phase evidence discipline, finish-agent branch finish
  decision enforcement.
- `workflow_runtime/cli.py`: new slice-* subcommands wired into the
  parser.
- `workflow.py`: facade imports for the new CLI surface.
- Agent prompts (`agents/`): dev-orchestrator, implement-agent,
  review-agent, plan-agent, finish-agent updated for slice lifecycle
  contracts and `branch_finish_decision` enforcement.
- `sdlc-project-bootstrap/templates/workflow/`: full template mirror for
  slices.py and all modified modules so new projects bootstrap with slice
  support.
- `skills/meta-skill-lifecycle-governance/scripts/install_skill.py`:
  no-op on unchanged payload to prevent timestamp churn on re-install.
- Tests: `tests/test_workflow.py` grew by ~2300 lines of slice lifecycle
  and dispatch contract regressions; `tests/test_wrapper_contracts.py`
  grew by ~60 lines of prompt-contract assertions.

## Architecture Impact

- `workflow_runtime/slices.py` is a sibling of `lifecycle.py`/`governance.py`
  in the module dependency direction: it consumes `state.py` (sole run-state
  writer) and `core.py` helpers. It does not write run-state directly except
  through `state.save_run_state`.
- Slice lifecycle is an `apply_change` concern only; create_change,
  archive_change, and post_archive_actions remain non-sliced in P0.
- `dispatch.py` after-dispatch now classifies evidence keys by phase and
  rejects cleanup-only keys in `archive_change` and positive cleanup keys
  that are not `True` in `post_archive_actions`.

## References

- Architecture memory: `architecture/workflow-runtime-architecture.md`
- Decision memory: `decisions/workflow-runtime-modularization.md`
- Module memory: `modules/agents.md`
- Plan/spec artifacts (archived):
  `docs/superpowers/archive/plans/2026-07-12-sliced-apply-change-p0.md`,
  `docs/superpowers/archive/specs/2026-07-12-sliced-apply-change-p0.md`