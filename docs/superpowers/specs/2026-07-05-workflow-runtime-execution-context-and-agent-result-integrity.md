# Workflow Runtime Execution Context and Agent Result Integrity

## Context

The `2026-07-05-incremental-derived-artifact-sync-filtering` run exposed a control-plane/data-plane mismatch:

- Workflow run state lived in the main/control checkout.
- Implementation changes lived in a feature worktree.
- Runtime context recorded only `change_id`, not the execution source of truth.
- Agent results lost `slice_id` and did not persist important artifacts such as `worktree_path`.
- The final run history did not contain `finish-agent` as the final recorded agent result.

This spec makes workflow execution context explicit while preserving compatibility with non-worktree execution. Worktree mode becomes a supported execution mode, not a global assumption.

## Goals / Non-Goals

**Goals:**

- Add an explicit execution context model that supports both `main_checkout` and `worktree` modes.
- Persist worktree metadata only when worktree mode is used.
- Make `before-dispatch` output canonical `runtime_context` for downstream agents.
- Make `after-dispatch` preserve `slice_id` from CLI, agent result, or dispatch intent.
- Persist agent artifacts in `run.json`, not only in handoff markdown.
- Preserve existing non-worktree/main-checkout workflows.
- Reduce evidence loss before terminal archive/finalization.

**Non-Goals:**

- Do not implement branch finish decision gates; that belongs to the finish lifecycle spec.
- Do not require every run to use a worktree.
- Do not move workflow run state into worktrees.
- Do not implement workspace hydration; that belongs to the verification hygiene spec.
- Do not replace all agent prompts with runtime scripts in this spec.

## Covered Optimization Points

This spec covers or partially covers these optimization points from the run analysis:

- **2. Worktree path is not workflow first-class context** — introduce execution context fields for worktree mode.
- **3. Review-agent defaults to cwd** — provide runtime context consumed by review-agent; prompt hardening is in Spec 1.
- **4. Finish-agent archives before orchestrator after-dispatch** — add runtime integrity requirements so final agent evidence must be recorded before terminal movement; detailed finish ownership is in Spec 4.
- **5. Agent result slice_id lost** — fix after-dispatch slice fallback and persistence.
- **6. Finish-agent final evidence missing from run.json** — require final agent evidence to persist before terminal finalization.
- **7. Main/worktree commit responsibilities confused** — define execution context source of truth for implementation vs control checkout; branch policy is in Spec 4.
- **15. after-dispatch should inherit slice_id from result or dispatch intent** — direct runtime fix.
- **16. before-dispatch should output canonical runtime context** — direct runtime fix.
- **17. finish-agent should separate branch decision and archive execution** — deferred to Spec 4, but runtime context must support it.
- **18. runtime should prevent finish-agent from terminal finalize** — deferred to Spec 4, but this spec defines evidence-before-finalize invariant.
- **19. runtime should support final evidence before terminal move** — direct design requirement.
- **20. implement/review evidence should include artifacts** — persist artifacts under `agent_results`.

## Decisions

### Decision 1: Add `context.execution_mode`

Workflow run context must distinguish two execution modes:

```json
{
  "context": {
    "change_id": "example-change",
    "execution_mode": "main_checkout"
  }
}
```

```json
{
  "context": {
    "change_id": "example-change",
    "execution_mode": "worktree",
    "control_root": "/path/to/main/checkout",
    "worktree_path": "/path/to/main/checkout/.worktrees/example-change",
    "base_branch": "main",
    "feature_branch": "feature/example-change",
    "parent_ref": "abc123"
  }
}
```

Allowed values:

```text
main_checkout
worktree
```

If missing in legacy runs, runtime must treat it as `main_checkout` unless worktree-specific evidence is present.

### Decision 2: Worktree Fields Are Required Only in Worktree Mode

For `execution_mode=main_checkout`:

