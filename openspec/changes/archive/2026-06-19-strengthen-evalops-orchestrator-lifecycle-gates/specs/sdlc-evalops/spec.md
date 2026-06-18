## ADDED Requirements

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
