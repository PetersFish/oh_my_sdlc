# Derived Sync Hook Phase Awareness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the already implemented derived-sync phase boundary so apply-phase commits allow attributable canonical-to-derived drift, review scope excludes unwritten generated targets, and finish still requires zero drift.

**Architecture:** Reuse the existing workflow runtime phase source and existing derived-artifact sync classification/mapping. Add one phase-aware policy layer at the current hook/check entrypoint instead of creating a new sync state machine or mapping table. Keep authored implementation scope separate from finish-owned generated cleanup.

**Tech Stack:** Python standard library, Git hooks, existing workflow runtime modules, existing sync scripts, pytest/unittest, Markdown agent contracts.

**Primary Spec:** `docs/superpowers/specs/2026-07-14-derived-sync-hook-phase-awareness.md`

**Existing Design Dependency:** `docs/superpowers/archive/specs/2026-07-13-derived-sync-phase-boundary-design.md`

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
- support canonical Skill directory deletion or rename; reject those operations
  explicitly until a distributed-removal contract exists.

Executable tests are required for hook policy, phase resolution, attribution,
Git review-scope fixtures, and terminal enforcement code. Agent prose itself is
verified by inspection rather than fixed-string assertions.

## Resolved Implementation Architecture

Use one Python policy entrypoint invoked by the existing shell hook:

```text
.githooks/pre-commit
  -> python3 scripts/derived_sync_hook_policy.py --root <checkout-root>
  -> structured exit code + JSON/plain diagnostics
```

`scripts/derived_sync_hook_policy.py` owns only orchestration and pure policy:

- collect staged index entries with `git diff --cached --name-status -z`;
- collect complete dirty state with `git status --porcelain=v1 -z`;
- discover Git worktrees with `git worktree list --porcelain`;
- bind the current checkout to exactly one active workflow run;
- call shared classification exported by `scripts/sync_derived_artifacts.py`;
- return a stable allow/reject result without writing files.

Do not duplicate canonical mappings in the new module. Extend
`scripts/sync_derived_artifacts.py` to expose path-aware classification using:

- its existing Agent and Skill target constants;
- the governed live/template pairs exported by
  `skills/sdlc-project-bootstrap/scripts/sync_templates.py`;
- the existing full-mode sync-rule list.

Normalize read-only checker output at the checker boundary rather than parsing
human-readable text. `sync_templates.py` and
`check_skill_distribution.py` already support JSON. Extend
`scripts/setup_agents.py --check` with JSON output that identifies each stale
target path, then have the aggregate entrypoint consume those structured
reports.

The policy model must keep these inputs separate:

```text
staged index paths and statuses
unstaged/untracked worktree paths and statuses
matching workflow run and phase
expected generated targets/domains
actual dirty or staged generated paths
path-level stale targets reported by full read-only checks
```

Terminal enforcement belongs in workflow runtime lifecycle code. Before
`cmd_done` or terminal `cmd_advance` moves a run to history, execute the real
read-only derived sync check and consume its exit status. Finish-agent evidence
remains required but is not a substitute for this check.

---

## Slice 1: Locate Existing Enforcement and Establish Baseline

### Task 1: Map Existing Hook, Phase, Sync, and Review Paths

**Files:**
- Inspect: `.githooks/pre-commit`
- Inspect: `scripts/sync_derived_artifacts.py`
- Inspect: `skills/sdlc-project-bootstrap/scripts/sync_templates.py`
- Inspect: `.ai/workflows/scripts/workflow_runtime/state.py`
- Inspect: `.ai/workflows/scripts/workflow_runtime/lifecycle.py`
- Inspect: `.ai/workflows/scripts/workflow_runtime/dispatch.py`
- Inspect: `agents/review-agent.md`
- Inspect: `agents/finish-agent.md`
- Inspect: `tests/test_precommit_hook.py`
- Inspect: `tests/test_sync_derived_artifacts.py`
- Inspect: `tests/test_workflow.py`

- [x] **Step 1: Load repository memory and required implementation disciplines**

Load:

- `sdlc-repository-memory-load`
- `implementation-contract-discipline`
- `behavioral-test-design`

