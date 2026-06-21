## Context

The repository already has specialized SDLC skills for Roadmap, OpenSpec, EvalOps, Memory, and Superpowers. The current `sdlc-orchestrator` coordinates those skills through instructions, but it does not own a durable workflow state. When an external worker skill completes, the next cross-skill lifecycle step depends on the assistant continuing the correct route in the same session. This failed for an archived OpenSpec change whose linked roadmap item remained active.

The design goal is to add a lightweight workflow runtime that makes phase state, resume behavior, required inputs, exit criteria, hooks, and blocked states explicit. The runtime must not fork or modify upstream `openspec-*` skills. Those skills remain worker capabilities invoked by the orchestrator.

## Goals / Non-Goals

**Goals:**

- Add `.ai/workflows/` as the durable home for workflow definitions, current run state, run history, and deterministic workflow scripts.
- Define a first `sdlc-main` workflow that models the full SDLC path: input, memory loading, brainstorming, intent decision, roadmap creation/review, OpenSpec change creation, apply, archive, post-archive actions, and done.
- Add `workflow.py` as the deterministic runtime that owns workflow run state, phase readiness, evidence, blocking, hook completion, and legal phase transitions.
- Keep domain state separate: Roadmap item state remains owned by `sdlc-roadmap`, OpenSpec state remains owned by `openspec-*`/CLI, EvalOps state remains owned by `sdlc-evalops`, and Memory state remains owned by memory skills.
- Require post-archive hooks for memory sync and roadmap completion so archived changes cannot be treated as done until post-archive actions are resolved.
- Coordinate roadmap state transitions at workflow boundaries: OpenSpec artifact completion can make a linked roadmap item ready, apply start can make it active, and post-archive completion can make it done.
- Support session resume through explicit resume intent or subject matching without automatically hijacking unrelated new-session work.
- Verify behavior through temporary-workspace fixtures so tests do not mutate real `.ai/roadmap`, `.ai/workflows`, or `openspec` data.

**Non-Goals:**

- Do not implement a background watcher, daemon, or file-system event listener.
- Do not support multiple concurrent active workflow runs in the first version.
- Do not implement a general DAG engine, parallel workers, or plugin system.
- Do not modify upstream `openspec-*` skills.
- Do not let `workflow.py` directly edit domain state such as roadmap item files, OpenSpec artifacts, eval datasets, or memory documents.
- Do not auto-skip failed evals, ambiguous roadmap links, or missing required inputs.
- Do not implement full cancellation UX in the first version; `cancelled` is a reserved run status for explicit future or manual cancellation handling.

## Decisions

### Decision 1: Use `.ai/workflows/` for durable workflow runtime state

Workflow runtime files will live under `.ai/workflows/`:

```text
.ai/workflows/
  definitions/
    sdlc-main.yaml
  runs/
    current.json
    history/
  scripts/
    workflow.py
```

Rationale: workflow state is a repository-local SDLC asset alongside `.ai/roadmap`, `.ai/memory`, and `.ai/evals`. It is not OpenCode configuration and should not live under `.opencode/`. It is also more durable than an agent scratchpad.

`workflow.py` will be initialized into `.ai/workflows/scripts/` by `sdlc-project-bootstrap`. The runtime script location is part of the project workflow foundation, while skill instructions remain responsible for invoking it through the orchestrator.

Alternatives considered:

- `.opencode/workflows/`: rejected because workflow run state is not tool configuration.
- `.agent/workflows/`: rejected for the first version because the repository already uses `.ai/` for durable SDLC assets.

### Decision 2: Separate workflow state, domain state, and evidence

The workflow runtime will own only workflow run state and evidence references. Domain states remain owned by their domain skills.

| State | Source of Truth | Writer |
|---|---|---|
| Workflow run state | `.ai/workflows/runs/current.json` | `workflow.py` |
| Roadmap domain state | `.ai/roadmap/areas/*/items/*.md` | `sdlc-roadmap` |
| OpenSpec domain state | `openspec/changes/*`, `openspec/specs/*` | `openspec-*` / OpenSpec CLI |
| EvalOps domain state | `.ai/evals/*` | `sdlc-evalops` |
| Memory domain state | `.ai/memory/*` | memory skills |
| Evidence | workflow run `evidence` | `workflow.py` after observation or worker results |

