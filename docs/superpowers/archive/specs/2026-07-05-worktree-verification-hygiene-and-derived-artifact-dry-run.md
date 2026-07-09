# Worktree Verification Hygiene and Derived Artifact Dry-Run

## Context

The `2026-07-05-incremental-derived-artifact-sync-filtering` run exposed two high-frequency review noise sources:

1. Worktree full regression can fail because generated runtime fixture directories under `.ai/evals/targets/...` are not present in the feature worktree.
2. Smoke-testing `scripts/sync_derived_artifacts.py --fix --changed-file ...` against real skills can refresh real `.skill-install.json` files with worktree-local absolute paths and timestamps.

These failures are not necessarily product regressions, but they cause `review-agent` to block or bounce work back to `implement-agent`. Because this is a repeated iteration tax, this spec moves verification hygiene earlier in the repair sequence.

A governing principle for this spec is: **the component that creates transient verification garbage must prevent it, isolate it, or clean it up before handing work to the next lifecycle agent.** Unit tests and smoke tests must not leave cleanup debt for review-agent, finish-agent, or a later manual recovery step.

## Goals / Non-Goals

**Goals:**

- Add `--dry-run` for derived artifact sync so smoke tests do not mutate real distributed artifacts.
- Add worktree hydration for minimal non-Git runtime fixture directories required by tests.
- Standardize verification reporting for accepted pre-existing/environment failures.
- Reduce false review blockers caused by worktree fixture gaps or smoke-test churn.
- Preserve existing full `--check` and `--fix` behavior unless `--dry-run` is explicitly used.
- Enforce producer-owned cleanup: tests or commands that create transient files must isolate or remove them before returning success.

**Non-Goals:**

- Do not redesign workflow runtime context; that belongs to the runtime context spec.
- Do not implement branch finish decision gates.
- Do not move workflow run state into worktrees.
- Do not make review-agent a broad regression runner.
- Do not silently accept real product failures as pre-existing failures.
- Do not add a separate `--plan` mode in this spec; `--dry-run` is the single non-mutating smoke mode.

## Covered Optimization Points

This spec covers or partially covers these optimization points from the run analysis:

- **9. Worktree baseline environment incomplete** — add hydration and validation for required worktree runtime fixtures.
- **10. Smoke test pollutes real derived artifacts** — add `--dry-run` for `sync_derived_artifacts.py`.
- **11. Agent permission lacks safe recovery mechanism** — reserve a constrained `git restore -- <known-safe-derived-path>` recovery path for accidental derived-artifact churn.
- **12. Full regression result wording inconsistent** — standardize `verification_summary` and accepted pre-existing failure evidence.
- **21. Full regression pre-existing failure should be structured** — add explicit evidence object for accepted failures.
- **22. Workspace hydration should be a standard worktree hook** — define minimal hydration contract.
- **23. Derived artifact dry-run should be default for smoke checks** — require safe dry-run smoke behavior.

## Decisions

### Decision 1: Hydration Means Minimal Runtime Fixture Creation, Not `.ai` Sync

Workspace hydration must not copy the whole `.ai/` directory into the implementation worktree. The workflow run state remains in the main/control checkout.

Hydration only creates or validates minimal non-Git runtime fixtures that tests require. Initial target:

```text
.ai/evals/targets/*/cases/inbox
.ai/evals/targets/*/cases/accepted
.ai/evals/targets/*/cases/rejected
```

The implementation may discover required targets from existing evalops metadata or use a deterministic configured list.

Do not hydrate:

```text
.ai/workflows/runs/active
.ai/workflows/runs/current.json
.ai/workflows/runs/history
```

### Decision 2: Add a Worktree Hydration Script

Add a controlled script, for example:

```bash
python3 .ai/workflows/scripts/hydrate_workspace.py --root <worktree_path>
python3 .ai/workflows/scripts/validate_workspace.py --root <worktree_path>
```

The script must be idempotent. It should create missing required directories, report what it created, and return non-zero only when required runtime fixtures cannot be created or validated.

