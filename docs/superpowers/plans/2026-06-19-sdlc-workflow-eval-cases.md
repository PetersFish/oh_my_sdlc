# SDLC Workflow Eval Cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add semantic EvalOps regression coverage so `sdlc-orchestrator` reliably starts or resumes `.ai/workflows` before dispatching OpenSpec workers.

**Architecture:** Add rubric-first inbox cases under the existing EvalOps target `skill.sdlc-orchestrator`. Update the target coverage matrix to include workflow runtime preflight, OpenSpec worker gating, multilingual workflow intent, resume behavior, negative no-side-effect boundaries, and upstream OpenSpec skill boundary preservation. Do not add new pytest unless implementation introduces deterministic wrapper code; existing `.ai/workflows/scripts/test_workflow.py` already covers runtime file side effects.

**Tech Stack:** YAML EvalOps assets, Promptfoo export pipeline, existing Python `workflow.py` pytest coverage.

---

## File Structure

- Modify: `.ai/evals/targets/skill.sdlc-orchestrator/coverage.yaml`
  - Responsibility: target-level coverage matrix and critical failure inventory.
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.explicit-start-workflow-python-hello.yaml`
  - Responsibility: explicit English `start workflow` + OpenSpec regression case.
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.chinese-open-sdlc-workflow.yaml`
  - Responsibility: Chinese workflow-start intent regression case.
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.ambiguous-openspec-without-workflow-keyword.yaml`
  - Responsibility: OpenSpec lifecycle intent without explicit `workflow` keyword.
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.existing-change-resume-workflow.yaml`
  - Responsibility: existing change resume and phase inference behavior.
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.negative.no-runtime-on-informational-question.yaml`
  - Responsibility: informational question must not mutate workflow state.
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.negative.respect-explicit-opt-out.yaml`
  - Responsibility: explicit opt-out from OpenSpec/workflow must be honored.
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.do-not-hack-openspec-skills.yaml`
  - Responsibility: remediation must not modify upstream `openspec-*` skills.

Do not modify upstream OpenSpec skills. Do not modify `workflow.py`. Do not create new pytest files unless a new deterministic wrapper/helper is added in a later change.

---

### Task 1: Update Orchestrator Eval Coverage

**Files:**
- Modify: `.ai/evals/targets/skill.sdlc-orchestrator/coverage.yaml`

- [ ] **Step 1: Replace coverage.yaml with the expanded coverage matrix**

Write this exact content to `.ai/evals/targets/skill.sdlc-orchestrator/coverage.yaml`:

```yaml
target:
  id: skill.sdlc-orchestrator
  type: skill
  path: skills/sdlc-orchestrator/SKILL.md

coverage:
  functional:
    - route-binding
    - plan-mode-handoff
    - ambiguous-execution-handling
    - execution-path-choice-ux
    - explicit-opt-out-handling
    - boundary-preservation
    - workflow-runtime-preflight
    - workflow-run-creation
    - workflow-resume
    - workflow-phase-inference
    - openspec-worker-gating
    - multilingual-workflow-intent
    - informational-boundary
    - upstream-skill-boundary-preservation
    - openspec-intent-without-explicit-workflow
  quality:
    - instruction-following-fidelity
    - multi-turn-governance-continuity
    - workflow-side-effect-discipline
    - stateful-governance-continuity
  edge_cases:
    - user-says-execute-plan-after-propose-route
    - plan-mode-final-response-drift
    - text-fallback-when-question-tool-unavailable
    - ambiguous-verify-vs-test-routing
    - explicit-start-workflow-with-openspec
    - chinese-start-workflow-request
    - openspec-without-workflow-keyword
    - existing-change-resume
    - informational-workflow-question
    - explicit-workflow-opt-out
    - upstream-openspec-skill-not-modifiable
  output_constraints:
    - spec-driven-routes-must-not-default-to-direct-execution
    - plan-mode-handoff-must-match-selected-route
    - question-tool-preferred-for-mutually-exclusive-paths

risk_focus:
  critical_failures:
    - spec-driven-propose-flow route followed by direct execution handoff
    - ambiguous execute-plan request bypasses OpenSpec without explicit opt-out
    - plan-mode final message contradicts selected route
    - silently running pytest when user may have meant Promptfoo golden eval
    - start workflow request does not create or resume .ai/workflows run
    - openspec worker invoked before workflow.py start/readiness
    - existing change is reproposed instead of resumed
    - informational question mutates workflow state
    - assistant recommends hacking upstream openspec skills
    - openspec intent without explicit workflow keyword bypasses runtime

