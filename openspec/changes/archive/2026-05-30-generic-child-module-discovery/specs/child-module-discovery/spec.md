## ADDED Requirements

### Requirement: Discover child module candidates under accepted parents
The system SHALL discover child module candidates only beneath parent modules that are accepted in `.ai-memory/discovery-prefs.json`.

#### Scenario: Accepted parent is scanned for child candidates
- **WHEN** `discovery-prefs.json` contains an accepted parent module with an owned filesystem path
- **THEN** child module discovery SHALL scan inside that parent path for candidate child modules

#### Scenario: Rejected parent is not scanned for child candidates
- **WHEN** `discovery-prefs.json` marks a module path as rejected
- **THEN** child module discovery SHALL NOT scan that path for child module candidates

### Requirement: Score child candidates with generic structural signals
The system SHALL assign each child module candidate a confidence score on a 10-point scale using generic structural signals rather than repository-specific path rules.

#### Scenario: Entry markers increase confidence
- **WHEN** a child candidate contains an explicit entry marker such as `SKILL.md`, `package.json`, `pyproject.toml`, `go.mod`, `pom.xml`, or `spec.md`
- **THEN** the candidate score SHALL increase based on the entry marker signal

#### Scenario: Supporting structure increases confidence
- **WHEN** a child candidate contains supporting directories such as `scripts/`, `schemas/`, `templates/`, `references/`, or `tests/`
- **THEN** the candidate score SHALL increase based on the supporting structure signal

#### Scenario: Fixture-like paths reduce confidence
- **WHEN** a child candidate path is fixture-like, such as `assets`, `images`, `fixtures`, `cache`, or `tmp`
- **THEN** the candidate score SHALL decrease based on the implementation-detail signal

### Requirement: Classify child confidence bands
The system SHALL classify child module candidates using fixed confidence bands: high confidence for scores higher than 7, medium confidence for scores from 5 through 7, and low confidence for scores lower than 5.

#### Scenario: High-confidence candidate is classified
- **WHEN** a child candidate receives a score greater than 7
- **THEN** it SHALL be classified as high confidence

#### Scenario: Medium-confidence candidate is classified
- **WHEN** a child candidate receives a score of 5, 6, or 7
- **THEN** it SHALL be classified as medium confidence

#### Scenario: Low-confidence candidate is classified
- **WHEN** a child candidate receives a score lower than 5
- **THEN** it SHALL be classified as low confidence

### Requirement: Persist child module decisions
The system SHALL persist child module accepted and rejected decisions in `.ai-memory/discovery-prefs.json` without invalidating existing top-level module decisions.

#### Scenario: Accepted child decision is persisted
- **WHEN** a high-confidence child module is auto-created or a user accepts a child module candidate
- **THEN** `discovery-prefs.json` SHALL record the child path with `status: accepted`, its `memory_id`, its parent module reference, and confirmation metadata

#### Scenario: Rejected child decision is persisted
- **WHEN** a child candidate is rejected as an implementation detail or by user decision
- **THEN** `discovery-prefs.json` SHALL record the child path with `status: rejected` and a rejection reason

### Requirement: Use nested child module memory paths
The system SHALL store child module memory files under nested parent paths using `modules/<parent>/<child>.md` style paths.

#### Scenario: Child module file path mirrors parent hierarchy
- **WHEN** a child module named `memory-sync` is created beneath parent module `skills`
- **THEN** the memory file path SHALL use a nested path such as `modules/skills/memory-sync.md`

### Requirement: Limit child module depth by default
The system SHALL support one child module level beneath a parent module by default and SHALL NOT recursively create grandchildren unless a future change explicitly enables deeper hierarchy.

#### Scenario: Grandchild candidate is not auto-created
- **WHEN** discovery finds a candidate beneath an existing child module
- **THEN** the system SHALL NOT auto-create it as a grandchild module by default
