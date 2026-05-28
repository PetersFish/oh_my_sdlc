## Context

Repository memory currently uses filesystem discovery to identify coarse modules and records user decisions in `.ai-memory/discovery-prefs.json`. This is useful for broad routing, but large accepted modules such as a collection of skills, services, specs, or packages can remain too broad to guide an agent to the specific files, tests, and constraints needed for a task.

The existing discovery model already has the right foundation: structural metadata, accepted/rejected dispositions, persisted preferences, and sync-time index rebuilds. This change extends that model rather than replacing it. Parent modules stay as stable routing boundaries, while child modules provide actionable navigation inside large parents.

## Goals / Non-Goals

**Goals:**

- Discover child module candidates generically under accepted parent modules without hardcoded path names.
- Auto-create high-confidence child modules and send lower-confidence candidates to review.
- Preserve parent modules as summaries and routing maps instead of expanding them into large catch-all documents.
- Enrich index entries so memory load can prefer specific child modules when query terms match child-owned paths, keywords, tests, or specs.
- Keep the implementation deterministic and dependency-free, consistent with the existing scripts.

**Non-Goals:**

- Do not introduce semantic embeddings, vector storage, or external search dependencies.
- Do not remove top-level module discovery or existing discovery preferences.
- Do not require every nested directory to become a child module.
- Do not create unlimited nested module trees; this change targets parent/child module relationships only.
- Do not special-case repository-specific paths such as `skills/` as part of the core rules.

## Decisions

### Decision: Use accepted parent modules as the boundary for child discovery

Child discovery will run only inside modules that are already accepted in `discovery-prefs.json`. This keeps child discovery anchored to a user-approved parent boundary and avoids re-opening the entire repository tree on every sync.

Alternative considered: scan every directory recursively and infer all parent/child relationships in one pass. That would discover more candidates, but it would also increase noise and make it harder to respect prior user decisions.

### Decision: Score child candidates with generic structural signals

The child discovery pass will score candidates using structural signals such as explicit entry markers (`SKILL.md`, `package.json`, `pyproject.toml`, `go.mod`, `pom.xml`, `spec.md`), supporting directories (`scripts/`, `schemas/`, `templates/`, `references/`, `tests/`), test/spec name alignment, file-count thresholds, and path/name consistency. Negative signals include fixture-like names (`assets`, `images`, `fixtures`, `cache`, `tmp`), very low file counts with no entry marker, and deeply nested implementation-detail paths.

Alternative considered: let the LLM decide all child modules from raw directory metadata. That is flexible but less repeatable and makes auto-generation harder to test. A deterministic score gives stable behavior while still allowing review for ambiguous cases.

### Decision: Auto-create only high-confidence child modules

Candidates above a high-confidence threshold will be created automatically. Scores use a 10-point scale: scores higher than 7 are high confidence, scores from 5 through 7 are medium confidence, and scores lower than 5 are low confidence. Medium-confidence candidates will be presented interactively during sync before writing pending review entries. Low-confidence candidates will be ignored or rejected with a recorded reason when they are clearly implementation details.

Alternative considered: require user confirmation for all child modules. That is safer, but it would make memory sync too noisy for repositories with many obvious child units.

### Decision: Store parent/child relationships in both memory and index metadata

Child module memory frontmatter and index entries will include `parent_id`. Child module files will use nested paths under the parent, such as `modules/<parent>/<child>.md`, because that mirrors the hierarchy and keeps related memory files grouped together. Index entries will also include routing-oriented fields such as `owned_paths`, `path_hints`, `keywords`, `test_paths`, and `spec_paths`. Parent module bodies will include a child routing map that points agents to more specific children.

Alternative considered: keep parent/child relationships only in document bodies. That would be readable, but `select_memory.py` currently scores only index fields, so body-only routing would not improve selection quality.

### Decision: Prefer specific child modules during memory load

`select_memory.py` will score enriched fields and prefer a child module over its parent when both match and the child has stronger path, keyword, test, or spec relevance. Parent modules remain fallback results when no specific child matches.

Alternative considered: always load both parent and child. That provides context but wastes the limited default result budget and can crowd out more relevant memory entries.

### Decision: Limit depth to one child level by default

The system will support parent modules and child modules, but not recursive grandchildren by default. Deeper splits require explicit future design or user direction.

Alternative considered: allow arbitrary recursive module hierarchy. That is more general but increases complexity in discovery preferences, index ranking, and user review flows.

## Risks / Trade-offs

- Over-eager auto-generation could create noisy child modules. -> Mitigate with conservative thresholds, negative signals, and review for medium-confidence candidates.
- Parent module summaries could become stale relative to child modules. -> Mitigate by updating parent child-routing maps during sync whenever child modules are created, merged, or rejected.
- Index schema expansion could break validators or tests. -> Mitigate by updating schemas and tests together, and keeping new fields optional for existing entries during migration.
- Query ranking may still miss relevant modules if keywords are sparse. -> Mitigate by deriving keywords from entry markers, owned paths, test paths, spec paths, and frontmatter metadata.
- Dirty-worktree sync may create provisional child modules from uncommitted structure. -> Mitigate by using existing `pending_commit` and reconciliation policies for memory generated from uncommitted snapshots.

## Migration Plan

1. Extend schemas and validators to accept optional child-module index fields and `parent_id`.
2. Extend discovery preferences to record parent/child accepted and rejected decisions without invalidating existing top-level entries.
3. Add child discovery and scoring beneath accepted parent modules.
4. Update sync behavior to auto-create high-confidence child module memory and queue medium-confidence candidates for review.
5. Update index rebuild to include enriched routing fields.
6. Update memory load scoring to use enriched fields and prefer specific children over broad parents.
7. Add tests for high-confidence auto-generation, low-confidence review, parent routing updates, schema validation, and child-preferred selection.

Rollback is straightforward because parent modules remain valid. If child discovery causes noise, disable the child-discovery pass or raise the auto-create threshold while keeping existing parent modules and discovery preferences intact.

## Open Questions

- None at this stage. The confidence bands, medium-confidence interaction behavior, and child module file layout are resolved in the decisions above.