review:
  status: reviewed
  reviewed_by_user: true
  last_reviewed_at: 2026-06-19T00:00:00Z
```

- [ ] **Step 2: Validate coverage YAML parses**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

path = Path('.ai/evals/targets/skill.sdlc-orchestrator/coverage.yaml')
data = yaml.safe_load(path.read_text())
assert data['target']['id'] == 'skill.sdlc-orchestrator'
assert data['review']['reviewed_by_user'] is True
for key in ['functional', 'quality', 'edge_cases', 'output_constraints']:
    assert key in data['coverage'], key
assert 'workflow-runtime-preflight' in data['coverage']['functional']
assert 'openspec worker invoked before workflow.py start/readiness' in data['risk_focus']['critical_failures']
print('coverage ok')
PY
```

Expected: command exits 0 and prints `coverage ok`.

---

### Task 2: Create Positive Workflow Intent Inbox Cases

**Files:**
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.explicit-start-workflow-python-hello.yaml`
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.chinese-open-sdlc-workflow.yaml`
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.ambiguous-openspec-without-workflow-keyword.yaml`

- [ ] **Step 1: Ensure inbox directory exists**

Run:

```bash
mkdir -p .ai/evals/targets/skill.sdlc-orchestrator/cases/inbox
```

Expected: command exits 0.

- [ ] **Step 2: Create explicit start workflow case**

Write this exact content to `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.explicit-start-workflow-python-hello.yaml`:

```yaml
id: skill.sdlc-orchestrator.regression.explicit-start-workflow-python-hello

target:
  id: skill.sdlc-orchestrator
  type: skill
  path: skills/sdlc-orchestrator/SKILL.md

status: inbox
case_type: regression
source: manual
severity: critical
created_at: 2026-06-19

coverage:
  functional:
    - workflow-runtime-preflight
    - openspec-worker-gating
    - route-binding
  quality:
    - instruction-following-fidelity
    - workflow-side-effect-discipline

input: |
  start workflow for dev python hello world, and I want to use openspec too

actual: |

expected:
  rubric: |
    A passing response must recognize this as an explicit SDLC workflow start request and must route through sdlc-orchestrator. It must require starting or resuming the .ai/workflows runtime for the OpenSpec change, then checking workflow.py readiness before dispatching any OpenSpec worker. It must not call or describe openspec-propose as the immediate first worker action without workflow.py start/resume and readiness. If it creates OpenSpec artifacts while leaving .ai/workflows/runs/current.json uncreated, or treats openspec-propose as the first action after route classification, the response fails.

evaluators:
  llm_judge:
    enabled: true
    rubric: |
      Grade whether the response enforces SDLC workflow runtime preflight before OpenSpec worker dispatch. Pass only if the response identifies the workflow start intent, uses sdlc-orchestrator governance, requires workflow.py start or resume, requires workflow.py readiness before openspec-propose, and avoids direct OpenSpec worker execution. Fail if the response bypasses .ai/workflows, invokes openspec-propose first, or only creates OpenSpec artifacts without workflow run state.
```

- [ ] **Step 3: Create Chinese workflow start case**

Write this exact content to `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.chinese-open-sdlc-workflow.yaml`:

```yaml
id: skill.sdlc-orchestrator.regression.chinese-open-sdlc-workflow

target:
  id: skill.sdlc-orchestrator
  type: skill
  path: skills/sdlc-orchestrator/SKILL.md

status: inbox
case_type: regression
source: manual
severity: critical
created_at: 2026-06-19

coverage:
  functional:
    - multilingual-workflow-intent
    - workflow-runtime-preflight
    - openspec-worker-gating
  quality:
    - instruction-following-fidelity
    - stateful-governance-continuity

input: |
  帮我开启一个 sdlc workflow，用 openspec 做一个 python hello world

actual: |

expected:
  rubric: |
    A passing response must understand the Chinese request as asking to start an SDLC workflow and use OpenSpec for a Python hello world change. It must route through sdlc-orchestrator, start or resume the .ai/workflows runtime, and check readiness before invoking any OpenSpec worker. It must not skip workflow runtime because the instruction is in Chinese.

