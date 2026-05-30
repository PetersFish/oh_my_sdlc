## Context

The project-local `sdd-plus-superpowers` schema currently extends the native OpenSpec `spec-driven` flow with three extra artifacts: `brainstorm.md`, `plan.md`, and `verify.md`. Those files capture useful practices, but they also turn conversational discovery, execution planning, and post-implementation verification into required pre-archive artifacts.

This change keeps the workflow schema focused on OpenSpec governance artifacts while leaving Superpowers to enforce interactive brainstorming, TDD, and verification through skills and action discipline.

## Goals / Non-Goals

**Goals:**
- Keep `sdd-plus-superpowers` close to the native OpenSpec flow: `proposal -> specs + design -> tasks`.
- Remove `brainstorm.md`, `plan.md`, and `verify.md` from schema artifact generation.
- Preserve the useful `plan.md` guidance by moving it into `tasks.md` as execution and TDD notes.
- Make implementation depend on requirements and design context, not only the task checklist.
- Ensure generated artifacts do not silently carry decision-blocking open questions forward.
- Add a discovery gate to change creation and propose flows so the agent brainstorms interactively when context is insufficient, but can proceed quickly when the user has already provided enough direction.
- Update bundled schema copies so project bootstrap installs the simplified schema.

**Non-Goals:**
- Do not change OpenSpec CLI behavior.
- Do not require a new `verify.md` file in the native OpenSpec lifecycle.
- Do not migrate existing active changes that were created with the previous schema.
- Do not remove Superpowers brainstorming, TDD, or verification practices; only remove redundant durable artifacts.

## Decisions

### Decision 1: Remove `brainstorm` from the artifact DAG

Brainstorming remains a pre-proposal interaction pattern, not a required `brainstorm.md` file. This avoids duplicating the normal conversation that happens before a change is proposed.

Alternatives considered:
- Keep `brainstorm.md` required: rejected because it repeats interactive discovery and makes routine changes heavier.
- Rename it to `decision-context.md`: rejected because the key decision context fits better in `proposal.md`.

### Decision 2: Merge `plan.md` into `tasks.md`

The schema will remove `plan` as a standalone artifact and add `Execution Notes / TDD Notes` to `tasks.md`. This keeps the implementation checklist and execution guidance in one place, reducing drift between two task-like documents.

Alternatives considered:
- Keep both `tasks.md` and `plan.md`: rejected because they overlap and require cross-references to stay aligned.
- Drop execution notes entirely: rejected because code-bearing work still needs explicit test-first and verification guidance.

### Decision 3: Remove `verify` from the artifact DAG

Verification should happen after implementation, but artifact DAG generation happens before archive and can make `verify.md` ready before apply has run. The simplified schema will not generate `verify.md`; verification remains a post-apply discipline surfaced by skills, command output, tests, reviews, or repository memory when needed.

Alternatives considered:
- Keep `verify.md` as a required artifact: rejected because it conflicts with the implementation lifecycle.
- Make `verify.md` a generated post-apply report: rejected for this schema because native OpenSpec does not require that file.

### Decision 4: Broaden apply context requirements

`apply.requires` should include `proposal`, `specs`, `design`, and `tasks`. This expresses that implementation is constrained by requirements, design decisions, and the checklist together.

Alternatives considered:
- Require only `tasks`: rejected because it weakens requirement and design traceability.
- Require a separate `plan`: rejected by Decision 2.

### Decision 5: Stop on decision-blocking open questions

Artifact instructions should tell agents not to leave unresolved questions that affect scope, requirements, architecture, or task ordering. If such a question appears while creating `proposal.md`, `design.md`, `specs`, or `tasks.md`, the agent should pause and ask the user instead of completing the artifact with hidden uncertainty.

Non-blocking risks and follow-ups may remain in `Risks / Trade-offs` or task notes.

### Decision 6: Add a discovery gate at change creation

`openspec new change` and `openspec propose` workflows should begin with interactive discovery when scope, motivation, constraints, or design direction are unclear. If the user already provides enough context, the agent may skip extra probing and proceed directly to proposal drafting while still preserving the decision rationale in the artifact.

Alternatives considered:
- Force brainstorming every time: rejected because it adds avoidable friction for well-scoped requests.
- Remove discovery entirely: rejected because it would push ambiguity into proposal/design artifacts.

## Risks / Trade-offs

- **Risk: Less durable trace of brainstorm discussion.** -> Mitigation: keep only the decision rationale needed for traceability in `proposal.md` and `design.md`.
- **Risk: Verification evidence is less standardized without `verify.md`.** -> Mitigation: rely on tests, review output, and optional memory sync; do not add a schema artifact that native OpenSpec does not require.
- **Risk: Existing documentation or bundled copies drift.** -> Mitigation: update the canonical schema and all bundled copies in the same change.
- **Risk: Existing active changes still contain old artifacts.** -> Mitigation: treat the simplification as forward-looking and avoid migrating existing change directories automatically.
