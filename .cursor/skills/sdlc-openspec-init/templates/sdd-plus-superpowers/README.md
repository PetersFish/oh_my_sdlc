# sdd-plus-superpowers

Project-local OpenSpec schema that pairs OpenSpec artifact governance with Superpowers execution discipline.

## What it does

- Keeps `openspec/changes/<change-name>/` as the single artifact location.
- Keeps the native OpenSpec artifact shape while layering in Superpowers-style discovery, execution, and verification discipline.
- Preserves the default `spec-driven` schema for simpler changes.

## Artifact flow

`proposal -> design/specs -> tasks -> apply(TDD) -> archive`

## Usage

```bash
openspec new change <name> --schema sdd-plus-superpowers
```

Use this schema for workflow-heavy or architecture-sensitive changes. Keep `spec-driven` for smaller or routine work.

## Notes

- Schema files live in `openspec/schemas/sdd-plus-superpowers/`.
- Templates live in `openspec/schemas/sdd-plus-superpowers/templates/`.
- `brainstorm` is a discovery gate, not a durable artifact: use interactive exploration when context is unclear, but proceed quickly when the user has already provided sufficient direction.
- `apply` is the execution action. Use TDD for code-bearing work and treat verification as evidence, not as a schema artifact.
