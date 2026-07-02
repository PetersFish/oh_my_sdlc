## MODIFIED Requirements

### Requirement: Roadmap Lifecycle Hooks
The workflow runtime SHALL coordinate linked roadmap state transitions at OpenSpec workflow boundaries without directly modifying roadmap item files. Hook completion for roadmap lifecycle hooks SHALL validate the observed roadmap item frontmatter state before removing the hook from `pending_hooks`.

#### Scenario: Create change can make linked roadmap item ready
- **WHEN** `create_change` completes OpenSpec artifacts for a linked roadmap item
- **THEN** the workflow SHALL register or run `roadmap_status_ready_if_linked` so the roadmap worker can make the item `ready` when applicable

#### Scenario: Ready hook requires observed ready state
- **WHEN** `roadmap_status_ready_if_linked` is pending for exactly one linked roadmap item
- **AND** the linked roadmap item status is `ready`
- **THEN** `complete-hook roadmap_status_ready_if_linked` SHALL remove the hook from `pending_hooks` and record roadmap hook evidence showing `ready`

#### Scenario: Ready hook blocks stale state
- **WHEN** `roadmap_status_ready_if_linked` is pending for exactly one linked roadmap item
- **AND** the linked roadmap item status is not `ready`
- **THEN** `complete-hook roadmap_status_ready_if_linked` SHALL keep the hook pending and block with `domain_state_mismatch`

#### Scenario: Ready hook handles no linked item idempotently
- **WHEN** `roadmap_status_ready_if_linked` is pending and the change has no linked roadmap item
- **THEN** `complete-hook roadmap_status_ready_if_linked` SHALL complete with `no_linked_item` evidence

#### Scenario: Ready hook blocks multiple linked items
- **WHEN** `roadmap_status_ready_if_linked` is pending and the change has multiple linked roadmap items
- **THEN** `complete-hook roadmap_status_ready_if_linked` SHALL keep the hook pending, block with `user_decision_required`, and report the candidate items

#### Scenario: Apply change can make linked roadmap item active
- **WHEN** `apply_change` starts for a linked roadmap item with `status: ready`
- **THEN** the workflow SHALL register or run `roadmap_apply_start_if_ready` so the roadmap worker can make the item `active` and set `started_at`

#### Scenario: Apply-start hook requires observed active state
- **WHEN** `roadmap_apply_start_if_ready` is pending for exactly one linked roadmap item
- **AND** the linked roadmap item status is `active`
- **AND** the linked roadmap item has a non-empty `started_at`
- **THEN** `complete-hook roadmap_apply_start_if_ready` SHALL remove the hook from `pending_hooks` and record roadmap hook evidence showing `active`

#### Scenario: Apply-start hook blocks stale ready state
- **WHEN** `roadmap_apply_start_if_ready` is pending for exactly one linked roadmap item
- **AND** the linked roadmap item status is `ready`
- **THEN** `complete-hook roadmap_apply_start_if_ready` SHALL keep the hook pending and block with `domain_state_mismatch`

#### Scenario: Apply-start hook handles no linked item idempotently
- **WHEN** `roadmap_apply_start_if_ready` is pending and the change has no linked roadmap item
- **THEN** `complete-hook roadmap_apply_start_if_ready` SHALL complete with `no_linked_item` evidence

#### Scenario: Apply-start hook blocks multiple linked items
- **WHEN** `roadmap_apply_start_if_ready` is pending and the change has multiple linked roadmap items
- **THEN** `complete-hook roadmap_apply_start_if_ready` SHALL keep the hook pending, block with `user_decision_required`, and report the candidate items

#### Scenario: Workflow does not mutate roadmap lifecycle directly
- **WHEN** roadmap ready, active, or done state must change
- **THEN** the workflow runtime SHALL rely on `sdlc-roadmap` or orchestrator-routed roadmap behavior rather than editing roadmap files directly

#### Scenario: Runtime remediation names roadmap worker
- **WHEN** a roadmap lifecycle hook blocks because the linked roadmap item state has not changed
- **THEN** the block or finding SHALL direct the next action to the existing `sdlc-roadmap` worker and SHALL NOT direct users to hand-edit `.roadmap/` files
