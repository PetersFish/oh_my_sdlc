# sdlc-evalops

## Purpose

Manage AI eval assets as version-controlled, tool-neutral artifacts. Standardize EvalOps under `.ai/evals/` with target-scoped workspaces, canonical golden cases, derived Promptfoo exports, and structured eval reports.

## Requirements

### Requirement: EvalOps Root and Target Workspace Layout
The `sdlc-evalops` skill SHALL standardize EvalOps assets under `.ai/evals/` with target-scoped workspaces under `.ai/evals/targets/`.

#### Scenario: EvalOps root is `.ai/evals/`
- **WHEN** EvalOps assets are initialized or migrated for this repository
- **THEN** the long-term EvalOps root SHALL be `.ai/evals/`
- **AND** root `evals/` SHALL NOT remain a long-term source of truth

#### Scenario: Target workspace namespace is `targets/`
- **WHEN** an AI behavior target is registered for EvalOps
- **THEN** its workspace SHALL be created under `.ai/evals/targets/<target-id>/`

#### Scenario: Platform directories are limited to consumed runtime assets
- **WHEN** global EvalOps platform assets are created
- **THEN** `platform_directories` in `.ai/evals/manifest.yaml` SHALL be empty when no consumed runtime directory exists
- **AND** `.ai/evals/runners/` SHALL NOT exist when no custom provider is required
- **AND** `.ai/evals/templates/` and `.ai/evals/schemas/` SHALL NOT be required until EvalOps scripts actually consume them

#### Scenario: Reference target workspace exists
- **WHEN** `skill.sdlc-orchestrator` is migrated as the reference target
- **THEN** `.ai/evals/targets/skill.sdlc-orchestrator/` SHALL contain `manifest.yaml`, `coverage.yaml`, `cases/`, `exports/`, and `reports/`

### Requirement: EvalOps Manifests
The `sdlc-evalops` skill SHALL define global and target manifests that make target discovery, export generation, and report policy explicit.

#### Scenario: Global manifest declares targets and defaults
- **WHEN** `.ai/evals/manifest.yaml` is present
- **THEN** it SHALL declare the EvalOps schema version, registered targets, default export policy, default assertion policy, report policy, platform directories, and the model matrix path

#### Scenario: Target manifest declares source and generated artifacts
- **WHEN** `.ai/evals/targets/<target-id>/manifest.yaml` is present
- **THEN** it SHALL declare the target id, target type, target source paths, canonical case directories, coverage file, Promptfoo export outputs, report directory, assertion policy, and export freshness inputs

#### Scenario: Export script uses manifests rather than broad scanning
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/export-promptfoo.py <target-id>` runs
- **THEN** it SHALL resolve the target from `.ai/evals/manifest.yaml` and the target workspace `manifest.yaml`
- **AND** it SHALL NOT depend on scanning unrelated targets for canonical inputs

### Requirement: Canonical Cases and Promptfoo Exports
The `sdlc-evalops` skill SHALL treat canonical golden cases as source artifacts and Promptfoo files as derived exports.

#### Scenario: Golden cases are canonical
- **WHEN** a case is promoted to golden for a target
- **THEN** the canonical case SHALL live under `.ai/evals/targets/<target-id>/cases/golden/`

#### Scenario: Promptfoo export is generated from golden cases
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/export-promptfoo.py <target-id>` runs
- **THEN** it SHALL generate Promptfoo export files under `.ai/evals/targets/<target-id>/exports/promptfoo/` from canonical golden cases

#### Scenario: Export freshness check detects stale outputs
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/export-promptfoo.py <target-id> --check` runs and generated Promptfoo outputs are missing or stale
- **THEN** the command SHALL fail with a clear freshness error

#### Scenario: Export freshness check passes for current outputs
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/export-promptfoo.py <target-id> --check` runs and generated Promptfoo outputs match canonical inputs
- **THEN** the command SHALL exit successfully without rewriting files

### Requirement: Skill Source Injection
The `sdlc-evalops` skill SHALL generate Promptfoo prompts by injecting target source content declared by the target manifest.

#### Scenario: Skill source is injected for reference target
- **WHEN** Promptfoo exports are generated for `skill.sdlc-orchestrator`
- **THEN** the generated prompt SHALL include the current contents of `skills/sdlc-orchestrator/SKILL.md` or the source path declared by the target manifest

