## Context

`workflow.py` already owns run state, guarded transitions, hook tracking, and validation for the SDLC workflow runtime. The upcoming agent-backed wrapper architecture depends on a slightly stronger runtime contract so agents can read stable state and return evidence without taking over state-machine concerns.

This change intentionally stays below the wrapper-architecture line. It adds the minimum state and validation features the wrapper change expects, while preserving current command names, run storage layout, and workflow transition behavior.

## Goals / Non-Goals

**Goals:**
- Add explicit `flow_type` state with a backward-compatible default of `spec-flow`
- Allow externally selected `lightweight-flow` only when the user explicitly confirms that choice before workflow progress continues
- Let workflow phases declare `evidence_keys` that the runtime validates during phase completion
- Keep `workflow.py` as the deterministic owner of phase completion and transition checks
- Preserve workflow runtime/template synchronization expectations

**Non-Goals:**
- Splitting `workflow.py` into modules
- Rewriting the runtime into a class-based state machine
- Introducing typed evidence schemas or a general contract registry
- Replacing concrete workers in `sdlc-main.yaml` beyond minimal contract support
- Adding a new top-level `dev-orchestrator` command in this change

## Decisions

**Decision 1: `flow_type` becomes first-class run state**

Every active run stores `flow_type` in its persisted state. `workflow.py start` accepts `--flow-type`, defaults to `spec-flow` when not provided, and `resume` preserves the stored value.

Rationale: the wrapper architecture needs a deterministic field that downstream agents can read instead of re-deriving governance mode from surrounding context.

Alternative considered: infer flow type lazily in each downstream agent. Rejected because different agents could infer differently, making routing nondeterministic.

**Decision 2: `lightweight-flow` is confirmation-gated**

When `workflow.py start` receives `--flow-type lightweight-flow` (typically from an external LLM agent), it creates a run in blocked state with `block.type: user_decision_required`, a message naming the flow type, and `next_allowed` listing the confirmation action. The run must not advance until the confirmation is recorded. Once confirmed, the block clears, `status` becomes `running`, and `flow_type` is set to `lightweight-flow`.

Without `--flow-type`, the runtime defaults to `spec-flow` and starts immediately. The runtime does NOT infer flow type from subject type or other signals — flow type selection is an external decision (LLM, orchestrator, or user).

Rationale: lightweight tasks benefit from ergonomic defaults, but misclassifying a governed task as lightweight would weaken SDLC controls. Requiring external decision + user confirmation keeps the governance gate explicit.

Alternative considered: static code inference from subject type. Rejected because it replaces one deterministic signal with another and doesn't incorporate the richer context an LLM or orchestrator can evaluate.

**Decision 3: `evidence_keys` stay phase-local and shallow**

Phase definitions may declare a simple list of required `evidence_keys`. `complete-phase` checks that each declared key is present and non-empty before marking the phase complete.

Rationale: wrapper and agent outputs need a minimal fail-closed contract now, but typed evidence schemas would add more design surface than this prerequisite change should absorb.

Alternative considered: typed evidence contracts in YAML. Rejected for now because the wrapper contracts are still evolving.

**Decision 4: evidence-key enforcement lives in `complete-phase`**

Recording evidence remains append/update behavior only. The authoritative completion gate stays in `complete-phase`, which now validates both existing exit criteria and declared `evidence_keys`.

Rationale: this preserves the runtime's single point of truth for phase completion and avoids accidental phase completion through evidence recording alone.

Alternative considered: validate evidence keys during `record-evidence`. Rejected because evidence can arrive incrementally and should not be blocked before completion time.

**Decision 5: template sync remains part of the contract**

Any runtime implementation changes under `.ai/workflows/` must be synced with the canonical workflow templates in `skills/sdlc-project-bootstrap/templates/workflow/`.

Rationale: the repository already treats live workflow files and template copies as a governed pair, and this contract change affects that runtime surface.

**Decision 6: typed evidence contracts deferred until wrapper contracts stabilize**

RM-ORCH-008 only requires `evidence_keys` presence and non-empty validation. Typed evidence schemas per phase are explicitly deferred to a later follow-up item once wrapper output formats and agent evidence contracts have stabilized through actual use.

Rationale: introducing typed schemas now would couple the runtime contract to early wrapper output formats that are still evolving. Starting with shallow validation maximizes contract stability while still providing the fail-closed gate wrappers need. If wrapper implementation later shows repeated ambiguity or unsafe evidence interpretation, typed contracts should be added as a separate item.

## Risks / Trade-offs

[Silent governance downgrade] → Mitigation: `lightweight-flow` requires explicit external selection (LLM/orchestrator passes `--flow-type`) plus user confirmation before the run continues.

[Contract too weak for future wrappers] → Mitigation: require `evidence_keys` now, then add typed contracts later only if wrapper implementation proves they are needed.

[Workflow drift between live and canonical copies] → Mitigation: require template sync as part of implementation and verification.

[Extra validation breaking existing flows] → Mitigation: default `flow_type` to `spec-flow`, keep validation narrow, and preserve command/output shapes outside the new checks.

## Migration Plan

1. Extend run-state creation and validation to persist `flow_type` with `spec-flow` default behavior.
2. Extend workflow definition validation to accept `evidence_keys` on phases.
3. Update `complete-phase` to fail closed on missing or empty required evidence keys.
4. Add or update behavior tests for flow-type defaulting, explicit lightweight-flow selection with confirmation, and evidence-key validation.
5. Sync `.ai/workflows/` runtime changes back to canonical workflow templates and verify no drift remains.
