## Context

`cmd_before_dispatch` rejects most workers whenever persisted run status is `blocked`. The branch-finish gate is evaluated later in that command, so a run previously blocked for a missing or invalid `branch_finish_decision` cannot recover merely by recording a corrected value: `cmd_record_context` changes `context` but preserves `status` and `block`.

The repair must remain narrow. Workflow blocks encode several independent failure domains, and recording context must not erase an unrelated worker, hook, EvalOps, or domain-state block. The live workflow runtime is the implementation source; repository policy then requires synchronization to the canonical bootstrap template and derived project-level copies.

## Goals / Non-Goals

**Goals:**

- Make a missing/invalid branch-decision block recover automatically when `record-context` stores an allowed `branch_finish_decision`.
- Clear only a block whose persisted reason is the branch decision that has now become valid.
- Restore the run to `running` with `block: null`, allowing existing guarded dispatch and advancement logic to operate normally.
- Cover the state transition through executable CLI behavior in temporary workspaces.

**Non-Goals:**

- Adding a general-purpose force-unblock command.
- Relaxing the valid branch decision set or silently choosing a default.
- Clearing unrelated block types or changing branch action execution.
- Refactoring the broader workflow state machine.

## Decisions

### Reconcile at the context mutation boundary

After building and validating the tentative context, `cmd_record_context` will evaluate whether the recorded key/value resolves the currently persisted branch-decision block. If and only if all reconciliation predicates hold, the same state save will set `status` to `running` and `block` to `None`.

This boundary is preferred because it makes the correction atomic: the durable context and its corresponding unblock are persisted together. It also lets subsequent commands consume coherent state without each command needing stale-block bypass logic.

**Alternatives considered:**

- **Ignore stale status in `before-dispatch`:** rejected because other commands such as `advance` would still see a blocked run, and state would remain internally contradictory.
- **Require an explicit generic unblock command:** rejected because it adds an unnecessary manual step and can clear unrelated blocks without proving the cause was resolved.
- **Recompute all blocks after every context write:** rejected as too broad and risky for this repair.

### Use explicit, narrow block ownership predicates

Reconciliation will require all of the following:

1. The run is currently `blocked`.
2. The recorded key is `branch_finish_decision`.
3. The new tentative context resolves to decision status `ok` under the existing validator.
4. The persisted block represents the branch-decision gate, identified by its decision-specific reason/type/action metadata as encoded by the runtime's current blocked transition.

If the existing persisted block lacks sufficiently structured reason metadata, the implementation may add a small helper that recognizes only the runtime's own branch-decision block shape (for example its `user_decision_required` type plus `ask_user_branch_finish_decision` next action). It must not use message substring matching as the primary contract.

Missing or invalid corrections leave state blocked. Valid decision writes against unrelated blocks update context but preserve the block.

### Verify end-to-end state transitions

Regression tests will invoke the CLI helper against temporary workflow state rather than inspect source strings. The core red/green sequence is:

1. Persist a run blocked by missing or invalid branch decision.
2. Record an allowed decision through `record-context`.
3. Assert persisted state is `running` and `block` is null.
4. Invoke the next guarded command (`before-dispatch` for finish-agent, and `advance` where the fixture is phase-complete) and assert it proceeds rather than reporting `run_is_blocked`.

Negative tests prove an invalid correction and an unrelated block remain blocked.

EvalOps is not required: this is deterministic workflow state-machine behavior with no AI output target.

### Synchronize governed copies after the live fix

Implementation changes begin in `.ai/workflows/scripts/workflow.py`. After focused and full workflow tests pass, run the repository's workflow template sync/fix path so canonical and project-level derived copies match the live runtime, then verify with the incremental derived-artifact check.

## Risks / Trade-offs

- **[Risk] Over-broad block recognition clears a valid unrelated block** → Require decision-specific structured predicates and add an unrelated-block preservation test.
- **[Risk] Context becomes valid but a legacy block shape is not recognized** → Base recognition on the current runtime-generated next action/type and document that only runtime-owned decision blocks are eligible.
- **[Risk] Dispatch passes but advancement remains blocked** → Assert persisted state normalization and exercise the relevant next guarded command, not just decision validation.
- **[Risk] Live and bootstrap copies drift** → Include sync and incremental distribution checks as required implementation tasks.

## Migration Plan

No data migration is required. Existing active runs recover when users record a valid corrected branch decision after the repair. Rollback consists of reverting the runtime and synchronized template copies; existing run JSON remains schema-compatible.

## Open Questions

None. The repair uses the current allowed decision set and existing decision-specific remediation action.
