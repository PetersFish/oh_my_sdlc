## MODIFIED Requirements

### Requirement: OpenSpec memory sync delegates to repository memory system
`openspec-memory-sync` SHALL use `repository-memory-load` to load relevant repository memory before starting its workflow. It SHALL collect OpenSpec change artifacts (proposal, design, spec, tasks, verify) and pass them as context into the repository memory sync workflow. It SHALL preserve the `verify -> memory-sync -> archive` gate. It SHALL write `openspec/changes/<change-id>/memory-sync.md` as a per-change report.

#### Scenario: OpenSpec change with existing repository memory
- **WHEN** `openspec-memory-sync` runs for a verified OpenSpec change and `.ai-memory/` exists
- **THEN** it SHALL first load relevant memory via `repository-memory-load`, then collect OpenSpec artifacts, then delegate memory operations to `repository-memory-sync`, and finally write the per-change `memory-sync.md` report

#### Scenario: OpenSpec change without repository memory
- **WHEN** `openspec-memory-sync` runs and `.ai-memory/` does not exist
- **THEN** it SHALL suggest running `repository-memory-init` and then proceed with the sync workflow once initialized

### Requirement: Spec ID detection and lineage
`openspec-memory-sync` SHALL detect the OpenSpec change ID automatically using the same priority order as `repository-memory-sync`: user explicit specification, current change directory path, active OpenSpec changes, and archive path. When multiple active changes form a lineage, it SHALL map them to a single spec memory with lineage metadata.

#### Scenario: Single active OpenSpec change
- **WHEN** `openspec-memory-sync` runs and exactly one active OpenSpec change exists
- **THEN** it SHALL automatically use that change ID as the spec context

#### Scenario: Change B refines change A
- **WHEN** active change B explicitly refines active change A
- **THEN** `openspec-memory-sync` SHALL create or update a single spec memory with lineage metadata

## REMOVED Requirements

### Requirement: Do not expand into V2 memory layers
**Reason**: This change replaces the MVP with the full V2 system. The restriction against expanding into memory layers, indexes, and compression is no longer applicable because `repository-memory-sync` now implements exactly those capabilities.
**Migration**: The `openspec-memory-sync` skill now delegates to `repository-memory-sync` for memory operations. The MVP guardrail is replaced by the V2 system's per-type policies, review queue, and frontmatter evidence linkage.

### Requirement: Limit durable outputs to ADRs, pitfalls, and module docs
**Reason**: The V2 system supports eight formal memory types: modules, architecture, decisions, pitfalls, specs, evolution, sessions (local), and schemas (validation only). The MVP restriction to three types is superseded.
**Migration**: Existing ADR docs under `docs/decisions/` map to `.ai-memory/decisions/`. Existing pitfall docs under `docs/pitfalls/` map to `.ai-memory/pitfalls/`. Existing module docs under `docs/modules/` map to `.ai-memory/modules/`.