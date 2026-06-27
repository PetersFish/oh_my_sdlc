## ADDED Requirements

### Requirement: wrapper-backed modules support explicit provider configuration
The system SHALL allow wrapper-backed modules to select their backend implementation from repository configuration rather than hardcoding the backend in workflow phases, prompts, or ad hoc routing logic.

#### Scenario: provider selection comes from configuration
- **WHEN** a wrapper-backed module needs to choose a backend
- **THEN** it SHALL read the provider name from deterministic repository configuration rather than inferring it from user phrasing, flow type, or prompt prose

#### Scenario: wrapper provider selection is module-scoped
- **WHEN** configuration is defined for multiple wrapper-backed modules
- **THEN** each module SHALL use its own provider key (for example `spec.provider`, `memory.provider`) so one module's backend choice does not implicitly control another's

#### Scenario: provider configuration lives in project-level client directories
- **WHEN** the repository defines wrapper provider configuration
- **THEN** the configuration SHALL live in project-level files under `.opencode/sdlc-providers.yaml`, `.cursor/sdlc-providers.yaml`, and `.claude/sdlc-providers.yaml`

#### Scenario: provider registries are YAML-backed and loaded by code
- **WHEN** wrapper provider resolution is performed
- **THEN** the available providers and capabilities SHALL come from a YAML registry resolved by a Python loader rather than being embedded only in prompt prose

### Requirement: spec wrapper provider is configurable
The system SHALL support a configurable `spec.provider` for the spec wrapper.

#### Scenario: default spec provider is OpenSpec
- **WHEN** `spec.provider` is omitted
- **THEN** the spec wrapper SHALL default to `openspec`

#### Scenario: configured spec provider selects backend
- **WHEN** `spec.provider` is set to a supported provider such as `openspec` or `github/spec-kit`
- **THEN** the spec wrapper SHALL route spec lifecycle actions to that provider's implementation

#### Scenario: spec provider declares supported capabilities
- **WHEN** the spec wrapper evaluates a configured provider
- **THEN** it SHALL verify that the provider supports the required lifecycle capability for the current action, such as create/propose, continue, apply, or archive

#### Scenario: unsupported spec provider action fails closed
- **WHEN** the configured spec provider does not implement the required lifecycle capability
- **THEN** the wrapper SHALL return a structured blocker rather than silently falling back or partially executing a different backend

### Requirement: memory wrapper provider is configurable
The system SHALL support a configurable `memory.provider` for the memory wrapper.

#### Scenario: default memory provider is local
- **WHEN** `memory.provider` is omitted
- **THEN** the memory wrapper SHALL default to the local repository-backed provider

#### Scenario: configured memory provider selects backend
- **WHEN** `memory.provider` is set to a supported provider
- **THEN** the memory wrapper SHALL route memory load and sync operations to that provider's implementation

#### Scenario: memory provider declares supported capabilities
- **WHEN** the memory wrapper evaluates a configured provider
- **THEN** it SHALL verify support for the required capability, such as `load`, `repository_sync`, or `spec_post_archive_sync`

#### Scenario: spec-flow post-archive memory sync uses explicit capability name
- **WHEN** the memory wrapper is asked to perform post-archive sync for a spec-governed lifecycle
- **THEN** it SHALL resolve that operation through the `spec_post_archive_sync` capability rather than through an implementation-specific capability name

#### Scenario: unsupported memory provider action fails closed
- **WHEN** the configured memory provider does not implement the required capability for the current phase or hook
- **THEN** the wrapper SHALL return a structured blocker rather than silently switching to another provider

### Requirement: provider registries are explicit and validated
The system SHALL maintain explicit provider registries or capability maps for configurable wrapper-backed modules.

#### Scenario: unknown provider name fails closed
- **WHEN** configuration names a provider that is not registered for that module
- **THEN** the wrapper SHALL return a structured blocker identifying the unknown provider and the allowed provider names

#### Scenario: provider configuration must be complete enough to execute
- **WHEN** a registered provider requires additional configuration fields or credentials
- **THEN** the wrapper SHALL validate those requirements before execution and return a structured blocker if they are missing

#### Scenario: provider choice does not change workflow semantics
- **WHEN** a wrapper switches between supported providers for the same module
- **THEN** workflow phases, evidence envelope semantics, and gate behavior SHALL remain stable even though the backend implementation changes

#### Scenario: provider configs stay aligned across supported client directories
- **WHEN** provider configuration is distributed for `.opencode`, `.cursor`, and `.claude`
- **THEN** the wrapper system SHALL treat those files as equivalent project-level configuration surfaces for the same provider model
