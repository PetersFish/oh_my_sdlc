# Sync History: 20260712-remove-superpowers-direct-dead-code

## Changed Files

Committed range `db18359..a9cc65b` (post_archive_actions cleanup for the
accepted archived lightweight-flow change
`remove-superpowers-direct-dead-code`):

- `agents/dev-orchestrator.md` — removed `superpowers-direct` Plan Mode handoff branch
- `.ai/workflows/scripts/workflow.py`, `.ai/workflows/scripts/workflow_runtime/policies.py` — removed `superpowers-direct` policy/dispatch surface
- `openspec/specs/sdlc-orchestrator/spec.md` — deleted retired "Direct flow handoff may name direct execution" scenario
- Distributed agent + workflow template copies (`.opencode/`, `.claude/`, `.cursor/`, `skills/sdlc-project-bootstrap/templates/workflow/`)
- `tests/test_workflow.py`, `tests/test_workflow_modules.py`, `tests/test_wrapper_contracts.py` — trimmed dead regression cases
- `docs/superpowers/plans/2026-07-12-remove-superpowers-direct-dead-code.md` → archived to `docs/superpowers/archive/plans/`
- `.ai/workflows/runs/active/2026-07-12-remove-superpowers-direct-dead-code/` run-state files
- `.ai/memory/evolution/20260712-remove-superpowers-direct-dead-code.md` (this sync)
- `.ai/memory/manifest.json`, `.ai/memory/index.json` (this sync)

## Evidence Used

- Stable commit range `db18359..a9cc65b` (clean worktree at sync time).
- Lightweight-flow archive handoff at `.ai/workflows/runs/active/2026-07-12-remove-superpowers-direct-dead-code/handoffs/remove-superpowers-direct-dead-code/finish-agent.md` (`archive_action_completed: true`, accepted).
- implement-agent verification evidence (`verification_passed: true`, 1201 tests + 49 subtests, zero failures).
- review-agent completion evidence (accepted).
- Canonical spec remediation commit `63be305` removing the retired scenario.

## Memory Deltas

- `evolution/20260712-remove-superpowers-direct-dead-code.md` — NEW. Records
  removal of the `superpowers-direct` Plan Mode handoff route from
  dev-orchestrator, workflow runtime policies, and the canonical
  sdlc-orchestrator spec. Linked commits `5f3afe3`, `63be305`. Linked spec
  `sdlc-orchestrator`.
- `manifest.json` — last-synced commit advanced to `a9cc65b`.
- `index.json` — rebuilt; 42 entries, new evolution entry included.

## Skipped

- `pitfalls`: no failure evidence (no stack trace, failing test, or observed misbehavior). Planned dead-code removal, not a bug fix.
- `decisions`: no new architecture decisions; refactor follows existing workflow-runtime architecture.
- `architecture`: no new architecture candidates; module map and dependency direction unchanged.
- `specs`: no new spec memory; the `sdlc-orchestrator` spec remediation removed a retired scenario without introducing a new spec ID.
- `modules`: no new module candidates accepted; diff-detected module memory for `agents` and `workflow-runtime` unchanged in structure.

## Review Required

None. No `needs_user_review` items.

## Confidence

High — stable commit range, clean worktree, verified implementation, accepted review.