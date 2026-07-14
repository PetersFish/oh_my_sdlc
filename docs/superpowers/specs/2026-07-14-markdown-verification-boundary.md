# Markdown Verification Boundary

## Context

Agent and Skill Markdown changes are currently often verified with pytest assertions that check for headings, sentences, or keywords. These tests prove only that prose exists; they do not prove that an agent follows the instruction. They also make prompt wording difficult to refactor and cause test growth for non-code changes.

Markdown artifacts have two distinct roles:

1. instructional prose interpreted by a model or human;
2. machine-interpreted configuration, schema, metadata, or generation input.

Verification must distinguish these roles. Instructional prose should not create code-level tests. Machine-interpreted structure remains eligible for deterministic tests. Agent behavior regressions are represented by Eval cases when justified.

The classification and Eval rules are shared across planning, implementation, review, orchestration, and finalization. They must therefore have one canonical implementation rather than being duplicated across multiple agent prompts.

## Goals

- Prose-only Agent or Skill changes do not generate pytest or unittest cases.
- Machine-interpreted Markdown remains structurally testable.
- Code changes continue to use normal TDD and test-suite evolution.
- Agent behavior failures use event-driven Eval coverage rather than prose-presence assertions.
- One shared Skill is the canonical source for Markdown verification classification and Eval policy.
- Agents contain only the trigger for loading the shared Skill and their role-specific responsibilities.
- Future prompt-related test growth stops without deleting historical tests in this change.

## Non-Goals

- No bulk deletion of existing prompt tests.
- No repository-wide Eval migration.
- No general test-suite refactoring.
- No weakening of permission, parser, schema, or sync validation.
- No mandatory Eval for every Markdown edit.
- No changes to derived-sync phase ownership beyond relying on the existing derived-sync phase-boundary design.
- No duplication of the full shared policy in individual agent files.

## Decisions

### 1. Shared Skill Is the Canonical Policy Source

Create one canonical shared Skill:

```text
skills/markdown-verification-discipline/SKILL.md
```

The Skill owns the complete policy for:

- verification classification;
- instructional prose handling;
- machine-interpreted Markdown handling;
- executable code handling;
- provider transformation handling;
- event-driven Eval triggers;
- Eval ownership and retention.

The shared Skill is the only canonical implementation of Decisions 2–8 below.

Agent prompts must not copy the full policy. They contain only:

- when the Skill must be loaded;
- which role-specific decision or verification action the agent owns;
- which structured evidence fields the agent must produce or consume.

### 2. Verification Classification

Every change affecting Agent or Skill Markdown is classified as one or more of:

```text
instructional_prose
machine_interpreted_markdown
executable_code
provider_transform
```

The classification determines verification.

### 3. Instructional Prose

Instructional prose includes:

- role and responsibility descriptions;
- reasoning guidance;
- operational checklists;
- workflow instructions;
- review guidance;
- examples intended for the model;
- explanatory headings and wording;
- human-readable handoff guidance.

For prose-only changes:

- no pytest or unittest case is added or modified solely to prove the prose exists;
- no artificial RED/GREEN loop is required;
- existing code tests need not be expanded;
- focused verification consists of artifact inspection, syntax validation where applicable, and any explicitly requested Eval.

Implementation evidence records:

```json
{
  "verification_classification": {
    "change_types": ["instructional_prose"],
    "code_tests_required": false,
    "eval_required": false,
    "reason": "No executable or machine-interpreted behavior changed."
  }
}
```

### 4. Machine-Interpreted Markdown

Code tests remain required or permitted when Markdown contains behavior consumed by code, including:

- YAML frontmatter;
- permissions;
- runtime-loaded metadata;
- structured schemas;
- provider transformation directives;
- source-to-derived mappings;
- content parsed or validated by scripts.

Tests must verify parser or runtime behavior rather than exact prose.

Preferred:

```python
config = load_agent_config(path)
assert resolve_permission(config, command) == DENY
```

Disallowed as the sole verification:

```python
assert "MUST NOT run command X" in markdown_body
```

### 5. Executable Code

If a change includes executable code, normal test-suite evolution applies to that behavior. The implementation must decide whether to:

```text
use_existing_coverage
modify_existing_test
extend_parameterized_matrix
add_independent_test
merge_duplicate_tests
delete_obsolete_tests
```

Markdown prose in the same change does not independently require prose-presence tests.

### 6. Provider Transformations

Provider-specific transformation code is executable behavior and remains testable. Tests may cover:

- canonical-to-provider mapping;
- provider-specific frontmatter conversion;
- unsupported-field removal;
- path mapping;
- deterministic output;
- stale-file detection.

The tests verify transformation behavior, not the semantic quality of the prompt prose.

### 7. Event-Driven Eval

Eval cases are not generated for every Markdown edit. An Eval should be introduced when:

- a user reports an Agent or Skill behavior failure;
- the same failure recurs;
- the change affects a safety or destructive-operation boundary;
- lifecycle completion or structured output placement failed;
- a critical agent contract cannot be validated deterministically;
- the user explicitly requests regression coverage.

Ordinary wording changes, section reorganization, and explanatory additions do not require Eval.

Once a real failure becomes an Eval case, it should remain as regression coverage unless the supported behavior is removed.

### 8. Eval Ownership

Eval creation is user-initiated or explicitly approved for normal prompt changes. Agents may recommend an Eval but must not automatically proliferate cases for low-risk prose edits.

Evidence may record:

```json
{
  "eval_assessment": {
    "required": false,
    "trigger": "none",
    "recommended_cases": []
  }
}
```

For an approved failure-driven case:

