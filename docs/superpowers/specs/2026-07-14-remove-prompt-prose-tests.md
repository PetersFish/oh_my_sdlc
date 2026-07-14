# Remove Prompt Prose Tests

## Context

The repository contains tests that inspect Agent and Skill Markdown for exact headings, sentences, keywords, or rule fragments. These tests were introduced to protect prompt contracts, but they verify text presence rather than agent behavior. They are brittle under semantically equivalent rewrites and have contributed to rapid growth in `tests/test_wrapper_contracts.py` and related suites.

P1 prevents new prose-presence tests. This change addresses the existing debt by classifying prompt-related tests, deleting only those that verify instructional prose, preserving machine contracts, and migrating selected real behavior regressions to Eval cases when justified.

## Goals

- Inventory existing prompt-related tests.
- Classify every candidate before removal.
- Delete tests whose sole assertion is prompt prose presence.
- Preserve frontmatter, permission, parser, runtime-schema, sync, and provider-transform tests.
- Consolidate duplicate canonical and generated-copy assertions.
- Migrate selected user-observed or high-risk behavior regressions to Eval cases.
- Reduce static prompt-test volume without weakening executable safety contracts.

## Non-Goals

- No general test-suite modularization.
- No deletion based only on age, line count, or coverage percentage.
- No migration of every deleted test to Eval.
- No redesign of the Eval framework.
- No changes to P0 derived-sync ownership.
- No broad rewrite of Agent or Skill content.

## Decisions

### 1. Required Classification

Every candidate test must be classified as exactly one primary type:

```text
prompt_prose
machine_structure
permission_runtime
output_schema_runtime
derived_sync_behavior
provider_specific_transform
artifact_loadability
mixed
```

The classification and action are recorded in a migration inventory.

### 2. Prompt Prose Tests

A test is `prompt_prose` when its only purpose is to prove that instructional text exists or uses specific wording.

Examples:

```python
assert "Final Output Contract Discipline" in body
assert "MUST NOT run sync" in body
assert "changed_files" in body
```

These tests must be deleted unless the asserted text is itself consumed by a parser or generator.

Equivalent heading, keyword, or sentence assertions spread across multiple methods are deleted together rather than retained as historical documentation.

### 3. Machine Structure Tests

Tests remain when they validate machine-readable structure, including:

- YAML frontmatter parsing;
- required metadata fields;
- valid modes and permission values;
- malformed configuration rejection;
- artifact path and encoding validity;
- structured embedded schema parsed by code.

Where possible, they must assert parsed values or effective behavior rather than raw text.

### 4. Permission Runtime Tests

Permission tests remain when they validate effective command authorization or matching semantics.

Preferred:

```python
assert resolve_permission(config, command) == "deny"
```

A raw-text permission test should be rewritten to parser-level or runtime-level coverage when the repository exposes suitable code. If no parser exists and the frontmatter is the actual runtime input, a minimal structural assertion may remain, but exact instructional prose must be excluded.

### 5. Output Schema Runtime Tests

Tests remain when executable runtime code validates Agent result envelopes, required fields, state transitions, or structured evidence.

Tests that merely assert that a Markdown example mentions a field are removed if runtime validation already protects the contract.

If no runtime validator exists, the gap must be documented. This change does not automatically add a validator unless required for safe removal.

### 6. Derived Sync Tests

Tests for deterministic canonical-to-derived behavior remain, including:

- dry-run planning;
- drift detection;
- write-producing sync;
- no-op behavior;
- stale-file deletion;
- target mapping;
- generated-scope validation;
- provider transformation.

Tests must not repeat the complete semantic prompt contract against every generated copy.

### 7. Canonical and Generated Assertions

Canonical semantic assertions and derived synchronization assertions are separated.

For a canonical prose rule:

- prose-presence assertion: delete;
- generated copies byte-match canonical after sync: retain only if this is the intended transformation;
- provider-specific structural transform: retain only for actual provider differences.

Generated copies must not independently multiply semantic prose assertions.

### 8. Eval Migration Criteria

A deleted prompt prose test is migrated to Eval only when at least one condition holds:

- it represents a user-reported behavior failure;
- the failure has recurred;
- it protects safety, destructive operations, lifecycle finalization, or data integrity;
- it protects structured output placement that cannot be covered deterministically;
- the user explicitly approves or requests the Eval.

Tests created only from speculative prompt requirements are deleted without automatic Eval replacement.

### 9. Migration Inventory

Create a temporary or archived migration record containing:

```json
{
  "test": "TestImplementAgentContract.test_forbids_sync_fix",
  "classification": "prompt_prose",
  "action": "delete",
  "replacement": null,
  "reason": "Exact sentence presence does not verify agent behavior."
}
```

For retained or rewritten coverage:

```json
{
  "test": "TestAgentPermissions.test_sync_fix_denied",
  "classification": "permission_runtime",
  "action": "rewrite",
  "replacement": "parser-level effective permission assertion"
}
```

### 10. Safe Removal Procedure

For each bounded group:

1. identify candidate tests;
2. classify them;
3. confirm whether executable coverage exists;
4. delete or rewrite tests;
5. add approved Eval replacements where required;
6. run focused tests;
7. run full regression;
8. inspect unexpected coverage or behavior gaps;
9. record the migration result.

Deletion must be incremental rather than one unreviewable mass removal.

### 11. Review Requirements

`review-agent` must verify:

- every removed test has a classification;
- machine contracts were not mistaken for prose;
- permission and runtime-schema coverage remains effective;
- generated sync behavior remains covered;
- Eval migration follows the trigger policy;
- no new prose-presence tests were introduced during cleanup;
- full regression remains green.

### 12. Completion Evidence

Implementation evidence includes:

```json
{
  "prompt_test_cleanup": {
    "deleted_prompt_prose_tests": 0,
    "rewritten_machine_contract_tests": 0,
    "retained_tests": 0,
    "eval_cases_added": [],
    "inventory_path": "...",
    "full_regression": "pass"
  }
}
```

Counts are descriptive, not targets. The goal is correct classification, not maximum deletion.

## Initial Candidate Areas

Expected inspection areas include:

- `tests/test_wrapper_contracts.py`
- Agent-related tests in other test modules
- canonical-versus-derived copy tests
- tests added for exact headings, protocol sentences, and output-discipline wording
- existing EvalOps cases related to real Agent failures

The implementation must search the current repository rather than assume all candidates are located in one file.

## Affected Areas

- prompt-related test modules
- Eval case directories for approved migrations
- test migration inventory or archived cleanup summary
- canonical test helpers if parser-level assertions are introduced

No production behavior should change unless a missing deterministic validator is explicitly added as a separate, justified code change.

## Acceptance Criteria

- Every deleted prompt-related test is classified before removal.
- Exact prose, heading, and keyword presence tests are removed.
- Frontmatter and machine-readable structure tests remain.
- Effective permission behavior remains tested.
- Runtime result-schema validation remains tested.
- Derived synchronization behavior remains tested.
- Generated copies no longer duplicate canonical semantic prose assertions.
- Only justified real behavior regressions migrate to Eval.
- No automatic one-for-one Eval replacement occurs.
- Focused and full regression suites pass.
- The cleanup produces no new prompt prose tests.
- P0 and P1 rules remain authoritative.
