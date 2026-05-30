## Context

Repository memory is currently initialized by `sdlc-repository-memory-init` and synchronized by `sdlc-repository-memory-sync`. The sync workflow can discover broad parent modules and child module candidates, but the current child module implementation maps each candidate directory to one memory file. That works for isolated modules, but it fragments domains where sibling directories are intentionally related, such as `skills/sdlc-repository-memory-init`, `skills/sdlc-repository-memory-load`, and `skills/sdlc-repository-memory-sync`.

Testing the repository memory lifecycle also requires repeated teardown and recreation of `.ai-memory/`. Manual deletion is error-prone because `.ai-memory/` may contain committed files, uncommitted sync state, review queue entries, or prior snapshots. A dedicated reset skill should make this workflow explicit, interactive, and safe.

## Goals / Non-Goals

**Goals:**

- Add a dedicated `sdlc-repository-memory-reset` skill for interactive reset, re-init, optional sync, and validation.
- Keep reset behavior narrow: only `.ai-memory/` is reset, and git commits are never created automatically.
- Improve child module discovery so semantically related sibling directories can be grouped into one logical child module.
- Preserve path-level routing by storing every grouped directory in `owned_paths` and mapping each source path in `discovery-prefs.json`.
- Require sync history to report skipped memory types and reasons, especially for `architecture`, `decisions`, `pitfalls`, `specs`, and `evolution`.

**Non-Goals:**

- Do not redesign repository memory schemas unless existing frontmatter and index fields are insufficient.
- Do not change how `sdlc-repository-memory-init` initializes a missing `.ai-memory/`.
- Do not automatically archive, commit, or restore git-tracked memory files.
- Do not treat every child directory as a required child memory file.

## Decisions

### Decision 1: Implement reset as a separate skill, not an init flag

Reset is destructive while init is intentionally conservative and refuses to overwrite an existing manifest. Keeping reset separate preserves the safety contract of init and makes destructive behavior trigger only when the user asks for reset, re-init, or test lifecycle cleanup.

Alternatives considered:
- Add a reset mode to `sdlc-repository-memory-init`: rejected because it weakens init's one-time setup semantics.
- Make sync auto-reset when requested: rejected because sync should not own destructive teardown.

### Decision 2: Reset defaults to interactive mode

The reset skill will ask before deleting `.ai-memory/` and ask again before running sync after init. It will present at least these reset choices: backup then delete, delete without backup, or cancel. After init, it will present: run sync now or stop after init.

This matches the user's selected default and avoids surprising writes during testing.

Alternatives considered:
- Always reset and sync: faster for tests but too destructive as a default.
- Reset only: safer but less useful for the repeated re-init + sync workflow.

### Decision 3: Backup outside `.ai-memory/` before deletion

When the user chooses backup, reset should copy `.ai-memory/` to a timestamped directory outside the directory being removed, such as `/tmp/ai-memory-reset-<timestamp>/` or another safe workspace-local backup path. Backing up inside `.ai-memory/snapshots/` is not sufficient because the reset deletes `.ai-memory/`.

Alternatives considered:
- Use `.ai-memory/snapshots/`: rejected for reset because it is deleted with `.ai-memory/`.
- Require git before reset: rejected because repository memory can exist in non-git contexts, but git state should still be reported when available.

### Decision 4: Add semantic grouping before child memory creation

Child module discovery should first score child candidates structurally, then group semantically related siblings before creating memory files. Grouping can use deterministic signals first and LLM judgment second:

- Shared prefix families: `sdlc-repository-memory-*`, `transform-*`, `research-*`, `qa-*`, `media-*`, `ops-*`, `integration-*`, `meta-skill-*`.
- Shared parent path and domain terms from `frontmatter_name`, `frontmatter_description`, candidate path, and tags.
- Existing broad parent context, such as `skills`.

The grouped module should be written as a logical child memory file, for example `modules/skills/memory.md`, with `parent_id: skills` and `owned_paths` listing all grouped directories.

Alternatives considered:
- One child memory per directory: simple but creates noisy, low-value memory routing.
- Only broad parent module with no children: concise but loses domain-specific load targets.

### Decision 5: Preserve per-path discovery decisions even when grouped

`discovery-prefs.json` should record every source path in a group. Each path can point to the same `memory_id` and `memory_path`, with a status that represents merge/acceptance into a logical module. This avoids re-presenting grouped paths as new candidates on future syncs while keeping path-level provenance.

No schema change is required if existing fields are used consistently:

- `fs_path`: the source directory path
- `status`: `accepted`
- `memory_id`: the grouped memory id
- `memory_path`: the grouped memory file
- `parent_id`: the accepted parent module id

### Decision 6: Keep medium-confidence groups interactive

High-confidence semantic groups can be auto-created when they have strong deterministic evidence, such as multiple sibling directories with a common prefix and matching frontmatter names. Medium-confidence groups should be presented to the user before writing formal memory or review queue entries. Low-confidence child candidates should be skipped or rejected with explicit reasons.

This preserves the current review policy while avoiding unnecessary fragmentation.

### Decision 7: Sync history must include skipped types

Every sync report should contain a `Skipped` section with memory types not updated and the reason. This is especially important for `architecture` and `decisions`, which are intentionally candidate-only and require user confirmation before formal memory is created. The absence of these entries makes a correct skip look like an omission.

## Risks / Trade-offs

- **Risk: Semantic grouping over-aggregates unrelated skills** -> Mitigation: only auto-group with strong prefix/domain evidence; present medium-confidence groups interactively.
- **Risk: Reset deletes useful uncommitted memory** -> Mitigation: show dirty state and offer backup before deletion; never auto-delete without confirmation.
- **Risk: Discovery preferences become harder to read when many paths map to one memory file** -> Mitigation: use consistent `memory_id`, `memory_path`, and `parent_id` fields for every grouped source path.
- **Risk: Grouped modules hide individual entry points** -> Mitigation: include grouped directories, key files, and entry points in the logical child memory body.
- **Risk: More sync workflow complexity** -> Mitigation: keep grouping logic constrained to child module discovery and avoid changing top-level module discovery.

## Migration Plan

1. Add the `sdlc-repository-memory-reset` skill with an interactive reset workflow.
2. Update `sdlc-repository-memory-sync` documentation to require semantic grouping before child memory creation.
3. Extend `child_modules.py` or add a helper to build grouped child module content from multiple candidates.
4. Update sync-history guidance so skipped memory types and reasons are always reported.
5. Add tests for reset safety behavior, semantic grouping, discovery-prefs mapping, and skipped-type reporting.

Rollback is straightforward: remove the reset skill and revert sync grouping changes. Existing `.ai-memory/` files remain valid because grouped modules use current module frontmatter and index fields.

## Open Questions

- What exact backup location should reset use by default: `/tmp/ai-memory-reset-<timestamp>/` or a repository-local ignored directory?
- Should discovery preferences use a dedicated future status like `merged`, or is `accepted` with shared `memory_id` sufficient for this change?