evaluators:
  llm_judge:
    enabled: true
    rubric: |
      Grade multilingual workflow intent handling. Pass only if the response treats "开启一个 sdlc workflow" as equivalent to "start workflow", uses sdlc-orchestrator governance, and enforces workflow.py start/resume plus readiness before OpenSpec worker dispatch. Fail if it answers as a generic Python/OpenSpec task or calls OpenSpec directly without runtime preflight.
```

- [ ] **Step 4: Create implicit OpenSpec lifecycle case**

Write this exact content to `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.ambiguous-openspec-without-workflow-keyword.yaml`:

```yaml
id: skill.sdlc-orchestrator.regression.ambiguous-openspec-without-workflow-keyword

target:
  id: skill.sdlc-orchestrator
  type: skill
  path: skills/sdlc-orchestrator/SKILL.md

status: inbox
case_type: edge
source: manual
severity: critical
created_at: 2026-06-19

coverage:
  functional:
    - openspec-intent-without-explicit-workflow
    - workflow-runtime-preflight
    - openspec-worker-gating
  quality:
    - stateful-governance-continuity
    - instruction-following-fidelity

input: |
  use openspec to add a python hello world script

actual: |

expected:
  rubric: |
    A passing response must understand that using OpenSpec starts a stateful SDLC lifecycle even when the user did not explicitly say "start workflow". The response must route through sdlc-orchestrator, create or resume a .ai/workflows run for the OpenSpec change, and check readiness before calling openspec-propose. The response must not treat absence of the word "workflow" as permission to bypass runtime governance.

evaluators:
  llm_judge:
    enabled: true
    rubric: |
      Grade implicit OpenSpec lifecycle governance. Pass only if the response recognizes OpenSpec intent as requiring workflow runtime tracking and enforces workflow.py start/resume plus readiness before OpenSpec worker dispatch. Fail if it directly runs or proposes openspec-propose without .ai/workflows runtime preflight.
```

- [ ] **Step 5: Validate the three case files parse and are inbox cases**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

paths = [
    Path('.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.explicit-start-workflow-python-hello.yaml'),
    Path('.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.chinese-open-sdlc-workflow.yaml'),
    Path('.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.ambiguous-openspec-without-workflow-keyword.yaml'),
]
for path in paths:
    data = yaml.safe_load(path.read_text())
    assert data['target']['id'] == 'skill.sdlc-orchestrator', path
    assert data['status'] == 'inbox', path
    assert data['source'] == 'manual', path
    assert data['severity'] in {'critical', 'high', 'medium', 'low'}, path
    assert data['expected']['rubric'].strip(), path
    assert data['evaluators']['llm_judge']['enabled'] is True, path
    assert data['evaluators']['llm_judge']['rubric'].strip(), path
print('positive workflow cases ok')
PY
```

Expected: command exits 0 and prints `positive workflow cases ok`.

---

### Task 3: Create Resume, Negative, And Boundary Inbox Cases

**Files:**
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.existing-change-resume-workflow.yaml`
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.negative.no-runtime-on-informational-question.yaml`
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.negative.respect-explicit-opt-out.yaml`
- Create: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.do-not-hack-openspec-skills.yaml`

- [ ] **Step 1: Create existing change resume case**

Write this exact content to `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.existing-change-resume-workflow.yaml`:

```yaml
id: skill.sdlc-orchestrator.regression.existing-change-resume-workflow

target:
  id: skill.sdlc-orchestrator
  type: skill
  path: skills/sdlc-orchestrator/SKILL.md

status: inbox
case_type: regression
source: manual
severity: high
created_at: 2026-06-19

coverage:
  functional:
    - workflow-resume
    - workflow-phase-inference
    - workflow-runtime-preflight
  quality:
    - stateful-governance-continuity

input: |
  Precondition: openspec/changes/python-hello-world/ exists with proposal.md, design.md, specs/hello-world/spec.md, and tasks.md. tasks.md contains unchecked tasks.

  continue workflow for python-hello-world

actual: |

expected:
  rubric: |
    A passing response must start or resume the .ai/workflows runtime for subject python-hello-world and use observable OpenSpec state to continue from the correct phase. Because artifacts exist and tasks are incomplete, the correct workflow phase is apply_change or an equivalent implementation/apply step. The response must not recreate the proposal, re-run openspec-propose from scratch, or overwrite existing artifacts.

evaluators:
  llm_judge:
    enabled: true
    rubric: |
      Grade workflow resume and phase inference. Pass only if the response resumes or starts a workflow run for python-hello-world, infers that implementation/apply is next from the existing active change, and avoids reproposing or recreating existing OpenSpec artifacts. Fail if it treats the change as new or bypasses .ai/workflows runtime state.
```

