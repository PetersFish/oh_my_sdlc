## ADDED Requirements

### Requirement: Roadmap Governed Actions
The workflow runtime SHALL recognize stateful roadmap mutations as governed actions and return valid preflight decisions for them.

#### Scenario: Roadmap insert preflight is recognized
- **WHEN** `workflow.py preflight --action roadmap_insert --subject-type roadmap_item --subject-id <item-id>` runs
- **THEN** the runtime SHALL return a valid preflight decision and SHALL NOT return `unknown_action`

#### Scenario: Roadmap replan preflight is recognized
- **WHEN** `workflow.py preflight --action roadmap_replan --subject-type roadmap_item --subject-id <item-id>` runs
- **THEN** the runtime SHALL return a valid preflight decision and SHALL NOT return `unknown_action`

#### Scenario: Roadmap review requires review phase
- **WHEN** `workflow.py preflight --action roadmap_review --subject-type roadmap_item --subject-id <item-id>` runs for an active run outside `review_roadmap`
- **THEN** the runtime SHALL block with a wrong-phase decision that names the allowed roadmap review phase

#### Scenario: Roadmap non-phase-changing mutations require matching run
- **WHEN** `workflow.py preflight` runs for `roadmap_revise`, `roadmap_cancel`, or `roadmap_reorder`
- **THEN** the runtime SHALL require a matching active run or completed history and SHALL NOT advance the current phase by policy side effect

### Requirement: Roadmap Item Phase Inference
The workflow runtime SHALL infer safe phases for `roadmap_item` subjects when starting or resuming workflow runs.

#### Scenario: New roadmap item starts at create roadmap
- **WHEN** `workflow.py start --subject-type roadmap_item --subject-id <item-id>` runs and no later evidence is available
- **THEN** the runtime SHALL infer `create_roadmap`

#### Scenario: Reviewed roadmap item starts at review roadmap
- **WHEN** a roadmap item has enough evidence to indicate review is the current step
- **THEN** the runtime SHALL infer or preserve `review_roadmap` rather than falling back to `input`

### Requirement: Replanned Roadmap Run Invalidation
The workflow runtime SHALL provide a single-subject primitive for invalidating active runs that are abandoned by roadmap replan.

#### Scenario: Cancel-run removes active run without history
- **WHEN** `workflow.py cancel-run --subject-type roadmap_item --subject-id <item-id> --reason replanned` runs for a matching active roadmap item run
- **THEN** the runtime SHALL remove the matching `active/<run_id>.json` file and SHALL NOT write `history/<run_id>.json`

#### Scenario: Cancel-run clears current pointer when needed
- **WHEN** `cancel-run` removes a run that `current.json` points to
- **THEN** the runtime SHALL clear `current.json` to `{}`

#### Scenario: Cancel-run reports missing run idempotently
- **WHEN** `cancel-run` runs for a roadmap item with no matching active run
- **THEN** the runtime SHALL report a not-found outcome without modifying unrelated active runs

### Requirement: Roadmap Governance Check Coverage
The governance-check command SHALL detect roadmap state that indicates missing workflow governance while remaining read-only.

#### Scenario: Governance-check reports active roadmap item without run
- **WHEN** a roadmap item has `status: active` and no matching active run or done history exists
- **THEN** `workflow.py governance-check` SHALL report an ungoverned roadmap finding with remediation commands and SHALL NOT modify files

#### Scenario: Governance-check reports archived linked item without workflow evidence
- **WHEN** an archived OpenSpec change is linked from a roadmap item and no matching workflow evidence exists
- **THEN** `workflow.py governance-check` SHALL report a finding with explicit runtime remediation commands

#### Scenario: Governance-check ignores roadmap list and init
- **WHEN** roadmap state only reflects read-only listing or bootstrap initialization
- **THEN** `workflow.py governance-check` SHALL NOT report a missing-governance finding for `roadmap list` or `roadmap_init`

### Requirement: Canonical-Run Promotion Preflight
The `openspec_create` preflight SHALL accept a linked active `roadmap_item` run as the canonical run when a roadmap item has been promoted to an OpenSpec change, avoiding duplicate runs.

#### Scenario: Openspec create finds linked roadmap item run
- **WHEN** `workflow.py preflight --action openspec_create --subject-type openspec_change --subject-id <change-id>` runs and a `roadmap_item` active run exists whose `context.change_id` or linked roadmap item frontmatter matches `<change-id>`
- **THEN** the runtime SHALL set the pointer to that roadmap item run, validate the run's phase against `create_change`, and return `allowed: true`

#### Scenario: Openspec create does not create duplicate run after promotion
- **WHEN** promotion has already linked a roadmap item to an OpenSpec change and the roadmap item run is active
- **THEN** `openspec_create` preflight SHALL NOT return `missing_active_run` and SHALL NOT require starting a new `openspec_change` run

#### Scenario: Direct openspec change still creates openspec change run
- **WHEN** no linked roadmap item run exists for the requested change id
- **THEN** `openspec_create` preflight MAY return `missing_active_run` and the orchestrator MAY start a new `openspec_change/<change-id>` run as before