- [x] **Step 2: Identify the real pre-commit or validation entrypoint**

Record:

- hook script path;
- Python helper/module invoked by the hook;
- current behavior when canonical files are staged and derived copies are stale;
- current behavior outside an active workflow.

Baseline facts to confirm rather than rediscover:

- `.githooks/pre-commit` currently implements policy directly in shell;
- `classify_changes()` is domain-level and `discover_changed_files_from_git()`
  combines staged and unstaged paths;
- workflow state is rooted at `.ai/workflows/runs/` under a supplied root;
- `review_change_set_mismatch` currently belongs to review-agent behavior, not
  a standalone runtime comparator;
- terminal validation currently accepts successful finish-agent evidence
  without independently running derived sync check.

Do not design a new hook entrypoint until the existing one is located.

- [x] **Step 3: Identify authoritative workflow phase resolution**

Locate the existing runtime API or state reader that determines:

```text
active workflow exists
current phase
current run status
```

The implementation must reuse this source. It must not infer phase from agent name, branch, commit message, or changed paths.

Also record how `git worktree list --porcelain`, `context.control_root`, and
`context.worktree_path` can bind the current checkout to a unique active run.
An unrelated run in another worktree must not affect policy.

- [x] **Step 4: Identify canonical-to-derived classification logic**

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

Explicitly record the current mismatch between
`sync_templates.py:GOVERNED` and
`sync_derived_artifacts.py:GOVERNED_WORKFLOW_FILES`: all governed
`workflow_runtime/*.py` paths must become recognized without copying the list
into the hook policy module.

- [x] **Step 5: Identify review mismatch computation**

Trace where `review_change_set_mismatch` is produced and determine whether it compares:

- implementation evidence against actual Git changes;
- expected generated paths against Git changes;
- full live worktree scope including unstaged generated drift;
- committed `base_ref..<head_ref>` scope.

If no executable comparator exists, record review enforcement as agent-governed
and do not invent a runtime review subsystem.

- [x] **Step 6: Run current focused baseline tests**

Use existing test files discovered above. At minimum run the focused suites for:

- derived sync classification;
- hook/pre-commit behavior;
- review change-set validation;
- finish terminal validation.

Record exact commands and results before modifications.

### Task 2: Confirm the Remaining Reproduction

- [x] **Step 1: Create or reuse a temporary test fixture/repository state**

Model this scenario without modifying generated copies manually:

```text
active phase = apply_change
canonical agent or skill file changed/staged
derived provider copies remain stale
generated files are not staged
```

Create both main-checkout and linked-worktree variants. In the worktree
variant, keep workflow state under the control root and record the feature
checkout in `context.worktree_path`.

- [x] **Step 2: Verify current failure mode**

Demonstrate which current component blocks:

- Git hook;
- review mismatch validation;
- finish validation;
- or none of the above.

Also demonstrate that the current changed-file discovery cannot distinguish a
partially staged canonical file from additional unstaged edits, and that a
governed `workflow_runtime/*.py` change is skipped by the current incremental
classifier.

If the reported issue is already fully resolved, stop and return evidence instead of implementing speculative policy.

- [x] **Step 3: Capture the minimal failing contract**

The RED condition must assert executable behavior, for example:

```text
apply_change + attributable canonical drift + no generated edits -> hook allows commit
```

Do not add prompt string-presence tests.

---

## Slice 2: Reusable Phase and Drift Policy Model

### Task 3: Add Focused Failing Tests for Policy Decisions

**Files:**
- Create: `tests/test_derived_sync_hook_policy.py`
- Modify: `tests/test_sync_derived_artifacts.py`
- Modify: `tests/test_setup_agents.py`

- [x] **Step 1: Add RED cases for apply-phase allowance**

Cover:

1. canonical Agent change with attributable stale provider copies;
2. canonical Skill change with attributable stale provider copies;
3. recognized workflow/template canonical change when covered by existing mapping;
4. generated targets not staged and not manually modified.
5. main-checkout run bound to the current repository root;
6. worktree-mode run state stored under the control root and bound through
   normalized `context.worktree_path`;
