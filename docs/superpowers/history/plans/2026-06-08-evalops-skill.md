# sdlc-evalops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `sdlc-evalops`, a meta-skill that manages AI eval assets (coverage matrix, case collection, golden dataset), exports to Promptfoo, and runs regression evaluation for skill/agent/workflow/project targets.

**Architecture:** Single SKILL.md as the LLM-facing instruction document, mirroring the established `SKILL.md + templates/` pattern used by `sdlc-openspec-init` and `meta-skill-lifecycle-governance`. Seven internal commands (`init`, `define-coverage`, `capture`, `generate-cases`, `triage`, `promote`, `run`) are exposed as LLM-orchestratable capabilities behind three high-level natural-language workflows (`create-eval-suite`, `capture-regression`, `run-regression`). Templates provide ready-to-copy artifact scaffolds.

**Tech Stack:** OpenCode SKILL.md format (YAML frontmatter + Markdown body), YAML templates, Python unittest for content validation tests.

---

### File Structure

```
skills/sdlc-evalops/
  SKILL.md                          # LLM-facing skill instructions
  templates/
    default-coverage.yaml           # Coverage matrix template
    default-case.yaml               # Eval case template
    eval-policy.yaml                # Default eval policy
    target-index.yaml               # Default target index
    promptfooconfig.yaml            # Promptfoo config export template
    promptfoo-cases.yaml            # Promptfoo cases export template
  evals/
    evals.json                      # Routing eval for this skill itself

tests/
  test_evalops_skill.py             # Content validation tests
```

---

### Task 1: Create skill directory, templates, and eval stub

**Files:**
- Create: `skills/sdlc-evalops/` (directory)
- Create: `skills/sdlc-evalops/templates/` (directory)
- Create: `skills/sdlc-evalops/evals/` (directory)
- Create: `skills/sdlc-evalops/templates/default-coverage.yaml`
- Create: `skills/sdlc-evalops/templates/default-case.yaml`
- Create: `skills/sdlc-evalops/templates/eval-policy.yaml`
- Create: `skills/sdlc-evalops/templates/target-index.yaml`
- Create: `skills/sdlc-evalops/templates/promptfooconfig.yaml`
- Create: `skills/sdlc-evalops/templates/promptfoo-cases.yaml`
- Create: `skills/sdlc-evalops/evals/evals.json`

- [ ] **Step 1: Create directory structure**

Run: 

```bash
mkdir -p skills/sdlc-evalops/templates skills/sdlc-evalops/evals
```

- [ ] **Step 2: Write default-coverage.yaml template**

```yaml
target:
  id: <<target-id>>
  type: <<target-type>>
  path: <<target-source-path>>

coverage:
  functional: []
  quality: []
  edge_cases: []
  output_constraints: []

risk_focus:
  critical_failures: []

review:
  status: draft
  reviewed_by_user: false
  last_reviewed_at: null
```

Run: 

```bash
cat > skills/sdlc-evalops/templates/default-coverage.yaml << 'COVERAGEEOF'
target:
  id: <<target-id>>
  type: <<target-type>>
  path: <<target-source-path>>

coverage:
  functional: []
  quality: []
  edge_cases: []
  output_constraints: []

risk_focus:
  critical_failures: []

review:
  status: draft
  reviewed_by_user: false
  last_reviewed_at: null
COVERAGEEOF
```

- [ ] **Step 3: Write default-case.yaml template**

```yaml
id: <<target-id>>.<<case-type>>.<<short-name>>

target:
  id: <<target-id>>
  type: <<target-type>>
  path: <<target-source-path>>

status: inbox
case_type: failure
source: manual
severity: medium
created_at: <<YYYY-MM-DD>>

coverage:
  functional: []
  quality: []

input: |
  <<user-input>>

actual: |
  <<actual-output-if-applicable>>

expected:
  must_include: []
  must_not_include: []
  rubric: |
    <<evaluation-rubric>>

evaluators:
  rule_based:
    contains: []
  llm_judge:
    enabled: false
    rubric: |
      <<llm-judge-rubric>>
```

Run: 

