## MODIFIED Requirements

### Requirement: Child module discovery for accepted parent modules with semantic grouping
For accepted modules that are broad containers, `sdlc-repository-memory-sync` SHALL evaluate child candidates beneath the parent path using generic structural scoring. Use a 10-point scale: scores higher than 7 are high confidence; scores 5-7 are medium confidence; scores lower than 5 are low confidence. Before creating individual child memory files, high-confidence child candidates SHALL be evaluated for semantic grouping by common prefix or domain. Grouped candidates SHALL be consolidated into a single logical child module memory file with multiple `owned_paths`. Child module memory files use `modules/<parent>/<child>.md` paths and include `parent_id`, key files, entry points, tests, related specs, and pitfalls when evidence exists.

#### Scenario: High-confidence candidates grouped by prefix
- **WHEN** four or more high-confidence child candidates under the same parent share a common directory name prefix and have matching `frontmatter_name` values
- **THEN** `sdlc-repository-memory-sync` SHALL create a single grouped logical child module instead of individual child memory files, listing all grouped paths in `owned_paths`

#### Scenario: Medium-confidence grouping presented to user
- **WHEN** child candidates with medium confidence scores share a prefix or domain, or when fewer than four candidates share a prefix
- **THEN** `sdlc-repository-memory-sync` SHALL present the proposed grouping to the user before writing memory files

#### Scenario: No grouping applied to isolated candidates
- **WHEN** a child candidate does not share a prefix or domain with any sibling
- **THEN** `sdlc-repository-memory-sync` SHALL process it as a standalone child module using the existing per-candidate path

#### Scenario: Paths in discovery-prefs map to grouped memory
- **WHEN** grouped child candidates were previously `new`
- **THEN** each source path in `discovery-prefs.json` SHALL be recorded with the grouped `memory_id` and `memory_path`, parent_id, and `status: accepted`

### Requirement: Sync history skipped types reporting
`sdlc-repository-memory-sync` SHALL include a `Skipped` section in every sync history report. For each memory type not updated during a sync run, the section SHALL list the type and the reason it was skipped. Types that are candidate-only (`architecture`, `decisions`) or require specific evidence (`evolution`, `specs`, `pitfalls`) SHALL be listed with the applicable policy reason.

#### Scenario: First sync with no prior evidence
- **WHEN** a first sync has no architecture candidates, no decision candidates, no pitfall evidence, no spec ID, and no stable commit range for evolution
- **THEN** the sync history `Skipped` section SHALL list architecture (no candidates), decisions (no candidates), pitfalls (no failure evidence), specs (no change ID detected), evolution (no stable commit range)

#### Scenario: Sync with partial type updates
- **WHEN** a sync updates sessions, modules, and evolution but has no architecture or decision candidates
- **THEN** the sync history `Skipped` section SHALL list architecture (no candidates) and decisions (no candidates)
