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
sync_status: synced
evidence_mode: commit
linked_commits: ["ab70b4f087524f9a1344fd561f8ae4c5b2653c09", "171d4a8c6e20f59618c4b0c91d5fb1c3e5eb7967", "c42b21151f443a5271c3bc18799d14c8f18e33c2", "4628303f404cddab2ededf1adfae61bdd18ff431", "b39987940396746093b243fbe6789115c2cfd12f", "ab06a0287f43ec7e50b280ce1bddd2cdc39d3aad", "b368a7f731ea3cf734827fee0b5484b72eb9319b"]
linked_specs: ["2026-07-05-review-agent-live-diff-and-implement-verification-contract"]
linked_sessions: ["20260629-202700", "20260705-lifecycle-hardening-and-derived-sync", "2026-07-05-review-agent-live-diff-and-implement-verification-contract", "2026-07-05-review-agent-worktree-mode-git-c-hardening", "2026-07-05-roadmap-agent-primary-subject-gating", "2026-07-05-subagent-owned-post-archive-cleanup", "2026-07-09-workflow-runtime-execution-context-and-agent-result-integrity", "2026-07-11-workflow-final-tail-commit"]
updated_at: 2026-07-11T00:00:00Z
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
- 2026-07-05: Lifecycle hardening — added `safe_delete.py` allow-rules to implement-agent and finish-agent; moved derived-drift ownership to finish-agent with Derived Artifact Sync section; implement-agent no longer treats distributed-copy drift as a default apply-change blocker; review-agent flags derived drift as a finish follow-up; permission-contract ordering locked via deny-first bash rules.
- 2026-07-05: Review live diff and verification contract — implement-agent now required to deliver changed_files, worktree_path, diff_commands, verification_commands in success output; dev-orchestrator forwards implement-agent change-set and verification evidence to review-agent dispatch; review-agent establishes live Git change set before CodeGraph, inspects implement-agent verification evidence, only re-runs tests under explicit exception conditions; added 33 prompt-contract tests for new protocols.
- 2026-07-05: Review-agent worktree-mode Git-C hardening — added 7 `git -C * <subcmd>` read-only bash allow rules (status, diff, log, ls-files, check-ignore, rev-parse, branch); added Worktree-Mode Live Change Review Protocol section requiring explicit worktree path as source of truth, `git -C <worktree_path>` for live inspection, no shell cwd dependency, and blockers for missing/invalid worktree context; added 10 static permission+protocol tests; plain Git commands preserved for main-checkout mode.
- 2026-07-05: Roadmap-agent primary-subject gating — dev-orchestrator now enforces that roadmap-agent dispatch and roadmap lifecycle hooks (ready, apply-start, done) are gated on `primary_subject.type == "roadmap_item"`; non-roadmap-item runs (e.g., spec_change) skip roadmap hooks and return `blocked` with reason `roadmap_not_enabled` if roadmap-agent dispatch is attempted; added primary-subject gating documentation to dev-orchestrator prompt; workflow.py implements `_roadmap_agent_enabled()` and `_is_roadmap_hook()` runtime helpers for the gate.
- 2026-07-05: Subagent-owned post-archive cleanup — finish-agent contract now separates archive_change (finish/spec-wrapper) from post_archive_actions (cleanup/memory/roadmap/drift sync); finish-agent success in post_archive_actions is blocked when positive cleanup evidence keys (`memory_sync_done`, `roadmap_done_checked`, `derived_artifacts_synced`, `cleanup_complete`) are present but not `True`; dev-orchestrator updated to reflect the post_archive_actions as finish-agent-owned subagent phase separate from archive_change; added `POSITIVE_CLEANUP_EVIDENCE_KEYS` and validation in both `cmd_after_dispatch` and `cmd_complete_phase`.
- 2026-07-09: Workflow runtime execution context and agent result integrity — dev-orchestrator now assembles a mandatory runtime context block with execution_mode, change_id, primary_design_path, design_artifact_paths, and subject_type/id; agents (implement, review, finish) now require runtime context in their contracts and must return `missing_runtime_context` when absent; after-dispatch validates result_contract keys (`verification_passed`, `review_complete`, `review_blockers`); workflow.py added `_MAIN_CHECKOUT_AGENTS`, `_assemble_runtime_context()`, `cmd_ensure_context()`, and `cmd_after_dispatch()` with `result_contract` storage; superpowers_direct policy now creates no run; tests expanded to 81 tests covering runtime context assembly, result contract validation, and agent contract compliance.
- 2026-07-11: Final tail commit protocol — dev-orchestrator now includes a "Final Tail Commit Protocol" section requiring it to capture the active `run_id` before advancing to `done`, call `workflow.py final-commit --run-id <run_id> --push` after the run reaches done, and report `git status --short` plus `residual_dirty_paths`; direct `git add`/`git commit`/`git push` for final governance artifact publishing is now forbidden; workflow.py gained `cmd_final_commit` with an allowlist-scoped stager (history run dir, current.json, .ai/roadmap/, .ai/memory/, openspec/changes/archive/, docs/superpowers/archive/) that commits only allowlisted paths and leaves unrelated dirty files unstaged.