Rationale: this avoids making the workflow engine a new owner of all SDLC data. For example, when an archived change needs a roadmap item marked done, the orchestrator invokes `sdlc-roadmap done`; `workflow.py` only verifies the roadmap item reached `done` and records evidence.

### Decision 3: Make `workflow.py` deterministic and non-interactive

`workflow.py` will expose commands for state and transition management:

```text
status
start
resume
readiness
resolve
record-evidence
complete-phase
complete-hook
advance
block
done
validate
```

It will read workflow definitions and run state, run deterministic loaders, compute `phase_readiness`, record evidence, block when inputs or decisions are missing, and prevent illegal transitions. It will not call skills, ask user questions, or modify domain state.

Rationale: this keeps the runtime testable and prevents prompt-dependent state mutations. The orchestrator remains responsible for user interaction and worker dispatch.

### Decision 4: Keep `sdlc-orchestrator` as policy and dispatch layer

The orchestrator will start or resume runs, call `workflow.py readiness` before phase workers, invoke allowed worker skills, call `workflow.py complete-phase` or `complete-hook` after workers finish, and explain blocked states to the user.

Rationale: the orchestrator should decide and dispatch, not directly edit `current.json` or duplicate worker logic. It remains the user-facing policy layer while `workflow.py` is the deterministic state machine.

### Decision 5: Model `sdlc-main` as the first workflow

The first workflow will cover the full SDLC flow:

```text
input
load_memory
brainstorm
decide_intent
create_roadmap
review_roadmap
review_decision
create_change
apply_change
archive_change
post_archive_actions
done
```

`create_change`, `apply_change`, and `archive_change` use existing OpenSpec skills as workers. A separate nested `openspec-change` workflow is deferred until the main flow is stable.

Rationale: the post-archive bug came from treating OpenSpec archive as the full workflow. The first runtime should model the complete SDLC lifecycle instead of only the OpenSpec subset.

### Decision 6: Use phase readiness and blocked states before worker execution

Each phase defines required inputs. `workflow.py readiness` computes:

```json
{
  "phase": "archive_change",
  "ready": false,
  "missing_required_inputs": ["context.change_id"]
}
```

If readiness fails, the run becomes blocked and only input resolution is allowed. Missing inputs are not errors; they are deterministic control signals.

Rationale: phase readiness enables context routing and prevents workers from running with incomplete context. It also supports session resume because the next action is explicit.

### Decision 7: Post-archive actions are required hooks, not optional follow-up text

`post_archive_actions` will include at least:

```text
memory_sync
roadmap_done_if_relevant
```

`archive_change` completion only proves that the change moved to `openspec/changes/archive/`. The workflow cannot enter `done` while required post-archive hooks remain pending.

`memory_sync` is mandatory in `post_archive_actions`. It can complete only when memory is synced or when a formal resolution is recorded by the workflow; unlike optional hooks, it cannot be omitted from the post-archive phase.

Rationale: this directly prevents the archived-change/active-roadmap mismatch from being silently accepted as complete.

### Decision 8: Resume is intent-aware, not automatic session takeover

New sessions may detect an active workflow, but they should not automatically resume it. Resume occurs when the user explicitly asks to resume or when the incoming request subject matches the active run's `primary_subject`.

Rationale: durable workflow state should preserve continuity without hijacking unrelated new work or brainstorming sessions.

### Decision 9: Tests use explicit temporary roots

`workflow.py` will support an explicit root argument, such as:

```bash
workflow.py --root /tmp/workspace start --workflow sdlc-main --subject-type openspec_change --subject-id demo-change
```

Tests create fixture workspaces under temporary directories and assert that `workflow.py` writes only under `.ai/workflows/runs/`.

Rationale: the runtime must be tested against archived OpenSpec and roadmap states without mutating real repository data.

### Decision 10: Support one active run first, then multiple active runs

The first implementation will keep one active run for simplicity, but the workflow model must not preclude multiple active runs in a future version. Future multi-run support should move from a single `current.json` active run to per-run files plus an active-run index while preserving the same phase, hook, and evidence semantics.

Rationale: one active run is enough to validate the runtime and prevent post-archive skips, but SDLC work eventually needs multiple active workflow runs for concurrent changes.

## Runtime Contracts

### Run State Shape

