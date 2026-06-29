# Plan Agent Handoff

## Metadata
- Agent: plan-agent
- Workflow Run ID: 2026-06-29-subagent-json-examples-followup
- Phase: create_change
- Flow Type: lightweight-flow
- Slice ID: default
- Status: success

## Objective
Plan a very small follow-up change that adds missing failed/blocked JSON examples to worker subagent prompts where success-only examples create contract drift risk, limited to implement/review/finish agents and only the minimum supporting tests if needed.

## Work Completed
- Reviewed canonical `test-agent` failure-example baseline.
- Inspected `agents/implement-agent.md`, `agents/review-agent.md`, and `agents/finish-agent.md` to identify current success-only example gaps.
- Inspected `tests/test_wrapper_contracts.py` to determine the smallest viable prompt-contract lock.
- Produced a minimal implementation plan with per-agent blocked/failed decisions and focused verification commands.
- Wrote durable artifacts for this workflow run.

## Files/Artifacts Changed
- `.ai/workflows/runs/2026-06-29-subagent-json-examples-followup/plans/default/plan.md`
- `.ai/workflows/runs/2026-06-29-subagent-json-examples-followup/handoffs/default/plan-agent.md`

## Commands Run (none)
- None

## Evidence Summary
- `implement-agent` should gain both blocked and failed examples.
- `review-agent` should gain blocked-only examples, with separate implement-route and plan-route variants.
- `finish-agent` should gain both blocked and failed examples.
- A small `tests/test_wrapper_contracts.py` update is recommended to lock the prompt contract without reopening the larger change.

## Blockers
- None

## Assumptions
- The implementing worker will keep the scope limited to prompt examples and the smallest adjacent wording needed for clarity.
- Static prompt-content assertions are acceptable because the subject is documentation/prompt contract text.

## Risks/Follow-Ups
- Avoid inventing new evidence keys while adding examples.
- Distributed agent copies must be regenerated after canonical edits.

## Raw Logs (none)
- None
