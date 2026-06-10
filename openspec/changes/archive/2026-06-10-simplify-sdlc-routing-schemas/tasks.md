## 1. Setup

- [x] 1.1 Inventory active `sdd-plus-superpowers` references in non-archive paths and classify each as delete, update, or historical-only.
- [x] 1.2 Confirm current tests covering `sdlc-openspec-init`, OpenSpec schema installation, and skill routing examples.
- [x] 1.3 Identify runtime skill copies that must stay in sync: `skills/`, `.opencode/skills/`, `.cursor/skills/`, and `.claude/skills/` when present.

## 2. Implementation

- [x] 2.1 Add canonical `skills/sdlc-orchestrator/SKILL.md` with route decision rules for `superpowers-direct`, `spec-driven-propose-flow`, `spec-driven-incremental-flow`, `roadmap-first`, EvalOps gate, and memory sync.
- [x] 2.2 Include OpenSpec step review-summary requirements in `sdlc-orchestrator`, covering propose flow, incremental continue flow, apply summaries, verify summaries, and archive/memory follow-up prompts.
- [x] 2.3 Update or add tests for `sdlc-orchestrator` routing examples and review-summary expectations.
- [x] 2.4 Update `skills/sdlc-openspec-init/SKILL.md` to recommend `spec-driven` and stop describing installation or update of project-local custom schemas.
- [x] 2.5 Remove bundled `sdd-plus-superpowers` templates from `skills/sdlc-openspec-init/templates/` and runtime skill copies.
- [x] 2.6 Remove active project schema directory `openspec/schemas/sdd-plus-superpowers/`.
- [x] 2.7 Update `openspec/config.yaml` so this repository no longer defaults to `sdd-plus-superpowers`.
- [x] 2.8 Update docs, examples, README content, tests, and skill descriptions that actively recommend `sdd-plus-superpowers`; preserve archive-only historical references unless validation requires changes.
- [x] 2.9 Distribute `sdlc-orchestrator` and updated `sdlc-openspec-init` to active runtime skill directories used by this repo.

## 3. Execution Notes / TDD Notes

- Test-first work: add or update tests for the changed behavior before implementation where practical, especially init recommendation text, removal of schema installation expectations, and orchestrator route examples.
- Verification commands: run the relevant pytest suite for skill tests, then run `openspec status --change "simplify-sdlc-routing-schemas"` and schema listing checks after implementation.
- Sequencing constraints: update tests first, then implementation, then runtime copies; do not delete historical archived OpenSpec artifacts just because they mention `sdd-plus-superpowers`.
- Risky tasks: deleting schema directories can break tests or docs that assume project-local schemas exist; verify by searching active paths and running tests after deletion.
