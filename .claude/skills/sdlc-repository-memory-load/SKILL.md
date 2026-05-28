---
name: sdlc-repository-memory-load
description: Use when starting work in a repository with `.ai-memory/`, continuing previous work, loading repository memory, hydrating context, planning, editing, reviewing, or working on modules with prior repository decisions. Do not use for writing or updating memory.
license: MIT
---

# Repository Memory Load

Read-only selective context hydration for agents. Loads relevant memory from `.ai-memory/index.json` and outputs a structured context pack.

## When to Use

- Before planning, editing, reviewing, or continuing work in a repository
- A user asks to load repo memory, hydrate context, or resume context
- Before OpenSpec workflow steps if `.ai-memory/` exists
- When you need prior decisions, architecture notes, or module context

**Do NOT use for:** Writing or updating memory (use `sdlc-repository-memory-sync` instead).

## Required Inputs

- **Repository root path** (required)
- **Query keywords** (optional, comma-separated)
- **Task context** (optional, helps scoring)
- **Max results** (optional, default 5)

## Workflow

1. **Check manifest.** Look for `.ai-memory/manifest.json` at the repository root. If missing, suggest running `sdlc-repository-memory-init` and stop.
2. **Read index.** Load `.ai-memory/index.json`.
3. **Score entries.** Rank entries by query keywords, tags, path hints, and memory type.
4. **Select top entries.** Take up to `max_results` (default 5).
5. **Exclude paths.** Never load entries from: `sync-history/`, `sessions/`, `snapshots/`, `tmp/`, `cache/`, `review-queue.json`.
6. **Load memory files.** Read the selected entry files.
7. **Output context pack.** Format and return the structured context pack.

## Excluded Paths

Never load these by default:

| Path | Reason |
|------|--------|
| `sync-history/` | Audit log only |
| `sessions/` | Local-only session data |
| `snapshots/` | Internal state |
| `tmp/` | Ephemeral |
| `cache/` | Ephemeral |
| `review-queue.json` | Sync workflow state |

## Context Pack Output Format

```md
# Repository Memory Context

## Loaded Memory
- `.ai-memory/modules/...`
- `.ai-memory/specs/...`

## Relevant Facts
- fact 1
- fact 2

## Constraints
- constraint 1

## Skipped
- sync-history: audit only
- sessions: local-only
- review-queue: sync workflow state only
```

## Guardrails

- Do NOT modify any files under `.ai-memory/` or elsewhere
- Do NOT load excluded paths by default
- Do NOT load more than `max_results` files without explicit user request
- Do NOT treat `pending_commit` memory as stable fact; always note pending status in context pack
- Do NOT assume the repository has memory if `.ai-memory/manifest.json` is missing

## Output

Return the context pack. If no memory exists, report that `.ai-memory/` is not initialized and suggest `sdlc-repository-memory-init`.