## ADDED Requirements

### Requirement: Corrected Branch Decisions Reconcile Stale Blocks
The workflow runtime SHALL reconcile a persisted branch-decision block when a corrected branch decision is recorded. Reconciliation SHALL occur only when the corrected value is valid for the current workflow gate and the existing block was caused by that branch-decision gate. A successful reconciliation SHALL persist the run as `running`, clear the stale block, and permit normal guarded workflow progress. The runtime SHALL preserve unrelated blocks and SHALL preserve the blocked state for missing or invalid corrections.

#### Scenario: Corrected valid decision unblocks a missing-decision run
- **WHEN** a run is blocked because a required branch decision is missing
- **AND** an allowed branch decision is recorded in workflow context
- **THEN** the runtime SHALL set the run status to `running`
- **AND** the runtime SHALL clear the branch-decision block
- **AND** the next otherwise-valid guarded workflow action SHALL not fail because of the stale block

#### Scenario: Corrected valid decision unblocks an invalid-decision run
- **WHEN** a run is blocked because its recorded branch decision is invalid
- **AND** the branch decision is replaced with an allowed value
- **THEN** the runtime SHALL set the run status to `running`
- **AND** the runtime SHALL clear the branch-decision block
- **AND** the next otherwise-valid guarded workflow action SHALL be allowed to proceed

#### Scenario: Invalid correction remains blocked
- **WHEN** a run is blocked by a branch-decision gate
- **AND** a replacement branch decision is still missing or invalid
- **THEN** the runtime SHALL preserve the blocked status and branch-decision block

#### Scenario: Unrelated block is preserved
- **WHEN** a run is blocked for a reason other than the branch-decision gate
- **AND** an allowed branch decision is recorded
- **THEN** the runtime SHALL update the context value without clearing or replacing the unrelated block

#### Scenario: Main checkout without branch gate is not spuriously unblocked
- **WHEN** a run does not require a branch-finish decision gate
- **AND** a branch decision value is recorded while the run has an unrelated block
- **THEN** the runtime SHALL preserve the unrelated blocked state