```bash
cat > skills/sdlc-evalops/templates/default-case.yaml << 'CASEEOF'
id: <<target-id>>.<<case-type>>.<<short-name>>

target:
  id: <<target-id>>
  type: <<target-type>>
  path: <<target-source-path>>

status: inbox
case_type: failure
source: manual
severity: medium
created_at: <<YYYY-MM-DD>>

coverage:
  functional: []
  quality: []

input: |
  <<user-input>>

actual: |
  <<actual-output-if-applicable>>

expected:
  must_include: []
  must_not_include: []
  rubric: |
    <<evaluation-rubric>>

evaluators:
  rule_based:
    contains: []
  llm_judge:
    enabled: false
    rubric: |
      <<llm-judge-rubric>>
CASEEOF
```

- [ ] **Step 4: Write eval-policy.yaml template**

```yaml
default_runner: promptfoo
golden_requires_human_approval: true
ai_generated_cases_default_status: inbox
coverage_review_required_before_generation: true
```

Run: 

```bash
cat > skills/sdlc-evalops/templates/eval-policy.yaml << 'POLICYEOF'
default_runner: promptfoo
golden_requires_human_approval: true
ai_generated_cases_default_status: inbox
coverage_review_required_before_generation: true
POLICYEOF
```

- [ ] **Step 5: Write target-index.yaml template**

```yaml
targets: []
```

Run: 

```bash
echo 'targets: []' > skills/sdlc-evalops/templates/target-index.yaml
```

- [ ] **Step 6: Write promptfooconfig.yaml template**

```yaml
description: "EvalOps export for <<target-id>>"

prompts:
  - "<<prompt-file-or-text>>"

providers: []

defaultTest:
  assert:
    - type: contains
      value: "<<placeholder>>"

tests: "<<cases-file>>"
```

Run: 

```bash
cat > skills/sdlc-evalops/templates/promptfooconfig.yaml << 'PFCONFIGEOF'
description: "EvalOps export for <<target-id>>"

prompts:
  - "<<prompt-file-or-text>>"

providers: []

defaultTest:
  assert:
    - type: contains
      value: "<<placeholder>>"

tests: "<<cases-file>>"
PFCONFIGEOF
```

- [ ] **Step 7: Write promptfoo-cases.yaml template**

```yaml
- vars:
    input: |
      <<user-input>>
  assert:
    - type: contains
      value: <<expected-substring>>
```

Run: 

```bash
cat > skills/sdlc-evalops/templates/promptfoo-cases.yaml << 'PFCASEEOF'
- vars:
    input: |
      <<user-input>>
  assert:
    - type: contains
      value: <<expected-substring>>
PFCASEEOF
```

- [ ] **Step 8: Write evals/evals.json routing stub**

```json
{
  "skill_name": "sdlc-evalops",
  "evals": [
    {
      "id": 1,
      "prompt": "帮我给 research-general skill 建一套 eval case，用于回归测试。",
      "expected_output": "Recognize create-eval-suite intent, check initialization, lead into coverage brainstorming.",
      "files": []
    },
    {
      "id": 2,
      "prompt": "刚才 research skill 又遗漏了成本分析，帮我把这个失败沉淀下来。",
      "expected_output": "Recognize capture-regression intent, extract context, ask confirmation before writing to inbox.",
      "files": []
    },
    {
      "id": 3,
      "prompt": "我改完了 openspec-init，跑一下它的 eval。",
      "expected_output": "Recognize run-regression intent, locate target, export promptfoo, run and summarize.",
      "files": []
    }
  ]
}
```

Run: 

```bash
cat > skills/sdlc-evalops/evals/evals.json << 'EVALSEOF'
{
  "skill_name": "sdlc-evalops",
  "evals": [
    {
      "id": 1,
      "prompt": "帮我给 research-general skill 建一套 eval case，用于回归测试。",
      "expected_output": "Recognize create-eval-suite intent, check initialization, lead into coverage brainstorming.",
      "files": []
    },
    {
      "id": 2,
      "prompt": "刚才 research skill 又遗漏了成本分析，帮我把这个失败沉淀下来。",
      "expected_output": "Recognize capture-regression intent, extract context, ask confirmation before writing to inbox.",
      "files": []
    },
    {
      "id": 3,
      "prompt": "我改完了 openspec-init，跑一下它的 eval。",
      "expected_output": "Recognize run-regression intent, locate target, export promptfoo, run and summarize.",
      "files": []
    }
  ]
}
EVALSEOF
```

