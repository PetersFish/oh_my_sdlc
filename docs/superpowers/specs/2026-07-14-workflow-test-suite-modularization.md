# Workflow Test Suite Modularization

## Context

The workflow runtime has been decomposed into modules such as state, definitions, domains, policies, dispatch, lifecycle, and governance, but much of the detailed verification remains concentrated in a large CLI-oriented test file. This creates a God Test File with duplicated setup, expensive subprocess execution, weak domain boundaries, and poor failure localization.

P3-1 defines how tests should evolve. This change applies those rules to the workflow test area by extracting shared fixtures, moving detailed permutations to module-level suites, retaining representative CLI and end-to-end coverage, and removing semantically subsumed tests only after explicit coverage analysis.

## Goals

- Split the monolithic workflow test area by production domain.
- Make module-level tests the primary home for detailed branch coverage.
- Retain bounded CLI and end-to-end contract coverage.
- Extract reusable workspace builders and helpers.
- Parameterize clearly equivalent policy and preflight scenarios.
- Improve failure localization and test readability.
- Preserve supported behavior and full regression safety.
- Reduce future change amplification in `tests/test_workflow.py`.

## Non-Goals

- No production behavior redesign.
- No broad refactoring of unrelated test modules.
- No deletion based only on file size.
- No requirement to reduce total test count or total test lines by a fixed percentage.
- No replacement of real integration coverage with mocks when filesystem or process behavior is contractual.
- No prompt prose test cleanup; P2 owns that work.
- No new test governance rules; P3-1 is authoritative.

## Target Structure

The implementation should converge toward a structure similar to:

```text
tests/workflow/
  __init__.py
  helpers.py
  fixtures.py
  test_cli_start_status.py
  test_state_io.py
  test_definitions.py
  test_domains.py
  test_policies.py
  test_dispatch.py
  test_lifecycle.py
  test_governance.py
  test_terminal_evidence.py
  test_workflow_e2e.py
```

The exact structure may differ after repository analysis. The implementation must follow actual production module boundaries and avoid duplicate conceptual suites.

## Decisions

### 1. Baseline Before Movement

Before refactoring:

- run the current focused workflow suites;
- run the full regression suite;
- record test counts, commands, and results;
- identify existing skipped, flaky, or known failing tests;
- capture the current major test classes and domains.

The refactor must not silently absorb pre-existing failures.

### 2. Contract Inventory

Create a migration inventory mapping existing tests to:

```text
state
definitions
domains
policies
dispatch
lifecycle
governance
terminal_evidence
cli_contract
e2e_workflow
shared_fixture
obsolete_or_duplicate_candidate
```

Each moved, merged, or deleted test must have a destination or justification.

### 3. Module-Level Primary Coverage

Detailed permutations belong at module level when the contract can be verified without process-level orchestration.

Examples:

- state save/load and history movement;
- workflow definition validation;
- domain loader behavior;
- policy decisions and reasons;
- dispatch evidence persistence;
- lifecycle transition rules;
- governance and finalization checks;
- terminal evidence candidate resolution.

Module tests should call the extracted runtime API directly and use temporary workspaces only where filesystem behavior is part of the contract.

### 4. CLI Coverage Boundary

CLI tests remain for:

- argument parsing;
- invalid choice behavior;
- exit codes;
- stdout and stderr serialization;
- command routing;
- representative command-level filesystem effects;
- compatibility of supported command surfaces.

CLI tests must not duplicate every policy or state branch already covered directly at module level.

### 5. End-to-End Coverage Boundary

`test_workflow_e2e.py` retains a bounded set of scenarios covering:

- representative happy-path lifecycle;
- critical blocked and resume path;
- canonical roadmap-to-change promotion path;
- apply, review, finish, and history integration;
- critical data-loss or finalization protection;
- one representative legacy compatibility path where still supported.

Every edge case does not require an end-to-end subprocess test.

### 6. Shared Fixtures and Builders

Extract reusable helpers for:

- temporary repository/workspace creation;
- workflow definition copying;
- active-run state creation;
- roadmap item creation;
- spec or OpenSpec change creation;
- task-file creation;
- JSON/YAML loading;
- CLI invocation;
- Git fixture initialization where needed.

Helpers must expose domain intent rather than low-level file-writing duplication. They must not become a second implementation of production logic.

### 7. Parameterization Candidates

Consolidate cases when setup, execution, and assertion shape are equivalent.

Initial candidate patterns include:

- multiple governed actions returning the same reason under the same missing-state condition;
- equivalent accepted subject types or statuses;
- repeated malformed definitions differing only by field value;
- provider or slice variants sharing one evidence-resolution contract.

