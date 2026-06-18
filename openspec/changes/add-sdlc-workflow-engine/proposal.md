## Why

The current SDLC skill system relies on prompt discipline to continue cross-skill lifecycle steps after a worker skill completes, which allowed an archived OpenSpec change to leave its linked roadmap item active. A lightweight workflow engine is needed now to make phase state, resume behavior, required inputs, hooks, and completion criteria explicit without modifying upstream `openspec-*` skills.

## What Changes

- Introduce `.ai/workflows/` as the repository-local workflow runtime area for workflow definitions, current run state, history, and deterministic workflow scripts.
- Add a `sdlc-main` workflow that covers input, memory loading, brainstorming, intent decision, roadmap creation/review, OpenSpec change creation, apply, archive, post-archive actions, and done.
- Add a deterministic `workflow.py` runtime API for `start`, `resume`, `status`, `readiness`, `resolve`, `record-evidence`, `complete-phase`, `complete-hook`, `advance`, `block`, `done`, and `validate`.
- Separate workflow run state from domain state and evidence state: workflow state is owned by `workflow.py`, domain state remains owned by the existing domain skills, and evidence is recorded by the workflow runtime after observation or worker results.
- Require phase-level `required_inputs`, `phase_readiness`, blocked-state handling, and deterministic context loaders so workers receive only the context required for the current phase.
- Add post-archive hooks for memory sync and roadmap completion so archive success is not treated as full lifecycle completion until hooks are resolved.
- Keep upstream `openspec-*` skills unmodified; the workflow engine treats them as external workers.
- Add regression fixtures and tests for archived OpenSpec changes linked to active, done, missing, ambiguous, and mismatched roadmap items.

## Capabilities

### New Capabilities
- `sdlc-workflow-engine`: Defines the repository-local workflow engine, workflow/run state model, `workflow.py` command API, phase readiness, resume semantics, hook handling, and fixture-based test strategy.

### Modified Capabilities
- `sdlc-orchestrator`: The orchestrator must use the workflow runtime for SDLC run start/resume, readiness checks, worker dispatch, blocked-state handling, and post-archive hook coordination instead of relying only on in-session prompt discipline.
- `sdlc-roadmap-revision-workflow`: Roadmap completion after OpenSpec archive moves under workflow-managed post-archive hooks while `sdlc-roadmap` remains the owner of roadmap mutations.
- `openspec-memory-sync`: Memory sync resolution becomes a workflow-managed post-archive action for `sdlc-main`, with existing memory skills remaining the workers that perform durable memory updates.

## Impact

- Adds `.ai/workflows/definitions/`, `.ai/workflows/runs/`, and `.ai/workflows/scripts/workflow.py` plus schemas or validation logic for workflow definitions and run state.
- Updates `sdlc-orchestrator` skill guidance to start or resume `sdlc-main` runs, call `workflow.py` before and after worker phases, and avoid claiming completion while required hooks remain pending.
- Updates `sdlc-roadmap` integration guidance to keep roadmap item files as the domain source of truth and let workflow-managed hooks invoke `sdlc-roadmap done` when relevant.
- Updates memory-sync workflow expectations from a mandatory pre-archive gate to a post-archive action in `sdlc-main`, while still requiring explicit resolution such as synced, not needed, or user deferred with reason.
- Adds tests that run against temporary workspaces using an explicit root path so real `.ai/roadmap`, `.ai/workflows`, and `openspec` data are not modified.
