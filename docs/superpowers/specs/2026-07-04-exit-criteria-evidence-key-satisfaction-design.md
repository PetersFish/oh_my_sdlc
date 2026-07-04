# Exit Criteria Evidence-Key Satisfaction

## Context

The SDLC workflow runtime (`workflow.py after-dispatch`) validates phase completion using two sequential checks against the phase definition:

1. `_missing_phase_evidence_keys` — verifies each `evidence_keys` entry has a truthy value in the evidence view.
2. `_missing_exit_criteria` — verifies the `criteria_satisfied` string field contains all `exit_criteria` entries.

In every workflow phase definition (`sdlc-main.yaml`), `exit_criteria` and `evidence_keys` are identical:

| Phase | exit_criteria | evidence_keys |
|-------|---------------|---------------|
| create_change | spec_artifacts_done | spec_artifacts_done |
| apply_change | tasks_complete, tdd_passed, eval_passed_or_human_decision_recorded | tasks_complete, tdd_passed, eval_passed_or_human_decision_recorded |
| archive_change | archive_path_exists | archive_path_exists |
| post_archive_actions | pending_hooks_empty | (none) |

This means the two checks validate the same set of keys, but via different mechanisms: one checks actual evidence values, the other checks a string declaration. When an agent provides a truthy evidence key value (e.g. `archive_path_exists: true`) but does not list that key name in the `criteria_satisfied` string, the first check passes and the second fails.

This was observed in run `2026-07-03-apply-change-evidence-contract-tightening`:

- `finish-agent` returned `evidence.archive_path_exists: true` (satisfying `evidence_keys`).
- `finish-agent` returned `criteria_satisfied: "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded"` (copying apply_change's criteria, not archive_change's).
- `_missing_phase_evidence_keys` passed (the key had a truthy value).
- `_missing_exit_criteria` failed (the string did not contain `archive_path_exists`).
- `after-dispatch` blocked the phase with `missing_exit_criteria_satisfied`.

This will recur for any new agent or phase where the agent provides the correct evidence values but does not precisely mirror the `criteria_satisfied` string to match the current phase's `exit_criteria` list.

## Goals

- Allow exit criteria to be satisfied by either a truthy evidence key value OR an explicit `criteria_satisfied` string entry.
- Eliminate the redundant rejection where evidence keys are already verified as truthy but the string declaration is incomplete.
- Preserve `criteria_satisfied` as an optional explicit declaration for backward compatibility and human-decision scenarios.
- Keep the change minimal: only modify `_missing_exit_criteria` and its direct test coverage.

## Non-Goals

- Do not remove `criteria_satisfied` from agent contracts or agent prompts.
- Do not change `evidence_keys` validation (`_missing_phase_evidence_keys`).
- Do not change phase definitions in `sdlc-main.yaml`.
- Do not generalize aggregation semantics beyond what the prior apply-change change already introduced.
- Do not change `post_archive_actions` behavior (it has no `evidence_keys` defined; the fix naturally handles this via the `criteria_satisfied` string path).

## Decisions

### Decision 1: Exit criteria satisfied by evidence key value OR string declaration

`_missing_exit_criteria` will treat an exit criterion as satisfied if **either** of the following is true:

1. The criterion name appears in the `criteria_satisfied` string (current behavior, preserved).
2. The criterion name exists as a key in the evidence view with a truthy value (`not None, not "", not False`).

This makes the two checks complementary rather than redundant: `_missing_phase_evidence_keys` verifies the value is real, and `_missing_exit_criteria` accepts that as sufficient without also requiring a string declaration.

Rationale:

- `exit_criteria` and `evidence_keys` are identical in all phases that define both. Requiring both a truthy value AND a string declaration is pure redundancy.
- Agents already provide evidence key values as the primary contract. The string is a convenience, not a source of truth.
- Future agents that provide correct evidence values but imperfect `criteria_satisfied` strings will no longer be blocked.

### Decision 2: Apply to all phases, not just apply_change

