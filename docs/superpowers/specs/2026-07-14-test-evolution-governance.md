# Test Evolution Governance

## Context

The current Superpowers implementation workflow can be interpreted as append-only TDD: every requirement or bug fix adds new test methods even when existing tests already express the same observable contract. Over time this creates duplicated scenarios, obsolete expectations, excessive end-to-end coverage, and high maintenance cost.

The problem is not test growth itself. New supported behavior often requires new coverage. The problem is the absence of a governed decision about whether coverage should be reused, modified, extended, merged, moved, added, or deleted.

This change establishes test-suite evolution rules for future executable-code changes. It does not perform the large workflow test-file restructuring handled by P3-2.

## Goals

- Preserve strict regression protection and credible TDD for executable behavior changes.
- Require existing-coverage search before adding tests.
- Classify behavior changes before choosing a test action.
- Allow modifying, parameterizing, merging, moving, or deleting tests.
- Add standalone tests only for genuinely independent behavior dimensions.
- Prefer stable observable contracts over implementation details.
- Add review gates against unnecessary test growth.
- Support dedicated test-only refactoring without artificial RED evidence.

## Non-Goals

- No fixed limit on total test lines or test count.
- No automatic deletion based on coverage percentage.
- No mandatory zero net test growth.
- No requirement to parameterize semantically distinct cases.
- No repository-wide test rewrite.
- No workflow test-file decomposition; that is P3-2.
- No prompt prose test policy; P1 and P2 are authoritative.

## Terminology

### Observable Contract

A supported outcome visible through an API, CLI, persisted state, filesystem effect, structured result, validation result, compatibility path, security boundary, or integration behavior.

### Independent Behavior Dimension

A semantically distinct boundary that requires permanent coverage, such as explicit versus fallback selection, allowed versus denied security behavior, or legacy versus current compatibility.

Different literal values, IDs, filenames, or action names are not automatically independent dimensions.

### Coverage Decision

One of:

```text
existing_coverage_only
modify_existing
extend_matrix
add_independent_test
merge_duplicates
move_test_layer
delete_obsolete
mixed
```

## Decisions

### 1. TDD Requires RED, Not Necessarily a New Test Method

For executable behavior changes, valid RED evidence may come from:

- an existing test that already reproduces the defect;
- a corrected or tightened existing expectation;
- a new row in an existing parameterized matrix;
- a consolidated contract exposing the missing behavior;
- a new independent test;
- a moved lower-level test that fails against current behavior.

Invalid TDD:

```text
change production code
-> all tests pass
-> add a test that passes immediately
-> report RED/GREEN complete
```

The agent must not fabricate RED evidence when the worktree already contains the fix.

### 2. Existing-Coverage Search

Before adding or substantially rewriting tests, `implement-agent` must search:

- the directly corresponding test module;
- tests naming the production symbol, command, status, reason, or state field;
- parameterized suites;
- representative integration and end-to-end coverage;
- recently changed tests in the affected domain.

Evidence includes searched paths, matched tests, identified gap, and selected coverage decision.

### 3. Behavior Classification

Classify the production change as one or more of:

```text
new_behavior_dimension
corrected_existing_behavior
replaced_behavior
removed_behavior
refactor_no_behavior_change
test_architecture_refactor
```

Default actions:

- new dimension: `extend_matrix` or `add_independent_test`;
- corrected behavior: `modify_existing` or `extend_matrix`;
- replaced behavior: `modify_existing` plus `delete_obsolete`;
- removed behavior: `delete_obsolete` or retain only rejection coverage;
- behavior-preserving refactor: `existing_coverage_only`;
- test architecture refactor: merge, move, parameterize, or delete redundant tests.

### 4. Decision Precedence

When equivalent regression protection is available, prefer:

1. use an existing failing test;
2. tighten or correct an existing test;
3. extend a parameterized matrix;
4. consolidate duplicate tests and add the missing row;
5. add one independent test at the lowest appropriate layer;
6. add integration or end-to-end coverage only for genuine cross-component behavior.

Safety-critical redundancy may remain when its separate failure boundary is documented.

### 5. Parameterization

Tests should become a contract matrix when they share:

- equivalent setup;
- the same execution path;
- the same assertion shape;
- the same semantic contract;
- differences limited to input and expected values.

Do not combine cases that merely share a final blocked status but protect different causes such as missing state, invalid phase, malformed input, and corruption.

Each matrix row must have a descriptive identifier and preserve useful failure diagnostics.

### 6. Test Layer Selection

Use the lowest-cost layer that fully protects the contract:

```text
pure function or policy
-> module-level state/domain
-> component/integration
-> CLI subprocess
-> full end-to-end workflow
```

