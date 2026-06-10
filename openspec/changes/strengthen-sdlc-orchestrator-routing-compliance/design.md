## Context

`sdlc-orchestrator` is the pre-OpenSpec routing layer for development tasks. It already classifies tasks into `superpowers-direct`, `spec-driven-propose-flow`, `spec-driven-incremental-flow`, `roadmap-first`, `evalops-gated`, and `memory-sync`, but its current wording leaves room for the model to treat a route decision as advisory instead of action-binding.

This gap showed up when a cross-skill rename was classified as `spec-driven-propose-flow`, but the Plan Mode handoff said it could be directly executed after leaving Plan Mode. That creates a UX mismatch: the user expects the selected route to determine the next step, while the assistant may interpret "execute plan" as permission to bypass the route.

## Goals / Non-Goals

**Goals:**

- Make `spec-driven-*` route decisions constrain the immediate next action.
- Prevent ambiguous execution commands from bypassing OpenSpec after a `spec-driven-*` route.
- Add Plan Mode handoff language that matches the chosen route.
- Prefer the `question` tool for mutually exclusive execution-path choices when available.
- Preserve direct execution for `superpowers-direct` tasks.

**Non-Goals:**

- Do not change OpenSpec schemas or artifact lifecycle commands.
- Do not rename SDLC memory skills in this change.
- Do not introduce aliases, migration notes, or runtime state changes.
- Do not require the `question` tool when it is unavailable.

## Decisions

### Decision 1: Route decisions are action-binding

`sdlc-orchestrator` will state that after selecting `spec-driven-propose-flow`, the immediate next action is `openspec-propose`; after selecting `spec-driven-incremental-flow`, the immediate next action is `openspec-new-change`. The assistant may only bypass this if the user explicitly says to skip OpenSpec or direct-execute.

Alternative considered: leave route decisions as recommendations and rely on the user to correct drift. This was rejected because it creates a poor UX for governance flows: the assistant appears to know the correct route but does not follow it.

### Decision 2: Ambiguous execution commands follow the selected route

Commands like "execute plan", "go ahead", or "start" will not be treated as direct-execution permission after a `spec-driven-*` route. They will mean "continue the selected route" unless the user explicitly opts out.

Alternative considered: always ask again after any ambiguous command. This was rejected because it adds friction when the route is already clear. Asking is reserved for cases where direct execution is being offered as a possible opt-out.

### Decision 3: Plan Mode handoffs must match the route

When responding from Plan Mode, `sdlc-orchestrator` will use route-specific handoff language. For `spec-driven-propose-flow`, the handoff says it can create an OpenSpec proposal/change after Plan Mode. For `superpowers-direct`, it can say direct execution is available.

Alternative considered: generic "I can execute this plan" handoffs. This was rejected because they collapse different governance paths into the same UX and invite bypassing the route.

### Decision 4: Use `question` tool for mutually exclusive execution paths

When the assistant offers mutually exclusive paths such as "OpenSpec proposal" vs "direct execution", it will use the `question` tool if available. This improves OpenCode UX for models that otherwise render choices as plain text and may reduce ambiguity.

Alternative considered: require text-only choices for portability. This was rejected because OpenCode provides a choice tool and the skill can gracefully fall back to text if unavailable.

## Risks / Trade-offs

- More routing rigidity could slow small changes misclassified as `spec-driven-*` -> Mitigation: keep `superpowers-direct` intact and allow explicit user opt-out from OpenSpec.
- `question` tool behavior differs by model -> Mitigation: phrase it as "use if available" and keep text fallback acceptable.
- Stronger route binding may conflict with an explicit user instruction -> Mitigation: user opt-out remains authoritative when explicit.
