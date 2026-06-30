# SDLC Subagent Consistency Audit Implementation Plan

> **For agentic workers:** This is a planning artifact only. Execute later with a bounded implementation worker; do not modify workflow runtime or unrelated repository files while applying this plan.

**Goal:** Align `implement-agent`, `test-agent`, `review-agent`, and `finish-agent` with the tightened `dev-orchestrator` / `plan-agent` contract so downstream routing, permissions, evidence envelopes, and handoff artifacts are consistent.

**Architecture:** Treat `agents/dev-orchestrator.md`, `agents/plan-agent.md`, and the current workflow runtime behavior as the contract baseline. Update only canonical subagent prompts in `agents/` and keep workflow state ownership, provider dispatch, and user-facing routing in `dev-orchestrator`.

**Tech Stack:** Markdown agent prompts, Python workflow runtime contract awareness, pytest for workflow contract checks, ripgrep/static prompt verification.

---

## Objective
Produce one prompt-alignment change covering the remaining four SDLC worker agents:
- `agents/implement-agent.md`
- `agents/test-agent.md`
- `agents/review-agent.md`
- `agents/finish-agent.md`

The change should normalize role boundaries, permissions, provider abstraction, routing names, evidence envelopes, and handoff/raw-log requirements without broadening workflow runtime scope.

## Decision Summary

### 1) Run-directory unification is deferred from this change
There is a broader naming question around workflow-run metadata layout and possible unification of per-run files/directories. That is **explicitly deferred** here because:
- this audit is scoped to subagent prompt consistency, not runtime storage migration;
- changing run-directory structure would couple prompt edits to `workflow.py`, tests, and possible backward-compatibility handling;
- the current inconsistency can be addressed safely at the prompt-contract layer first.

**Recommendation:** record run-directory unification as a separate follow-up change after subagent prompts are normalized and verified.

### 2) Prefer `run.json` over `manifest.json`
For any future single-file per-run metadata naming, prefer `run.json` because it is more specific, matches the domain term already used throughout the workflow, and avoids confusion with broader project-level manifests.

### 3) Standardize failure routing names
Normalize worker-agent implementation blockers back to:
- `dispatch_implement_agent`
- `dispatch_plan_agent`

Do not keep mixed `back_to_*` names. The dispatch-style names match orchestrator vocabulary and reduce adapter logic.

## Scope Boundaries

### In scope
- Canonical prompt edits in `agents/implement-agent.md`, `agents/test-agent.md`, `agents/review-agent.md`, `agents/finish-agent.md`
- Prompt examples, routing names, permission allowlists, evidence-envelope schemas, and handoff/raw-log requirements

### Out of scope
- `workflow.py` feature changes unless verification proves existing tests/docs must be updated for wording consistency
- run-directory storage migration or `manifest.json` → `run.json` runtime conversion
- distributed agent copy updates, commits, or archival work

## Target Prompt Policy

### Shared worker-agent norms
Apply these to all four worker prompts:
1. `dev-orchestrator` remains the only workflow-state owner and user-facing routing host.
2. Worker agents perform phase-local technical work only.
3. Output envelopes use real JSON booleans, always include `slice_id`, and use normalized `recommended_next_action` values.
4. Handoff artifacts use the same section set everywhere.
5. Raw logs are either explicit artifact paths or `none`; never vague free text.

## Exact Skill Guidance by Subagent

### implement-agent
- **Keep allow:** `implementation-contract-discipline`, `behavioral-test-design`, `test-driven-development`, `verification-before-completion`, `requesting-code-review`
- **Conditional allow:** `systematic-debugging` only when reproduction/diagnosis is required; `context7-mcp` only when a library/framework contract must be checked; `sdlc-evalops` only if the change touches durable eval assets under `.ai/evals/`
- **Remove:** broad `skill: allow`; `using-git-worktrees`; `executing-plans`; any provider-specific hardcoded skill requirement such as `openspec-apply-change`

### test-agent
- **Keep allow:** `behavioral-test-design`, `verification-before-completion`
- **Conditional allow:** `sdlc-evalops` only for AI-behavior/eval-backed changes; `context7-mcp` only if test verification depends on external library contract lookup
- **Remove:** broad `skill: allow`; any wording that makes EvalOps mandatory for ordinary non-AI verification

