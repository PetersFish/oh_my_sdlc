---
id: 20260621-workflow-runtime-enhancements
type: evolution
title: 2026-06-21 — Workflow Runtime Enhancements
summary: Added verify-foundations command, --json flag, sync_templates.py (canonical protection), init_foundations.py (command-backed init), git pre-commit hook, and multi-CLI distribution enforcement.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_commits: [78d5ba3]
linked_specs: []
linked_sessions: []
updated_at: 2026-06-21T16:00:00Z
tags: [workflow, sync, init, distributions, hooks]
---

## New Capabilities

**workflow.py**:
- `verify-foundations` command: read-only health check for 6 foundation items (workflow_py, workflow_yaml, workflow_runs, agents_md, openspec_config, memory_manifest)
- `--json` flag: machine-readable output for all commands
- `FOUNDATIONS` dict and `cmd_verify_foundations()` function (line ~1532-1555)

**sync_templates.py** (new):
- Syncs live `.ai/workflows/` → canonical `skills/sdlc-project-bootstrap/templates/`
- `--check` mode: read-only drift detection (exit 1 if drift)
- `--check-distributed` mode: canonical vs 3 project-level copies
- `--distribute` mode: push canonical to all project-level copies
- `--json` mode: machine-readable reports
- Governed files: workflow.py, sdlc-main.yaml

**init_foundations.py** (new):
- Deterministic `.ai/workflows/` directory structure creation
- Copies workflow.py and sdlc-main.yaml from skill templates
- Idempotent, `--json` support, `--templates` override

**Git infrastructure**:
- `.githooks/pre-commit`: two-tier check (live==canonical + canonical==distributed)
- Installed via `git config core.hooksPath .githooks`

**Distribution**:
- `sdlc-project-bootstrap/scripts/` distributed to all 4 locations (skills/, .opencode/, .claude/, .cursor/)
- Lifecycle governance scripts backported (install_skill.py, lifecycle_utils.py) from .opencode to canonical
- User-level ~/.config/opencode entity directories synced

**Tests**:
- test_workflow.py moved from `.ai/workflows/scripts/` to `tests/` (repo convention)
- New: tests/test_sync_templates.py (13 tests), tests/test_init_foundations.py (6 tests)
- verify-foundations: 4 new tests in test_workflow.py
- Test suite: 94 passed + 11 subtests
