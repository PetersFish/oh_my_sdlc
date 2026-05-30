## ADDED Requirements

### Requirement: Auto-create high-confidence child module memory
`sdlc-repository-memory-sync` SHALL automatically create child module memory for child candidates whose confidence score is higher than 7.

#### Scenario: High-confidence child module is auto-created
- **WHEN** child discovery returns a new child candidate with score greater than 7
- **THEN** memory sync SHALL create a child module memory file, update `discovery-prefs.json` with `status: accepted`, and include the child in the rebuilt index

#### Scenario: Auto-created child module records parent reference
- **WHEN** memory sync creates a child module memory file
- **THEN** the child memory SHALL record its parent module reference and use a nested path under `modules/<parent>/`

### Requirement: Present medium-confidence child candidates interactively
`sdlc-repository-memory-sync` SHALL present medium-confidence child candidates interactively before writing pending review entries.

#### Scenario: Medium-confidence child candidate requires interaction
- **WHEN** child discovery returns a new child candidate with score from 5 through 7
- **THEN** memory sync SHALL present the candidate to the user with Accept, Reject, Merge, and Save as proposed options before writing it to review state

#### Scenario: Save as proposed writes review queue item
- **WHEN** the user chooses Save as proposed for a medium-confidence child candidate
- **THEN** memory sync SHALL write an open review queue item and SHALL NOT create a formal child module memory file

### Requirement: Reject or ignore low-confidence child candidates
`sdlc-repository-memory-sync` SHALL not create formal memory for low-confidence child candidates whose score is lower than 5.

#### Scenario: Low-confidence implementation detail is rejected
- **WHEN** child discovery returns a low-confidence child candidate with negative implementation-detail signals
- **THEN** memory sync SHALL skip formal memory creation and MAY record the rejection reason in `discovery-prefs.json`

### Requirement: Update parent module routing map
`sdlc-repository-memory-sync` SHALL update a parent module's child routing map when child modules are created, accepted, merged, or rejected.

#### Scenario: Parent routing map includes new child
- **WHEN** a child module is created beneath a parent module
- **THEN** memory sync SHALL update the parent module memory with a child routing entry pointing to the child memory file

#### Scenario: Parent module remains broad summary
- **WHEN** child modules exist beneath a parent module
- **THEN** the parent module SHALL retain boundary and routing information rather than duplicating all child module details

### Requirement: Generate actionable child module content
`sdlc-repository-memory-sync` SHALL generate child module memory content that includes actionable navigation fields for agents.

#### Scenario: Child module includes navigation sections
- **WHEN** memory sync creates a child module memory file
- **THEN** the file SHALL include sections for when to load, key files, entry points, tests, related specs, and known pitfalls when evidence is available