CLI and end-to-end tests remain appropriate for parsing, exit codes, serialization, real filesystem transitions, and cross-module lifecycle behavior. Detailed branch permutations should normally live below the end-to-end layer.

### 7. Stable Assertions

Prefer assertions on:

- returned status and reason;
- persisted state transition;
- accepted or rejected input;
- emitted structured evidence;
- filesystem result;
- security boundary;
- supported schema.

Avoid assertions on private call order, incidental helper decomposition, temporary naming, internal dictionary ordering, or exact prose unless explicitly machine-contractual.

### 8. Obsolete-Test Removal

Tests must be deleted or rewritten when:

- the corresponding supported behavior is removed;
- an old contract is replaced;
- a duplicate is fully subsumed by a clearer contract matrix;
- the test locks down an implementation detail no longer contractual;
- equivalent lower-level coverage plus representative integration coverage replaces a redundant high-level test.

Do not delete tests solely because they are old, passing, or increase line count.

### 9. Incremental Hygiene

Within the touched test area, agents should make small low-risk improvements:

- extract repeated setup;
- merge equivalent cases;
- remove obsolete expectations caused by the same change;
- rename unclear tests;
- move detailed branch coverage to a lower layer.

Do not expand a bounded implementation slice into an unrelated repository-wide rewrite.

### 10. Structured Evidence

`implement-agent` reports:

```json
{
  "test_suite_evolution": {
    "change_classification": ["corrected_existing_behavior"],
    "coverage_decision": "extend_matrix",
    "searched_paths": [],
    "matched_existing_tests": [],
    "coverage_gap": "",
    "red_evidence": {
      "command": "",
      "result": "fail",
      "failure_reason": ""
    },
    "test_artifacts": {
      "added": [],
      "modified": [],
      "deleted": [],
      "parameterized_cases_added": [],
      "tests_merged": []
    },
    "net_growth_justification": ""
  }
}
```

`net_growth_justification` is required when a change adds at least five standalone test methods, more than one hundred test lines, a new test file for an existing domain, or a new high-level test duplicating lower-level coverage. These are review triggers, not hard limits.

### 11. Review Gate

`review-agent` rejects or requests clarification when:

- new tests duplicate an existing observable contract;
- literal-only variants were added as separate methods without justification;
- an obsolete expectation remains beside replacement behavior;
- removed production behavior retains unexplained tests;
- assertions lock down implementation details;
- an end-to-end test lacks an integration rationale;
- TDD evidence is not credible;
- large growth lacks justification.

Review does not reject growth solely because line count increased.

Review evidence includes:

```json
{
  "test_suite_review": {
    "coverage_preserved": true,
    "existing_coverage_searched": true,
    "duplicate_contracts_introduced": false,
    "obsolete_tests_retained": false,
    "parameterization_opportunities_missed": false,
    "test_layer_appropriate": true,
    "implementation_detail_lock_in": false,
    "tdd_red_evidence_credible": true,
    "growth_justification_accepted": true,
    "findings": []
  }
}
```

### 12. Test-Only Refactoring

For behavior-preserving test architecture work:

- establish a passing baseline;
- identify preserved contracts;
- refactor a bounded area;
- run focused and full regression before and after;
- document moved, merged, parameterized, and deleted tests.

Artificial RED is not required when production behavior does not change. If production behavior changes during the refactor, normal TDD applies to that behavior.

## Agent Changes

- `implement-agent`: coverage search, classification, decision, and evidence.
- `review-agent`: maintainability and duplication review.
- `plan-agent`: identify affected observable contracts and likely test layer without prescribing one test per task.
- `dev-orchestrator`: forward test strategy and evidence.
- `finish-agent`: retain final regression gate without requiring positive new-test count.

## Affected Areas

- canonical agent prompts and templates
- structured evidence schemas if validated by runtime code
- tests for executable evidence validation
- SDLC documentation
- distributed copies synchronized under P0

## Acceptance Criteria

- Executable changes still require credible regression evidence.
- TDD no longer means one new test method per change.
- Existing tests are searched before new tests are added.
- Every executable behavior change has a classification and coverage decision.
- Corrected behavior may modify an existing test.
- Equivalent variants may extend a matrix.
- Removed behavior removes or rewrites obsolete tests.
- New independent behavior remains permanently covered.
- Review detects duplicated contracts and missed parameterization.
- Large test growth requires explanation but is not automatically rejected.
- Behavior-preserving test refactoring does not require artificial RED.
- Full regression remains mandatory.
- P1 and P2 remain authoritative for Prompt and Markdown verification.