#### Scenario: Golden cases avoid duplicating full skill source
- **WHEN** canonical golden cases are authored for a skill target
- **THEN** they SHALL describe scenario input and expected behavior
- **AND** they SHALL NOT duplicate the full target skill source as case-local prompt text

### Requirement: Assertion Policy
The `sdlc-evalops` skill SHALL keep pass/fail assertions explicit, target-local, and deterministic by default.

#### Scenario: Global assertion pollution is prohibited
- **WHEN** Promptfoo export templates or generated configs are created
- **THEN** they SHALL NOT add hidden global assertions that apply to all targets without explicit target or case ownership

#### Scenario: Deterministic assertions are preferred
- **WHEN** canonical cases define pass/fail expectations
- **THEN** they SHOULD use deterministic assertions such as contains, not-contains, regex, structural checks, explicit tool-use checks, or exact-value checks where appropriate

#### Scenario: Unconfigured llm-rubric is prohibited
- **WHEN** a canonical case or target policy uses `llm-rubric`
- **THEN** it SHALL explicitly configure rubric text, grading model, and any required thresholds
- **AND** generated Promptfoo exports SHALL NOT contain unconfigured `llm-rubric` assertions

### Requirement: Session Eval and Promptfoo Eval Boundaries
The `sdlc-evalops` skill SHALL distinguish interactive session evaluation from generated Promptfoo evaluation.

#### Scenario: Session eval captures and reviews cases
- **WHEN** real AI behavior failures or coverage gaps are found during development
- **THEN** session eval SHALL capture candidate cases, map them to coverage, and require review before promotion to golden

#### Scenario: Promptfoo eval runs canonical golden exports
- **WHEN** implementation changes affect an AI behavior target
- **THEN** Promptfoo eval SHALL run generated exports from canonical golden cases or report a blocked runner dependency explicitly
- **AND** the eval command SHALL include `-o <report-path>` to write results to `.ai/evals/targets/<target-id>/reports/<run-id>/promptfoo-output.json`

### Requirement: Reports Policy
The `sdlc-evalops` skill SHALL store eval reports under target workspaces and require final reporting for EvalOps-gated changes.

#### Scenario: Reports are target-scoped
- **WHEN** an eval run produces reports for a target
- **THEN** reports SHALL be stored under `.ai/evals/targets/<target-id>/reports/`

#### Scenario: Final golden eval reporting includes required facts
- **WHEN** an EvalOps-gated change completes or pauses
- **THEN** the final report summary SHALL include target id, case counts, export freshness status, eval command, pass/fail result count when available, report path, and any blocked runner dependency

### Requirement: Eval Runner Script
The `sdlc-evalops` skill SHALL provide a runner script that chains export generation, Promptfoo eval, and structured report writing with configurable concurrency and incremental run support.

#### Scenario: Runner script chains export, eval, and report writing
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/run-promptfoo-eval.py <target-id>` is executed
- **THEN** it SHALL run `<sdlc-evalops-skill-dir>/scripts/export-promptfoo.py <target-id>` first to ensure exports are fresh
- **AND** it SHALL run `promptfoo eval -c <config-path> -o <report-path> --max-concurrency <N> --no-cache` where N is read from `run_policy.max_concurrency` in `.ai/evals/model-matrix.yaml`
- **AND** it SHALL write `summary.md` and `failures.yaml` under `.ai/evals/targets/<target-id>/reports/<run-id>/`
- **AND** it SHALL update `reports/run-index.json` with the run entry

#### Scenario: Runner script reads concurrency from model matrix
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/run-promptfoo-eval.py <target-id>` executes
- **THEN** it SHALL read `.ai/evals/model-matrix.yaml` `run_policy` block
- **AND** it SHALL use `run_policy.max_concurrency` as the `--max-concurrency` value for `promptfoo eval`
- **AND** if `max_concurrency` is absent it SHALL default to 1

#### Scenario: Runner script produces required report files
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/run-promptfoo-eval.py <target-id>` completes
- **THEN** `.ai/evals/targets/<target-id>/reports/<run-id>/` SHALL contain `promptfoo-output.json`, `summary.md`, and `failures.yaml`
- **AND** `summary.md` SHALL include target id, case counts, run mode, export freshness status, eval command, pass/fail result count, and report path

#### Scenario: Runner script uses API key from environment
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/run-promptfoo-eval.py <target-id>` launches `promptfoo eval`
- **THEN** it SHALL pass the `OPENCODE_GO_API_KEY` environment variable to the subprocess
- **AND** it SHALL NOT write the API key value into any file