### review-agent
- **Keep allow:** `receiving-code-review`, `requesting-code-review`, `verification-before-completion`
- **Conditional allow:** `behavioral-test-design` only if review findings require checking behavioral test quality
- **Remove:** broad `skill: allow`; interactive review flow language that turns the worker into the user-facing review host

### finish-agent
- **Keep allow:** `finishing-a-development-branch`, `verification-before-completion`
- **Conditional allow:** `sdlc-openspec-memory-sync` only when the verified change contract explicitly requires post-verify memory sync before archive; `sdlc-repository-memory-sync` only when finish work explicitly includes repository-memory follow-up
- **Remove:** broad `skill: allow`; provider-specific hardcoded `openspec-archive-change`; any skill wording that implies ownership of workflow runtime hooks

## Exact Bash Allowlist Guidance by Subagent

### implement-agent
- **Keep:** repository-local implementation/test commands needed to edit and verify the targeted change (for example `python3 -m pytest ...`, linters, formatter, package/test runner commands, and read-only git inspection if already part of established repo practice)
- **Remove:** `workflow.py *`; direct workflow runtime commands such as `ensure-run`, `advance`, `complete-hook`; unrelated repo-management commands

### test-agent
- **Keep:** read-only verification commands only, such as targeted `pytest`, `python3 -m pytest`, repo test runners, and static inspection commands like `rg` when needed to support verification evidence
- **Remove:** `workflow.py *`; commands that mutate code, workflow state, or release/archive state

### review-agent
- **Keep:** read-only inspection and validation commands only, such as `git diff --stat`, `git diff -- <path>`, targeted test reruns when needed to validate a review concern, and static inspection commands
- **Remove:** `workflow.py *`; commands for commits, archive actions, or workflow-state mutation

### finish-agent
- **Keep:** only commands genuinely needed for finish/archive evidence collection, such as read-only git status/log inspection and any explicitly sanctioned archive verification command if the existing workflow already requires it
- **Remove:** `workflow.py *` ownership semantics from the prompt; `sync_templates.py` access; unrelated broad filesystem/release permissions

## Evidence Envelope Normalization Targets

### Shared rules
- `status` is one of `success`, `blocked`, or `failed`
- booleans are JSON booleans, never quoted strings
- always include `agent`, `phase`, `slice_id`, and `artifacts`
- `focused_tests` entries always include `command` and `result`
- blocked outputs use actionable blocker reasons and orchestrator-friendly next actions

### Example: implement-agent success
```json
{
  "agent": "implement-agent",
  "status": "success",
  "phase": "apply_change",
  "slice_id": "default",
  "flow_type": "lightweight-flow",
  "evidence": {
    "implementation_complete": true,
    "tests_targeted": true,
    "plan_followed": true,
    "code_summary": {
      "files_changed": [
        "agents/implement-agent.md",
        "agents/test-agent.md"
      ],
      "behavior_changed": "Worker prompt contracts normalized to orchestrator-aligned routing, permissions, and evidence schema"
    },
    "focused_tests": [
      {
        "command": "python3 -m pytest tests/test_workflow.py -v",
        "result": "PASS"
      }
    ]
  },
  "artifacts": {
    "handoff_path": ".ai/workflows/runs/<run_id>/handoffs/default/implement-agent.md",
    "raw_log_paths": []
  },
  "blockers": [],
  "recommended_next_action": "dispatch_test_agent"
}
```

### Example: implement-agent blocked
```json
{
  "agent": "implement-agent",
  "status": "blocked",
  "phase": "apply_change",
  "slice_id": "default",
  "flow_type": "lightweight-flow",
  "evidence": {
    "implementation_complete": false,
    "user_input_required": false,
    "focused_tests": [
      {
        "command": "python3 -m pytest tests/test_workflow.py -v",
        "result": "FAIL - prompt contract expectation mismatch requires replanning"
      }
    ]
  },
  "artifacts": {
    "handoff_path": ".ai/workflows/runs/<run_id>/handoffs/default/implement-agent.md",
    "raw_log_paths": []
  },
  "blockers": [
    {
      "reason": "implementation_replan_required",
      "message": "Existing plan no longer matches verified orchestrator/runtime contract",
      "recommended_action": "dispatch_plan_agent"
    }
  ],
  "recommended_next_action": "dispatch_plan_agent"
}
```

