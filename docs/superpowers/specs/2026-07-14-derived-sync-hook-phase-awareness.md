# Derived Sync Hook Phase Awareness

## Context

This specification extends the already implemented:

```text
docs/superpowers/specs/2026-07-13-derived-sync-phase-boundary-design.md
```

That design already establishes:

- `implement-agent` does not run write-producing derived-artifact synchronization during `apply_change`;
- canonical Agent, Skill, and template drift is expected during implementation;
- `finish-agent` owns write-producing synchronization after review;
- generated changes belong to finish cleanup rather than implementation scope;
- synchronization must be clean before finalization.

A remaining enforcement gap may still cause valid canonical changes to be blocked:

- a Git hook may require derived artifacts to be synchronized before an `apply_change` commit;
- review change-set validation may compare authored evidence against generated or stale derived paths;
- finalization may not distinguish temporary apply-phase drift from unresolved terminal drift.

This follow-up does not redesign sync ownership or add a derived-sync state machine. It only makes existing hook and review enforcement aware of the lifecycle phase boundary.

## Goals

- Allow expected canonical-to-derived drift during an `apply_change` commit.
- Continue rejecting manually edited or unrelated generated artifacts.
- Ensure review change-set validation remains limited to authored implementation scope.
- Require zero derived drift before finish completion and final commit.
- Preserve the existing `implement-agent` and `finish-agent` ownership boundary.

## Non-Goals

- No new workflow phase.
- No new persisted derived-sync state machine.
- No implement-agent dry-run target planning requirement.
- No planned-target manifest.
- No separate generated commit requirement.
- No changes to prompt-test policy.
- No general test-suite refactoring.
- No change to `install_skill.py` no-op behavior.
- No change to canonical-to-derived source ownership.
- No support in this change for canonical Skill directory deletion or rename;
  those operations require a separate distributed-removal contract.

## Decisions

### 1. Existing Sync Ownership Remains Authoritative

During `apply_change`, `implement-agent` MUST NOT run:

```text
sync_derived_artifacts.py --fix
setup_agents.py --force
install_skill.py
```

It MUST NOT manually edit generated provider copies.

`finish-agent` remains the sole owner of write-producing derived synchronization after review.

This specification does not require `implement-agent` to run `--check` or `--dry-run` planning. The existing phase-boundary design remains authoritative on that point.

### 2. Apply-Phase Hook Policy

When the active workflow phase is `apply_change`, a commit hook MUST allow stale derived artifacts when all of the following are true:

- at least one recognized canonical source changed;
- the stale generated targets are attributable to those canonical changes through the existing sync mapping;
- generated targets are not staged in the authored commit;
- generated targets were not manually modified;
- no unrelated generated drift exists;
- the commit otherwise satisfies ordinary repository and workflow checks.

Expected stale generated files are not implementation failures and MUST NOT require synchronization before the authored commit.

### 3. Apply-Phase Hook Rejections

The apply-phase hook MUST reject:

- manually modified generated provider copies;
- staged generated files mixed into the authored implementation commit;
- generated drift that cannot be attributed to a changed canonical source;
- unrelated pre-existing generated drift;
- canonical and generated files both edited manually;
- missing or invalid workflow phase context when phase-specific policy is required.

The rejection reason SHOULD distinguish these conditions from ordinary expected drift.

Recommended reasons:

```text
manual_generated_artifact_change
generated_artifact_mixed_with_authored_commit
unattributed_generated_drift
unrelated_generated_drift
missing_workflow_phase_context
ambiguous_workflow_run_context
workflow_checkout_mismatch
unsupported_canonical_skill_removal
```

### 4. Review Scope Uses Authored Changes

During review, the authoritative scope is the authored Git change set produced by implementation.

Review-agent MUST:

- review canonical Agent, Skill, and template changes;
- review executable code and manually authored tests;
- compare implementation evidence against actual authored Git changes;
- reject generated files that were manually changed during implementation.

Review-agent MUST NOT:

- require stale generated copies to be synchronized before review;
- include unstaged expected derived drift as authored `changed_files`;
- report `review_change_set_mismatch` solely because generated copies remain stale;
- treat generated copies as independently authored semantic changes.