#### Scenario: Runner script handles eval failure
- **WHEN** `promptfoo eval` exits non-zero
- **THEN** the runner script SHALL exit non-zero and report the error to stderr

### Requirement: Eval Command Documentation
The `sdlc-evalops` skill SHALL document the canonical eval command with the required `-o` flag and reference the runner script.

#### Scenario: Eval command includes -o flag
- **WHEN** the `sdlc-evalops` skill documents the Promptfoo eval command
- **THEN** the command example SHALL include `-o .ai/evals/targets/<target-id>/reports/<run-id>/promptfoo-output.json`

#### Scenario: Runner script is the canonical eval path
- **WHEN** the `sdlc-evalops` skill documents how to run eval
- **THEN** it SHALL reference `<sdlc-evalops-skill-dir>/scripts/run-promptfoo-eval.py <target-id>` as the canonical runner
- **AND** it SHALL include the raw `promptfoo eval` command as a fallback with `-o` flag

### Requirement: Model Matrix Schema
The `sdlc-evalops` skill SHALL define a `.ai/evals/model-matrix.yaml` schema contract while deferring full matrix runner implementation.

#### Scenario: Model matrix schema is defined
- **WHEN** `.ai/evals/model-matrix.yaml` is created
- **THEN** it SHALL define schema version, models, providers, environments, target selection, and run policy fields

#### Scenario: Full matrix runner is implemented
- **WHEN** the `add-eval-matrix-runner` change is applied
- **THEN** the system SHALL provide `<sdlc-evalops-skill-dir>/scripts/run-eval-matrix.py` as the canonical matrix runner
- **AND** the matrix runner SHALL execute golden evals across all configured model entries in `.ai/evals/model-matrix.yaml`

#### Scenario: Promptfoo provider is generated from model matrix
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/export-promptfoo.py <target-id>` generates a `promptfooconfig.yaml`
- **THEN** the providers section SHALL be derived from `.ai/evals/model-matrix.yaml` default model's `promptfoo` block
- **AND** the generated provider SHALL use `openai:chat:<model>` as the id
- **AND** the generated provider SHALL include `apiBaseUrl: https://opencode.ai/zen/go/v1` in config
- **AND** the generated provider SHALL include `apiKeyEnvar: OPENCODE_GO_API_KEY` in config
- **AND** the generated provider SHALL include `headers.Accept-Encoding: identity` in config
- **AND** the generated grader SHALL include `headers.Accept-Encoding: identity` in config
- **AND** the generated config SHALL NOT contain an API key value
- **AND** the `apiBaseUrl` SHALL be the base URL only, without appending `/chat/completions`

#### Scenario: Accept-Encoding identity is required for opencode-go endpoint
- **WHEN** the opencode-go endpoint returns a compressed response and Promptfoo/Node processes it
- **THEN** the `Accept-Encoding: identity` header SHALL be present in every provider and grader config
- **AND** a generated or smoke config that omits `Accept-Encoding: identity` SHALL fail the relevant test suite

#### Scenario: Promptfoo template is a real OpenAI-compatible example
- **WHEN** the Promptfoo config template is distributed
- **THEN** it SHALL use `openai:chat:<<model>>` with `apiBaseUrl`, `apiKeyEnvar`, and `headers.Accept-Encoding: identity` as the example provider
- **AND** it SHALL include a grader provider example with the same contract
- **AND** it SHALL NOT use empty `providers: []`

### Requirement: Smoke Test

The `sdlc-evalops` skill SHALL include a minimal Promptfoo smoke test config that validates the opencode-go OpenAI-compatible provider without requiring actual golden cases.

#### Scenario: Smoke test config is a valid standalone Promptfoo eval
- **WHEN** `.ai/evals/smoke/promptfooconfig.yaml` is used with `promptfoo eval`
- **THEN** it SHALL use `openai:chat:<model>` with `apiBaseUrl`, `apiKeyEnvar`, and `headers.Accept-Encoding: identity`
- **AND** it SHALL contain exactly one test case with a deterministic `contains` assertion

### Requirement: Eval Matrix Runner
The `sdlc-evalops` workflow SHALL provide a matrix runner that executes canonical golden evals across configured model matrix entries.

