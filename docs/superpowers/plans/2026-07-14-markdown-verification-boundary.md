# Markdown Verification Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Execute one bounded slice at a time and keep checkboxes synchronized.

**Goal:** Introduce `markdown-verification-discipline` as the single shared policy for Agent and Skill Markdown verification, then make planning, implementation, review, orchestration, and finalization agents load or consume that policy without duplicating it.

**Architecture:** Decisions about instructional prose, machine-interpreted Markdown, executable code, provider transformations, and event-driven Eval live once in a canonical Skill. `plan-agent`, `implement-agent`, and `review-agent` explicitly load the Skill when Markdown work is in scope. `dev-orchestrator` forwards the approved classification, `finish-agent` honors it, and `AGENTS.md` contains only a short routing trigger. Derived copies are synchronized only during finish according to the existing derived-sync phase boundary.

**Tech Stack:** Markdown Skill and agent contracts, YAML frontmatter, existing skill distribution tooling, existing agent setup tooling, pytest/unittest only for machine-interpreted behavior or executable sync/load logic.

**Primary Spec:** `docs/superpowers/specs/2026-07-14-markdown-verification-boundary.md`

---

## File Structure

- Create: `skills/markdown-verification-discipline/SKILL.md` — canonical shared policy.
- Modify: `AGENTS.md` — short routing trigger only.
- Modify: `agents/plan-agent.md` — explicit Skill load and classification ownership.
- Modify: `agents/implement-agent.md` — explicit Skill load and application responsibility.
- Modify: `agents/review-agent.md` — explicit Skill load and verification-selection review.
- Modify: `agents/dev-orchestrator.md` — forward classification and Eval assessment.
- Modify: `agents/finish-agent.md` — honor approved classification during final verification.
- Modify only if required: structured handoff or runtime schema documentation for `verification_classification` and `eval_assessment`.
- Modify only if executable parsing or loading behavior changes: relevant code tests.
- Do not add or expand prose-presence tests.
- Derived copies under `.opencode/`, `.claude/`, and `.cursor/` are produced by finish-owned synchronization, not by implementation tasks.

---

## Slice 1: Create the Shared Markdown Verification Skill

### Task 1: Add the Canonical Skill

**Files:**
- Create: `skills/markdown-verification-discipline/SKILL.md`

- [ ] **Step 1: Read existing Skill conventions**

Inspect representative discipline Skills and `skills/TAXONOMY.md` before choosing frontmatter and section structure.

Verify:

```text
- skill name follows repository taxonomy;
- description uses folded YAML block scalar;
- trigger conditions are explicit;
- the Skill does not duplicate unrelated test-design or derived-sync policy.
```

- [ ] **Step 2: Create Skill frontmatter**

The description must trigger when:

- planning Agent or Skill Markdown changes;
- implementing Agent or Skill Markdown changes;
- reviewing whether code tests or Eval coverage are appropriate;
- distinguishing instructional prose from machine-interpreted Markdown.

- [ ] **Step 3: Implement the shared decision workflow**

The Skill body must define:

1. classification values:
   - `instructional_prose`;
   - `machine_interpreted_markdown`;
   - `executable_code`;
   - `provider_transform`;
2. verification behavior for each classification;
3. prohibition on tests whose sole purpose is proving prose presence;
4. parser/runtime test requirements for machine-interpreted content;
5. event-driven Eval triggers;
6. user approval or initiation rule for normal prompt Eval creation;
7. structured `verification_classification` and `eval_assessment` evidence.

- [ ] **Step 4: Keep boundaries explicit**

The Skill must state that it does not own:

- general behavioral test design;
- implementation contract discipline;
- derived artifact synchronization;
- bulk deletion of historical prompt tests.

- [ ] **Step 5: Validate the Skill artifact**

Use existing Skill validation or loading commands where available. Do not add a pytest assertion for wording or headings.

Expected result:

```text
- frontmatter parses;
- Skill is discoverable/loadable;
- no code-level prose-presence test is introduced.
```

---

## Slice 2: Add Global Routing Without Duplicating Policy

### Task 2: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Add one concise routing rule**

Add a short rule under the existing contract/test discipline area:

```markdown
When planning, implementing, or reviewing Agent or Skill Markdown changes,
load `markdown-verification-discipline` before deciding verification.
```

- [ ] **Step 2: Do not copy Skill content**

`AGENTS.md` must not reproduce classification details, Eval trigger lists, or evidence schemas.