Unlike the prior apply-change aggregation change (which was scoped to `apply_change`), this fix applies to all phases. The reason:

- `_missing_exit_criteria` already receives `phase_evidence_view` (which for non-apply_change phases is just `agent_evidence`).
- The truthy-value check works uniformly: if the agent provides `archive_path_exists: true`, that satisfies the `archive_path_exists` exit criterion regardless of phase.
- No phase-specific aggregation is needed for this fix; it operates on whatever evidence view the caller already provides.

Rationale:

- The problem is not apply-change-specific; it affects any phase where an agent provides evidence values but an imperfect string declaration.
- Scoping the fix to one phase would leave the same bug in other phases.

### Decision 3: `criteria_satisfied` remains optional but honored

The `criteria_satisfied` string field is not removed or ignored. It continues to work as a valid satisfaction path. Agents that already emit correct `criteria_satisfied` strings will pass without change.

Agents that omit `criteria_satisfied` but provide truthy evidence key values will also pass.

Agents that provide neither a truthy evidence value nor a string declaration for a required criterion will still be blocked.

Rationale:

- Backward compatible: no agent prompt changes required.
- Forward compatible: new agents can rely on evidence values alone.
- No safety loss: the truthy-value check is at least as reliable as a string declaration (both are agent-provided).

## Scope

This change applies to the exit criteria validation path in `workflow.py after-dispatch`:

- `_missing_exit_criteria` function
- All phases that define `exit_criteria` in `sdlc-main.yaml`

No changes to:

- `_missing_phase_evidence_keys` (unchanged)
- `_build_phase_evidence_view` (unchanged)
- `sdlc-main.yaml` phase definitions (unchanged)
- Agent prompts (unchanged)

## Architecture

### Current Problem

```
after-dispatch validation flow:
  1. _missing_phase_evidence_keys(phase_evidence_view, phase_def)
     → checks each evidence_keys entry has truthy value
     → if missing → block: "missing_phase_evidence_keys"

  2. _missing_exit_criteria(phase_evidence_view, phase_def)
     → checks criteria_satisfied string contains all exit_criteria
     → if missing → block: "missing_exit_criteria_satisfied"
```

When check 1 passes (evidence values are truthy) but check 2 fails (string is incomplete), the agent is blocked despite providing valid evidence. This is the redundancy problem.

### New Model

```
after-dispatch validation flow:
  1. _missing_phase_evidence_keys(phase_evidence_view, phase_def)
     → unchanged: checks each evidence_keys entry has truthy value

  2. _missing_exit_criteria(phase_evidence_view, phase_def)
     → checks each exit_criteria entry is satisfied by:
       (a) appearing in criteria_satisfied string, OR
       (b) having a truthy value in the evidence view
     → if neither (a) nor (b) for any required criterion → block
```

This makes check 2 a superset of its current behavior: it accepts everything it currently accepts, plus evidence-key-value satisfaction.

## Runtime Behavior Changes

### `_missing_exit_criteria` signature and implementation

Current:

```python
def _missing_exit_criteria(agent_evidence: Dict[str, Any], phase_def: Dict[str, Any]) -> List[str]:
    raw = agent_evidence.get("criteria_satisfied", "")
    satisfied = {item for item in str(raw).split(",") if item}
    required = set(phase_def.get("exit_criteria", []))
    return sorted(required - satisfied)
```

New:

```python
def _missing_exit_criteria(phase_evidence_view: Dict[str, Any], phase_def: Dict[str, Any]) -> List[str]:
    raw = phase_evidence_view.get("criteria_satisfied", "")
    satisfied = {item for item in str(raw).split(",") if item}
    required = set(phase_def.get("exit_criteria", []))
    for key in list(required - satisfied):
        value = phase_evidence_view.get(key)
        if value is not None and value != "" and value is not False:
            satisfied.add(key)
    return sorted(required - satisfied)
```

The parameter name changes from `agent_evidence` to `phase_evidence_view` to reflect that the caller already passes the merged view (line 1953). The function signature change is internal; the call site already passes `phase_evidence_view`.