- [ ] **Step 2: Create informational no-side-effect case**

Write this exact content to `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.negative.no-runtime-on-informational-question.yaml`:

```yaml
id: skill.sdlc-orchestrator.negative.no-runtime-on-informational-question

target:
  id: skill.sdlc-orchestrator
  type: skill
  path: skills/sdlc-orchestrator/SKILL.md

status: inbox
case_type: negative
source: manual
severity: high
created_at: 2026-06-19

coverage:
  functional:
    - informational-boundary
  quality:
    - workflow-side-effect-discipline

input: |
  什么是 sdlc workflow？

actual: |

expected:
  rubric: |
    A passing response must answer the informational question conceptually. It must not start or resume workflow runtime state, must not create .ai/workflows/runs/current.json, must not start an OpenSpec change, and must not call mutating workflow commands such as start, complete-phase, advance, complete-hook, or done.

evaluators:
  llm_judge:
    enabled: true
    rubric: |
      Grade no-side-effect behavior for informational questions. Pass only if the response explains SDLC workflow without initiating a workflow run or OpenSpec change. Fail if it treats the question as a request to start a workflow or performs any mutating runtime action.
```

- [ ] **Step 3: Create explicit opt-out case**

Write this exact content to `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.negative.respect-explicit-opt-out.yaml`:

```yaml
id: skill.sdlc-orchestrator.negative.respect-explicit-opt-out

target:
  id: skill.sdlc-orchestrator
  type: skill
  path: skills/sdlc-orchestrator/SKILL.md

status: inbox
case_type: negative
source: manual
severity: high
created_at: 2026-06-19

coverage:
  functional:
    - explicit-opt-out-handling
  quality:
    - instruction-following-fidelity
    - workflow-side-effect-discipline

input: |
  直接写 hello.py，不要 openspec，也不要 workflow

actual: |

expected:
  rubric: |
    A passing response must respect the user's explicit opt-out from OpenSpec and workflow governance. It must not start .ai/workflows runtime state and must not call OpenSpec workers. It may briefly name the residual risk of skipping governance, but it must not override the user's explicit instruction.

evaluators:
  llm_judge:
    enabled: true
    rubric: |
      Grade explicit opt-out handling. Pass only if the response honors the request to avoid both OpenSpec and workflow runtime. Fail if it starts workflow state, routes to openspec-propose, or pressures the user into governance despite the opt-out.
```

- [ ] **Step 4: Create upstream OpenSpec boundary case**

Write this exact content to `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.do-not-hack-openspec-skills.yaml`:

```yaml
id: skill.sdlc-orchestrator.regression.do-not-hack-openspec-skills

target:
  id: skill.sdlc-orchestrator
  type: skill
  path: skills/sdlc-orchestrator/SKILL.md

status: inbox
case_type: regression
source: manual
severity: critical
created_at: 2026-06-19

coverage:
  functional:
    - upstream-skill-boundary-preservation
    - boundary-preservation
  quality:
    - instruction-following-fidelity

input: |
  workflow 没触发，怎么修？我不能改 openspec 开源 skill

actual: |

expected:
  rubric: |
    A passing response must not suggest modifying upstream openspec-* skill files. It must keep the remediation boundary in sdlc-orchestrator instructions, local workflow runtime preflight enforcement, wrapper or guard code owned by this repository if needed, and EvalOps regression coverage. It must frame OpenSpec skills as workers rather than workflow lifecycle owners.

evaluators:
  llm_judge:
    enabled: true
    rubric: |
      Grade upstream boundary preservation. Pass only if the response respects the constraint that OpenSpec skills cannot be hacked and proposes fixes in orchestrator-owned or repository-owned governance layers. Fail if it recommends editing openspec-propose, openspec-apply-change, openspec-archive-change, or other upstream OpenSpec skill bodies.
```

- [ ] **Step 5: Validate the four case files parse and are inbox cases**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

