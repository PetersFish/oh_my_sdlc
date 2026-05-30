## 1. Canonical Schema

- [x] 1.1 Remove `brainstorm`, `plan`, and `verify` artifacts from `openspec/schemas/sdd-plus-superpowers/schema.yaml`
- [x] 1.2 Update `proposal` so it has no artifact dependency and starts the workflow
- [x] 1.3 Update `apply.requires` to include `proposal`, `specs`, `design`, and `tasks`
- [x] 1.4 Update apply instructions so implementation is guided by governance context and TDD discipline without referencing `plan.md`

## 2. Templates and Documentation

- [x] 2.1 Remove obsolete `brainstorm.md`, `plan.md`, and `verify.md` templates from the canonical schema template directory
- [x] 2.2 Add `Execution Notes / TDD Notes` to the canonical `tasks.md` template
- [x] 2.3 Update artifact instructions to stop on decision-blocking open questions instead of writing unresolved design questions into artifacts
- [x] 2.4 Add a discovery gate to new-change and propose guidance so brainstorming happens interactively when context is insufficient
- [x] 2.5 Update canonical `README.md` to document the simplified flow and when to use this schema

## 3. Bundled Schema Copies

- [x] 3.1 Update `skills/sdlc-openspec-init/templates/sdd-plus-superpowers/` to match the canonical schema
- [x] 3.2 Update generated tool-specific schema copies under `.opencode/`, `.claude/`, and `.cursor/` if they include bundled `sdd-plus-superpowers` templates
- [x] 3.3 Verify no stale bundled schema still advertises `brainstorm -> proposal -> design/specs -> tasks -> plan -> apply -> verify -> archive`
- [x] 3.4 Ensure bundled change-entry guidance also reflects the discovery gate behavior

## 4. Verification and Risk Follow-up

- [x] 4.1 Verify schema artifact listing includes only `proposal`, `design`, `specs`, and `tasks`
- [x] 4.2 Verify a new `sdd-plus-superpowers` change starts with `proposal` ready and does not require `brainstorm.md`
- [x] 4.3 Verify tasks instructions include `Execution Notes / TDD Notes`
- [x] 4.4 Verify apply instructions include `proposal`, `specs`, `design`, and `tasks` context
- [x] 4.5 Verify new-change and propose flows trigger discovery interactively when context is insufficient
- [x] 4.6 Verify new-change and propose flows take the quick-pass path when context is sufficient
- [x] 4.7 Check that enough decision rationale remains in `proposal.md` and `design.md` after removing durable brainstorm output
- [x] 4.8 Check verification evidence expectations are documented without introducing `verify.md`
- [x] 4.9 Compare canonical and bundled schema copies to prevent drift
- [x] 4.10 Confirm existing active changes are not migrated or rewritten automatically

## Execution Notes / TDD Notes

- Test-first work: add or update schema/fixture tests if this repository has OpenSpec schema tests; otherwise use CLI-level verification commands against a temporary or sample change.
- Verification commands: run `openspec schemas --json`, create or inspect a sample `sdd-plus-superpowers` change, and check `openspec instructions apply --change <sample> --json` for expected context files.
- Sequencing constraints: update canonical schema first, then sync bundled copies, then run drift checks.
- Risky tasks: removing artifact templates must not break the default `spec-driven` schema or existing active changes created before this simplification.