The first version of `.ai/workflows/runs/current.json` will use this shape:

```json
{
  "version": 1,
  "run_id": "2026-06-18-demo-change",
  "workflow": "sdlc-main",
  "status": "running",
  "current_phase": "post_archive_actions",
  "primary_subject": {
    "type": "openspec_change",
    "id": "demo-change"
  },
  "context": {
    "change_id": "demo-change",
    "roadmap_item_id": "RM-DEMO-001",
    "eval_target_id": "skill.demo"
  },
  "phase_readiness": {
    "phase": "post_archive_actions",
    "ready": true,
    "missing_required_inputs": []
  },
  "pending_hooks": [
    "memory_sync",
    "roadmap_done_if_relevant"
  ],
  "completed_hooks": [],
  "completed_phases": [
    "input",
    "load_memory",
    "brainstorm",
    "decide_intent",
    "create_change",
    "apply_change",
    "archive_change"
  ],
  "gates": {},
  "evidence": {
    "archive_path": "openspec/changes/archive/2026-06-18-demo-change"
  },
  "block": null,
  "updated_at": "2026-06-18T00:00:00"
}
```

Field semantics:

- `workflow` names the workflow definition, initially `sdlc-main`.
- `run_id` names the workflow instance. For OpenSpec changes, the initial format is `<YYYY-MM-DD>-<change-id>`.
- `primary_subject` is the stable resume key. If a new session request references the same subject, the orchestrator resumes this run instead of creating another.
- `context` stores cross-phase business references, not domain state ownership.
- `context.eval_target_id` is conditionally required. When the orchestrator classifies a workflow path as needing semantic EvalOps verification, `eval_target_id` must be present before the EvalOps gate can run. When the workflow only requires deterministic unit tests or other non-semantic checks, `eval_target_id` is not required.
- `phase_readiness` stores the current phase's readiness check result. When `ready` is false, only input resolution is allowed.
- `pending_hooks` blocks workflow completion until every required hook is resolved.
- `gates` stores resolution records for cross-cutting quality gates that are not domain state and are not post-archive hooks.
- `evidence` records observations or worker outputs used to prove exit criteria.
- `block` is `null` unless `status` is `blocked`.

`gates` is a workflow-owned ledger for gate outcomes such as deterministic testing, EvalOps, and human-approved exceptions. It does not own test files, eval cases, or memory content. Those remain domain state or external evidence. A gate record should include status, evidence references, and any human decision that allows the workflow to proceed.

Example:

```json
{
  "gates": {
    "tdd": {
      "status": "passed",
      "evidence": "pytest tests/test_workflow.py",
      "checked_at": "2026-06-18T00:00:00"
    },
    "evalops": {
      "status": "passed",
      "eval_target_id": "skill.demo",
      "evidence": ".ai/evals/targets/skill.demo/reports/latest.json",
      "checked_at": "2026-06-18T00:00:00"
    }
  }
}
```

Valid gate status values for the MVP are:

```text
required
passed
not_required
user_exception
failed
```

If a semantic EvalOps gate fails, the workflow blocks with `eval_failed` and requires a human decision before continuing. Valid next actions are to revise implementation, revise eval cases, revise spec, or accept an explicit EvalOps exception with reason and residual risk.

When a run reaches `done`, `workflow.py done` keeps `.ai/workflows/runs/current.json` as the latest run with `status: done` and also writes an immutable copy to `.ai/workflows/runs/history/<run_id>.json`. New sessions therefore can distinguish a completed latest run from an active run without scanning history.

Valid `status` values for the MVP are:

```text
running
blocked
done
cancelled
```

Valid `block.type` values for the MVP are:

```text
missing_required_inputs
user_decision_required
worker_failed
exit_criteria_failed
eval_failed
hook_blocked
domain_state_mismatch
```

### `sdlc-main` Phase Contract

The MVP workflow definition will model these phases:

| Phase | Purpose | Primary workers | Exit criteria |
|---|---|---|---|
| `input` | Capture the initial request and subject | `sdlc-orchestrator` | `primary_subject_recorded` |
| `load_memory` | Load relevant repository memory if initialized | `sdlc-repository-memory-load` | `memory_context_loaded_or_not_initialized` |
| `brainstorm` | Clarify intent and design direction | `brainstorming` | `intent_ready_for_classification` |
| `decide_intent` | Choose roadmap or change path | `sdlc-orchestrator` | `workflow_branch_selected` |
| `create_roadmap` | Create roadmap item when requested | `sdlc-roadmap` | `roadmap_item_created` |
| `review_roadmap` | Review roadmap idea before promotion | `sdlc-roadmap` | `review_decision_recorded` |
| `review_decision` | Branch on review result | `sdlc-orchestrator` | `review_passed_or_failed` |
| `create_change` | Create complete OpenSpec artifacts | `openspec-propose`, `openspec-new-change`, `openspec-continue-change` | `openspec_artifacts_done` |
| `apply_change` | Implement and verify with TDD/EvalOps gates | `openspec-apply-change`, Superpowers, `sdlc-evalops` | `tasks_complete`, `tdd_passed`, `eval_passed_or_human_decision_recorded` |
| `archive_change` | Archive the OpenSpec change | `openspec-archive-change` | `archive_path_exists` |
| `post_archive_actions` | Resolve mandatory post-archive hooks | `sdlc-orchestrator`, memory skills, `sdlc-roadmap` | `pending_hooks_empty` |
| `done` | Close the run and write history | `sdlc-orchestrator`, `workflow.py` | `run_status_done` |

`archive_change` is not terminal. It only completes after `archive_path_exists`. The workflow then enters `post_archive_actions`, where `memory_sync` and `roadmap_done_if_relevant` must be resolved before `done`.

The workflow definition uses a constrained YAML shape:

```yaml
version: 1
id: sdlc-main
phases:
  create_change:
    required_inputs:
      - context.change_id
    context_loaders:
      - openspec_change_status
      - roadmap_linked_item
    allowed_workers:
      - openspec-propose
      - openspec-new-change
      - openspec-continue-change
    exit_criteria:
      - openspec_artifacts_done
    post_hooks:
      - roadmap_status_ready_if_linked
    next: apply_change
  review_decision:
    required_inputs:
      - context.review_decision
    branches:
      review_passed: create_change
      review_failed: review_roadmap
```

Supported phase fields for the MVP are `required_inputs`, `context_loaders`, `allowed_workers`, `exit_criteria`, `post_hooks`, `branches`, `next`, and `terminal`.

Branch phases use `branches` instead of a single `next`. `workflow.py advance` must require a recorded branch decision for branch phases and must reject unknown branch labels. For `decide_intent`, valid MVP branches are `create_roadmap` and `create_change`. For `review_decision`, valid branches are `review_passed` and `review_failed`.

`start` and `resume` infer the current phase for `primary_subject.type == "openspec_change"` from observable state:

```text
archive path exists -> post_archive_actions
active change exists and tasks complete and verification evidence exists -> archive_change
active change exists and tasks complete -> verify_change or apply_change blocked for verification evidence
active change exists -> apply_change
no active or archived change exists -> create_change
```

If the runtime cannot infer a safe phase from observable state, it blocks with `user_decision_required` and asks the orchestrator to get a phase decision from the user.

Roadmap state hooks around OpenSpec work are:

- `roadmap_status_ready_if_linked`: after `create_change`, if a linked roadmap item exists and OpenSpec artifacts are complete, the orchestrator routes to the roadmap worker to set the item to `ready` when applicable.
- `roadmap_apply_start_if_ready`: when `apply_change` begins for a linked roadmap item with `status: ready`, the orchestrator routes to the roadmap worker to set the item to `active` and `started_at`.
- `roadmap_done_if_relevant`: after archive, the orchestrator routes to `sdlc-roadmap done` when the linked item is active.

The workflow runtime detects and records these hooks but does not mutate roadmap files directly.

### `workflow.py` Command Contract

`workflow.py` commands have narrow responsibilities:

| Command | Writes state? | Purpose | Must not do |
|---|---:|---|---|
| `status` | No | Show current run, phase, hooks, block, and next allowed actions | Create/resume runs or mutate readiness |
| `start` | Yes | Create a new run or report that a matching active run should be resumed | Overwrite a different active run |
| `resume` | Yes | Recalculate loaders/readiness for the matching active run | Execute phase workers or hooks |
| `readiness` | Yes | Compute whether current phase required inputs are present | Guess missing inputs or call workers |
| `resolve` | Yes | Run deterministic loaders and fill resolvable context/evidence | Ask users or modify domain files |
| `record-evidence` | Yes | Record externally produced evidence | Complete phases or bypass exit criteria |
| `complete-phase` | Yes | Verify exit criteria and register phase post-hooks | Invoke workers or advance illegally |
| `complete-hook` | Yes | Verify hook completion evidence and clear resolved hooks | Invoke roadmap/memory workers |
| `advance` | Yes | Perform a guarded transition to the next phase | Force transition, skip hooks, or enter done early |
| `block` | Yes | Record a blocked state and allowed next actions | Choose a user decision |
| `done` | Yes | Close the workflow run and write history | Complete while hooks/gates are pending |
| `validate` | No | Validate workflow definition and run state consistency | Modify files |

Important command rules:

- `advance` is a guarded transition, not a force command.
- `done` is allowed only when `current_phase == "done"`, `pending_hooks == []`, `status != "blocked"`, and required gates are resolved.
- `resume` is state restoration and readiness recalculation; it does not continue execution by itself.
- All commands that inspect repository files must accept an explicit root, with tests always passing `--root <tmp-workspace>`.
- `resolve`, `record-evidence`, `complete-phase`, `complete-hook`, and `block` must be individually testable and must not trigger worker execution as a side effect.

### Deterministic Loaders

The MVP deterministic loaders are:

| Loader | Reads | Writes | Ambiguous behavior |
|---|---|---|---|
| `openspec_change_status` | `openspec/changes/*`, `openspec/changes/archive/*` | `evidence.openspec_status` | Block if state cannot be classified |
| `openspec_archive_path` | `openspec/changes/archive/*` | `evidence.archive_path` | Block if multiple archive paths match |
| `roadmap_linked_item` | `.ai/roadmap/areas/*/items/*.md` | `context.roadmap_item_id` or `evidence.roadmap_link` | Block with candidates if multiple matches exist |
| `roadmap_item_status` | linked roadmap item file | `evidence.roadmap_item_status` | Block if linked item is missing |

High-risk or ambiguous values are never guessed. `workflow.py` reports candidates and allowed actions; `sdlc-orchestrator` asks the user.

Loader outcomes are classified as:

- `deterministic`: a single value can be derived from files or CLI output and may be recorded by `workflow.py`.
- `user_confirmed`: multiple candidates or a high-risk inferred value exists; `workflow.py` blocks and the orchestrator asks the user.
- `manual_required`: no deterministic source exists; the orchestrator must ask the user for the missing input.

### Post-Archive Hook Contract

`post_archive_actions` includes these mandatory hooks:

```text
memory_sync
roadmap_done_if_relevant
```

`memory_sync` valid resolutions:

- `synced`: memory sync ran and produced evidence.
- `not_needed`: allowed only with an explicit reason explaining why no durable facts were produced.
- `user_deferred`: allowed only with an explicit reason and residual risk.

`roadmap_done_if_relevant` behavior:

- No linked roadmap item: complete with `no_linked_item` evidence.
- One linked item with `status: done` and non-null `completed_at`: complete idempotently.
- One linked item with `status: active`: block until the orchestrator invokes `sdlc-roadmap done <item-id>` and `workflow.py complete-hook` verifies `done`.
- One linked item with `status: idea`, `ready`, or `cancelled`: block with `domain_state_mismatch`.
- Multiple linked items: block with `user_decision_required`, return candidates, and allow these actions: choose one item to mark done, repair roadmap links manually, mark all active matches done with reason, or skip roadmap done with reason.

### Resume Semantics

Session start may detect an active workflow but does not automatically resume it. Resume occurs when either:

- the user explicitly asks to resume the workflow, or
- the incoming request subject matches `primary_subject`.

If an unrelated request arrives while a run is active, the orchestrator may mention the active run briefly but continues with the new topic unless the user chooses to resume.

If `current.json.status` is:

- `running`: resume returns the current phase and next allowed action.
- `blocked`: resume returns the block reason and next allowed actions.
- `done`: no active resume is needed.
- `cancelled`: restart requires explicit user intent.

### Test Matrix

The MVP tests will use temporary workspace fixtures with an explicit root and must cover:

