---
id: multi-cli-skill-distribution
type: architecture
title: Multi-CLI Skill Distribution Architecture
summary: Skills are authored once as canonical copies in skills/ and distributed to multiple CLI targets (.opencode/skills/, .claude/skills/, .cursor/skills/) via the skill-lifecycle-governance install scripts. This avoids duplication of authorship while ensuring each CLI environment has the exact skill files it needs. Load when adding new CLI targets, troubleshooting skill installation, or modifying the distribution pipeline.
sync_status: synced
evidence_mode: commit
linked_commits: ['62085d3']
linked_specs: []
linked_sessions: ['2026-05-27-001']
updated_at: 2026-05-27T13:43:32Z
confidence: high
tags: [architecture, multi-cli, distribution, skills]
---

# Multi-CLI Skill Distribution Architecture

## Current Understanding

This repository distributes AI assistant skills to three CLI environments simultaneously. The architecture follows a hub-and-spoke model where the canonical source (`skills/`) is the single source of truth, and each CLI target receives a complete copy.

### Architecture Diagram

```
skills/<skill-name>/          ← Canonical source (authored here)
    ├── SKILL.md              ← Skill instructions
    ├── SOURCE.md             ← Original/upstream reference
    ├── scripts/              ← Executable scripts
    ├── schemas/              ← JSON schemas
    ├── templates/            ← Output templates
    ├── evals/                ← Evaluation tests
    └── references/           ← Reference docs

        ▼ install_skill.py ▼

.opencode/skills/<name>/      ← OpenCode CLI copy
.claude/skills/<name>/        ← Claude Code CLI copy
.cursor/skills/<name>/        ← Cursor CLI copy
    └── .skill-install.json   ← Install metadata (version, source, timestamp)
```

### Key Principles

1. **Single source of truth**: All authorship happens in `skills/`. Installed copies are never edited directly.
2. **Full copy, not symlinks**: Each CLI gets a physical copy. This avoids cross-filesystem issues and ensures each CLI can operate independently.
3. **Installation metadata**: Each installed copy gets `.skill-install.json` with version, source commit, install timestamp, and target CLI info.
4. **Verification by comparison**: `verify_install.py` and `compare_skill_copy.py` check consistency between canonical and installed copies.
5. **Backport support**: `prepare_backport.py` enables flowing project-originated changes back to the canonical copy.

### CLI Target Differences

| Feature | OpenCode | Claude | Cursor |
|---|---|---|---|
| Skill loading | `skill` tool | `Skill` tool | Via `.cursor/skills/` |
| Commands | `.opencode/commands/` | `.claude/commands/` | `.cursor/commands/` |
| Rules | — | `.claude/rules/` | `.cursor/rules/` |

## Evidence

- First commit (62085d3) established this architecture with `install_skill.py`, `verify_install.py`, `compare_skill_copy.py`
- 27+ skills distributed across three CLI targets
- Test: `tests/test_repository_memory_skill_copies.py` validates consistency

## Operational Guidance

- When creating a new skill, author it in `skills/<name>/` first, then install
- Never edit files in `.opencode/skills/`, `.claude/skills/`, or `.cursor/skills/` directly
- Run `verify_install.py` after any canonical skill changes
- If a project pilot uncovers needed changes, use `prepare_backport.py` to flow them back

## Update Notes

- 2026-05-27: Created from first memory sync — architecture documented from user confirmation
