## Why

Repository memory currently discovers and indexes only coarse top-level modules, which helps identify broad areas but does not reliably guide agents to the specific files, tests, specs, and pitfalls needed for focused work. Large modules need a generalized child-module mechanism so memory can route from a broad parent area to precise, actionable submodules without hardcoding repository-specific paths.

## What Changes

- Add generalized child module discovery for accepted parent modules that are too broad to serve as actionable navigation units.
- Automatically create high-confidence child modules using structural signals such as entry markers, independent tests, scripts, schemas, templates, references, specs, and path/name alignment.
- Route low-confidence child module candidates through review instead of auto-creating them.
- Keep parent modules as navigation and boundary summaries while child modules carry key files, entry points, tests, related specs, and known pitfalls.
- Extend memory index metadata so selection can prefer specific child modules over broad parent modules when query terms match child paths, keywords, or test/spec hints.
- Avoid hardcoded module splits such as special-casing `skills/`; the same rules should apply to any large accepted module.

## Capabilities

### New Capabilities

- `child-module-discovery`: Discovers, scores, creates, and tracks child module memory entries beneath accepted parent modules using generic structural signals and confidence thresholds.

### Modified Capabilities

- `module-discovery`: Extend module discovery requirements to support parent/child relationships, child candidate scoring, high-confidence auto-generation, and low-confidence review.
- `repository-memory-sync`: Update sync requirements so child module creation, parent routing-map updates, review-queue handling, and discovery preferences are managed during memory sync.
- `repository-memory-load`: Update loading requirements so richer index metadata can rank specific child modules ahead of broad parent modules.

## Impact

- Affects `.opencode/skills/sdlc-repository-memory-sync/SKILL.md` and related sync scripts for module discovery, index rebuild, validation, and discovery preferences.
- Affects `.opencode/skills/sdlc-repository-memory-load/SKILL.md` and `select_memory.py` ranking behavior.
- Affects `.ai-memory/index.json` schema expectations for module entries by adding parent and routing-oriented fields.
- Affects memory file conventions for module documents, especially parent module routing maps and child module actionable navigation sections.
- Requires updates to tests covering module discovery, repository memory sync, and repository memory load behavior.
