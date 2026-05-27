---
id: skill-lifecycle-governance
type: module
title: Skill Lifecycle Governance Framework
summary: Governs the lifecycle of personal AI skills across development, repo evaluation, project pilots, project-originated iteration, backporting, release, and multi-CLI distribution. Provides Python scripts for install, verify, compare, and backport operations. Load when creating, improving, piloting, releasing, or distributing a skill across CLI targets.
sync_status: synced
evidence_mode: commit
linked_commits: ['62085d3']
linked_specs: []
linked_sessions: ['2026-05-27-001']
updated_at: 2026-05-27T13:43:32Z
confidence: high
tags: [skills, lifecycle, distribution, cli-targets, backport]
---

# Skill Lifecycle Governance Framework

## Current Understanding

The lifecycle governance framework (`skills/skill-lifecycle-governance/`) manages the full lifecycle of AI skills across multiple CLI environments (OpenCode, Claude, Cursor). It was the foundational commit of this repository (commit 62085d3).

### Scripts

| Script | Purpose |
|---|---|
| `install_skill.py` | Install a skill to target CLI directories |
| `verify_install.py` | Verify skill copies are consistent across CLIs |
| `compare_skill_copy.py` | Compare skill copies for differences |
| `prepare_backport.py` | Prepare backport from deployed skill to canonical |
| `lifecycle_utils.py` | Shared utilities across all scripts |

### CLI Targets

Skills are distributed to three CLI environments:
- `.opencode/skills/` — OpenCode CLI
- `.claude/skills/` — Claude Code CLI
- `.cursor/skills/` — Cursor CLI

Each target gets a full copy of the skill directory with installation metadata (`.skill-install.json`).

### Lifecycle Phases

1. **Development** — Author skill in `skills/<name>/`
2. **Repo Evaluation** — Test with evals in `skills/<name>/evals/`
3. **Project Pilot** — Install to a real project, iterate
4. **Backport** — Bring learnings back to canonical copy
5. **Release** — Freeze version, create release notes
6. **Distribution** — Install to all target CLIs

## Evidence

- First commit (62085d3) introduced the full framework with scripts, templates, and test
- Tests: `tests/test_lifecycle_utils.py`

## Operational Guidance

- Canonical copies live in `skills/` — never edit installed copies directly
- Use `verify_install.py` to check consistency after changes
- Use `prepare_backport.py` when project-originated changes need to flow back to canonical

## Update Notes

- 2026-05-27: First memory sync — documented lifecycle governance framework
