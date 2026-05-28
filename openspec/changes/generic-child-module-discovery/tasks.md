## 1. Schemas And Data Model

- [x] 1.1 Extend memory frontmatter schema to allow `parent_id` for child module entries.
- [x] 1.2 Extend index schema to allow `parent_id`, `owned_paths`, `path_hints`, `keywords`, `test_paths`, and `spec_paths`.
- [x] 1.3 Extend discovery preferences schema to preserve parent/child accepted and rejected decisions without breaking existing top-level entries.
- [x] 1.4 Update validation logic to accept existing top-level module entries and new child module entries.

## 2. Child Module Discovery

- [x] 2.1 Add child discovery mode beneath accepted parent modules from `.ai-memory/discovery-prefs.json`.
- [x] 2.2 Emit parent linkage metadata for each child candidate.
- [x] 2.3 Implement 10-point structural scoring using entry markers, supporting directories, name/path alignment, file-count signals, and fixture-like negative signals.
- [x] 2.4 Classify child candidates as high (`> 7`), medium (`5-7`), or low (`< 5`) confidence.
- [x] 2.5 Preserve known and previously rejected child dispositions from discovery preferences.
- [x] 2.6 Ensure child discovery remains standard-library only and respects existing hidden-directory and exclude-pattern rules.

## 3. Sync Workflow

- [x] 3.1 Auto-create child module memory files for high-confidence child candidates.
- [x] 3.2 Store child module files using nested paths such as `modules/<parent>/<child>.md`.
- [x] 3.3 Persist accepted child decisions with parent references in `discovery-prefs.json`.
- [x] 3.4 Present medium-confidence child candidates interactively with Accept, Reject, Merge, and Save as proposed options before writing review entries.
- [x] 3.5 Skip or reject low-confidence implementation-detail candidates without creating formal memory.
- [x] 3.6 Update parent module memory with a child routing map when child modules are created, accepted, merged, or rejected.
- [x] 3.7 Generate child module content with when-to-load, key-files, entry-points, tests, related-specs, and known-pitfalls sections when evidence exists.

## 4. Index Rebuild And Loading

- [x] 4.1 Rebuild `.ai-memory/index.json` with enriched child module metadata.
- [x] 4.2 Derive index keywords from child entry markers, owned paths, test paths, spec paths, and frontmatter metadata.
- [x] 4.3 Update `select_memory.py` to score `owned_paths`, `path_hints`, `keywords`, `test_paths`, and `spec_paths`.
- [x] 4.4 Prefer a specific matching child module over its broad parent when enriched-field relevance is stronger.
- [x] 4.5 Preserve parent modules as fallback results when no child module matches.
- [x] 4.6 Verify memory load remains read-only for parent and child module selection.

## 5. Tests And Verification

- [x] 5.1 Add module discovery tests for accepted-parent child scanning and parent linkage metadata.
- [x] 5.2 Add module discovery tests for high, medium, and low confidence scoring bands.
- [x] 5.3 Add sync tests for high-confidence auto-created child modules and nested memory paths.
- [x] 5.4 Add sync tests for medium-confidence interactive handling and Save as proposed review entries.
- [x] 5.5 Add sync tests for parent routing map updates and actionable child module sections.
- [x] 5.6 Add load tests showing enriched metadata ranks a child module above its parent.
- [x] 5.7 Add validation tests for new schema fields and backwards compatibility with existing module entries.
- [x] 5.8 Run the repository test suite and `openspec validate generic-child-module-discovery`.
