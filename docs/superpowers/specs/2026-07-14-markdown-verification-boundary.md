# Markdown Verification Boundary

## Context

Agent and Skill Markdown changes are currently often verified with pytest assertions that check for headings, sentences, or keywords. These tests prove only that prose exists; they do not prove that an agent follows the instruction. They also make prompt wording difficult to refactor and cause test growth for non-code changes.

Markdown artifacts have two distinct roles:

1. instructional prose interpreted by a model or human;
2. machine-interpreted configuration, schema, metadata, or generation input.

Verification must distinguish these roles. Instructional prose should not create code-level tests. Machine-interpreted structure remains eligible for deterministic tests. Agent behavior regressions are represented by Eval cases when justified.

## Goals

- Prose-only Agent or Skill changes do not generate pytest or unittest cases.
- Machine-interpreted Markdown remains structurally testable.
- Code changes continue to use normal TDD and test-suite evolution.
- Agent behavior failures use event-driven Eval coverage rather than prose-presence assertions.
- `implement-agent` and `review-agent` make an explicit verification-type decision.
- Future prompt-related test growth stops without deleting historical tests in this change.

## Non-Goals

- No bulk deletion of existing prompt tests.
- No repository-wide Eval migration.
- No general test-suite refactoring.
- No weakening of permission, parser, schema, or sync validation.
- No mandatory Eval for every Markdown edit.
- No changes to derived-sync phase ownership beyond relying on P0.

## Decisions

### 1. Verification Classification

Every change affecting Agent or Skill Markdown is classified as one or more of:

```text
instructional_prose
machine_interpreted_markdown
executable_code
provider_transform
```

The classification determines verification.

### 2. Instructional Prose

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

### 3. Machine-Interpreted Markdown

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

### 4. Executable Code

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

### 5. Provider Transformations

Provider-specific transformation code is executable behavior and remains testable. Tests may cover:

- canonical-to-provider mapping;
- provider-specific frontmatter conversion;
- unsupported-field removal;
- path mapping;
- deterministic output;
- stale-file detection.

The tests verify transformation behavior, not the semantic quality of the prompt prose.

### 6. Event-Driven Eval

Eval cases are not generated for every Markdown edit. An Eval should be introduced when:

- a user reports an Agent or Skill behavior failure;
- the same failure recurs;
- the change affects a safety or destructive-operation boundary;
- lifecycle completion or structured output placement failed;
- a critical agent contract cannot be validated deterministically;
- the user explicitly requests regression coverage.

Ordinary wording changes, section reorganization, and explanatory additions do not require Eval.

Once a real failure becomes an Eval case, it should remain as regression coverage unless the supported behavior is removed.

### 7. Eval Ownership

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

### 8. Implement-Agent Rules

`implement-agent` must:

1. classify changed Markdown;
2. avoid prose-presence tests for instructional changes;
3. run code tests only for executable or machine-interpreted behavior;
4. record whether an Eval trigger exists;
5. preserve normal focused and regression verification for code changes;
6. use P0 deferred sync for canonical changes.

It must not claim TDD success for a prose-only change by adding a test that passes immediately.

### 9. Review-Agent Rules

`review-agent` verifies:

- classification is correct;
- no unnecessary prose-presence test was introduced;
- machine-interpreted changes have appropriate deterministic coverage;
- code changes have appropriate behavioral tests;
- an Eval was not omitted when explicitly required;
- an Eval was not added without a meaningful trigger when the change is low risk.

Review must not reject a prose-only change solely because no pytest case was added.

### 10. Finish-Agent Rules

`finish-agent` runs final repository verification appropriate to the actual change set. For prose-only canonical changes, it performs derived synchronization and consistency checks under P0, but does not require new prompt prose tests.

## Agent Changes

- `implement-agent`: add verification classification and prohibit prose-presence test generation.
- `review-agent`: review the selected verification type instead of requiring new tests.
- `plan-agent`: identify whether requirements affect prose, machine structure, code, or provider transformation.
- `dev-orchestrator`: forward verification classification and Eval decisions.
- `finish-agent`: apply final verification without converting prose edits into code-test obligations.

## Affected Areas

- canonical agent prompts
- relevant SDLC documentation and templates
- structured implementation and review evidence
- wrapper/runtime schema only if evidence validation is implemented in code
- distributed copies synchronized under P0

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
- P0 deferred-sync behavior remains authoritative for canonical changes.
