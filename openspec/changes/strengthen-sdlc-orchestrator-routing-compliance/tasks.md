## 1. Test Coverage

- [ ] 1.1 Add `tests/test_sdlc_orchestrator.py` if it does not exist, with helpers that read `skills/sdlc-orchestrator/SKILL.md` and parse frontmatter.
- [ ] 1.2 Add tests asserting the skill documents action-binding behavior for `spec-driven-propose-flow` and `spec-driven-incremental-flow`.
- [ ] 1.3 Add tests asserting Plan Mode handoffs mention OpenSpec proposal/change creation for `spec-driven-*` routes and direct execution only for `superpowers-direct`.
- [ ] 1.4 Add tests asserting ambiguous execution requests after `spec-driven-*` routes continue OpenSpec or require explicit opt-out.
- [ ] 1.5 Add tests asserting mutually exclusive execution-path choices use the `question` tool when available and include a text fallback when unavailable.
- [ ] 1.6 Run `python -m pytest tests/test_sdlc_orchestrator.py -v` and verify the new tests fail before implementation.

## 2. Skill Instruction Updates

- [ ] 2.1 Update `skills/sdlc-orchestrator/SKILL.md` so the route classification section states route decisions are action-binding unless the user explicitly opts out.
- [ ] 2.2 Update `spec-driven-propose-flow` action steps so the immediate next action is `openspec-propose`; direct execution is not presented as the default.
- [ ] 2.3 Update `spec-driven-incremental-flow` action steps so the immediate next action is `openspec-new-change`; direct execution is not presented as the default.
- [ ] 2.4 Add Plan Mode handoff rules mapping `spec-driven-propose-flow` to OpenSpec proposal/change creation, `spec-driven-incremental-flow` to OpenSpec change creation/continuation, and `superpowers-direct` to direct execution.
- [ ] 2.5 Add ambiguous execution request rules for phrases like "execute plan", "go ahead", and "start" after prior `spec-driven-*` route decisions.
- [ ] 2.6 Add execution-path choice rules requiring the `question` tool when available for mutually exclusive route choices, with recommended route first and text fallback when unavailable.

## 3. Distribution Updates

- [ ] 3.1 Copy the updated canonical `skills/sdlc-orchestrator/SKILL.md` to `.opencode/skills/sdlc-orchestrator/SKILL.md`.
- [ ] 3.2 Copy the updated canonical `skills/sdlc-orchestrator/SKILL.md` to `.claude/skills/sdlc-orchestrator/SKILL.md`.
- [ ] 3.3 Copy the updated canonical `skills/sdlc-orchestrator/SKILL.md` to `.cursor/skills/sdlc-orchestrator/SKILL.md`.
- [ ] 3.4 Add or update tests that assert the distributed orchestrator copies match the canonical skill file.

## 4. Verification

- [ ] 4.1 Run `python -m pytest tests/test_sdlc_orchestrator.py -v` and verify all orchestrator tests pass.
- [ ] 4.2 Run any existing skill taxonomy or skill-copy tests that cover SDLC skills and verify they pass.
- [ ] 4.3 Run `openspec status --change strengthen-sdlc-orchestrator-routing-compliance` and verify the change is apply-ready.
- [ ] 4.4 Review `skills/sdlc-orchestrator/SKILL.md` for contradictions with existing boundary rules, especially the rule that the orchestrator routes and delegates rather than implementing downstream workflows.