7. governed `.ai/workflows/scripts/workflow_runtime/*.py` canonical changes.

Expected decision:

```text
allow
```

- [x] **Step 2: Add RED cases for apply-phase rejection**

Cover distinct reasons:

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

Add a same-domain unrelated-drift case: stage one canonical Skill or Agent
change while a different generated target in that same domain is dirty. The
policy must reject rather than allowing the entire domain.

Use parameterization only when setup, execution path, and assertion shape are equivalent.

- [x] **Step 3: Add compatibility cases**

Cover:

- no active workflow -> preserve existing hook behavior;
- active workflow in a non-apply phase -> do not apply the apply allowance;
- unresolved/corrupt active phase -> explicit context failure.
- active run in a different worktree -> preserve existing non-workflow behavior;
- two matching active runs -> explicit ambiguous-context failure;
- partial staged canonical edit plus additional unstaged canonical edit ->
  policy uses only the staged path/status as authored scope;
- generated file staged, unstaged, renamed, deleted, and untracked -> each
  remains visible through porcelain status parsing.

Add a failing `setup_agents.py --check --json` case proving the report names
the exact repository-relative stale Agent target rather than returning only a
non-zero status or human-readable message.

- [x] **Step 4: Run focused tests and confirm RED**

Run:

```bash
python3 -m pytest tests/test_derived_sync_hook_policy.py tests/test_sync_derived_artifacts.py tests/test_setup_agents.py -v
```

Expected: the new policy tests fail because
`scripts/derived_sync_hook_policy.py`, path-aware classification, and structured
Agent drift reporting do not yet exist; existing unaffected tests remain green.

### Task 4: Implement One Phase-Aware Policy Function

**Files:**
- Create: `scripts/derived_sync_hook_policy.py`
- Modify: `scripts/sync_derived_artifacts.py`
- Modify: `scripts/setup_agents.py`
- Read/import: `skills/sdlc-project-bootstrap/scripts/sync_templates.py`
- Reuse: `.ai/workflows/scripts/workflow_runtime/state.py`
- Test: `tests/test_derived_sync_hook_policy.py`
- Test: `tests/test_sync_derived_artifacts.py`
- Test: `tests/test_setup_agents.py`

- [x] **Step 1: Define a small policy result**

Use the repository's existing result conventions. Implement this result shape:

```python
HookPolicyResult(
    allowed: bool,
    reason: str | None,
    phase: str | None,
    run_id: str | None,
    staged_canonical_paths: list[str],
    actual_dirty_generated_paths: list[str],
    actual_staged_generated_paths: list[str],
    detected_stale_generated_paths: list[str],
    attributable_stale_generated_paths: list[str],
    unattributed_generated_paths: list[str],
    details: dict,
)
```

Do not introduce a persisted runtime state.

- [x] **Step 2: Resolve lifecycle phase from runtime state**

Rules:

- active run with phase `apply_change` -> apply policy;
- active finish/finalization context -> strict clean policy;
- no active run -> existing non-workflow behavior;
- active run but unreadable phase -> explicit failure.

Implement checkout-to-run binding before phase selection:

- resolve the current root with `git rev-parse --show-toplevel`;
- enumerate roots from `git worktree list --porcelain`;
- use the existing state reader to inspect active runs under candidate control
  roots;
- match worktree runs by normalized `context.worktree_path`;
- match main-checkout runs by normalized control/current root;
- return no active run for runs belonging only to other worktrees;
- reject multiple matching runs, corrupt matching state, and contradictory
  checkout context.

- [x] **Step 3: Reuse existing canonical attribution**

Feed changed/staged files into existing sync classification logic.

Replace `discover_changed_files_from_git()` as the hook input source with two
explicit collectors:

```text
discover_staged_entries(root)
  -> git diff --cached --name-status -z

discover_worktree_entries(root)
  -> git status --porcelain=v1 -z
```

Keep the existing combined discovery function for existing aggregate CLI
compatibility; do not silently change its public behavior in this task.

The hook policy may adapt the existing result, but must not duplicate mappings such as:

```text
agents/* -> provider agent copies
skills/* -> provider skill copies
workflow source -> template/distributed copies
```