```json
{
  "eval_assessment": {
    "required": true,
    "trigger": "user_reported_behavior_failure",
    "recommended_cases": ["finish-agent-final-json-placement"]
  }
}
```

### 9. Skill Loading Contract

The shared policy is effective only when the relevant agents actually load it.

The following agents must load `markdown-verification-discipline` when Agent or Skill Markdown is in scope:

- `plan-agent`;
- `implement-agent`;
- `review-agent`.

`dev-orchestrator` and `finish-agent` may rely on the approved classification passed through workflow evidence, but they must load the Skill when they need to create, override, or re-evaluate that classification.

A bare prose reference such as “follow the Markdown verification rule” is insufficient. Agent instructions must use an explicit load requirement.

### 10. Plan-Agent Rules

`plan-agent` must:

1. load `markdown-verification-discipline` when Agent or Skill Markdown is affected;
2. classify the change;
3. identify whether code tests are required;
4. identify whether an Eval trigger exists;
5. include the classification in planning artifacts and handoff evidence.

It must not prescribe one new test per Markdown requirement.

### 11. Implement-Agent Rules

`implement-agent` must:

1. load `markdown-verification-discipline` for Agent or Skill Markdown work;
2. apply the approved classification;
3. avoid prose-presence tests for instructional changes;
4. run code tests only for executable or machine-interpreted behavior;
5. record whether an Eval trigger exists;
6. preserve normal focused and regression verification for code changes;
7. rely on the existing derived-sync phase boundary for canonical changes.

It must not claim TDD success for a prose-only change by adding a test that passes immediately.

### 12. Review-Agent Rules

`review-agent` must:

1. load `markdown-verification-discipline` when reviewing Agent or Skill Markdown changes;
2. verify that classification is correct;
3. verify that no unnecessary prose-presence test was introduced;
4. verify that machine-interpreted changes have appropriate deterministic coverage;
5. verify that code changes have appropriate behavioral tests;
6. verify that an Eval was not omitted when explicitly required;
7. verify that an Eval was not added without a meaningful trigger for low-risk prose edits.

Review must not reject a prose-only change solely because no pytest case was added.

### 13. Dev-Orchestrator Rules

`dev-orchestrator` must preserve and forward:

- `verification_classification`;
- `eval_assessment`;
- the shared Skill path or name when downstream re-evaluation is required.

It must not independently duplicate the full policy or reinterpret the classification without loading the shared Skill.

### 14. Finish-Agent Rules

`finish-agent` runs final repository verification appropriate to the approved classification.

For prose-only canonical changes, it performs derived synchronization and consistency checks under the existing derived-sync phase boundary, but does not require new prompt prose tests.

If final repository state introduces executable or machine-interpreted changes not covered by the approved classification, finish-agent must block or request re-evaluation rather than silently broadening the verification type.

### 15. AGENTS.md Routing Rule

`AGENTS.md` contains only a concise routing rule:

```text
When planning, implementing, or reviewing Agent or Skill Markdown changes,
load `markdown-verification-discipline` before deciding verification.
```

Detailed policy remains in the shared Skill.

## Shared Skill Contract

The Skill frontmatter must describe when it is required, including:

- planning verification for Agent or Skill Markdown changes;
- implementing such changes;
- reviewing whether tests or Eval coverage are appropriate;
- distinguishing instructional prose from machine-consumed Markdown.

The Skill body contains Decisions 2–8 in operational form and defines the structured evidence examples used by agents.

The Skill must not own derived synchronization, general test design, or broad implementation contract discipline. Those remain with their existing dedicated policies and Skills.

## Agent Changes

- `plan-agent`: add explicit shared-Skill loading trigger and classification output responsibility.
- `implement-agent`: add explicit shared-Skill loading trigger and prohibit prose-presence test generation through the shared policy.
- `review-agent`: add explicit shared-Skill loading trigger and verification-selection review responsibility.
- `dev-orchestrator`: forward classification and Eval assessment without duplicating policy.
- `finish-agent`: honor the approved classification during final verification.
- `AGENTS.md`: add one short routing trigger.

## Affected Areas

- `skills/markdown-verification-discipline/SKILL.md`;
- `agents/plan-agent.md`;
- `agents/implement-agent.md`;
- `agents/review-agent.md`;
- `agents/dev-orchestrator.md`;
- `agents/finish-agent.md`;
- `AGENTS.md`;
- relevant SDLC documentation and templates;
- structured implementation and review evidence;
- wrapper/runtime schema only if evidence validation is implemented in code;
- distributed copies synchronized under the existing derived-sync phase boundary.

Historical prompt-test deletion is handled by P2.

## Acceptance Criteria

- Prose-only Agent or Skill changes add no pytest or unittest cases.
- Prose-only changes do not require an artificial RED/GREEN loop.
- Machine-interpreted Markdown remains covered by parser or runtime tests.
- Permission tests verify effective behavior rather than sentence presence.
- Provider transformation code remains deterministically tested.
- Mixed code-and-Markdown changes test the executable behavior only.
- Eval cases are event-driven and normally user-initiated or explicitly approved.
- A user-reported critical behavior failure can be retained as an Eval regression.
- `review-agent` accepts valid prose-only changes without new tests.
- Existing prompt tests are not bulk-deleted by this change.
- Decisions 2–8 have one canonical implementation in `markdown-verification-discipline`.
- Agent prompts do not duplicate the full shared policy.
- Plan, implement, and review agents explicitly load the shared Skill when relevant.
- `AGENTS.md` contains only the short routing trigger.
- Dev-orchestrator forwards classification and Eval evidence without reimplementing the policy.
- Finish-agent honors the approved classification.
- Distributed Skill and agent copies remain synchronized through the existing finish-owned sync process.