| Case | Fixture state | Expected workflow result |
|---|---|---|
| Archived change + active roadmap | Archived `demo-change`, linked roadmap item `active` | `post_archive_actions`, pending `roadmap_done_if_relevant`, cannot `done` |
| Archived change + done roadmap | Linked item `done`, `completed_at` set | Hook completes idempotently, can reach `done` |
| Archived change + no roadmap link | No item has matching `openspec_change` | Hook completes with `no_linked_item` |
| Archived change + multiple roadmap links | Two items link the same change | Block `user_decision_required` with candidates |
| Archived change + non-active non-done roadmap | Linked item `idea`, `ready`, or `cancelled` | Block `domain_state_mismatch` |
| Missing required input | Current phase requires absent input | Block `missing_required_inputs` |
| Same-subject resume | Active run subject matches incoming subject | Same `run_id`, readiness recalculated, no new run |
| Different-subject resume | Active run subject differs | Conflict/user decision required; no overwrite |
| Memory sync deferred without reason | `complete-hook memory_sync --resolution user_deferred` without reason | Fail/block |
| Write-boundary protection | Test fixture includes roadmap and OpenSpec files | `workflow.py` writes only `.ai/workflows/runs/*` |

Fixtures will create minimal `openspec/changes/archive/<date>-demo-change/` and `.ai/roadmap/areas/<area>/items/*.md` structures under a temporary root. Tests must not call upstream `openspec-*` skills or real `sdlc-roadmap` mutations; domain changes are simulated by editing fixture files inside the test.

## Risks / Trade-offs

These risks and trade-offs are accepted for the MVP design.

- **Risk: Workflow runtime becomes a second orchestrator** -> Mitigation: keep `workflow.py` deterministic and non-interactive; keep policy and user choices in `sdlc-orchestrator`.
- **Risk: Workflow state duplicates domain state** -> Mitigation: store references and evidence, not authoritative domain values; validate domain state through loaders.
- **Risk: Post-archive memory sync happens later than the existing pre-archive gate** -> Mitigation: require explicit post-archive resolution states (`synced`, `not_needed`, or `user_deferred` with reason) before workflow `done`.
- **Risk: One active run is limiting** -> Mitigation: keep one active run as the MVP constraint, but design run IDs and state files so a later active-run index can support multiple active runs without changing phase semantics.
- **Risk: Ambiguous domain matches block workflow progress** -> Mitigation: return candidates and allowed decisions to the orchestrator; require human selection or repair for multiple roadmap links.
- **Risk: External worker summaries diverge from observable state** -> Mitigation: `complete-phase` verifies exit criteria from files/CLI/evidence instead of trusting chat summaries.

## Migration Plan

1. Update `sdlc-project-bootstrap` so it initializes `.ai/workflows/definitions/`, `.ai/workflows/runs/`, and `.ai/workflows/scripts/workflow.py` as part of the project SDLC foundation.
2. Add `.ai/workflows/definitions/sdlc-main.yaml` and initial run-state schema expectations.
3. Add `.ai/workflows/scripts/workflow.py` with read-only commands first: `status`, `validate`, and `readiness`.
4. Add run lifecycle commands: `start`, `resume`, `resolve`, `record-evidence`, `complete-phase`, `complete-hook`, `advance`, `block`, and `done`.
5. Update `sdlc-orchestrator` guidance to use the runtime for SDLC runs and post-archive hook coordination.
6. Update `sdlc-roadmap` guidance to clarify that roadmap domain state remains roadmap-owned and that workflow hooks invoke roadmap mutations.
7. Update memory sync expectations so `sdlc-main` treats memory sync as a mandatory post-archive action that must be resolved before workflow completion.
8. Add temporary-workspace tests for archived OpenSpec changes linked to active, done, missing, multiple, and mismatched roadmap items.

Rollback strategy: because the runtime is additive and does not modify upstream `openspec-*` skills, rollback can remove or ignore `.ai/workflows/` and restore prompt-only orchestrator behavior. Domain state remains in Roadmap, OpenSpec, EvalOps, and Memory files.

## Open Questions

- None for the MVP design. Settled decisions: `workflow.py` is initialized under `.ai/workflows/scripts/` by `sdlc-project-bootstrap`, `memory_sync` is mandatory in post-archive actions, and future versions should support multiple active runs after the one-active-run MVP is stable.
