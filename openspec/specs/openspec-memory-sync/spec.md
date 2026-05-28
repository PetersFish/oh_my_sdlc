# sdlc-openspec-memory-sync

OpenSpec adapter for the repository memory system. Wraps `sdlc-repository-memory-load` and `sdlc-repository-memory-sync`, preserving the `verify -> memory-sync -> archive` gate while delegating memory operations to the core skills.

## Requirements

### Requirement: OpenSpec memory sync delegates to repository memory system
`sdlc-openspec-memory-sync` SHALL use `sdlc-repository-memory-load` to load relevant repository memory before starting its workflow. It SHALL collect OpenSpec change artifacts (proposal, design, spec, tasks, verify) and pass them as context into the repository memory sync workflow. It SHALL preserve the `verify -> memory-sync -> archive` gate. It SHALL write `openspec/changes/<change-id>/memory-sync.md` as a per-change report.

#### Scenario: OpenSpec change with existing repository memory
- **WHEN** `sdlc-openspec-memory-sync` runs for a verified OpenSpec change and `.ai-memory/` exists
- **THEN** it SHALL first load relevant memory via `sdlc-repository-memory-load`, then collect OpenSpec artifacts, then delegate memory operations to `sdlc-repository-memory-sync`, and finally write the per-change `memory-sync.md` report

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

### Requirement: Post-verify memory sync gate
The `sdlc-openspec-memory-sync` skill SHALL run after a change has been verified and before it is archived, so durable memory can be updated while the change context is still available.

#### Scenario: Verified change needs memory sync
- **WHEN** a user asks to archive a verified OpenSpec change
- **THEN** the skill SHALL inspect the change artifacts, verification evidence, and delegate memory operations via `sdlc-repository-memory-sync` before archive proceeds

### Requirement: Per-change memory sync report
The skill SHALL write `openspec/changes/<change-id>/memory-sync.md` that records the docs changed, the doc types skipped as not applicable, the evidence used, and any remaining gaps before archive.

#### Scenario: Sync completes with updates
- **WHEN** the skill finishes updating memory docs
- **THEN** it SHALL produce a memory-sync report that lists the changed files and the evidence behind each update

### Requirement: Archive gate on missing evidence
The skill SHALL stop the archive flow when required evidence is missing, unless the user explicitly confirms a waiver.

#### Scenario: Verification is missing
- **WHEN** the verification evidence is missing
- **THEN** the skill SHALL not silently continue to archive and SHALL report that the archive is blocked unless the user waives the requirement