- [ ] **Step 9: Commit**

```bash
git add skills/sdlc-evalops/
git commit -m "feat: scaffold sdlc-evalops directory, templates, and eval stub"
```

---

### Task 2: Write SKILL.md — Frontmatter and When to Use

**Files:**
- Create: `skills/sdlc-evalops/SKILL.md`

- [ ] **Step 1: Write the frontmatter and initial sections**

```markdown
---
name: sdlc-evalops
description: Manage AI eval assets across skill, agent, workflow, RAG, and project targets. Use when the user wants to create eval cases, define coverage for a target's quality dimensions, capture real failures for regression, manage a golden dataset, export to Promptfoo, or run eval. Triggers include: building an eval suite, capturing a regression case, running eval for a target, defining quality coverage, managing an inbox/golden case pipeline, or phrases like 评测体系, 评估用例, 回归测试, eval case, golden dataset, coverage matrix. Do NOT use for debugging a single code failure (use systematic-debugging), writing unit tests (use test-driven-development), or one-off model comparisons without durable case management.
compatibility: Requires filesystem access for reading/writing evals/ directory, bash for promptfoo eval, and access to the target's source. Uses qa-ai-architecture for evaluator design discussions and brainstorming for coverage exploration when available.
---

# EvalOps Skill

Manage AI eval assets as version-controlled, tool-neutral artifacts. The skill defines three natural-language workflows (create-eval-suite, capture-regression, run-regression) backed by seven internal commands. Internal case schema is the source of truth; Promptfoo exports are derived artifacts.

## When to Use

- The user asks to build an eval suite for a skill, agent, workflow, RAG pipeline, or code project AI task.
- The user wants to capture a real failure as a regression case.
- The user wants to run eval after modifying a target.
- The user asks to define or review quality coverage dimensions.
- The user asks to manage inbox/golden cases (triage, promote, reject).
- The user asks to export eval cases to Promptfoo.

## When Not to Use

- The user is debugging a single code failure — use `systematic-debugging`.
- The user wants to write unit tests for code — use `test-driven-development`.
- The user is doing one-off model comparison without needing durable case management.
- The user wants to create, modify, or distribute a skill itself — use `meta-skill-lifecycle-governance`.
```

- [ ] **Step 2: Verify file written**

```bash
test -f skills/sdlc-evalops/SKILL.md && echo "OK"
```

- [ ] **Step 3: Commit**

```bash
git add skills/sdlc-evalops/SKILL.md
git commit -m "feat: add SKILL.md frontmatter and When to Use section"
```

---

### Task 3: Write SKILL.md — Interaction Model

**Files:**
- Modify: `skills/sdlc-evalops/SKILL.md`

- [ ] **Step 1: Append the Interaction Model section**

Append to SKILL.md:

```markdown
## Interaction Model

The skill exposes three high-level natural-language workflows. The LLM orchestrates them from user intent. The seven internal commands (init, define-coverage, capture, generate-cases, triage, promote, run) are capabilities, not required CLI input.

### Workflow 1: create-eval-suite

Trigger: user wants to build an eval suite for a target.

```
1. Check if evals/ is initialized; if not, run init first.
2. Determine target-id from context: `<target-type>.<name>`.
3. Check if coverage/`<target-id>`.yaml exists and `review.reviewed_by_user` is true.
4. If missing or unreviewed: enter coverage brainstorming (define-coverage).
5. Once coverage is reviewed: generate candidate cases into inbox.
6. Present candidate summary to user.
7. Ask: continue iterating, accept selected, or stop?
8. Triage accepted candidates.
9. Promote selected to golden (requires explicit user confirmation).
10. Run golden eval and summarize.
```

### Workflow 2: capture-regression

Trigger: user reports a failure or unexpected behavior from a target.

```
1. Extract input, actual output, and expected behavior from conversation context.
2. Ask user: "Should I capture this as a regression case for <target-id>?"
3. If confirmed: write to `evals/cases/inbox/<target-id>/<case-id>.yaml`.
4. Optionally offer to triage accept (not golden).
5. Remind: promote is a separate step for golden.
```

### Workflow 3: run-regression

Trigger: user modified a target and wants to run eval.

```
1. Locate target-id from user context or scan `metadata/target-index.yaml`.
2. Verify `evals/cases/golden/<target-id>/` has cases.
3. Export Promptfoo configs to `evals/exports/promptfoo/<target-id>/`.
4. Run `promptfoo eval -c <config-path>`.
5. Save run report to `evals/reports/runs/<run-id>/`.
6. Summarize: pass/fail counts, failed cases with severity.
7. If failures exist: suggest capture for new patterns, do NOT auto-fix.
```

### Proactive Capture

The assistant SHOULD proactively suggest capture when:
- The user points out a skill output is wrong or incomplete.
- The user corrects the AI's output.
- An eval run shows failures.
- A code review finds AI workflow gaps.
- OpenSpec verify detects a behavioral deviation.

The assistant MUST ask for confirmation before writing any case to disk.
```

