# Worker Subagent Failure Example Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the smallest prompt-contract follow-up that gives `implement-agent`, `review-agent`, and `finish-agent` explicit non-success JSON examples where success-only examples currently leave blocked/failed output shape ambiguous.

**Architecture:** Treat `agents/test-agent.md` as the clarity baseline for failure examples, but keep this follow-up tightly scoped to prompt examples plus only the minimum prompt-contract tests needed to lock the added examples in place. Preserve all existing routing semantics; only document them more concretely.

**Tech Stack:** Markdown agent prompts, distributed agent copies generated from canonical `agents/`, pytest static contract checks in `tests/test_wrapper_contracts.py`.

---

## Scope

### In scope
- `agents/implement-agent.md`
- `agents/review-agent.md`
- `agents/finish-agent.md`
- corresponding distributed copies under `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`
- `tests/test_wrapper_contracts.py` only if needed to lock the new prompt-contract examples

### Out of scope
- reopening the broader subagent consistency change
- workflow runtime changes
- prompt rewrites outside the added failure/blocked examples and the smallest surrounding text needed to reference them

## Decision Summary

### `implement-agent.md` should gain **both** blocked and failed examples
Why:
- it currently shows only success even though its prompt already documents blocker-style outcomes (`missing_change_id`, plan/design uncertainty) and terminal error-style outcomes (`artifact_generation_failed` / wrapper-apply failure)
- without both examples, implement workers can drift on whether a non-success result should reroute for replanning vs surface as an unrecoverable failure

Recommended additions:
1. **Blocked example** — requirement/design or workflow-context issue that cannot be resolved inside the slice, with `recommended_next_action` aligned to either `dispatch_plan_agent` or `fix_workflow_context` depending on the specific scenario chosen during edit
2. **Failed example** — unrecoverable wrapper/artifact-generation failure with `recommended_next_action: "surface_error"`

### `review-agent.md` should gain **blocked-only** examples
Why:
- its documented non-success paths are all blockers: missing verification evidence, executable review findings, completion verification failure, or design ambiguity revealed by review
- the prompt does not currently define any distinct terminal `failed` route, so adding one would broaden the contract instead of clarifying it

Recommended additions:
1. **Blocked example to implement-agent** — executable issue found during review or completion verification, with `recommended_next_action: "dispatch_implement_agent"`
2. **Blocked example to plan-agent** — requirement/design ambiguity exposed by review, with `recommended_next_action: "dispatch_plan_agent"`

### `finish-agent.md` should gain **both** blocked and failed examples
Why:
- its failure table already mixes retryable/precondition blockers (`missing_verification_evidence`, `hook_blocked`, `item_not_found`) with a terminal finish/archive error (`archive_failed`)
- success-only JSON leaves too much room for workers to collapse all non-success outcomes into a single status

Recommended additions:
1. **Blocked example** — precondition or hook-resolution blocker, preferably `missing_verification_evidence` or `hook_blocked`
2. **Failed example** — archive/finish execution failure with `recommended_next_action: "surface_error"`

## Minimal Test Strategy

A small static contract test update is recommended because this change is documentation-contract hardening, not runtime behavior work.

Add focused assertions in `tests/test_wrapper_contracts.py` that the canonical prompt bodies contain the new example statuses/routes:
- `implement-agent`: contains at least one blocked example and one failed example
- `review-agent`: contains blocked examples for both implement reroute and plan escalation, and no new success-route drift
- `finish-agent`: contains at least one blocked example and one failed example

These are acceptable string-level tests because the subject under test is static prompt content, not executable business behavior.

## Implementation Order (TDD-aware)

### Task 1: Lock the missing prompt-contract examples with failing static tests
**Files:**
- Modify: `tests/test_wrapper_contracts.py`
- Reads for reference: `agents/test-agent.md`, `agents/implement-agent.md`, `agents/review-agent.md`, `agents/finish-agent.md`

**Test cases to add**
- `test_implement_agent_includes_blocked_and_failed_examples`
  - Verifies `implement-agent` prompt body includes both non-success example types
  - Expected failure before implementation: only success JSON is present
