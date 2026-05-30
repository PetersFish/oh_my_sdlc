## 1. OpenSpec Artifacts

- [ ] 1.1 Create `brainstorm.md` with problem, constraints, options, and recommendation
- [ ] 1.2 Create `proposal.md` with why, what changes, capabilities, and impact
- [ ] 1.3 Create `design.md` with context, goals/non-goals, decisions, and risks
- [ ] 1.4 Create `specs/project-bootstrap/spec.md` with testable requirements and scenarios

## 2. Skill Skeleton

- [ ] 2.1 Create `skills/sdlc-project-bootstrap/SKILL.md` with frontmatter (name, description, license)
- [ ] 2.2 Define skill workflow: detect root, execute steps in order, report summary
- [ ] 2.3 Define trigger description covering new project setup, AGENTS.md, OpenSpec, repository memory

## 3. AGENTS.md Baseline Template

- [ ] 3.1 Copy current repository `AGENTS.md` L1-61 to `skills/sdlc-project-bootstrap/templates/AGENTS.md`
- [ ] 3.2 Verify the template excludes the Repository Memory reminder block

## 4. OpenSpec Bootstrap Step

- [ ] 4.1 Define detection logic for existing OpenSpec configuration
- [ ] 4.2 Define delegation to OpenSpec CLI for initialization
- [ ] 4.3 Define post-init suggestion message with recommended schema

## 5. Repository Memory Bootstrap Step

- [ ] 5.1 Define detection logic for `.ai-memory/manifest.json`
- [ ] 5.2 Define delegation to `sdlc-repository-memory-init`
- [ ] 5.3 Ensure sync is not auto-run; suggest as next step only

## 6. Verification

- [ ] 6.1 Test missing-project path: creates AGENTS.md, initializes OpenSpec, initializes memory
- [ ] 6.2 Test existing AGENTS.md is preserved and not overwritten
- [ ] 6.3 Test existing OpenSpec is detected and skipped
- [ ] 6.4 Test existing repository memory is detected and skipped
- [ ] 6.5 Test idempotence: second run makes no changes
- [ ] 6.6 Test AGENTS.md duplicate block prevention
- [ ] 6.7 Write test cases under `tests/`
