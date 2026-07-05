# Finish-Agent Branch Decision and Terminal Ownership

## Context

The `2026-07-05-incremental-derived-artifact-sync-filtering` run exposed a finish-phase lifecycle ownership problem. After review accepted the implementation, `finish-agent` proceeded through branch finish, memory sync, workflow advancement, and final history movement without an explicit user branch-finish decision and without preserving final `finish-agent` evidence in `run.json`.

The result was a completed history run whose latest recorded `agent_result` was not `finish-agent`, while the finish handoff claimed that branch finish, hooks, and finalization had completed. This indicates that branch outcome, implementation commit ownership, workflow artifact commits, memory sync target, and terminal finalization need explicit governance.

This spec defines the finish-stage contract. It depends on the runtime context and evidence integrity spec for robust context persistence, but can be designed independently for user confirmation.

## Goals / Non-Goals

**Goals:**

- Add an explicit branch finish decision gate before branch-affecting finish actions.
- Prevent `finish-agent` from silently choosing merge, PR, keep, or discard.
- Separate implementation commits from workflow/control commits.
- Define memory sync target ref rules for each branch finish outcome.
- Ensure final agent evidence is recorded before active run is moved to history.
- Make lightweight-flow archive evidence semantically accurate.
- For completed lightweight-flow runs, archive the corresponding Superpowers spec and plan files into `docs/superpowers/archive/`.
- Preserve main-checkout/non-worktree compatibility.

**Non-Goals:**

- Do not require every run to use a worktree.
- Do not implement dry-run/hydration behavior; that belongs to the verification hygiene spec.
- Do not redesign the whole workflow phase graph unless needed for finish gating.
- Do not automate remote PR creation unless the user explicitly selects `create_pr` and required credentials/tooling exist.
- Do not silently merge implementation commits into main.
- Do not define the final workflow artifact Git commit; `workflow-final-tail-commit` owns the final commit boundary after the run reaches done.

## Covered Optimization Points

This spec covers or partially covers these optimization points from the run analysis:

- **1. Finish-agent lacks branch finish decision gate** — direct fix.
- **4. Finish-agent archives/finalizes before orchestrator after-dispatch** — enforce terminal ownership boundaries.
- **6. Finish-agent final evidence missing from run.json** — require evidence-before-finalize invariant with runtime support.
- **7. Main and worktree commit responsibilities are confused** — define implementation vs workflow commit ownership.
- **8. Memory sync commit target unclear** — define memory sync target by branch finish action.
- **13. Lightweight-flow archive evidence naming misleading** — replace `archive_path_exists: true` with semantic archive evidence and archive Superpowers artifacts.
- **14. Finish-agent prompt and skill inconsistent** — prompt must require blocker when branch decision is missing.
- **17. Finish-agent should split branch decision and archive execution** — direct design.
- **18. Runtime should prevent finish-agent from terminal finalize** — direct design.
- **19. Runtime should support final evidence before terminal move** — consume or depend on runtime invariant.

## Decisions

### Decision 1: Add `branch_finish_decision` Gate

When a run has implementation changes on a feature branch or worktree, finish must require an explicit branch finish decision before branch-affecting actions.

Allowed values:

```text
merge_local
create_pr
keep_branch
discard
```

The decision must be stored in workflow state, for example:

```json
{
  "gates": {
    "branch_finish_decision": {
      "status": "required",
      "allowed_values": ["merge_local", "create_pr", "keep_branch", "discard"],
      "selected": null,
      "reason": "implementation branch requires explicit finish decision"
    }
  }
}
```

After user selection:

```json
{
  "context": {
    "branch_finish_decision": "keep_branch"
  },
  "gates": {
    "branch_finish_decision": {
      "status": "passed",
      "selected": "keep_branch"
    }
  }
}
```

### Decision 2: No Silent Default Branch Outcome

There is no default branch finish decision. `finish-agent`, `dev-orchestrator`, and runtime must not silently choose `keep_branch`, `create_pr`, `merge_local`, or `discard`.

