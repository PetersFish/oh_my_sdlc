## Why

New project initialization in this ecosystem currently requires the developer to know and execute multiple independent steps: create `AGENTS.md`, initialize OpenSpec, install the `sdd-plus-superpowers` schema (currently only in this repo, must be manually copied), and set up repository memory. Each step has different tools and invocation patterns, and the correct execution order (`AGENTS.md` -> OpenSpec -> schema -> memory) is not obvious. An orchestration skill paired with a dedicated OpenSpec init skill provides a single, idempotent, dry-run-capable entry point that sequences these steps correctly and reports results.

## What Changes

- **New skill `sdlc-openspec-init`**: Initializes OpenSpec in a project, installs the `sdd-plus-superpowers` schema from this repository when needed, lists the available schemas via `openspec schemas --json`, prompts the user to choose one or more OpenSpec AI tools with `opencode` as the default, prompts the user to choose a default schema, and persists that choice in `openspec/config.yaml`. Supports schema detection, installation when missing, schema iteration over time, and recovery when `openspec init` skips `openspec/config.yaml` in non-interactive mode. Can be invoked standalone.
- **New skill `sdlc-project-bootstrap`**: Orchestrates project foundation initialization with a fixed execution order:
  1. `AGENTS.md` initialization (create from template or conservative merge)
  2. OpenSpec + schema initialization (delegate to `sdlc-openspec-init`)
  3. Repository memory initialization (delegate to `sdlc-repository-memory-init`)
- **New template `templates/AGENTS.md`**: Baseline agent behavior rules (from current repository `AGENTS.md` lines 1-61), bundled with `sdlc-project-bootstrap`.
- **Dry-run support**: `sdlc-project-bootstrap` supports preview mode that reports planned actions without modifying files.
- Each step is idempotent. Existing artifacts are preserved; only missing artifacts or missing standard blocks are added.
- The skill reports created, skipped, and appended actions, plus suggested next steps.

## Capabilities

### New Capabilities
- `sdlc-openspec-init`: OpenSpec initialization and schema installation for new projects, with reusable schema lifecycle management
- `sdlc-project-bootstrap`: Single-command project foundation initialization with sequenced, idempotent steps and dry-run preview

## Impact

- New canonical skill directories:
  - `skills/sdlc-openspec-init/`
    - `SKILL.md`: OpenSpec initialization and schema installation workflow
    - `templates/sdd-plus-superpowers/`: Schema files copied from this repository
  - `skills/sdlc-project-bootstrap/`
    - `SKILL.md`: Orchestration workflow and guard rules
    - `templates/AGENTS.md`: Baseline agent behavior rules
- No changes to existing skills (`sdlc-repository-memory-init`, etc.)
- No schema changes
- No breaking changes
- No new Python scripts in v1; all logic is in SKILL.md instructions