Expose a shared path-aware classifier from `sync_derived_artifacts.py`. Obtain
the complete governed workflow source list from `sync_templates.py:GOVERNED`
so `workflow_runtime/*.py` changes are included. Add focused tests proving the
shared classifier, aggregate incremental selection, and hook policy all produce
the same workflow classification.

Extend read-only aggregate reporting so failed checks expose normalized stale
paths rather than only a suite return code. Run all governed read-only checks
for hook policy, then partition each stale path against targets attributable to
the staged canonical set. This must catch clean-relative-to-`HEAD` historical
drift in an unrelated Agent, Skill, or workflow target. Do not suppress an
entire suite merely because one staged canonical path belongs to that suite.

Invoke workflow and Skill checkers with their existing `--json` options. Add a
`--json` option to `setup_agents.py --check` whose report includes normalized
repository-relative stale paths for template and activation drift. Do not parse
plain-text `DRIFT` lines in the policy layer.

- [x] **Step 4: Distinguish stale from manually changed generated files**

The policy must differentiate:

- generated files merely stale because canonical changed;
- generated files modified in the worktree;
- generated files staged in the authored commit;
- unrelated generated drift.

Do not treat an unwritten expected target as a changed file.

Generated-path detection must operate on actual Git status entries. A clean
but stale provider copy is not a dirty path; a manually edited provider copy is.
Reject generated paths outside the targets attributable to the staged
canonical set, including unrelated drift within the same Agent or Skill
domain.

Combine Git status and sync-check evidence:

- Git status proves whether generated files were manually modified or staged;
- full read-only check output proves which clean or dirty generated files are
  stale relative to canonical sources;
- shared target attribution proves whether each stale path belongs to the
  staged canonical set.

- [x] **Step 5: Return stable diagnostic reasons**

Prefer the spec reasons when compatible with existing error conventions:

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

- [x] **Step 6: Run focused policy tests and confirm GREEN**

Run:

```bash
python3 -m pytest tests/test_derived_sync_hook_policy.py tests/test_sync_derived_artifacts.py -v
```

Also run:

```bash
python3 -m pytest tests/test_setup_agents.py -v
```

Expected: all tests pass, including structured Agent drift-path reporting.

---

## Slice 3: Integrate Phase-Aware Policy into the Git Hook

### Task 5: Update the Existing Hook Entry Point

**Files:**
- Modify: `.githooks/pre-commit`
- Use: `scripts/derived_sync_hook_policy.py`
- Modify: `tests/test_precommit_hook.py`

- [x] **Step 1: Preserve ordinary checks**

The new allowance must not skip unrelated repository checks, including any existing validation for:

- malformed files;
- invalid workflow templates;
- manually modified generated artifacts;
- unrelated dirty state;
- ordinary non-workflow commits.

Invoke the Python policy before the existing distribution checks. The Python
result decides whether expected apply-phase drift may bypass only the affected
distribution-drift check; it must not short-circuit unrelated hook rules.

- [x] **Step 2: Apply allowance only during `apply_change`**

Allow the commit only when:

- at least one recognized canonical source changed;
- expected stale targets are attributable through existing mapping;
- generated files are neither modified nor staged;
- no unrelated drift exists.

- [x] **Step 3: Reject mixed authored/generated commits**

A commit containing both canonical authored files and generated provider copies must fail during apply, even when generated content matches what sync would produce.

Generated cleanup remains finish-owned.

Base this decision on index status from `git diff --cached --name-status -z`.
Do not continue the current whitespace-splitting `for f in $STAGED_FILES`
pattern for the new policy path.

- [x] **Step 4: Produce actionable hook output**

Error output must state:

- the stable reason;
- offending paths when available;
- whether the user must remove generated changes, restore unrelated drift, or repair workflow context.

Expected canonical drift must not print a warning that looks like a failure.

- [x] **Step 5: Add subprocess-level hook tests where practical**

At least one representative integration test should execute the real hook/check entrypoint for:

- apply allowance;
- manual generated edit rejection;
- no-active-workflow compatibility.

Also execute the real hook for:

- worktree-mode phase binding through control-root state;
- active run belonging to another worktree;
- partial staging;
- same-domain unrelated generated drift;
- staged generated rename/delete;
- unsupported canonical Skill directory deletion.

Detailed permutations should remain in the lower-level policy tests.

- [x] **Step 6: Run hook-focused verification**

Run:

```bash
python3 -m pytest tests/test_precommit_hook.py tests/test_derived_sync_hook_policy.py -v
```

Expected: all tests pass.

---

## Slice 4: Correct Review Change-Set Validation

### Task 6: Reproduce and Fix Stale-Derived Review Mismatch

**Files:**
- Modify: an existing executable review change-set validation module only if Slice 1 discovers one and the reproduction proves a defect
- Modify: its existing review validation tests only under the same condition
- Clarify: `agents/review-agent.md` only if executable behavior alone cannot express the contract

- [x] **Step 1: Add a failing review case**

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

Use a temporary Git repository and assert that stale but unwritten target paths
do not appear in `git diff`, `git diff --cached`, or untracked-file output. This
is the executable proof when review scope remains agent-governed.

- [x] **Step 2: Retain rejection for actual generated modifications**

Add or preserve cases where generated files are:

- modified;
- staged;
- committed inside the reviewed range;
- listed inconsistently in implementation evidence.

These remain real change-set mismatches or generated-artifact violations.

- [x] **Step 3: Base comparison on actual Git changes**

Review validation must not synthesize expected generated targets into the change set.

For sliced review, preserve the existing authoritative commit-range behavior. For live-worktree review, compare against files actually modified/staged/untracked according to the existing contract.

- [x] **Step 4: Make the smallest code change**

If current code is already correct and only the prompt wording is ambiguous, do not modify runtime code or tests. Clarify the canonical review-agent instruction without adding prose-presence tests.

Do not add a new runtime review comparator solely to satisfy a testability
preference. Record the temporary-Git fixture result and manual canonical prompt
inspection as the verification mode for this branch.

- [x] **Step 5: Run focused review tests**

Confirm:

- stale but unwritten targets do not mismatch;
- actual generated edits still fail;
- unrelated changed files still fail;
- ordinary source/test scope behavior is unchanged.

If no executable comparator exists, replace this step with the temporary-Git
scope test plus manual inspection; do not claim an executable review-policy
suite exists.

---

## Slice 5: Enforce Strict Finish Closure

### Task 7: Verify and Harden Terminal Drift Enforcement

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/lifecycle.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py` only if the terminal blocker shape must be shared
- Sync later: `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/lifecycle.py`
- Modify: `tests/test_workflow.py`
- Clarify: `agents/finish-agent.md` only if necessary

- [x] **Step 1: Inspect current finish sequence**

Confirm that finish currently performs:

```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
```

or the appropriate full-mode equivalent when sync-rule files changed.

Verify the source of incremental changed paths. After the pre-cleanup commit,
`--changed-files-from-git` no longer contains the committed canonical authored
paths, so it must not be used as the only selector. Finish must either:

- pass the preserved reviewed authored paths through repeated
  `--changed-file` arguments; or
- use full mode when those paths are unavailable or sync-rule files changed.

Terminal enforcement always uses full read-only `--check`, because terminal
correctness must detect unrelated drift in every governed domain.

- [x] **Step 2: Add RED cases only for missing executable guarantees**

Required RED cases:

- finish completion attempted without required sync;
- sync check reports remaining drift;
- unrelated generated changes remain;
- manually changed generated file survives sync;
- terminal worktree policy remains dirty.
- finish-agent reports `derived_artifacts_synced: true` without a clean check;
- the read-only check command is missing or cannot execute;
- canonical changes were committed before cleanup and are absent from current
  worktree discovery.

Expected terminal reason:

```text
derived_artifact_drift_unresolved
```

Reuse existing terminal reason conventions if a canonical equivalent already exists.

- [x] **Step 3: Require clean terminal state**

Finish completion must fail until:

- write-producing sync completed where required;
- read-only check passes;
- generated cleanup is included in finish evidence;
- unrelated dirty files are absent.

Add a runtime helper that executes:

```bash
python3 scripts/sync_derived_artifacts.py --check --json
```

against the run's authoritative repository/worktree root. Consume the process
exit code and structured report. Call it immediately before `_finalize_run_to_history`
from both `cmd_done` and the terminal branch of `cmd_advance`. Return
`derived_artifact_drift_unresolved` for drift and an explicit execution error
when the command cannot run. Do not persist a new derived-sync state machine.

Resolve the check root from existing execution context and branch-finish
decision: use the surviving feature worktree for `keep_branch`/`create_pr`, and
the control/main checkout after `merge_local` or confirmed `discard`. Reject a
missing or contradictory target root instead of falling back to the shell
working directory. Add one focused test for each supported branch-finish root
selection.

- [x] **Step 4: Avoid changing implementation ownership**

Do not make implement-agent sync or test generated copies. The fix must remain entirely in finish/terminal enforcement.

- [x] **Step 5: Run focused terminal tests**

Use temporary executable fixtures or a fake sync script to prove the runtime
actually invokes the command. A test that only supplies
`derived_artifacts_synced: false` is insufficient.

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "terminal or derived_artifact" -v
```