### Example: test-agent blocked to implement
```json
{
  "agent": "test-agent",
  "status": "blocked",
  "phase": "apply_change",
  "slice_id": "default",
  "flow_type": "lightweight-flow",
  "evidence": {
    "verification_complete": false,
    "regression_found": true,
    "focused_tests": [
      {
        "command": "python3 -m pytest tests/test_workflow.py -v",
        "result": "FAIL - review-agent route expectation still points to dispatch_finish_agent"
      }
    ]
  },
  "artifacts": {
    "handoff_path": ".ai/workflows/runs/<run_id>/handoffs/default/test-agent.md",
    "raw_log_paths": []
  },
  "blockers": [
    {
      "reason": "verification_failed",
      "message": "Implementation does not yet satisfy normalized routing contract",
      "recommended_action": "dispatch_implement_agent"
    }
  ],
  "recommended_next_action": "dispatch_implement_agent"
}
```

### Example: review-agent success
```json
{
  "agent": "review-agent",
  "status": "success",
  "phase": "apply_change",
  "slice_id": "default",
  "flow_type": "lightweight-flow",
  "evidence": {
    "review_complete": true,
    "approval_ready": true,
    "major_findings": [],
    "focused_tests": [
      {
        "command": "rg -n \"dispatch_finish_agent|back_to_\" agents/*.md",
        "result": "PASS - no stale routing names in canonical worker prompts"
      }
    ]
  },
  "artifacts": {
    "handoff_path": ".ai/workflows/runs/<run_id>/handoffs/default/review-agent.md",
    "raw_log_paths": []
  },
  "blockers": [],
  "recommended_next_action": "complete_apply_change"
}
```

### Example: finish-agent success
```json
{
  "agent": "finish-agent",
  "status": "success",
  "phase": "archive_change",
  "slice_id": "default",
  "flow_type": "lightweight-flow",
  "evidence": {
    "archive_ready": true,
    "post_archive_actions_complete": true,
    "provider_dispatch_respected": true,
    "focused_tests": [
      {
        "command": "rg -n \"openspec-archive-change|complete-hook|workflow.py \\*\" agents/finish-agent.md",
        "result": "PASS - no stale provider/runtime ownership wording"
      }
    ]
  },
  "artifacts": {
    "handoff_path": ".ai/workflows/runs/<run_id>/handoffs/default/finish-agent.md",
    "raw_log_paths": []
  },
  "blockers": [],
  "recommended_next_action": "complete_archive_change"
}
```

## Exact Handoff / Raw-Log Requirements
Every worker handoff file should contain these sections in this order:
1. `Metadata`
2. `Objective`
3. `Work Completed`
4. `Files/Artifacts Changed`
5. `Commands Run`
6. `Evidence Summary`
7. `Blockers`
8. `Assumptions`
9. `Risks/Follow-Ups`
10. `Raw Logs`

Additional rules:
- `Commands Run` must list executed commands or `none`
- `Raw Logs` must say `none` when there are no logs
- `artifacts.raw_log_paths` must be an array; use `[]` when none exist
- handoff files should mention exact changed prompt files so downstream agents do not need to rediscover scope

## Implementation Sequencing Constraints

### Sequence 1: establish shared contract first
1. Re-read `agents/dev-orchestrator.md`, `agents/plan-agent.md`, and relevant workflow runtime guidance.
2. Lock the shared normalization rules before touching any of the four worker prompts.

### Sequence 2: normalize routing and boundaries before permissions
3. Update role/boundary language in all four worker prompts.
4. Replace stale routing names with `dispatch_implement_agent` / `dispatch_plan_agent` where failure handoff is needed.
5. Fix review-agent success routing so it completes `apply_change` rather than dispatching finish-agent directly.

### Sequence 3: then tighten permissions
6. Replace `skill: allow` with explicit keep/conditional/remove guidance per agent.
7. Remove stale `workflow.py *` and other unrelated bash allowances after boundary text is already narrowed.

