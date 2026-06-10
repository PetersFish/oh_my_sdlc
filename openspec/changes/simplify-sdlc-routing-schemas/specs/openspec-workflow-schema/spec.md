## ADDED Requirements

### Requirement: sdd-plus-superpowers Removal
The system SHALL remove `sdd-plus-superpowers` as an active project-local schema and bundled initialization template.

#### Scenario: Active schema files are removed
- **WHEN** this change is implemented
- **THEN** active `sdd-plus-superpowers` schema directories SHALL be removed from project OpenSpec schemas and bundled `sdlc-openspec-init` templates

#### Scenario: Historical archive references are preserved
- **WHEN** archived OpenSpec changes mention `sdd-plus-superpowers`
- **THEN** those historical records SHALL NOT be rewritten solely to remove the old schema name

#### Scenario: Repository default schema no longer uses removed schema
- **WHEN** implementation completes in this repository
- **THEN** `openspec/config.yaml` SHALL NOT set `sdd-plus-superpowers` as the default schema

### Requirement: No Custom Replacement Schema
The system SHALL avoid introducing a replacement project-local schema for this workflow simplification.

#### Scenario: No spec-driven-light schema is added
- **WHEN** this change is implemented
- **THEN** the repository SHALL NOT add a `spec-driven-light` schema under `openspec/schemas/` or `sdlc-openspec-init` templates

#### Scenario: Formal changes use spec-driven
- **WHEN** the orchestrator routes medium or very complex formal changes into OpenSpec
- **THEN** it SHALL use the package-provided `spec-driven` schema

## MODIFIED Requirements

### Requirement: OpenSpec Init Recommended Schema
`sdlc-openspec-init` SHALL recommend the package-provided `spec-driven` schema instead of installing or recommending custom workflow schemas.

#### Scenario: New project initialization does not install custom schemas
- **WHEN** `sdlc-openspec-init` initializes OpenSpec for a project
- **THEN** it SHALL NOT install bundled custom schema templates before listing available schemas

#### Scenario: Schema selection recommends spec-driven
- **WHEN** `sdlc-openspec-init` asks the user to choose a default schema
- **THEN** it SHALL present `spec-driven` as the recommended schema

#### Scenario: Suggested next step uses current schemas
- **WHEN** `sdlc-openspec-init` reports completion
- **THEN** its suggested next steps SHALL reference `spec-driven`, not `sdd-plus-superpowers`
