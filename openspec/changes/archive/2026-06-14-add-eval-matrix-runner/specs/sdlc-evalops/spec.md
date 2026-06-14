## ADDED Requirements

### Requirement: Eval Matrix Runner
The `sdlc-evalops` workflow SHALL provide a matrix runner that executes canonical golden evals across configured model matrix entries.

#### Scenario: Matrix runner reads configured model entries
- **WHEN** `scripts/run-eval-matrix.py <target-id>` is executed
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
The matrix runner SHALL handle per-model failures according to the model matrix run policy.

#### Scenario: Default matrix run continues after model failure
- **WHEN** a model run fails and `run_policy.fail_fast` is false
- **THEN** the runner SHALL continue to remaining configured model entries
- **AND** it SHALL record the failed model with an error count or failure status

#### Scenario: Fail-fast stops remaining runs
- **WHEN** a model run fails and `run_policy.fail_fast` is true
- **THEN** the runner SHALL stop scheduling additional model runs
- **AND** it SHALL write summaries for completed and failed runs before exiting

#### Scenario: Matrix run exits non-zero on failures
- **WHEN** one or more model runs fail or return errors
- **THEN** the matrix runner SHALL exit non-zero after writing available reports
