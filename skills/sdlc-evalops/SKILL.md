---
name: sdlc-evalops
description: Manage AI eval assets across skill, agent, workflow, RAG, and project targets. Use when the user wants to create eval cases, define coverage for a target's quality dimensions, capture real failures for regression, manage a golden dataset, export to Promptfoo, or run eval. Triggers include: building an eval suite, capturing a regression case, running eval for a target, defining quality coverage, managing an inbox/golden case pipeline, managing target workspaces under .ai/evals/targets/, or phrases like 评测体系, 评估用例, 回归测试, eval case, golden dataset, coverage matrix. Do NOT use for debugging a single code failure (use systematic-debugging), writing unit tests (use test-driven-development), or one-off model comparisons without durable case management.
compatibility: Requires filesystem access for reading/writing .ai/evals/ directory, bash for promptfoo eval, Python for scripts/export-promptfoo.py, and access to the target's source. Uses qa-ai-architecture for evaluator design discussions and brainstorming for coverage exploration when available.
---

# EvalOps Skill

Manage AI eval assets as version-controlled, tool-neutral artifacts. The skill defines three natural-language workflows (create-eval-suite, capture-regression, run-regression) backed by seven internal commands. EvalOps root is `.ai/evals/` with target-scoped workspaces under `.ai/evals/targets/<target-id>/`. Internal case schema is the source of truth; Promptfoo exports are derived via `scripts/export-promptfoo.py`.

## When to Use

- The user asks to build an eval suite for a skill, agent, workflow, RAG pipeline, or code project AI task.
- The user wants to capture a real failure as a regression case.
- The user wants to run eval after modifying a target.
- The user asks to define or review quality coverage dimensions.
- The user asks to manage inbox/golden cases (triage, promote, reject).
- The user asks to export eval cases to Promptfoo.
- The user needs to initialize or manage `.ai/evals/` or a target workspace under `.ai/evals/targets/<target-id>/`.

## When Not to Use

- The user is debugging a single code failure — use `systematic-debugging`.
- The user wants to write unit tests for code — use `test-driven-development`.
- The user is doing one-off model comparison without needing durable case management.
- The user wants to create, modify, or distribute a skill itself — use `meta-skill-lifecycle-governance`.

## EvalOps Root and Global Manifest

The EvalOps root is `.ai/evals/` at the project root. The old root `evals/` is NOT a long-term source of truth; it is migration input only.

`.ai/evals/manifest.yaml` is the global registry and policy surface. It declares:

- `schema_version`: current EvalOps schema version
- `targets`: list of registered targets with id and workspace path
- `default_export_policy`: how Promptfoo exports are derived
- `default_assertion_policy`: deterministic assertion preference and llm-rubric policy
- `report_policy`: where reports live and required reporting fields
- `platform_directories`: runtime directories (declared when consumed by scripts; default is empty)
- `model_matrix_path`: path to the model matrix schema file

## Target Workspaces and Target Manifest

Each AI behavior target gets a workspace at `.ai/evals/targets/<target-id>/`. The workspace contains:

- `manifest.yaml`: declares target id, type, source paths, canonical case directories, coverage file, Promptfoo export outputs, report directory, assertion policy, and export freshness inputs
- `coverage.yaml`: quality dimensions and required coverage for the target
- `cases/inbox/`, `cases/accepted/`, `cases/rejected/`, `cases/golden/`: case lifecycle state
- `exports/promptfoo/`: generated Promptfoo files (derived, not canonical)
- `reports/`: eval outputs and final golden eval summaries

The target manifest makes `scripts/export-promptfoo.py <target-id>` self-contained: it locates canonical golden cases, injects source files, and writes exports without scanning unrelated targets.

## Interaction Model

The skill exposes three high-level natural-language workflows. The LLM orchestrates them from user intent. The seven internal commands (init, define-coverage, capture, generate-cases, triage, promote, run) are capabilities, not required CLI input.

### Workflow 1: create-eval-suite

Trigger: user wants to build an eval suite for a target.

```
1. Check if .ai/evals/ is initialized; if not, run init first.
2. Determine target-id from context: `<target-type>.<name>`.
3. Check if .ai/evals/targets/<target-id>/coverage.yaml exists and `review.reviewed_by_user` is true.
4. If missing or unreviewed: enter coverage brainstorming (define-coverage).
5. Once coverage is reviewed: generate candidate cases into inbox.
6. Present candidate summary to user.
7. Ask: continue iterating, accept selected, or stop?
8. Triage accepted candidates.
9. Promote selected to golden (requires explicit user confirmation).
10. Run `scripts/export-promptfoo.py <target-id>` to generate Promptfoo exports.
11. Run golden eval and summarize.
```

