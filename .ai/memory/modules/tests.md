---
id: tests
type: module
title: Tests
summary: Test infrastructure and test image assets.
parent_id: root
sync_status: synced
evidence_mode: discovery
linked_commits: ["ab06a0287f43ec7e50b280ce1bddd2cdc39d3aad", "b368a7f731ea3cf734827fee0b5484b72eb9319b"]
linked_specs: []
linked_sessions: ["20260629-202700", "2026-07-09-workflow-runtime-execution-context-and-agent-result-integrity", "2026-07-11-workflow-final-tail-commit"]
updated_at: 2026-07-11T00:00:00Z
confidence: high
tags: [tests]
owned_paths: [tests/]
path_hints: [tests/]
keywords: [test, testing]
test_paths: [tests/]
spec_paths: []
---

# Tests

## Current Understanding

Test directory containing test scripts and image assets for testing.

## Evidence

Directory discovery. Contains test scripts for workflow orchestration, prompt contracts, derived artifact sync, evalops, and SDLC orchestrator routing.

## Key Files

- `tests/test_workflow.py` — workflow.py preflight, ensure-run, complete-phase, governance, runtime context, and final-commit tests (81+11 tests)
- `tests/test_wrapper_contracts.py` — agent prompt output contract and frontmatter assertions
- `tests/test_sync_derived_artifacts.py` — derived artifact sync integration tests
- `tests/test_evalops_root.py` — evalops root-level tests
- `tests/test_evalops_skill.py` — evalops skill-level tests
- `tests/test_sdlc_orchestrator.py` — orchestrator routing tests

## Operational Guidance

## Child Modules

## Key Files

## Entry Points

## Tests

## Related Specs

## Known Pitfalls

## Update Notes

First sync after memory reset. Created from discovery.
Updated after `workflow-final-tail-commit`: added final-commit test class (11 tests) covering missing run_id, history run not found, not-done run, run_id mismatch, noop on clean tree, allowlisted history file commit, unrelated file exclusion, pre-staged unrelated file preservation, run_id-scoped allowlist, superpowers archive artifact commit, push success, noop-with-push, and push failure reporting.
