# Lifecycle Hardening And Derived Sync Spec

## Purpose

Harden the SDLC lifecycle around review execution, controlled file deletion, derived-artifact synchronization, and handoff integrity.

The change should reduce false workflow blockers, keep executable verification available to `review-agent`, move distributed-drift enforcement to the finishing phase, and make cross-target synchronization a deterministic repository capability instead of a remembered operator ritual.

## Context

The repository now uses `dev-orchestrator` plus specialized agent prompts under `agents/` to drive governed SDLC flow. Workflow state is owned by `.ai/workflows/scripts/workflow.py`, while canonical source content is distributed to project-level targets under `.opencode/`, `.claude/`, and `.cursor/`.

Recent cleanup removed `test-agent` from the default lifecycle. That work exposed several follow-up weaknesses:

- `review-agent` permissions appear to allow `pytest`, `git status`, and verification scripts, but runtime behavior has still blocked those commands in some review sessions.
- Agents performing bounded cleanup work sometimes need to delete repository files, but current permission ergonomics encourage ad hoc helper scripts or awkward workarounds.
- Distributed drift checks are valuable, but they create unnecessary churn when enforced during implementation or review rather than at final closure.
- Derived synchronization behavior is spread across multiple scripts and conventions, which makes it easy to forget one of the required checks or fix-up commands.
- Handoff artifacts can be copied into workflow history even when their metadata does not clearly match the active run context.

The repository already contains partial mechanisms for these areas:

- `agents/review-agent.md` declares bash allow-rules for `pytest`, `python3 scripts/*`, `python3 skills/*`, and observational git commands.
- `.githooks/pre-commit` already enforces workflow template drift checks and distributed-copy drift checks when the local git hook is installed.
- `skills/sdlc-project-bootstrap/scripts/sync_templates.py` already manages live workflow, canonical template, and project-level distributed workflow-template synchronization.
- `scripts/setup_agents.py` already provides aggregate install + activation checks for project-level agent targets.

This change should harden these pieces into a clearer contract and better lifecycle boundaries.

## Problem

The repository currently has five related operational problems:

1. **Review verification is not reliable enough.**
   `review-agent` is supposed to re-run targeted tests and verification checks, but command execution has been blocked in practice despite prompt-level allow-rules. This weakens review evidence and leaves runtime behavior dependent on permission parser details or stale distributions.

2. **File deletion is operationally awkward.**
   Deleting in-repo files often requires temporary helper scripts because broad `rm` access is unsafe while no repository-scoped safe deletion command exists.

3. **Distributed drift is enforced too early.**
   Derived-copy drift is a closure concern, not a normal implementation or code-review concern. Blocking implementation/review on distributed-copy lag creates workflow noise without improving source correctness.

4. **Derived synchronization is fragmented.**
   Operators must remember multiple commands for workflow templates, agent distribution, and skill distribution checks. This increases omission risk and obscures what “fully synced” means.

5. **Handoff metadata is insufficiently guarded.**
   Workflow history copies can preserve artifacts whose title, run context, phase, or flow type are misleading or inconsistent with the active dispatch context.

## Goals

- Ensure `review-agent` can reliably execute approved verification commands in normal review flow.
- Add a safe, repository-scoped deletion mechanism for agents instead of relying on raw `rm`.
- Move distributed-drift enforcement out of `implement-agent` and `review-agent` default completion gates.
- Make `finish-agent` the default owner of derived-artifact synchronization checks and remediation.
- Provide a single repository entrypoint for derived-artifact check/fix operations.
- Replace scattered derived-artifact check/fix instructions in `AGENTS.md` and canonical subagent prompts with the new aggregate entrypoint wherever the aggregate command applies.
- Cover workflow templates, agents, and all canonical skills under `skills/` in derived-artifact checks.
- Strengthen handoff metadata validation before workflow history copies are accepted as valid evidence.
- Preserve existing source-of-truth boundaries: canonical source files remain authoritative, distributed copies remain derived.

## Non-Goals

- Do not introduce CI in this change.
- Do not include `.ai/memory/`, EvalOps exports, research artifacts, or other runtime outputs in the first version of derived-artifact synchronization.
- Do not redesign the entire workflow state machine.
- Do not make `review-agent` responsible for broad debugging or implementation repair.
- Do not replace existing workflow-template or agent-setup scripts; instead, compose them behind a clearer aggregate entrypoint.
- Do not weaken pre-commit protections for users who have hooks installed.

## Scope Overview

This change has five workstreams:

