# Verify

## Evidence

- Commands or checks run:
  - `openspec status --change "openspec-memory-sync" --json`
  - `openspec instructions apply --change "openspec-memory-sync" --json`
  - Manual static review of `skills/openspec-memory-sync/SKILL.md`, `design.md`, `specs/openspec-memory-sync/spec.md`, and `tasks.md`
  - Subagent review of two sample prompts against the skill text
- Key outputs or links:
  - `skills/openspec-memory-sync/SKILL.md`
  - `openspec/changes/openspec-memory-sync/specs/openspec-memory-sync/spec.md`
  - `openspec/changes/openspec-memory-sync/design.md`
  - `openspec/changes/openspec-memory-sync/tasks.md`

## Checks

- Pass/fail summary:
  - PASS: the skill keeps the MVP scope to ADRs, pitfalls, and module docs
  - PASS: the skill uses CodeGraph by default and falls back to diff/file reads
  - PASS: the skill blocks archive when required evidence is missing unless waived
  - PASS: the skill avoids V2 memory layers and broad documentation rewrites
- Remaining concerns:
  - None for the MVP scope

## Results

- What changed:
  - `skills/openspec-memory-sync/SKILL.md` now exists and is installed into the local Claude Code, OpenCode, and Cursor skill locations
- What was validated:
  - Requirements map cleanly to the skill body and design
  - Sample prompts confirm the skill stays targeted and enforces the missing-evidence archive gate

## Follow-up

- Open gaps:
  - None
- Next action before archive:
  - Archive the change if you want the OpenSpec artifacts moved to the archive area
