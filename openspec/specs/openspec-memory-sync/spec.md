# sdlc-openspec-memory-sync

OpenSpec adapter for the repository memory system. Wraps `sdlc-repository-memory-load` and `sdlc-repository-memory-sync`, preserving the `verify -> memory-sync -> archive` gate while delegating memory operations to the core skills.

## Requirements

### Requirement: OpenSpec memory sync delegates to repository memory system
`sdlc-openspec-memory-sync` SHALL use `sdlc-repository-memory-load` to load relevant repository memory before starting its workflow. It SHALL collect OpenSpec change artifacts (proposal, design, spec, tasks, verify, and archive context when available) and pass them as context into the repository memory sync workflow. It SHALL write `openspec/changes/<change-id>/memory-sync.md` when the change is still active or an equivalent workflow evidence entry when the change has already been archived.

#### Scenario: OpenSpec change with existing repository memory
- **WHEN** `sdlc-openspec-memory-sync` runs for a verified OpenSpec change and `.ai-memory/` exists
- **THEN** it SHALL first load relevant memory via `sdlc-repository-memory-load`, then collect OpenSpec artifacts, then delegate memory operations to `sdlc-repository-memory-sync`, and finally write the per-change `memory-sync.md` report or workflow evidence when the active change directory is no longer available

#### Scenario: OpenSpec change without repository memory
- **WHEN** `sdlc-openspec-memory-sync` runs and `.ai-memory/` does not exist
- **THEN** it SHALL suggest running `sdlc-repository-memory-init` and then proceed with the sync workflow once initialized

### Requirement: Spec ID detection and lineage
`sdlc-openspec-memory-sync` SHALL detect the OpenSpec change ID automatically using the same priority order as `sdlc-repository-memory-sync`: user explicit specification, current change directory path, active OpenSpec changes, and archive path. When multiple active changes form a lineage, it SHALL map them to a single spec memory with lineage metadata.

#### Scenario: Single active OpenSpec change
- **WHEN** `sdlc-openspec-memory-sync` runs and exactly one active OpenSpec change exists
- **THEN** it SHALL automatically use that change ID as the spec context

#### Scenario: Change B refines change A
- **WHEN** active change B explicitly refines active change A
- **THEN** `sdlc-openspec-memory-sync` SHALL create or update a single spec memory with lineage metadata

### Requirement: Workflow-Managed Post-Archive Memory Sync
The SDLC main workflow SHALL treat memory sync as a mandatory post-archive action that must be explicitly resolved before the workflow can complete.

#### Scenario: Workflow registers memory sync after archive
- **WHEN** `archive_change` completes in `sdlc-main`
- **THEN** the workflow runtime SHALL register `memory_sync` as a pending post-archive hook

#### Scenario: Memory sync completes as synced
- **WHEN** memory sync runs and produces evidence of durable memory updates
- **THEN** the workflow runtime SHALL complete `memory_sync` with `synced` resolution

#### Scenario: Memory sync completes as not needed
- **WHEN** a change has no durable facts to write to memory
- **THEN** the workflow runtime SHALL complete `memory_sync` as `not_needed` only if an explicit reason is recorded

#### Scenario: Memory sync is deferred by user
- **WHEN** the user chooses to defer memory sync
- **THEN** the workflow runtime SHALL complete `memory_sync` as `user_deferred` only if an explicit reason and residual risk are recorded

#### Scenario: Workflow cannot complete while memory sync pending
- **WHEN** `memory_sync` remains pending
- **THEN** the workflow SHALL NOT transition to `done`

### Requirement: Per-change memory sync report
The skill SHALL write `openspec/changes/<change-id>/memory-sync.md` when the active change directory is available. When memory sync is performed after archive and the active change directory no longer exists, the workflow runtime SHALL record memory sync evidence in the workflow run instead.

#### Scenario: Sync completes with updates
- **WHEN** the skill finishes updating memory docs before archive
- **THEN** it SHALL produce a memory-sync report that lists the changed files and the evidence behind each update

#### Scenario: Post-archive sync completes with updates
- **WHEN** memory sync completes after archive inside `sdlc-main`
- **THEN** the workflow runtime SHALL record evidence that lists the changed files and the basis for the `memory_sync` resolution

### Requirement: Archive gate on missing evidence
The skill SHALL stop the archive flow when required evidence is missing, unless the user explicitly confirms a waiver.

#### Scenario: Verification is missing
- **WHEN** the verification evidence is missing
- **THEN** the skill SHALL not silently continue to archive and SHALL report that the archive is blocked unless the user waives the requirement
