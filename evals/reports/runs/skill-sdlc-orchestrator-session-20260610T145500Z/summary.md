# skill.sdlc-orchestrator Session Eval Summary

- Target: `skill.sdlc-orchestrator`
- Eval mode: in-session rule-injection eval, no Promptfoo
- Model: current active OpenCode session model after user switch to DeepSeek V4 Pro
- Skill source of truth: `skills/sdlc-orchestrator/SKILL.md` on disk
- Cases run: 6
- Passed: 6
- Failed: 0
- Errors: 0

## Important Notes

- This is not an independent Promptfoo run. It verifies whether the current session model can comply when the current `sdlc-orchestrator` rules are present in-context.
- The OpenCode `skill` tool returned stale `sdlc-orchestrator` content missing the newer route-binding sections, so this run used the repository file that was read from disk.
- The previous Promptfoo run did not reliably test activated-skill behavior because it sent only the case input to the model and did not inject the full current skill instructions.
- The Promptfoo export also has a known harness issue: global `defaultTest` requires `openspec-propose` for all cases, which contradicts the typo-fix positive case.

## Result

The current session model passes the golden set when the current `sdlc-orchestrator` rules are injected from disk.

## Case Results

| Case | Result | Notes |
|---|---:|---|
| `skill.sdlc-orchestrator.regression.propose-route-no-direct-exec` | PASS | Response routes to `openspec-propose` / OpenSpec proposal and does not default to direct execution. |
| `skill.sdlc-orchestrator.regression.execute-plan-after-propose-route` | PASS | Ambiguous `执行plan` continues the prior `spec-driven-propose-flow` via `openspec-propose`. |
| `skill.sdlc-orchestrator.regression.plan-mode-handoff` | PASS | Plan Mode handoff names OpenSpec proposal/change creation, not direct implementation. |
| `skill.sdlc-orchestrator.regression.question-tool-for-exclusive-paths` | PASS | Target behavior is to use the `question` tool with OpenSpec as the recommended first choice. |
| `skill.sdlc-orchestrator.positive.superpowers-direct-allows-direct-exec` | PASS | Typo fix routes to `superpowers-direct` and does not require `openspec-propose` or `openspec-new-change`. |
| `skill.sdlc-orchestrator.positive.explicit-opt-out-direct-exec` | PASS | Explicit OpenSpec opt-out is acknowledged and direct execution is allowed. |