- [ ] **Step 2: Commit**

```bash
git add skills/sdlc-evalops/SKILL.md
git commit -m "feat: add Interaction Model section with three workflows"
```

---

### Task 4: Write SKILL.md — Data Models and Directory Structure

**Files:**
- Modify: `skills/sdlc-evalops/SKILL.md`

- [ ] **Step 1: Append Data Models section**

Append to SKILL.md:

```markdown
## Directory Structure

The skill maintains assets under `evals/` at the project root:

```
evals/
  coverage/
    <target-id>.yaml
  cases/
    inbox/<target-id>/
    accepted/<target-id>/
    rejected/<target-id>/
    golden/<target-id>/
  exports/
    promptfoo/<target-id>/
  reports/
    runs/<run-id>/
    diagnosis/
  metadata/
    target-index.yaml
    eval-policy.yaml
```

`target-id` format: `<target-type>.<name>`. Examples:
- `skill.research-general`
- `agent.contract-review`
- `workflow.repository-memory-sync`
- `rag.customer-support`
- `project.checkout-api`

## Data Models

### Coverage Matrix

Template at `templates/default-coverage.yaml`. Key fields:

- `target`: id, type, path
- `coverage`: functional, quality, edge_cases, output_constraints — each a list of dimension strings
- `risk_focus.critical_failures`: list of specific failure patterns to prevent
- `review`: status (draft|reviewed), reviewed_by_user, last_reviewed_at

The coverage matrix is the **planning layer** for eval cases. It must be reviewed by the user (`reviewed_by_user: true`) before `generate-cases` can run.

### Eval Case

Template at `templates/default-case.yaml`. Key fields:

- `id`: unique identifier, recommended format `<target-id>.<case-type>.<short-name>`
- `target`: id, type, path
- `status`: inbox | accepted | rejected | golden
- `case_type`: failure | regression | golden_candidate | edge | positive | negative
- `source`: manual | observed | eval_failure | ai_suggested
- `severity`: critical | high | medium | low
- `coverage`: functional and quality dimensions this case exercises
- `input`: the user input to the target
- `actual`: the actual output (for failure cases)
- `expected`: must_include (list), must_not_include (list), rubric (text)
- `evaluators`: rule_based (contains list), llm_judge (enabled, rubric)

### Eval Policy

Template at `templates/eval-policy.yaml`. Defines:

- `default_runner`: fixed to `promptfoo` in MVP
- `golden_requires_human_approval`: always true
- `ai_generated_cases_default_status`: always inbox
- `coverage_review_required_before_generation`: always true

### Target Index

Template at `templates/target-index.yaml`. A registry of all eval targets in the project.
```

- [ ] **Step 2: Commit**

```bash
git add skills/sdlc-evalops/SKILL.md
git commit -m "feat: add Data Models and Directory Structure sections"
```

---

### Task 5: Write SKILL.md — Commands

**Files:**
- Modify: `skills/sdlc-evalops/SKILL.md`

- [ ] **Step 1: Append Commands section**

Append to SKILL.md:

```markdown
## Commands

Seven internal commands back the three workflows. The LLM selects and chains them; users may also invoke them directly.

### init

Initialize `evals/` directory at the project root.

**When**: first evalops usage in a project, or user explicitly asks.

**Produces**:
- `evals/coverage/`, `evals/cases/{inbox,accepted,rejected,golden}/`, `evals/exports/promptfoo/`, `evals/reports/{runs,diagnosis}/`
- `evals/metadata/target-index.yaml`
- `evals/metadata/eval-policy.yaml` (from `templates/eval-policy.yaml`)

**Rules**:
- Do NOT create cases during init.
- Do NOT auto-scan project targets.

### define-coverage

Define or iterate a coverage matrix for a target.

**Input**: target-id, target type, source path, user's quality concerns.

**Produces**: `evals/coverage/<target-id>.yaml`

**Process**:
1. Brainstorm with user: functional dimensions, quality attributes, edge cases, output constraints.
2. Identify critical failures — what specific failures are unacceptable?
3. Write coverage with `review.status: draft`.
4. Ask user to confirm. On confirmation, set `review.reviewed_by_user: true`.
5. If user says "refine later", keep draft but warn that generate-cases is gated on review.

### capture

Capture a failure, edge case, or positive example into inbox.

**Input**: target-id, input text, expected behavior, actual output (optional), severity, case_type, source.

**Produces**: `evals/cases/inbox/<target-id>/<case-id>.yaml`

**Rules**:
- Default status is inbox.
- Do NOT write to golden — even for "high-value" cases.
- Proactive suggestion allowed; writing to disk requires user confirmation.
- Extract input/actual from conversation context where possible.

### generate-cases

Generate candidate eval cases from a coverage matrix.

**Input**: target-id, optional focus dimensions, optional count.

**Produces**: `evals/cases/inbox/<target-id>/candidate-*.yaml`

**Hard Gate**:
- If `evals/coverage/<target-id>.yaml` does not exist: stop, run define-coverage first.
- If `coverage.review.reviewed_by_user` is not true: stop, ask user to review/refine coverage first.
- If coverage is reviewed: generate candidates.

**After generation, ask**:
- Continue iterating on a coverage dimension?
- Delete similar/overlapping candidates?
- Supplement with real-failure-style cases?
- Accept selected candidates?

**Rules**:
- AI-generated cases MUST enter inbox, never golden.
- Prefer coverage gaps and real failure patterns over generic bulk generation.

### triage

Sort inbox cases: accept, reject, revise, merge, split, or defer.

**Input**: target-id, case-ids, action, reason.

**Produces**: Moves cases between inbox/ accepted/ rejected/ directories.

**Rules**:
- accept does NOT equal golden. Promote is a separate step.
- Reject must record the reason.
- Accepted cases must have at minimum: non-empty expected (must_include or rubric), non-empty coverage, and a severity.

### promote

Promote accepted cases to golden regression cases.

**Input**: target-id, case-ids.

**Produces**: `evals/cases/golden/<target-id>/<case-id>.yaml`

**Pre-checks before promoting**:
- Case status is accepted (not inbox).
- expected.must_include or expected.rubric is non-empty.
- coverage is non-empty.
- severity is set.
- At least one evaluator is defined.
- User explicitly confirms: "Promote <case-id> to golden?"

### run

Run golden eval for a target using Promptfoo.

**Input**: target-id, optional provider/model.

**Produces**:
- `evals/exports/promptfoo/<target-id>/promptfooconfig.yaml`
- `evals/exports/promptfoo/<target-id>/cases.yaml`
- `evals/reports/runs/<run-id>/summary.md`
- `evals/reports/runs/<run-id>/promptfoo-output.json`
- `evals/reports/runs/<run-id>/failures.yaml`

**Steps**:
1. Read golden cases from `evals/cases/golden/<target-id>/`.
2. Map cases to Promptfoo format (see Promptfoo Mapping below).
3. Write `promptfooconfig.yaml` and `cases.yaml`.
4. Run `promptfoo eval -c <config-path> -o <reports-dir>/promptfoo-output.json`.
5. Parse output: pass/fail per case.
6. Write summary.md and failures.yaml.
7. Summarize for user: pass count, fail count, failed case ids with severity.
8. If failures: suggest capture for new patterns. Do NOT auto-fix.

**Rules**:
- Only run golden cases. Do not run inbox or accepted.
- Export is derived; internal case YAML remains source of truth.
- Do not modify target, case, or coverage on failure.
```

- [ ] **Step 2: Commit**

```bash
git add skills/sdlc-evalops/SKILL.md
git commit -m "feat: add seven internal commands section"
```

---

### Task 6: Write SKILL.md — Promptfoo Mapping, Hard Rules, and Workflow Integration