### Decision 3: Derived Artifact Sync Uses `--dry-run` as the Single Non-Mutating Smoke Mode

`sync_derived_artifacts.py` must support `--dry-run` as the single non-mutating smoke mode. Do not add a separate `--plan` mode in this spec.

`--dry-run` must exercise classification, suite construction, report generation, and command planning without mutating real distributed artifacts.

Required behavior:

- No writes to `.opencode/`, `.claude/`, `.cursor/`, or `.skill-install.json`.
- No invocation of mutating install/distribution subprocesses unless they are replaced by dry-run stubs or command-plan records.
- JSON output must report what would have happened, including scope, affected domains, selected suites, skipped writes, and dry-run status.
- Return codes should reflect whether the planned operation would succeed, while clearly marking that no writes were performed.

Example:

```bash
python3 scripts/sync_derived_artifacts.py --dry-run --changed-file <path> --json
```

### Decision 4: Smoke Tests Must Prefer `--dry-run`

Agent and handoff guidance should prefer:

```bash
python3 scripts/sync_derived_artifacts.py --dry-run --changed-file <path> --json
```

Use real `--fix` only when the task explicitly requires repairing drift or when the work package intends to update distributed artifacts.

Unit tests for changed-file classification, incremental suite selection, and smoke behavior should use temporary fixture directories whenever possible. When tests must touch real derived artifact paths, they must restore the pre-test state before returning success.

### Decision 5: Producer-Owned Cleanup Is Mandatory

Any test, script, or smoke command that creates transient files is responsible for cleanup before handing work to the next lifecycle stage.

This principle applies at three levels:

1. **Unit tests:** must use temporary directories, monkeypatch/subprocess stubs, or cleanup fixtures so repository state is identical before and after the test.
2. **Smoke tests:** must use `--dry-run` unless the intent is to actually repair drift.
3. **Agents:** if an agent intentionally runs a mutating command as part of a work package, that agent must either include the resulting artifacts as intentional changes or restore accidental churn before returning success.

A test suite that leaves `.skill-install.json` churn behind is failing its own cleanup contract, even if assertions pass.

### Decision 6: Standardize Verification Summary Status

Agent handoffs and JSON results should use a structured verification status enum:

```text
pass
fail
pass_with_accepted_preexisting_failures
```

When `pass_with_accepted_preexisting_failures` is used, the evidence must include:

```json
{
  "verification_summary": {
    "status": "pass_with_accepted_preexisting_failures",
    "full_regression": {
      "command": "python3 -m pytest tests/ -v",
      "passed": 1038,
      "failed": 1,
      "accepted_preexisting_failures": [
        {
          "test": "tests/test_evalops_root.py::TestTargetWorkspace::test_workspace_has_required_directories",
          "reason": "worktree lacks generated evalops fixture dirs",
          "confirmation": "passes on main checkout or passes after hydration",
          "owner": "environment_fixture"
        }
      ]
    }
  }
}
```

Review-agent may accept such evidence only when the failure is clearly scoped, named, and confirmed not to be caused by the implementation.

### Decision 7: Use Constrained `git restore` as the Safe Restore Path

If real derived-artifact churn still appears during development, agents should not hand-edit `.skill-install.json` field-by-field.

Use Option B: allow a constrained restore path for known safe derived artifacts:

```yaml
"git restore -- <known-safe-derived-path>": allow
```

The allowlist should be as narrow as practical. It should cover known generated/distributed artifact paths that are safe to restore when churn is accidental, for example specific `.skill-install.json` files under known distribution targets.

Do not add a new `safe_restore.py` script in this spec.

### Decision 8: Review-Agent Should Not Block on Accepted Hygiene Evidence

If implement-agent provides structured evidence that:

- hydration was run or not required;
- `--dry-run` was used for derived sync smoke checks; and
- any remaining failure is listed in `accepted_preexisting_failures` with a concrete test id and reason;

then review-agent should not bounce the task back solely for that known hygiene issue.