### Workflow 2: capture-regression

Trigger: user reports a failure or unexpected behavior from a target.

```
1. Extract input, actual output, and expected behavior from conversation context.
2. Ask user: "Should I capture this as a regression case for <target-id>?"
3. If confirmed: write to `.ai/evals/targets/<target-id>/cases/inbox/<case-id>.yaml`.
4. Optionally offer to triage accept (not golden).
5. Remind: promote is a separate step for golden.
```

### Workflow 3: run-regression

Trigger: user modified a target and wants to run eval.

```
1. Locate target-id from user context or scan `.ai/evals/manifest.yaml`.
2. Verify `.ai/evals/targets/<target-id>/cases/golden/` has cases.
3. Export Promptfoo configs via `scripts/export-promptfoo.py <target-id>`.
4. Run `promptfoo eval -c <config-path>`.
5. Save run report to `.ai/evals/targets/<target-id>/reports/<run-id>/`.
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

## Pre-Implementation Eval Asset Gate

For any new AI-behavior target, or any change that expands a target's behavior scope, eval assets MUST be prepared before implementation begins.

**Required before implementation:**
- `.ai/evals/targets/<target-id>/coverage.yaml` exists.
- `coverage.review.reviewed_by_user` is true.
- Critical/high-risk dimensions have at least one accepted or golden case.
- For release-bound work, critical cases SHOULD be promoted to golden before implementation starts.

**Exceptions:**
- Pure deterministic code changes may use TDD only and do not require eval assets.
- Existing targets with stable golden datasets may skip case generation and run existing golden cases.
- Newly discovered failures during implementation or verification should be captured to inbox and triaged later; they do not need to block initial implementation.

## Directory Structure

The skill maintains assets under `.ai/evals/` at the project root:

```
.ai/evals/
  manifest.yaml           # global target registry and default policy
  model-matrix.yaml       # model matrix schema (runner deferred)
  targets/
    <target-id>/
      manifest.yaml       # target metadata, source paths, export/report policy
      coverage.yaml       # quality coverage matrix
      cases/
        inbox/
        accepted/
        rejected/
        golden/
      exports/
        promptfoo/         # generated Promptfoo configs (derived)
      reports/             # eval run outputs and summaries
