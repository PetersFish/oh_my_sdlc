# Retire Legacy sdlc-orchestrator Skill Spec

## Purpose

Retire the legacy `skills/sdlc-orchestrator/` skill family now that SDLC orchestration has moved to the `dev-orchestrator` agent and the active workflow runtime.

This cleanup must remove active runtime, test, EvalOps, roadmap, and documentation references that still treat `sdlc-orchestrator` as a live skill. The goal is not to rewrite history. The goal is to make the active repository state consistent with the current architecture.

## Context

The active SDLC path already routes through `dev-orchestrator`:

- `agents/dev-orchestrator.md` is the top-level SDLC routing entry point.
- `.ai/workflows/definitions/sdlc-main.yaml` uses `dev-orchestrator` for default governed routing phases.
- Current workflow hooks such as roadmap and post-archive actions are runtime-managed through `workflow.py` and dispatched through active agents.

The remaining `sdlc-orchestrator` references are now repository debt:

- A legacy canonical skill still exists under `skills/sdlc-orchestrator/`.
- Distributed copies still exist under `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/`.
- Active tests still assert that the legacy skill and its EvalOps target exist.
- Active skills still mention `sdlc-orchestrator` as the owner of routing or post-archive decisions.
- `.ai/evals/manifest.yaml` still registers `skill.sdlc-orchestrator`.
- `.ai/roadmap/manifest.json` and the corresponding workflow area still point at `skills/sdlc-orchestrator` as the owner path.

## Problem

Keeping the legacy skill in active state creates architectural drift:

1. The runtime says `dev-orchestrator` is the live SDLC entry point.
2. Tests and EvalOps assets still say `sdlc-orchestrator` is active.
3. Roadmap and skill docs still describe the legacy skill as the routing owner.
4. This mismatch makes future cleanup riskier because tests continue proving an obsolete contract.

## Goals

- Delete the legacy `sdlc-orchestrator` skill and its project-level distributed copies.
- Delete the active EvalOps target `skill.sdlc-orchestrator` instead of archiving or migrating it.
- Migrate active skill docs and scripts to describe `dev-orchestrator` and `workflow.py` as the current routing/governance owners.
- Update active roadmap metadata so no owner path points at deleted skill files.
- Update tests so they stop asserting legacy skill existence while preserving useful coverage for active EvalOps and workflow behavior.
- Keep historical archives, old specs, and old design notes untouched unless they are copied into active paths.

## Non-Goals

- Do not rewrite `openspec/changes/archive/` history.
- Do not rewrite old `docs/superpowers/specs/` or `docs/superpowers/plans/` files solely to remove historical references.
- Do not migrate retired `skill.sdlc-orchestrator` golden cases into `agent.dev-orchestrator` as a bulk rename.
- Do not weaken EvalOps runner/export behavior coverage.
- Do not redesign the SDLC workflow runtime.

## Target Architecture

After cleanup, active ownership should look like this:

```text
User SDLC routing
  -> dev-orchestrator
     -> workflow.py entry / dispatch hooks
     -> specialized agents

Roadmap mutation owner
  -> sdlc-roadmap / roadmap-agent

Roadmap lifecycle trigger owner
  -> dev-orchestrator + workflow.py hooks

EvalOps active targets
  -> active skills and agents only
  -> no skill.sdlc-orchestrator target
```

## Required Repository Changes

### 1. Delete Legacy Skill Assets

Delete these active files and directories:

- `skills/sdlc-orchestrator/`
- `.opencode/skills/sdlc-orchestrator/`
- `.claude/skills/sdlc-orchestrator/`
- `.cursor/skills/sdlc-orchestrator/`

### 2. Delete Active EvalOps Target

Delete the active target registration and workspace:

- Remove `skill.sdlc-orchestrator` from `.ai/evals/manifest.yaml`
- Delete `.ai/evals/targets/skill.sdlc-orchestrator/`

The chosen policy is direct deletion, not archival migration.

### 3. Migrate Active Skill Documentation

Update active skill files that still describe `sdlc-orchestrator` as current:

- `skills/meta-skill-evaluator/SKILL.md`
- `skills/sdlc-roadmap/SKILL.md`
- `skills/sdlc-evalops/SKILL.md`

Required direction:

- Overall SDLC routing owner: `dev-orchestrator`
- Workflow lifecycle/state owner: `workflow.py`
- Roadmap domain mutation owner: `sdlc-roadmap` and `roadmap-agent` where applicable

### 4. Migrate Active Script Messaging

Update active script/help text examples so they stop using `skill.sdlc-orchestrator` as the default example target:

- `skills/sdlc-evalops/scripts/export-promptfoo.py`
- `skills/sdlc-evalops/scripts/run-promptfoo-eval.py`
- `skills/sdlc-evalops/scripts/run-eval-matrix.py`
- `skills/sdlc-roadmap/scripts/sync.py`

### 5. Migrate Active Roadmap Ownership Metadata

Active roadmap metadata must not point at deleted files.

Update:

- `.ai/roadmap/manifest.json`
- `.ai/roadmap/areas/workflow.sdlc-orchestrator/manifest.json`

Minimum acceptable result:

- `owner_path` no longer references `skills/sdlc-orchestrator`
- The area remains a valid active area for workflow-related roadmap items

### 6. Update Tests

Tests that only prove legacy skill existence should be removed or rewritten.

Required outcomes:

- Delete dedicated `sdlc-orchestrator` skill tests.
- Delete tests that require project-level distributed `sdlc-orchestrator` copies.
- Keep workflow tests that explicitly prove active phases do not route through legacy `sdlc-orchestrator`.
- Preserve EvalOps runner/export behavior coverage by targeting an active target such as `skill.sdlc-evalops`.

## Acceptance Criteria

- No active repository path under `skills/`, `tests/`, `.ai/evals/`, or active `.ai/roadmap/*.json` requires `skills/sdlc-orchestrator/` to exist.
- `skills/sdlc-orchestrator/` and its project-level distributed copies are deleted.
- `.ai/evals/manifest.yaml` no longer registers `skill.sdlc-orchestrator`.
- `.ai/evals/targets/skill.sdlc-orchestrator/` no longer exists.
- Active skill docs describe `dev-orchestrator` and `workflow.py` as the current orchestration/governance owners where appropriate.
- Active roadmap metadata no longer points at deleted `skills/sdlc-orchestrator` paths.
- Active EvalOps runner/export tests still prove behavior against a live target.
- `tests/test_workflow.py` still proves default phases do not route through legacy `sdlc-orchestrator`.
- Historical archive/spec/design files may still mention `sdlc-orchestrator` without blocking completion.

## Verification Expectations

The execution plan must include:

- Repository searches limited to active paths.
- Focused pytest runs for modified test modules.
- EvalOps export freshness check against an active target.
- EvalOps matrix dry-run against an active target.
- Roadmap validation after metadata updates.

## Review Questions

1. Should the roadmap workflow area keep the id `workflow.sdlc-orchestrator` for continuity, or should that rename happen in a separate change?
2. Should `agent.dev-orchestrator` gain new golden cases later, or should that remain out of scope for this retirement cleanup?
3. Are there any user-level global `sdlc-orchestrator` skill copies that need follow-up cleanup outside this repository change?
