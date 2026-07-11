# Implement Agent Handoff — Review Remediation

## Metadata

- **Agent:** implement-agent
- **Phase:** apply_change
- **Slice ID:** default
- **Flow Type:** lightweight-flow
- **Run ID:** 2026-07-11-workflow-final-tail-commit
- **Execution Mode:** main_checkout
- **Worktree Path:** `/Users/yuping/Documents/workspace/oh_my_skills`
- **Change ID:** workflow-final-tail-commit
- **Status:** success

## Objective

Remediate the blocking review finding: `cmd_final_commit` must not commit unrelated pre-existing staged changes while preserving index state, and add appropriate regression coverage for an unrelated pre-staged tracked file.

## Work Completed

### TDD Red/Green Loop

1. **RED** — Added `test_final_commit_does_not_commit_pre_staged_unrelated_file` to `tests/test_workflow.py`. This test:
   - Creates a tracked `src/unrelated.py`, commits it as baseline.
   - Modifies the allowlisted `run.json` (dirty).
   - Pre-stages `src/unrelated.py` modification via `git add` BEFORE final-commit.
   - Runs `final-commit` and asserts:
     - `src/unrelated.py` is NOT in the resulting commit (`git show --name-only`).
     - `src/unrelated.py` staged index state IS preserved (`M  src/unrelated.py` in `git status --porcelain`).
     - `src/unrelated.py` appears in `residual_dirty_paths`.
   - Confirmed RED: `AssertionError: 'src/unrelated.py' unexpectedly found in ['.ai/workflows/runs/history/2026-07-05-example/run.json', 'src/unrelated.py']`

2. **GREEN** — Fixed `cmd_final_commit` in `.ai/workflows/scripts/workflow.py`:
   - **Root cause:** `git commit -m <message>` commits the entire index, including pre-existing staged files outside the allowlist.
   - **Fix:** Changed to `git commit -m <message> -- <staged_paths>` where `staged_paths` is filtered to allowlisted paths only. Explicit pathspecs scope the commit to only allowlisted governance artifacts, leaving pre-existing staged non-allowlisted files in the index untouched (state preserved).
   - Also fixed `staged_paths` reporting: `git diff --cached --name-only` output is now filtered through the allowlist so the JSON output reports only allowlisted staged paths, not pre-existing staged files.
   - Confirmed GREEN: new test passes.

3. **Sync** — Propagated canonical `workflow.py` fix to all 4 template copies via `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git`. Verified all 5 copies (canonical + 4 templates) contain the `git commit -m message -- staged_paths` fix.

## Files/Artifacts Changed

### Files modified by this remediation

| File | Reason |
|---|---|
| `.ai/workflows/scripts/workflow.py` | Fixed `cmd_final_commit` to scope commit to allowlisted paths only via `git commit -- <pathspecs>` and filter `staged_paths` reporting through allowlist |
| `tests/test_workflow.py` | Added `test_final_commit_does_not_commit_pre_staged_unrelated_file` regression test |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | Template sync (derived) |
| `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | Template sync (derived) |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | Template sync (derived) |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | Template sync (derived) |

### Pre-existing dirty files (from prior implement-agent run, not touched by this remediation)

- `agents/dev-orchestrator.md` and distributed copies
- `.opencode/agents/.agent-install.json`, `.claude/agents/.agent-install.json`, `.cursor/agents/.agent-install.json`
- `.opencode/skills/sdlc-project-bootstrap/.skill-install.json`, `.claude/...`, `.cursor/...`
- `docs/superpowers/plans/2026-07-05-workflow-final-tail-commit.md`
- `tests/test_wrapper_contracts.py`
- `.ai/workflows/runs/current.json`

## Commands Run

| Command | Result |
|---|---|
| `python3 -m pytest tests/test_workflow.py -k "test_final_commit_does_not_commit_pre_staged_unrelated_file" -v` (RED) | FAIL — `src/unrelated.py` unexpectedly found in commit |
| `python3 -m pytest tests/test_workflow.py -k "test_final_commit_does_not_commit_pre_staged_unrelated_file" -v` (GREEN) | PASS |
| `python3 -m pytest tests/test_workflow.py -k "final_commit" -v` | 13 passed |
| `python3 -m pytest tests/ -v` | 1172 passed, 49 subtests passed |
| `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git` | OK: all 8 fix suites in sync |
| `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git` | OK: all 6 check suites in sync |

## Evidence Summary

- **tasks_complete:** true — review finding remediated, regression coverage added, all verification passed.
- **tdd_passed:** true — RED phase confirmed expected failure, GREEN phase confirmed fix.
- **verification_passed:** true — full suite (1172 tests + 49 subtests) green, derived sync green.
- **focused_tests:** 13 final_commit tests pass (including new regression test).
- **full_regression:** 1172 passed, 49 subtests passed, 0 failed.
- **derived_sync:** all 6 check suites in sync.

## Issues

- None encountered during remediation. The fix was straightforward: scoping `git commit` to explicit pathspecs.

## Learnings

- A dirty-path allowlist for `git add` is insufficient when the Git index may already contain pre-existing staged changes; `git commit` consumes the entire index unless explicit pathspecs are passed. The fix uses `git commit -m <msg> -- <paths>` to scope the commit independently of what else is staged.
- `staged_paths` JSON reporting must also be filtered through the allowlist, not taken raw from `git diff --cached --name-only`, to avoid reporting pre-existing staged files as if final-commit staged them.

## Suggestions

- Consider adding the pre-existing-index policy to the final-commit spec (`docs/superpowers/specs/2026-07-05-workflow-final-tail-commit.md`) so the behavior contract explicitly states that pre-existing staged files outside the allowlist are preserved in the index and excluded from the commit.
- Add index-state scenarios to the final-commit test matrix: mixed staged/unstaged changes on one path, and commit failure with index preservation.

## Risks/Follow-Ups

- The spec document does not yet explicitly document the pre-existing-index preservation contract. This is a documentation follow-up, not a behavioral risk (the behavior is tested and correct).

## Raw Logs

- Full test suite output saved to tool output cache (1172 passed, 49 subtests passed in 53.59s).
- Focused test output: 13 passed, 302 deselected in 2.07s.