- [ ] **Step 3: Inspect for conflicting global guidance**

Ensure existing statements such as “write tests for bug fixes” are not interpreted as requiring code tests for prose-only Markdown changes. Prefer a narrowly scoped clarification or reference to the new Skill rather than duplicating its policy.

---

## Slice 3: Integrate Planning and Implementation Roles

### Task 3: Update plan-agent

**Files:**
- Modify: `agents/plan-agent.md`

- [ ] **Step 1: Add explicit load trigger**

Require `plan-agent` to load `markdown-verification-discipline` whenever Agent or Skill Markdown is part of the planned change.

- [ ] **Step 2: Define role-specific output**

Require planning artifacts or handoff evidence to include:

```json
{
  "verification_classification": {
    "change_types": [],
    "code_tests_required": false,
    "eval_required": false,
    "reason": ""
  },
  "eval_assessment": {
    "required": false,
    "trigger": "none",
    "recommended_cases": []
  }
}
```

- [ ] **Step 3: Prevent test-per-requirement planning**

Add a role-specific prohibition against prescribing one new test case for every Markdown requirement.

### Task 4: Update implement-agent

**Files:**
- Modify: `agents/implement-agent.md`

- [ ] **Step 1: Add explicit load trigger**

Require `implement-agent` to load `markdown-verification-discipline` before deciding verification for Agent or Skill Markdown work.

- [ ] **Step 2: Define application responsibilities**

Require implement-agent to:

- apply the approved classification;
- avoid prose-presence tests;
- run deterministic tests only for executable or machine-interpreted behavior;
- avoid artificial RED/GREEN claims for prose-only edits;
- record Eval assessment;
- rely on finish-owned derived sync.

- [ ] **Step 3: Remove or reconcile conflicting prompt language**

Search for unconditional wording that says every behavior change or bug fix must add a test. Narrow it so it applies to executable behavior, while the shared Skill governs Markdown semantics.

- [ ] **Step 4: Do not modify generated copies**

Keep canonical agent changes only. Deferred provider-copy drift is handled by the existing phase-boundary process.

---

## Slice 4: Integrate Review, Orchestration, and Finish Roles

### Task 5: Update review-agent

**Files:**
- Modify: `agents/review-agent.md`

- [ ] **Step 1: Add explicit load trigger**

Require `review-agent` to load `markdown-verification-discipline` for Agent or Skill Markdown reviews.

- [ ] **Step 2: Add role-specific review criteria**

Review must verify:

- classification correctness;
- no unnecessary prose-presence test;
- deterministic coverage for machine-interpreted changes;
- behavioral coverage for executable changes;
- Eval presence only when triggered or approved;
- prose-only changes are not rejected for lacking pytest additions.

- [ ] **Step 3: Avoid duplicating the shared rule text**

Use a short role-specific checklist and refer to the Skill for definitions and triggers.

### Task 6: Update dev-orchestrator

**Files:**
- Modify: `agents/dev-orchestrator.md`

- [ ] **Step 1: Forward approved evidence**

Ensure downstream dispatch context preserves:

- `verification_classification`;
- `eval_assessment`.

- [ ] **Step 2: Prevent independent reinterpretation**

The orchestrator must not recreate classification rules. If it needs to override or create a classification, it must load the shared Skill or dispatch the appropriate planning role.

### Task 7: Update finish-agent

**Files:**
- Modify: `agents/finish-agent.md`

- [ ] **Step 1: Honor approved classification**

For prose-only canonical changes, finish-agent must run derived synchronization and consistency checks without demanding new prompt prose tests.

- [ ] **Step 2: Detect scope expansion**

If finalization introduces executable or machine-interpreted changes outside the approved classification, finish-agent must block or request re-evaluation.

- [ ] **Step 3: Keep finalization responsibilities separate**

Do not copy classification or Eval rules into finish-agent. It consumes the approved evidence and loads the Skill only when re-evaluation is necessary.

---

## Slice 5: Evidence and Compatibility Review

### Task 8: Inspect Structured Evidence Paths

**Files:**
- Inspect: workflow result schemas, handoff templates, and runtime validation.
- Modify only if current code rejects or drops the new evidence fields.

- [ ] **Step 1: Trace evidence flow**

Confirm whether arbitrary nested evidence already survives:

```text
plan-agent handoff
-> dev-orchestrator dispatch
-> implement-agent result
-> review-agent context
-> finish-agent context
```

