## ADDED Requirements

### Requirement: Score enriched module index metadata
`sdlc-repository-memory-load` SHALL score enriched index metadata fields including `parent_id`, `owned_paths`, `path_hints`, `keywords`, `test_paths`, and `spec_paths` when selecting relevant memory entries.

#### Scenario: Query matches path hints
- **WHEN** a query contains terms matching a module entry's `path_hints`
- **THEN** `select_memory.py` SHALL increase that entry's relevance score

#### Scenario: Query matches tests or specs
- **WHEN** a query contains terms matching a module entry's `test_paths` or `spec_paths`
- **THEN** `select_memory.py` SHALL increase that entry's relevance score

### Requirement: Prefer specific child modules over broad parents
`sdlc-repository-memory-load` SHALL prefer a matching child module over its broad parent when the child has stronger relevance from owned paths, keywords, test paths, or spec paths.

#### Scenario: Child and parent both match query
- **WHEN** both a parent module and one of its child modules match the same query
- **THEN** `select_memory.py` SHALL rank the child module above the parent if the child has stronger enriched-field relevance

#### Scenario: Parent remains fallback when no child matches
- **WHEN** no child module matches the query
- **THEN** `sdlc-repository-memory-load` MAY return the parent module as the relevant broad context

### Requirement: Preserve read-only loading behavior with child modules
`sdlc-repository-memory-load` SHALL remain read-only when selecting parent or child module memory.

#### Scenario: Loading child module does not write files
- **WHEN** `sdlc-repository-memory-load` selects child module entries
- **THEN** it SHALL NOT create, modify, or delete any memory files, index entries, or discovery preferences
