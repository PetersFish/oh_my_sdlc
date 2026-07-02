# Roadmap Hook Governance Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make roadmap-governed SDLC runs reliably execute and validate linked roadmap item transitions before completing ready/apply-start/done hooks.

**Architecture:** Introduce a thin `roadmap-agent` lifecycle subagent. `dev-orchestrator` cannot use General Task dispatch for roadmap-governed hooks because that path skips `before-dispatch`/`after-dispatch` and explicitly does not affect workflow lifecycle state. The new `roadmap-agent` is the governed execution boundary and uses the existing `sdlc-roadmap` skill for all roadmap domain mutations; `workflow.py` remains the verifier that observes actual roadmap frontmatter state before hook completion.

**Tech Stack:** Python workflow CLI, YAML workflow definitions, Markdown agent prompts, `sdlc-roadmap` skill, OpenSpec change artifacts, pytest/unittest tests.

---

## Architecture Re-Evaluation

### Option A — Keep `sdlc-roadmap` via General Task dispatch

- **Pros:** Fewer new files; preserves the earlier “no new agent” direction.
- **Cons:** Not reliable for governed hooks. `agents/dev-orchestrator.md` says General Task dispatch skips `before-dispatch` and `after-dispatch`, and those tasks “do not affect workflow lifecycle state.” Roadmap ready/apply-start/done hooks are lifecycle-affecting work, so executing them as arbitrary general tasks would bypass the workflow evidence gate that this change is trying to harden.
- **Decision:** Do not use this as the governed execution path.

### Option B — Add `roadmap-agent`, backed by `sdlc-roadmap` (**Recommended**)

- **Pros:** Makes roadmap hook execution a first-class lifecycle dispatch with `before-dispatch`, structured result envelopes, `after-dispatch`, and runtime hook validation. Keeps domain logic in `sdlc-roadmap` instead of duplicating it.
- **Cons:** Adds one canonical agent prompt plus distribution/config tests.
- **Decision:** Implement this. It is the smallest reliable architecture that satisfies the user’s optimization goal.

## Files To Touch

