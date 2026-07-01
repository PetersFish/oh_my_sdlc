## Why

The SDLC agents currently inherit one shared model choice even though orchestration, planning, implementation, testing, review, and finish work have different cost and reasoning needs. This change is needed now to centralize per-agent model selection without coupling model settings to canonical `agents/*.md` prompts or expanding bootstrap into a maintenance workflow.

## What Changes

- Add a canonical `agents/config/model-profiles.yaml` template that defines fixed model profiles and per-agent assignments.
- Keep canonical `agents/*.md` model-agnostic and move effective `model` and `variant` rendering into a target-side activation step.
- Split agent setup into template sync, effective-config activation, and an aggregate setup entry so config-only refreshes can be non-destructive.
- Preserve per-target effective config files for `.opencode/`, `.claude/`, and `.cursor/` installs instead of overwriting local adjustments on reinstall.
- Update initialization-time bootstrap guidance to call the script entrypoints for agent setup without turning `sdlc-project-bootstrap` into a general refresh skill.
- Do not add a new `sdlc-agent-config` skill in this change.

## Capabilities

### New Capabilities
- `subagent-model-config`: Centralized per-agent model profile configuration, target-side activation, and aggregate agent setup behavior for derived CLI agent copies.

### Modified Capabilities

None.

## Impact

- Adds agent model profile configuration under `agents/config/`.
- Adds shared config/render helper logic and new setup/activation scripts under `scripts/`.
- Modifies `scripts/install_agents.py` semantics so template sync and activation drift are handled separately.
- Updates canonical `agents/*.md` plus derived agent copies under `.opencode/`, `.claude/`, and `.cursor/`.
- Updates bootstrap documentation and focused tests covering install, activation, setup, and bootstrap guidance.
