---
name: sdlc-repository-memory-reset
description: Safely reset and reinitialize repository memory. Use when testing memory sync workflows, needing to start fresh with `.ai/memory/`, or when the user asks to reset/reinitialize/re-init repository memory. Handles backup, deletion, re-initialization, optional sync, and post-reset validation with interactive confirmation at each destructive step.
license: MIT
---

# Repository Memory Reset

Safely remove `.ai/memory/`, re-initialize infrastructure, and optionally run sync — with interactive confirmation at each destructive step.

For manual path migration from `.ai-memory/` to `.ai/memory/`, follow `docs/sdlc-runtime-layout.md`. Do not merge canonical and legacy directories automatically.

## When to Use

- Testing `sdlc-repository-memory-sync` or `sdlc-repository-memory-init` workflows and needing a clean slate.
- User explicitly asks to reset, reinitialize, or start fresh with repository memory.
- User says "memory reset", "re-init memory", "reset .ai/memory", or describes a reset workflow.
- When `.ai/memory/` is in a broken or inconsistent state and needs recreation.

## Required Inputs

- Repository root path (defaults to `.`).

## Workflow

1. **Detect existing memory state.** Check whether `.ai/memory/manifest.json` exists.
   - If `.ai/memory/` does not exist, report that no repository memory is present and ask whether to run `sdlc-repository-memory-init` instead. STOP if user declines.
   - If `.ai/memory/` exists, check git status for files under `.ai/memory/` and report dirty/clean state.

2. **Confirm reset action.** Present the user with choices:
   - **Backup then delete**: Copy `.ai/memory/` to `/tmp/ai-memory-reset-<YYYYMMDD-HHMMSS>/`, then delete `.ai/memory/`.
   - **Delete without backup**: Delete `.ai/memory/` immediately without creating a backup.
   - **Cancel**: Stop the reset. No changes made.

   If uncommitted changes exist under `.ai/memory/`, highlight this before presenting choices.

3. **Execute deletion.** If the user chose a delete action:
   - If backup was chosen: create the backup directory, copy `.ai/memory/` contents, report backup path.
   - Remove `.ai/memory/` entirely (e.g., `rm -rf .ai/memory/`).

4. **Re-initialize.** Run the `sdlc-repository-memory-init` workflow to recreate `.ai/memory/` with directory structure, manifest, index, review-queue, discovery-prefs, and .gitignore.

5. **Prompt for sync.** Ask the user whether to run `sdlc-repository-memory-sync`:
   - **Run sync now**: Invoke `sdlc-repository-memory-sync` with the current session context.
   - **Stop after init**: Do not run sync. Report that memory has been reset and re-initialized, and sync is available to run separately.

6. **Validate after reset.** Run `validate_memory.py` and report the result. Validation failures SHALL be reported but SHALL NOT block the reset from being considered complete.

7. **Report summary.** Output:
   - Whether backup was created and its path
   - Re-initialization result (created files/dirs, skipped files)
   - Sync result and sync ID (if sync was run)
   - Validation result

## Guardrails

- Do NOT auto-commit to git. The user controls version control.
- Do NOT delete `.ai/memory/` without explicit user confirmation.
- Backup MUST be stored outside `.ai/memory/` (e.g., `/tmp/`) since the reset deletes `.ai/memory/`.
- Do NOT proceed with deletion if the user selects Cancel.
- Never overwrite an existing backup; use timestamped directory names.
- Reset is a test support workflow. In production, use `sdlc-repository-memory-load` and `sdlc-repository-memory-sync` for the normal lifecycle.

## Output

After completion, report:

```
Repository Memory Reset Complete

Backup: <backup path | none (user chose no backup)>
Re-init: <created files/dirs summary>
Sync: <sync ID | not run>
Validation: <valid | N errors>
```
