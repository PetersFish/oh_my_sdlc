## 1. Behavior Tests (TDD — write first, pass after implementation)

Note: this phase now distinguishes contract-level coverage already added for the architecture skeleton from still-pending executable routing and wrapper-integration coverage.

- [x] 1.1 Write test: `flow_type` round-trips in workflow run state — `start`/`resume` preserves `flow_type` in the run JSON, and `validate_run_state` rejects unknown values
- [x] 1.2 Write test: missing `flow_type` causes agent/wrapper to return a structured blocker rather than proceeding
- [x] 1.3 Write contract-level test: normalized result dict uses the shared evidence envelope shape and keeps workflow state mutation inside `workflow.py`
- [ ] 1.3b Write executable routing test: `dev-orchestrator` returns normalized result dict but never directly writes `.ai/workflows/runs/` files; runtime-visible state mutation is only through `workflow.py` commands and hooks
- [x] 1.4 Write test: `complete-phase --exit-criteria-satisfied` fails when required evidence keys declared in the phase definition are missing or empty in run state
- [x] 1.5 Write contract/helper test: parallel package disjointness rules reject shared files or modules and produce a blocker payload
- [ ] 1.5b Write executable routing test: `dev-orchestrator` rejects parallel dispatch when proposed work packages share files or modules and returns that blocker before subagent dispatch
- [x] 1.6 Write test: `sdlc-orchestrator` is manual-trigger only — its description must not auto-match on "new development task", "any new development task", or equivalent generic phrases
- [x] 1.7 Write contract-level test: `test-agent` verification sequence and normalized evidence fields are defined in wrapper/agent contracts
- [ ] 1.7b Write executable routing test: `test-agent` reruns the focused tests claimed by `implement-agent` first, then checks new or changed TDD tests for overfit, then runs broader regression/integration verification, and emits passing or failing verification evidence in normalized form
- [x] 1.8 Write contract-level test: `test-agent` failure routing defaults to `implement-agent`, with ambiguity escalation to `plan-agent`
- [ ] 1.8b Write executable routing test: `test-agent` preserves the implementation slice identifier and blocker evidence across the implement/test loop, and escalates to `plan-agent` only when verification reveals requirement ambiguity or design uncertainty
- [ ] 1.9 Write executable routing test: `dev-orchestrator` does not request `review-agent`, `complete-phase`, or `advance` after `implement-agent` success alone; passing `test-agent` verification evidence is required first
- [x] 1.10 Write contract-level test: specialized agents emit the shared evidence envelope with required top-level fields and `focused_tests` is validated as an array when focused test evidence is present
- [x] 1.11 Write contract-level test: cross-agent handoff artifacts use the required Markdown sections
- [ ] 1.11b Write executable routing test: `dev-orchestrator` forwards `artifacts.handoff_path` to the next agent when cross-agent context is needed
- [x] 1.12 Write contract-level test: raw logs are exposed through `artifacts.raw_log_paths[]` and ignored by deterministic phase-gate decisions
- [ ] 1.12b Write executable artifact test: raw logs are written under the workflow run only when an agent or wrapper retains them by reference

## 2. Design and Contract Artifacts

- [x] 2.1 Update `design.md`: `dev-orchestrator` as a top-level agent (not a subagent of `sdlc-orchestrator`); `dev-orchestrator` may dispatch `plan-agent`/`implement-agent`/`test-agent`/`review-agent`/`finish-agent` without nesting limits
- [x] 2.2 Update `specs/sdlc-orchestrator/spec.md`: orchestrator is downgraded to manual trigger; execution dispatch responsibility migrates to `dev-orchestrator`; orchestrator retains policy and user-interaction boundaries for legacy callers
- [x] 2.3 Define the shared wrapper request/response contract document: inputs (`workflow_run_id`, `phase`, `action`, `flow_type`, artifact paths, constraints), outputs (`agent`, `status`, `phase`, `slice_id`, `flow_type`, `evidence`, `artifacts`, `blockers`, recommended next action)
- [x] 2.4 Define `dev-orchestrator` routing responsibilities: agent selection, work-package splitting, evidence collection, and normalized result return; document phase-agent mapping for `plan-agent`, `implement-agent`, `test-agent`, `review-agent`, `finish-agent`
- [x] 2.5 Define agent behavior contracts: `plan-agent` (brainstorming + TDD-aware plan), `implement-agent` (TDD inner loop plus focused verification evidence emission), `test-agent` (independent verification, ordered focused-rerun and overfit checks, broader regression/integration verification, pass/fail evidence emission, default blocker routing to `implement-agent`), `review-agent` (code review + completion evidence), `finish-agent` (archive/cleanup)
- [x] 2.6 Define wrapper contracts for spec, memory, roadmap, eval, and verification modules; each contract specifies evidence keys, evidence-envelope mapping, handoff artifact references, raw log references, exit criteria, failure modes, and remediation guidance
- [x] 2.7 Define safe parallel dispatch rules: only split independent work packages with disjoint files/modules; document per-package evidence collection and final integration verification; document when to serialize vs parallelize
- [x] 2.8 Document that all wrapped backends preserve current user-visible behavior
- [x] 2.9 Document thin dispatch AOP scope: `before_dispatch` / `after_dispatch` lifecycle hooks around agent execution, with state transitions still owned by `workflow.py`
- [x] 2.10 Document that the full object-oriented state-machine rewrite described in `docs/manual/design/state_machine_design.md` is deferred to a separate change
- [x] 2.11 Define the fixed Markdown structure for cross-agent handoff artifacts and the required metadata fields
- [x] 2.12 Define the raw-log storage policy under `.ai/workflows/runs/<run_id>/logs/<slice_id>/<agent>/...`, including when logs are optional and how they are referenced from structured evidence
- [x] 2.13 Define provider-configurable wrapper routing for `spec` and `memory`, including config keys, provider registry expectations, defaults, capability mapping, and fail-closed behavior
- [x] 2.14 Record provider config locations under `.opencode/`, `.cursor/`, and `.claude/`, and define YAML registry plus Python loader as the provider resolution mechanism

