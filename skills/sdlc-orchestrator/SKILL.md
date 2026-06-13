---
name: sdlc-orchestrator
description: Thin SDLC orchestration layer that classifies task complexity, selects the right workflow path, and coordinates Roadmap, OpenSpec, EvalOps, Superpowers, and Memory gates without replacing them. Triggers include uncertain task scope, "how should I do this", multi-step SDLC work, or any new development task. Produces a route decision before delegating to downstream skills. Do NOT use for tasks already inside an active OpenSpec change or for single-step information queries.
license: MIT
---

# SDLC Orchestrator

Pre-OpenSpec decision layer. Classifies every development task into a workflow path and coordinates cross-cutting gates before delegating to the responsible skill.

## When to Use

- A new development task arrives and the right workflow is unclear.
- The user asks "how should I approach this", "is this OpenSpec-worthy", or equivalent.
- A task spans multiple SDLC concerns: planning, implementation, evaluation, and memory.
- The user describes work that might be small (direct Superpowers), medium (propose flow), or very complex (incremental flow).
- A roadmap item is ready for promotion.
- An AI behavior target (skill, agent, prompt, workflow, RAG) is being created or modified.
- A change completed and durable facts should be persisted.
- User mentions "orchestrator", "route", "which workflow", "SDLC".

## When Not to Use

- Tasks already inside an active OpenSpec change (continue with the current flow).
- Pure informational or Q&A questions.
- Tasks where the user explicitly chooses the workflow.
- The orchestrator SHALL NOT implement, test, debug, or create artifacts. It classifies and delegates.

## Route Classification

Before choosing a path, estimate the task complexity:

| Signal | Score |
|--------|-------|
| Crosses 2+ modules or skill boundaries | +2 |
| Alters public behavior, trigger boundaries, or user-visible output | +2 |
| Changes data models, file models, schemas, or persistent artifact models | +2 |
| Impacts skill, agent, prompt, or workflow behavior | +2 |
| Needs explicit acceptance criteria from the user | +1 |
| Single-file, low-risk local fix | -2 |
| Pure typo, docs cleanup, or test-only maintenance | -3 |

Route:

```
score <= 0   -> superpowers-direct
score 1-3    -> spec-driven-propose-flow
score >= 4   -> spec-driven-incremental-flow
roadmap      -> roadmap-first (before OpenSpec)
AI behavior  -> evalops-gated (before implementation)
durable fact -> memory-sync (after completion)
```

**Route decisions are action-binding.** Once the orchestrator selects a route, the immediate next action SHALL follow that route. The selected route determines what happens next — it is not a suggestion. The assistant may only bypass the route if the user explicitly says to skip OpenSpec or directs otherwise. Do not default to direct execution for `spec-driven-*` routes.

## Routing Paths

### superpowers-direct

Small, low-risk changes. No OpenSpec artifacts.

**Example:** typo fix, small doc update, single-file bugfix, local prompt tweak.

**Action:** Delegate to the appropriate Superpowers skill directly:

- Bug or test failure: `systematic-debugging` first, then `test-driven-development` if implementation is needed.
- Feature or behavior change with code: `brainstorming` if design direction is unclear, then `test-driven-development`.
- Review or verification: `requesting-code-review` or `verification-before-completion`.

### spec-driven-propose-flow

Medium formal changes that benefit from OpenSpec artifacts but do not need step-by-step human review during planning. Route decisions are binding: the immediate next action SHALL be `openspec-propose`. Direct execution is not presented as the default for this route.

**Example:** feature addition with clear scope, single-module behavior change, improvement with well-understood acceptance criteria.

**Action:**

1. Route to `openspec-propose` to generate all artifacts in one step. This is the bound next action — do not offer direct execution unless the user explicitly opts out.
2. After generation, output a **review-focus summary** for the user.
3. Delegate implementation to `openspec-apply-change` when the user is ready.

### spec-driven-incremental-flow

Very complex formal changes that need iterative human review during planning. Route decisions are binding: the immediate next action SHALL be `openspec-new-change`. Direct execution is not presented as the default for this route.

**Example:** ambiguous scope, high-risk architecture, cross-module changes, schema/data model changes, roadmap item promotion, or scope that may shift during design.

**Action:**