### Decision 9: Tests Must Prove Repository Cleanliness

Tests added for this spec must include repository-cleanliness assertions around previously polluting paths.

At minimum, tests should prove:

- `sync_derived_artifacts.py --dry-run --changed-file skills/<name>/SKILL.md --json` does not modify `.skill-install.json` in real or fixture distribution targets.
- Incremental classification tests use temporary fixtures or stubs and leave no working tree changes.
- Hydration tests create only expected fixture directories and do not create workflow run state under the worktree.

## Flow

```text
worktree created or selected
  |
  v
hydrate_workspace.py --root <worktree_path>
  |
  v
validate_workspace.py --root <worktree_path>
  |
  v
implement-agent runs focused tests and relevant regression
  |
  |- derived sync smoke -> --dry-run
  |- unit tests isolate or clean their own transient files
  |- full regression -> structured verification_summary
  v
review-agent accepts or blocks based on structured evidence
```

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/scripts/hydrate_workspace.py` | New idempotent hydration script for required runtime fixtures. |
| `.ai/workflows/scripts/validate_workspace.py` | Optional validation script for hydration state. |
| `scripts/sync_derived_artifacts.py` | Add `--dry-run` non-mutating mode. |
| `tests/test_sync_derived_artifacts.py` | Add tests proving `--dry-run` and unit tests do not rewrite `.skill-install.json` or leave repository churn. |
| `tests/test_evalops_root.py` or fixture setup tests | Add worktree hydration coverage or reduce dependence on missing empty dirs. |
| `agents/implement-agent.md` | Prefer `--dry-run` derived sync smoke checks; record `verification_summary`; require producer-owned cleanup. |
| `agents/review-agent.md` | Accept structured pre-existing/environment failure evidence; do not block on known hygiene issues when cleanup contract is satisfied. |
| `.opencode/agents/*`, `.claude/agents/*`, `.cursor/agents/*` | Distributed copies generated from canonical agents. |
| `tests/test_wrapper_contracts.py` or related tests | Prompt contract tests for `--dry-run`, cleanup ownership, and structured verification evidence. |

## Acceptance Criteria

- Worktree hydration creates required evalops fixture directories without copying workflow run state.
- Hydration is idempotent and safe to run repeatedly.
- `sync_derived_artifacts.py --dry-run` does not modify `.opencode/`, `.claude/`, `.cursor/`, or `.skill-install.json`.
- Existing `--check` and `--fix` behavior remains backward compatible.
- No separate `--plan` mode is required or introduced by this spec.
- Implement-agent and review-agent prompt contracts prefer `--dry-run` for derived sync smoke checks.
- Tests that create transient files must isolate or clean them before success; repository churn after a passing test is a test failure.
- Verification evidence supports `pass`, `fail`, and `pass_with_accepted_preexisting_failures`.
- Accepted pre-existing failures must include exact test id, reason, and confirmation method.
- Review-agent does not return work to implement-agent solely because of known hydration/dry-run hygiene noise when structured evidence is present.
- Constrained `git restore -- <known-safe-derived-path>` recovery is documented or allowlisted where needed for accidental derived churn.

## Risks / Trade-offs

**Hydration can hide real fixture setup defects:** Mitigate by keeping hydration explicit, idempotent, and logged. If a test requires a fixture, the fixture contract should be documented.

**Dry-run semantics can diverge from real fix behavior:** Tests must cover classification, command planning, report output, and non-mutation. Real `--fix` remains the source of truth for actual repair.

**Accepted pre-existing failure can become a dumping ground:** Require exact test ids and confirmation. Broad statements such as "all tests passed except environment" are not acceptable.

**Constrained git restore can be too broad if poorly written:** Keep allowlist patterns narrow and limited to known derived artifact paths. The default expectation is still prevention or test-owned cleanup, not after-the-fact restore.

**Producer-owned cleanup can require more test fixture work:** This is intentional. A passing test suite must not leave garbage for later lifecycle agents to discover.
