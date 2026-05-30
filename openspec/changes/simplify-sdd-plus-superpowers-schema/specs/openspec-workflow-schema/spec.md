## ADDED Requirements

### Requirement: Simplified sdd-plus-superpowers artifact flow
The `sdd-plus-superpowers` schema SHALL define only OpenSpec governance artifacts in its artifact flow: `proposal`, `design`, `specs`, and `tasks`.

#### Scenario: Listing schema artifacts
- **WHEN** the `sdd-plus-superpowers` schema is inspected
- **THEN** the artifact list includes `proposal`, `design`, `specs`, and `tasks`
- **AND** the artifact list does not include `brainstorm`, `plan`, or `verify`

### Requirement: Proposal starts the workflow
The `sdd-plus-superpowers` schema SHALL allow `proposal` to be the first artifact created without requiring a durable brainstorming artifact.

#### Scenario: Creating a new change
- **WHEN** a change is created with the `sdd-plus-superpowers` schema
- **THEN** `proposal` is ready as the first artifact
- **AND** no `brainstorm.md` file is required before `proposal.md`

### Requirement: Change entry uses discovery gate
OpenSpec change creation and propose workflows for `sdd-plus-superpowers` SHALL run a discovery gate before writing proposal content.

#### Scenario: Context is insufficient
- **WHEN** the user asks to create or propose a `sdd-plus-superpowers` change without enough scope, motivation, constraints, or design direction
- **THEN** the agent starts interactive brainstorming or exploration before writing proposal content
- **AND** no `brainstorm.md` file is created

#### Scenario: Context is sufficient
- **WHEN** the user provides enough scope, motivation, constraints, and design direction to draft the proposal
- **THEN** the agent may proceed without additional brainstorming questions
- **AND** the agent summarizes the relevant decision context in the proposal or design artifacts
- **AND** no `brainstorm.md` file is created

### Requirement: Tasks include execution guidance
The `tasks.md` template for `sdd-plus-superpowers` SHALL include an `Execution Notes / TDD Notes` section for test-first guidance, verification commands, sequencing constraints, and risk follow-up tasks.

#### Scenario: Generating tasks instructions
- **WHEN** tasks instructions are requested for a `sdd-plus-superpowers` change
- **THEN** the tasks template includes an `Execution Notes / TDD Notes` section
- **AND** the section prompts for test-first work, verification commands, sequencing constraints, and risky tasks

### Requirement: Apply requires governance context
The `sdd-plus-superpowers` apply action SHALL require `proposal`, `specs`, `design`, and `tasks` before implementation can proceed.

#### Scenario: Requesting apply instructions
- **WHEN** apply instructions are requested for a `sdd-plus-superpowers` change
- **THEN** the apply context includes `proposal`, `specs`, `design`, and `tasks`
- **AND** implementation is not represented as depending only on `tasks.md`

### Requirement: Decision-blocking questions stop artifact completion
The `sdd-plus-superpowers` artifact instructions SHALL require unresolved questions that affect scope, requirements, architecture, or task ordering to be resolved interactively before completing an artifact.

#### Scenario: Design has an unresolved architecture question
- **WHEN** an agent is creating an artifact and discovers an unresolved question that changes architecture or scope
- **THEN** the agent pauses to ask the user instead of completing the artifact with that unresolved question
- **AND** only non-blocking risks or follow-ups may remain in the artifact

### Requirement: Bundled schema copies match canonical schema
Bundled `sdd-plus-superpowers` schema templates used by OpenSpec initialization skills SHALL match the canonical schema files under `openspec/schemas/sdd-plus-superpowers/`.

#### Scenario: Installing schema into a new project
- **WHEN** `sdlc-openspec-init` installs the bundled `sdd-plus-superpowers` schema
- **THEN** the installed schema follows the simplified artifact flow and template behavior from the canonical schema
