## Why

After capturing/ generating an EvalOps case for an AI behavior target, the assistant often stops without interacting with the user to triage, accept, or promote to golden. After implementation completes, golden eval for the affected target is not automatically run. When golden eval fails, there is no systematic failure-analysis gate that requires a user-confirmed fix plan before modifying the target. These gaps leave eval assets stranded in inbox, break the EvalOps-gated completion contract, and allow behavioral regressions to persist without structured diagnosis.

## What Changes

- **sdlc-evalops**: `capture-regression` and `generate-cases` workflows now require an explicit triage interaction (ask user to accept/revise/reject/keep-in-inbox) before proceeding. `accept` is followed by a separate promote-to-golden prompt.
- **sdlc-evalops**: `run` failure handling now requires failure classification (target-behavior-bug, case-expectation-bug, evaluator-issue, runner-config-issue, model-variance) and a user-confirmed fix plan before modifying the target or its eval assets.
- **sdlc-orchestrator**: The EvalOps gate now enforces the complete lifecycle loop. The orchestrator SHALL NOT route to implementation until EvalOps cases pass through triage or the user explicitly opts out. The orchestrator SHALL require both pytest and golden eval before claiming completion for EvalOps-gated changes. Golden eval failure blocks forward progress and triggers failure analysis.

## Capabilities

### New Capabilities
<!-- None. This change strengthens existing capabilities, not introduces new ones. -->

### Modified Capabilities
- `sdlc-evalops`: capture/generate workflows now require mandatory triage interaction; run failure now requires classification + user-confirmed fix plan.
- `sdlc-orchestrator`: EvalOps gate now enforces full lifecycle loop (triage → promote → implement → pytest → golden eval → pass/fail gate → failure analysis).

## Impact

- Affected skills: `skills/sdlc-evalops/SKILL.md`, `skills/sdlc-orchestrator/SKILL.md`
- Affected specs: `openspec/specs/sdlc-evalops/spec.md`, `openspec/specs/sdlc-orchestrator/spec.md`
- Affected tests: `tests/test_evalops_skill.py`, `tests/test_sdlc_orchestrator.py`
- Affected eval targets: `.ai/evals/targets/skill.sdlc-evalops/`, `.ai/evals/targets/skill.sdlc-orchestrator/`
- No breaking changes to file models, APIs, or data schemas