**Files:**
- Modify: `skills/sdlc-evalops/SKILL.md`

- [ ] **Step 1: Append remaining sections**

Append to SKILL.md:

```markdown
## Promptfoo Export Mapping

When exporting to Promptfoo, map internal case fields as follows:

| Internal Field | Promptfoo Mapping |
|----------------|-------------------|
| `input` | `vars.input` in test case |
| `expected.must_include` | `assert.type: contains` |
| `expected.must_not_include` | `assert.type: not-contains` |
| `expected.rubric` | `assert.type: llm-rubric` |
| `coverage / severity / case_type` | test metadata |

Supported assertions in MVP: `contains`, `not-contains`, `regex`, `llm-rubric`, `javascript`.

Export templates are at `templates/promptfooconfig.yaml` and `templates/promptfoo-cases.yaml`.

## Hard Rules

These rules override any contextual ambiguity. Violating them produces an incorrect eval pipeline.

1. **Coverage Matrix is the planning layer.** Without a user-reviewed coverage matrix, do not generate cases.
2. **AI-generated cases MUST enter inbox first.** Never write directly to accepted or golden.
3. **Golden Dataset MUST require human confirmation.** Promote only after user explicitly approves each case.
4. **Coverage MUST be user-reviewed before candidate generation.** If `review.reviewed_by_user` is not true, stop and require review.
5. **Promptfoo exports are derived artifacts, not source of truth.** Internal case YAML is canonical. Re-export when cases change.
6. **Eval failure MUST NOT trigger automatic fixes in MVP.** Failure may be caused by the target, the case, the expected, the evaluator, the context, or model variance.
7. **capture defaults to inbox.** Even if the user calls it "regression-critical", it goes to inbox. Triage and promote are separate gates.

## Workflow Integration

### With Superpowers Skills

- `brainstorming`: use for coverage exploration and case design discussions.
- `test-driven-development`: use for code behavior verification; this skill covers AI behavior.
- `meta-skill-lifecycle-governance`: EVALUATE-IN-REPO phase should run golden eval before release.
- `verification-before-completion`: before claiming work complete, report whether eval was run.

### With OpenSpec

```
openspec propose → design → spec → tasks
→ apply + TDD
→ evalops run (for affected targets)
→ openspec verify
→ memory sync
→ archive
```

### With Skill Lifecycle

```
DEVELOP → EVALUATE-IN-REPO (run golden eval)
→ PILOT-IN-PROJECT (capture real failures to inbox)
→ BACKPORT (flow generic failure cases back to canonical repo)
→ RELEASE (pass critical golden eval)
→ DISTRIBUTE
```

## Templates

Bundled templates under `templates/`:

| Template | Purpose |
|----------|---------|
| `default-coverage.yaml` | Coverage matrix scaffold |
| `default-case.yaml` | Eval case scaffold |
| `eval-policy.yaml` | Default policy values |
| `target-index.yaml` | Target registry scaffold |
| `promptfooconfig.yaml` | Promptfoo config export |
| `promptfoo-cases.yaml` | Promptfoo test cases export |

## File Naming Convention

Case ids follow: `<target-id>.<case-type>.<short-name>`

Examples:
- `skill.research-general.failure.cost-analysis-001`
- `agent.contract-review.edge.ambiguous-clause-003`
- `project.checkout-api.regression.missing-validation-002`

Candidate cases generated by AI use: `candidate-<sequential>` as short-name.
```

- [ ] **Step 2: Commit**

```bash
git add skills/sdlc-evalops/SKILL.md
git commit -m "feat: add Promptfoo mapping, hard rules, and workflow integration"
```

---

### Task 7: Write tests — Frontmatter and structural validation

**Files:**
- Create: `tests/test_evalops_skill.py`

- [ ] **Step 1: Write test file with frontmatter and structural tests**

