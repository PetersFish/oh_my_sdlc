## Why

New project initialization in this ecosystem currently requires the developer to know and execute three independent steps: create `AGENTS.md`, initialize OpenSpec, and set up repository memory. Each step has different tools and invocation patterns, and the correct execution order (`AGENTS.md` -> OpenSpec -> memory) is not obvious. An orchestration skill provides a single, idempotent entry point that sequences these steps correctly and reports results.

## What Changes

- **New skill `sdlc-project-bootstrap`**: Orchestrates project foundation initialization with a fixed execution order:
  1. `AGENTS.md` initialization (create from template or conservative merge)
  2. OpenSpec initialization (delegate to OpenSpec CLI)
  3. Repository memory initialization (delegate to `sdlc-repository-memory-init`)
- **New template `templates/AGENTS.md`**: Baseline agent behavior rules (from current repository `AGENTS.md` lines 1-61), bundled with the skill so it is self-contained for the AGENTS step.
- Each step is idempotent. Existing artifacts are preserved; only missing artifacts or missing standard blocks are added.
- The skill reports created, skipped, and appended actions, plus suggested next steps.

## Capabilities

### New Capabilities
- `sdlc-project-bootstrap`: Single-command project foundation initialization with sequenced, idempotent steps

## Impact

- New canonical skill directory: `skills/sdlc-project-bootstrap/`
  - `SKILL.md`: Orchestration workflow and guard rules
  - `templates/AGENTS.md`: Baseline agent behavior rules
- No changes to existing skills (`sdlc-repository-memory-init`, etc.)
- No schema changes
- No breaking changes
- No new Python scripts in v1; all logic is in SKILL.md instructions