Expected: all focused terminal and derived-artifact cases pass after the
implementation; before implementation, the new invocation cases fail because
terminal movement does not execute the check.

---

## Slice 6: Canonical Agent Clarifications and Distribution

### Task 8: Update Only Necessary Agent Contracts

**Files:**
- Modify if needed: `agents/review-agent.md`
- Modify if needed: `agents/finish-agent.md`
- Modify if needed: `agents/implement-agent.md`
- Derived copies: finish-owned synchronization

- [x] **Step 1: Keep existing phase-boundary wording authoritative**

Do not duplicate the full specification in each agent.

Only add role-specific clarifications:

- implement-agent: expected distributed-copy drift is not an apply blocker and generated copies remain untouched;
- review-agent: stale but unwritten derived targets are not authored scope;
- finish-agent: finalization requires sync and clean check.

For finish-agent, specify that incremental sync selection comes from preserved
reviewed/authored paths, not only post-commit worktree discovery, and that full
mode is required when those paths are unavailable.

- [x] **Step 2: Do not add prompt prose tests**

Agent Markdown changes are instructional prose unless frontmatter or machine-read structure changes.

Verification is inspection plus existing artifact syntax checks. Do not add `assertIn()` tests for the new wording.

- [x] **Step 3: Leave derived copies untouched during implementation and review**

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
- main-checkout and worktree-to-run binding;
- unrelated active run isolation and ambiguous-run rejection;
- staged-index versus unstaged-worktree separation;
- governed workflow runtime module attribution;
- same-domain unrelated generated drift;
- unsupported Skill deletion/rename rejection.

- [ ] **Step 2: Run review validation tests**

Include stale-unwritten and actual-generated-change scenarios.

- [ ] **Step 3: Run finish/terminal tests**

Require clean sync closure.

- [ ] **Step 4: Run apply-phase broad regression and record exact phase-deferred tests**

Run the broad suite before finish sync. Any failure may be marked
`phase_deferred` only when all of the following hold:

- the exact pytest node id is recorded;
- the failure is solely a canonical/distributed equality assertion;
- no executable source behavior failed;
- the test is scheduled for rerun immediately after finish sync.

All other failures block implementation.

- [ ] **Step 5: Run existing derived sync suites**

At minimum include the existing suites for:

- `sync_derived_artifacts.py`;
- workflow/template synchronization;
- skill installation/no-op behavior when touched indirectly;
- wrapper/runtime validation affected by code changes.

- [ ] **Step 6: Defer final full regression until finish synchronization**

Do not claim the repository-wide suite is green while expected derived copies
are intentionally stale. Record the apply-phase result and exact deferred node
ids for finish handoff.

After Task 10 performs finish-owned synchronization, run:

```bash
python3 -m pytest tests/ -v
```

Do not return implementation success without a passing full regression or individually documented accepted pre-existing/environment failures under the repository's current verification contract.

Phase-deferred drift tests are not accepted pre-existing failures. They must
pass after synchronization before completion.

