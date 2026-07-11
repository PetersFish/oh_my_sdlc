## Metadata

- **Run ID:** 2026-07-09-finish-agent-branch-decision-and-terminal-ownership
- **Slice ID:** default
- **Agent:** implement-agent
- **Phase:** apply_change
- **Flow Type:** lightweight-flow
- **Status:** success
- **Re-dispatch:** fixes review-agent absolute-path classification blocker

## Objective

Fix the review-agent blocker: `_archive_lightweight_superpowers_artifacts()`
only classified repo-relative paths starting with `docs/superpowers/plans/` or
`docs/superpowers/specs/`. The governed runtime context for this slice provides
absolute `primary_design_path` / `design_artifact_paths[]`, so fallback-derived
Superpowers artifacts were dropped before move/skipped validation. This left
`archive_action_completed: true` while no plan/spec files moved.

Add absolute-path normalization to repo-relative before classification, plus
behavior tests for absolute runtime design artifact paths.

## Work Completed

Followed TDD red/green:

1. RED — wrote two failing behavior tests in `TestLightweightFlowArchiveMoves`:
   - `test_absolute_runtime_design_artifact_paths_move_plan_and_spec`: runtime
     contract supplies ABSOLUTE plan+spec paths; asserted both are moved to
     typed archive dirs and removed from active dirs.
   - `test_absolute_runtime_path_missing_source_blocks`: runtime contract
     supplies absolute plan+spec paths that do NOT exist on disk; asserted
     after-dispatch emits `workflow.py block` with
     `missing_lightweight_archive_artifacts` and flips
     `archive_action_completed` to false.
   Both failed for the expected reason: `_archive_dst_for()` returned None for
   absolute paths, so nothing was paired, moved, or skipped.
2. GREEN — added `_to_repo_rel(p)` helper inside
   `_archive_lightweight_superpowers_artifacts` that normalizes absolute
   paths under the repo root to repo-relative POSIX strings (via
   `os.path.relpath`), leaving repo-relative paths unchanged and outside-repo
   paths as `../...` so `_archive_dst_for()` drops them. Applied the
   normalization to every collected `source_paths` entry (both explicit
   finish-agent evidence and runtime-contract fallback) before destination
   derivation. This is a localized change: `_archive_dst_for()` and the
   slug/date counterpart fallback now operate on normalized repo-relative paths
   unchanged.
3. Synced the canonical template and distributed copies of `workflow.py`.
4. Ran focused tests, full regression, derived-artifact check, and plan
   checkbox check.

## Files/Artifacts Changed

| File | Status | Reason |
|---|---|---|
| `.ai/workflows/scripts/workflow.py` | modified | `_to_repo_rel` absolute-path normalization in `_archive_lightweight_superpowers_artifacts` |
| `tests/test_workflow.py` | modified | Two new behavior tests covering absolute runtime design artifact paths |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | modified | Canonical template synced from live |
| `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | modified | Distributed copy synced |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | modified | Distributed copy synced |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | modified | Distributed copy synced |

(Prior implement-agent changes for the original dispatch — agents/, yaml,
wrapper contracts, plan checkboxes, and the two earlier archive behavior tests
— remain in the worktree from the original dispatch and are not re-touched
here beyond the template sync that this re-dispatch's workflow.py edit
required.)

## Commands Run

- `python3 -m pytest tests/test_workflow.py -k "test_absolute_runtime_design_artifact_paths_move_plan_and_spec or test_absolute_runtime_path_missing_source_blocks" -v` (RED: 2 failed; GREEN: 2 passed)
- `python3 -m pytest tests/test_workflow.py -q` (301 passed, 25 subtests passed)
- `python3 -m pytest tests/ -q` (1152 passed, 49 subtests passed — up from 1150)
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .` (synced)
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute` (distributed)
- `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git` (OK: all 6 suites in sync)
- `python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-05-finish-agent-branch-decision-and-terminal-ownership.md` (ok)

## Evidence Summary

- tasks_complete: true
- tdd_passed: true (both new tests watched fail then pass)
- Focused tests: 2 new tests pass.
- Full regression: 1152 passed, 0 failed (up from 1150 — the 2 new tests).
- Derived artifacts in sync (incremental check OK, 6 suites).
- Plan checkbox check: ok.

## Issues

- None new.

## Learnings

- The review blocker was a data-shape mismatch: the governed workflow runtime
  supplies absolute design artifact paths, but the archive helper was written
  against repo-relative string prefixes. Normalizing at the boundary
  (`_to_repo_rel`) before classification is the minimal fix — the rest of the
  helper (destination derivation, slug/date fallback, move loop) already
  operates on repo-relative paths.
- `os.path.relpath` on Windows can raise `ValueError` for cross-drive paths;
  the helper guards that case and falls back to the normalized absolute path,
  which `_archive_dst_for()` then drops as non-superpowers.

## Suggestions

- The archive helper now has two inline helpers (`_to_repo_rel`,
  `_archive_dst_for`). If a third normalization need arises, consider promoting
  `_to_repo_rel` to a module-level utility so other path-sensitive helpers
  (e.g., history copy, handoff resolution) share the same repo-relative
  contract.
- Consider asserting in the runtime-context builder that design artifact
  paths are repo-relative, so helpers downstream never have to normalize — but
  that is a larger contract change outside this blocker fix.

## Risks/Follow-Ups

- None new. Prior follow-ups (memory sync target ref enforcement, branch
  action execution) remain prompt-level contracts as noted in the original
  handoff.

## Raw Logs

- Focused test output retained in tool-output cache (pytest -v).