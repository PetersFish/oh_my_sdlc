# Derived Sync Hook Phase Awareness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Execute one bounded slice at a time and keep checkboxes synchronized.

**Goal:** Extend the already implemented derived-sync phase boundary so apply-phase commits allow attributable canonical-to-derived drift, review scope excludes unwritten generated targets, and finish still requires zero drift.

**Architecture:** Reuse the existing workflow runtime phase source and existing derived-artifact sync classification/mapping. Add one phase-aware policy layer at the current hook/check entrypoint instead of creating a new sync state machine or mapping table. Keep authored implementation scope separate from finish-owned generated cleanup.

**Tech Stack:** Python standard library, Git hooks, existing workflow runtime modules, existing sync scripts, pytest/unittest, Markdown agent contracts.

**Primary Spec:** `docs/superpowers/specs/2026-07-14-derived-sync-hook-phase-awareness.md`

**Existing Design Dependency:** `docs/superpowers/specs/2026-07-13-derived-sync-phase-boundary-design.md`

---

## Scope Guardrails

This plan MUST NOT:

- reintroduce write-producing sync in `implement-agent`;
- add a persisted `derived_sync` state machine;
- add dry-run target manifests or planned-target evidence;
- create a second canonical-to-derived mapping table;
- require separate generated commits;
- add tests that assert fixed prompt prose, headings, or sentences;
- redesign `install_skill.py` no-op behavior;
- broaden into general test-suite refactoring.

Executable tests are required only for hook policy, phase resolution, attribution, review filtering, and terminal enforcement code.

---

## Slice 1: Locate Existing Enforcement and Establish Baseline

### Task 1: Map Existing Hook, Phase, Sync, and Review Paths

**Files:**
- Inspect: `.githooks/`
- Inspect: `scripts/sync_derived_artifacts.py`
- Inspect: `.ai/workflows/scripts/`
- Inspect: review change-set validation modules
- Inspect: finish terminal validation modules
- Inspect: existing tests covering hooks, sync, review mismatch, and workflow phase

- [ ] **Step 1: Load repository memory and required implementation disciplines**

Load:

- `sdlc-repository-memory-load`
- `implementation-contract-discipline`
- `behavioral-test-design`

- [ ] **Step 2: Identify the real pre-commit or validation entrypoint**

Record:

- hook script path;
- Python helper/module invoked by the hook;
- current behavior when canonical files are staged and derived copies are stale;
- current behavior outside an active workflow.

Do not design a new hook entrypoint until the existing one is located.

- [ ] **Step 3: Identify authoritative workflow phase resolution**

Locate the existing runtime API or state reader that determines:

```text
active workflow exists
current phase
current run status
```

The implementation must reuse this source. It must not infer phase from agent name, branch, commit message, or changed paths.

- [ ] **Step 4: Identify canonical-to-derived classification logic**

Locate the logic already used by:

