## ADDED Requirements

### Requirement: OpenSpec CLI initialization
`sdlc-openspec-init` SHALL detect whether OpenSpec is initialized at the project root and delegate to the OpenSpec CLI when it is missing.

#### Scenario: OpenSpec is already initialized
- **WHEN** `openspec/config.yaml` exists at the project root
- **THEN** the skill SHALL report OpenSpec as already initialized and skip CLI init

#### Scenario: OpenSpec is not initialized
- **WHEN** no OpenSpec configuration exists at the project root
- **THEN** the skill SHALL invoke OpenSpec CLI initialization

#### Scenario: No OpenSpec change is created automatically
- **WHEN** the skill initializes OpenSpec via CLI
- **THEN** the skill SHALL NOT automatically create an OpenSpec change

### Requirement: sdd-plus-superpowers schema installation
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

### Requirement: Schema bundled as template
The `sdd-plus-superpowers` schema files SHALL be bundled in `skills/sdlc-openspec-init/templates/sdd-plus-superpowers/` and SHALL match the canonical source at this repository's `openspec/schemas/sdd-plus-superpowers/`.

#### Scenario: Template files are complete
- **WHEN** the template directory `templates/sdd-plus-superpowers/` is inspected
- **THEN** it SHALL contain `schema.yaml` and `templates/` matching the canonical source

### Requirement: Dry-run support
`sdlc-openspec-init` SHALL support dry-run mode that reports planned actions without modifying files.

#### Scenario: Dry-run on uninitialized project
- **WHEN** dry-run mode is invoked on a project with no OpenSpec or schema
- **THEN** the skill SHALL report planned actions (init OpenSpec, install schema) without modifying files

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