```python
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALOPS_SKILL = REPO_ROOT / "skills" / "sdlc-evalops"


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    raw = text[3:end].strip()
    result = {}
    for line in raw.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


class TestEvalopsSkillFrontmatter:
    """Validate sdlc-evalops frontmatter and basic structure."""

    def test_skill_md_exists(self):
        assert (EVALOPS_SKILL / "SKILL.md").is_file(), \
            "sdlc-evalops/SKILL.md must exist"

    def test_skill_md_has_valid_frontmatter(self):
        fm = _read_frontmatter(EVALOPS_SKILL / "SKILL.md")
        assert fm.get("name") == "sdlc-evalops", \
            f"Expected name=sdlc-evalops, got {fm.get('name')}"
        assert "description" in fm, "description must exist in frontmatter"
        assert len(fm["description"]) > 50, \
            f"description too short: {len(fm['description'])} chars"
        desc = fm["description"].lower()
        assert "eval" in desc, "description must reference eval"
        assert "skill" in desc or "agent" in desc or "target" in desc, \
            "description must reference eval targets"

    def test_skill_md_has_compatibility(self):
        fm = _read_frontmatter(EVALOPS_SKILL / "SKILL.md")
        assert "compatibility" in fm, "compatibility must exist in frontmatter"

    def test_skill_md_mentions_all_seven_commands(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        commands = ["init", "define-coverage", "capture", "generate-cases",
                     "triage", "promote", "run"]
        lower = content.lower()
        for cmd in commands:
            assert cmd.lower() in lower, f"SKILL.md must mention command: {cmd}"

    def test_skill_md_mentions_three_workflows(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        workflows = ["create-eval-suite", "capture-regression", "run-regression"]
        lower = content.lower()
        for wf in workflows:
            assert wf.lower() in lower, f"SKILL.md must mention workflow: {wf}"

    def test_skill_md_mentions_target_id_format(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "target-type" in content.lower(), \
            "SKILL.md must define target-id format"
        assert "skill.research-general" in content.lower(), \
            "SKILL.md must include a target-id example"

    def test_skill_md_defines_dir_structure(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "evals/" in content, "SKILL.md must reference evals/ directory"
        assert "coverage/" in content, "SKILL.md must reference coverage/ directory"
        assert "inbox" in content.lower(), "SKILL.md must reference inbox"
        assert "golden" in content.lower(), "SKILL.md must reference golden"

    def test_skill_md_has_promptfoo_mapping(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "promptfoo" in lower, "SKILL.md must reference Promptfoo"
        assert "promptfooconfig.yaml" in lower, \
            "SKILL.md must reference promptfooconfig.yaml"
        assert "contains" in lower, "SKILL.md must reference contains assertion"
        assert "llm-rubric" in lower, "SKILL.md must reference llm-rubric"


class TestEvalopsSkillHardRules:
    """Validate hard rules are present and enforced."""

    def test_hard_rules_section_exists(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "## Hard Rules" in content, "SKILL.md must have Hard Rules section"

    def test_coverage_is_planning_layer(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "coverage matrix is the planning layer" in lower, \
            "Hard rule: coverage is planning layer"

    def test_ai_cases_inbox_first(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "ai-generated cases" in lower, \
            "Hard rule: AI-generated cases must be mentioned"
        assert "inbox" in lower, "Hard rule: inbox must be mentioned"

    def test_golden_requires_human_approval(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "human confirmation" in lower or "human approval" in lower, \
            "Hard rule: golden requires human approval"

    def test_coverage_review_before_generation(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "reviewed_by_user" in lower, \
            "Hard rule: must check reviewed_by_user before generate"
        assert "before" in lower, "Hard rule: gate must be before generation"

    def test_promptfoo_derived_not_source(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "derived" in lower, "Hard rule: exports are derived artifacts"

    def test_no_auto_fix_on_failure(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "not" in lower and "auto" in lower and "fix" in lower, \
            "Hard rule: no automatic fix on eval failure"


class TestEvalopsSkillTemplates:
    """Validate bundled templates exist and are well-formed."""

    def test_coverage_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "default-coverage.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_case_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "default-case.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_eval_policy_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "eval-policy.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_target_index_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "target-index.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_promptfoo_config_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "promptfooconfig.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_promptfoo_cases_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "promptfoo-cases.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_coverage_template_has_required_sections(self):
        content = (EVALOPS_SKILL / "templates" / "default-coverage.yaml") \
            .read_text(encoding="utf-8")
        assert "target:" in content, "Coverage template must have target section"
        assert "coverage:" in content, "Coverage template must have coverage section"
        assert "review:" in content, "Coverage template must have review section"

    def test_case_template_has_required_sections(self):
        content = (EVALOPS_SKILL / "templates" / "default-case.yaml") \
            .read_text(encoding="utf-8")
        assert "target:" in content, "Case template must have target section"
        assert "status:" in content, "Case template must have status field"
        assert "expected:" in content, "Case template must have expected section"
        assert "evaluators:" in content, "Case template must have evaluators section"

    def test_policy_template_golden_requires_approval(self):
        content = (EVALOPS_SKILL / "templates" / "eval-policy.yaml") \
            .read_text(encoding="utf-8")
        assert "golden_requires_human_approval: true" in content, \
            "Policy must enforce golden requires human approval"

    def test_policy_template_ai_cases_default_inbox(self):
        content = (EVALOPS_SKILL / "templates" / "eval-policy.yaml") \
            .read_text(encoding="utf-8")
        assert "ai_generated_cases_default_status: inbox" in content, \
            "Policy must default AI cases to inbox"


class TestEvalopsSkillEvals:
    """Validate evals/evals.json covers routing scenarios."""

    def test_evals_json_exists(self):
        path = EVALOPS_SKILL / "evals" / "evals.json"
        assert path.is_file(), f"Missing: {path}"

    def test_evals_json_has_three_scenarios(self):
        data = json.loads(
            (EVALOPS_SKILL / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        assert data["skill_name"] == "sdlc-evalops"
        assert len(data["evals"]) >= 3, \
            f"Expected at least 3 eval scenarios, got {len(data['evals'])}"

    def test_evals_cover_all_three_workflows(self):
        data = json.loads(
            (EVALOPS_SKILL / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        outputs = " ".join(e["expected_output"] for e in data["evals"]).lower()
        assert "create-eval-suite" in outputs, \
            "Evals must cover create-eval-suite workflow"
        assert "capture" in outputs, \
            "Evals must cover capture-regression workflow"
        assert "run" in outputs, \
            "Evals must cover run-regression workflow"


class TestEvalopsSkillWorkflowIntegration:
    """Validate workflow integration mentions exist."""

    def test_mentions_openspec_integration(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "openspec" in content.lower(), \
            "SKILL.md must mention OpenSpec integration"

    def test_mentions_skill_lifecycle_integration(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "evaluate-in-repo" in lower, \
            "SKILL.md must mention EVALUATE-IN-REPO"

    def test_mentions_brainstorming_integration(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "brainstorming" in lower, \
            "SKILL.md must mention brainstorming integration"
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_evalops_skill.py
git commit -m "test: add evalops skill frontmatter, rules, templates, and evals tests"
```

