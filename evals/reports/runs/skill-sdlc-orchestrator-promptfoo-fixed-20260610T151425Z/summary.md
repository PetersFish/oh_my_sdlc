# skill.sdlc-orchestrator Fixed Promptfoo Eval Summary

- Eval ID: `eval-Z4A-2026-06-10T15:14:27`
- Target: `skill.sdlc-orchestrator`
- Runner: Promptfoo via `opencode` provider
- Config: `evals/exports/promptfoo/skill.sdlc-orchestrator/promptfooconfig.yaml`
- Prompt: `evals/exports/promptfoo/skill.sdlc-orchestrator/prompt.md`
- Output: `promptfoo-output.json`
- Cases run: 6
- Passed: 6
- Failed: 0
- Errors: 0

## Fixes Validated

- Removed the global `defaultTest.assert` that required every case to contain `openspec-propose`.
- Added a skill-injected Promptfoo prompt so the runner evaluates `sdlc-orchestrator` behavior instead of bare model behavior.
- Replaced `llm-rubric` assertions with deterministic JavaScript assertions to avoid external grader failures.
- Corrected golden case inputs that conflicted with current route scoring rules.