```

`target-id` format: `<target-type>.<name>`. Examples:
- `skill.sdlc-orchestrator`
- `skill.research-general`
- `agent.contract-review`
- `workflow.repository-memory-sync`
- `rag.customer-support`
- `project.checkout-api`

## Data Models

### Global Manifest

`.ai/evals/manifest.yaml` declares the EvalOps schema version, all registered targets, and default policies.

### Target Manifest

`.ai/evals/targets/<target-id>/manifest.yaml` declares:
- `target_id`, `target_type`, description
- `source_paths`: list of source files injected into Promptfoo prompts at export time
- `canonical_case_directories`: paths to inbox, accepted, rejected, golden directories
- `coverage_file`: path to coverage matrix
- `promptfoo_export_outputs`: directory and file paths for generated exports
- `report_directory`: where eval run outputs are stored
- `assertion_policy`: deterministic assertion preference and llm-rubric allowance
- `export_freshness_inputs`: which inputs affect export freshness (golden cases, source paths, templates, coverage)

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

### Model Matrix Schema

`.ai/evals/model-matrix.yaml` defines the schema contract for future multi-model validation:

- `models`: named model entries with provider and config
- `environments`: where evals can run
- `target_selection`: which targets to include by default
- `run_policy`: sequential/parallel, fail_fast, timeout, retry_count

The full multi-model matrix runner is deferred. This schema exists so future work has a stable contract.

## Session Eval vs Promptfoo Eval

This skill distinguishes two evaluation modes:

### Session Eval

Interactive evaluation during development. Captures real failures, drafts candidate cases, reviews coverage, and requires human confirmation before promotion to golden. Session eval is NOT a substitute for final Promptfoo golden eval when implementation changes affect AI behavior.

### Promptfoo Eval

Generated evaluation using `scripts/export-promptfoo.py <target-id>`. Derives Promptfoo configs from canonical golden cases, injects target skill source, and runs deterministic exports. Promptfoo eval SHALL run canonical golden exports when implementation changes affect an AI behavior target. If the runner is unavailable, the blocked dependency MUST be reported explicitly.

## Assertion Policy

### Deterministic Assertions Preferred

Canonical cases SHOULD use deterministic assertions: `contains`, `not-contains`, `regex`, structural checks, explicit tool-use checks, or exact-value checks where appropriate.

### No Global Assertion Pollution

Promptfoo exports MUST NOT rely on hidden global assertions (`defaultTest.assert`) that silently affect every target. Shared templates may define structure, but assertions that determine pass/fail belong in canonical cases or explicit target policy.

### llm-rubric Requires Explicit Configuration

`llm-rubric` assertions in canonical cases MUST explicitly configure rubric text. Unconfigured `llm-rubric` assertions (missing rubric text) are prohibited. Generated Promptfoo exports SHALL NOT contain unconfigured `llm-rubric` assertions. The target manifest's `assertion_policy.allow_llm_rubric` gate determines whether the export script generates llm-rubric assertions for that target.

## Reports Policy

Eval run outputs and final summaries live under `.ai/evals/targets/<target-id>/reports/`.

The final golden eval report summary for an EvalOps-gated change SHALL include:
- Target id
- Case counts (total, passed, failed)
- Export freshness status
- Eval command used
- Pass/fail result count
- Report path
- Any blocked runner dependency (if applicable)

## Commands

Seven internal commands back the three workflows. The LLM selects and chains them; users may also invoke them directly.

### init

Initialize `.ai/evals/` directory at the project root.

**When**: first evalops usage in a project, or user explicitly asks.

**Produces**:
- `.ai/evals/manifest.yaml`
- `.ai/evals/model-matrix.yaml` (with default opencode-go provider)
- `.ai/evals/targets/`
- `scripts/export-promptfoo.py`
- `scripts/run-promptfoo-eval.py`

**Rules**:
- Do NOT create cases during init.
- Do NOT auto-scan project targets.
- Do NOT migrate old root `evals/` automatically; migration is a separate step.

### define-coverage

Define or iterate a coverage matrix for a target.

**Input**: target-id, target type, source path, user's quality concerns.

**Produces**: `.ai/evals/targets/<target-id>/coverage.yaml`

**Process**:
1. Ensure `.ai/evals/targets/<target-id>/` exists. If not, create the target workspace.
2. Brainstorm with user: functional dimensions, quality attributes, edge cases, output constraints.
3. Identify critical failures — what specific failures are unacceptable?
4. Write coverage with `review.status: draft`.
5. Ask user to confirm. On confirmation, set `review.reviewed_by_user: true`.
6. If user says "refine later", keep draft but warn that generate-cases is gated on review.

### capture

Capture a failure, edge case, or positive example into inbox.

**Input**: target-id, input text, expected behavior, actual output (optional), severity, case_type, source.

**Produces**: `.ai/evals/targets/<target-id>/cases/inbox/<case-id>.yaml`

**Rules**:
- Default status is inbox.
- Do NOT write to golden — even for "high-value" cases.
- Proactive suggestion allowed; writing to disk requires user confirmation.
- Extract input/actual from conversation context where possible.

### generate-cases

Generate candidate eval cases from a coverage matrix.

**Input**: target-id, optional focus dimensions, optional count.

**Produces**: `.ai/evals/targets/<target-id>/cases/inbox/candidate-*.yaml`

**Hard Gate**:
- If `.ai/evals/targets/<target-id>/coverage.yaml` does not exist: stop, run define-coverage first.
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

**Produces**: `.ai/evals/targets/<target-id>/cases/golden/<case-id>.yaml`

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
- `.ai/evals/targets/<target-id>/exports/promptfoo/promptfooconfig.yaml` (via export script)
- `.ai/evals/targets/<target-id>/exports/promptfoo/cases.yaml`
- `.ai/evals/targets/<target-id>/reports/<run-id>/summary.md`
- `.ai/evals/targets/<target-id>/reports/<run-id>/promptfoo-output.json`
- `.ai/evals/targets/<target-id>/reports/<run-id>/failures.yaml`

**Steps**:
1. Read golden cases from `.ai/evals/targets/<target-id>/cases/golden/`.
2. Run `scripts/run-promptfoo-eval.py <target-id>` which chains: export freshness → `promptfoo eval -c <config-path> -o <reports-dir>/promptfoo-output.json` → parse output → write `summary.md` and `failures.yaml`.
3. Summarize for user: pass count, fail count, failed case ids with severity.
4. If failures: suggest capture for new patterns. Do NOT auto-fix.

**Rules**:
- Only run golden cases. Do not run inbox or accepted.
- Export is derived via `scripts/export-promptfoo.py`; internal case YAML remains source of truth.
- Do not modify target, case, or coverage on failure.

## Promptfoo Export Mapping

When `scripts/export-promptfoo.py <target-id>` generates Promptfoo exports from canonical golden cases:

| Internal Field | Promptfoo Mapping |
|----------------|-------------------|
| `input` | `vars.input` in test case |
| `expected.must_include` | `assert.type: contains` |
| `expected.must_not_include` | `assert.type: not-contains` |
| `expected.rubric` (configured) | `assert.type: llm-rubric` |
| `evaluators.rule_based.contains` | `assert.type: contains` |
| `coverage / severity / case_type` | test metadata |

Supported assertions: `contains`, `not-contains`, `regex`, `llm-rubric` (configured only), `javascript`.

Export generation reads source files declared in the target manifest and injects them into the prompt. Golden cases describe scenario input and expected behavior; they SHALL NOT duplicate the full target skill source.

The `--check` flag (`scripts/export-promptfoo.py <target-id> --check`) exits non-zero when exports are missing or stale, enabling CI-style freshness validation.

## Promptfoo Provider Configuration

### Provider Source

Promptfoo provider configuration is generated from `.ai/evals/model-matrix.yaml`, not hardcoded in the export script. The first model listed in `models[]` is the default. Its `promptfoo` block is used verbatim to generate the `providers` section of `promptfooconfig.yaml`.

The preferred provider is Promptfoo's built-in OpenAI-compatible provider (`openai:chat:<model>`) with `apiBaseUrl` and `apiKeyEnvar`. This avoids distributing a custom provider script to every project.

### OpenCode-Go Endpoint Contract

The opencode-go OpenAI-compatible endpoint REQUIRES these provider config fields:

| Field | Value | Notes |
|-------|-------|-------|
| `apiBaseUrl` | `https://opencode.ai/zen/go/v1` | Base URL only — do NOT append `/chat/completions` |
| `apiKeyEnvar` | `OPENCODE_GO_API_KEY` | Promptfoo reads the key from the env var |
| `headers.Accept-Encoding` | `identity` | Prevents `TypeError: terminated` from Node/undici decompress interceptor |

