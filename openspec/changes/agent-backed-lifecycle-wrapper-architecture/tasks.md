## 1. Behavior Tests (TDD — write first, pass after implementation)

- [ ] 1.1 Write test: `flow_type` round-trips in workflow run state — `start`/`resume` preserves `flow_type` in the run JSON, and `validate_run_state` rejects unknown values
- [ ] 1.2 Write test: missing `flow_type` causes agent/wrapper to return a structured blocker rather than proceeding
- [ ] 1.3 Write test: `dev-orchestrator` returns normalized result dict but never directly writes `.ai/workflows/runs/` files; state mutation is only through `workflow.py record-evidence`/`complete-phase`/`advance`/`block`
- [ ] 1.4 Write test: `complete-phase --exit-criteria-satisfied` fails when required evidence keys declared in the phase definition are missing or empty in run state
- [ ] 1.5 Write test: `dev-orchestrator` rejects parallel dispatch when proposed work packages share files or modules and returns a blocker
- [ ] 1.6 Write test: `sdlc-orchestrator` is manual-trigger only — its description must not auto-match on "new development task", "any new development task", or equivalent generic phrases
- [ ] 1.7 Write test: `test-agent` reruns the focused tests claimed by `implement-agent` first, then checks new or changed TDD tests for overfit, then runs broader regression/integration verification, and emits passing or failing verification evidence in normalized form
- [ ] 1.8 Write test: `test-agent` emits verification failures back to `implement-agent` by default, preserves the implementation slice identifier and blocker evidence across the loop, and escalates to `plan-agent` only when verification reveals requirement ambiguity or design uncertainty
- [ ] 1.9 Write test: `dev-orchestrator` does not request `review-agent`, `complete-phase`, or `advance` after `implement-agent` success alone; passing `test-agent` verification evidence is required first
- [ ] 1.10 Write test: specialized agents emit the shared evidence envelope with required top-level fields and `focused_tests` is validated as an array when focused test evidence is present
- [ ] 1.11 Write test: cross-agent handoff artifacts use the required Markdown sections, and `dev-orchestrator` forwards `artifacts.handoff_path` to the next agent when cross-agent context is needed
- [ ] 1.12 Write test: raw logs are exposed through `artifacts.raw_log_paths[]`, stored under the workflow run, and ignored by deterministic phase-gate decisions

## 2. Design and Contract Artifacts

- [ ] 2.1 Update `design.md`: `dev-orchestrator` as a top-level agent (not a subagent of `sdlc-orchestrator`); `dev-orchestrator` may dispatch `plan-agent`/`implement-agent`/`test-agent`/`review-agent`/`finish-agent` without nesting limits
- [ ] 2.2 Update `specs/sdlc-orchestrator/spec.md`: orchestrator is downgraded to manual trigger; execution dispatch responsibility migrates to `dev-orchestrator`; orchestrator retains policy and user-interaction boundaries for legacy callers
- [ ] 2.3 Define the shared wrapper request/response contract document: inputs (`workflow_run_id`, `phase`, `action`, `flow_type`, artifact paths, constraints), outputs (`agent`, `status`, `phase`, `slice_id`, `flow_type`, `evidence`, `artifacts`, `blockers`, recommended next action)
- [ ] 2.4 Define `dev-orchestrator` routing responsibilities: agent selection, work-package splitting, evidence collection, and normalized result return; document phase-agent mapping for `plan-agent`, `implement-agent`, `test-agent`, `review-agent`, `finish-agent`
- [ ] 2.5 Define agent behavior contracts: `plan-agent` (brainstorming + TDD-aware plan), `implement-agent` (TDD inner loop plus focused verification evidence emission), `test-agent` (independent verification, ordered focused-rerun and overfit checks, broader regression/integration verification, pass/fail evidence emission, default blocker routing to `implement-agent`), `review-agent` (code review + completion evidence), `finish-agent` (archive/cleanup)
- [ ] 2.6 Define wrapper contracts for spec, memory, roadmap, eval, and verification modules; each contract specifies evidence keys, evidence-envelope mapping, handoff artifact references, raw log references, exit criteria, failure modes, and remediation guidance
- [ ] 2.7 Define safe parallel dispatch rules: only split independent work packages with disjoint files/modules; document per-package evidence collection and final integration verification; document when to serialize vs parallelize
- [ ] 2.8 Document that all wrapped backends preserve current user-visible behavior
- [ ] 2.9 Document thin dispatch AOP scope: `before_dispatch` / `after_dispatch` lifecycle hooks around agent execution, with state transitions still owned by `workflow.py`
- [ ] 2.10 Document that the full object-oriented state-machine rewrite described in `docs/manual/design/state_machine_design.md` is deferred to a separate change
- [ ] 2.11 Define the fixed Markdown structure for cross-agent handoff artifacts and the required metadata fields
- [ ] 2.12 Define the raw-log storage policy under `.ai/workflows/runs/<run_id>/logs/<slice_id>/<agent>/...`, including when logs are optional and how they are referenced from structured evidence

## 3. Implementation

- [ ] 3.1 Implement `flow_type` field in `workflow.py` run state schema (`RUN_STATE_KEYS`, `--flow-type` CLI arg, `cmd_start`/`cmd_ensure_run` defaults, `validate_run_state` validation)
- [ ] 3.2 Implement evidence-keys validation in `cmd_complete_phase` so that declared `evidence_keys` in the phase YAML are checked against run state evidence before the phase is marked complete
- [ ] 3.3 Implement thin dispatch lifecycle conventions: `before_dispatch` records dispatch intent such as `evidence.agent_phase`, and `after_dispatch` records the shared evidence envelope before requesting `complete-phase` / `advance` / `block` through `workflow.py`
- [ ] 3.4 Update `sdlc-main.yaml` workflow definition to reference agent-backed execution model where applicable
- [ ] 3.5 Update `sdlc-orchestrator` SKILL.md description to manual-trigger only; execution dispatch routing migrates to `dev-orchestrator`
- [ ] 3.6 Implement `dev-orchestrator` agent routing logic
- [ ] 3.7 Implement wrapper contracts for lifecycle modules
- [ ] 3.8 Implement agent behavior contracts, including shared evidence envelope emission, fixed handoff artifact generation, and optional raw log retention by reference
- [ ] 3.9 Do not introduce a full `state_machine.py` rewrite or remap `sdlc-main.yaml` into `plan` / `implement` / `review` / `finalize` / `done` in this change

## 4. Verification

- [ ] 4.1 Verify all behavior tests from Phase 1 pass
- [ ] 4.2 Verify all existing workflow paths (`roadmap_item`, `openspec_change`, `superpowers_direct`) pass through wrappers without behavior change
- [ ] 4.3 Verify wrapper contracts fail closed when required evidence is missing
