## Why

Memory sync testing requires frequent re-initialization of `.ai-memory/`, forcing manual deletion and re-sync each time. No safe, structured mechanism exists for this reset workflow. Additionally, the current child module discovery creates one module per directory, fragmenting logically related skill packages (e.g., all `sdlc-repository-memory-*` skills) into separate memory files instead of a cohesive domain entry — reducing memory load usefulness.

## What Changes

- **New skill `sdlc-repository-memory-reset`**: Safely remove `.ai-memory/`, re-initialize, and optionally sync — with interactive confirmation at each destructive step.
- **Semantic child module grouping in `sdlc-repository-memory-sync`**: When child candidates under an accepted parent share a common prefix or domain, aggregate them into a single logical child module with multiple `owned_paths` rather than creating one memory file per directory.
- Sync history output SHALL include explicit skip reasons for every memory type not updated in a sync run.

## Capabilities

### New Capabilities
- `repository-memory-reset`: Safe `.ai-memory/` reset lifecycle: backup confirmation, directory tear-down, re-init via `sdlc-repository-memory-init`, interactive sync prompt, post-reset validation.
- `child-module-semantic-grouping`: Logical clustering of child module candidates by shared prefix or domain semantics. When multiple sibling directories share a common prefix pattern (e.g., `sdlc-repository-memory-*`, `transform-*`), aggregate them into one child module memory file with a single `parent_id` and multiple `owned_paths`.

### Modified Capabilities
- `repository-memory-sync`: Child module discovery (step 6e) SHALL apply semantic grouping before creating child memory files. Sync history output SHALL enumerate skipped memory types with explicit reasons. (No other existing requirements change.)

## Impact

- New skill file: `skills/sdlc-repository-memory-reset/SKILL.md`
- Modified skill: `skills/sdlc-repository-memory-sync/SKILL.md` (add semantic grouping rules, add skip-reason reporting)
- Modified script: `child_modules.py` may need grouping logic or the grouping is implemented in the LLM sync workflow
- No API contract changes; no breaking changes
- `.ai-memory/sync-history/` format: `Skipped` section now mandatory with per-type reasons
