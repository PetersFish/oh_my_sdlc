# skill.sdlc-orchestrator Golden Eval Summary

- Eval ID: `eval-p1J-2026-06-10T14:27:06`
- Target: `skill.sdlc-orchestrator`
- Runner: Promptfoo via `opencode` provider
- Actual model observed in raw responses: `openai/gpt-5.5`
- Cases run: 6
- Passed: 0
- Failed: 6
- Errors: 0
- Output: `promptfoo-output.json`

## Result

The current model did not pass the golden set in this run.

## Important Harness Notes

- `promptfooconfig.yaml` labels the provider as `opencode-deepseek-v4`, but each raw response reports `providerID: openai` and `modelID: gpt-5.5`.
- The export config includes a global `defaultTest` requiring every case to contain `openspec-propose`. This incorrectly affects positive cases that intentionally should not mention `openspec-propose`, especially the simple typo-fix case.
- The explicit opt-out case uses `llm-rubric`; Promptfoo attempted an Anthropic rubric grader and reported a malformed grader output / connection issue, so that case includes evaluator infrastructure risk in addition to model behavior risk.

## Failure Themes

- Cross-skill rename advice did not bind the next action to `openspec-propose`.
- Ambiguous `执行plan` after a previous `spec-driven-propose-flow` classification did not continue via `openspec-propose`.
- Plan Mode exit response did not mention OpenSpec handoff.
- Cross-skill approach advice did not mention OpenSpec routing.
- Simple typo-fix case was failed by the global default assertion, even though its case-level assertion only forbids `openspec-propose`.
- Explicit opt-out case could not be reliably graded due to rubric grader failure.
