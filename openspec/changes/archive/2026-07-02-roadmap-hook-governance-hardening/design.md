## Context

The SDLC workflow runtime already models roadmap-linked OpenSpec work and declares lifecycle hooks in `sdlc-main.yaml`. The post-archive `roadmap_done_if_relevant` hook has runtime validation that observes linked roadmap item state before completion. The earlier lifecycle hooks, `roadmap_status_ready_if_linked` and `roadmap_apply_start_if_ready`, are declared but not yet equivalently validated, so a run can lose a pending hook without proving that the linked roadmap item moved to `ready` or `active`.

Current constraints:
- The workflow runtime owns run state only; roadmap item files remain owned by `sdlc-roadmap`.
- `dev-orchestrator` is a routing and coordination layer, not a domain-state mutation worker.
- Canonical files must be updated first, then synced/distributed: workflow runtime templates via `sync_templates.py`; agent prompts via `scripts/setup_agents.py`.

## Goals / Non-Goals

**Goals:**
- Add a dedicated `roadmap-agent` lifecycle worker for roadmap-governed hooks, with the agent using the existing `sdlc-roadmap` skill for roadmap item mutations.
- Make `idea/planned -> ready`, `ready -> active`, and `active -> done` transitions observable and enforceable from workflow hook completion.
- Keep `dev-orchestrator` within its routing-only boundary while making roadmap-governed routes explicit.
- Add focused runtime and prompt/contract tests that fail before the hardening and pass after it.

**Non-Goals:**
- Do not introduce a separate roadmap domain implementation outside the existing `sdlc-roadmap` skill.
- Do not make `workflow.py` directly edit roadmap item files.
- Do not redesign the roadmap data model or add new workflow phases beyond the existing declared phases/hooks.
- Do not broaden unrelated OpenSpec, EvalOps, or memory-sync behavior.

## Decisions

### Decision 1: Validate hook completion by re-reading roadmap state

Implement ready/apply-start validation in the same runtime seam as `roadmap_done_if_relevant`: `complete-hook` inspects `evidence.roadmap_link` and the current roadmap item frontmatter before removing the hook. Completion succeeds only when the linked item state matches the expected mutation:
- `roadmap_status_ready_if_linked`: linked item status is `ready`.
- `roadmap_apply_start_if_ready`: linked item status is `active` and `started_at` is non-empty.
- `roadmap_done_if_relevant`: linked item status is `done` and `completed_at` is non-empty (existing behavior retained).

Alternative considered: trust worker output envelopes. Rejected because the requirement is to prove the domain mutation actually happened, not that a worker claimed it happened.

### Decision 2: Introduce `roadmap-agent` as the governed execution boundary

`dev-orchestrator` cannot reliably execute roadmap-governed work through its General Task dispatch path because that path explicitly skips `before-dispatch` and `after-dispatch`, and general tasks "do not affect workflow lifecycle state." Roadmap hooks are lifecycle-affecting work: they must run under workflow dispatch validation, emit structured evidence, and be followed by runtime hook completion. Therefore, add `roadmap-agent` to the lifecycle dispatch model for roadmap hook execution.

The new agent is intentionally thin: it loads and follows the existing `sdlc-roadmap` skill, performs the required roadmap state mutation, writes only workflow artifacts plus domain files owned by `sdlc-roadmap`, and returns a structured evidence envelope. `dev-orchestrator` routes to this agent; it does not mutate roadmap files or complete hooks by hand.

Alternative considered: keep dispatching arbitrary general tasks that use the `sdlc-roadmap` skill. Rejected because general task dispatch bypasses lifecycle hooks and cannot be used as a reliable governed execution path.

### Decision 3: Keep roadmap mutations in `sdlc-roadmap`

The workflow runtime will block with actionable remediation when expected roadmap state is absent. The remediation should route the user/orchestrator to `roadmap-agent`, which invokes `sdlc-roadmap` to perform the transition, then re-run `resolve`/`complete-hook`. The runtime records evidence and hook resolution only after observation.

Alternative considered: directly patch roadmap item frontmatter from `workflow.py`. Rejected because existing specs require domain state to remain domain-owned.

### Decision 4: Prompt changes stay minimal and canonical-first

Update `agents/dev-orchestrator.md` only enough to add `roadmap-agent` to governed hook dispatch and prohibit general-task dispatch for lifecycle-affecting roadmap hooks. Add canonical `agents/roadmap-agent.md` and update distribution/config tests. Update `agents/finish-agent.md` only if it needs to hand off post-archive roadmap hook work to `roadmap-agent`. After canonical updates, distribute agent prompts with `scripts/setup_agents.py`.

Alternative considered: make finish-agent handle all roadmap hooks directly. Rejected because ready/apply-start hooks occur before finishing and need a reusable governed worker.

## Risks / Trade-offs

- Runtime validation may block runs that previously advanced despite stale roadmap state → Mitigation: return explicit `domain_state_mismatch`/`user_decision_required` evidence and remediation commands.
- New agent adds prompt/distribution surface area → Mitigation: keep it thin, require `sdlc-roadmap`, add prompt contract tests, and include it in `VALID_AGENT_NAMES`/phase mapping only for roadmap hook phases.
- Template/prompt drift can reintroduce the bug in bootstrapped projects → Mitigation: include template sync/distribution commands and checks in the implementation plan.
