## 1. sdlc-evalops SKILL.md Strengthening

- [x] 1.1 In `capture-regression` workflow: after writing case to inbox, add mandatory triage step (ask user to accept/revise/reject/keep-in-inbox using question tool)
- [x] 1.2 In `capture-regression` workflow: after accept, add separate promotion-to-golden prompt with explicit confirmation
- [x] 1.3 In `generate-cases` workflow: after candidate summary, add triage interaction (continue iterating / accept selected / stop)
- [x] 1.4 Add new workflow: `eval-failure-analysis` with five-category classification (target-behavior-bug, case-expectation-bug, evaluator-issue, runner-config-issue, model-variance) and user-confirmed fix plan requirement
- [x] 1.5 Update `run` workflow step 4: replace "suggest capture for new patterns, do NOT auto-fix" with full failure classification workflow from 1.4
- [x] 1.6 Add new hard rule: After every capture/generate, the assistant MUST offer triage before proceeding to any other task
- [x] 1.7 Add new hard rule: Eval failure MUST trigger classification + user-confirmed fix plan before modifying target or eval assets

## 2. sdlc-orchestrator SKILL.md Strengthening

- [x] 2.1 In `evalops-gated` section: expand EvalOps Gate Phases to include the full lifecycle state machine (coverage → triage → promote → implement → pytest → golden eval → pass/fail gate → failure analysis)
- [x] 2.2 Add new rule: orchestrator SHALL NOT route to implementation until triage is complete for inbox cases in the current session
- [x] 2.3 Add new rule: orchestrator SHALL require both pytest pass AND golden eval run before claiming completion for EvalOps-gated changes
- [x] 2.4 Add new rule: golden eval failure blocks forward progress; orchestrator SHALL route to `sdlc-evalops` failure analysis, not permit direct fix
- [x] 2.5 Update `Final Golden Eval Reporting` section: add blocked state reporting (no golden cases, runner unavailable, API key not set), failure state reporting (failure count + reference to failure classification)
- [x] 2.6 Add new rule: the final implementation summary SHALL NOT claim completion if EvalOps state is before golden-eval-pass

## 3. Pytest Coverage

- [x] 3.1 `tests/test_evalops_skill.py`: Test that SKILL.md capture-regression workflow references mandatory triage step and question tool
- [x] 3.2 `tests/test_evalops_skill.py`: Test that SKILL.md capture-regression workflow references separate golden promotion confirmation
- [x] 3.3 `tests/test_evalops_skill.py`: Test that SKILL.md defines the five failure categories in eval-failure-analysis
- [x] 3.4 `tests/test_evalops_skill.py`: Test that SKILL.md contains hard rule that eval failure must not trigger auto-fix
- [x] 3.5 `tests/test_sdlc_orchestrator.py`: Test that SKILL.md EvalOps Gate Phases include triage and golden eval state tracking
- [x] 3.6 `tests/test_sdlc_orchestrator.py`: Test that SKILL.md mandates golden eval before completion claim for EvalOps-gated changes
- [x] 3.7 `tests/test_sdlc_orchestrator.py`: Test that SKILL.md requires failure analysis routing when golden eval fails

## 4. Eval Regression Cases

- [x] 4.1 Create `.ai/evals/targets/skill.sdlc-evalops/cases/inbox/` regression case: after capture, assistant must offer triage (accept/revise/reject) before continuing
- [x] 4.2 Create `.ai/evals/targets/skill.sdlc-evalops/cases/inbox/` regression case: eval run failure must trigger classification, not auto-fix
- [x] 4.3 Create `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/` regression case: after generating eval case for an EvalOps-gated change, orchestrator must require triage before implementation
- [x] 4.4 Create `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/` regression case: orchestrator must NOT claim completion for EvalOps-gated change without golden eval

## 5. Eval Case Lifecycle Gate

- [x] 5.1 Present the newly created inbox regression cases to the user and ask which cases to accept, revise, reject, or keep in inbox
- [x] 5.2 For user-accepted cases, ask separately whether to promote each accepted case to golden
- [x] 5.3 Promote only user-confirmed cases to `cases/golden/` and leave non-promoted accepted cases in `cases/accepted/`
- [x] 5.4 If no cases are promoted to golden, report golden eval as blocked and ask whether the user wants an explicit EvalOps exception before proceeding
- [x] 5.5 Run `python3 -m pytest tests/test_evalops_skill.py tests/test_sdlc_orchestrator.py -v`; if pytest fails, fix via TDD before any golden eval run
- [x] 5.6 Run golden eval for `skill.sdlc-evalops` if any `skill.sdlc-evalops` cases were promoted; if the run is blocked, report the blocked dependency explicitly
- [x] 5.7 Run golden eval for `skill.sdlc-orchestrator` if any `skill.sdlc-orchestrator` cases were promoted; if the run is blocked, report the blocked dependency explicitly
- [x] 5.8 If golden eval passes, proceed to sync and validation
- [x] 5.9 If golden eval fails, classify failures using the five-category EvalOps failure model, present a fix plan, and wait for user confirmation before making any optimization or repair

## 6. Sync and Validation

- [x] 6.1 Sync `skills/sdlc-evalops/SKILL.md` to `.opencode/skills/sdlc-evalops/SKILL.md` and `.config/opencode/skills/sdlc-evalops/SKILL.md`
- [x] 6.2 Sync `skills/sdlc-orchestrator/SKILL.md` to `.opencode/skills/sdlc-orchestrator/SKILL.md` and other runtime copies
- [x] 6.3 Run `python3 skills/sdlc-roadmap/scripts/validate.py` to confirm roadmap integrity
