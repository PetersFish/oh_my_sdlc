## MODIFIED Requirements

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
