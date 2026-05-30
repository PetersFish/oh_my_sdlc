# sdlc-repository-memory-load

Read-only selective context hydration for AI agents from repository memory. Loads relevant memory files from `.ai-memory/index.json` and outputs a structured context pack.

## Requirements

### Requirement: Selective memory loading via index
`sdlc-repository-memory-load` SHALL read `.ai-memory/index.json` and select up to 5 relevant memory files based on the current task context, query keywords, tags, path hints, and memory type.

#### Scenario: Loading memory for a specific task
- **WHEN** an agent invokes `sdlc-repository-memory-load` with a task involving "openspec memory sync"
- **THEN** it SHALL read `.ai-memory/index.json`, score entries by keyword and tag relevance, and return up to 5 matching entries

#### Scenario: No matching memory entries
- **WHEN** `sdlc-repository-memory-load` runs but no index entries match the task context
- **THEN** it SHALL return an empty result set with a clear explanation that no relevant memory was found

#### Scenario: More than 5 matching entries
- **WHEN** more than 5 index entries match the task context
- **THEN** `sdlc-repository-memory-load` SHALL return only the top 5 by relevance score

### Requirement: Exclude restricted directories from loading
`sdlc-repository-memory-load` SHALL NOT load or return entries from `.ai-memory/sync-history/`, `.ai-memory/sessions/`, `.ai-memory/snapshots/`, `.ai-memory/tmp/`, `.ai-memory/cache/`, or `.ai-memory/review-queue.json` by default.

#### Scenario: Index contains entries in restricted paths
- **WHEN** `.ai-memory/index.json` contains entries pointing to `sync-history/` or `sessions/`
- **THEN** `sdlc-repository-memory-load` SHALL exclude them from results

#### Scenario: Filtered output excludes review-queue
- **WHEN** `sdlc-repository-memory-load` processes the index
- **THEN** it SHALL NOT include `review-queue.json` in any loading or output

### Requirement: Context pack output format
`sdlc-repository-memory-load` SHALL output a structured context pack containing: Loaded Memory (file paths), Relevant Facts (key facts from loaded files), Constraints (important constraints from memory), and Skipped (categories and reasons for exclusion).

#### Scenario: Generating a context pack
- **WHEN** `sdlc-repository-memory-load` completes loading relevant memory files
- **THEN** it SHALL output a context pack with sections for Loaded Memory, Relevant Facts, Constraints, and Skipped categories

#### Scenario: No memory available
- **WHEN** `sdlc-repository-memory-load` runs and `.ai-memory/index.json` does not exist or is empty
- **THEN** it SHALL output a context pack indicating no repository memory is available

### Requirement: Read-only operation
`sdlc-repository-memory-load` SHALL NOT modify any files under `.ai-memory/` or any other location. It is strictly read-only.

#### Scenario: Load does not write files
- **WHEN** `sdlc-repository-memory-load` runs
- **THEN** it SHALL NOT create, modify, or delete any files

### Requirement: Selective memory script CLI
The `select_memory.py` script SHALL accept `--root` (repository root path), `--query` (search keywords), `--max` (maximum results, default 5), and `--json` (JSON output mode) arguments. It SHALL read the index, score entries, and return selected entries without loading file contents.

#### Scenario: Running select_memory.py with a query
- **WHEN** `python select_memory.py --root . --query "module architecture" --json` is executed
- **THEN** it SHALL read `.ai-memory/index.json`, score entries by query relevance, and output up to the configured maximum entries as JSON

#### Scenario: Missing index file
- **WHEN** `.ai-memory/index.json` does not exist
- **THEN** `select_memory.py` SHALL output an empty result set with an explanation

### Requirement: Memory validation script
The `validate_memory.py` script (shared with `sdlc-repository-memory-sync`) SHALL accept `--root` and `--json` arguments. It SHALL validate manifest, index, review queue, discovery prefs, and memory frontmatter and return validation results.

#### Scenario: Valid memory passes validation
- **WHEN** `python validate_memory.py --root . --json` is run on a valid `.ai-memory/`
- **THEN** it SHALL report all files as valid

#### Scenario: Invalid manifest fails validation
- **WHEN** `manifest.json` is missing required fields
- **THEN** `validate_memory.py` SHALL report specific validation errors

### Requirement: Missing `.ai-memory/` handling
`sdlc-repository-memory-load` SHALL check for `.ai-memory/manifest.json` existence. If it does not exist, `sdlc-repository-memory-load` SHALL inform the user that repository memory is not initialized and suggest running `sdlc-repository-memory-init`.

#### Scenario: Running load on uninitialized repository
- **WHEN** `sdlc-repository-memory-load` runs in a repository without `.ai-memory/`
- **THEN** it SHALL output a message suggesting `sdlc-repository-memory-init` and not fail with an error

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