The `Accept-Encoding: identity` header is REQUIRED. Without it, the endpoint may return a compressed response that triggers a bug in Promptfoo/Node's decompress pipeline, causing every eval case to fail with `TypeError: terminated` in 2-3 seconds regardless of timeout settings.

### Target Provider vs Grader Provider

The `providers` block configures the eval target model (the model being evaluated). The `defaultTest.options.provider` block configures the grader model used for `llm-rubric` assertions. They may differ.

For opencode-go models, the target model may be any model reachable via the endpoint. The grader model should be one with stable structured/JSON output (e.g., GLM, Qwen, Kimi).

Do not use reasoning-oriented models (e.g., DeepSeek V4 Pro) as graders — they may output text in `reasoning_content` rather than body `content`, causing Promptfoo's `llm-rubric` to fail JSON extraction.

Generated example (target: deepseek-v4-pro, grader: glm-5.1):

```yaml
providers:
  - id: openai:chat:deepseek-v4-pro
    label: opencode-go/deepseek-v4-pro
    config:
      apiBaseUrl: https://opencode.ai/zen/go/v1
      apiKeyEnvar: OPENCODE_GO_API_KEY
      headers:
        Accept-Encoding: identity
      temperature: 0
      max_tokens: 4096
defaultTest:
  options:
    provider:
      id: openai:chat:glm-5.1
      config:
        apiBaseUrl: https://opencode.ai/zen/go/v1
        apiKeyEnvar: OPENCODE_GO_API_KEY
        headers:
          Accept-Encoding: identity
        temperature: 0
        max_tokens: 4096
```

The `defaultTest.options.provider` block is the grader for `llm-rubric` assertions.

### API Key Rules

- The API key MUST come from the `OPENCODE_GO_API_KEY` environment variable.
- Promptfoo reads the key via the `apiKeyEnvar` config; do not hardcode the value.
- API keys MUST NOT be written into any repository file — not in `.ai/evals/model-matrix.yaml`, not in generated exports, not in case files.

### Manual Smoke Test

`opencode run --model opencode-go/deepseek-v4-pro "hello"` may be used as a manual smoke test to verify the model is reachable.

