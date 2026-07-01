## Metadata

- Run ID: 2026-06-30-subagent_model_config
- Slice ID: subagent_model_config
- Agent: implement-agent
- Phase: apply_change
- Flow Type: spec-flow
- Status: success
- Recommended Next Agent: dispatch_test_agent

## Objective

Remediate the review finding that `setup_agents.py --dry-run` did not provide the approved non-writing preview of both template-sync and activation for a fresh target, and add direct behavioral coverage for that aggregate path.

## Work Completed

- Added a new aggregate dry-run behavior test in `tests/test_setup_agents.py`:
  - `test_setup_dry_run_reports_fresh_target_preview_without_writing`
  - Executes `setup_agents.py --dry-run` directly against a fresh target path.
  - Verifies stdout previews template-sync install actions, config-template initialization, and activation actions.
  - Verifies the fresh target directory is not created.
- Verified RED phase before the fix:
  - The new test failed because stdout only contained the placeholder message `[DRY-RUN] would run install (template sync)` and did not provide the required preview contract.
- Implemented a surgical fix in `scripts/setup_agents.py`:
  - Added `_preview_dry_run()`.
  - Dry-run now inspects canonical agent markdown files without invoking the writing install path.
  - Dry-run now previews target config initialization using the canonical template when the target config does not exist.
  - Dry-run now loads the effective config (target config when present, canonical template otherwise) and computes activation preview messages using `update_frontmatter()` plus effective model/variant resolution.
  - Fresh-target dry-run no longer delegates to `activate_agents_config.py --dry-run`, so it no longer errors on missing target/config while still returning success.
- Re-ran the focused setup suite after the fix; all tests passed.

## Files/Artifacts Changed

- `scripts/setup_agents.py`
- `tests/test_setup_agents.py`

## Commands Run

1. `python3 -m pytest tests/test_setup_agents.py -k fresh_target_preview -v`
   - RED: failed before the fix with missing aggregate preview output.
   - GREEN: passed after the fix.
2. `python3 -m pytest tests/test_setup_agents.py -v`
   - Passed (`6 passed`).

## Evidence Summary

- The approved dry-run contract is now implemented end-to-end for fresh targets:
  - template-sync preview is explicit per file,
  - config-template initialization preview is explicit,
  - activation preview is explicit,
  - no files or directories are written.
- The regression coverage now exercises the aggregate `setup_agents.py --dry-run` entrypoint directly instead of indirectly testing only `activate_agents_config.py --dry-run`.

## Blockers

- None.

## Assumptions

- The canonical config template remains available under `agents/config/model-profiles.yaml` and is the correct basis for fresh-target dry-run activation preview.

## Risks/Follow-Ups

- This remediation intentionally keeps scope narrow to the review finding and does not change non-dry-run install/activation orchestration semantics.

## Raw Logs

- `.ai/workflows/runs/active/2026-06-30-subagent_model_config/logs/subagent_model_config/implement-agent/pytest-setup-agents-dry-run-red-green.log`
- `.ai/workflows/runs/active/2026-06-30-subagent_model_config/logs/subagent_model_config/implement-agent/pytest-setup-agents-full.log`