- [ ] **Step 2: Prefer documentation-only changes when runtime is already permissive**

Do not add schema code or tests unless the runtime actually validates and rejects these fields.

- [ ] **Step 3: If executable schema code changes, use normal code tests**

Only then add or modify behavioral tests for persistence, validation, or forwarding. Do not add static tests for prompt wording.

### Task 9: Audit for Policy Duplication

- [ ] **Step 1: Search canonical agent files**

Verify that no agent contains a full copy of the shared classification and Eval policy.

- [ ] **Step 2: Confirm role-specific content remains local**

Each agent should contain only its load trigger, responsibilities, and evidence contract.

- [ ] **Step 3: Confirm P2 remains separate**

Do not delete historical prompt prose tests in this implementation. That work belongs to `2026-07-14-remove-prompt-prose-tests.md`.

---

## Slice 6: Verification and Finish-Owned Distribution

### Task 10: Focused Verification

- [ ] **Step 1: Validate Markdown and Skill loading**

Run repository-supported Skill/frontmatter checks and inspect canonical agent references.

- [ ] **Step 2: Run code tests only when executable behavior changed**

If no executable parser, runtime, or distribution code changed, do not add or run a new focused pytest suite solely for prompt text.

Existing relevant smoke or repository validation commands may still be run as regression evidence.

- [ ] **Step 3: Run full regression according to current workflow policy**

Use the repository's existing full regression gate. Record any accepted pre-existing failures according to current evidence rules.

### Task 11: Review Before Derived Sync

- [ ] **Step 1: Submit only authored canonical changes for review**

Review scope should include:

- the new canonical Skill;
- canonical agent changes;
- `AGENTS.md`;
- any necessary schema code/tests.

It should not require generated provider copies yet.

### Task 12: Finish-Owned Synchronization

Owned by `finish-agent` after review passes:

- [ ] synchronize the new Skill to `.opencode/`, `.claude/`, and `.cursor/`;
- [ ] synchronize canonical agent changes;
- [ ] run derived-artifact checks until clean;
- [ ] verify activated agent frontmatter remains valid;
- [ ] run final repository verification;
- [ ] verify clean final worktree.

---

## Verification Scenarios

### Scenario 1: Prose-Only Agent Edit

Given only instructional prose changes:

- plan-agent loads the Skill and records `instructional_prose`;
- `code_tests_required=false`;
- implement-agent adds no pytest case;
- review-agent accepts the absence of new code tests;
- finish-agent synchronizes derived copies.

### Scenario 2: Permission Frontmatter Change

Given machine-interpreted permission changes:

- classification includes `machine_interpreted_markdown`;
- deterministic parser/effective-permission tests are selected when needed;
- no test asserts only that a sentence exists.

### Scenario 3: Markdown Plus Executable Transformation Code

Given a provider transformation script and canonical prompt both change:

- classification includes `executable_code` or `provider_transform`;
- code behavior receives appropriate tests;
- prompt prose does not independently create static tests.

### Scenario 4: User-Reported Agent Failure

Given a user-reported behavior failure:

- Eval assessment records the trigger;
- an Eval may be created after user initiation or approval;
- the case remains regression coverage after repair.

### Scenario 5: Low-Risk Wording Change

Given wording cleanup only:

- no Eval is automatically generated;
- no artificial RED/GREEN loop occurs;
- artifact and final sync verification are sufficient.

---

## Acceptance Checklist

- [ ] `markdown-verification-discipline` exists as the single canonical shared policy.
- [ ] The Skill frontmatter is valid and discoverable.
- [ ] Decisions for classification, tests, and Eval triggers are not duplicated across agents.
- [ ] `AGENTS.md` contains only a short load-routing rule.
- [ ] plan-agent explicitly loads the Skill and owns classification.
- [ ] implement-agent explicitly loads the Skill and applies classification.
- [ ] review-agent explicitly loads the Skill and validates verification selection.
- [ ] dev-orchestrator forwards classification and Eval assessment.
- [ ] finish-agent honors classification without requiring prose-presence tests.
- [ ] Prose-only changes do not add pytest/unittest cases.
- [ ] Machine-interpreted and executable behavior remains deterministically testable.
- [ ] No historical prompt-test cleanup is included in this change.
- [ ] Canonical changes are reviewed before finish-owned derived synchronization.
- [ ] Distributed Skill and agent copies are clean after finish.
- [ ] Full regression passes under the repository's existing verification policy.
