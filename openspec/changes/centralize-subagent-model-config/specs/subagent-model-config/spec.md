## ADDED Requirements

### Requirement: Canonical agent prompts and model config are separated
The repository SHALL define canonical per-agent model profile configuration in `agents/config/model-profiles.yaml`, and canonical `agents/*.md` prompts SHALL remain free of activation-managed `model` and `variant` fields.

#### Scenario: Canonical config template exists for agent model profiles
- **WHEN** agent setup assets are inspected in the repository
- **THEN** `agents/config/model-profiles.yaml` exists as the canonical template for profile and per-agent model assignments

#### Scenario: Canonical prompts stay model-agnostic
- **WHEN** canonical files under `agents/*.md` are distributed or reviewed
- **THEN** their prompt source does not rely on hardcoded activation-managed `model` or `variant` frontmatter

### Requirement: Template sync initializes targets without overwriting effective config
Template sync SHALL copy canonical agent prompts and the canonical model profile template into each target agent directory, SHALL preserve an existing target `config/model-profiles.yaml`, and SHALL treat activation-managed `model` and `variant` differences as non-canonical drift.

#### Scenario: First install initializes prompt files and target config
- **WHEN** agent setup runs against a target that does not yet contain installed agents or config
- **THEN** the target receives canonical agent markdown files and `config/model-profiles.yaml`

#### Scenario: Reinstall preserves local target config
- **WHEN** agent setup runs against a target that already has `config/model-profiles.yaml`
- **THEN** the existing target config is preserved instead of being overwritten by the canonical template

#### Scenario: Canonical drift check ignores activation-managed fields only
- **WHEN** canonical sync check compares an installed target file against the canonical prompt
- **THEN** differences in `model` and `variant` alone do not fail canonical drift detection

### Requirement: Activation renders effective model frontmatter from target config
Activation SHALL resolve each target agent's effective `model` and `variant` from the target `config/model-profiles.yaml`, using agent override before profile/default fallback, and SHALL write those values into the target markdown while preserving all other frontmatter and body content.

#### Scenario: Agent override wins for model selection
- **WHEN** `agents.<agent>.model` is present in the target config
- **THEN** activation writes that model value even if the assigned profile declares a different model

#### Scenario: Variant fallback chain is deterministic
- **WHEN** activation resolves `variant` for a target agent
- **THEN** it uses `agents.<agent>.variant`, otherwise `profiles.<profile>.variant`, otherwise `defaults.variant`, otherwise `medium`

#### Scenario: Activation can insert frontmatter when missing
- **WHEN** a target agent markdown file has no YAML frontmatter
- **THEN** activation inserts valid frontmatter containing the resolved `model` and `variant` while preserving the markdown body

### Requirement: Aggregate setup composes install and activation with safe verification modes
The repository SHALL provide an aggregate setup entrypoint that runs template sync before activation, supports `--check` to report template drift and activation drift, and supports `--dry-run` without mutating target files.

#### Scenario: Aggregate setup produces activated target agents
- **WHEN** the aggregate setup entrypoint runs for a target
- **THEN** canonical prompts are installed before effective `model` and `variant` are rendered into the target markdown

#### Scenario: Aggregate check reports config-render drift
- **WHEN** a target config changes after activation has already rendered markdown
- **THEN** aggregate `--check` fails until activation is rerun or the rendered frontmatter matches the effective config again

#### Scenario: Aggregate dry-run performs no writes
- **WHEN** the aggregate setup entrypoint runs with `--dry-run`
- **THEN** it reports the planned install and activation actions without modifying target files

### Requirement: Bootstrap guidance remains initialization-only
Initialization-time bootstrap guidance SHALL route agent setup through the aggregate script entrypoint and SHALL not redefine `sdlc-project-bootstrap` as a general maintenance skill or introduce a new `sdlc-agent-config` skill in this change.

#### Scenario: Bootstrap guidance uses script entrypoints for initialization
- **WHEN** bootstrap documentation describes enabling project agents
- **THEN** it instructs initialization through the script-based setup flow rather than direct YAML parsing or manual frontmatter editing

#### Scenario: Refresh behavior does not broaden bootstrap scope
- **WHEN** documentation mentions updating agents after effective config changes
- **THEN** it keeps bootstrap initialization-only and treats refresh as a script-routed operation instead of a new durable skill contract
