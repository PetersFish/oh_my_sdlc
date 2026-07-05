# SDLC Workflow Runtime Preflight Eval Cases Design

## Motivation

The `sdlc-orchestrator` skill currently has a gap: when a user explicitly or implicitly starts
an SDLC/OpenSpec workflow, the model may skip `workflow.py start/readiness` and call an
OpenSpec worker directly. This produces OpenSpec artifacts but leaves `.ai/workflows/runs/`
empty, breaking the entire stateful governance chain.

The fix is **not** to modify upstream `openspec-*` skills — those are open-source and
modifying them would create merge conflicts. The fix lives in `sdlc-orchestrator`'s
instruction priority, local runtime preflight discipline, and EvalOps regression coverage.

This design defines 7 semantic regression cases targeting `skill.sdlc-orchestrator`.
The deterministic workflow runtime behavior is already covered by existing pytest tests,
so this change should not add duplicate runtime tests unless implementation introduces a
new local wrapper/helper.

## Architecture

Two complementary verification layers already exist or are added by this design:

1. **Promptfoo semantic cases** — added by this design as rubric-first LLM evaluation of the orchestrator's
   decision-making: did the model correctly identify the intent, invoke the orchestrator,
   and enforce runtime preflight before dispatching any OpenSpec worker?

2. **Existing deterministic pytest coverage** — `.ai/workflows/scripts/test_workflow.py`
   already verifies that `workflow.py start/resume/readiness` create and update
   `.ai/workflows/runs/current.json` with correct fields and phase inference.

The boundary is firm: `openspec-*` skills remain pure workers. The `sdlc-orchestrator` is
the sole lifecycle owner responsible for runtime preflight, phase tracking, and evidence recording.

## Eval Target

- **Target id**: `skill.sdlc-orchestrator`
- **Workspace**: `.ai/evals/targets/skill.sdlc-orchestrator/`
- **Coverage**: `.ai/evals/targets/skill.sdlc-orchestrator/coverage.yaml`
- **Assertion policy**: rubric-first for semantic behavior; deterministic assertions
  reserved for exact structural checks only

## 7 Inbox Cases

All cases enter `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/` first.
They will be triaged and promoted to golden after user review.

Each case YAML should use the EvalOps schema fields directly:

- `status: inbox`
- `source: manual`
- `case_type`: one of `regression`, `edge`, `positive`, or `negative`
- `expected.rubric` and `evaluators.llm_judge.rubric` as the primary semantic assertion
- `coverage.functional` and `coverage.quality` populated from the listed coverage dimensions

### Case 1: explicit-start-workflow-python-hello

- **id**: `skill.sdlc-orchestrator.regression.explicit-start-workflow-python-hello`
- **case_type**: regression
- **severity**: critical
- **input**: `start workflow for dev python hello world, and I want to use openspec too`
- **coverage dimensions**: `workflow-runtime-preflight`, `openspec-worker-gating`, `route-binding`
- **expected rubric**:
  - The orchestrator MUST recognize this as an explicit SDLC workflow start request.
  - The orchestrator MUST start or resume a `.ai/workflows` runtime run.
  - The orchestrator MUST call readiness before dispatching any OpenSpec worker.
  - The response MUST NOT invoke `openspec-propose` directly without runtime preflight.
  - If at any point the model proposes to call `openspec-propose` as the immediate first
    action without `workflow.py start/readiness`, the response is a failure.

### Case 2: chinese-open-sdlc-workflow

- **id**: `skill.sdlc-orchestrator.regression.chinese-open-sdlc-workflow`
- **case_type**: regression
- **severity**: critical
- **input**: `帮我开启一个 sdlc workflow，用 openspec 做一个 python hello world`
- **coverage dimensions**: `multilingual-workflow-intent`, `workflow-runtime-preflight`
- **expected rubric**:
  - The Chinese phrase '开启 sdlc workflow' (open/start SDLC workflow) MUST be recognized
    as semantically equivalent to `start workflow`.
  - The orchestrator MUST be loaded for this request.
  - A workflow run MUST be created or resumed.
  - The OpenSpec worker MUST NOT be dispatched before readiness is confirmed.

### Case 3: ambiguous-openspec-without-workflow-keyword

- **id**: `skill.sdlc-orchestrator.regression.ambiguous-openspec-without-workflow-keyword`
- **case_type**: edge
- **severity**: critical
- **input**: `use openspec to add a python hello world script`
- **coverage dimensions**: `openspec-intent-without-explicit-workflow`, `stateful-openspec-lifecycle`
- **expected rubric**:
  - Even though 'start workflow' was not explicitly stated, entering OpenSpec lifecycle
    is itself a stateful SDLC run that the orchestrator MUST govern.
  - The orchestrator MUST create a `.ai/workflows` run for the change.
  - The orchestrator MUST NOT skip runtime solely because the user omitted the
    keyword 'workflow' or 'start workflow'.
  - The response MUST NOT directly call `openspec-propose` without runtime preflight.

### Case 4: existing-change-resume-workflow

- **id**: `skill.sdlc-orchestrator.regression.existing-change-resume-workflow`
- **case_type**: regression
- **severity**: high
- **precondition**: `openspec/changes/python-hello-world/` exists with all artifacts
  created but `tasks.md` tasks not yet all checked off.
- **input**: `continue workflow for python-hello-world`
- **coverage dimensions**: `workflow-resume`, `workflow-phase-inference`
- **expected rubric**:
  - The orchestrator MUST start or resume a workflow run for subject `python-hello-world`.
  - The runtime phase MUST be inferred from observable state — the artifacts are done
    but tasks are incomplete, so the phase should be `apply_change`, not `create_change`.
  - The orchestrator MUST NOT re-propose the change from scratch.
  - The orchestrator MUST NOT re-create OpenSpec artifacts that already exist.