### Task 10: Review Scope and Finish Sync

- [ ] **Step 1: Confirm implementation change set contains authored files only**

Before review, provider copies must remain unchanged.

- [ ] **Step 2: Review commit range or live authored scope**

Confirm expected stale targets do not appear as synthesized changes.

- [ ] **Step 3: Run finish-owned derived synchronization**

Use repeated `--changed-file` arguments from the preserved reviewed authored
change set for ordinary incremental synchronization. Do not rely solely on
`--changed-files-from-git` after the pre-cleanup commit. Use full mode when the
authored path set is unavailable, a sync-rule file changed, or classification
requests full fallback.

- [ ] **Step 4: Run final sync check**

Run full read-only `python3 scripts/sync_derived_artifacts.py --check --json`
and require zero drift across every governed domain.

- [ ] **Step 5: Rerun phase-deferred tests and full regression**

Rerun every exact node id recorded as `phase_deferred`, then run:

```bash
python3 -m pytest tests/ -v
```

All phase-deferred tests and the full regression must pass before terminal
completion, apart from separately documented accepted pre-existing/environment
failures under the repository's existing contract.

- [ ] **Step 6: Verify terminal repository state**

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
| Governed workflow runtime module changed | Allow when staged and attributable | Review authored runtime change | Sync templates/distributions and require clean |
| Generated provider file manually modified | Reject | Reject if reached | Reject |
| Generated file staged with canonical change | Reject | Reject if reached | N/A |
| Unrelated generated drift exists | Reject | Report unrelated scope where applicable | Reject |
| Drift cannot be attributed to canonical source | Reject | Do not synthesize ownership | Reject |
| No active workflow | Preserve existing behavior | Preserve existing behavior | Preserve existing behavior |
| Active run belongs to another worktree | Preserve existing behavior | Use explicit review worktree | Do not borrow the other run's phase |
| Multiple active runs match current checkout | Explicit ambiguous-context failure | Block on invalid runtime context | Block |
| Canonical path partially staged with additional unstaged edits | Evaluate staged index scope only | Review actual Git scopes separately | Sync accepted authored paths or use full mode |
| Canonical Skill directory deleted or renamed | Reject as unsupported | N/A | N/A |
| Active workflow phase unreadable | Explicit context failure | Explicit context failure if needed | Explicit context failure |
| Finish sync check still dirty | N/A | N/A | Block with terminal drift reason |
| Finish-agent claims clean without executable check | N/A | N/A | Runtime executes check and blocks on failure |
| Distribution consistency test fails only from expected apply drift | Record exact phase-deferred node id | Do not treat as general pass | Rerun after sync and require pass |

---

## Completion Criteria

- [ ] Existing derived-sync phase-boundary ownership remains unchanged.
- [ ] Apply-phase authored commits allow attributable stale derived targets.
- [ ] Apply hook rejects manual, mixed, unrelated, and unattributed generated changes.
- [ ] Phase is resolved from existing workflow runtime state.
- [ ] Current checkout is bound to exactly one matching active run; unrelated worktree runs are ignored and ambiguous matches fail closed.
- [ ] Existing sync mapping logic is reused.
- [ ] Staged index scope is separate from unstaged/untracked worktree scope.
- [ ] Attribution is path-aware and detects unrelated drift within the same sync domain.
- [ ] Governed `workflow_runtime/*.py` sources are classified consistently.
- [ ] Canonical Skill directory deletion/rename is rejected as unsupported.
- [ ] Review does not mismatch solely because unwritten generated targets are stale.
- [ ] Review still rejects generated files actually changed during implementation.
- [ ] Finish requires successful sync, clean check, and clean terminal state.
- [ ] Terminal runtime executes the full read-only sync check and consumes its exit status.
- [ ] Finish incremental selection uses preserved authored paths or safely falls back to full mode after the pre-cleanup commit.
- [ ] Non-workflow hook behavior remains compatible.
- [ ] No new derived-sync state machine or manifest exists.
- [ ] No prompt prose-presence tests were added.
- [ ] Exact phase-deferred distribution tests pass after finish sync.
- [ ] Focused tests and full regression pass.