#### Scenario: Matrix runner reads configured model entries
- **WHEN** `<sdlc-evalops-skill-dir>/scripts/run-eval-matrix.py <target-id>` is executed
- **THEN** it SHALL read `.ai/evals/model-matrix.yaml`
- **AND** it SHALL use `models[]` entries as the provider matrix
- **AND** it SHALL fail with a clear error if no model entries are configured

#### Scenario: Matrix runner executes golden cases only
- **WHEN** the matrix runner runs a target
- **THEN** it SHALL use the target workspace's canonical `cases/golden/` inputs
- **AND** it SHALL NOT run inbox, accepted, or rejected cases

#### Scenario: Matrix runner supports configured target selection
- **WHEN** no explicit target id is provided and `target_selection.default` is `all`
- **THEN** the runner SHALL resolve targets from `.ai/evals/manifest.yaml`
- **AND** it SHALL apply `target_selection.filter_by_type` when configured

### Requirement: Per-Model Promptfoo Config Generation
The matrix runner SHALL generate run-scoped Promptfoo configs for each model entry without mutating canonical exports.

#### Scenario: Per-model config uses current matrix entry
- **WHEN** the runner prepares a Promptfoo config for a model entry
- **THEN** `providers[0]` SHALL be derived from that entry's `promptfoo` block
- **AND** `defaultTest.options.provider` SHALL be derived from that entry's `grader` block when present
- **AND** the config SHALL preserve `headers.Accept-Encoding: identity` when present in the model matrix

#### Scenario: Canonical exports are not mutated
- **WHEN** a matrix run executes multiple model entries
- **THEN** it SHALL NOT rewrite `.ai/evals/targets/<target-id>/exports/promptfoo/` for each model
- **AND** run-scoped Promptfoo files SHALL be written under the matrix report directory

#### Scenario: API keys remain environment references
- **WHEN** per-model configs are generated
- **THEN** they SHALL use `apiKeyEnvar` references from the model matrix
- **AND** they SHALL NOT write raw API key values to any generated file

### Requirement: Matrix Reports
The matrix runner SHALL write structured reports grouped by target and model.

#### Scenario: Per-model report directory is created
- **WHEN** a target/model run completes or fails
- **THEN** the runner SHALL write a per-model report directory under `.ai/evals/targets/<target-id>/reports/<matrix-run-id>/<model-name>/`
- **AND** the directory SHALL contain the Promptfoo output when available
- **AND** the directory SHALL contain a summary with pass/fail/error counts

#### Scenario: Aggregate matrix summary is created
- **WHEN** a matrix run completes
- **THEN** the runner SHALL write an aggregate `summary.md` under `.ai/evals/targets/<target-id>/reports/<matrix-run-id>/`
- **AND** the summary SHALL group results by model
- **AND** the summary SHALL include total, passed, failed, and error counts per model

#### Scenario: Provider metadata is recorded
- **WHEN** a matrix run writes per-model or aggregate summaries
- **THEN** summaries SHALL include configured model metadata from `.ai/evals/model-matrix.yaml`
- **AND** summaries SHALL include observed provider/model metadata when available from generated config or Promptfoo output

### Requirement: Matrix Run Failure Handling
The matrix runner SHALL handle per-model failures according to the model matrix run policy, including cancellation of parallel runs on fail-fast.

#### Scenario: Default matrix run continues after model failure
- **WHEN** a model run fails and `run_policy.fail_fast` is false
- **THEN** the runner SHALL continue to remaining configured model entries
- **AND** it SHALL record the failed model with an error count or failure status

#### Scenario: Fail-fast stops remaining runs including parallel
- **WHEN** a model run fails and `run_policy.fail_fast` is true
- **THEN** the runner SHALL cancel or not start remaining scheduled model runs, including those already submitted to the thread pool
- **AND** it SHALL write summaries for completed and failed runs before exiting

#### Scenario: Matrix run exits non-zero on failures
- **WHEN** one or more model runs fail or return errors
- **THEN** the matrix runner SHALL exit non-zero after writing available reports

### Requirement: Mandatory Triage Interaction After Case Capture

After the `capture-regression` or `capture` workflow writes a case to inbox, the assistant SHALL offer the user triage actions before proceeding to any other task. The assistant SHALL NOT continue to implementation, run eval, or close the interaction without presenting the triage prompt.