### Case 5: no-runtime-on-informational-question

- **id**: `skill.sdlc-orchestrator.negative.no-runtime-on-informational-question`
- **case_type**: negative
- **severity**: high
- **input**: `什么是 sdlc workflow？`
- **coverage dimensions**: `informational-boundary`, `no-unwanted-side-effects`
- **expected rubric**:
  - The response MUST be a conceptual explanation of what SDLC workflow is.
  - The orchestrator MUST NOT create `.ai/workflows/runs/current.json`.
  - The orchestrator MUST NOT start any OpenSpec change.
  - The orchestrator MUST NOT call workflow runtime mutation commands (start, complete-phase, advance, etc.).

### Case 6: respect-explicit-opt-out

- **id**: `skill.sdlc-orchestrator.negative.respect-explicit-opt-out`
- **case_type**: negative
- **severity**: high
- **input**: `直接写 hello.py，不要 openspec，也不要 workflow`
- **coverage dimensions**: `explicit-opt-out-handling`, `user-intent-priority`
- **expected rubric**:
  - The orchestrator MUST respect the user's explicit opt-out.
  - The orchestrator MUST NOT start a workflow runtime run.
  - The orchestrator MUST NOT call any OpenSpec worker.
  - It is acceptable (but not required) to briefly note residual risk from skipping
    governance. However, the response MUST NOT override the user's opt-out.

### Case 7: do-not-hack-openspec-skills

- **id**: `skill.sdlc-orchestrator.regression.do-not-hack-openspec-skills`
- **case_type**: regression
- **severity**: critical
- **input**: `workflow 没触发，怎么修？我不能改 openspec 开源 skill`
- **coverage dimensions**: `boundary-preservation`, `upstream-skill-integrity`, `remediation-routing`
- **expected rubric**:
  - The response MUST NOT suggest modifying any `openspec-*` skill files.
  - The fix plan MUST be scoped to `sdlc-orchestrator`, local workflow runtime
    preflight enforcement, wrapper/guard, or EvalOps coverage.
  - The response MUST frame OpenSpec skills as workers, not lifecycle owners.
  - Recommending additional regression eval cases is encouraged.

## Deterministic Runtime Coverage

The workflow runtime's file-system side effects are deterministic code behavior, not semantic
AI behavior. They are therefore better covered by pytest than Promptfoo. Existing pytest coverage
already exercises the runtime contract, so this design does not add duplicate runtime tests.

Existing coverage in `.ai/workflows/scripts/test_workflow.py` includes:

- `start` creates `.ai/workflows/runs/current.json`
- `primary_subject` records `type: openspec_change` and the requested change id
- missing changes infer `current_phase == "create_change"`
- active changes infer `current_phase == "apply_change"`
- archived changes infer `current_phase == "post_archive_actions"`
- completed-task changes infer `current_phase == "archive_change"`
- `readiness` blocks when required inputs are missing
- commands accept `--root` and run against temporary workspaces without mutating real repository state

### When To Add Pytest

Add pytest only if implementation introduces new deterministic code such as a local
`sdlc_workflow_preflight(change_id)` helper or orchestrator dispatch wrapper. In that case,
pytest should verify the helper invokes `workflow.py start/resume` and `workflow.py readiness`
before any worker dispatch. If implementation only changes `sdlc-orchestrator` instructions
and EvalOps cases, Promptfoo semantic regression cases are the appropriate coverage.

## Coverage Updates

The following dimensions SHALL be added to `.ai/evals/targets/skill.sdlc-orchestrator/coverage.yaml`:

### functional (new)
- `workflow-runtime-preflight`
- `workflow-run-creation`
- `workflow-resume`
- `workflow-phase-inference`
- `openspec-worker-gating`
- `multilingual-workflow-intent`
- `informational-boundary`
- `upstream-skill-boundary-preservation`
- `openspec-intent-without-explicit-workflow`

### quality (new)
- `workflow-side-effect-discipline`
- `stateful-governance-continuity`

### edge_cases (new)
- `explicit-start-workflow-with-openspec`
- `chinese-start-workflow-request`
- `openspec-without-workflow-keyword`
- `existing-change-resume`
- `informational-workflow-question`
- `explicit-workflow-opt-out`
- `upstream-openspec-skill-not-modifiable`

### critical_failures (new)
- `start workflow request does not create or resume .ai/workflows run`
- `openspec worker invoked before workflow.py start/readiness`
- `existing change is reproposed instead of resumed`
- `informational question mutates workflow state`
- `assistant recommends hacking upstream openspec skills`
- `openspec intent without explicit workflow keyword bypasses runtime`

## Non-Goals

- Do NOT modify any file under `skills/openspec-*`, `.opencode/skills/openspec-*`,
  or the upstream OpenSpec npm package.
- Do NOT modify `workflow.py` runtime (it is not the cause of this bug).
- Do NOT create Promptfoo deterministic assertions using broad `must_include` keyword
  checks for semantic behavior evaluation.

## Risks

- **Risk**: Rubric-only eval may pass on wording but miss file-system gaps.
  **Mitigation**: Rely on existing `workflow.py` pytest coverage for deterministic runtime behavior;
  add wrapper-level pytest only if new wrapper code is introduced.
- **Risk**: Model may satisfy the rubric by describing the correct process without actually
  doing it (simulated compliance).
  **Mitigation**: Keep the semantic cases focused on required tool-ordering behavior and pair them
  with existing runtime tests that prove the deterministic command side effects.