## 3. Implementation

Note: this phase now separates architecture skeleton work already landed (runtime hooks, contract registry, agent prompt files) from still-pending executable routing and backend wrapper integration.

- [x] 3.1 Implement `flow_type` field in `workflow.py` run state schema (`RUN_STATE_KEYS`, `--flow-type` CLI arg, `cmd_start`/`cmd_ensure_run` defaults, `validate_run_state` validation)
- [x] 3.2 Implement evidence-keys validation in `cmd_complete_phase` so that declared `evidence_keys` in the phase YAML are checked against run state evidence before the phase is marked complete
- [x] 3.3 Implement thin dispatch lifecycle conventions: `before_dispatch` records dispatch intent and validates agent/phase/`flow_type`, and `after_dispatch` records normalized agent results inside `workflow.py` state before suggesting deterministic next actions
- [x] 3.4 Add phase-agent mapping and agent-backed execution references to workflow/runtime contracts where applicable, without yet cutting every phase over to `dev-orchestrator` as the sole allowed worker
- [x] 3.5 Update `sdlc-orchestrator` SKILL.md description to manual-trigger only; execution dispatch routing migrates to `dev-orchestrator`
- [x] 3.6 Implement `dev-orchestrator` agent routing logic (agent file: `.opencode/agents/dev-orchestrator.md`; distributed copies in `.claude/agents/` and `.cursor/agents/`)
- [x] 3.7 Implement wrapper contract registry for lifecycle modules
- [ ] 3.7b Implement executable wrapper adapters for lifecycle modules that call current backends and normalize outputs into phase evidence keys
- [x] 3.7c Implement provider configuration loading and validation for wrapper-backed modules, starting with `spec.provider` and `memory.provider`
- [x] 3.7d Implement provider registries/capability maps for `spec` and `memory`, with defaults and fail-closed behavior for unknown or incomplete providers
- [x] 3.7e Add project-level provider config files under `.opencode/sdlc-providers.yaml`, `.cursor/sdlc-providers.yaml`, and `.claude/sdlc-providers.yaml`
- [x] 3.7f Implement a YAML registry plus Python loader that resolves module, provider, and capability selection for wrapper-backed modules
- [x] 3.7g Model memory provider capabilities with `load`, `repository_sync`, and `spec_post_archive_sync`
- [x] 3.8 Implement agent prompt/frontmatter contracts, including shared evidence envelope requirements, handoff structure requirements, and raw-log reference requirements
- [ ] 3.8b Implement executable agent behavior integration so those contracts are enforced by the default dispatch path rather than documentation alone
- [ ] 3.8c Wire `after_dispatch` evidence mapping so normalized agent results satisfy phase-level `evidence_keys` without manual reshaping
- [ ] 3.8d Cut `sdlc-main.yaml` default execution path over to `dev-orchestrator` where this change intends agent-backed routing to be the live path
- [x] 3.9 Do not introduce a full `state_machine.py` rewrite or remap `sdlc-main.yaml` into `plan` / `implement` / `review` / `finalize` / `done` in this change

## 4. Verification

- [ ] 4.1 Verify all behavior tests from Phase 1 pass
- [ ] 4.2 Verify all existing workflow paths (`roadmap_item`, `openspec_change`, `superpowers_direct`) either pass through the new wrappers or remain on the documented legacy path without user-visible behavior drift during migration
- [ ] 4.3 Verify executable wrapper integrations fail closed when required evidence is missing
- [ ] 4.4 Verify configured provider selection works for `spec` and `memory`, including defaults and structured blockers for unknown or unsupported providers
- [ ] 4.5 Verify provider configs remain consistent across `.opencode/`, `.cursor/`, and `.claude/`
