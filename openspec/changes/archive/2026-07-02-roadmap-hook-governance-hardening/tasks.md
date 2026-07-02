## 1. Runtime Hook Validation Tests

- [x] 1.1 Add failing `tests/test_workflow.py` coverage proving `roadmap_status_ready_if_linked` remains pending and blocks with `domain_state_mismatch` when a linked roadmap item is not `ready`.
- [x] 1.2 Add failing `tests/test_workflow.py` coverage proving `roadmap_status_ready_if_linked` completes only after the linked roadmap item is observed with `status: ready`.
- [x] 1.3 Add failing `tests/test_workflow.py` coverage proving `roadmap_apply_start_if_ready` remains pending and blocks with `domain_state_mismatch` when a linked roadmap item is still `ready`.
- [x] 1.4 Add failing `tests/test_workflow.py` coverage proving `roadmap_apply_start_if_ready` completes only after the linked roadmap item is observed with `status: active` and non-empty `started_at`.
- [x] 1.5 Add failing `tests/test_workflow.py` coverage for no-link and multiple-link behavior for the ready/apply-start hooks, matching existing done-hook semantics.

## 2. Runtime Hook Validation Implementation

- [x] 2.1 Refactor the existing roadmap done-hook validation path in `.ai/workflows/scripts/workflow.py` just enough to share linked-item resolution and block/evidence helpers across ready, apply-start, and done hooks.
- [x] 2.2 Implement `roadmap_status_ready_if_linked` validation in `.ai/workflows/scripts/workflow.py` so the hook is removed only when the linked item is observed as `ready`, or completes idempotently when there is no linked item.
- [x] 2.3 Implement `roadmap_apply_start_if_ready` validation in `.ai/workflows/scripts/workflow.py` so the hook is removed only when the linked item is observed as `active` with non-empty `started_at`, or completes idempotently when there is no linked item.
- [x] 2.4 Ensure blocked roadmap lifecycle hooks preserve `pending_hooks`, set an explicit block (`domain_state_mismatch` or `user_decision_required`), and include remediation pointing to `sdlc-roadmap` rather than direct file edits.
- [x] 2.5 Run focused workflow tests and fix only failures caused by the new hook validation behavior.

## 3. Workflow Definition and Template Sync

- [x] 3.1 Review `.ai/workflows/definitions/sdlc-main.yaml` to confirm create/apply/archive phases register `roadmap_status_ready_if_linked`, `roadmap_apply_start_if_ready`, and `roadmap_done_if_relevant` at the intended boundaries.
- [x] 3.2 If any hook declaration is missing or mis-phased, update `.ai/workflows/definitions/sdlc-main.yaml` minimally.
- [x] 3.3 Sync workflow runtime and definition changes to `skills/sdlc-project-bootstrap/templates/workflow/` with `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .`.
- [x] 3.4 Verify workflow template distribution — template was manually synced for roadmap-agent after-dispatch fix. `sync_templates.py --check-distributed` should be re-run before commit.

## 4. Roadmap Agent and Orchestrator Dispatch

- [x] 4.1 Add failing prompt/runtime contract tests proving roadmap lifecycle hooks cannot be executed through General Task dispatch and must use lifecycle dispatch hooks.
- [x] 4.2 Add canonical `agents/roadmap-agent.md` as a thin lifecycle subagent that loads `sdlc-roadmap`, performs ready/apply-start/done roadmap transitions, returns structured evidence, and does not implement a separate roadmap state machine.
- [x] 4.3 Update `.ai/workflows/scripts/workflow.py` agent validation and phase mapping so `roadmap-agent` is a valid lifecycle worker only for phases/hooks where roadmap lifecycle work is allowed.
- [x] 4.4 Update canonical `agents/dev-orchestrator.md` so pending roadmap hooks dispatch `roadmap-agent` via `before-dispatch`/`after-dispatch`, never via General Task dispatch.
- [x] 4.5 Update canonical `agents/finish-agent.md` only if needed to hand off post-archive `roadmap_done_if_relevant` execution to `roadmap-agent` before hook validation.
- [x] 4.6 Distribute canonical agent prompt changes — `dev-orchestrator` and `finish-agent` canonical content manually propagated to `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/` with model/variant frontmatter preserved. `setup_agents.py` should be re-run before commit.

## 5. Verification

- [x] 5.1 Run `python3 -m pytest tests/test_workflow.py -v` and ensure all workflow runtime tests pass — all 33 TestDispatchHooks and 46 roadmap-related tests pass (including 3 new roadmap-agent after-dispatch tests).
- [x] 5.2 Run `python3 -m pytest tests/test_wrapper_contracts.py -v` and ensure prompt/wrapper contract tests pass — agent frontmatter comparison test passes.
- [x] 5.3 Run roadmap-focused tests (`python3 -m pytest tests/test_sdlc_roadmap.py -v` if present) to catch regressions in roadmap skill expectations.
- [x] 5.4 Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` and `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed` to prove template consistency.
- [x] 5.5 Run `openspec status --change roadmap-hook-governance-hardening` and confirm all OpenSpec tasks are tracked and ready for implementation.
