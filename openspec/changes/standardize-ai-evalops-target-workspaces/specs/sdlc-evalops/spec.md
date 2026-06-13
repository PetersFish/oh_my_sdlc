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

#### Scenario: Platform directories use non-underscored names
- **WHEN** global EvalOps platform assets are created
- **THEN** they SHALL use `.ai/evals/templates/`, `.ai/evals/schemas/`, and `.ai/evals/runners/`

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

### Requirement: Reports Policy
The `sdlc-evalops` skill SHALL store eval reports under target workspaces and require final reporting for EvalOps-gated changes.

#### Scenario: Reports are target-scoped
- **WHEN** an eval run produces reports for a target
- **THEN** reports SHALL be stored under `.ai/evals/targets/<target-id>/reports/`

#### Scenario: Final golden eval reporting includes required facts
- **WHEN** an EvalOps-gated change completes or pauses
- **THEN** the final report summary SHALL include target id, case counts, export freshness status, eval command, pass/fail result count when available, report path, and any blocked runner dependency

### Requirement: Model Matrix Schema
The `sdlc-evalops` skill SHALL define a `.ai/evals/model-matrix.yaml` schema contract while deferring full matrix runner implementation.

#### Scenario: Model matrix schema is defined
- **WHEN** `.ai/evals/model-matrix.yaml` is created
- **THEN** it SHALL define schema version, models, providers, environments, target selection, and run policy fields

#### Scenario: Full matrix runner is deferred
- **WHEN** this change is implemented
- **THEN** the system SHALL NOT require a complete multi-model matrix runner for acceptance
- **AND** runner implementation SHALL remain available for a later roadmap item
