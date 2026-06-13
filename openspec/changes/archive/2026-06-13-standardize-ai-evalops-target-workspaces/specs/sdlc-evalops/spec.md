## ADDED Requirements

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
- **WHEN** `scripts/export-promptfoo.py <target-id>` runs
- **THEN** it SHALL resolve the target from `.ai/evals/manifest.yaml` and the target workspace `manifest.yaml`
- **AND** it SHALL NOT depend on scanning unrelated targets for canonical inputs

### Requirement: Canonical Cases and Promptfoo Exports
The `sdlc-evalops` skill SHALL treat canonical golden cases as source artifacts and Promptfoo files as derived exports.

#### Scenario: Golden cases are canonical
- **WHEN** a case is promoted to golden for a target
- **THEN** the canonical case SHALL live under `.ai/evals/targets/<target-id>/cases/golden/`

#### Scenario: Promptfoo export is generated from golden cases
- **WHEN** `scripts/export-promptfoo.py <target-id>` runs
- **THEN** it SHALL generate Promptfoo export files under `.ai/evals/targets/<target-id>/exports/promptfoo/` from canonical golden cases

#### Scenario: Export freshness check detects stale outputs
- **WHEN** `scripts/export-promptfoo.py <target-id> --check` runs and generated Promptfoo outputs are missing or stale
- **THEN** the command SHALL fail with a clear freshness error

#### Scenario: Export freshness check passes for current outputs
- **WHEN** `scripts/export-promptfoo.py <target-id> --check` runs and generated Promptfoo outputs match canonical inputs
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
The `sdlc-evalops` skill SHALL provide a runner script that chains export generation, Promptfoo eval, and structured report writing.

#### Scenario: Runner script chains export, eval, and report writing
- **WHEN** `scripts/run-promptfoo-eval.py <target-id>` is executed
- **THEN** it SHALL run `scripts/export-promptfoo.py <target-id>` first to ensure exports are fresh
- **AND** it SHALL run `promptfoo eval -c <config-path> -o <report-path> --max-concurrency 1 --no-cache`
- **AND** it SHALL write `summary.md` and `failures.yaml` under `.ai/evals/targets/<target-id>/reports/<run-id>/`

#### Scenario: Runner script produces required report files
- **WHEN** `scripts/run-promptfoo-eval.py <target-id>` completes
- **THEN** `.ai/evals/targets/<target-id>/reports/<run-id>/` SHALL contain `promptfoo-output.json`, `summary.md`, and `failures.yaml`
- **AND** `summary.md` SHALL include target id, case counts, export freshness status, eval command, pass/fail result count, and report path

#### Scenario: Runner script uses API key from environment
- **WHEN** `scripts/run-promptfoo-eval.py <target-id>` launches `promptfoo eval`
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
- **THEN** it SHALL reference `scripts/run-promptfoo-eval.py <target-id>` as the canonical runner
- **AND** it SHALL include the raw `promptfoo eval` command as a fallback with `-o` flag

### Requirement: Model Matrix Schema
The `sdlc-evalops` skill SHALL define a `.ai/evals/model-matrix.yaml` schema contract while deferring full matrix runner implementation.

#### Scenario: Model matrix schema is defined
- **WHEN** `.ai/evals/model-matrix.yaml` is created
- **THEN** it SHALL define schema version, models, providers, environments, target selection, and run policy fields

#### Scenario: Full matrix runner is deferred
- **WHEN** this change is implemented
- **THEN** the system SHALL NOT require a complete multi-model matrix runner for acceptance
- **AND** runner implementation SHALL remain available for a later roadmap item

#### Scenario: Promptfoo provider is generated from model matrix
- **WHEN** `scripts/export-promptfoo.py <target-id>` generates a `promptfooconfig.yaml`
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
