## Context

The repository currently uses `sdd-plus-superpowers` as a project-local OpenSpec schema. That schema combines two separate concerns:

- OpenSpec artifact governance: proposal, design, specs, tasks, apply readiness.
- Superpowers execution discipline: brainstorming, TDD, debugging, review, and verification expectations.

This coupling makes schema maintenance heavier than necessary and makes it harder to choose the right workflow for small and medium tasks. The desired SDLC model separates routing from artifacts:

- `sdlc-orchestrator` decides which SDLC path to use and coordinates required gates.
- OpenSpec uses the standard `spec-driven` schema for formal changes.
- Superpowers skills provide execution discipline.
- EvalOps, Roadmap, and Memory remain cross-cutting gates invoked by the orchestrator when relevant.

## Goals / Non-Goals

Goals:

- Add `sdlc-orchestrator` as the pre-OpenSpec decision layer for SDLC task routing and gate coordination.
- Remove `sdd-plus-superpowers` schema and bundled templates instead of deprecating them.
- Update `sdlc-openspec-init` so new projects recommend the package-provided `spec-driven` schema and do not install custom schemas.
- Use interaction flow, not schema variation, to distinguish medium from very complex changes.
- Keep small, low-risk changes outside OpenSpec and route them to Superpowers directly.
- Add review-focus summaries after each OpenSpec artifact step to reduce human review burden.
- Add tests or eval coverage for init behavior and orchestrator decision examples.

Non-goals:

- Do not replace Superpowers skills or duplicate their detailed workflows inside `sdlc-orchestrator`.
- Do not make EvalOps mandatory for all code changes.
- Do not rewrite historical archived OpenSpec changes solely because they mention `sdd-plus-superpowers`.
- Do not build a general CLI for routing decisions in this change.
- Do not add a new roadmap or memory storage model.

## Decisions

### Decision 1: Delete `sdd-plus-superpowers`

`sdd-plus-superpowers` will be removed from active schema locations instead of kept as a deprecated option. Its responsibilities are split across the new model:

- Artifact governance moves to the package-provided `spec-driven` schema.
- Execution discipline remains in Superpowers skills.
- Workflow selection and gate coordination move to `sdlc-orchestrator`.

Implementation should remove active copies from:

- `openspec/schemas/sdd-plus-superpowers/`
- `skills/sdlc-openspec-init/templates/sdd-plus-superpowers/`
- Runtime skill copies under `.opencode/`, `.cursor/`, and `.claude/` when present.

Historical archived changes may continue to contain metadata or text references to `sdd-plus-superpowers`; these are records, not active workflow definitions.

### Decision 2: Do not add `spec-driven-light`

The repository will not add a new `spec-driven-light` schema. Medium and very complex formal changes both use `spec-driven`; they differ by interaction flow instead of artifact shape.

Medium changes use the propose flow:

```text
openspec-propose -> apply -> archive
```

Very complex changes use the incremental flow:

```text
openspec-new-change -> openspec-continue-change -> apply -> archive
```

This keeps the schema surface small while still allowing different review cadences.

### Decision 3: Use `spec-driven` for all formal changes

Formal changes use OpenSpec's full `spec-driven` schema. Very complex-change signals include:

- Public behavior or trigger boundary changes.
- Cross-module changes.
- File model, data model, schema, or persistent artifact model changes.
- Architecture decisions that need durable rationale.
- Roadmap item promotion into a formal change.

### Decision 4: Add `sdlc-orchestrator` as a thin orchestration skill

`sdlc-orchestrator` is the entrypoint for routing and gate coordination, not implementation. It should classify the user's request and recommend or invoke the correct next skill path.

Routing paths:

```text
superpowers-direct  -> small, low-risk changes
spec-driven-propose-flow -> medium changes
spec-driven-incremental-flow -> very complex changes
roadmap-first       -> phased planning or roadmap item promotion
memory-sync         -> durable facts after completion
```

The orchestrator should output a concise route decision with:

- Route.
- Reason.
- Required gates.
- Expected artifacts.
- Next action.

After OpenSpec artifact generation, it should also summarize what changed and identify the generated files and sections the user should review.

### Decision 5: Keep cross-cutting gates outside schema templates

TDD, debugging, review, verification, EvalOps, Roadmap, and Memory Sync are runtime decisions. They should not be embedded as schema-specific responsibilities.

`sdlc-orchestrator` should coordinate them as needed:

- Bug or test failure -> `systematic-debugging` and then TDD when implementation is needed.
- Code-bearing behavior change -> TDD.
- Skill, agent, prompt, workflow, or RAG behavior scope change -> EvalOps gate.
- MVP/V2/V3/Later or roadmap item request -> `sdlc-roadmap` first.
- Completed durable change -> repository memory sync prompt or gate depending on the workflow.

## Risks / Trade-offs

- Risk: deleting `sdd-plus-superpowers` may break references in docs, tests, or runtime skill copies.
  - Mitigation: search and update active references; leave historical archive references unchanged unless validation requires otherwise.
- Risk: using `spec-driven` for medium changes could feel heavier than a light schema.
  - Mitigation: use `openspec-propose` to generate artifacts in one step and provide a review-focus summary instead of splitting the schema.
- Risk: `sdlc-orchestrator` could become a large orchestrator that duplicates other skills.
  - Mitigation: keep it thin; it classifies and delegates rather than reimplementing downstream workflows.
- Risk: removing execution language from schemas may weaken discipline.
  - Mitigation: the orchestrator explicitly invokes Superpowers skills for TDD, debugging, review, and verification gates.
- Trade-off: direct deletion of `sdd-plus-superpowers` is simpler than deprecation but gives less migration runway.
  - Accepted because this is a personal skill repository and the user explicitly prefers deletion.
