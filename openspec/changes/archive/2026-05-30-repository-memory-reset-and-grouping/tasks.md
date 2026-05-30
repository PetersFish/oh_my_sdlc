## 1. Reset Skill

- [x] 1.1 Create `skills/sdlc-repository-memory-reset/SKILL.md` with interactive workflow: detect state, confirm reset (backup/delete/cancel), re-init via `sdlc-repository-memory-init`, prompt for sync, validate, report summary
- [x] 1.2 Implement reset state detection: check `.ai-memory/` existence, report git dirty/clean status for memory files
- [x] 1.3 Implement backup logic: copy `.ai-memory/` to `/tmp/ai-memory-reset-<timestamp>/` when user chooses backup
- [x] 1.4 Implement delete flow with confirmation guard (no auto-delete without user choice)
- [x] 1.5 Wire post-reset re-init: invoke `sdlc-repository-memory-init` workflow after deletion
- [x] 1.6 Wire post-init sync prompt: ask user whether to sync, invoke `sdlc-repository-memory-sync` if chosen
- [x] 1.7 Wire post-reset validation: run `validate_memory.py` and report result
- [x] 1.8 Implement reset summary output: backup path, re-init result, sync ID (if applicable), validation status

## 2. Child Module Semantic Grouping

- [x] 2.1 Add prefix detection logic to sync workflow (step 6e): identify child candidates under the same parent that share a common directory name prefix
- [x] 2.2 Define prefix families for skills taxonomy: `sdlc-repository-memory-*`, `sdlc-openspec-*`, `transform-*`, etc.
- [x] 2.3 Implement grouping judgment: high confidence (>7 score, common prefix, matching frontmatter) auto-creates grouped module; medium confidence (5-7, fewer siblings or semantic-only) presents to user
- [x] 2.4 Implement grouped child module memory file creation: write one `modules/<parent>/<child>.md` with `parent_id`, multiple `owned_paths`, and body listing all grouped candidates with key files and SKILL.md descriptions
- [x] 2.5 Update `discovery-prefs.json` for grouped paths: each grouped source path gets a `module_map` entry with the same `memory_id` and `memory_path`, `parent_id`, and `confirmed_at`
- [x] 2.6 Update `child_modules.py` or add grouping helper to produce grouped memory content from multiple candidates instead of one candidate at a time

## 3. Sync History Skipped Types

- [x] 3.1 Update `sdlc-repository-memory-sync` output template to require a `Skipped` section listing every memory type not updated and the reason
- [x] 3.2 Implement reason generation per type: `architecture` (no candidates / user declined), `decisions` (no candidates / user declined), `pitfalls` (no failure evidence), `specs` (no change ID detected), `evolution` (no stable commit range)
- [x] 3.3 Update sync-history template under `templates/sync-history.md` to include `## Skipped` section

## 4. Integration and Verification

- [x] 4.1 Manual test: run reset with backup on a repo with existing `.ai-memory/`, verify backup path, re-init, prompt for sync, validate
- [x] 4.2 Manual test: run reset without backup, verify `.ai-memory/` is deleted and re-created
- [x] 4.3 Manual test: run sync with semantic grouping on a repo with `skills/` parent, verify grouped child modules (memory, transform) are created with correct `owned_paths`
- [x] 4.4 Manual test: verify sync history includes `Skipped` section with per-type reasons
- [x] 4.5 If existing python test files need updates for grouping or reset behavior, add or modify tests under `tests/`
