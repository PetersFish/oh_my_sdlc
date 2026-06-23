# Session Summary: RM-EVAL-004 Roadmap Review + SDLC Workflow Fixes

**Date:** 2026-06-23

## Flow

1. **Roadmap review** — reviewed RM-EVAL-004 (Promptfoo Eval 加速：并发 + 增量运行)
   - Removed cancelled RM-EVAL-003 dependency
   - Added Problem Context (10+ min serial eval)
   - Added Design Notes (Git-diff baseline, ThreadPoolExecutor, moderate defaults)

2. **OpenSpec artifacts** — created change `evalops-concurrency-incremental-eval`
   - proposal.md, design.md, specs (3 capabilities), tasks.md (9 groups, 30 checkboxes)
   - Set RM-EVAL-004 to `ready` with `openspec_change: evalops-concurrency-incremental-eval`

3. **Governance block** — opencode plugin detected `ungoverned_roadmap_item` + `linked_item_no_workflow_evidence`
   - Remediation loop: resolve kept failing → dead loop

## Problems Discovered (8 fixes applied)

### Problem 1: Roadmap phase inference was wrong (`_infer_phase`)
- Checked for nonexistent `status: review` → always fell through to `create_roadmap`
- **Fix:** idea → `review_roadmap`, ready+linked → `create_change`, active → `apply_change`

### Problem 2: No way to write `context.change_id` for roadmap promotion
- `create_change` phase requires `context.change_id` but no CLI to set it
- **Fix:** Added `record-context` command (`--key change_id --value ...`)

### Problem 3: `resolve` was a no-op (only reloaded loaders)
- Re-running resolve in a loop never cleared blocks
- **Fix:** Resolve now recalculates readiness, clears `missing_required_inputs` + `domain_state_mismatch` blocks when resolved

### Problem 4: `complete-phase` didn't clear old blocks
- Once `exit_criteria_failed` was set, passing correct exit criteria couldn't unblock
- **Fix:** Complete-phase now clears any existing block and sets `status: running` on success

### Problem 5: `--exit-criteria-satisfied` expects criterion names, not boolean
- Passed `true` instead of `roadmap_item_created` / `openspec_artifacts_done`
- Runtime uses string-set intersection: `_check_exit_criteria(state, phase_def, supplied)`
- **Addressed:** Correct strings now documented in `sdlc_main.yaml` exit_criteria

### Problem 6: Governance-check missed linked evidence
- Only checked `context.change_id`; missed `evidence.change_id` + frontmatter `openspec_change`
- Finding name `archived_linked_item_no_evidence` was misleading (item not archived)
- Remediation text suggested `ensure-run --action roadmap_insert` (doesn't work)
- **Fix:** Check evidence + frontmatter; renamed to `linked_item_no_workflow_evidence`; remediation suggests `record-context` for existing run or `start` for new run

### Problem 7: `ensure-run` hardcoded openspec archive check
- For non-openspec_change subjects (like roadmap_item), archive check wrongly blocked
- **Fix:** Only check archive for `subject_type == "openspec_change"`

### Problem 8: Stale user-level orchestrator skill
- `~/.config/opencode/skills/sdlc-orchestrator/SKILL.md` was outdated (lacked Canonical-Run Promotion section)
- **Fix:** Distributed canonical `skills/sdlc-orchestrator/SKILL.md` to user-level

## Final State
- `workflow.py`: 112 tests pass
- Governance: `block: false`, `findings: []`
- RM-EVAL-004 run: `current_phase: apply_change`, `status: running`, `context.change_id: evalops-concurrency-incremental-eval`
- Template synced: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
