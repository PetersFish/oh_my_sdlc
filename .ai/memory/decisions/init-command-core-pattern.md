---
id: init-command-core-pattern
type: decisions
title: Init Functions as Command Core + Skill Shell
summary: Mechanical init steps extracted into deterministic Python scripts; skills become interactive wrappers that call commands. Backstopped by verify-foundations.
parent_id: root
sync_status: synced
evidence_mode: commit
linked_commits: [78d5ba3]
linked_specs: []
linked_sessions: []
updated_at: 2026-06-21T16:00:00Z
confidence: high
tags: [init, bootstrap, reliability, skill-design]
deciders: [yuping]
status: accepted
---

## Context

Skill-triggered initialization (e.g., `sdlc-project-bootstrap` Step 4, `sdlc-openspec-init`, `sdlc-repository-memory-init`) relied entirely on LLM following step-by-step instructions in SKILL.md. Mechanical steps (directory creation, file copying, config writing) could be skipped, misordered, or silently fail.

The user observed: "是不是没有命令方式可靠?" — is command-style more reliable than skill-triggered?

## Decision

**Pattern**: Split init into two layers:

1. **Command core** (deterministic Python script): creates directories, copies templates, writes config. Idempotent, testable, CI-runnable. Example: `skills/sdlc-project-bootstrap/scripts/init_foundations.py`
2. **Skill shell** (SKILL.md instructions): asks user for interactive decisions (AI tools, schema, memory-load reminder), then calls the command core. Reports results.

**Backstop**: `workflow.py verify-foundations` — read-only health check of all 6 foundation items. Orchestrator calls it before workflow start. Missing foundations route to appropriate init path.

## Consequences

- `memory-init` already had `init_memory.py` command core — confirmed pattern works
- `openspec-init` wraps `openspec init` CLI — also command-backed
- `bootstrap Step 4` was the gap — now filled by `init_foundations.py`
- `sdlc-orchestrator` SKILL.md now requires foundation verification before workflow start
- `verify-foundations` handles bootstrap edge case: if `workflow.py` itself missing, route directly to bootstrap
