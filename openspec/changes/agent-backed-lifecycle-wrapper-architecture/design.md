## Context

The `sdlc-orchestrator` currently routes directly to concrete worker skills (OpenSpec, Superpowers, Roadmap, Memory, EvalOps). This couples the workflow lifecycle to today's implementation choices. The goal is an agent-backed lifecycle wrapper architecture where `workflow.py` remains the deterministic state machine and `dev-orchestrator` routes phase actions to specialized agents through stable module-level wrapper contracts.

## Goals / Non-Goals

**Goals:**
- Define agent-backed wrapper interfaces for all lifecycle modules
- Introduce `dev-orchestrator` as a top-level agent that routes to specialized sub-agents (plan, implement, test, review, finish)
- Support explicit `spec-flow` and `lightweight-flow` flow types
- Keep `workflow.py` as the only owner of state transitions, hooks, and gates
- Map current skills as wrapped backends without changing user-visible behavior
- Move safe parallel dispatch to `dev-orchestrator` level
- Downgrade `sdlc-orchestrator` to manual-trigger only; default SDLC routing migrates to `dev-orchestrator`

**Non-Goals:**
- No replacement of existing skills in the first phase
- No generic agent framework rewrite
- No marketplace/plugin registry
- No nested subagent delegation for parallelism
- No full object-oriented state-machine rewrite of `workflow.py` in this change
- No rewrite of `sdlc-main.yaml` into the future high-level `plan` / `implement` / `review` / `finalize` / `done` phase model in this change

## Decisions

**Decision 1: Agent-backed wrappers as module contracts**

Each lifecycle module (spec, memory, roadmap, eval, planning, implementation, testing, review, finish, verification) gets a wrapper contract that defines inputs, outputs, evidence keys, exit criteria, and failure modes. Wrappers normalize agent/tool output into workflow evidence so downstream gates do not depend on tool-specific formats.

Rationale: Pure Python wrappers are predictable but rigid; raw agent calls are flexible but nondeterministic. Wrapper contracts at the boundary create a stable interface that both sides depend on, letting either side evolve independently.

**Decision 2: `dev-orchestrator` as routing coordinator, not executor**

`dev-orchestrator` receives the current allowed phase action from `workflow.py`, selects the appropriate specialized agent, optionally splits safe parallel work packages, collects structured evidence, and returns normalized results. It does not own workflow state transitions.

Rationale: Separating routing from execution prevents the orchestrator from becoming a bottleneck or monolithic hub. Each agent has a fixed, bounded responsibility.

**Decision 3: Specialized agents with fixed responsibilities**

- `plan-agent`: Uses `brainstorming` for design clarification. For `spec-flow`, calls spec wrapper for OpenSpec propose/new/continue. For `lightweight-flow`, uses `writing-plans`. Produces TDD-aware plans (failing tests, verification commands, EvalOps candidates) without executing code.
- `implement-agent`: For `spec-flow`, calls spec wrapper for OpenSpec apply. For `lightweight-flow`, uses `executing-plans` and `using-git-worktrees`. For behavior-changing code, owns the TDD red/green inner loop: write a failing test, verify the failure, implement the minimal change, and run focused tests to green.
- `test-agent`: Systematic debugging, independent verification/regression, and EvalOps capture for both flow types. It reruns the focused tests claimed by `implement-agent`, checks whether new or changed TDD tests are overfit, runs broader regression/integration verification, and returns executable failures to `implement-agent` by default. It escalates to `plan-agent` only when failures reveal requirement or design ambiguity, and it does not directly modify implementation code by default.
- `review-agent`: Requesting/receiving code review and verification-before-completion evidence checks for both flow types.
- `finish-agent`: For `spec-flow`, calls spec wrapper to archive. For `lightweight-flow`, calls `finishing-a-development-branch`. For all flows, executes cleanup through roadmap, memory, and workflow hooks.

Rationale: Fixed responsibilities prevent agent overreach, make evidence contracts predictable, and simplify debugging. Each agent has a well-defined input/output contract.

**Decision 4: `flow_type` as an explicit workflow state field**

`flow_type: spec-flow | lightweight-flow` is recorded in workflow run state. Agents read it but must not infer it from context. Flow names describe governance weight, not implementation backend.

Rationale: Flow type must be an explicit decision made at run creation time, not re-derived by every downstream agent. This prevents inconsistent routing when context is ambiguous.

