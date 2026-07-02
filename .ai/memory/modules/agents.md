---
id: agents
type: module
title: Agent Prompts
summary: >-
  Canonical agent prompt definitions for SDLC subagents (plan, implement, test,
  review, finish, roadmap) and the dev-orchestrator. Agent prompts define
  output JSON contracts, failure-mode routing, required skills, and
  lifecycle-phase permissions.
parent_id: root
sync_status: pending_commit
evidence_mode: uncommitted_snapshot
linked_commits: []
linked_specs: []
linked_sessions: ["20260629-202700"]
updated_at: 2026-07-02T11:20:00Z
confidence: high
tags: [agents, prompts, sdlc, subagents, roadmap]
owned_paths: [agents/]
path_hints: [agents/, .opencode/agents/, .claude/agents/, .cursor/agents/]
keywords: [agent, prompt, subagent, sdlc, orchestrator, json-examples]
test_paths: [tests/test_wrapper_contracts.py]
spec_paths: []
---

# Agent Prompts

## Current Understanding

Canonical agent prompts live in `agents/` and define the output contract and
behavior for each SDLC subagent. Each agent prompt references the standardized
evidence envelope, handoff artifact, and raw log conventions. Distributed
copies are maintained under `.opencode/agents/`, `.claude/agents/`, and
`.cursor/agents/`.

Roadmap-governed lifecycle hooks now use a dedicated `roadmap-agent` instead of
going through General Task dispatch. `implement-agent` also uses a stricter
contract: when verification, template sync, or distribution work is still
pending, it must return `blocked` rather than `success` with blockers.

## Evidence

Directory discovery plus change-driven updates (7 canonical agent markdown
files). Prompt bodies include JSON
examples for success, blocked, and failed output shapes to reduce contract
drift during subagent dispatch.

## Key Files

- `agents/dev-orchestrator.md` — primary mode orchestrator, dispatch hooks
- `agents/implement-agent.md` — apply_change phase implementation worker
- `agents/test-agent.md` — independent verification worker
- `agents/review-agent.md` — code review and contract validation worker
- `agents/finish-agent.md` — archive/finish and hook resolution worker
- `agents/plan-agent.md` — create_change phase planning worker
- `agents/roadmap-agent.md` — lifecycle hook worker for roadmap ready/apply-start/done transitions

## Entry Points

- `scripts/install_agents.py` — distributes canonical agents to CLI targets

## Tests

- `tests/test_wrapper_contracts.py` — prompt-contract and frontmatter assertions

## Update Notes

- 2026-06-29: Added blocked/failed JSON examples to implement, review, and finish agent prompts
- 2026-07-02: Added `roadmap-agent`; `dev-orchestrator` routes governed roadmap hooks through lifecycle dispatch; `implement-agent` must return `blocked` instead of `success + blockers` when verification or sync follow-ups remain.
