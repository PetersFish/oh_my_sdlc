# Deferred Derived Sync Lifecycle

## Context

Canonical Agent and Skill changes create expected drift in generated provider copies and templates. The current lifecycle can treat that drift as an `apply_change` blocker even when the authored change is valid. Running write-producing synchronization during implementation avoids the blocker but introduces generated files into the implementation change set, causing review-scope churn and changed-file mismatch.

Expected canonical-to-derived drift must become a governed intermediate state. Authored changes are implemented and reviewed first; generated artifacts are synchronized and verified during finalization.

## Goals

- Expected derived drift does not block `apply_change`.
- `implement-agent` performs non-mutating sync planning only.
- `review-agent` reviews authored changes without requiring generated copies.
- `finish-agent` owns write-producing synchronization.
- Apply-phase Git hooks allow declared deferred drift.
- Finish-phase validation requires zero remaining drift.
- Actual generated scope cannot silently exceed the planned target set.

## Non-Goals

- No prompt-test cleanup.
- No Eval framework changes.
- No general test-suite refactoring.
- No change to ordinary code TDD rules.
- No new canonical source hierarchy.
- No parallel generated-artifact commits.

## Decisions

### 1. Derived Sync State

Persist one of:

```text
not_required
deferred
in_progress
clean
blocked
```

`deferred` means canonical sources changed, generated targets are expected to be stale, and `finish-agent` owns resolution.

Expected drift during `apply_change` is `deferred`, not `blocked`.

### 2. Read-Only Planning

The sync tool must provide a non-mutating planning mode, for example:

```bash
python3 scripts/sync_derived_artifacts.py --dry-run --changed-files-from-git
```

It returns:

```json
{
  "drift_detected": true,
  "canonical_sources": ["agents/implement-agent.md"],
  "planned_writes": [
    ".opencode/agents/implement-agent.md",
    ".claude/agents/implement-agent.md",
    ".cursor/agents/implement-agent.md"
  ],
  "planned_deletes": [],
  "unexpected_existing_changes": []
}
```

Planning must not modify generated files, metadata, timestamps, manifests, or repository state.

### 3. Implement-Agent Ownership

When canonical sources change, `implement-agent` must:

1. identify changed canonical sources;
2. run non-mutating sync planning;
3. record planned generated targets;
4. leave generated files untouched;
5. return success when implementation verification otherwise passes.

It must not:

- run `sync_derived_artifacts.py --fix`;
- run `setup_agents.py --force`;
- run write-producing installation commands;
- manually edit generated provider copies;
- block solely because expected drift exists;
- include planned generated targets in authored `changed_files[]`.

### 4. Deferred Sync Evidence

Implementation evidence includes:

```json
{
  "derived_sync": {
    "status": "deferred",
    "owner": "finish-agent",
    "canonical_sources": ["agents/implement-agent.md"],
    "planned_targets": [
      ".opencode/agents/implement-agent.md",
      ".claude/agents/implement-agent.md",
      ".cursor/agents/implement-agent.md"
    ]
  }
}
```

If no affected canonical source changed, use `not_required` with empty source and target lists.

### 5. Authored and Generated Change Sets

Evidence distinguishes:

```json
{
  "change_set": {
    "authored_files": [],
    "generated_files": [],
    "deferred_generated_targets": []
  }
}
```

During implementation and review:

- `authored_files` is authoritative;
- `generated_files` is normally empty;
- `deferred_generated_targets` records future finish scope.

Planned targets are not current Git changes.

### 6. Review-Agent Scope

`review-agent` reviews:

- canonical Agent and Skill changes;
- executable code;
- manually authored tests;
- deferred-sync evidence and target plausibility.

It must not:

- require generated copies before review;
- run write-producing synchronization;
- count deferred targets as changed-file mismatches;
- treat generated copies as independently authored semantics.

A review change-set mismatch compares Git state with `authored_files`, excluding declared deferred targets that have not yet been written.

### 7. Blocking Conditions

Expected drift does not block. `blocked` is reserved for:

- affected targets cannot be determined;
- generated files were already manually modified;
- dry-run planning fails;
- drift has no identifiable canonical source;
- ownership is ambiguous;
- unrelated generated changes are present;
- final sync fails or remains dirty.

### 8. Phase-Aware Git Hook

#### Apply-Change Commit

The hook permits canonical drift when:

- canonical sources changed;
- sync status is `deferred`;
- planned targets are recorded;
- generated files are not mixed into the authored commit;
- no unrelated generated modifications exist.

The hook rejects undeclared drift, manual generated-file edits, missing planning evidence, and generated files mixed into the authored implementation commit.

#### Finish Commit

The hook requires:

- write-producing sync completed;
- read-only sync check reports clean;
- actual generated files are within approved targets;
- no unrelated dirty files remain.

### 9. Finish-Agent Ownership

After review passes, `finish-agent` must:

1. load deferred-sync evidence;
2. run write-producing synchronization;
3. collect actual writes and deletes;
4. compare actual scope with planned targets;
5. block on unexpected scope expansion;
6. run sync check and require clean status;
7. run final verification;
8. commit generated artifacts;
9. verify a clean worktree.

Unexpected scope returns `derived_sync_scope_expanded` and must not be silently committed.

### 10. Commit Boundary

Preferred history:

```text
Commit A — authored implementation
- canonical Agent or Skill files
- executable code
- manually authored tests

Commit B — generated finalization
- provider copies
- generated templates
- generated metadata
```

Commit B belongs to `finish-agent`, not to the implementation slice's authored review scope.

## Agent Changes

- `implement-agent`: dry-run planning, deferred evidence, no write-producing sync.
- `review-agent`: authored-scope review and deferred-target exclusion.
- `finish-agent`: generated sync, scope validation, final clean gate.
- `dev-orchestrator`: preserve and forward deferred-sync evidence.

## Affected Areas

- `scripts/sync_derived_artifacts.py`
- Git hook or pre-commit validation code
- workflow runtime evidence schema
- canonical agent prompts
- project bootstrap workflow templates
- executable tests for sync planning, hook policy, and scope validation
- distributed copies produced only after finish synchronization

## Acceptance Criteria

- Canonical Agent or Skill changes do not block solely because generated copies are stale.
- `implement-agent` records expected drift as `deferred`.
- Dry-run planning produces no writes.
- Generated files remain absent from implementation review scope.
- `review-agent` excludes deferred targets from changed-file mismatch.
- Apply-phase Git hooks permit valid declared drift and reject undeclared drift.
- Manually modified generated files are rejected before finish.
- `finish-agent` performs write-producing sync.
- Actual generated scope cannot exceed the approved target set.
- Final sync check reports clean.
- Generated artifacts are committed separately where practical.
- Final worktree is clean.
- Existing executable sync and hook tests pass.
