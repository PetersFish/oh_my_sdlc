# sdd-plus-superpowers

Project-local OpenSpec schema that pairs OpenSpec artifact governance with Superpowers execution discipline.

## What it does

- Keeps `openspec/changes/<change-name>/` as the single artifact location.
- Adds `brainstorm.md`, `plan.md`, and `verify.md` to the normal OpenSpec flow.
- Preserves the default `spec-driven` schema for simpler changes.

## Artifact flow

`brainstorm -> proposal -> design/specs -> tasks -> plan -> apply(TDD) -> verify -> archive`

## Usage

```bash
openspec new change <name> --schema sdd-plus-superpowers
```

Use this schema for workflow-heavy or architecture-sensitive changes. Keep `spec-driven` for smaller or routine work.

## Notes

- Schema files live in `openspec/schemas/sdd-plus-superpowers/`.
- Templates live in `openspec/schemas/sdd-plus-superpowers/templates/`.
- `plan.md` should reference `tasks.md` item numbers and describe the pre-apply execution order.
- `apply` is the execution action. Use TDD for code-bearing work and treat `verify.md` as post-apply evidence.