---

### Task 8: Run tests and verify

**Files:**
- None (verification only)

- [ ] **Step 1: Run the full test suite**

```bash
python -m pytest tests/test_evalops_skill.py -v
```

Expected: all tests PASS.

- [ ] **Step 2: If any test fails, fix the SKILL.md or template content until all pass**

- [ ] **Step 3: Run existing test suite to ensure no regressions**

```bash
python -m pytest tests/ -v
```

Expected: no new failures introduced.

- [ ] **Step 4: Verify SKILL.md line count**

```bash
wc -l skills/sdlc-evalops/SKILL.md
```

Expected: SKILL.md should be substantive (200+ lines).

- [ ] **Step 5: Commit final fixes if any**

```bash
git add skills/sdlc-evalops/SKILL.md tests/test_evalops_skill.py
git commit -m "fix: address test failures after verification"
```

Or if all pass on first run:

```bash
echo "All tests pass, no fixes needed"
```
```

---

### Task 9: Run the full verification suite and finalize

**Files:**
- None (verification only)

- [ ] **Step 1: Run full test suite one final time**

```bash
python -m pytest tests/test_evalops_skill.py -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run existing test suite to confirm no regressions**

```bash
python -m pytest tests/ -v
```

Expected: all pre-existing tests still PASS.

- [ ] **Step 3: Inspect git status**

```bash
git status --short
```

Expected: only `skills/sdlc-evalops/` and `tests/test_evalops_skill.py` are new.

- [ ] **Step 4: Commit**

```bash
git add skills/sdlc-evalops/ tests/test_evalops_skill.py
git commit -m "feat: add sdlc-evalops — EvalOps asset management and Promptfoo integration"
```
