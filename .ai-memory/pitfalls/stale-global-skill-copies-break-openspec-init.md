---
id: pitfalls/stale-global-skill-copies-break-openspec-init
type: pitfalls
title: Stale global skill copies bypass OpenSpec init guardrails
summary: If global CLI skill copies are stale, bootstrap/init may run old non-interactive OpenSpec commands and skip config.yaml persistence despite updated repo-local skills.
sync_status: synced
evidence_mode: session_observation
linked_commits: []
linked_specs: [add-project-bootstrap-skill]
linked_sessions: []
updated_at: 2026-05-31T11:10:00Z
confidence: high
tags: [pitfall, openspec, bootstrap, init, skill-distribution]
owned_paths:
  - skills/sdlc-openspec-init/SKILL.md
  - skills/sdlc-project-bootstrap/SKILL.md
  - .opencode/skills/sdlc-openspec-init/SKILL.md
  - .opencode/skills/sdlc-project-bootstrap/SKILL.md
path_hints:
  - ~/.config/opencode/skills/sdlc-openspec-init/SKILL.md
  - ~/.config/opencode/skills/sdlc-project-bootstrap/SKILL.md
  - ~/.claude/skills/sdlc-openspec-init/SKILL.md
  - ~/.claude/skills/sdlc-project-bootstrap/SKILL.md
  - ~/.cursor/skills/sdlc-openspec-init/SKILL.md
  - ~/.cursor/skills/sdlc-project-bootstrap/SKILL.md
keywords: [config.yaml skipped, non-interactive mode, stale global skills, redistribute]
test_paths:
  - tests/test_project_bootstrap_skills.py
spec_paths:
  - openspec/changes/add-project-bootstrap-skill/specs/openspec-init/spec.md
  - openspec/changes/add-project-bootstrap-skill/specs/project-bootstrap/spec.md
---

# Stale global skill copies bypass OpenSpec init guardrails

## Current Understanding

The OpenSpec bootstrap flow can appear "still broken" after a local fix when the active CLI loads global skills from home directories that still contain old SKILL.md content.

## Evidence

- Observed output included: `config.yaml skipped in non-interactive mode`.
- Output lacked the new required OpenSpec result fields (`AI tools`, `Default schema`) that the updated bootstrap contract requires.
- Direct reads confirmed global files under `~/.config/opencode/skills`, `~/.claude/skills`, and `~/.cursor/skills` were stale and still used `openspec init` without tool/schema prompting.

## Operational Guidance

- When fixing OpenSpec bootstrap/init behavior, always sync canonical skill updates to all active global CLI targets, not only repo-local `.opencode/.claude/.cursor` copies.
- Verify all copies with direct file diff before declaring fix complete.
- Re-run bootstrap only after redistribution.

## Known Pitfalls

- Repo-local skill synchronization alone is insufficient if runtime uses global skill paths.

## Update Notes

Recorded during post-verify memory sync for `add-project-bootstrap-skill`.