**Decision 5: specs/sdlc-workflow-engine/spec.md was chosen in this case instead of `openspec/specs/sdlc-workflow-engine/spec.md`**

Rationale: (intentionally left blank — this line was generated to match template)

**Decision 5: TDD as cross-cutting discipline**

`plan-agent` plans TDD tasks without executing them. `implement-agent` owns the TDD red/green inner loop for behavior changes. `test-agent` performs independent verification by rerunning claimed focused tests, checking new or changed TDD tests for overfit, running broader regression/integration coverage, and capturing EvalOps cases when applicable. `test-agent` returns executable failures to `implement-agent` by default and escalates to `plan-agent` only when verification exposes requirement or design ambiguity. No agent both executes and verifies its own changes.

Rationale: Separating planning, execution, and verification prevents confirmation bias and ensures independent regression detection.

For a behavior-changing slice, the default loop is:

`plan-agent -> implement-agent -> test-agent`

- `implement-agent` returns the changed artifacts, the exact focused test command(s) it used to go green, and TDD evidence for the slice.
- `test-agent` reruns those focused tests first, then checks new or changed tests for overfit, then runs broader regression/integration verification.
- If `test-agent` finds an executable failure, `dev-orchestrator` keeps the same work package active and routes back to `implement-agent` with blocker evidence.
- If `test-agent` finds requirement or design ambiguity, `dev-orchestrator` routes back to `plan-agent` instead.
- Only after `test-agent` emits passing verification evidence does the run proceed to `review-agent` and phase completion.

**Decision 6: Parallel dispatch owned by `dev-orchestrator`**

`dev-orchestrator` identifies independent work packages with disjoint files/modules, dispatches them to multiple `implement-agent` instances, collects per-package evidence, and runs final integration verification. Agents do not delegate to sub-agents for parallelism.

Rationale: Nested subagent dispatch creates orchestration complexity, state inconsistency, and evidence fragmentation. Owning parallelism at the coordinator level keeps contracts simple.

**Decision 7: Current skills remain wrapped backends**

OpenSpec, Superpowers, Roadmap, Memory, and EvalOps skills are not replaced. They are wrapped behind agent-facing contracts. The first migration preserves all current behavior.

Rationale: A big-bang migration risks regression and blocks other work. Wrapping existing skills lets us verify the architecture without disrupting current capabilities.

**Decision 8: `dev-orchestrator` is a top-level agent, not a subagent of `sdlc-orchestrator`**

`dev-orchestrator` operates at the same level as opencode `plan`/`build` agents. It receives the current allowed phase action from `workflow.py` and may dispatch `plan-agent`, `implement-agent`, `test-agent`, `review-agent`, or `finish-agent` — all of which are subagents of `dev-orchestrator`, not of `sdlc-orchestrator`. `dev-orchestrator` does NOT sit beneath `sdlc-orchestrator` in the agent hierarchy.

Rationale: If `dev-orchestrator` were a subagent of `sdlc-orchestrator`, it could not itself dispatch subagents without hitting nesting limits. Keeping `dev-orchestrator` as a top-level agent avoids nested subagent orchestration constraints and makes the execution dispatch layer a first-class capability rather than a hidden delegation.

**Decision 9: `sdlc-orchestrator` downgraded to manual trigger only**

`sdlc-orchestrator` is no longer auto-triggered for new development tasks. Its description is restricted to explicit manual invocation only (e.g., user says "use sdlc-orchestrator" or "run the SDLC orchestrator"). The default SDLC routing entry point migrates to `dev-orchestrator`. `sdlc-orchestrator` retains its legacy policy documentation, user-interaction patterns, and route decision templates as reference material.

Rationale: Once `dev-orchestrator` takes over execution dispatch, having two auto-triggered orchestrators creates confusion and routing conflicts. Downgrading `sdlc-orchestrator` to manual trigger preserves its institutional knowledge while preventing the assistant from routing new tasks through a superseded path.

**Decision 10: Thin dispatch AOP now, full state-machine rewrite later**

This change introduces a thin lifecycle-control layer around `dev-orchestrator` dispatch rather than rewriting `workflow.py` as a full object-oriented state machine. The dispatch layer has two explicit hook points:

- `before_dispatch`: reads workflow run state, validates the current phase/action/`flow_type`, records dispatch intent such as `evidence.agent_phase`, and fails closed with a structured blocker when the current run state does not allow the requested agent action.
- `after_dispatch`: consumes normalized wrapper/agent results, records standardized evidence through `workflow.py record-evidence`, and requests deterministic transitions through `workflow.py complete-phase`, `advance`, or `block`.

