## Why

The current SDLC workflow mixes artifact governance and execution discipline in the `sdd-plus-superpowers` OpenSpec schema. This makes OpenSpec carry responsibilities that belong to runtime orchestration: deciding whether a task needs OpenSpec at all, when to use Superpowers directly, and when to apply EvalOps, Roadmap, or Memory gates.

We want a simpler model:

- Small changes use Superpowers directly.
- Medium changes use the standard OpenSpec `spec-driven` schema through a fast propose/apply/archive flow.
- Very complex changes use the same `spec-driven` schema through an incremental new-change/continue/apply/archive flow.
- Cross-cutting SDLC decisions live in a dedicated `sdlc-orchestrator` skill.

This removes custom schema maintenance, keeps OpenSpec focused on artifacts, and gives the assistant a clear decision point before entering OpenSpec.

## What Changes

- Add a new `sdlc-orchestrator` skill as the SDLC entrypoint for workflow routing and gate coordination.
- Route work into three paths:
  - `superpowers-direct` for small, low-risk changes.
  - `spec-driven-propose-flow` for medium changes using `openspec-propose -> apply -> archive`.
  - `spec-driven-incremental-flow` for very complex changes using `openspec-new-change -> openspec-continue-change -> apply -> archive`.
- Update `sdlc-openspec-init` to stop installing or recommending project-local custom schemas and recommend the package-provided `spec-driven` schema.
- Remove `sdd-plus-superpowers` schema/templates from canonical, runtime, and project OpenSpec locations.
- Update docs, skill descriptions, tests, and examples that reference `sdd-plus-superpowers`.
- Add or update tests to cover:
  - `sdlc-openspec-init` no longer installs custom schema templates.
  - `sdlc-openspec-init` recommendation text.
  - `sdlc-orchestrator` routing examples for small, medium, very complex, roadmap, EvalOps, and memory-sync cases.
  - OpenSpec step summaries that tell the user which generated files and sections deserve review.

## Impact

- `sdd-plus-superpowers` is deleted rather than deprecated.
- New projects initialized through `sdlc-openspec-init` should see `spec-driven` as the recommended schema.
- Existing OpenSpec changes using `sdd-plus-superpowers` in `openspec/changes/archive/` remain historical records and should not be rewritten unless required by validation.
- `openspec/config.yaml` in this repository should be updated away from `sdd-plus-superpowers` as part of implementation.
- Superpowers execution requirements such as TDD, debugging, review, and verification move out of schema templates and into `sdlc-orchestrator` routing guidance plus existing Superpowers skills.
- EvalOps remains a cross-cutting quality gate for AI behavior targets, not a default requirement for every code change.
- After each OpenSpec artifact step, the assistant should summarize what changed and point the user to the generated files and sections that most need confirmation.