The existing live Git diff remains authoritative for files actually changed. Expected but unwritten generated targets are not part of that diff and must not be synthesized into review scope.

### 5. Finish-Phase Hook Policy

During finish or finalization, temporary drift is no longer allowed.

Before final commit or workflow completion, `finish-agent` MUST:

1. run the existing write-producing derived synchronization;
2. run the existing read-only synchronization check;
3. require the check to report clean;
4. include generated changes in finish cleanup evidence;
5. verify no unrelated dirty files remain.

The workflow runtime MUST independently execute the read-only synchronization
check before terminal movement. A worker-provided boolean such as
`derived_artifacts_synced: true` is supporting evidence, not proof that the
check ran or passed. Terminal movement MUST consume the actual check exit code
and fail closed when the check cannot run.

The terminal check root MUST follow the existing branch-finish decision and
execution context. Use the surviving worktree for `keep_branch` or
`create_pr`; use the control/main checkout only after `merge_local` has made
the reviewed result available there or `discard` has removed it. A missing or
contradictory target root must block rather than silently checking a different
checkout.

The finish-phase hook MUST reject completion when:

- derived synchronization has not been run where required;
- the read-only check still reports drift;
- generated files were manually changed outside the sync mechanism;
- unrelated generated changes remain;
- the final worktree is not clean according to terminal policy.

Recommended terminal blocker:

```text
derived_artifact_drift_unresolved
```

### 6. Phase Resolution

Hook policy must resolve the current lifecycle phase from the existing workflow runtime state.

It MUST NOT infer phase solely from:

- commit message;
- changed filenames;
- current agent name;
- branch name.

If no active workflow exists, existing non-workflow hook behavior remains unchanged.

If an active workflow exists but its phase cannot be resolved safely, the hook should fail with an explicit context error rather than applying the wrong phase policy.

#### Checkout-To-Run Binding

The hook MUST bind the current Git checkout to exactly one workflow run before
using phase-specific policy:

1. resolve the current checkout root with Git;
2. inspect existing active workflow state from the authoritative control root;
3. match the checkout root against normalized run context, preferring
   `context.worktree_path` for worktree-mode runs and the control repository
   root for main-checkout runs;
4. apply phase-specific policy only when exactly one active run matches;
5. reject ambiguous matches, corrupt pointers, unreadable matching state, or a
   run whose recorded worktree path contradicts the current checkout.

An active run belonging to another worktree MUST NOT change the current
checkout's hook policy. If no run matches the current checkout, existing
non-workflow behavior applies even when unrelated active runs exist elsewhere.

### 7. Canonical Source Attribution

Expected apply-phase drift may be allowed only when the repository can attribute it to a changed canonical source using existing synchronization ownership rules.

Examples include:

```text
agents/* -> .opencode/agents/*, .claude/agents/*, .cursor/agents/*
skills/* -> distributed skill copies
workflow templates -> installed/generated workflow copies
```

Implementation should reuse existing sync discovery and mapping logic rather than create a second independent mapping table inside the hook.

Attribution MUST be path-aware rather than suite-aware. The shared
classification result must distinguish at least:

```text
staged_canonical_paths
expected_derived_domains
actual_dirty_generated_paths
actual_staged_generated_paths
detected_stale_generated_paths
attributable_stale_generated_paths
unattributed_generated_paths
```

Domain-level values such as `agents: true` or `workflows: true` are not enough
to prove that every failing generated path belongs to the staged canonical
change. Existing mappings such as `sync_templates.py`'s governed workflow file
list and the existing Agent/Skill target rules must be exported or adapted as
the shared source of truth.

Git status alone is insufficient: a generated copy can be clean relative to
`HEAD` yet stale relative to a canonical source committed earlier. The policy
MUST consume path-level results from a full read-only derived synchronization
check, partition every stale path into attributable or unattributed sets, and
reject any unattributed stale path. Suppressing an entire failing Agent, Skill,
or workflow suite is forbidden.

The attribution contract MUST include all governed workflow runtime modules,
not only `workflow.py` and `sdlc-main.yaml`.

#### Index And Worktree Separation

Pre-commit policy evaluates the commit represented by the Git index. It MUST:

