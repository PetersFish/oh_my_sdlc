# Implement-Agent Handoff

## Metadata
- Agent: implement-agent
- Run: 2026-06-29-subagent-consistency-audit
- Phase: apply_change
- Slice: default
- Flow type: lightweight-flow
- Status: success

## Objective
Implement the approved prompt-contract normalization for the four worker subagents only, plus minimal contract tests and distributed agent-copy refresh.

## Work Completed
- Added focused contract tests for worker-agent bash allowlists, explicit skill allowlists, normalized routing names, real JSON booleans, shared handoff sections, and review/finish contract wording.
- Normalized canonical worker prompts in `agents/implement-agent.md`, `agents/test-agent.md`, `agents/review-agent.md`, and `agents/finish-agent.md`.
- Removed stale worker `workflow.py *` bash allowances and broad `skill: allow` permissions.
- Replaced stale `back_to_*` routing with `dispatch_implement_agent` / `dispatch_plan_agent` where applicable.
- Normalized review-agent success routing to `complete_phase`.
- Replaced provider-specific OpenSpec wording in worker prompts with provider-agnostic wrapper/provider wording.
- Standardized evidence-envelope booleans, `raw_log_paths`, and handoff/raw-log section guidance across the four worker prompts.
- Distributed canonical agent updates to `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`.

## Files/Artifacts Changed
- `tests/test_wrapper_contracts.py`
- `agents/implement-agent.md`
- `agents/test-agent.md`
- `agents/review-agent.md`
- `agents/finish-agent.md`
- `.opencode/agents/implement-agent.md`
- `.opencode/agents/test-agent.md`
- `.opencode/agents/review-agent.md`
- `.opencode/agents/finish-agent.md`
- `.claude/agents/implement-agent.md`
- `.claude/agents/test-agent.md`
- `.claude/agents/review-agent.md`
- `.claude/agents/finish-agent.md`
- `.cursor/agents/implement-agent.md`
- `.cursor/agents/test-agent.md`
- `.cursor/agents/review-agent.md`
- `.cursor/agents/finish-agent.md`
- `.opencode/agents/.agent-install.json`
- `.claude/agents/.agent-install.json`
- `.cursor/agents/.agent-install.json`

## Commands Run
- `python3 -m pytest tests/test_wrapper_contracts.py -k "worker_agents_use_explicit_skill_allowlists or worker_prompts_do_not_use_back_to_routes or review_agent_success_completes_phase or finish_agent_does_not_claim_runtime_hook_ownership or worker_prompts_use_real_json_booleans or worker_prompts_share_normalized_handoff_sections or only_routing_agents_have_workflow_py_bash_allow" -v`
- `python3 scripts/install_agents.py --target ./.opencode/agents --force`
- `python3 scripts/install_agents.py --target ./.claude/agents --force`
- `python3 scripts/install_agents.py --target ./.cursor/agents --force`
- `python3 -m pytest tests/test_wrapper_contracts.py -v`

## Evidence Summary
- Red phase: the new focused wrapper-contract tests failed against stale worker prompts as expected.
- Green phase: the focused prompt-contract tests passed after canonical prompt updates and distribution.
- Broader verification: `tests/test_wrapper_contracts.py` passed in full.
- Scope stayed within worker prompts, direct distributed copies, and the minimal directly-related contract test file.

## Blockers
- none

## Assumptions
- Prompt-contract normalization remains a prompt/test-only change; workflow runtime routing semantics are unchanged in this slice.
- Distributed agent copies should mirror canonical prompt files immediately after canonical edits.

## Risks/Follow-Ups
- `skills/_lib/wrapper_contracts.py` and workflow runtime tests still contain legacy remediation vocabulary in some helper/test paths; that broader runtime alignment remains out of scope for this change.
- Future run-directory or runtime-path unification should be handled in a separate change as planned.

## Raw Logs
- `.ai/workflows/runs/2026-06-29-subagent-consistency-audit/logs/default/implement-agent/focused-wrapper-contracts.log`
- `.ai/workflows/runs/2026-06-29-subagent-consistency-audit/logs/default/implement-agent/test_wrapper_contracts-full.log`
