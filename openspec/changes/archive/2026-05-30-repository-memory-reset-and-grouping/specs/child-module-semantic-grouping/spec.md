## ADDED Requirements

### Requirement: Group child candidates by semantic prefix
When child module candidates under an accepted parent share a common directory name prefix, `sdlc-repository-memory-sync` SHALL group those candidates into a single logical child module rather than creating one memory file per candidate. Grouping SHALL use deterministic prefix signals detected from candidate `name` and `path` fields.

#### Scenario: Siblings share a common prefix
- **WHEN** a parent module `skills/` has child candidates `skills/sdlc-repository-memory-init`, `skills/sdlc-repository-memory-load`, `skills/sdlc-repository-memory-sync`, and `skills/sdlc-openspec-memory-sync`
- **THEN** these candidates SHALL be grouped into a single logical child module (e.g., `modules/skills/memory.md`)

#### Scenario: Siblings share a different common prefix
- **WHEN** a parent module `skills/` has child candidates `skills/transform-algo-render`, `skills/transform-markdown-svg`, `skills/transform-math-formula`, and `skills/transform-xmind`
- **THEN** these candidates SHALL be grouped into a single logical child module (e.g., `modules/skills/transform.md`)

#### Scenario: No common prefix among siblings
- **WHEN** child candidates under the same parent do not share a common prefix
- **THEN** each candidate SHALL be evaluated individually as a standalone child module

### Requirement: Group by domain semantics when prefix is absent
When child candidates do not share a common prefix but are semantically related by domain (determined from `frontmatter_name`, `frontmatter_description`, and path), `sdlc-repository-memory-sync` MAY present a proposed grouping to the user as a medium-confidence group.

#### Scenario: Semantically related without common prefix
- **WHEN** child candidates exist under the same parent but have no shared prefix, yet their frontmatter descriptions reference the same domain
- **THEN** the sync workflow MAY present a medium-confidence grouping proposal to the user

#### Scenario: No detectable semantic relationship
- **WHEN** child candidates have neither a common prefix nor detectable semantic relationship
- **THEN** they SHALL NOT be grouped automatically

### Requirement: Logical child module uses multiple owned_paths
A grouped logical child module memory file SHALL include every grouped candidate's source path in its `owned_paths` field. Each source path SHALL also be recorded in `discovery-prefs.json` with the same `memory_id` and `memory_path` pointing to the grouped memory file.

#### Scenario: Grouped paths in owned_paths
- **WHEN** a logical child module groups `skills/sdlc-repository-memory-init`, `skills/sdlc-repository-memory-load`, and `skills/sdlc-repository-memory-sync`
- **THEN** the memory frontmatter `owned_paths` SHALL list all three paths, and `discovery-prefs.json` SHALL have one entry per path with the same `memory_id`

#### Scenario: Future sync skips grouped candidates
- **WHEN** a subsequent sync discovers the same child candidate paths and each path is already in `discovery-prefs.json` with `status: accepted`
- **THEN** the candidates SHALL be treated as `known` and skipped without re-presentation

### Requirement: High-confidence groups auto-create, medium-confidence groups require user confirmation
Groups formed from deterministic prefix signals (multiple siblings, matching prefix, matching `frontmatter_name`) SHALL be auto-created as child module memory files. Groups formed from weaker semantic signals or single candidates SHALL be presented to the user as medium-confidence candidates.

#### Scenario: High-confidence prefix group auto-created
- **WHEN** four or more child candidates share a common prefix and have matching `frontmatter_name` values
- **THEN** the grouped child module SHALL be created automatically without user confirmation

#### Scenario: Medium-confidence grouping presented interactively
- **WHEN** two or three candidates share a common prefix or have only semantic relationship
- **THEN** the proposed grouping SHALL be presented to the user for confirmation before creating memory files

### Requirement: Grouped module body lists all contained candidates
The body of a grouped logical child module SHALL list all grouped directories, their key files, entry points, and SKILL.md descriptions. The `summary` frontmatter field SHALL describe the domain purpose of the group.

#### Scenario: Grouped module body completeness
- **WHEN** a child module groups `sdlc-repository-memory-init`, `sdlc-repository-memory-load`, `sdlc-repository-memory-sync`, and `sdlc-openspec-memory-sync`
- **THEN** the memory body SHALL contain a child sections table listing each skill with its description, key files, and tests