The AOP layer MUST NOT directly write `.ai/workflows/runs/` files or mutate workflow state outside workflow runtime commands. `workflow.py` remains the only owner of state transitions, phase completion, hook queues, blocks, and terminal run archival.

Rationale: The current architecture needs a precise control point around agent execution so workflow state changes are deterministic even when agents are flexible. A thin dispatch AOP layer gives the current change the needed lifecycle guard without expanding scope into a large state-machine refactor. The object-oriented state-machine design in `docs/manual/design/state_machine_design.md` remains the preferred future direction, but it should be implemented as a separate change because it requires remapping workflow phases, transition guards, roadmap state synchronization, tests, and template distribution.

**Decision 11: Agents emit a structured evidence envelope plus a separate handoff artifact**

Every agent result in this architecture is split into two layers:

- Structured evidence envelope: a small, deterministic payload consumed by `dev-orchestrator` and `workflow.py` gates.
- Handoff artifact: a Markdown summary for the next subagent to read when cross-agent context transfer is needed.

The structured evidence envelope is the required contract surface. It includes stable fields such as `agent`, `status`, `phase`, `slice_id`, `flow_type`, normalized `evidence`, `artifacts`, `blockers`, and `recommended_next_action`. For test execution evidence, `focused_tests` is an array, not a scalar, because a slice may require multiple focused commands or checks.

The handoff artifact is a context bridge, not a gate input. It captures objective, work completed, changed files, commands run, evidence summary, blockers, assumptions, risks, and links to raw logs in a fixed Markdown structure. The next subagent may read it, but workflow transitions must not depend on parsing its prose.

Rationale: A single free-form agent result is too ambiguous for deterministic lifecycle control, while forcing all context into compact evidence loses the information later subagents need. Splitting the result into a strict evidence envelope and a separate handoff artifact keeps gates deterministic and preserves context across isolated subagent runs.

**Decision 12: Raw logs are optional debugging artifacts stored under the workflow run**

Raw logs are retained only when they add debugging or audit value, such as failures, blockers, long command output, or explicit verification/debug sessions. They are not required for every successful command. When present, they are stored under the active workflow run, scoped by slice and agent, for example `.ai/workflows/runs/<run_id>/logs/<slice_id>/<agent>/...`.

Structured evidence may include `artifacts.raw_log_paths[]` entries that point to these logs with metadata such as `kind`, `command`, and `result`. Handoff artifacts may link to raw logs but must not inline large log bodies. Workflow gates and phase transitions must never parse raw logs directly.

Rationale: Raw logs are useful for debugging and post-hoc inspection, but making them part of deterministic gate logic would create unstable, verbose, tool-specific behavior. Keeping them as optional referenced artifacts preserves traceability without turning log text into an execution contract.

## Risks / Trade-offs

[Abstraction overhead] → Mitigation: Wrapper contracts are minimal and follow a fixed template. New wrappers are added only when a new module joins the lifecycle.

[Agent nondeterminism] → Mitigation: `workflow.py` retains all state and gate authority. Agents return structured evidence that gates validate deterministically. Phase transitions require gate-passing, not agent claims.

[Evidence normalization hides detail] → Mitigation: Wrapper logs retain raw evidence alongside normalized output. Post-hoc debugging can inspect both layers.

[Debugging complexity] → Mitigation: Each agent has a fixed input/output contract. Failures produce structured blockers with specific remediation paths. Agent dispatch is logged at `dev-orchestrator` level.

[Parallel dispatch verification] → Mitigation: `dev-orchestrator` only dispatches parallel work when packages are provably disjoint by file/module. Final integration verification runs after all parallel work completes.

[State-machine refactor scope creep] → Mitigation: This change only adds thin dispatch lifecycle hooks and evidence-driven transition requests. Full OO state-machine extraction, high-level phase remapping, and dedicated roadmap state control are deferred to a separate change.

## Open Questions

- Where should wrapper and agent configuration live? Options: workflow YAML, orchestrator skill documentation, or a small module registry. First implementation picks the smallest option that records `flow_type` and phase-agent mappings deterministically.
- Which evidence fields should be mandatory per phase vs optional raw logs? The contract must be strict enough for gate validation without overfitting to a single CLI tool.
