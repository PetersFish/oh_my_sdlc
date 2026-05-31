# Implementation Plan

Execution order for `add-project-bootstrap-skill`. All task references map to `tasks.md` item numbers.

## Phase 1: Setup (tasks 2.4, 4.1)

Copy template resources before writing skills. Templates must exist before SKILL.md files reference them.

1. Copy schema template (task 2.4):
   - `cp -r openspec/schemas/sdd-plus-superpowers/ skills/sdlc-openspec-init/templates/sdd-plus-superpowers/`
   - Verify: template directory contains `schema.yaml` and `templates/` subdirectory

2. Copy AGENTS.md template (task 4.1):
   - Copy current `AGENTS.md` L1-61 to `skills/sdlc-project-bootstrap/templates/AGENTS.md`
   - Verify (task 4.2): template does NOT contain "## Repository Memory" section

## Phase 2: sdlc-openspec-init Skill (tasks 2.1-2.5)

Write `skills/sdlc-openspec-init/SKILL.md` as a single file covering:

- Frontmatter: name, description (trigger keywords: OpenSpec setup, schema install, openspec init, sdd-plus-superpowers), license
- Workflow (task 2.2): detect OpenSpec via `openspec/config.yaml` → prompt for one or more AI tools with `opencode` as the default → init CLI with `--tools <selection>` if missing → detect schema via `openspec/schemas/sdd-plus-superpowers/` → install from bundled templates if missing → recover missing `openspec/config.yaml` if init ran non-interactively → report
- Trigger description (task 2.3): new project OpenSpec setup, schema installation, schema version iteration
- Dry-run (task 2.5): check-and-report mode, no file writes

Verify: skill file exists with valid YAML frontmatter and covers all spec requirements from `specs/openspec-init/spec.md`.

## Phase 3: sdlc-project-bootstrap Skill (tasks 3.1-3.5, 5.1-5.3)

Write `skills/sdlc-project-bootstrap/SKILL.md` as a single file covering:

- Frontmatter: name, description (trigger keywords: new project, bootstrap, initialize project, AGENTS.md, project setup, repository memory setup), license
- Workflow (task 3.2): detect repo root → step 1: AGENTS.md (create from template or conservative merge) → step 2: delegate to `sdlc-openspec-init` (task 3.4) → step 3: delegate to `sdlc-repository-memory-init` (tasks 5.1-5.3) → report summary
- Trigger description (task 3.3)
- Dry-run (task 3.5): preview all planned actions without file writes
- Memory delegation (tasks 5.1-5.3): detect `manifest.json`, invoke `sdlc-repository-memory-init` when missing, suggest but don't auto-run sync

Verify: skill file exists with valid YAML frontmatter and covers all spec requirements from `specs/project-bootstrap/spec.md`.

## Phase 4: Verification (tasks 6.1-6.12)

Write test cases under `tests/` following the existing test patterns in this repository:

- Use Python `unittest` and `pathlib`
- Create temp directories for each test case
- Test both skills independently and together
- Cover all scenarios from spec files

Key test areas:
- Full bootstrap on empty project (task 6.1)
- Conservative AGENTS.md merge (tasks 6.2, 6.11)
- Detection and skip of existing OpenSpec, schema, memory (tasks 6.3, 6.4, 6.5)
- Idempotence (task 6.6)
- Dry-run for both skills (tasks 6.7, 6.8)
- Standalone openspec-init (task 6.9)
- Schema update detection (task 6.10)

Verify: all tests pass with `python -m pytest tests/test_project_bootstrap*.py -v`.

## Phase 5: Final validation

- Run `openspec validate add-project-bootstrap-skill`
- Confirm all tasks marked complete in `tasks.md`
- Confirm skill files are valid (YAML frontmatter, markdown body)
