# SDLC Runtime Layout

SDLC skills store runtime state under `.ai/`.

## Canonical Paths

| Runtime area | Canonical path | Legacy fallback |
|---|---|---|
| Repository memory | `.ai/memory/` | `.ai-memory/` |
| Roadmap | `.ai/roadmap/` | `.roadmap/` |

New initialization writes only to canonical paths. Existing projects remain readable through legacy fallback when the canonical path does not exist.

## Manual Migration

Run these commands only after confirming the project does not already have canonical runtime state:

```bash
mkdir -p .ai
mv .ai-memory .ai/memory
mv .roadmap .ai/roadmap
```

If both canonical and legacy directories exist, do not merge automatically. Inspect both directories and decide which one is authoritative.

## Conflict Rule

When both canonical and legacy directories exist, SDLC scripts prefer canonical paths:

- `.ai/memory/` wins over `.ai-memory/`
- `.ai/roadmap/` wins over `.roadmap/`

Legacy directories should be removed only after the user confirms their contents have been migrated or are obsolete.