If the decision is missing, `finish-agent` must return:

```json
{
  "status": "blocked",
  "blockers": [
    {
      "reason": "missing_branch_finish_decision",
      "message": "finish requires explicit branch_finish_decision before branch-affecting actions",
      "recommended_action": "ask_user_branch_finish_decision"
    }
  ],
  "recommended_next_action": "ask_user_branch_finish_decision"
}
```

### Decision 3: Main-Checkout Mode May Not Require Branch Gate

For `execution_mode=main_checkout`, if there is no feature branch/worktree and implementation changes were made directly in the control checkout, `branch_finish_decision` is not required by default.

However, if a feature branch exists or `context.feature_branch` is recorded, the gate is required even if the current checkout is main-like.

### Decision 4: Split Finish Into Decision and Execution

Finish should conceptually split into:

```text
1. require_branch_finish_decision
2. execute_branch_finish_action
3. archive_or_lightweight_finish
4. post_archive_hooks
5. terminal finalize by orchestrator/runtime
```

`finish-agent` may execute the branch action only after the decision gate is passed.

### Decision 5: Define Branch Finish Actions

#### `merge_local`

- Merge feature branch into base branch locally.
- Implementation commits become part of base/main.
- Memory sync target should be the merged base/main commit.
- Requires clean worktree and explicit merge evidence.

#### `create_pr`

- Push feature branch and prepare or create a PR if tooling is available.
- Implementation commits remain on feature branch.
- Memory sync target should be the feature branch commit unless PR merge is completed in the same governed flow.
- If PR creation cannot be performed by available tools, return PR-ready evidence and block/ask for manual PR confirmation as appropriate.

#### `keep_branch`

- Push or preserve feature branch.
- Do not merge implementation commits into main.
- Memory sync target should be the feature branch commit.
- Workflow/control artifacts may still be committed on main/control checkout.

#### `discard`

- Discard/remove the feature branch/worktree only after explicit user confirmation.
- Do not merge implementation commits.
- Memory sync should be `not_needed` or should target the control ref with explicit reason.
- Must record discard evidence and residual risk.

### Decision 6: Separate Implementation Commits From Workflow Commits

Define two commit classes:

```text
implementation commits
  - source code
  - tests
  - docs tied to implementation
  - plan checkbox updates inside implementation worktree when part of the work package
  - live on feature branch/worktree until merge/PR/discard decision

workflow commits
  - workflow run state
  - run history
  - memory sync artifacts
  - roadmap lifecycle artifacts
  - Superpowers spec/plan archive moves
  - control-plane archive/finalization records
  - live on main/control checkout
```

Finish must not imply that implementation commits are in main unless `branch_finish_decision=merge_local` has completed or a PR has been merged outside the flow and confirmed.

### Decision 7: Memory Sync Target Depends on Branch Decision

Memory sync must record target ref explicitly:

```json
{
  "memory_sync": {
    "target_ref_type": "feature_branch",
    "target_ref": "feature/incremental-derived-artifact-sync-filtering",
    "target_commit": "a14deec",
    "resolution": "synced"
  }
}
```

Rules:

| Branch finish decision | Memory sync target |
|---|---|
| `merge_local` | merged base/main commit |
| `create_pr` | feature branch commit unless PR merged in-flow |
| `keep_branch` | feature branch commit |
| `discard` | `not_needed` or control ref with explicit reason |

Do not implicitly sync both feature branch and main. If both must be touched, the contract must state why and record both refs separately.

### Decision 8: Finish-Agent Must Not Own Terminal Finalization

`finish-agent` must not directly execute final workflow terminal movement:

Forbidden for finish-agent:

```text
workflow.py done
workflow.py advance to done when that moves active run to history
manual move active run -> history
manual clear current.json
manual finalize/move run directory
```

Allowed for finish-agent:

```text
produce final evidence
execute provider archive wrapper when delegated
execute branch finish action after explicit decision
run safe finish checks
return recommended_next_action for dev-orchestrator/runtime
```

