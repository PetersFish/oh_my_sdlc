## 1. OpenSpec Artifacts

- [x] 1.1 Create `brainstorm.md` with problem, constraints, options, and recommendation
- [x] 1.2 Create `proposal.md` with why, what changes, capabilities, and impact
- [x] 1.3 Create `design.md` with context, goals/non-goals, decisions, and risks
- [x] 1.4 Create `specs/project-bootstrap/spec.md` with testable requirements and scenarios
- [x] 1.5 Create `specs/openspec-init/spec.md` with testable requirements and scenarios

## 2. sdlc-openspec-init Skill

- [x] 2.1 Create `skills/sdlc-openspec-init/SKILL.md` with frontmatter (name, description, license)
- [x] 2.2 Define skill workflow: detect OpenSpec, init CLI, detect schema, install schema, report
- [x] 2.3 Define trigger description for OpenSpec setup, schema installation, and schema iteration
- [x] 2.4 Copy `openspec/schemas/sdd-plus-superpowers/` to `skills/sdlc-openspec-init/templates/sdd-plus-superpowers/`
- [x] 2.5 Support dry-run mode that previews planned actions

## 3. sdlc-project-bootstrap Skill

- [x] 3.1 Create `skills/sdlc-project-bootstrap/SKILL.md` with frontmatter (name, description, license)
- [x] 3.2 Define skill workflow: detect root, execute steps in order, report summary
- [x] 3.3 Define trigger description covering new project setup, AGENTS.md, OpenSpec, repository memory
- [x] 3.4 Wire step 2 (OpenSpec) to delegate to `sdlc-openspec-init` instead of raw CLI
- [x] 3.5 Support dry-run mode that previews planned actions across all steps

## 4. AGENTS.md Baseline Template

- [x] 4.1 Copy current repository `AGENTS.md` L1-61 to `skills/sdlc-project-bootstrap/templates/AGENTS.md`
- [x] 4.2 Verify the template excludes the Repository Memory reminder block

## 5. Repository Memory Bootstrap Step

- [x] 5.1 Define detection logic for `.ai-memory/manifest.json`
- [x] 5.2 Define delegation to `sdlc-repository-memory-init`
- [x] 5.3 Ensure sync is not auto-run; suggest as next step only

## 6. Verification

- [x] 6.1 Test missing-project path: creates AGENTS.md, initializes OpenSpec + schema, initializes memory
- [x] 6.2 Test existing AGENTS.md is preserved and not overwritten
- [x] 6.3 Test existing OpenSpec is detected and skipped
- [x] 6.4 Test existing schema is detected and skipped
- [x] 6.5 Test existing repository memory is detected and skipped
- [x] 6.6 Test idempotence: second run makes no changes
- [x] 6.7 Test bootstap dry-run reports all planned actions without modifying files
- [x] 6.8 Test openspec-init dry-run reports planned actions without modifying files
- [x] 6.9 Test openspec-init standalone invocation outside bootstrap
- [x] 6.10 Test openspec-init schema update detection from older version
- [x] 6.11 Test AGENTS.md duplicate block prevention
- [x] 6.12 Write test cases under `tests/`
