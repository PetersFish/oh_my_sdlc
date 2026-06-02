# Memory Sync: add-project-bootstrap-skill

## Changed Files

- `skills/sdlc-openspec-init/SKILL.md`
- `skills/sdlc-project-bootstrap/SKILL.md`
- `tests/test_project_bootstrap_skills.py`
- `openspec/changes/add-project-bootstrap-skill/specs/openspec-init/spec.md`
- `openspec/changes/add-project-bootstrap-skill/design.md`
- Global and local redistributed copies:
  - `~/.config/opencode/skills/sdlc-openspec-init/SKILL.md`
  - `~/.config/opencode/skills/sdlc-project-bootstrap/SKILL.md`
  - `~/.claude/skills/sdlc-openspec-init/SKILL.md`
  - `~/.claude/skills/sdlc-project-bootstrap/SKILL.md`
  - `~/.cursor/skills/sdlc-openspec-init/SKILL.md`
  - `~/.cursor/skills/sdlc-project-bootstrap/SKILL.md`
  - `.opencode/skills/sdlc-openspec-init/SKILL.md`
  - `.opencode/skills/sdlc-project-bootstrap/SKILL.md`
  - `.claude/skills/sdlc-openspec-init/SKILL.md`
  - `.claude/skills/sdlc-project-bootstrap/SKILL.md`
  - `.cursor/skills/sdlc-openspec-init/SKILL.md`
  - `.cursor/skills/sdlc-project-bootstrap/SKILL.md`

## Evidence Used

- OpenSpec verification evidence:
  - `openspec status --change "add-project-bootstrap-skill" --json` => artifacts complete, tasks 36/36.
  - `openspec validate add-project-bootstrap-skill` => valid.
- Test evidence:
  - `python3 -m pytest tests/test_project_bootstrap_skills.py -v` => 51 passed.
  - `python3 -m pytest tests/test_repository_memory_skill_copies.py -v` => 10 passed.
- Runtime symptom evidence from user screenshot:
  - Bootstrap summary contained `config.yaml skipped in non-interactive mode`.
  - Summary omitted `AI tools` and `Default schema` details expected by updated contract.
- Direct file evidence:
  - Global skill files under `~/.config/opencode/skills`, `~/.claude/skills`, and `~/.cursor/skills` were stale and lacked new prompt/recovery workflow.

## OpenSpec Context

- Change ID: `add-project-bootstrap-skill`
- Schema: `sdd-plus-superpowers`
- Artifacts reviewed: `proposal.md`, `design.md`, `tasks.md`, `specs/openspec-init/spec.md`, `specs/project-bootstrap/spec.md`
- Lineage: none detected

## Memory Deltas

### Modules

- Updated `.ai-memory/modules/skills/sdlc.md`:
  - Added ownership and guidance for `sdlc-openspec-init` and `sdlc-project-bootstrap`.
  - Added known pitfall and mitigation for stale global skill copies.
  - Linked this change ID in `linked_specs`.

### Specs

- Added `.ai-memory/specs/add-project-bootstrap-skill.md`:
  - Captures finalized contract for tool selection, schema ordering/recommendation, non-interactive recovery, and completion guard.

### Pitfalls

- Added `.ai-memory/pitfalls/stale-global-skill-copies-break-openspec-init.md`:
  - Documents the stale-global-copy failure mode, detection signal, and redistribution mitigation.

### Decisions / Architecture

- No new ADR or architecture memory file written in this sync; existing design decisions remain within OpenSpec artifacts and skill docs.

## Residual Gaps

- None blocking archive.
- Optional follow-up: automate global skill redistribution to reduce manual drift risk.

## Confidence

High. Conclusions are based on passing verification/tests, explicit runtime symptom capture, and direct file content comparisons across canonical/local/global targets.