```bash
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

Record how it classifies:

- agent canonical changes;
- skill canonical changes;
- workflow/template changes;
- docs/test-only changes;
- full-mode fallback changes.

- [ ] **Step 5: Identify review mismatch computation**

Trace where `review_change_set_mismatch` is produced and determine whether it compares:

- implementation evidence against actual Git changes;
- expected generated paths against Git changes;
- full live worktree scope including unstaged generated drift;
- committed `base_ref..<head_ref>` scope.

- [ ] **Step 6: Run current focused baseline tests**

Use existing test files discovered above. At minimum run the focused suites for:

- derived sync classification;
- hook/pre-commit behavior;
- review change-set validation;
- finish terminal validation.

Record exact commands and results before modifications.

### Task 2: Confirm the Remaining Reproduction

- [ ] **Step 1: Create or reuse a temporary test fixture/repository state**

Model this scenario without modifying generated copies manually:

```text
active phase = apply_change
canonical agent or skill file changed/staged
derived provider copies remain stale
generated files are not staged
```

- [ ] **Step 2: Verify current failure mode**

Demonstrate which current component blocks:

- Git hook;
- review mismatch validation;
- finish validation;
- or none of the above.

If the reported issue is already fully resolved, stop and return evidence instead of implementing speculative policy.

- [ ] **Step 3: Capture the minimal failing contract**

The RED condition must assert executable behavior, for example:

```text
apply_change + attributable canonical drift + no generated edits -> hook allows commit
```

Do not add prompt string-presence tests.

---

## Slice 2: Reusable Phase and Drift Policy Model

### Task 3: Add Focused Failing Tests for Policy Decisions

**Files:**
- Modify: the existing hook/sync policy test module discovered in Slice 1
- Modify or create: a narrowly scoped policy test module only if no suitable module exists

- [ ] **Step 1: Add RED cases for apply-phase allowance**

Cover:

1. canonical Agent change with attributable stale provider copies;
2. canonical Skill change with attributable stale provider copies;
3. recognized workflow/template canonical change when covered by existing mapping;
4. generated targets not staged and not manually modified.

Expected decision:

```text
allow
```

- [ ] **Step 2: Add RED cases for apply-phase rejection**

Cover distinct reasons:

```text
manual_generated_artifact_change
generated_artifact_mixed_with_authored_commit
unattributed_generated_drift
unrelated_generated_drift
missing_workflow_phase_context
```

Use parameterization only when setup, execution path, and assertion shape are equivalent.

- [ ] **Step 3: Add compatibility cases**

Cover:

- no active workflow -> preserve existing hook behavior;
- active workflow in a non-apply phase -> do not apply the apply allowance;
- unresolved/corrupt active phase -> explicit context failure.

- [ ] **Step 4: Run focused tests and confirm RED**

Run the smallest relevant test subset and record the expected failures.

### Task 4: Implement One Phase-Aware Policy Function

**Files:**
- Modify: existing hook/check helper module
- Modify: existing workflow phase resolution integration
- Reuse: existing sync classification/mapping module

- [ ] **Step 1: Define a small policy result**

Use the repository's existing result conventions. A conceptual shape is:

```python
HookPolicyResult(
    allowed: bool,
    reason: str | None,
    details: dict,
)
```

Do not introduce a persisted runtime state.

- [ ] **Step 2: Resolve lifecycle phase from runtime state**

Rules:

- active run with phase `apply_change` -> apply policy;
- active finish/finalization context -> strict clean policy;
- no active run -> existing non-workflow behavior;
- active run but unreadable phase -> explicit failure.

- [ ] **Step 3: Reuse existing canonical attribution**

Feed changed/staged files into existing sync classification logic.

The hook policy may adapt the existing result, but must not duplicate mappings such as:

```text
agents/* -> provider agent copies
skills/* -> provider skill copies
workflow source -> template/distributed copies
```

- [ ] **Step 4: Distinguish stale from manually changed generated files**

The policy must differentiate:

- generated files merely stale because canonical changed;
- generated files modified in the worktree;
- generated files staged in the authored commit;
- unrelated generated drift.

Do not treat an unwritten expected target as a changed file.

- [ ] **Step 5: Return stable diagnostic reasons**

Prefer the spec reasons when compatible with existing error conventions:

```text
manual_generated_artifact_change
generated_artifact_mixed_with_authored_commit
unattributed_generated_drift
unrelated_generated_drift
missing_workflow_phase_context
```

- [ ] **Step 6: Run focused policy tests and confirm GREEN**

---

## Slice 3: Integrate Phase-Aware Policy into the Git Hook

### Task 5: Update the Existing Hook Entry Point

**Files:**
- Modify: existing `.githooks/` entrypoint or its invoked validation script
- Modify: executable hook tests

- [ ] **Step 1: Preserve ordinary checks**

The new allowance must not skip unrelated repository checks, including any existing validation for:

- malformed files;
- invalid workflow templates;
- manually modified generated artifacts;
- unrelated dirty state;
- ordinary non-workflow commits.

- [ ] **Step 2: Apply allowance only during `apply_change`**

Allow the commit only when:

- at least one recognized canonical source changed;
- expected stale targets are attributable through existing mapping;
- generated files are neither modified nor staged;
- no unrelated drift exists.

- [ ] **Step 3: Reject mixed authored/generated commits**

A commit containing both canonical authored files and generated provider copies must fail during apply, even when generated content matches what sync would produce.

Generated cleanup remains finish-owned.

- [ ] **Step 4: Produce actionable hook output**

Error output must state:

- the stable reason;
- offending paths when available;
- whether the user must remove generated changes, restore unrelated drift, or repair workflow context.

Expected canonical drift must not print a warning that looks like a failure.

- [ ] **Step 5: Add subprocess-level hook tests where practical**

At least one representative integration test should execute the real hook/check entrypoint for:

- apply allowance;
- manual generated edit rejection;
- no-active-workflow compatibility.

Detailed permutations should remain in the lower-level policy tests.

- [ ] **Step 6: Run hook-focused verification**

Record exact commands and results.

---

## Slice 4: Correct Review Change-Set Validation

### Task 6: Reproduce and Fix Stale-Derived Review Mismatch

**Files:**
- Modify: existing review change-set validation module only if the reproduction proves a defect
- Modify: existing review validation tests
- Clarify: `agents/review-agent.md` only if executable behavior alone cannot express the contract

- [ ] **Step 1: Add a failing review case**

Scenario:

```text
implementation authored canonical file
provider copies are stale but unchanged
implementation changed_files matches actual authored Git scope
```

Expected:

```text
no review_change_set_mismatch
```

- [ ] **Step 2: Retain rejection for actual generated modifications**

Add or preserve cases where generated files are:

- modified;
- staged;
- committed inside the reviewed range;
- listed inconsistently in implementation evidence.

These remain real change-set mismatches or generated-artifact violations.

- [ ] **Step 3: Base comparison on actual Git changes**

Review validation must not synthesize expected generated targets into the change set.

For sliced review, preserve the existing authoritative commit-range behavior. For live-worktree review, compare against files actually modified/staged/untracked according to the existing contract.

- [ ] **Step 4: Make the smallest code change**

If current code is already correct and only the prompt wording is ambiguous, do not modify runtime code or tests. Clarify the canonical review-agent instruction without adding prose-presence tests.

- [ ] **Step 5: Run focused review tests**

Confirm:

- stale but unwritten targets do not mismatch;
- actual generated edits still fail;
- unrelated changed files still fail;
- ordinary source/test scope behavior is unchanged.

---

## Slice 5: Enforce Strict Finish Closure

### Task 7: Verify and Harden Terminal Drift Enforcement

**Files:**
- Modify: finish validation/runtime code only if existing enforcement is incomplete
- Modify: existing terminal/finish tests
- Clarify: `agents/finish-agent.md` only if necessary

- [ ] **Step 1: Inspect current finish sequence**

Confirm that finish currently performs:

```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

or the appropriate full-mode equivalent when sync-rule files changed.

- [ ] **Step 2: Add RED cases only for missing executable guarantees**

Potential cases:

- finish completion attempted without required sync;
- sync check reports remaining drift;
- unrelated generated changes remain;
- manually changed generated file survives sync;
- terminal worktree policy remains dirty.

Expected terminal reason:

```text
derived_artifact_drift_unresolved
```

Reuse existing terminal reason conventions if a canonical equivalent already exists.

- [ ] **Step 3: Require clean terminal state**

Finish completion must fail until:

- write-producing sync completed where required;
- read-only check passes;
- generated cleanup is included in finish evidence;
- unrelated dirty files are absent.

- [ ] **Step 4: Avoid changing implementation ownership**

Do not make implement-agent sync or test generated copies. The fix must remain entirely in finish/terminal enforcement.

- [ ] **Step 5: Run focused terminal tests**

---

## Slice 6: Canonical Agent Clarifications and Distribution

### Task 8: Update Only Necessary Agent Contracts

**Files:**
- Modify if needed: `agents/review-agent.md`
- Modify if needed: `agents/finish-agent.md`
- Modify if needed: `agents/implement-agent.md`
- Derived copies: finish-owned synchronization

- [ ] **Step 1: Keep existing phase-boundary wording authoritative**

Do not duplicate the full specification in each agent.

Only add role-specific clarifications:

- implement-agent: expected distributed-copy drift is not an apply blocker and generated copies remain untouched;
- review-agent: stale but unwritten derived targets are not authored scope;
- finish-agent: finalization requires sync and clean check.

- [ ] **Step 2: Do not add prompt prose tests**

Agent Markdown changes are instructional prose unless frontmatter or machine-read structure changes.

Verification is inspection plus existing artifact syntax checks. Do not add `assertIn()` tests for the new wording.

- [ ] **Step 3: Leave derived copies untouched during implementation and review**

Provider copies under `.opencode/`, `.claude/`, and `.cursor/` are synchronized by finish-agent according to the already implemented phase-boundary design.

---

## Slice 7: Full Verification and Handoff

### Task 9: Run Focused and Full Regression

- [ ] **Step 1: Run policy and hook tests**

Include:

- phase resolution;
- apply allowance;
- manual generated edit rejection;
- mixed commit rejection;
- unattributed/unrelated drift rejection;
- non-workflow compatibility.

- [ ] **Step 2: Run review validation tests**

Include stale-unwritten and actual-generated-change scenarios.

- [ ] **Step 3: Run finish/terminal tests**

Require clean sync closure.

- [ ] **Step 4: Run existing derived sync suites**

At minimum include the existing suites for:

- `sync_derived_artifacts.py`;
- workflow/template synchronization;
- skill installation/no-op behavior when touched indirectly;
- wrapper/runtime validation affected by code changes.

- [ ] **Step 5: Run full project regression**

```bash
python3 -m pytest tests/ -v
```

Do not return implementation success without a passing full regression or individually documented accepted pre-existing/environment failures under the repository's current verification contract.

### Task 10: Review Scope and Finish Sync

- [ ] **Step 1: Confirm implementation change set contains authored files only**

Before review, provider copies must remain unchanged.

- [ ] **Step 2: Review commit range or live authored scope**

Confirm expected stale targets do not appear as synthesized changes.

- [ ] **Step 3: Run finish-owned derived synchronization**

Use incremental mode for ordinary affected canonical changes and full mode only when sync classification/rule files require it.

- [ ] **Step 4: Run final sync check**

Require zero drift.

- [ ] **Step 5: Verify terminal repository state**

Confirm:

- generated changes are attributable to the sync mechanism;
- no unrelated dirty files remain;
- final worktree and workflow terminal policy are clean.

---

## Acceptance Verification Matrix

| Scenario | Apply hook | Review | Finish |
|---|---|---|---|
| Canonical Agent change; provider copies stale but untouched | Allow | Review canonical authored change | Sync and require clean |
| Canonical Skill change; provider copies stale but untouched | Allow | Review canonical authored change | Sync and require clean |
| Generated provider file manually modified | Reject | Reject if reached | Reject |
| Generated file staged with canonical change | Reject | Reject if reached | N/A |
| Unrelated generated drift exists | Reject | Report unrelated scope where applicable | Reject |
| Drift cannot be attributed to canonical source | Reject | Do not synthesize ownership | Reject |
| No active workflow | Preserve existing behavior | Preserve existing behavior | Preserve existing behavior |
| Active workflow phase unreadable | Explicit context failure | Explicit context failure if needed | Explicit context failure |
| Finish sync check still dirty | N/A | N/A | Block with terminal drift reason |

---

## Completion Criteria

- [ ] Existing derived-sync phase-boundary ownership remains unchanged.
- [ ] Apply-phase authored commits allow attributable stale derived targets.
- [ ] Apply hook rejects manual, mixed, unrelated, and unattributed generated changes.
- [ ] Phase is resolved from existing workflow runtime state.
- [ ] Existing sync mapping logic is reused.
- [ ] Review does not mismatch solely because unwritten generated targets are stale.
- [ ] Review still rejects generated files actually changed during implementation.
- [ ] Finish requires successful sync, clean check, and clean terminal state.
- [ ] Non-workflow hook behavior remains compatible.
- [ ] No new derived-sync state machine or manifest exists.
- [ ] No prompt prose-presence tests were added.
- [ ] Focused tests and full regression pass.
