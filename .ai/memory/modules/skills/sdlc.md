---
id: skills/sdlc
type: module
title: SDLC Workflow Skills
summary: SDLC lifecycle management skills covering project bootstrap, OpenSpec init, workflow orchestration and routing, evalops quality gates, roadmap planning, repository memory init/load/sync/reset, and OpenSpec memory sync.
parent_id: skills
sync_status: synced
evidence_mode: discovery
linked_commits: []
linked_specs: [add-project-bootstrap-skill, sdlc-repository-memory-sync, sdlc-repository-memory-load, sdlc-repository-memory-init, sdlc-repository-memory-reset, sdlc-openspec-memory-sync, add-sdlc-roadmap-skill, simplify-sdlc-routing-schemas, standardize-ai-evalops-target-workspaces]
linked_sessions: []
updated_at: 2026-06-13T08:50:00Z
confidence: high
tags: [sdlc, openspec, bootstrap, memory, workflow, orchestration, roadmap, evalops]
owned_paths:
  - skills/sdlc-repository-memory-init
  - skills/sdlc-openspec-init
  - skills/sdlc-project-bootstrap
  - skills/sdlc-repository-memory-load
  - skills/sdlc-repository-memory-reset
  - skills/sdlc-repository-memory-sync
  - skills/sdlc-openspec-memory-sync
  - skills/sdlc-roadmap
  - skills/sdlc-orchestrator
  - skills/sdlc-evalops
path_hints:
  - skills/sdlc-repository-memory-init
  - skills/sdlc-openspec-init
  - skills/sdlc-project-bootstrap
  - skills/sdlc-repository-memory-load
  - skills/sdlc-repository-memory-reset
  - skills/sdlc-repository-memory-sync
  - skills/sdlc-openspec-memory-sync
  - skills/sdlc-roadmap
  - skills/sdlc-orchestrator
  - skills/sdlc-evalops
keywords: [sdlc, bootstrap, openspec, schema, tools, memory, init, load, sync, reset, orchestration, roadmap, evalops]
test_paths:
  - tests/test_evalops_root.py
  - tests/test_evalops_skill.py
  - tests/test_sdlc_orchestrator.py
spec_paths: []
---

# SDLC Workflow Skills

## Current Understanding

Grouped child module for SDLC-related skills sharing the `sdlc-*` prefix. These skills cover project foundation bootstrap, OpenSpec initialization with schema/tool selection, and the full lifecycle of repository memory management.

- **sdlc-repository-memory-init** — One-time `.ai-memory/` infrastructure creation
- **sdlc-openspec-init** — OpenSpec initialization, AI tool selection, schema installation/default persistence, and partial init recovery
- **sdlc-project-bootstrap** — Ordered bootstrap orchestration: AGENTS.md -> OpenSpec/init schema -> repository memory
- **sdlc-repository-memory-load** — Loading repository memory context for sessions
- **sdlc-repository-memory-reset** — Safe deletion and re-initialization of `.ai-memory/`
- **sdlc-repository-memory-sync** — Synchronizing memory after code changes
- **sdlc-openspec-memory-sync** — Post-verify memory sync gate for OpenSpec
- **sdlc-roadmap** — Thin orchestration between long-term product roadmap and single OpenSpec changes
- **sdlc-orchestrator** — Pre-OpenSpec decision layer classifying task complexity and coordinating SDLC gates
- **sdlc-evalops** — AI eval asset management (case creation, golden dataset, Promptfoo export, eval coverage) with Promptfoo Provider Configuration for opencode-go models

## Evidence

Prefix-based semantic grouping of sibling skill directories under `skills/`, plus change-driven updates from `add-project-bootstrap-skill`, `add-sdlc-roadmap-skill`, `simplify-sdlc-routing-schemas`, and `standardize-ai-evalops-target-workspaces`.

## Operational Guidance

Use `sdlc-project-bootstrap` for new-project foundation setup, `sdlc-openspec-init` for standalone OpenSpec/schema setup, `sdlc-repository-memory-load` when starting work, and `sdlc-repository-memory-sync` after changes. Use `sdlc-orchestrator` for initial task routing and workflow selection. Use `sdlc-roadmap` for long-term product planning.

## Key Files

- skills/sdlc-repository-memory-init/scripts/init_memory.py
- skills/sdlc-repository-memory-sync/scripts/detect_state.py
- skills/sdlc-repository-memory-sync/scripts/discover_modules.py
- skills/sdlc-repository-memory-sync/scripts/validate_memory.py
- skills/sdlc-repository-memory-sync/scripts/rebuild_index.py
- skills/sdlc-repository-memory-load/scripts/load_memory.py

## Entry Points

## Tests

## Related Specs

## Known Pitfalls

- Stale global skill copies (for example under `~/.config/opencode/skills`) can silently bypass updated bootstrap/init guardrails even when repo-local copies are current.
- Symptom: bootstrap summary reports `config.yaml skipped in non-interactive mode` and lacks `AI tools`/`Default schema` fields.
- Mitigation: redistribute canonical `skills/sdlc-openspec-init/SKILL.md` and `skills/sdlc-project-bootstrap/SKILL.md` to all active CLI targets (`~/.config/opencode/skills`, `~/.claude/skills`, `~/.cursor/skills`, and repo-local copies).
- **EvalOps/Promptfoo**: Using a reasoning model (DeepSeek V4 Pro) as the `llm-rubric` grader causes JSON extraction failures. Use a stable non-reasoning model (GLM-5.1) instead. See `pitfalls/deepseek-v4-pro-grader-json-extraction-failure`.
- **EvalOps/Promptfoo**: `max_tokens` must account for reasoning overhead. For DeepSeek V4 Pro, `max_tokens=4096` is recommended (2000 was too low). See `pitfalls/reasoning-model-max-tokens-truncation`.
- **EvalOps/Promptfoo**: Exact `contains` assertions on LLM outputs are brittle. Prefer `llm-rubric` for semantics, `contains` only for skill names. See `pitfalls/exact-contains-assertions-brittle`.

## Update Notes

First sync after memory reset. Created from prefix-based child module discovery.
Updated after `add-project-bootstrap-skill`: added bootstrap/init ownership and stale-global-copy pitfall.
Updated after `simplify-sdlc-routing-schemas`: added sdlc-orchestrator and sdlc-roadmap ownership; removed sdd-plus-superpowers custom schema; OpenSpec defaults to package-provided spec-driven; schema installation step removed from sdlc-openspec-init.
Updated after `standardize-ai-evalops-target-workspaces`: added sdlc-evalops ownership; recorded 3 Promptfoo eval pitfalls (grader model selection, max_tokens sizing, assertion design).
