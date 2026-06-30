## Metadata
- Agent: implement-agent
- Workflow Run ID: 2026-06-29-subagent-json-examples-followup
- Phase: apply_change
- Flow Type: lightweight-flow
- Slice ID: default
- Status: success

## Objective
Retry the prompt-example follow-up with scope narrowed to only the approved implement/review/finish examples and the minimum contract tests that lock them in place.

## Work Completed
- Reverted prior scope drift in `agents/test-agent.md`, its distributed copies, and overbroad prompt-contract assertions.
- Kept `tests/test_wrapper_contracts.py` limited to the three new prompt-example assertions.
- Ran the focused pytest selection against prompts without the new examples and confirmed the new tests failed.
- Added blocked and failed JSON examples to `agents/implement-agent.md`.
- Added blocked routing JSON examples to `agents/review-agent.md`.
- Added blocked and failed JSON examples to `agents/finish-agent.md`.
- Updated only the matching distributed copies under `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`.
- Re-ran the focused contract/parity pytest selection and confirmed it passed.

## Files/Artifacts Changed
- `tests/test_wrapper_contracts.py`
- `agents/implement-agent.md`
- `agents/review-agent.md`
- `agents/finish-agent.md`
- `.opencode/agents/implement-agent.md`
- `.opencode/agents/review-agent.md`
- `.opencode/agents/finish-agent.md`
- `.claude/agents/implement-agent.md`
- `.claude/agents/review-agent.md`
- `.claude/agents/finish-agent.md`
- `.cursor/agents/implement-agent.md`
- `.cursor/agents/review-agent.md`
- `.cursor/agents/finish-agent.md`

## Commands Run
- `python3 -m pytest tests/test_wrapper_contracts.py -k "implement_agent_includes_blocked_and_failed_examples or review_agent_includes_blocked_routing_examples or finish_agent_includes_blocked_and_failed_examples" -v`
- `python3 -m pytest tests/test_wrapper_contracts.py -k "implement_agent_includes_blocked_and_failed_examples or review_agent_includes_blocked_routing_examples or finish_agent_includes_blocked_and_failed_examples or claude_cursor_copies_match_opencode" -v`

## Evidence Summary
- Red phase observed: the three new prompt-contract tests failed before the prompt examples were re-added.
- Green phase observed: the three new prompt-contract tests plus parity coverage passed after the minimal prompt edits.
- Final diff is limited to the three intended canonical agent prompts, their distributed copies, and the focused test file.

## Blockers
- None.

## Assumptions
- Static string assertions are sufficient because the subject under test is prompt/documentation contract text.
- Existing workflow-run artifacts outside this slice remain runtime state and were left untouched.

## Risks/Follow-Ups
- The distributed copies were updated manually to avoid unrelated churn; future broader agent-contract changes should use a dedicated distribution pass when scope allows it.

## Raw Logs
- `.ai/workflows/runs/2026-06-29-subagent-json-examples-followup/logs/default/implement-agent/red-prompt-contract-tests.log`
- `.ai/workflows/runs/2026-06-29-subagent-json-examples-followup/logs/default/implement-agent/green-prompt-contract-tests.log`