### Eval Command

#### Canonical Runner (recommended)

```bash
export OPENCODE_GO_API_KEY=<key>
python scripts/run-promptfoo-eval.py <target-id>
```

This chains export freshness, `promptfoo eval` with `-o` report output, and structured `summary.md`/`failures.yaml` writing under `.ai/evals/targets/<target-id>/reports/<run-id>/`.

#### Raw Promptfoo Command (fallback)

```bash
export OPENCODE_GO_API_KEY=<key>
RUN_ID="<target-id>-$(date -u +%Y%m%dT%H%M%SZ)"
promptfoo eval \
  -c .ai/evals/targets/<target-id>/exports/promptfoo/promptfooconfig.yaml \
  -o .ai/evals/targets/<target-id>/reports/${RUN_ID}/promptfoo-output.json \
  --max-concurrency 1 \
  --no-cache
```

The `-o` flag is required to write repo-pinned reports. Without it, results go to Promptfoo's local store (`~/.promptfoo/promptfoo.db`) and are not traceable in the repository.

## Hard Rules

These rules override any contextual ambiguity. Violating them produces an incorrect eval pipeline.

1. **Coverage Matrix is the planning layer.** Without a user-reviewed coverage matrix, do not generate cases.
2. **AI-generated cases MUST enter inbox first.** Never write directly to accepted or golden.
3. **Golden Dataset MUST require human confirmation.** Promote only after user explicitly approves each case.
4. **Coverage MUST be user-reviewed before candidate generation.** If `review.reviewed_by_user` is not true, stop and require review.
5. **Promptfoo exports are derived artifacts, not source of truth.** Internal case YAML is canonical. Use `scripts/export-promptfoo.py` to derive Promptfoo configs.
6. **Eval failure MUST NOT trigger automatic fixes in MVP.** Failure may be caused by the target, the case, the expected, the evaluator, the context, or model variance.
7. **capture defaults to inbox.** Even if the user calls it "regression-critical", it goes to inbox. Triage and promote are separate gates.
8. **Global assertion pollution is prohibited.** Promptfoo exports MUST NOT add hidden `defaultTest.assert` that applies to all targets. Assertions belong in canonical cases or target policy.
9. **Unconfigured llm-rubric is prohibited.** If a case uses `llm-rubric`, it MUST explicitly configure rubric text. Empty rubric assertions SHALL NOT be exported.
10. **Session eval is not a substitute for Promptfoo golden eval.** Session eval captures and reviews cases; Promptfoo eval runs canonical golden exports. Final golden eval is required for EvalOps-gated AI behavior changes.

## Workflow Integration

### With Superpowers Skills

- `brainstorming`: use for coverage exploration and case design discussions.
- `test-driven-development`: use for deterministic code behavior verification; this skill covers AI behavior.
- `verification-before-completion`: before claiming work complete, report whether eval was run and whether eval assets existed before implementation.

### With Skill Lifecycle Governance

`meta-skill-lifecycle-governance` is a repository skill lifecycle governance capability, not a Superpowers core workflow. It can require `evalops run` during EVALUATE-IN-REPO and require critical golden eval pass before RELEASE.

### With sdlc-orchestrator

The orchestrator gates new AI skill development and material AI behavior changes through EvalOps:
1. Identify the AI behavior target.
2. Require EvalOps coverage definition before implementation unless the user explicitly confirms an exception.
3. Require human confirmation before promoting drafted cases to golden.
4. Route implementation through the selected OpenSpec or Superpowers path.
5. Require final golden eval or a clearly reported blocked eval state before claiming completion.

### With OpenSpec

**For a new AI-behavior target or behavior-scope expansion:**

```
openspec propose
→ brainstorming
→ evalops define-coverage
→ evalops generate-cases
→ evalops triage
→ evalops promote critical golden cases
→ openspec design → spec → tasks
→ apply + TDD where applicable
→ evalops run
→ openspec verify
→ memory sync
→ archive
```

**For an existing target with reviewed coverage and golden cases:**

```
openspec propose
→ inspect existing coverage and golden cases
→ update coverage/cases if behavior scope changed
→ apply + TDD where applicable
→ scripts/export-promptfoo.py <target-id>
→ evalops run
→ capture new failures to inbox if found
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

## Skill-Owned Templates

These templates are bundled with the skill package (`skills/sdlc-evalops/templates/`). They are **not** runtime assets under `.ai/evals/templates/` (that directory is deferred until EvalOps scripts consume it).

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