### Call site (unchanged)

Line 1953 already calls:

```python
missing_exit_criteria = _missing_exit_criteria(phase_evidence_view, phase_def)
```

No call site change needed.

## Affected Files

- `.ai/workflows/scripts/workflow.py` — `_missing_exit_criteria` function (live runtime)
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` — canonical template (must stay byte-synced)
- project-level distributed workflow template copies (`.opencode/`, `.claude/`, `.cursor/`)
- `tests/test_workflow.py` — new behavior tests + regression tests

No agent prompt changes required.

## Testing Strategy

### New behavior tests

- `test_exit_criteria_satisfied_by_evidence_key_value` — agent returns `archive_path_exists: true` but `criteria_satisfied` does not contain `archive_path_exists`; should pass (no block).
- `test_exit_criteria_satisfied_by_string_only` — agent returns `criteria_satisfied: "archive_path_exists"` but no `archive_path_exists` key in evidence; should pass (backward compatible).
- `test_exit_criteria_missing_both_value_and_string` — agent provides neither evidence value nor string declaration for a required criterion; should block with `missing_exit_criteria_satisfied`.
- `test_exit_criteria_evidence_key_falsy_does_not_satisfy` — agent returns `archive_path_exists: false`; should block (falsy values do not satisfy).
- `test_exit_criteria_apply_change_evidence_key_satisfies` — apply_change agent returns `tasks_complete: true` but omits it from `criteria_satisfied`; should pass via evidence key value.

### Regression tests

- All existing `after_dispatch` tests in `test_workflow.py` must continue passing.
- Existing `missing_exit_criteria_satisfied` block tests must still block when neither path is satisfied.
- `test_workflow.py` full suite.
- `tests/test_wrapper_contracts.py` (no prompt changes, should be unaffected).
- Sync/drift tests for workflow template and distributed copies.

### Edge cases

- `post_archive_actions` has `exit_criteria: [pending_hooks_empty]` but no `evidence_keys`. The agent provides `pending_hooks_empty: true` in evidence and `criteria_satisfied: "pending_hooks_empty"` in string. Both paths satisfy; no change in behavior.
- `create_change` has `exit_criteria: [spec_artifacts_done]` and `evidence_keys: [spec_artifacts_done]`. Same uniform behavior.
- Empty `criteria_satisfied` string with truthy evidence keys: should pass.
- Empty `criteria_satisfied` string with no evidence keys: should block (both paths fail).

## Risks

- **Over-loosening:** If an agent provides a truthy value for a key that is not actually meaningful (e.g. `archive_path_exists: true` without a real archive file), the runtime would pass. Mitigation: `_missing_phase_evidence_keys` already checks the same keys for truthy values; this fix does not change that check. The risk is no greater than the existing evidence-key validation.
- **String declaration becomes advisory:** Agents that previously relied on `criteria_satisfied` as the sole satisfaction path may stop emitting it. Mitigation: This is acceptable; the string remains a valid path and agent prompts still recommend it.
- **Phase-specific aggregation:** For `apply_change`, the `phase_evidence_view` includes merged prior agent evidence. A truthy value from a prior agent result (e.g. `tasks_complete: true` from implement-agent) would satisfy the exit criterion even if the current review-agent did not restate it. This is already the intended behavior from the prior change (Decision 3 in the apply-change-evidence-contract-tightening spec).

## Mitigations

- Keep `_missing_phase_evidence_keys` unchanged as the first gate.
- Add explicit falsy-value test to prove `false`/`""`/`None` do not satisfy.
- Run full regression suite to confirm no existing block tests break.

## Success Criteria

- An agent that provides truthy evidence key values but an incomplete `criteria_satisfied` string passes phase completion.
- An agent that provides a correct `criteria_satisfied` string but no evidence key values passes phase completion (backward compatible).
- An agent that provides neither is still blocked.
- Falsy evidence values (`false`, `""`, `None`) do not satisfy exit criteria.
- All existing workflow and wrapper-contract tests continue passing.
- Workflow template and distributed copies remain in sync.