#### Scenario: Triage prompt follows capture
- **WHEN** a case is written to `.ai/evals/targets/<target-id>/cases/inbox/` via `capture-regression`
- **THEN** the assistant SHALL present the user with mutually exclusive triage actions: accept, revise, reject, or keep in inbox
- **AND** the assistant SHALL use the `question` tool when available for this interaction

#### Scenario: Triage prompt follows generate-cases
- **WHEN** candidate cases are generated to inbox via `generate-cases`
- **THEN** the assistant SHALL present the case summary and ask the user to select triage actions for each case or the batch
- **AND** the assistant SHALL NOT auto-accept or skip triage even when coverage is reviewed

#### Scenario: Triage is mandatory before other workflow steps
- **WHEN** a case has been captured to inbox
- **THEN** the assistant SHALL NOT proceed to implementation, golden eval, or any downstream workflow without first completing the triage interaction
- **AND** the assistant MAY begin triage within the same message batch that created the inbox case

#### Scenario: Text-based fallback when question tool is unavailable
- **WHEN** the `question` tool is not available and a case is captured
- **THEN** the assistant SHALL present acceptable/reject/revise/keep-in-inbox choices as concise text with numbered options and ask the user to choose explicitly

### Requirement: Separate Golden Promotion Confirmation

After the user selects "accept" for a case, the assistant SHALL separately ask for explicit confirmation before promoting the case to golden. The assistant SHALL NOT treat "accept" as equivalent to "promote to golden."

#### Scenario: Promotion follows acceptance as separate step
- **WHEN** the user accepts a case during triage
- **THEN** the assistant SHALL move the case to `cases/accepted/`
- **AND** the assistant SHALL then ask whether to promote the case to golden with explicit confirmation language ("Promote `<case-id>` to golden?")

#### Scenario: User confirms golden promotion
- **WHEN** the user explicitly confirms golden promotion
- **THEN** the assistant SHALL move the case to `cases/golden/`
- **AND** update the case status to `golden`

#### Scenario: User declines golden promotion
- **WHEN** the user says no or "keep in accepted"
- **THEN** the case SHALL remain in `cases/accepted/`
- **AND** the assistant SHALL NOT promote to golden

### Requirement: Eval Failure Classification and Fix Plan

When golden eval returns failures, the assistant SHALL classify each failure into one of five categories, present a suggested fix plan based on the classification, and require user confirmation before modifying the target or eval assets.

#### Scenario: Failure is classified before any modification
- **WHEN** a golden eval run returns one or more failed cases
- **THEN** the assistant SHALL classify each failure as one of: target-behavior-bug, case-expectation-bug, evaluator-issue, runner-config-issue, or model-variance
- **AND** the assistant SHALL present the classification with evidence from the eval output

#### Scenario: Fix plan requires user confirmation
- **WHEN** the assistant presents a failure classification and suggested fix plan
- **THEN** the assistant SHALL use the `question` tool (when available) to ask the user to confirm the fix plan before modifying the target, case, evaluator, or runner config
- **AND** the assistant SHALL NOT modify any file until the user confirms

#### Scenario: Five failure categories are defined
- **WHEN** classifying an eval failure
- **THEN** the category SHALL be determined as follows:
  - **target-behavior-bug**: The target skill, agent, or prompt output is incorrect; the eval expectation is correct.
  - **case-expectation-bug**: The eval case's `expected` section (rubric, must_include, etc.) is incorrect; the target behavior is correct.
  - **evaluator-issue**: The rubric, grader model, or assertion mechanism produces invalid results (e.g., grader JSON extraction failure, rubric-parsing error).
  - **runner-config-issue**: The Promptfoo config, provider, API key, or environment is misconfigured.
  - **model-variance**: The target model output varies within acceptable semantic range; the case assertion is too brittle.

#### Scenario: Automatic fixes are prohibited on eval failure
- **WHEN** eval failures are detected and classified
- **THEN** the assistant SHALL NOT modify the target skill, case file, evaluator config, or runner config until the user confirms the fix plan
- **AND** this prohibition applies regardless of failure severity

### Requirement: Triage Interaction for generate-cases

When `generate-cases` produces candidate eval cases, the interaction SHALL follow a structured selection workflow before any case is accepted or promoted.

#### Scenario: Candidate summary presented before triage
- **WHEN** candidate cases are generated to inbox
- **THEN** the assistant SHALL present a concise summary listing each case id, its coverage dimensions, and severity
- **AND** the assistant SHALL ask the user to select actions: continue iterating, accept selected, or stop
