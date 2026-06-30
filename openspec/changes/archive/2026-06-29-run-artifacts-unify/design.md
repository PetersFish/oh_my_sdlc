## Context

The SDLC workflow runtime stores run state as JSON files and run artifacts (handoffs, logs, plans) in separate directory trees. The current structure mixes flat JSON files (`active/<run_id>.json`) with subdirectory-based artifacts (`<run_id>/handoffs/`, `<run_id>/plans/`, `<run_id>/logs/`). When archiving runs (via `done` or `advance` to terminal phase), only the JSON file moves from `active/` to `history/`, leaving the artifact directories orphaned. Additionally, legacy top-level `runs/handoffs/<run_id>/` and `runs/logs/<run_id>/` directories exist from an older path convention.

The agent definitions (plan-agent, implement-agent, test-agent, review-agent, finish-agent, dev-orchestrator) already use the unified `<run_id>/handoffs/` and `<run_id>/logs/` paths. The disconnect is solely in the workflow.py runtime's path management.

## Goals / Non-Goals

**Goals:**
- Unify all run artifacts under a single `active/<run_id>/` or `history/<run_id>/` directory
- `run.json` is the canonical run state file, stored inside the run directory
- Archiving moves the entire directory, preserving handoffs/logs/plans alongside the state
- Cancelling a run removes the entire directory
- Auto-migrate legacy top-level handoffs/ and logs/ directories on first access

**Non-Goals:**
- Changing agent definition paths (they already use the unified convention)
- Changing the `current.json` pointer file format
- Changing the YAML workflow definition
- Altering the evidence or gate system logic
- Restructuring the `runs/` directory layout beyond the unification described

## Decisions

### D1: Use `active/<run_id>/run.json` instead of `active/<run_id>.json`

**Rationale:** The run directory already exists for storing artifacts. Placing `run.json` inside this directory creates a single source of truth for a run's complete state. The `run.json` filename is explicit rather than buried in the directory name.

**Alternatives considered:**
- `active/<run_id>/state.json`: Less descriptive than `run.json`
- Keep flat JSON but add symlinks: Adds complexity without solving the directory problem
- Move everything into a single `.json` file with embedded artifacts: Too large, breaks existing agent workflows

### D2: Directory-level archiving and cancellation

**Rationale:** `shutil.move()` of the entire `active/<run_id>/` to `history/<run_id>/` is atomic on the same filesystem. It preserves all artifacts without enumeration. `shutil.rmtree()` for cancellation is the standard Python approach for recursive directory removal.

**Alternatives considered:**
- Enumerate and move individual files: Error-prone, requires maintaining a list of known artifact types
- Copy-then-delete: Slower, not atomic

### D3: Auto-migration on first access

**Rationale:** A one-time migration function that scans `runs/handoffs/` and `runs/logs/` for legacy directories, moving them into the corresponding `<run_id>/` directory. This runs during `save_run_state()` (first write) and `load_run_state()` (first read), ensuring migration happens transparently.

**Alternatives considered:**
- Migration script: Requires manual invocation, easy to forget
- No migration: Orphaned legacy directories accumulate
- Migration during `cmd_status`: Only runs when explicitly called

### D4: Backward-compatible history reading — **REJECTED**

**Rationale:** The product is not yet released; no need to support reading the old flat `history/<run_id>.json` format. Accept the risk that old-format files become unreadable after migration. All history reading code uses only the new `history/<run_id>/run.json` format.

**Alternatives considered:**
- Backward-compatible dual-read: Rejected — adds complexity for a pre-release state with no downstream consumers
- Migrate all history files: Unnecessary — old history is disposable in pre-release

## Risks / Trade-offs

- **[R1] Concurrent access during migration**: If two processes access the same run concurrently, one could be mid-migration. → Mitigation: Use `os.rename()` which is atomic on the same filesystem; add a `.migrated` sentinel file.
- **[R2] Test suite disruption**: Many tests reference `active/<run_id>.json` paths directly. → Mitigation: Update all test path references in the same change; run full test suite to verify.
- **[R3] Template sync requirement**: Changes to workflow.py must be synced to bootstrap templates. → Mitigation: Run `sync_templates.py` after implementation.
- **[R4] Old-format unreadability**: After migration, old flat `history/<run_id>.json` files become unreadable by governance-check and any new code. → Accepted: product is pre-release; no downstream consumers exist.
