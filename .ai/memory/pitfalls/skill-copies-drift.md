---
id: skill-copies-drift
type: pitfalls
title: Distributed Skill Copies Drift from Canonical
summary: Editing `.opencode/skills/<name>/SKILL.md` without syncing to `skills/<name>/SKILL.md` (canonical) or other distributed copies breaks canonical-distributed symmetry and causes test failures.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_specs: []
failure_evidence: [test_failure: test_opencode_copy_matches_canonical was passing at HEAD, broke after isolated .opencode edit]
linked_commits: [78d5ba3]
linked_sessions: []
updated_at: 2026-06-21T16:00:00Z
tags: [skills, distribution, drift, tests]
severity: medium
status: mitigated
---

## Symptom

Modifying `.opencode/skills/sdlc-orchestrator/SKILL.md` (added Foundation Verification section) without updating canonical `skills/sdlc-orchestrator/SKILL.md` caused `test_opencode_copy_matches_canonical` to fail. Same for `sdlc-project-bootstrap/SKILL.md`.

Additionally, new scripts (`sync_templates.py`, `init_foundations.py`) were only placed in `.opencode/skills/sdlc-project-bootstrap/scripts/` — canonical and other distributed copies had no `scripts/` directory at all.

## Root Cause

AGENTS.md lacked a rule about canonical-first skill updates. The workflow encouraged editing `.opencode/` directly since that's where OpenCode loads skills from.

## Mitigation

1. AGENTS.md "Skill Updates Discipline" section: changes MUST start in canonical `skills/<name>/`, then distribute
2. `sync_templates.py --check-distributed` detects canonical↔project-level drift
3. `.githooks/pre-commit` enforces distributed consistency for `sdlc-project-bootstrap` templates
4. All distributed copies now have `scripts/` directory and match canonical content
5. User-level `~/.config/opencode/skills/` entity directories (non-symlinked) must be synced after canonical changes

## Detection

`python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed`