1. Review permission hardening and permission-contract tests.
2. Safe repository deletion command and tests.
3. Lifecycle-boundary change so distributed drift is enforced by `finish-agent` rather than earlier workers.
4. Aggregate derived-artifact synchronization check/fix entrypoint.
5. Handoff metadata validation hardening and tests.

## Desired Lifecycle Model

```text
implement-agent
  -> focuses on canonical source changes and executable behavior
  -> does not block by default on distributed-copy drift

review-agent
  -> re-runs approved focused verification commands
  -> validates correctness, test quality, and evidence quality
  -> does not block by default on derived-copy drift

finish-agent
  -> checks derived-artifact synchronization state
  -> fixes or reports distributed drift
  -> performs final closure only when source and derived targets are aligned
```

## Design

### 1. Review Permission Hardening

`review-agent` already declares the intended command allow-list in frontmatter. The hardening work should treat the problem as a **permission resolution contract** issue, not as a missing allow-rule issue.

Required outcomes:

- The permission system must allow command-specific review operations such as:
  - `git status --short --branch`
  - `git diff --stat`
  - `git log --oneline -10`
  - `python3 -m pytest tests/test_workflow.py -v`
  - `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check`
- The catch-all `"*": deny` must be ordered before specific allows, per opencode's last-match-wins semantics; specific allows placed after the catch-all deny are the ones that take effect.
- Review validation should confirm that the distributed `review-agent.md` copies match the canonical prompt when permission-related changes are made.

Implementation direction:

- Add or update tests that assert the catch-all deny is the first bash rule and that specific allows follow it, so the existing deny-first ordering is preserved and protected against accidental reordering.
- Add review-agent-focused contract tests that assert the intended commands are allowed.
- If review commands are blocked at runtime despite correct frontmatter ordering, investigate distributed-copy staleness or runtime version support for last-match-wins semantics rather than reordering the frontmatter.

### 2. Safe Repository Deletion

The repository should provide a controlled deletion script, `scripts/safe_delete.py`, as the default deletion path for agents.

Contract:

- Accept repository-relative paths only.
- Reject absolute paths.
- Reject any path that escapes the repository root.
- Reject protected locations such as `.git/` and `.ai/memory/`.
- Default to file deletion only.
- Require explicit `--recursive` for directory deletion.
- Emit structured machine-readable output describing deleted, skipped, and refused paths.

Permission model:

- Agents should use `python3 scripts/safe_delete.py ...` as the normal deletion mechanism.
- Raw `rm` should not become the default automation path.
- If raw `rm` is retained at all, it should be treated as an explicit ask/fallback path rather than the normal workflow mechanism.

### 3. Distributed Drift Responsibility Boundary

Distributed-copy drift should no longer be a default blocker during `implement-agent` or `review-agent` completion for ordinary source changes.

New boundary:

- `implement-agent` owns canonical source changes, focused/full verification, and implementation evidence.
- `review-agent` owns correctness review, test-quality review, and evidence-quality review.
- `finish-agent` owns the final check that derived artifacts are in sync before closure completes.

This means:

- `implement-agent` should not fail by default solely because `.opencode/`, `.claude/`, or `.cursor/` copies have not yet been redistributed.
- `review-agent` should record drift as a closure follow-up only when it matters to finish, not as an apply-change blocker.
- `finish-agent` should run the derived-artifact check and either:
  - fix the drift through approved sync commands, or
  - return a precise blocker explaining which derived target remains out of sync.

### 4. Aggregate Derived-Artifact Sync Entry Point

Add `scripts/sync_derived_artifacts.py` as the repository-level aggregate entrypoint for derived synchronization.

Supported modes:

- `--check`: read-only verification of all supported derived artifacts.
- `--fix`: apply synchronization/fix-up actions using existing repository scripts.
- `--json`: emit structured output for workflow/agent consumption.

First-version coverage:

- Workflow runtime/template synchronization:
  - live `.ai/workflows/` governed files
  - canonical workflow templates under `skills/sdlc-project-bootstrap/templates/`
  - project-level distributed workflow templates under `.opencode/`, `.claude/`, `.cursor/`
- Agents:
  - canonical prompts under `agents/`
  - project-level distributed agent copies under `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`
  - activation drift for model/variant frontmatter
- Skills:
  - all canonical skill directories under `skills/`
  - corresponding project-level distributed copies under `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`

Excluded from first version:

- `.ai/memory/`
- EvalOps exports and generated eval outputs
- research artifacts
- workflow run history
- other ephemeral runtime outputs

The script should compose existing mechanisms rather than reimplement them. Expected dependencies include:

