## Context

The SDLC workflow runtime stores active run state in a single `.ai/workflows/runs/current.json` file. `cmd_start` blocks any different-subject run when an active run exists, preventing parallel workflow runs for concurrent OpenSpec changes. This design replaces the single-file model with a directory-based `active/` layout and a pointer file, enabling multiple concurrent runs without breaking existing phase command signatures.

Constraints:
- Phase commands (`readiness`, `resolve`, `advance`, `done`, etc.) must retain zero-argument `load_run_state(root)` signatures.
- `governance-check` must remain read-only.
- No changes to the workflow phase machine or transition logic.
- Tests must pass with the updated layout.

## Goals / Non-Goals

**Goals:**
- Support multiple concurrent workflow runs in `active/<run_id>.json`.
- Keep `current.json` as a session-scoped pointer to the active run.
- Transparent session switching via entry-point pointer assignment.
- Governance-check scans all active runs for pending hooks.
- Zero signature changes to 10 phase commands.

**Non-Goals:**
- No change to `history/` format or content.
- No locking or merge mechanism for concurrent runs touching the same subject.
- No automatic run prioritization or scheduling.
- No legacy migration (no historical `current.json` burden exists).

## Decisions

### Decision 1: Directory-based active runs with pointer file

**Choice:** Use `active/<run_id>.json` directory + `current.json` as a pointer-only file (`{"run_id": "..."}`). Full run state is stored only in `active/<run_id>.json`; `current.json` never duplicates run fields.

**Alternatives considered:**
- **Remove `current.json` entirely**: Would require changing all 10 phase commands to accept a `run_id` parameter. Rejected to avoid breaking phase command signatures.
- **Namespace-prefixed single files (e.g., `current-<id>.json`)**: Harder to enumerate active runs, requires filename parsing to identify runs. Rejected in favor of directory scanning.

**Rationale:** Directory-based layout enables standard filesystem tools (os.listdir) for scanning and listing. Pointer file preserves existing command signatures. The pointer is set by entry points (`start`, `resume`, `preflight`), making session switching transparent.

### Decision 2: load_run_state dual-mode

**Choice:** `load_run_state(root)` reads pointer → loads pointed run. `load_run_state(root, run_id)` loads a specific file for batch scanning.

**Rationale:** Phase commands use the zero-arg form and operate transparently on the pointed run. Governance-check and status-all use the explicit form to iterate all active runs.

### Decision 3: save_run_state writes active file and pointer

**Choice:** `save_run_state(root, state)` writes full state to `active/<run_id>.json` and writes only `{"run_id": "<run_id>"}` to `current.json`.

**Rationale:** Avoids duplicating run state between two files. The active file is the only source for full run details; the pointer only selects the current session run.

### Decision 4: Run ID as filename key

**Choice:** `run_id` is the filename (e.g., `active/os-opencode_change-add-foo.json`). Filenames are self-describing.

**Rationale:** Avoids needing to parse JSON to identify a run. Makes directory listing immediately informative.

### Decision 5: Same-subject duplicate rejection

**Choice:** `cmd_start` rejects duplicate active runs for the same `subject_id`. Exactly one active run per subject at any time.

**Rationale:** Prevents conflicting state for the same OpenSpec change. A single change cannot have two concurrent active runs.

### Decision 6: cmd_resume requires explicit subject

**Choice:** `cmd_resume` always requires `--subject-type` + `--subject-id`. If arguments are missing, it reports an error and lists active run summaries with subject info.

**Rationale:** With multiple active runs, implicit resume is ambiguous. Listing active runs in the error output gives the user the information needed to re-run `resume` with the correct subject. `cmd_status` remains available for proactively inspecting active runs.

### Decision 7: Entry points set the pointer

**Choice:** `cmd_start`, `cmd_resume`, and `cmd_preflight` all update `current.json` pointer to their resolved run.

**Rationale:** Session switching is handled naturally. When the user continues work on a different change, the next entry-point call updates the pointer.

### Decision 8: Governance-check scans all active files

**Choice:** Scan all `active/` files for `pending_hooks` (not just the pointed run). Continue using `history/` for done evidence (dangling archive check).

**Rationale:** Ensures hooks from parallel runs are visible in governance diagnostics. The pointed run is session-scoped; governance is repository-scoped.

### Decision 9: Status uses pointer-aware output

**Choice:** `cmd_status` is read-only and pointer-aware:
- If `current.json` points to an existing active run, show that run's full state.
- If `current.json` is `{}` or absent, report no current run and list active run summaries.
- If `current.json` points to a missing active file, report a stale pointer and list active run summaries.
- If subject args are provided, show the matching active run's full state.

**Rationale:** This preserves the old "status shows current run" behavior when a session pointer exists, while still helping users recover or choose a run when no current pointer is set.

## Risks / Trade-offs

- **Directory scanning overhead**: Scanning `active/` is slightly slower than reading a single file, but the number of active runs is small (typically 1-3).
- **Pointer maintenance**: Adding one more file (`current.json` as pointer) increases maintenance surface, but avoids changing 10 command signatures.
- **Ambiguity for multi-subject sessions**: Losing the "exactly one active run" invariant means some commands need explicit subject disambiguation. `cmd_status` lists all active runs; the pointer handles single-subject sessions transparently.
- **Concurrent run conflicts**: Concurrent runs touching the same roadmap item or same file could produce merge conflicts. The runtime provides isolation, not synchronization — this is a user-level concern.
- **Stale pointer risk**: `current.json` may point to a missing active file if a run is removed or interrupted unexpectedly. `cmd_status` reports stale pointers and lists active run summaries so the user can resume the correct run.

## Migration Plan

1. Implement the new `active/` directory and pointer file logic in `workflow.py`.
2. No legacy data to migrate — this project has no historical `current.json` burden requiring migration.
3. Run full test suite (`python3 -m pytest tests/test_workflow.py -v`).
4. Sync canonical templates after implementation.
