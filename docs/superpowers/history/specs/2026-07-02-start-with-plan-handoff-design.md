# Start-With-Plan Handoff Design

## Context

Before using `dev-orchestrator`, a user may use opencode Plan Mode to brainstorm and produce existing design artifacts. Those artifacts may be either OpenSpec change artifacts under `openspec/changes/<change-id>/` or Superpowers documents under `docs/superpowers/specs/` and `docs/superpowers/plans/`.

After those artifacts exist, the user wants to tell `dev-orchestrator` to implement the requirement without redispatching `plan-agent`. The workflow still needs to be governed by the SDLC runtime so implementation gets the existing `implement-agent`, `test-agent`, and `review-agent` quality gates.

## Goals / Non-Goals

**Goals:**
- Support implementation handoff from existing OpenSpec artifacts and existing Superpowers plan artifacts.
- Keep `dev-orchestrator` as a routing coordinator only: it collects `flow_type` and `primary_design_path`, starts or resumes the workflow, and dispatches the correct lifecycle agent.
- Skip `plan-agent` only when a valid existing design artifact set is selected.
- Let workflow runtime infer phase from `flow_type` and artifacts; do not add an `--initial-phase` override.
- Preserve governed execution: `workflow.py start/resume`, `before-dispatch`, `implement-agent`, `test-agent`, `review-agent`, and normal evidence handling.

**Non-Goals:**
- Do not implement a new planning system.
- Do not make `dev-orchestrator` inspect implementation details or design a solution.
- Do not treat start-with-plan as `superpowers-direct`; it remains governed lifecycle execution.
- Do not add broad fuzzy matching across arbitrary document directories.
- Do not change the existing OpenSpec artifact model.

## Decisions

### Decision 1: Use Existing Artifact Contract Names

The handoff input uses the already established design artifact contract:

- `flow_type`: `spec-flow` or `lightweight-flow`
- `primary_design_path`: the selected main design artifact
- `design_artifact_paths[]`: structured related artifacts forwarded to workers

Do not introduce a separate `plan_path` field. `primary_design_path` is the canonical field for both OpenSpec and Superpowers handoff.

### Decision 2: Runtime Infers Phase By Flow Type

`workflow.py start` will determine `flow_type` before phase inference and pass it into `_infer_phase`:

```python
flow_type = args.flow_type or "spec-flow"
phase = _infer_phase(root, subject_type, subject_id, flow_type)
```

The runtime remains the sole owner of workflow phase state. Agents do not force an initial phase.

### Decision 3: `spec-flow` Keeps Existing OpenSpec Inference

For `subject_type=spec_change` and `flow_type=spec-flow`, `_infer_phase` keeps the current OpenSpec behavior:

| OpenSpec classification | Phase |
|---|---|
| `missing`, `scaffold`, `unknown` | `create_change` |
| `active`, `in-progress` | `apply_change` |
| `complete` | `archive_change` |
| `archived` | `post_archive_actions` |

This means an OpenSpec change with incomplete `tasks.md` already starts at `apply_change` and can dispatch `implement-agent` without a new API.

### Decision 4: `lightweight-flow` Infers Apply Phase From Superpowers Plan

For `subject_type=spec_change` and `flow_type=lightweight-flow`, `_infer_phase` checks whether a matching Superpowers plan exists.

Matching is deterministic and conservative:

- Candidate files live under `docs/superpowers/plans/*.md`.
- A plan matches when the plan filename stem contains the `subject_id` slug, or when the stem with a leading date prefix removed equals the `subject_id` slug.
- If exactly one matching plan exists, return `apply_change`.
- If no matching plan exists, return `create_change`.
- If multiple matching plans exist, return `create_change`; `dev-orchestrator` must ask the user to choose a `primary_design_path` before starting or resuming the run.

This keeps runtime deterministic and prevents it from guessing among multiple plans.

### Decision 5: `dev-orchestrator` Collects Handoff Inputs

When the user asks to implement an existing design, `dev-orchestrator` collects two routing inputs before dispatch:

- `flow_type`
- `primary_design_path`

Input handling:

| User input | `dev-orchestrator` behavior |
|---|---|
| Provides both `flow_type` and `primary_design_path` | Validate that the path belongs to the flow, derive `subject_id`, then start/resume and dispatch implementation. |
| Provides only `flow_type` | List apply-ready candidates for that flow and ask the user to select `primary_design_path`. |
| Provides only `primary_design_path` | Infer `flow_type` by path rules; ask if ambiguous. |
| Provides neither | Ask for `flow_type` first, then list candidates for that flow. |

Path-to-flow rules:

- `openspec/changes/<change-id>/...` -> `spec-flow`
- `docs/superpowers/plans/...` -> `lightweight-flow`
- `docs/superpowers/specs/...` -> `lightweight-flow`, but a related `kind=plan` artifact must be found or selected before implementation.

### Decision 6: Start-With-Plan Is Governed Execution, Not Direct Execution

`superpowers-direct` means small tasks that do not create a workflow run and do not use lifecycle agents. Start-with-plan is different:

- It starts or resumes a workflow run.
- It calls `before-dispatch`.
- It dispatches `implement-agent`.
- It continues to `test-agent` and `review-agent` through normal `after-dispatch` routing.

The only skipped lifecycle worker is `plan-agent`, and only because the user selected existing design artifacts.