`dev-orchestrator` and `workflow.py` own terminal phase completion and final history movement.

### Decision 9: Final Evidence Before History Movement

A run must not be finalized to history unless the final `finish-agent` result has been recorded through `after-dispatch` or an atomic `finalize-after-dispatch` command.

The history `run.json` for a completed finish phase must include:

```json
{
  "evidence": {
    "agent_result": {
      "agent": "finish-agent",
      "status": "success"
    },
    "agent_results": {
      "<slice_id>": {
        "finish-agent": {
          "status": "success",
          "artifacts": {}
        }
      }
    }
  }
}
```

If roadmap-agent is the last hook worker, runtime must still preserve finish-agent evidence in `agent_results` and should not overwrite final lifecycle evidence in a way that hides finish completion.

### Decision 10: Lightweight-Flow Archive Evidence Must Be Semantic

Replace misleading lightweight-flow archive evidence:

```json
{
  "archive_path_exists": true
}
```

with semantic fields:

```json
{
  "archive_action_completed": true,
  "archive_artifact_path": null,
  "archive_not_required_reason": "lightweight-flow"
}
```

For spec-flow, `archive_artifact_path` should point to the OpenSpec archive path when applicable.

For lightweight-flow, `archive_artifact_path` should be `null` when there is no single archive artifact, and `archived_design_artifact_paths` must list the Superpowers spec/plan files moved into `docs/superpowers/archive/`.

Workflow phase criteria may need to support either legacy `archive_path_exists` or new semantic archive criteria during migration.

### Decision 11: Lightweight-Flow Archives Superpowers Spec and Plan Files

When a lightweight-flow run is completed, finish must archive the corresponding Superpowers design artifacts by moving them from active design directories into `docs/superpowers/archive/`.

Source directories:

```text
docs/superpowers/specs/
docs/superpowers/plans/
```

Destination directory:

```text
docs/superpowers/archive/
```

The archive operation must include the matching spec file and the matching plan file when both exist. Matching should use the runtime design artifact contract first:

1. `primary_design_path`.
2. `design_artifact_paths[]` with `kind=spec` or `kind=plan`.
3. deterministic slug/date matching only as a fallback.

The operation must preserve filenames unless a collision exists. If a destination filename already exists, finish must avoid overwriting by using a deterministic suffix or by returning a blocker that asks for manual resolution.

The finish result must record:

```json
{
  "archive_action_completed": true,
  "archive_not_required_reason": "lightweight-flow",
  "archived_design_artifact_paths": [
    "docs/superpowers/archive/2026-07-05-example-design.md",
    "docs/superpowers/archive/2026-07-05-example.md"
  ],
  "source_design_artifact_paths": [
    "docs/superpowers/specs/2026-07-05-example-design.md",
    "docs/superpowers/plans/2026-07-05-example.md"
  ]
}
```

If no matching Superpowers artifacts are found, finish must not silently claim archive success. It must either:

- record `archive_action_completed: false` with a concrete `archive_not_required_reason` when the flow truly has no Superpowers artifacts; or
- return a blocker such as `missing_lightweight_archive_artifacts` when artifacts were expected but unavailable.

### Decision 12: Finish-Agent Prompt Must Match Skill Behavior

The finish-agent prompt must hard-require:

- If branch decision is required and missing, return blocker `missing_branch_finish_decision`.
- Do not choose branch outcome silently.
- Do not finalize workflow run state.
- For lightweight-flow completion, archive matching Superpowers spec/plan files into `docs/superpowers/archive/` and record source/destination paths.
- Return final JSON evidence and handoff artifact path.
- Record which checkout/ref was used for each operation.

### Decision 13: Dev-Orchestrator Owns User Branch Decision Collection

When finish blocks with `missing_branch_finish_decision`, `dev-orchestrator` must ask the user to choose one of:

```text
merge_local
create_pr
keep_branch
discard
```

It must present a concise explanation of consequences and then record the selected decision in workflow state before redispatching finish-agent.

