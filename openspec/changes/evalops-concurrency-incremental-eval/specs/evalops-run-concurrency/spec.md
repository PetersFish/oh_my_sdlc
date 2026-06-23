## ADDED Requirements

### Requirement: Run Policy Concurrency Fields
The `model-matrix.yaml` `run_policy` block SHALL support `max_concurrency` and `max_parallel_models` fields to control Promptfoo case-level and matrix model-level concurrency.

#### Scenario: max_concurrency controls Promptfoo case parallelism
- **WHEN** `run_policy.max_concurrency` is set to a value N greater than 0
- **THEN** `run-promptfoo-eval.py` SHALL pass `--max-concurrency N` to the `promptfoo eval` command
- **AND** `run-eval-matrix.py` SHALL pass the same value when generating per-model Promptfoo configs

#### Scenario: max_parallel_models caps matrix model parallelism
- **WHEN** `run_policy.parallel` is true and `run_policy.max_parallel_models` is set to M
- **THEN** the matrix runner SHALL execute at most M model entries concurrently via `ThreadPoolExecutor`

#### Scenario: Missing concurrency fields use safe fallback
- **WHEN** `run_policy.max_concurrency` is absent from the config
- **THEN** runners SHALL default to `max_concurrency: 1`
- **WHEN** `run_policy.max_parallel_models` is absent and `parallel` is true
- **THEN** the matrix runner SHALL default to `max_parallel_models: 1`

#### Scenario: Templates and live model matrix use moderate defaults
- **WHEN** a new `model-matrix.yaml` template is created or the live `.ai/evals/model-matrix.yaml` is updated for this change
- **THEN** `run_policy` SHALL include `max_concurrency: 3`, `parallel: true`, `max_parallel_models: 2`

### Requirement: Parallel Model Execution in Matrix Runner
The matrix runner SHALL support parallel execution of model entries using `ThreadPoolExecutor` when `run_policy.parallel` is true.

#### Scenario: Sequential execution when parallel is false
- **WHEN** `run_policy.parallel` is false or absent
- **THEN** the matrix runner SHALL execute model entries sequentially in list order

#### Scenario: Parallel execution respects max_parallel_models
- **WHEN** `run_policy.parallel` is true and `max_parallel_models` is M
- **THEN** the matrix runner SHALL use `ThreadPoolExecutor(max_workers=M)` to run up to M model entries concurrently

#### Scenario: Fail-fast stops remaining parallel runs
- **WHEN** `run_policy.fail_fast` is true and a model run fails during parallel execution
- **THEN** the matrix runner SHALL cancel or not start remaining scheduled model runs
- **AND** it SHALL write summaries for completed and failed runs before exiting

#### Scenario: Run index updated once after parallel completion
- **WHEN** multiple model entries run in parallel and all complete
- **THEN** the matrix runner SHALL write a single aggregate entry to the run index after all model runs finish
- **AND** the run index entry SHALL record the matrix run mode and aggregate pass/fail counts

### Requirement: Concurrency Config in Single-Target Runner
The `run-promptfoo-eval.py` script SHALL read concurrency configuration from `.ai/evals/model-matrix.yaml`.

#### Scenario: Single-target runner reads max_concurrency
- **WHEN** `run-promptfoo-eval.py <target-id>` is executed
- **THEN** it SHALL read `run_policy.max_concurrency` from `.ai/evals/model-matrix.yaml`
- **AND** it SHALL pass `--max-concurrency <value>` to `promptfoo eval`

#### Scenario: Single-target runner respects model-matrix provider
- **WHEN** the runner invokes `export-promptfoo.py`
- **THEN** the export SHALL continue to derive the provider from the default model entry in model-matrix.yaml
- **AND** the runner SHALL NOT bypass or replace the export script's provider selection
