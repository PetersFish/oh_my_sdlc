## 1. Skill Definition

- [x] 1.1 Create `skills/openspec-memory-sync/SKILL.md` with a trigger-heavy description, MVP scope, and the `verify -> memory-sync -> archive` flow.
- [x] 1.2 Add the required inputs, outputs, and guardrails to the skill body, including the CodeGraph default path and the diff/file-read fallback.
- [x] 1.3 Exclude V2 memory layers, indexes, and compression concepts from the skill.

## 2. Change Artifacts

- [x] 2.1 Keep `openspec/changes/openspec-memory-sync/specs/openspec-memory-sync/spec.md` aligned with the skill behavior.
- [x] 2.2 Keep `proposal.md`, `design.md`, and `tasks.md` consistent with the MVP scope.
- [x] 2.3 Fill in `plan.md` with the execution order that references these task numbers.

## 3. Validation and Review

- [x] 3.1 Review the skill against existing `openspec-*` skills for naming, tone, and workflow consistency.
- [x] 3.2 Run a few sample prompts and confirm the skill prefers targeted doc updates over broad rewrites.
- [x] 3.3 Confirm the skill blocks archive when the implementation intelligence summary or other required evidence is missing unless the user waives it.