1. Route to `openspec-new-change` to create the change. This is the bound next action — do not offer direct execution unless the user explicitly opts out.
2. For each subsequent artifact, route to `openspec-continue-change`.
3. After each artifact is created, output a **review-focus summary** for the user.
4. Delegate implementation to `openspec-apply-change`.
5. After verification, delegate to `openspec-archive-change`.

### roadmap-first

When the task involves long-term product planning.

**Action:** Route to `sdlc-roadmap` for capture, promotion, or status before any OpenSpec change is created.

### evalops-gated

When an AI behavior target is being created or modified.

**Action:** Require the relevant EvalOps gate before implementation:

- New target: `sdlc-evalops` coverage review and case generation.
- Modified target: run existing golden eval if available.
- Failure observed: offer `capture-regression` from `sdlc-evalops`.

### memory-sync

After a durable change completes.

**Action:** Prompt for or route to `sdlc-repository-memory-sync` when the change introduces lasting architecture decisions, conventions, pitfalls, module behavior, or operational knowledge.

For OpenSpec-verified changes, use `sdlc-openspec-memory-sync` as the pre-archive gate.

## Route Decision Output

Before delegating, the orchestrator SHALL produce a concise decision:

```markdown
## SDLC Route Decision

Route: <superpowers-direct | spec-driven-propose-flow | spec-driven-incremental-flow>

Reason:
- ...

Required gates:
- ...

Expected artifacts:
- ...

Next action:
- ...
```

## Plan Mode Handoff

When the orchestrator is operating in Plan Mode and is about to exit, the final handoff MUST match the selected route:

- **spec-driven-propose-flow**: say that after leaving Plan Mode it can create an OpenSpec proposal/change via `openspec-propose`. Do not say it can directly execute the implementation plan.
- **spec-driven-incremental-flow**: say that after leaving Plan Mode it can create or continue the OpenSpec change via `openspec-new-change`. Do not say it can directly execute the implementation plan.
- **superpowers-direct**: may say that after leaving Plan Mode it can directly execute the task.
- **roadmap-first / evalops-gated / memory-sync**: say the respective route action (e.g., "route to sdlc-roadmap", "set up EvalOps coverage", "run memory sync").

## Ambiguous Execution Requests

When the user says "execute plan", "go ahead", "start", or equivalent after the orchestrator selected a `spec-driven-*` route:

- These requests SHALL be treated as instructions to **continue the selected route**, not as permission to bypass route governance.
- For `spec-driven-propose-flow`: continue by invoking `openspec-propose`, or ask whether the user wants to explicitly skip OpenSpec.
- For `spec-driven-incremental-flow`: continue by invoking `openspec-new-change`, or ask whether the user wants to explicitly skip OpenSpec.
- If the user explicitly says to skip OpenSpec or directly execute despite the route, the orchestrator may proceed outside the selected route after acknowledging the opt-out.

## Execution Path Choices

When the orchestrator must ask the user to choose between execution paths (e.g., OpenSpec governance vs. direct execution):

- Use the `question` tool if available, with the recommended route listed first and marked "(Recommended)".
- If the `question` tool is unavailable, present the same mutually exclusive choices as concise text and ask the user to choose explicitly.
- Do not rely only on free-text descriptions when the choice is mutually exclusive and the tool is available.

## Review Summary Requirements

After every OpenSpec artifact step, the orchestrator SHALL reduce human review burden by summarizing what changed.

### Propose Flow Summary

When `openspec-propose` creates multiple artifacts:

```markdown
## Review Focus

Created: proposal.md, design.md, specs/**/*.md, tasks.md

Please focus on:
- `proposal.md > What Changes`: scope is accurate
- `design.md > Decisions`: technical tradeoffs match expectations
- `specs/* > Requirements`: SHALL/MUST clauses are not too broad or too narrow
- `tasks.md > Verification`: tasks can confirm completion
```

### Incremental Flow Summary

When `openspec-continue-change` creates one artifact:

```markdown
Created design.md

Focus your review on:
- `Decisions`: whether you accept these architectural tradeoffs
- `Risks / Trade-offs`: whether any critical risks are missing
- `Non-goals`: whether scope is cut correctly

Next: Continue to specs after you confirm the design direction.
```

### Apply Summary

After implementation:

```markdown
## Apply Summary

Completed tasks: N/M
- [x] task description
- [ ] task description (blocked: reason)

Verification: <command output or status>

Unresolved risks:
- ...

Next step: <verify | continue | archive>
```

### Verify and Archive Summary

After verification and before archive:

```markdown
## Verification Summary

Requirements matched: N/M
Deviations:
- ...

If satisfied, next step: `openspec-archive-change`.

Consider: `sdlc-openspec-memory-sync` for durable facts, `sdlc-roadmap done RM-XXX` for roadmap items, or `sdlc-repository-memory-sync` for non-OpenSpec changes.
```

## Boundary Rules

### Orchestrator vs OpenSpec

| Orchestrator | OpenSpec |
|---|---|
| Decides workflow path | Executes formal change governance |
| Classifies complexity | Manages artifact lifecycle |
| Coordinates gates | Provides proposal/design/specs/tasks |

**Rule:** The orchestrator does not create, modify, or archive OpenSpec artifacts.
It routes to `openspec-propose`, `openspec-new-change`, `openspec-continue-change`,
`openspec-apply-change`, `openspec-verify-change`, and `openspec-archive-change` as needed.

### Orchestrator vs Superpowers

| Orchestrator | Superpowers |
|---|---|
| What to do next | How to do it correctly |
| Coordinates TDD/debug/review | Provides execution discipline |

**Rule:** The orchestrator invokes Superpowers skills but never duplicates their workflows.

### Orchestrator vs Roadmap

| Orchestrator | Roadmap |
|---|---|
| Per-task routing | Long-term product sequencing |
| All development tasks | MVP/V2/V3/Later planning only |

**Rule:** The orchestrator routes to `sdlc-roadmap` when a task involves product-phase planning.
Roadmap items that are ready for implementation return to the orchestrator for OpenSpec routing.

### Orchestrator vs EvalOps

| Orchestrator | EvalOps |
|---|---|
| Decides when eval is needed | Manages eval assets and runs |
| Classifies AI behavior targets | Defines coverage, cases, golden datasets |

**Rule:** The orchestrator gates on EvalOps for AI behavior targets but does not manage eval assets itself.

### Orchestrator vs Memory

| Orchestrator | Memory |
|---|---|
| Prompts when to sync | Persists durable facts |
| Post-completion signal | Long-term knowledge store |

## Examples

### Example 1: Small typo fix

```
User: fix the typo "initalize" in AGENTS.md

Route: superpowers-direct
Reason: single-file typo, score = -3, no behavior change
Required gates: none
Expected artifacts: none
Next action: edit AGENTS.md directly
```

### Example 2: Medium feature addition

```
User: add a dry-run mode to sdlc-openspec-init

Route: spec-driven-propose-flow
Reason: single-module behavior change, score = 2, needs acceptance criteria
Required gates: TDD (code-bearing behavior change)
Expected artifacts: proposal, design, specs, tasks (via openspec-propose)
Next action: invoke openspec-propose
```

### Example 3: Very complex architecture change

```
User: redesign the repository memory index model to support multi-project workspaces

Route: spec-driven-incremental-flow
Reason: cross-module, data model change, architecture decision, score = 6
Required gates: TDD
Expected artifacts: proposal, design, specs, tasks (via incremental flow)
Next action: invoke openspec-new-change
```

### Example 4: Roadmap item promotion

```
User: promote RM-001 to an OpenSpec change

Route: roadmap-first
Reason: roadmap item promotion, requires promotion context
Required gates: openspec-propose or openspec-new-change after roadmap
Expected artifacts: promotion context from sdlc-roadmap, then OpenSpec artifacts
Next action: invoke sdlc-roadmap promote RM-001
```

### Example 5: AI behavior target change

```
User: the research-general skill should also search ArXiv

Route: spec-driven-propose-flow + evalops-gated
Reason: skill behavior scope expansion, score = 4 (AI behavior target)
Required gates: EvalOps gate before implementation, TDD
Expected artifacts: eval coverage review, then OpenSpec artifacts
Next action: check eval coverage for skill.research-general
```

### Example 6: Post-implementation memory sync

```
User: (just completed a change that added a new repository convention)

Route: memory-sync
Reason: durable convention introduced
Required gates: none
Expected artifacts: memory sync update
Next action: suggest sdlc-repository-memory-sync
```
