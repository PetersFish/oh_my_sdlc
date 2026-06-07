---
name: meta-skill-evalops
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
