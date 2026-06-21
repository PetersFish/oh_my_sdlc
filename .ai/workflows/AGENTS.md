# AGENTS.md — Workflow Runtime Constraints

Behavioral constraints for agents modifying `.ai/workflows/scripts/workflow.py`.

## 1. Preflight Policy Extension

- New governed actions MUST be registered via `@register_policy("<action>", allowed_phases={...}, repair_hooks=[...], creates_run=True/False)` decorator.
- Action metadata is stored per-action in `POLICY_META`, NOT as function attributes (to avoid stacked-decorator overwrite bugs).
- `POLICY_REGISTRY` maps action → policy function. `POLICY_META` maps action → `{allowed_phases, repair_hooks, creates_run}`.
- NEVER add action-specific `if/elif` branches inside `cmd_preflight` or `cmd_ensure_run`.
- Each policy function receives `(root, action, subject_type, subject_id)` and returns a dict with keys `allowed`, `status`, `reason`, `next_action`.
- Shared run-context evaluation goes through `_evaluate_subject_run_context()`.
- Phase validation uses `ACTION_PHASE_MAP` (populated from `allowed_phases`).

## 2. Governance-Check Read-Only Contract

- `cmd_governance_check` MUST remain read-only. It MUST NOT create, modify, or delete any file.
- Finding remediation text MUST include explicit runtime commands (`ensure-run`, `complete-hook`, etc.) that resolve the finding.
- Every remediation MUST include the stop condition: re-run `governance-check` until `block=false`.

## 3. Dangling Archive Repair

- NEVER write done history records directly to resolve a `dangling_archive` finding.
- Repair MUST go through the runtime: `ensure-run --action dangling_archive_repair` creates an active run at `post_archive_actions`, followed by `resolve`, `complete-hook`, `advance`/`done`.
- If a linked roadmap item exists, the `roadmap_done_if_relevant` hook validates it. If no link exists, record `no_linked_item` resolution -- do NOT auto-create roadmap items.

## 4. Superpowers Direct Flow

- `superpowers_direct` action MUST NOT create a workflow run or write any workflow state.
- The `_policy_no_workflow` function MUST return `allowed=true, status=not_required` without any side effects.

## 5. Test Discipline

- Every new policy or command behavior MUST have a corresponding test in `test_workflow.py`.
- Tests use temporary directory fixtures (never mutate real `.ai/` or `openspec/` data).
- Run the full test suite before committing: `python3 -m pytest tests/test_workflow.py -v`.
- Each test MUST assert on the specific `status`, `reason`, and `next_action` fields of the preflight decision.

## 6. Code Style

- Follow existing patterns: `cmd_<command>(root, args)` for command handlers, `loader_*` for domain loaders.
- Use `_make_preflight_decision()` factory for all decision dicts -- never hand-construct the dict.
- Keep the `COMMANDS` set and `main()` dispatch in sync with all command functions.
