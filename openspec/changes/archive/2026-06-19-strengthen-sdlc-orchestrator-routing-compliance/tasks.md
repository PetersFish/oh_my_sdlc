## 1. EvalOps Assets

- [x] 1.1 Initialize `evals/` metadata and directory structure if missing, including `evals/coverage/`, `evals/cases/{inbox,accepted,rejected,golden}/`, `evals/exports/promptfoo/`, `evals/reports/runs/`, and `evals/metadata/`.
- [x] 1.2 Register target `skill.sdlc-orchestrator` in `evals/metadata/target-index.yaml` with type `skill` and path `skills/sdlc-orchestrator/SKILL.md`.
- [x] 1.3 Create reviewed coverage matrix `evals/coverage/skill.sdlc-orchestrator.yaml` covering route binding, Plan Mode handoff compliance, ambiguous execution request handling, execution-path choice UX, explicit OpenSpec opt-out handling, and orchestrator boundary preservation.
- [x] 1.4 Add golden case `evals/cases/golden/skill.sdlc-orchestrator/skill.sdlc-orchestrator.regression.propose-route-no-direct-exec.yaml` for the regression where `spec-driven-propose-flow` was selected but the handoff offered direct execution.
- [x] 1.5 Add golden case `evals/cases/golden/skill.sdlc-orchestrator/skill.sdlc-orchestrator.regression.execute-plan-after-propose-route.yaml` for the regression where the user says "execute plan" after a `spec-driven-propose-flow` route.
- [x] 1.6 Add golden case `evals/cases/golden/skill.sdlc-orchestrator/skill.sdlc-orchestrator.regression.plan-mode-handoff.yaml` for Plan Mode final responses after `spec-driven-*` route decisions.
- [x] 1.7 Add golden case `evals/cases/golden/skill.sdlc-orchestrator/skill.sdlc-orchestrator.regression.question-tool-for-exclusive-paths.yaml` for mutually exclusive OpenSpec-vs-direct execution choices.
- [x] 1.8 Add golden case `evals/cases/golden/skill.sdlc-orchestrator/skill.sdlc-orchestrator.positive.superpowers-direct-allows-direct-exec.yaml` for low-risk `superpowers-direct` tasks.
- [x] 1.9 Add golden case `evals/cases/golden/skill.sdlc-orchestrator/skill.sdlc-orchestrator.positive.explicit-opt-out-direct-exec.yaml` for explicit user opt-out from OpenSpec governance.
- [x] 1.10 Export Promptfoo config for `skill.sdlc-orchestrator` under `evals/exports/promptfoo/skill.sdlc-orchestrator/` or document the exact export command if export tooling is not yet available.

## 2. Test Coverage

- [x] 2.1 Add `tests/test_sdlc_orchestrator.py` if it does not exist, with helpers that read `skills/sdlc-orchestrator/SKILL.md` and parse frontmatter.
- [x] 2.2 Add tests asserting the skill documents action-binding behavior for `spec-driven-propose-flow` and `spec-driven-incremental-flow`.
- [x] 2.3 Add tests asserting Plan Mode handoffs mention OpenSpec proposal/change creation for `spec-driven-*` routes and direct execution only for `superpowers-direct`.
- [x] 2.4 Add tests asserting ambiguous execution requests after `spec-driven-*` routes continue OpenSpec or require explicit opt-out.
- [x] 2.5 Add tests asserting mutually exclusive execution-path choices use the `question` tool when available and include a text fallback when unavailable.
- [x] 2.6 Add tests asserting EvalOps coverage and golden cases exist for `skill.sdlc-orchestrator` before implementation is considered complete.
- [x] 2.7 Run `python -m pytest tests/test_sdlc_orchestrator.py -v` and verify the new tests fail before implementation.

## 3. Skill Instruction Updates

- [x] 3.1 Update `skills/sdlc-orchestrator/SKILL.md` so the route classification section states route decisions are action-binding unless the user explicitly opts out.
- [x] 3.2 Update `spec-driven-propose-flow` action steps so the immediate next action is `openspec-propose`; direct execution is not presented as the default.
- [x] 3.3 Update `spec-driven-incremental-flow` action steps so the immediate next action is `openspec-new-change`; direct execution is not presented as the default.
- [x] 3.4 Add Plan Mode handoff rules mapping `spec-driven-propose-flow` to OpenSpec proposal/change creation, `spec-driven-incremental-flow` to OpenSpec change creation/continuation, and `superpowers-direct` to direct execution.
- [x] 3.5 Add ambiguous execution request rules for phrases like "execute plan", "go ahead", and "start" after prior `spec-driven-*` route decisions.
- [x] 3.6 Add execution-path choice rules requiring the `question` tool when available for mutually exclusive route choices, with recommended route first and text fallback when unavailable.

## 4. Distribution Updates

- [x] 4.1 Copy the updated canonical `skills/sdlc-orchestrator/SKILL.md` to `.opencode/skills/sdlc-orchestrator/SKILL.md`.
- [x] 4.2 Copy the updated canonical `skills/sdlc-orchestrator/SKILL.md` to `.claude/skills/sdlc-orchestrator/SKILL.md`.
- [x] 4.3 Copy the updated canonical `skills/sdlc-orchestrator/SKILL.md` to `.cursor/skills/sdlc-orchestrator/SKILL.md`.
- [x] 4.4 Add or update tests that assert the distributed orchestrator copies match the canonical skill file.

## 5. Verification

- [x] 5.1 Run `python -m pytest tests/test_sdlc_orchestrator.py -v` and verify all orchestrator tests pass.
- [x] 5.2 Run any existing skill taxonomy or skill-copy tests that cover SDLC skills and verify they pass.
- [x] 5.3 Run the `skill.sdlc-orchestrator` golden eval or, if Promptfoo is not configured yet, verify the exported Promptfoo cases and document the blocked runner dependency.
- [x] 5.4 Run `openspec status --change strengthen-sdlc-orchestrator-routing-compliance` and verify the change is apply-ready.
- [x] 5.5 Review `skills/sdlc-orchestrator/SKILL.md` for contradictions with existing boundary rules, especially the rule that the orchestrator routes and delegates rather than implementing downstream workflows.
