## ADDED Requirements

### Requirement: Run Index File
The EvalOps runner scripts SHALL maintain a local run index at `.ai/evals/targets/<target-id>/reports/run-index.json` that records metadata for each eval run.

#### Scenario: Run index is created on first run
- **WHEN** a runner script executes and no run index exists
- **THEN** it SHALL create `reports/run-index.json` with the target id and an empty runs array

#### Scenario: Run index records full run entry
- **WHEN** a full eval run completes for a target
- **THEN** the runner SHALL append an entry to the run index containing run_id, mode "full", Git baseline (HEAD commit or tree hash), timestamp, and report path
- **AND** the entry SHALL record the set of case file names included in the run
- **AND** the entry SHALL record per-case run status for each included case

#### Scenario: Run index records only-new run entry
- **WHEN** an `--only-new` run completes
- **THEN** the runner SHALL append an entry with mode "only-new", the case files that were selected, and the Git baseline used for comparison
- **AND** the entry SHALL record per-case run status for each selected case

#### Scenario: Run index records only-failed run entry
- **WHEN** an `--only-failed` run completes
- **THEN** the runner SHALL append an entry with mode "only-failed", the case files that were rerun, and the failure source (`latest` or `full`)
- **AND** the entry SHALL record per-case run status for each rerun case

#### Scenario: Run index records case run status
- **WHEN** any eval run completes
- **THEN** the run index entry SHALL include per-case run status using values `passed`, `failed`, `skipped`, or `not_run`
- **AND** statuses SHALL correspond to the cases selected for that run mode

#### Scenario: Run index records failure set per run
- **WHEN** any eval run completes with failed cases
- **THEN** the run index entry SHALL include a `failed_cases` array listing the case IDs that failed
- **AND** entries with zero failures SHALL have an empty `failed_cases` array

### Requirement: Only-New Incremental Eval
The `run-promptfoo-eval.py` and `run-eval-matrix.py` scripts SHALL support a `--only-new` flag that runs only golden cases changed since the last full run.

#### Scenario: Only-new selects changed golden cases
- **WHEN** `--only-new` is passed and a prior full run entry exists in the run index with a recorded Git baseline
- **THEN** the runner SHALL use `git diff --name-only <baseline> -- <golden-dir>/` to identify changed case files
- **AND** it SHALL export and run only those golden cases whose files appear in the diff

#### Scenario: Only-new on first run without baseline
- **WHEN** `--only-new` is passed but no prior full run entry exists in the run index
- **THEN** the runner SHALL exit with a message instructing the user to run a full eval first

#### Scenario: Only-new with no changed cases
- **WHEN** `--only-new` runs and Git diff returns no changed golden case files
- **THEN** the runner SHALL print a message indicating no cases need to be run and exit successfully

#### Scenario: Only-new marks export and report as incremental
- **WHEN** an `--only-new` run completes
- **THEN** the generated report summary SHALL indicate the run mode as "only-new"
- **AND** the export freshness check SHALL still validate the subset of exported cases

### Requirement: Only-Failed Retry Eval
The `run-promptfoo-eval.py` and `run-eval-matrix.py` scripts SHALL support a `--only-failed` flag with a mandatory `--failed-from` argument to retry only previously failed cases.

#### Scenario: Only-failed from latest run
- **WHEN** `--only-failed --failed-from latest` is passed
- **THEN** the runner SHALL read the most recent run entry from the run index regardless of mode
- **AND** it SHALL export and run only the golden cases whose IDs appear in that entry's `failed_cases` array

#### Scenario: Only-failed from last full run
- **WHEN** `--only-failed --failed-from full` is passed
- **THEN** the runner SHALL read the most recent entry with mode "full" from the run index
- **AND** it SHALL export and run only the golden cases whose IDs appear in that entry's `failed_cases` array

#### Scenario: Only-failed with no prior failures
- **WHEN** `--only-failed` runs and the referenced run entry has an empty `failed_cases` array
- **THEN** the runner SHALL print a message indicating no failures to retry and exit successfully

#### Scenario: Only-failed when no run index exists
- **WHEN** `--only-failed` is passed but no run index exists
- **THEN** the runner SHALL exit with a message instructing the user to run a full eval first

#### Scenario: Only-failed marks report as incremental
- **WHEN** an `--only-failed` run completes
- **THEN** the generated report summary SHALL indicate the run mode as "only-failed" and the failure source (`latest` or `full`)

### Requirement: Run Mode in Report Summaries
All runner scripts SHALL include the run mode in generated report summaries.

#### Scenario: Summary includes run mode
- **WHEN** a run completes in any mode
- **THEN** the generated `summary.md` SHALL include a `Run Mode` field with value `full`, `only-new`, or `only-failed`

#### Scenario: Only-failed summary includes failure source
- **WHEN** an `--only-failed` run completes
- **THEN** the `summary.md` SHALL also include a `Failure Source` field with value `latest` or `full`
