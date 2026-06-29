# Review-Agent Handoff

## Metadata
- Run ID: 2026-06-29-subagent-consistency-audit
- Slice ID: default
- Agent: review-agent
- Phase: apply_change
- Flow Type: lightweight-flow
- Status: success
- Recommended Next Agent: complete_phase

## Objective
Perform final review of the worker-agent prompt normalization, confirm plan alignment and scope boundaries, and run bounded completion verification.

## Work Completed
- Confirmed test-agent evidence exists and reports `verification_passed: true`.
- Reviewed the approved plan plus plan/implement/test handoffs.
- Inspected canonical worker prompts and the related wrapper-contract tests.
- Verified review-agent success routing now uses `complete_phase`.
- Verified no runtime/path-layout migration was performed as part of this slice.
- Reran bounded completion verification with the repository test suite.

## Files/Artifacts Changed
- Wrote `.ai/workflows/runs/2026-06-29-subagent-consistency-audit/handoffs/default/review-agent.md`
- Wrote `.ai/workflows/runs/2026-06-29-subagent-consistency-audit/logs/default/review-agent/static-review-checks.log`
- Wrote `.ai/workflows/runs/2026-06-29-subagent-consistency-audit/logs/default/review-agent/pytest-tests-q-short.log`

## Commands Run
- `git diff --name-only -- agents/implement-agent.md agents/test-agent.md agents/review-agent.md agents/finish-agent.md tests/test_wrapper_contracts.py .opencode/agents/implement-agent.md .opencode/agents/test-agent.md .opencode/agents/review-agent.md .opencode/agents/finish-agent.md .claude/agents/implement-agent.md .claude/agents/test-agent.md .claude/agents/review-agent.md .claude/agents/finish-agent.md .cursor/agents/implement-agent.md .cursor/agents/test-agent.md .cursor/agents/review-agent.md .cursor/agents/finish-agent.md .opencode/agents/.agent-install.json .claude/agents/.agent-install.json .cursor/agents/.agent-install.json`
- stale-pattern checks across canonical worker prompts
- distributed copy parity check across `agents/`, `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`
- `python3 -m pytest tests/ -q --tb=short`

## Evidence Summary
- Reviewed scope matches the prompt-contract audit: canonical worker prompts plus related prompt-contract tests; no workflow runtime files were modified.
- No stale worker-agent routing/runtime/provider strings remain in the four canonical worker prompts.
- review-agent success routing now aligns to `complete_phase`.
- Permission/routing/provider-abstraction/evidence-envelope/handoff requirements are coherent across implement/test/review/finish prompts.
- Distributed worker-agent copies match canonical worker prompts byte-for-byte.
- Completion verification passed: `794 passed, 37 subtests passed`.

## Blockers
- none

## Assumptions
- Repository policy requiring agent redistribution after canonical agent edits remains intentional even though the original plan deferred broader distributed-copy work.
- Workflow run artifacts under `.ai/workflows/runs/` are operational byproducts, not part of the reviewed product-scope change.

## Risks/Follow-Ups
- `tests/test_wrapper_contracts.py` still contains some pre-existing legacy helper/remediation vocabulary outside the four worker-prompt surface; that broader cleanup remains separate from this slice.

## Raw Logs
- `.ai/workflows/runs/2026-06-29-subagent-consistency-audit/logs/default/review-agent/static-review-checks.log`
- `.ai/workflows/runs/2026-06-29-subagent-consistency-audit/logs/default/review-agent/pytest-tests-q-short.log`