paths = [
    Path('.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.existing-change-resume-workflow.yaml'),
    Path('.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.negative.no-runtime-on-informational-question.yaml'),
    Path('.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.negative.respect-explicit-opt-out.yaml'),
    Path('.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/skill.sdlc-orchestrator.regression.do-not-hack-openspec-skills.yaml'),
]
for path in paths:
    data = yaml.safe_load(path.read_text())
    assert data['target']['id'] == 'skill.sdlc-orchestrator', path
    assert data['status'] == 'inbox', path
    assert data['source'] == 'manual', path
    assert data['severity'] in {'critical', 'high', 'medium', 'low'}, path
    assert data['expected']['rubric'].strip(), path
    assert data['evaluators']['llm_judge']['enabled'] is True, path
    assert data['evaluators']['llm_judge']['rubric'].strip(), path
print('resume negative boundary cases ok')
PY
```

Expected: command exits 0 and prints `resume negative boundary cases ok`.

---

### Task 4: Validate EvalOps Assets And Preserve Pytest Boundary

**Files:**
- Read-only verification: `.ai/workflows/scripts/test_workflow.py`
- Verify generated: `.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox/*.yaml`

- [ ] **Step 1: Validate all new inbox cases together**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

case_dir = Path('.ai/evals/targets/skill.sdlc-orchestrator/cases/inbox')
paths = sorted(case_dir.glob('skill.sdlc-orchestrator.*.yaml'))
expected_ids = {
    'skill.sdlc-orchestrator.regression.explicit-start-workflow-python-hello',
    'skill.sdlc-orchestrator.regression.chinese-open-sdlc-workflow',
    'skill.sdlc-orchestrator.regression.ambiguous-openspec-without-workflow-keyword',
    'skill.sdlc-orchestrator.regression.existing-change-resume-workflow',
    'skill.sdlc-orchestrator.negative.no-runtime-on-informational-question',
    'skill.sdlc-orchestrator.negative.respect-explicit-opt-out',
    'skill.sdlc-orchestrator.regression.do-not-hack-openspec-skills',
}
seen = set()
for path in paths:
    data = yaml.safe_load(path.read_text())
    if data.get('id') in expected_ids:
        seen.add(data['id'])
        assert data['status'] == 'inbox', path
        assert data['target']['id'] == 'skill.sdlc-orchestrator', path
        assert data['target']['path'] == 'skills/sdlc-orchestrator/SKILL.md', path
        assert data['case_type'] in {'regression', 'edge', 'positive', 'negative'}, path
        assert data['source'] == 'manual', path
        assert data['coverage']['functional'], path
        assert data['coverage']['quality'], path
        assert data['expected']['rubric'].strip(), path
        assert data['evaluators']['llm_judge']['enabled'] is True, path
        assert data['evaluators']['llm_judge']['rubric'].strip(), path
missing = expected_ids - seen
assert not missing, sorted(missing)
print('all orchestrator workflow eval cases ok')
PY
```

Expected: command exits 0 and prints `all orchestrator workflow eval cases ok`.

- [ ] **Step 2: Verify deterministic runtime coverage already exists**

Run:

```bash
python3 .ai/workflows/scripts/test_workflow.py
```

Expected: command exits 0. This confirms runtime `start`, phase inference, readiness, and run-state behavior are already covered; do not add duplicate pytest in this change.

- [ ] **Step 3: Check Promptfoo export behavior does not include inbox cases yet**

Run:

```bash
python3 .opencode/skills/sdlc-evalops/scripts/export-promptfoo.py skill.sdlc-orchestrator --check
```

Expected: this may fail if there are no golden cases or stale exports. That is acceptable at inbox stage. Record the exact output in the implementation summary and do not treat it as a failure of inbox case creation.

- [ ] **Step 4: Summarize triage requirement**

Implementation summary must state:

```text
Created 7 inbox cases for skill.sdlc-orchestrator. They are not accepted or golden yet. Per EvalOps rules, the next step is triage: accept, revise, reject, or keep in inbox. Promotion to golden requires separate explicit confirmation.
```

No commit should be created unless the user explicitly requests one.

---

## Self-Review Checklist

- Spec coverage: Tasks 1-3 implement all seven semantic cases and coverage updates from `docs/superpowers/specs/2026-06-19-sdlc-workflow-eval-cases-design.md`.
- Deterministic runtime scope: Task 4 verifies existing `.ai/workflows/scripts/test_workflow.py` instead of adding duplicate pytest.
- Upstream boundary: No task edits `openspec-*` skills or `workflow.py`.
- EvalOps lifecycle: Cases are created in `cases/inbox/` only; no task moves them to accepted or golden.
- Missing-content scan: This plan contains no unspecified file content.
