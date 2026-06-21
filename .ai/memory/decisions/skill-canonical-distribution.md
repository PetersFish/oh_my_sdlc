---
id: skill-canonical-distribution
type: decisions
title: Canonical-First Skill Updates with Multi-CLI Distribution
summary: Skills under skills/ are canonical source of truth. Changes must be made there first, then distributed to project-level and user-level CLI targets.
parent_id: root
sync_status: synced
evidence_mode: commit
linked_commits: [78d5ba3]
linked_specs: []
linked_sessions: []
updated_at: 2026-06-21T16:00:00Z
confidence: high
tags: [skills, distribution, canonical, governance]
deciders: [yuping]
status: accepted
---

## Context

During development, SKILL.md changes were made to `.opencode/skills/` but NOT synced to canonical `skills/` or other distributed copies (`.claude/`, `.cursor/`). This broke `test_opencode_copy_matches_canonical` and similar tests.

The user requested that AGENTS.md enforce: skill updates only in canonical `skills/`, then redistribute to all CLI targets.

## Decision

1. **Canonical is `skills/<name>/`** — this is the single source of truth for all skill content (SKILL.md, scripts/, templates/, schemas/)
2. **Project-level distribution**: `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/` — managed by `sync_templates.py --distribute` (for workflow templates) and `skills/meta-skill-lifecycle-governance/scripts/install_skill.py` (for full skills)
3. **User-level distribution**: paths vary by OS (e.g., `~/.config/opencode/skills/`). Delegate to `meta-skill-lifecycle-governance` skill's DISTRIBUTE action.
4. **Pre-commit enforcement**: `.githooks/pre-commit` ensures template consistency for `sdlc-project-bootstrap` across canonical and all project-level copies
5. **AGENTS.md documents the discipline** — do NOT edit distributed copies directly

## Consequences

- Root `AGENTS.md` "Skill Updates Discipline" section codifies the rules
- `test_sdlc_orchestrator.py::TestOrchestratorDistributedCopies` now passes (was failing due to drift)
- Lifecycle governance scripts backported from `.opencode/` (better version) to `skills/`
- User-level copies of non-symlinked skills must be explicitly synced after canonical changes