- `worktree_path` is not required.
- `feature_branch` is not required.
- Review may use plain Git commands against current checkout.
- Memory sync defaults to current checkout/ref unless another ref is explicitly specified.

For `execution_mode=worktree`:

- `control_root` is required.
- `worktree_path` is required.
- `feature_branch` is required.
- `base_branch` and `parent_ref` should be recorded when known.
- Review/finish agents must treat `worktree_path` as implementation source of truth.

### Decision 3: Workflow Run State Remains in Control Root

Do not copy `.ai/workflows/runs/active`, `.ai/workflows/runs/current.json`, or `.ai/workflows/runs/history` into the implementation worktree.

The main/control checkout owns workflow run state. The worktree owns implementation source changes. The bridge between them is runtime context and agent artifacts.

### Decision 4: `before-dispatch` Emits Runtime Context

`before-dispatch` output must include a `runtime_context` object derived from `state.context`:

```json
{
  "agent": "review-agent",
  "status": "dispatched",
  "phase": "apply_change",
  "slice_id": "example-change",
  "flow_type": "lightweight-flow",
  "runtime_context": {
    "execution_mode": "worktree",
    "control_root": "/path/to/main",
    "worktree_path": "/path/to/main/.worktrees/example-change",
    "base_branch": "main",
    "feature_branch": "feature/example-change",
    "parent_ref": "abc123",
    "change_id": "example-change"
  },
  "recommended_next_action": "execute_agent"
}
```

Agents should not infer source-of-truth paths from prose when `runtime_context` is available.

### Decision 5: Add a Controlled Context Recording Path

Runtime should provide or extend a command to record execution context, for example:

```bash
python3 .ai/workflows/scripts/workflow.py --root . record-context --key execution_mode --value worktree
python3 .ai/workflows/scripts/workflow.py --root . record-context --key worktree_path --value <path>
python3 .ai/workflows/scripts/workflow.py --root . record-context --key feature_branch --value <branch>
```

If an aggregate command is added, it must validate mode-specific requirements before writing.

### Decision 6: after-dispatch Slice ID Fallback Order

`after-dispatch` must compute `slice_id` using this precedence:

```text
1. CLI --slice-id
2. agent_result.slice_id
3. state.evidence.agent_phase.slice_id
4. state.context.change_id
5. "default"
```

This prevents correctly structured agent JSON from being persisted under `default` when the CLI omits `--slice-id`.

### Decision 7: Persist Agent Artifacts in Run State

`after-dispatch` must persist artifacts alongside evidence:

```json
{
  "evidence": {
    "agent_results": {
      "example-change": {
        "implement-agent": {
          "agent": "implement-agent",
          "status": "success",
          "phase": "apply_change",
          "slice_id": "example-change",
          "flow_type": "lightweight-flow",
          "evidence": {},
          "artifacts": {
            "worktree_path": "...",
            "repo_root": "...",
            "base_ref": "...",
            "feature_branch": "...",
            "changed_files": [],
            "diff_commands": [],
            "verification_commands": [],
            "handoff_path": "..."
          },
          "blockers": [],
          "recommended_next_action": "dispatch_review_agent"
        }
      }
    }
  }
}
```

The latest `evidence.agent_result` should also include `artifacts` so the most recent result is complete.

### Decision 8: Define Minimum Agent Artifact Contract

For implementation work packages, `implement-agent` should return these artifacts when available:

```json
{
  "artifacts": {
    "worktree_path": "...",
    "repo_root": "...",
    "base_ref": "...",
    "feature_branch": "...",
    "changed_files": [],
    "diff_commands": [],
    "verification_commands": [],
    "handoff_path": "...",
    "design_artifact_paths": []
  }
}
```

`review-agent` should return:

```json
{
  "artifacts": {
    "worktree_path": "...",
    "reviewed_changed_files": [],
    "handoff_path": "..."
  }
}
```

`finish-agent` should return:

```json
{
  "artifacts": {
    "worktree_path": "...",
    "feature_branch": "...",
    "branch_finish_action": "...",
    "handoff_path": "..."
  }
}
```

### Decision 9: Final Evidence Must Be Recorded Before Terminal Move

A workflow run must not be moved from active to history before the final lifecycle worker's result is persisted.

Accepted implementation options:

Option A — add a single atomic command:

```bash
workflow.py finalize-after-dispatch --agent finish-agent --value '<json-result>' --slice-id <slice-id>
```

This command records the agent result, validates terminal conditions, then moves active run to history.

Option B — modify existing terminal commands so they refuse to finalize unless the latest required final agent result has been recorded.

Either option must prevent a history `run.json` from reaching `status=done` while missing the relevant final `finish-agent` result for `archive_change` / `post_archive_actions`.

### Decision 10: Backward Compatibility for Existing Runs

Legacy run states without `execution_mode` remain valid. Runtime validation must not fail historical `run.json` files solely because the new fields are absent.

Migration behavior:

- Missing `execution_mode` -> interpret as `main_checkout`.
- Missing `agent_results[...][...].artifacts` -> treat as empty artifacts.
- Existing `slice_id=default` records remain readable, but new records should use the corrected fallback order.

## Flow

```text
workflow.py start/resume
  |
  |- context.execution_mode = main_checkout | worktree
  v
before-dispatch
  |- validates agent/phase
  |- emits runtime_context
  v
agent executes with runtime_context
  v
after-dispatch
  |- reads result JSON
  |- resolves slice_id using fallback order
  |- persists evidence + artifacts
  |- returns next workflow command
  v
terminal movement only after final agent evidence is persisted
```

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/scripts/workflow.py` | Add execution context handling, runtime_context output, slice fallback, artifact persistence, final evidence invariant. |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | Keep bootstrap runtime template in sync. |
| `agents/dev-orchestrator.md` | Require dispatch prompts to forward runtime_context and avoid path inference from prose. |
| `agents/implement-agent.md` | Return minimum artifact envelope when implementation changes are made. |
| `agents/review-agent.md` | Prefer runtime_context and artifact worktree fields for source-of-truth selection. |
| `agents/finish-agent.md` | Return final artifacts; do not rely on prose-only handoff evidence. |
| `.opencode/agents/*`, `.claude/agents/*`, `.cursor/agents/*` | Distributed copies generated from canonical agents. |
| `tests/test_workflow.py` | Runtime tests for execution_mode validation, before-dispatch runtime_context, after-dispatch slice fallback, artifact persistence, and final evidence invariant. |
| `tests/test_wrapper_contracts.py` | Agent JSON artifact contract and distributed prompt checks. |

## Acceptance Criteria

- Existing main-checkout runs still start, resume, dispatch, and complete without worktree fields.
- Worktree-mode runs can record and expose `worktree_path`, `feature_branch`, `base_branch`, `parent_ref`, and `control_root`.
- `before-dispatch` output includes `runtime_context`.
- `after-dispatch` uses the slice fallback order: CLI > agent result > dispatch intent > change_id > default.
- `after-dispatch` persists agent `artifacts` under both latest result and `agent_results[slice][agent]`.
- A final history `run.json` cannot be marked done while missing required final lifecycle agent evidence.
- Historical runs without `execution_mode` remain valid.

## Risks / Trade-offs

**Runtime context can become too large:** Keep it limited to source-of-truth fields and identifiers. Do not copy large handoff content into context.

**Backward compatibility can hide missing worktree context:** Only default to `main_checkout` when no worktree-specific evidence is present. If `execution_mode=worktree`, missing required worktree fields must block.

**Atomic finalize may overlap finish-agent lifecycle changes:** This spec should define the invariant. The finish lifecycle spec can decide the exact orchestration policy and branch decision gate.

**Artifacts may duplicate handoff content:** Persist only machine-readable artifact references and command lists, not full markdown handoff bodies.
