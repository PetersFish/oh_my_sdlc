---
name: sdlc-repository-memory-init
description: Use when initializing or enabling repository memory, creating `.ai-memory/`, setting up repository-local memory metadata, or adding the optional AGENTS.md memory-load reminder.
license: MIT
---

# Repository Memory Init

One-time initialization of `.ai-memory/` in a repository. Creates the directory structure, manifest, index, review-queue, and gitignore required by the Repository Memory Skill System V2.

## When to use

- A user asks to set up or enable repository memory for a project.
- A user wants to create `.ai-memory/` in a repository that does not yet have one.
- A user asks about initializing memory infrastructure for a repository.
- A user mentions "repository memory" and `.ai-memory/` does not exist yet.

## Required inputs

- Repository root path (defaults to `.` if not provided).

## Workflow

1. **Check for existing initialization.** Look for `.ai-memory/manifest.json` at the repository root.
   - If it exists, report that the repository is already initialized and stop. Do not overwrite.
 2. **Run `init_memory.py`.** If the manifest is missing, execute `scripts/init_memory.py --root <repo-root>` to create:
    - `.ai-memory/` directory with all subdirectories (modules, architecture, decisions, pitfalls, specs, evolution, sync-history, sessions, snapshots, tmp, cache).
    - `.ai-memory/manifest.json` from template.
    - `.ai-memory/index.json` from template.
    - `.ai-memory/review-queue.json` from template.
    - `.ai-memory/discovery-prefs.json` from template (default exclude_patterns, max_depth=5, empty module_map).
    - `.ai-memory/.gitignore`.
    The script preserves any existing files and reports created vs skipped.
3. **Check for root AGENTS.md.** Look for `AGENTS.md` at the repository root.
4. **Ask the user whether to add the memory-load reminder.** Show the text from `templates/AGENTS-memory-block.md`. If the user agrees, append it to the root `AGENTS.md` (creating the file if it does not exist). If the user declines, skip this step.
5. **Output summary.** Report:
   - Which files and directories were created vs skipped.
   - The AGENTS.md status (reminder added, reminder skipped, or user declined).

## Guardrails

- Do NOT modify workflow skills (sync, load, etc.). Init is infrastructure only.
- Do NOT auto-commit to git. The user controls version control.
- Do NOT overwrite an existing manifest, index, or review-queue. If they exist, report and skip.
- Do NOT create memory content files (modules, architecture docs, etc.). That is sync's job.
- Init is rare and explicit. It is not part of every sync cycle.

## Output

After initialization, report:

```
Repository Memory initialized at <repo-root>/.ai-memory/

Created: <list of created files/dirs>
Skipped (already existed): <list of skipped files/dirs>

AGENTS.md: <added memory-load reminder | reminder skipped (user declined) | already present>
discovery-prefs.json: <created | skipped (already existed)>
```