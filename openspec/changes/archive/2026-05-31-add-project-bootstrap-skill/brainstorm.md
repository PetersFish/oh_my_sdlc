# Brainstorm

## Problem

Starting a new project in this ecosystem requires multiple manual initialization steps:

- Creating `AGENTS.md` with standard agent behavior rules
- Initializing OpenSpec for spec-driven development
- Installing the `sdd-plus-superpowers` schema (currently only exists in this repo, must be manually copied)
- Setting up repository memory (`.ai-memory/`) for durable context

These steps have a fixed dependency order (`AGENTS.md` -> OpenSpec -> memory) but currently require the developer to know and execute each one manually. There is no single entry point that sequences these initializations correctly, ensures idempotence, and reports what was done. Additionally, the `sdd-plus-superpowers` schema has no automated installation path for new repositories.

## Constraints

- Must reuse existing capabilities (`sdlc-repository-memory-init`, OpenSpec CLI) rather than duplicating them
- Must be idempotent: safe to run multiple times without overwriting existing work
- Must not auto-commit to git
- Must not auto-run memory sync (init only)
- Must use conservative merge for existing `AGENTS.md`
- Must support dry-run preview so users can see planned actions before execution
- The `sdd-plus-superpowers` schema is only in this repository today; new repos need a path to install it
- Schema will iterate over time; schema lifecycle management should be a dedicated concern
- v1 scope intentionally narrow; designed to be extensible for future bootstrap steps

## Options

### Option A: Single orchestration skill (original)

One `sdlc-project-bootstrap` skill that sequences AGENTS.md creation/merge, OpenSpec CLI init, and `sdlc-repository-memory-init`. Schema installation not automated.

**Trade-offs:**
- Smallest implementation surface
- Schema still requires manual copy, no dry-run

### Option B: Self-contained bootstrap skill

Bundles all initialization logic into one skill with no external dependencies.

**Trade-offs:**
- Template duplication with existing init modules
- Maintenance drift risk

### Option C: Orchestration skill + dedicated openspec-init skill (recommended)

Two skills working together:

- `sdlc-openspec-init`: Handles OpenSpec initialization and `sdd-plus-superpowers` schema installation. Can be invoked standalone or by bootstrap.
- `sdlc-project-bootstrap`: Orchestrates AGENTS.md, calls `sdlc-openspec-init`, calls `sdlc-repository-memory-init`. Supports dry-run.

**Trade-offs:**
- Two skills instead of one, but each has clear scope
- Schema lifecycle management is owned by the right domain skill
- Dry-run is a natural fit for the bootstrap orchestrator
- Follows same delegation pattern already used for memory (bootstrap -> memory-init)

## Recommendation

Option C. The `sdd-plus-superpowers` schema requires installation and will iterate — this is not a trivial one-line CLI call but a domain capability that deserves its own skill. Separating it from bootstrap keeps bootstrap as a pure orchestrator and makes schema management independently testable and upgradeable. Dry-run enters v1 scope as a bootstrap-level feature that previews all planned actions across steps.
