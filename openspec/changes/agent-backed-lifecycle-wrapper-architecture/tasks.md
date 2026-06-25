## 1. Behavior Tests (TDD — write first, pass after implementation)

- [ ] 1.1 Write test: `flow_type` round-trips in workflow run state — `start`/`resume` preserves `flow_type` in the run JSON, and `validate_run_state` rejects unknown values
- [ ] 1.2 Write test: missing `flow_type` causes agent/wrapper to return a structured blocker rather than proceeding
- [ ] 1.3 Write test: `dev-orchestrator` returns normalized result dict but never directly writes `.ai/workflows/runs/` files; state mutation is only through `workflow.py record-evidence`/`complete-phase`/`advance`/`block`
- [ ] 1.4 Write test: `complete-phase --exit-criteria-satisfied` fails when required evidence keys declared in the phase definition are missing or empty in run state
- [ ] 1.5 Write test: `dev-orchestrator` rejects parallel dispatch when proposed work packages share files or modules and returns a blocker
- [ ] 1.6 Write test: `sdlc-orchestrator` is manual-trigger only — its description must not auto-match on "new development task", "any new development task", or equivalent generic phrases

## 2. Design and Contract Artifacts

- [ ] 2.1 Update `design.md`: `dev-orchestrator` as a top-level agent (not a subagent of `sdlc-orchestrator`); `dev-orchestrator` may dispatch `plan-agent`/`implement-agent`/`test-agent`/`review-agent`/`finish-agent` without nesting limits
- [ ] 2.2 Update `specs/sdlc-orchestrator/spec.md`: orchestrator is downgraded to manual trigger; execution dispatch responsibility migrates to `dev-orchestrator`; orchestrator retains policy and user-interaction boundaries for legacy callers
- [ ] 2.3 Define the shared wrapper request/response contract document: inputs (`workflow_run_id`, `phase`, `action`, `flow_type`, artifact paths, constraints), outputs (`status`, `evidence`, `artifacts`, `blockers`, recommended next action)
- [ ] 2.4 Define `dev-orchestrator` routing responsibilities: agent selection, work-package splitting, evidence collection, and normalized result return; document phase-agent mapping for `plan-agent`, `implement-agent`, `test-agent`, `review-agent`, `finish-agent`
- [ ] 2.5 Define agent behavior contracts: `plan-agent` (brainstorming + TDD-aware plan), `implement-agent` (red/green TDD loop), `test-agent` (independent verification/EvalOps capture), `review-agent` (code review + completion evidence), `finish-agent` (archive/cleanup)
- [ ] 2.6 Define wrapper contracts for spec, memory, roadmap, eval, and verification modules; each contract specifies evidence keys, exit criteria, failure modes, and remediation guidance
- [ ] 2.7 Define safe parallel dispatch rules: only split independent work packages with disjoint files/modules; document per-package evidence collection and final integration verification; document when to serialize vs parallelize
- [ ] 2.8 Document that all wrapped backends preserve current user-visible behavior

## 3. Implementation

- [ ] 3.1 Implement `flow_type` field in `workflow.py` run state schema (`RUN_STATE_KEYS`, `--flow-type` CLI arg, `cmd_start`/`cmd_ensure_run` defaults, `validate_run_state` validation)
- [ ] 3.2 Implement evidence-keys validation in `cmd_complete_phase` so that declared `evidence_keys` in the phase YAML are checked against run state evidence before the phase is marked complete
- [ ] 3.3 Implement agent-dispatch handoff fields as an evidence convention (`evidence.agent_phase`) so the workflow runner can know which agent is currently executing
- [ ] 3.4 Update `sdlc-main.yaml` workflow definition to reference agent-backed execution model where applicable
- [ ] 3.5 Update `sdlc-orchestrator` SKILL.md description to manual-trigger only; execution dispatch routing migrates to `dev-orchestrator`
- [ ] 3.6 Implement `dev-orchestrator` agent routing logic
- [ ] 3.7 Implement wrapper contracts for lifecycle modules
- [ ] 3.8 Implement agent behavior contracts

## 4. Verification

- [ ] 4.1 Verify all behavior tests from Phase 1 pass
- [ ] 4.2 Verify all existing workflow paths (`roadmap_item`, `openspec_change`, `superpowers_direct`) pass through wrappers without behavior change
- [ ] 4.3 Verify wrapper contracts fail closed when required evidence is missing
