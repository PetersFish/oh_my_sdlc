# Worktree Verification Hygiene and Derived Artifact Dry-Run

## Context

The `2026-07-05-incremental-derived-artifact-sync-filtering` run exposed two high-frequency review noise sources:

1. Worktree full regression can fail because generated runtime fixture directories under `.ai/evals/targets/...` are not present in the feature worktree.
2. Smoke-testing `scripts/sync_derived_artifacts.py --fix --changed-file ...` against real skills can refresh real `.skill-install.json` files with worktree-local absolute paths and timestamps.

These failures are not necessarily product regressions, but they cause `review-agent` to block or bounce work back to `implement-agent`. Because this is a repeated iteration tax, this spec moves verification hygiene earlier in the repair sequence.

## Goals / Non-Goals

**Goals:**

- Add a dry-run or plan mode for derived artifact sync so smoke tests do not mutate real distributed artifacts.
- Add worktree hydration for minimal non-Git runtime fixture directories required by tests.
- Standardize verification reporting for accepted pre-existing/environment failures.
- Reduce false review blockers caused by worktree fixture gaps or smoke-test churn.
- Preserve existing full `--check` and `--fix` behavior unless a dry-run/plan flag is explicitly used.

**Non-Goals:**

- Do not redesign workflow runtime context; that belongs to the runtime context spec.
- Do not implement branch finish decision gates.
- Do not move workflow run state into worktrees.
- Do not make review-agent a broad regression runner.
- Do not silently accept real product failures as pre-existing failures.

## Covered Optimization Points

This spec covers or partially covers these optimization points from the run analysis:

- **9. Worktree baseline environment incomplete** — add hydration and validation for required worktree runtime fixtures.
- **10. Smoke test pollutes real derived artifacts** — add `--dry-run` or `--plan` for `sync_derived_artifacts.py`.
- **11. Agent permission lacks safe recovery mechanism** — introduce or reserve a controlled restore path for accidental derived-artifact churn.
- **12. Full regression result wording inconsistent** — standardize `verification_summary` and accepted pre-existing failure evidence.
- **21. Full regression pre-existing failure should be structured** — add explicit evidence object for accepted failures.
- **22. Workspace hydration should be a standard worktree hook** — define minimal hydration contract.
- **23. Derived artifact dry-run should be default for smoke checks** — require safe check-first/smoke behavior.

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

### Decision 3: Derived Artifact Sync Needs Non-Mutating Smoke Modes

`sync_derived_artifacts.py` must support a mode that exercises classification and suite construction without mutating real distributed artifacts.

Accepted designs:

- `--plan`: report what suites/commands would run, without executing mutating commands.
- `--dry-run`: execute safe checks and command planning, but skip writes to `.opencode/`, `.claude/`, `.cursor/`, and `.skill-install.json`.

At least one of these modes must be implemented. If both are implemented, their semantics must be documented and tested.

### Decision 4: Smoke Tests Should Prefer Non-Mutating Modes

Agent and handoff guidance should prefer:

```bash
python3 scripts/sync_derived_artifacts.py --plan --changed-file <path> --json
```

or:

```bash
python3 scripts/sync_derived_artifacts.py --dry-run --changed-file <path> --json
```

Use real `--fix` only when the task explicitly requires repairing drift or when the work package intends to update distributed artifacts.

### Decision 5: Standardize Verification Summary Status

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

### Decision 6: Add a Safe Restore Path for Derived Churn

If real derived-artifact churn still appears during development, agents should not hand-edit `.skill-install.json` field-by-field. Add one controlled mechanism:

Option A:

```bash
python3 scripts/safe_restore.py <path>
```

Option B:

```yaml
"git restore -- <known-safe-derived-path>": allow
```

Prefer Option A if the project wants stricter validation. The script must refuse paths outside known derived artifact directories unless explicitly configured.

### Decision 7: Review-Agent Should Not Block on Accepted Hygiene Evidence

If implement-agent provides structured evidence that:

- hydration was run or not required;
- non-mutating derived sync smoke mode was used; and
- any remaining failure is listed in `accepted_preexisting_failures` with a concrete test id and reason;

then review-agent should not bounce the task back solely for that known hygiene issue.

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
  |- derived sync smoke -> --plan or --dry-run
  |- full regression -> structured verification_summary
  v
review-agent accepts or blocks based on structured evidence
```

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/scripts/hydrate_workspace.py` | New idempotent hydration script for required runtime fixtures. |
| `.ai/workflows/scripts/validate_workspace.py` | Optional validation script for hydration state. |
| `scripts/sync_derived_artifacts.py` | Add `--plan` and/or `--dry-run` non-mutating mode. |
| `tests/test_sync_derived_artifacts.py` | Add tests proving non-mutating modes do not rewrite `.skill-install.json`. |
| `tests/test_evalops_root.py` or fixture setup tests | Add worktree hydration coverage or reduce dependence on missing empty dirs. |
| `agents/implement-agent.md` | Prefer non-mutating derived sync smoke checks; record `verification_summary`. |
| `agents/review-agent.md` | Accept structured pre-existing/environment failure evidence; do not block on known hygiene issues. |
| `.opencode/agents/*`, `.claude/agents/*`, `.cursor/agents/*` | Distributed copies generated from canonical agents. |
| `tests/test_wrapper_contracts.py` or related tests | Prompt contract tests for non-mutating smoke mode and structured verification evidence. |

## Acceptance Criteria

- Worktree hydration creates required evalops fixture directories without copying workflow run state.
- Hydration is idempotent and safe to run repeatedly.
- `sync_derived_artifacts.py --plan` or `--dry-run` does not modify `.opencode/`, `.claude/`, `.cursor/`, or `.skill-install.json`.
- Existing `--check` and `--fix` behavior remains backward compatible.
- Implement-agent and review-agent prompt contracts prefer non-mutating derived sync smoke checks.
- Verification evidence supports `pass`, `fail`, and `pass_with_accepted_preexisting_failures`.
- Accepted pre-existing failures must include exact test id, reason, and confirmation method.
- Review-agent does not return work to implement-agent solely because of known hydration/dry-run hygiene noise when structured evidence is present.

## Risks / Trade-offs

**Hydration can hide real fixture setup defects:** Mitigate by keeping hydration explicit, idempotent, and logged. If a test requires a fixture, the fixture contract should be documented.

**Dry-run semantics can diverge from real fix behavior:** Tests must cover command planning and report output. Real `--fix` remains the source of truth for actual repair.

**Accepted pre-existing failure can become a dumping ground:** Require exact test ids and confirmation. Broad statements such as "all tests passed except environment" are not acceptable.

**Safe restore permissions can be too broad:** Prefer a script that validates allowed paths before restoring.
