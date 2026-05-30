# Brainstorm

## Problem

Starting a new project in this ecosystem requires multiple manual initialization steps:

- Creating `AGENTS.md` with standard agent behavior rules
- Initializing OpenSpec for spec-driven development
- Setting up repository memory (`.ai-memory/`) for durable context

These steps have a fixed dependency order (`AGENTS.md` -> OpenSpec -> memory) but currently require the developer to know and execute each one manually. There is no single entry point that sequences these initializations correctly, ensures idempotence, and reports what was done.

## Constraints

- Must reuse existing capabilities (`sdlc-repository-memory-init`, OpenSpec CLI) rather than duplicating them
- Must be idempotent: safe to run multiple times without overwriting existing work
- Must not auto-commit to git
- Must not auto-run memory sync (init only)
- Must use conservative merge for existing `AGENTS.md`
- v1 scope intentionally narrow; designed to be extensible for future bootstrap steps

## Options

### Option A: Orchestration skill (recommended)

Single `sdlc-project-bootstrap` skill that sequences three steps: AGENTS.md creation/merge, OpenSpec CLI init, and `sdlc-repository-memory-init` delegation. Each step checks preconditions before acting. Extensible via adding new steps to the sequence.

**Trade-offs:**
- Smallest implementation surface
- Clear dependency on existing skills/CLI
- Easy to add future steps (README, CI, .gitignore)

### Option B: Self-contained bootstrap skill

Bundles all initialization logic (AGENTS template, OpenSpec templates, memory templates) into one skill with no external dependencies.

**Trade-offs:**
- No dependency risk from external skills changing
- Template duplication with existing init modules
- Maintenance drift risk

### Option C: Multi-skill initialization pipeline

Each concern gets its own skill (`sdlc-agents-init`, `sdlc-openspec-init`, `sdlc-repository-memory-init`), and bootstrap merely invokes them in order.

**Trade-offs:**
- Cleanest separation of concerns
- Highest implementation cost for v1
- Premature decomposition for currently trivial steps

## Recommendation

Option A (Orchestration skill). The AGENTS.md step is simple enough to inline (creating from template), the OpenSpec step delegates to CLI, and the memory step delegates to existing init. This keeps v1 small while the step-based structure makes future decomposition natural if any step grows complex enough to warrant its own skill.