### Sequence 4: then normalize schemas/examples
8. Rewrite evidence-envelope examples to valid JSON with real booleans and required fields.
9. Add the standardized handoff/raw-log section requirements to each worker prompt.
10. Ensure finish-agent wording covers both archive and post-archive contexts without hardcoding one phase sample incorrectly.

### Sequence 5: verify before claiming completion
11. Run static prompt checks.
12. Run workflow contract tests if the repository already has tests that assert these semantics.
13. Re-read final diffs for accidental runtime-scope creep.

## TDD-Aware Task Plan

### Task 1: Capture stale contract expectations
**Behavior verified:** current prompt set still contains stale routing, broad skill permissions, and runtime-ownership wording.

**Planned tests and expected failure before implementation:**
- `test_worker_prompts_do_not_use_back_to_routes` — expected initial failure if any `back_to_plan` / `back_to_implement` remains
- `test_review_agent_success_does_not_dispatch_finish_agent` — expected initial failure on current review-agent prompt
- `test_worker_prompts_do_not_grant_skill_allow_broadly` — expected initial failure if `skill: allow` remains
- `test_finish_agent_does_not_claim_runtime_hook_ownership` — expected initial failure if `complete-hook` ownership language remains

**Verification commands:**
- `rg -n "back_to_|dispatch_finish_agent|skill: allow|workflow.py \*|openspec-apply-change|openspec-archive-change|complete-hook" agents/*.md`

### Task 2: Normalize implement-agent and test-agent
**Behavior verified:** apply-phase worker and verifier use explicit permissions, provider-agnostic wording, and normalized failure routes.

**Expected failure before implementation:** static grep still finds stale `skill: allow`, provider-specific names, or `back_to_*` routes.

**Verification commands:**
- `rg -n "skill: allow|openspec-apply-change|back_to_|workflow.py \*" agents/implement-agent.md agents/test-agent.md`

### Task 3: Normalize review-agent
**Behavior verified:** review stays review-only, uses normalized envelopes, and returns `complete_apply_change` on success.

**Expected failure before implementation:** review-agent still recommends `dispatch_finish_agent` or broad review-host behavior.

**Verification commands:**
- `rg -n "dispatch_finish_agent|skill: allow|workflow.py \*" agents/review-agent.md`

### Task 4: Normalize finish-agent
**Behavior verified:** finish-agent is archive/post-archive scoped, provider-agnostic, and does not claim workflow runtime ownership.

**Expected failure before implementation:** finish-agent still hardcodes `openspec-archive-change`, `complete-hook`, or unrelated bash allowances.

**Verification commands:**
- `rg -n "openspec-archive-change|complete-hook|sync_templates.py|workflow.py \*|skill: allow" agents/finish-agent.md`

### Task 5: Verify whole set together
**Behavior verified:** all four canonical prompts share one routing/permission/evidence/handoff contract.

**Verification commands:**
- `rg -n "back_to_|dispatch_finish_agent|skill: allow|workflow.py \*|openspec-apply-change|openspec-archive-change|complete-hook" agents/*.md`
- `python3 -m pytest tests/test_workflow.py -v`

## Focused Verification Strategy
- Confirm no worker prompt claims workflow-state ownership.
- Confirm only explicit keep/conditional skills remain.
- Confirm stale provider-specific skill names are removed where wrapper/provider dispatch is required.
- Confirm failure routing uses `dispatch_implement_agent` / `dispatch_plan_agent`.
- Confirm review success routing no longer jumps directly to finish-agent.
- Confirm handoff/raw-log sections are identical across worker prompts.
- Confirm runtime-oriented changes did not leak into this prompt-only change unless justified by failing tests.

## EvalOps Candidates
If this prompt contract later controls AI-worker behavior in practice, capture durable eval cases for:
- worker returns valid JSON booleans instead of quoted booleans;
- review-agent success completes apply phase instead of dispatching finish-agent;
- blocked verification routes to `dispatch_implement_agent`;
- plan-needed routing returns `dispatch_plan_agent`;
- finish-agent avoids claiming runtime-hook ownership.

## Open Decisions
- None required to start the prompt-only normalization pass.
- Separate follow-up recommended for run-directory unification and any `run.json` runtime migration discussion.