- Create: `agents/roadmap-agent.md` — thin lifecycle worker for roadmap hooks; loads `sdlc-roadmap` and returns the standard evidence envelope.
- Modify: `agents/dev-orchestrator.md` — dispatch pending roadmap hooks to `roadmap-agent` through lifecycle dispatch, never General Task dispatch.
- Maybe modify: `agents/finish-agent.md` — only to hand off post-archive roadmap hook execution to `roadmap-agent` if current finish-agent flow would otherwise mutate roadmap directly.
- Modify: `.ai/workflows/scripts/workflow.py` — add `roadmap-agent` to valid agent names/phase mapping and add ready/apply-start hook validation.
- Maybe modify: `.ai/workflows/definitions/sdlc-main.yaml` — only if hook declarations are missing or mis-phased.
- Modify via sync: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` and maybe `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml`.
- Modify distributed agent copies via `scripts/setup_agents.py`.
- Modify tests: `tests/test_workflow.py`, `tests/test_wrapper_contracts.py`, `tests/test_sdlc_orchestrator.py`, and agent distribution/config tests if they enumerate canonical agents.

## TDD Implementation Order

### Task 1: Prove General Task Dispatch Is Not Valid for Governed Roadmap Hooks

**Files:**
- Modify: `tests/test_wrapper_contracts.py` or `tests/test_sdlc_orchestrator.py`

- [ ] Add a failing prompt/contract test asserting `dev-orchestrator` states that roadmap lifecycle hooks MUST NOT use General Task dispatch because it skips workflow dispatch hooks.
- [ ] Add a failing test asserting `dev-orchestrator` maps `roadmap_status_ready_if_linked`, `roadmap_apply_start_if_ready`, and `roadmap_done_if_relevant` to `roadmap-agent`.
- [ ] Add a failing test asserting `roadmap-agent` is present in the canonical agent set/distribution expectations.

Expected failure before implementation: no `roadmap-agent` exists, and `dev-orchestrator` has only general task guidance for arbitrary agents.

Verification command: `python3 -m pytest tests/test_wrapper_contracts.py tests/test_sdlc_orchestrator.py -v`

### Task 2: Add the Thin `roadmap-agent`

**Files:**
- Create: `agents/roadmap-agent.md`
- Modify: agent setup/config tests if they enumerate agent files

- [ ] Create `agents/roadmap-agent.md` with `mode: subagent`, minimal permissions, and required skill `sdlc-roadmap`.
- [ ] Define inputs: `workflow_run_id`, `phase`, `hook_name`, `flow_type`, `context.change_id`, `context.roadmap_item_id` when available, and `evidence.roadmap_link`.
- [ ] Define behavior: perform only the requested roadmap transition via `sdlc-roadmap`; do not implement a separate roadmap state machine; return JSON evidence with observed item id/status/timestamps and handoff path.
- [ ] Define write boundary: may write its own workflow artifacts and may allow `sdlc-roadmap` to mutate roadmap-owned files; must not modify source/tests/prompts/configs.

Expected failure before implementation: canonical/distribution tests cannot find `agents/roadmap-agent.md`.

Verification command: `python3 -m pytest tests/test_wrapper_contracts.py tests/test_setup_agents.py tests/test_install_agents.py -v`

### Task 3: Register `roadmap-agent` as a Lifecycle Worker

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `tests/test_workflow.py`

- [ ] Add failing tests that `before-dispatch --agent roadmap-agent` is accepted only in phases where a roadmap hook can be pending (`create_change`, `apply_change`, `post_archive_actions`) and rejected elsewhere.
- [ ] Add `roadmap-agent`/`roadmap_agent` to `VALID_AGENT_NAMES` and `CANONICAL_AGENT_NAMES`.
- [ ] Add `roadmap-agent` to `PHASE_AGENT_MAP` for the roadmap-hook phases only.
- [ ] If `after-dispatch` has agent-specific routing assumptions, add `roadmap-agent` handling that records evidence and returns the next runtime action for hook completion rather than completing unrelated phases.

Expected failure before implementation: `before-dispatch` returns `invalid_agent` or `agent_not_allowed_for_phase`.

Verification command: `python3 -m pytest tests/test_workflow.py -k 'dispatch or roadmap' -v`

### Task 4: Harden Ready and Apply-Start Hook Validation

**Files:**
- Modify: `tests/test_workflow.py`
- Modify: `.ai/workflows/scripts/workflow.py`

- [ ] Add failing tests for `roadmap_status_ready_if_linked`: stale linked item (`idea`/`planned`) keeps hook pending and blocks with `domain_state_mismatch`; observed `ready` completes the hook; no link completes with `no_linked_item`; multiple links block with `user_decision_required`.
- [ ] Add failing tests for `roadmap_apply_start_if_ready`: linked item still `ready` keeps hook pending; observed `active` plus non-empty `started_at` completes the hook; no link and multiple links match the ready-hook behavior.
- [ ] Refactor the existing `roadmap_done_if_relevant` validation path only enough to share linked-item resolution/block/evidence helpers.
- [ ] Implement ready/apply-start validation by re-reading roadmap item frontmatter; never trust worker output alone.

Expected failure before implementation: hooks complete without observed state validation or are unsupported.

Verification command: `python3 -m pytest tests/test_workflow.py::TestRoadmapLifecycleHooks -v`

### Task 5: Update Orchestrator/Finish Prompt Routing

**Files:**
- Modify: `agents/dev-orchestrator.md`
- Maybe modify: `agents/finish-agent.md`
- Modify: prompt contract tests

- [ ] Update `dev-orchestrator` to add a “Roadmap Hook Dispatch” section: pending roadmap hooks dispatch `roadmap-agent` via `before-dispatch`/`after-dispatch`, then call runtime `resolve`/`complete-hook` as appropriate.
- [ ] Explicitly state General Task dispatch is forbidden for lifecycle-affecting roadmap hooks.
- [ ] Update `finish-agent` only if needed so post-archive `roadmap_done_if_relevant` is handed to `roadmap-agent` instead of finish-agent doing roadmap mutation itself.

Expected failure before implementation: prompt tests still find missing roadmap-agent dispatch language.

Verification command: `python3 -m pytest tests/test_wrapper_contracts.py tests/test_sdlc_orchestrator.py -v`

### Task 6: Sync Templates and Distribute Agents

**Files:**
- Modify via commands: workflow template copies and distributed agent copies

- [ ] Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .`.
- [ ] If needed, run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute`.
- [ ] Run agent distribution:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
python3 scripts/setup_agents.py --global --force
```

Verification commands:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed
python3 -m pytest tests/test_setup_agents.py tests/test_install_agents.py -v
```

### Task 7: Final Verification

- [ ] Run `python3 -m pytest tests/test_workflow.py -v`.
- [ ] Run `python3 -m pytest tests/test_wrapper_contracts.py tests/test_sdlc_orchestrator.py -v`.
- [ ] Run `python3 -m pytest tests/test_sdlc_roadmap.py -v`.
- [ ] Run sync checks:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed
```

- [ ] Run `openspec status --change roadmap-hook-governance-hardening`.

## Focused Tests Summary

- General-task prohibition tests for roadmap lifecycle hooks.
- `roadmap-agent` canonical/distribution tests.
- `before-dispatch`/`after-dispatch` tests for `roadmap-agent` lifecycle eligibility.
- Ready hook stale/success/no-link/multiple-link tests.
- Apply-start hook stale/success/no-link/multiple-link tests.
- Prompt contract tests for dev-orchestrator routing-only behavior.

## EvalOps Candidates

- Target: `dev-orchestrator` — routes roadmap lifecycle hooks to `roadmap-agent`, never General Task dispatch.
- Target: `roadmap-agent` — uses `sdlc-roadmap` and returns evidence without duplicating roadmap domain logic.
- Target: `finish-agent` — post-archive roadmap done hook is not claimed complete without runtime validation.
