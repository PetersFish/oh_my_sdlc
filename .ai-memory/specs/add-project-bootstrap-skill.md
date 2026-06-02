---
id: specs/add-project-bootstrap-skill
type: specs
title: OpenSpec bootstrap and init skill contract
summary: Defines and verifies project bootstrap orchestration and OpenSpec init behavior, including pre-init tool selection, schema recommendation, partial init recovery, and strict summary contract.
sync_status: synced
evidence_mode: spec_reference
linked_commits: []
linked_specs: [add-project-bootstrap-skill]
linked_sessions: []
updated_at: 2026-05-31T11:10:00Z
confidence: high
tags: [openspec, bootstrap, schema, tools, recovery]
owned_paths:
  - openspec/changes/add-project-bootstrap-skill/specs/openspec-init/spec.md
  - openspec/changes/add-project-bootstrap-skill/specs/project-bootstrap/spec.md
path_hints:
  - skills/sdlc-openspec-init/SKILL.md
  - skills/sdlc-project-bootstrap/SKILL.md
keywords: [bootstrap, openspec init, ai tools selection, default schema, config.yaml recovery]
test_paths:
  - tests/test_project_bootstrap_skills.py
spec_paths:
  - openspec/changes/add-project-bootstrap-skill/specs/openspec-init/spec.md
  - openspec/changes/add-project-bootstrap-skill/specs/project-bootstrap/spec.md
---

# OpenSpec bootstrap and init skill contract

## Current Understanding

`add-project-bootstrap-skill` is complete and verified. The effective contract now requires:

- User AI tool selection before running `openspec init`
- Installation of `sdd-plus-superpowers` before schema listing
- `sdd-plus-superpowers` as recommended default schema
- Recovery path when CLI init skips `openspec/config.yaml` in non-interactive mode
- Bootstrap completion guard: do not report complete if OpenSpec result lacks `AI tools` and `Default schema`

## Evidence

- OpenSpec status shows all artifacts done and tasks 36/36 complete.
- `openspec validate add-project-bootstrap-skill` passes.
- Test suite passes including newly added summary-contract tests.

## Operational Guidance

- Use `sdlc-project-bootstrap` for new project foundation setup.
- If OpenSpec output lacks tool/schema selection details, re-run standalone `sdlc-openspec-init` and do not treat bootstrap as complete.
- Keep global and repo-local skill copies synchronized after SKILL.md updates.

## Update Notes

Added during post-verify sync before archiving `add-project-bootstrap-skill`.