## Flow

```text
review-agent accepted apply_change
  |
  v
dev-orchestrator complete-phase + advance to archive_change
  |
  v
before-dispatch finish-agent
  |
  v
finish-agent checks branch_finish_decision
  |
  |- missing -> blocker missing_branch_finish_decision
  |
  |- present -> execute selected branch finish action
                 archive/lightweight finish
                 for lightweight-flow: move matching spec/plan files to docs/superpowers/archive/
                 return final evidence
  v
after-dispatch records finish-agent evidence
  |
  v
dev-orchestrator/runtime completes phase/hooks
  |
  v
terminal finalize moves active run to history only after evidence is recorded
  |
  v
workflow.py final-commit commits final governance artifacts as defined by workflow-final-tail-commit
```

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/scripts/workflow.py` | Gate support, final evidence before finalize, semantic archive evidence migration, lightweight-flow Superpowers artifact archive support as needed. |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | Keep runtime template in sync. |
| `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml` | Archive evidence criteria update or backward-compatible migration. |
| `docs/superpowers/archive/` | Destination for archived lightweight-flow spec and plan files. |
| `agents/dev-orchestrator.md` | Ask for branch finish decision, record it, and keep terminal ownership. |
| `agents/finish-agent.md` | Require decision gate, archive lightweight-flow Superpowers artifacts, forbid silent choice/finalize, return structured final evidence. |
| `.opencode/agents/*`, `.claude/agents/*`, `.cursor/agents/*` | Distributed copies generated from canonical agents. |
| `tests/test_workflow.py` | Runtime tests for gate behavior, final evidence invariant, archive evidence migration, and lightweight-flow artifact archive moves. |
| `tests/test_wrapper_contracts.py` | Prompt/permission contract tests for finish-agent and dev-orchestrator. |

## Acceptance Criteria

- Worktree/feature-branch finish cannot proceed without explicit `branch_finish_decision`.
- Allowed branch decisions are exactly `merge_local`, `create_pr`, `keep_branch`, and `discard`.
- No default branch finish action is silently selected.
- `finish-agent` returns blocker `missing_branch_finish_decision` when required decision is absent.
- `finish-agent` does not directly move active run to history or clear workflow pointer.
- Completed history run retains `finish-agent` evidence in `agent_results`.
- Implementation commits and workflow commits are described and recorded separately.
- Memory sync records target ref and target commit according to branch decision.
- Lightweight-flow uses `archive_action_completed`, `archive_artifact_path`, `archive_not_required_reason`, and `archived_design_artifact_paths` instead of misleading `archive_path_exists: true` for new runs.
- Completed lightweight-flow runs move matching Superpowers spec and plan files from `docs/superpowers/specs/` and `docs/superpowers/plans/` into `docs/superpowers/archive/`.
- Lightweight-flow archive evidence records both source and destination design artifact paths.
- Existing legacy runs using `archive_path_exists` remain readable during migration.
- Final workflow artifact commit after done remains owned by the `workflow-final-tail-commit` spec and is not redefined here.

## Risks / Trade-offs

**More user interaction before finish:** This is intentional. Branch outcome is a material source-control decision and must not be silently selected.

**Finish lifecycle becomes more complex:** The complexity already exists implicitly. This spec makes it explicit and testable.

**Memory sync semantics may need more ref plumbing:** Required to avoid syncing feature and main implicitly or recording misleading commit targets.

**Archive evidence migration may touch workflow criteria:** Use a backward-compatible transition so existing runs and tests do not break abruptly.

**Superpowers artifact matching can be ambiguous:** Prefer `primary_design_path` and `design_artifact_paths[]` over filename inference. If multiple matches exist, block instead of guessing.

**Archive moves are workflow commits, not implementation commits:** Moving spec/plan files into `docs/superpowers/archive/` should be treated as governance artifact cleanup and committed by the final workflow artifact commit boundary, not silently mixed into implementation branch semantics unless explicitly required by the chosen branch action.