Do not parameterize semantically distinct blocker reasons merely because they return the same status code.

### 8. Observable Contract Preservation

Movement or consolidation must preserve:

- public command behavior;
- state schema and transitions;
- blocker reasons;
- persisted evidence;
- filesystem side effects;
- security and destructive-operation boundaries;
- supported legacy compatibility;
- failure diagnostics.

Line execution alone is not evidence that a contract remains protected.

### 9. Duplicate and Obsolete Tests

A test may be removed when:

- another clearer test fully subsumes the same observable contract;
- a parameterized matrix replaces equivalent standalone methods;
- detailed CLI coverage is replaced by direct module coverage plus representative CLI integration;
- the corresponding supported production behavior no longer exists.

Every deletion is recorded in the inventory with the surviving coverage location.

### 10. Incremental Migration Slices

The migration should proceed in bounded slices, for example:

1. shared helpers and state/definition tests;
2. domain and policy tests;
3. dispatch and terminal evidence tests;
4. lifecycle and governance tests;
5. CLI boundary cleanup;
6. end-to-end suite consolidation;
7. final removal or reduction of the legacy monolithic file.

Each slice must keep focused and full regression green before the next slice begins.

### 11. Legacy File Transition

`tests/test_workflow.py` may remain temporarily as a compatibility shell during migration. New detailed tests must not continue accumulating there once the corresponding domain suite exists.

The final state should either:

- remove the file; or
- retain only clearly named CLI/end-to-end coverage with a bounded responsibility.

A partial migration must document remaining classes and their planned destinations.

### 12. Import and Path Discipline

Test modules must import the canonical runtime implementation. They must not accidentally test distributed templates or copied runtime modules unless the test explicitly targets synchronization.

Path setup should be centralized. Repeated `sys.path` mutation across modules should be minimized and isolated in helpers or fixtures.

### 13. Test Runtime and Diagnostics

The refactor should improve or preserve:

- focused-suite runtime;
- failure localization;
- test node identifiers;
- cleanup reliability;
- deterministic temporary workspace behavior.

Performance improvement is desirable but not a hard acceptance threshold unless a baseline regression is material.

### 14. Evidence

Implementation evidence includes:

```json
{
  "workflow_test_modularization": {
    "baseline": {
      "commands": [],
      "result": "pass",
      "test_count": 0
    },
    "moved_tests": 0,
    "merged_tests": 0,
    "deleted_tests": 0,
    "new_domain_files": [],
    "remaining_legacy_classes": [],
    "inventory_path": "...",
    "focused_verification": [],
    "full_regression": "pass"
  }
}
```

Counts are descriptive and must not drive unsafe deletion.

### 15. Review Requirements

`review-agent` verifies:

- moved tests still protect the same observable contracts;
- helpers do not duplicate production logic;
- CLI and end-to-end deletions retain representative integration coverage;
- parameterization preserves readable failures;
- removed tests have documented surviving coverage;
- canonical runtime modules are tested rather than generated copies;
- the migration stays within the approved domain slice;
- focused and full regression pass.

### 16. Completion Gate

The change is complete when:

- all planned domain migrations are complete;
- the legacy file has a bounded responsibility or is removed;
- no unexplained duplicate workflow suites remain;
- migration inventory has no unresolved test entries;
- full regression passes;
- test discovery succeeds from repository root;
- temporary workspace cleanup remains reliable.

## Affected Areas

Expected areas include:

- `tests/test_workflow.py`
- `tests/test_workflow_modules.py`
- new `tests/workflow/` modules
- shared workflow test helpers and fixtures
- pytest configuration only if required for package discovery
- no production code unless a minimal testability seam is separately justified

## Acceptance Criteria

- A passing baseline is recorded before restructuring.
- Existing workflow tests are inventoried by domain.
- Detailed state, definition, domain, policy, dispatch, lifecycle, governance, and evidence cases move to appropriate module suites.
- CLI tests focus on command-surface contracts.
- End-to-end tests are bounded to representative cross-module scenarios.
- Repeated workspace setup is extracted into reusable helpers.
- Equivalent cases are parameterized where semantically appropriate.
- Deleted tests have documented surviving coverage.
- No new detailed domain tests are added to the legacy monolithic file after a domain migrates.
- Canonical runtime code remains the test target.
- Focused workflow suites pass after every migration slice.
- Full regression passes at completion.
- The final legacy workflow test file is removed or has a clearly bounded responsibility.
- P3-1 test evolution rules are followed throughout the migration.
