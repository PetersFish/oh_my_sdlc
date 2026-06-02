## ADDED Requirements

### Requirement: OpenSpec CLI initialization and tool selection
`sdlc-openspec-init` SHALL detect whether OpenSpec is initialized at the project root, prompt for one or more AI tools with `opencode` as the default, and delegate to the OpenSpec CLI when initialization is missing.

#### Scenario: OpenSpec is already initialized
- **WHEN** `openspec/config.yaml` exists at the project root
- **THEN** the skill SHALL report OpenSpec as already initialized and skip CLI init

#### Scenario: OpenSpec is not initialized
- **WHEN** no OpenSpec configuration exists at the project root
- **THEN** the skill SHALL ask the user to choose one or more AI tools, default to `opencode`, and invoke OpenSpec CLI initialization with `--tools <selected-tools>`

#### Scenario: Multiple AI tools are selected
- **WHEN** the user selects more than one supported AI tool
- **THEN** the skill SHALL pass the selection to `openspec init` as a comma-separated `--tools` value

#### Scenario: No AI tool integration is selected
- **WHEN** the user chooses no AI tool integration
- **THEN** the skill SHALL invoke `openspec init --tools none`

#### Scenario: No OpenSpec change is created automatically
- **WHEN** the skill initializes OpenSpec via CLI
- **THEN** the skill SHALL NOT automatically create an OpenSpec change

#### Scenario: Tool selection prompt precedes CLI init
- **WHEN** the skill detects OpenSpec is not initialized
- **THEN** the skill SHALL prompt the user for tool selection and SHALL NOT execute `openspec init` until the user has provided their tool choice

### Requirement: sdd-plus-superpowers schema installation
`sdlc-openspec-init` SHALL install the `sdd-plus-superpowers` schema into the project when it is missing. The schema SHALL be installed BEFORE listing available schemas so that it appears in the `openspec schemas --json` output.
`sdlc-openspec-init` SHALL install the `sdd-plus-superpowers` schema into the project when it is missing.

#### Scenario: Schema already installed
- **WHEN** `openspec/schemas/sdd-plus-superpowers/` already exists at the project root
- **THEN** the skill SHALL report the schema as already installed and skip installation

#### Scenario: Schema not installed
- **WHEN** `openspec/schemas/sdd-plus-superpowers/` does not exist at the project root
- **THEN** the skill SHALL copy the schema template from `skills/sdlc-openspec-init/templates/sdd-plus-superpowers/` to the project's `openspec/schemas/` directory

#### Scenario: Schema install target directory does not exist
- **WHEN** the `openspec/schemas/` directory does not exist
- **THEN** the skill SHALL create the directory before copying the schema

#### Scenario: Schema installed before listing available schemas
- **WHEN** the skill installs the `sdd-plus-superpowers` schema
- **THEN** the schema installation SHALL complete before the skill runs `openspec schemas --json`, so the newly installed schema appears in the listing

### Requirement: Schema bundled as template
The `sdd-plus-superpowers` schema files SHALL be bundled in `skills/sdlc-openspec-init/templates/sdd-plus-superpowers/` and SHALL match the canonical source at this repository's `openspec/schemas/sdd-plus-superpowers/`.

#### Scenario: Template files are complete
- **WHEN** the template directory `templates/sdd-plus-superpowers/` is inspected
- **THEN** it SHALL contain `schema.yaml` and `templates/` matching the canonical source

### Requirement: Schema discovery and default selection
`sdlc-openspec-init` SHALL list all available OpenSpec schemas with `openspec schemas --json` and ask the user to choose the default schema when one is not already configured.

#### Scenario: Available schemas include project and package schemas
- **WHEN** OpenSpec is initialized and the schema list is requested
- **THEN** the skill SHALL include both project-local schemas such as `sdd-plus-superpowers` and package-provided schemas such as `spec-driven`

#### Scenario: Default schema is not yet configured
- **WHEN** `openspec/config.yaml` exists but does not contain a `schema` value
- **THEN** the skill SHALL present the available schemas and ask the user to choose one as the default

#### Scenario: Default schema is chosen
- **WHEN** the user selects a schema from the available list
- **THEN** the skill SHALL persist the selected schema name in `openspec/config.yaml`

#### Scenario: Existing default schema is preserved
- **WHEN** `openspec/config.yaml` already contains a `schema` value and the user did not request a change
- **THEN** the skill SHALL keep the existing value and skip the schema choice prompt

#### Scenario: sdd-plus-superpowers is the recommended default schema
- **WHEN** the skill presents available schemas for default selection
- **THEN** `sdd-plus-superpowers` SHALL be presented as the recommended or default choice, while still allowing the user to select a different schema

### Requirement: Partial OpenSpec init recovery
`sdlc-openspec-init` SHALL recover from non-interactive CLI init runs that create OpenSpec state without `openspec/config.yaml` by persisting the config when the default schema is chosen.

#### Scenario: OpenSpec directory exists without config
- **WHEN** `openspec/` exists but `openspec/config.yaml` does not exist after CLI init
- **THEN** the skill SHALL treat the project as partially initialized and create `openspec/config.yaml` when persisting the selected default schema

### Requirement: Dry-run support
`sdlc-openspec-init` SHALL support dry-run mode that reports planned actions without modifying files.

#### Scenario: Dry-run on uninitialized project
- **WHEN** dry-run mode is invoked on a project with no OpenSpec or schema
- **THEN** the skill SHALL report planned actions (prompt for AI tools, init OpenSpec, install schema, list schemas, prompt for default schema) without modifying files

#### Scenario: Dry-run on partially initialized project
- **WHEN** dry-run mode is invoked on a project with OpenSpec init but no schema
- **THEN** the skill SHALL report OpenSpec as already initialized and only the schema installation as a planned action

### Requirement: Post-init suggestion
After successful initialization, `sdlc-openspec-init` SHALL suggest the next command for creating an OpenSpec change.

#### Scenario: Suggestion after full init
- **WHEN** OpenSpec and schema initialization complete
- **THEN** the skill SHALL suggest `openspec new change <name> --schema sdd-plus-superpowers`

#### Scenario: Suggestion when schema already present
- **WHEN** both OpenSpec and schema were already initialized
- **THEN** the skill SHALL still suggest creating a change using the available schema

### Requirement: Standalone invocation
`sdlc-openspec-init` SHALL be invocable independently of `sdlc-project-bootstrap`, supporting use cases where only OpenSpec/schema initialization is needed.

#### Scenario: Standalone invocation on new project
- **WHEN** the skill is invoked directly on a project without OpenSpec
- **THEN** the skill SHALL initialize OpenSpec and install the schema without requiring bootstrap

#### Scenario: Standalone invocation to update schema
- **WHEN** the skill is invoked on a project that already has OpenSpec but an older schema version
- **THEN** the skill SHALL detect the outdated schema and offer to update it

### Requirement: Idempotence
Running `sdlc-openspec-init` multiple times on the same project SHALL produce the same end state without overwriting or duplicating existing content.

#### Scenario: Second init run is a no-op
- **WHEN** the skill is run on a project with OpenSpec and schema already initialized
- **THEN** the skill SHALL report all steps as already initialized and make no changes
