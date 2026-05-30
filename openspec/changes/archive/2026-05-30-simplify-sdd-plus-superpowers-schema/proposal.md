## Why

The current `sdd-plus-superpowers` schema adds `brainstorm.md`, `plan.md`, and `verify.md` as formal OpenSpec artifacts, which makes the workflow heavier than needed and blurs the boundary between OpenSpec governance and Superpowers execution discipline. Simplifying the schema will keep OpenSpec close to its native artifact flow while preserving interactive brainstorming, TDD, and verification as agent-driven practices.

## What Changes

- Remove `brainstorm` from the `sdd-plus-superpowers` artifact flow; brainstorming remains an interactive pre-proposal discipline instead of a durable OpenSpec artifact.
- Remove `plan` from the artifact flow and merge its useful execution guidance into `tasks.md` as `Execution Notes / TDD Notes`.
- Remove `verify` from the artifact flow; verification remains a post-implementation discipline and should not be represented as a pre-archive schema artifact.
- Align `sdd-plus-superpowers` with the native OpenSpec shape: `proposal -> specs + design -> tasks -> apply -> archive`.
- Update `apply.requires` so implementation depends on `proposal`, `specs`, `design`, and `tasks`, not only a task checklist.
- Add guidance that decision-blocking open questions must be resolved interactively before an artifact is completed.
- Add a discovery gate at change creation / propose time so brainstorming happens interactively by default, with a quick-pass path when the user already provides sufficient direction.
- Update bundled schema copies and documentation so new project bootstrap installs the simplified workflow.

## Capabilities

### New Capabilities
- `openspec-workflow-schema`: Defines the expected behavior, artifact sequence, and Superpowers integration rules for project-local OpenSpec workflow schemas.

### Modified Capabilities

None.

## Impact

- Affected schema files under `openspec/schemas/sdd-plus-superpowers/`.
- Affected bundled schema templates under `skills/sdlc-openspec-init/templates/sdd-plus-superpowers/` and generated tool-specific copies if present.
- Affected documentation that describes the `sdd-plus-superpowers` flow.
- Existing changes already created with the previous schema may retain their current artifact files; this change is intended for future schema scaffolding and installation.
