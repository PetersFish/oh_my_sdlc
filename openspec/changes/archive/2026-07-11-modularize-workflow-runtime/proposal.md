## Why

The workflow runtime has accumulated state persistence, definition validation, domain loading, policy evaluation, governance diagnostics, lifecycle commands, and CLI parsing in a single large script. Splitting these responsibilities now will reduce change risk and maintenance cost before later state-machine work, while preserving the stable `workflow.py` interface used by users, agents, and bootstrap consumers.

## What Changes

- Keep `.ai/workflows/scripts/workflow.py` as the executable CLI facade with unchanged commands, arguments, exit codes, JSON output contracts, and run-state layout.
- Move cohesive runtime responsibilities into importable modules colocated under `.ai/workflows/scripts/`, without introducing a class-based state-machine redesign.
- Preserve the workflow runtime as the sole writer of `.ai/workflows/runs/` state and preserve existing domain ownership boundaries.
- Retain end-to-end CLI regression coverage while adding focused module-level tests for extracted pure and near-pure contracts.
- Extend bootstrap template synchronization and distribution coverage to include the complete workflow runtime module set.

## Capabilities

### New Capabilities
- `workflow-runtime-modularity`: Defines the responsibility boundaries, compatibility guarantees, state-write ownership, test coverage, and template parity required for the modular workflow runtime.

### Modified Capabilities

None.

## Impact

- Affected runtime: `.ai/workflows/scripts/workflow.py` and new sibling Python modules under `.ai/workflows/scripts/`.
- Affected tests: `tests/test_workflow.py` remains the CLI-level regression suite; focused module tests may be added under `tests/`.
- Affected bootstrap assets: `skills/sdlc-project-bootstrap/templates/workflow/` and derived project-level copies under `.opencode/`, `.claude/`, and `.cursor/`.
- Affected sync tooling: template inventory, synchronization, and drift checks must recognize all runtime modules rather than only `workflow.py`.
- No external command, run-file schema, workflow phase, domain ownership, or dependency behavior is intentionally changed.