- derive authored canonical inputs from `git diff --cached`;
- preserve rename and deletion status when collecting staged paths;
- inspect the complete porcelain worktree state separately for generated-file
  modifications and unrelated dirty paths;
- never use a combined `git diff HEAD` path set as the authored commit scope;
- avoid reading unstaged canonical content as if it were the staged content.

Partial staging and additional unstaged canonical edits MUST NOT broaden the
allowance granted to the staged commit.

Canonical Skill directory deletion and rename are outside this change. The
apply hook MUST fail with an explicit unsupported-operation reason rather than
allowing a commit that the current finish sync cannot close.

Recommended reason:

```text
unsupported_canonical_skill_removal
```

### 8. No New Prompt Prose Tests

Changes to Agent Markdown needed by this specification do not require tests that assert fixed instructional sentences or headings.

Executable tests are appropriate for:

- phase resolution;
- hook policy decisions;
- canonical-source attribution;
- rejection of manual generated edits;
- apply-phase allowance;
- finish-phase clean enforcement;
- review change-set filtering implemented in code.

Current review scope is agent-governed rather than enforced by a standalone
runtime comparator. If reproduction confirms that stale but unwritten targets
are already absent from Git-derived review scope, verification for that branch
is an executable Git fixture plus manual inspection of the canonical agent
contract. This specification does not require a new review-policy subsystem
solely to make prompt behavior executable.

### 9. Phase-Appropriate Regression Ordering

Verification is split across the ownership boundary:

- During `apply_change`, run focused and broad executable suites that do not
  require generated copies to have already been synchronized. Repository-level
  distribution-consistency tests that fail only because of expected phase
  drift must be recorded as phase-deferred, not accepted as generally passing.
- During finish cleanup, run write-producing synchronization, the read-only
  check, every phase-deferred distribution-consistency test, and then the full
  project regression.

A failure may be phase-deferred only when its exact test id is known and the
same test passes after finish-owned synchronization. Other failures remain
ordinary implementation failures.

## Affected Areas

Expected affected areas include:

```text
Git hook or pre-commit validation code
workflow phase resolution helpers
checkout-to-run binding helpers
staged-index and worktree status classification helpers
review change-set validation code, if it currently includes expected derived drift
finish terminal validation
existing executable hook and workflow tests
canonical Agent documentation only when clarification is required
```

The implementation must first locate the existing hook and sync mapping logic and extend it. It must not introduce duplicate lifecycle or derived-sync subsystems.

## Acceptance Criteria

- The existing 2026-07-13 derived-sync phase-boundary design remains the source of truth for sync ownership.
- An authored canonical Agent or Skill change can be committed during `apply_change` without first synchronizing provider copies.
- The apply allowance is based on staged index scope, not combined staged and unstaged changes.
- Expected stale generated copies do not produce an apply-phase blocker.
- Manually modified generated copies are rejected during implementation.
- Generated files cannot be mixed into the authored implementation commit.
- Unrelated or unattributed generated drift remains blocked.
- Review-agent does not report change-set mismatch solely because expected generated copies are stale.
- Review scope remains based on actual authored Git changes.
- Finish-agent performs write-producing synchronization after review.
- Finish completion is blocked while derived drift remains unresolved.
- Phase policy is resolved from workflow runtime state rather than commit metadata.
- A checkout is bound to exactly one matching active run before phase policy is applied.
- Active runs for other worktrees do not affect the current checkout.
- Ambiguous, corrupt, or contradictory run binding fails closed.
- Attribution reports concrete generated paths and detects unrelated drift within the same sync domain.
- Governed `workflow_runtime/*.py` files participate in workflow attribution.
- Canonical Skill deletion or rename is explicitly rejected as unsupported by this change.
- Existing non-workflow hook behavior remains compatible.
- Terminal movement executes and consumes an independent read-only sync check rather than trusting worker evidence alone.
- Phase-deferred distribution tests pass after finish-owned synchronization, followed by a passing full regression.
- No new derived-sync state machine, dry-run manifest, or target-planning contract is introduced.
- Executable hook, attribution, phase-binding, and terminal-policy tests pass.
- Review behavior is changed only if a reproduction demonstrates a real executable defect.