### Decision 7: Workflow Run Initialization From Selected Design Artifact

When `flow_type` and `primary_design_path` are known, `dev-orchestrator` initializes the workflow run from the selected artifact instead of asking `plan-agent` to create artifacts.

Initialization rules:

| Flow | `primary_design_path` | Derived `subject_type` | Derived `subject_id` | Start command |
|---|---|---|---|---|
| `spec-flow` | `openspec/changes/<change-id>/...` | `spec_change` | `<change-id>` | `workflow.py start --workflow sdlc-main --subject-type spec_change --subject-id <change-id> --flow-type spec-flow` |
| `lightweight-flow` | `docs/superpowers/plans/YYYY-MM-DD-<slug>.md` | `spec_change` | `<slug>` | `workflow.py start --workflow sdlc-main --subject-type spec_change --subject-id <slug> --flow-type lightweight-flow` |

Before starting a new run, `dev-orchestrator` must run:

1. `workflow.py verify-foundations`
2. `workflow.py status --subject-type <subject_type> --subject-id <subject_id>`

If `status` finds a matching active run, `dev-orchestrator` resumes or continues that run instead of starting a duplicate. If no matching active run exists, it calls the start command above. The runtime then calls `_infer_phase(..., flow_type)`; if the selected artifact set is apply-ready, the run starts in `apply_change` and `dev-orchestrator` may call `before-dispatch --agent implement-agent`.

If the runtime starts in `create_change`, `dev-orchestrator` must not force implementation. It should report that the selected artifact is missing, ambiguous, or not apply-ready, then ask the user to choose a valid `primary_design_path` or explicitly request new planning.

## Flow

```text
User: implement existing plan
  |
  v
dev-orchestrator
  |- collect flow_type + primary_design_path
  |- derive subject_id from selected artifact
  |- verify-foundations
  |- status --subject-type <subject_type> --subject-id <subject_id>
  |- start or resume the matching run
  v
workflow.py start
  |- _infer_phase(..., flow_type)
  |- spec-flow: OpenSpec artifact inference
  |- lightweight-flow: Superpowers plan inference
  v
apply_change phase
  |
  v
before-dispatch --agent implement-agent
  |
  v
implement-agent -> test-agent -> review-agent
```

## Artifact Selection Rules

### `spec-flow`

The selected `primary_design_path` should normally be `openspec/changes/<change-id>/tasks.md` because implementation depends most directly on tasks.

`design_artifact_paths[]` should include:

- `kind=proposal`: `openspec/changes/<change-id>/proposal.md`
- `kind=design`: `openspec/changes/<change-id>/design.md` when present
- `kind=tasks`: `openspec/changes/<change-id>/tasks.md`
- `kind=spec`: every `openspec/changes/<change-id>/specs/**/spec.md`

### `lightweight-flow`

The selected `primary_design_path` should be `docs/superpowers/plans/<plan>.md`.

`design_artifact_paths[]` should include:

- `kind=plan`: selected Superpowers plan
- `kind=spec`: related `docs/superpowers/specs/<topic>-design.md` when found or selected

If the user provides a Superpowers spec path but no related plan can be determined, `dev-orchestrator` asks the user to select the plan before implementation.

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/scripts/workflow.py` | Pass `flow_type` into `_infer_phase`; add lightweight-flow Superpowers plan inference. |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | Keep bootstrap workflow template in sync with live runtime. |
| `agents/dev-orchestrator.md` | Add start-with-plan handoff routing, input collection rules, and dispatch behavior. |
| `.opencode/agents/dev-orchestrator.md` | Distributed copy generated from canonical agent. |
| `.claude/agents/dev-orchestrator.md` | Distributed copy generated from canonical agent. |
| `.cursor/agents/dev-orchestrator.md` | Distributed copy generated from canonical agent. |
| `tests/test_workflow.py` | Runtime tests for flow-type phase inference. |
| `tests/test_wrapper_contracts.py` | Agent prompt and distributed-copy contract tests as needed. |
| `tests/test_sdlc_orchestrator.py` | Static orchestrator behavior contract tests as needed. |

## Risks / Trade-offs

**Multiple matching Superpowers plans:** runtime will not guess. It returns `create_change`; `dev-orchestrator` must ask the user to select `primary_design_path`.

**Subject id derivation:** `dev-orchestrator` should derive `subject_id` from the selected artifact path. For dated Superpowers plans, strip the leading date from the filename stem when deriving the slug.

**Prompt-only enforcement is insufficient:** runtime tests are required for `_infer_phase` behavior so phase inference remains executable behavior, not only documented text.

**Lightweight archive semantics remain unchanged:** this design only covers starting implementation from an existing plan. Finishing and archive behavior continue through existing lifecycle rules.

## Acceptance Criteria

- Starting `spec-flow` for an OpenSpec change with incomplete `tasks.md` still enters `apply_change`.
- Starting `lightweight-flow` for a subject with exactly one matching `docs/superpowers/plans/*.md` enters `apply_change`.
- Starting `lightweight-flow` with no matching plan enters `create_change`.
- Starting `lightweight-flow` with multiple matching plans does not guess; it does not enter `apply_change`.
- `dev-orchestrator` documents the four input cases for `flow_type` and `primary_design_path`.
- `dev-orchestrator` documents that start-with-plan skips `plan-agent` but still uses workflow hooks and lifecycle agents.
