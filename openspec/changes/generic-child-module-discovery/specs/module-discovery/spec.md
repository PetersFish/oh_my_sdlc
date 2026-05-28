## ADDED Requirements

### Requirement: Discover child module candidates for accepted parent modules
The `discover_modules.py` workflow SHALL support a child discovery mode that evaluates candidate directories beneath accepted parent modules recorded in `.ai-memory/discovery-prefs.json`.

#### Scenario: Child discovery uses accepted parent paths
- **WHEN** `discovery-prefs.json` contains an accepted module with a filesystem path
- **THEN** child discovery SHALL scan that path for child candidates using the same hidden-directory and exclude-pattern rules as top-level discovery

#### Scenario: Child discovery reports parent linkage
- **WHEN** child discovery emits a candidate beneath an accepted parent module
- **THEN** the candidate metadata SHALL include the parent module identifier and parent filesystem path

### Requirement: Emit child candidate scoring metadata
The module discovery output SHALL include child candidate scoring metadata sufficient for sync to auto-create high-confidence children and present medium-confidence children interactively.

#### Scenario: Child candidate includes score and confidence band
- **WHEN** a child candidate is emitted by discovery
- **THEN** the candidate metadata SHALL include its numeric score, confidence band, positive signals, and negative signals

#### Scenario: Discovery output remains dependency-free
- **WHEN** child discovery runs
- **THEN** it SHALL use only Python standard library modules

### Requirement: Respect existing discovery preferences for child candidates
The module discovery workflow SHALL compare child candidates against `.ai-memory/discovery-prefs.json` and mark them as `new`, `known`, or `previously_rejected` using the same disposition model as top-level candidates.

#### Scenario: Known child candidate is marked known
- **WHEN** a child path is already accepted in `discovery-prefs.json`
- **THEN** child discovery SHALL emit the candidate with disposition `known`

#### Scenario: Previously rejected child candidate is marked previously rejected
- **WHEN** a child path is rejected in `discovery-prefs.json`
- **THEN** child discovery SHALL emit the candidate with disposition `previously_rejected` and the rejection reason