- `test_review_agent_includes_blocked_routing_examples`
  - Verifies `review-agent` prompt body includes blocked routing examples for both `dispatch_implement_agent` and `dispatch_plan_agent`
  - Expected failure before implementation: review prompt contains only success JSON example
- `test_finish_agent_includes_blocked_and_failed_examples`
  - Verifies `finish-agent` prompt body includes both blocked and failed example types
  - Expected failure before implementation: finish prompt contains only success JSON example

**Verification command**
- `python3 -m pytest tests/test_wrapper_contracts.py -k "blocked_and_failed_examples or blocked_routing_examples" -v`

### Task 2: Add the smallest canonical prompt examples in `agents/implement-agent.md`
**Files:**
- Modify: `agents/implement-agent.md`

**Implementation details**
- insert one blocked JSON example after the existing success example
- insert one failed JSON example after the blocked example
- keep surrounding edits minimal: only enough label text to distinguish when blocked vs failed should be used
- ensure `recommended_next_action` matches the scenario chosen and stays consistent with existing failure-mode language

**Verification target**
- `test_implement_agent_includes_blocked_and_failed_examples`

### Task 3: Add blocked routing examples in `agents/review-agent.md`
**Files:**
- Modify: `agents/review-agent.md`

**Implementation details**
- keep the existing success example unchanged except for any tiny cross-reference needed
- add two blocked examples mirroring `test-agent` clarity:
  - executable issue → `dispatch_implement_agent`
  - requirement/design ambiguity → `dispatch_plan_agent`
- do not invent a new `failed` contract for review-agent

**Verification target**
- `test_review_agent_includes_blocked_routing_examples`

### Task 4: Add blocked and failed examples in `agents/finish-agent.md`
**Files:**
- Modify: `agents/finish-agent.md`

**Implementation details**
- add one blocked example for a precondition/hook blocker
- add one failed example for `archive_failed`
- keep phase wording valid for both `archive_change` and `post_archive_actions`

**Verification target**
- `test_finish_agent_includes_blocked_and_failed_examples`

### Task 5: Distribute canonical agent changes and rerun focused contract checks
**Files:**
- Regenerate: `.opencode/agents/implement-agent.md`, `.opencode/agents/review-agent.md`, `.opencode/agents/finish-agent.md`
- Regenerate: `.claude/agents/implement-agent.md`, `.claude/agents/review-agent.md`, `.claude/agents/finish-agent.md`
- Regenerate: `.cursor/agents/implement-agent.md`, `.cursor/agents/review-agent.md`, `.cursor/agents/finish-agent.md`
- Possibly updated metadata: `.opencode/agents/.agent-install.json`, `.claude/agents/.agent-install.json`, `.cursor/agents/.agent-install.json`

**Commands**
- `python3 scripts/install_agents.py --target ./.opencode/agents --force`
- `python3 scripts/install_agents.py --target ./.claude/agents --force`
- `python3 scripts/install_agents.py --target ./.cursor/agents --force`
- `python3 -m pytest tests/test_wrapper_contracts.py -k "implement_agent_includes_blocked_and_failed_examples or review_agent_includes_blocked_routing_examples or finish_agent_includes_blocked_and_failed_examples or claude_cursor_copies_match_opencode" -v`

## Focused Verification Plan

### Exact commands
1. `python3 -m pytest tests/test_wrapper_contracts.py -k "implement_agent_includes_blocked_and_failed_examples or review_agent_includes_blocked_routing_examples or finish_agent_includes_blocked_and_failed_examples" -v`
2. `python3 -m pytest tests/test_wrapper_contracts.py -k "claude_cursor_copies_match_opencode" -v`

### Expected red/green sequence
- **Red first:** the new static tests fail because the three canonical prompts currently contain success-only JSON examples
- **Green after edits/distribution:** the new tests pass and distributed-copy parity remains intact

## EvalOps Candidates
- None. This is prompt-contract documentation hardening, not an AI behavior target change under `.ai/evals/`.

## Risks / Follow-ups
- Keep example field names aligned with existing prompt text; do not accidentally introduce a new evidence schema while adding examples.
- If existing tests already cover these exact strings elsewhere, prefer extending those tests instead of duplicating assertions.
- If distributed copies are intentionally left out by the implementing worker, parity tests will fail; distribution is part of the change, not an optional cleanup.