- `skills/sdlc-project-bootstrap/scripts/sync_templates.py`
- `scripts/setup_agents.py`
- existing skill distribution verification logic under `skills/meta-skill-lifecycle-governance/scripts/`

Instruction migration requirement:

- When the aggregate entrypoint is available, repository instructions should stop requiring agents to remember separate workflow-template, agent, or skill distribution command sequences for the same closure check.
- `AGENTS.md` and canonical subagent prompts should be updated so the aggregate command becomes the primary documented entrypoint for derived-artifact check/fix flows.
- Legacy lower-level commands may still be documented as implementation details or specialized escape hatches, but they should no longer be the default operator guidance where the aggregate command applies.

### 5. Handoff Metadata Validation

Workflow handoff acceptance should enforce tighter alignment between agent result envelopes, handoff markdown metadata, and active workflow context.

Required validations:

- `agent_result.agent` matches the dispatched canonical agent.
- `agent_result.phase` matches the active phase.
- `agent_result.slice_id` matches the active slice.
- `agent_result.flow_type` matches the active run flow type.
- If a handoff markdown file is supplied, its `## Metadata` block must match the same canonical values.

Failure mode:

- Mismatches should block acceptance as a workflow artifact instead of silently writing misleading history copies.
- The blocker should state exactly which metadata field mismatched and what the expected value was.

History-copy behavior:

- Only validated handoff artifacts should be copied into `handoffs/<slice>/history/`.
- Related-but-not-primary artifacts should not masquerade as the current run handoff.

## Required Repository Changes

The implementation plan should inspect and update these areas:

1. Permission parsing or normalization code and its tests.
2. `agents/review-agent.md` and distributed copies if command patterns or documentation must be tightened.
3. New `scripts/safe_delete.py` plus its focused tests.
4. `agents/implement-agent.md`, `agents/review-agent.md`, and `agents/finish-agent.md` so derived-drift responsibilities are explicit.
5. Workflow logic and/or wrapper-contract logic that decides whether distributed drift is an apply-change blocker or a finish-phase blocker.
6. New `scripts/sync_derived_artifacts.py` and tests.
7. Existing sync/distribution scripts only as needed to support aggregate check/fix composition.
8. Workflow handoff validation logic and tests.
9. `AGENTS.md` and canonical subagent prompts so scattered derived-artifact check/fix instructions are replaced or demoted in favor of the aggregate entrypoint.

## Acceptance Criteria

- Review permission tests prove that specific approved commands remain executable for `review-agent` even when wildcard deny rules are present.
- `review-agent` can re-run targeted `pytest`, workflow check, and observational git commands through the intended permission path.
- The repository contains a safe deletion script for repository-scoped file removal, with tests for allowed and refused cases.
- Ordinary `implement-agent` and `review-agent` completion no longer block by default on distributed-copy drift.
- `finish-agent` is the default owner of derived-artifact drift checks before final closure.
- The repository contains a single aggregate derived-artifact entrypoint with `--check` and `--fix` modes.
- `AGENTS.md` and relevant canonical subagent prompts no longer require agents to remember separate workflow-template, agent, or skill distribution command sequences where the aggregate derived-artifact entrypoint applies.
- Aggregate derived checks cover workflow templates, agents, and all canonical skills under `skills/` plus their project-level distributed copies.
- First-version derived checks explicitly exclude `.ai/memory/`, EvalOps exports, research artifacts, and other runtime outputs.
- Handoff metadata mismatches are detected and rejected before history copies are written.
- Distributed agent and skill copies reflect the updated aggregate-entrypoint instructions after redistribution.
- Tests cover permission resolution, safe deletion, lifecycle-boundary behavior, aggregate derived checks, and handoff metadata validation.

## Verification Expectations

The implementation plan should include focused verification for:

- permission-resolution behavior
- `review-agent` command allowance contracts
- `safe_delete.py`
- aggregate derived-artifact check/fix behavior
- workflow handoff metadata validation
- existing sync/distribution regression tests that remain relevant

## Review Questions

1. Should `scripts/sync_derived_artifacts.py --fix` stop at the first failing category or attempt all categories and return a combined report?
2. Should skill distribution checks cover all canonical skills unconditionally, or support a future optimization to scope by changed skills when used outside finish flow?
3. Should raw `rm` remain available as an ask-only escape hatch, or should the repository require `safe_delete.py` exclusively for agent-driven deletion?
4. Should handoff metadata validation inspect only structured `## Metadata` sections, or also guard against misleading top-level titles when titles conflict with metadata?
