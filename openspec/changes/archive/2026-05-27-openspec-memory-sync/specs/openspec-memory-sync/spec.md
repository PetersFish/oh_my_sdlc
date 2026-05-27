## ADDED Requirements

### Requirement: Post-verify memory sync gate
The `openspec-memory-sync` skill MUST run after a change has been verified and before it is archived, so durable memory can be updated while the change context is still available.

#### Scenario: Verified change needs memory sync
- **WHEN** a user asks to archive a verified OpenSpec change
- **THEN** the skill MUST inspect the change artifacts, verification evidence, and implementation intelligence summary before archive proceeds

### Requirement: Evidence-backed targeted doc updates
The skill MUST classify change evidence into targeted memory deltas and update only the memory docs whose type is supported by current evidence. ADR, pitfall, and module docs MUST be skipped when the current chat, artifacts, verification evidence, implementation summary, diff, or changed files do not show a corresponding durable memory change.

#### Scenario: Decision change touches one module
- **WHEN** the change introduces a durable design decision or module-level responsibility change
- **THEN** the skill MUST update the relevant ADR or module doc instead of rewriting unrelated documentation

#### Scenario: No durable memory change applies
- **WHEN** the current evidence does not show an ADR, pitfall, or module-doc change
- **THEN** the skill MUST skip those doc types and explicitly record them as not applicable in `memory-sync.md`

### Requirement: CodeGraph-first structural analysis
The skill MUST use CodeGraph as the default structural evidence source when it is available, and it MUST fall back to git diff plus targeted file reads when CodeGraph is unavailable.

#### Scenario: CodeGraph is available
- **WHEN** the local CodeGraph index is available
- **THEN** the skill MUST use changed symbols, callers, callees, and impact data to support memory classification

#### Scenario: CodeGraph is unavailable
- **WHEN** the local CodeGraph index is unavailable or stale
- **THEN** the skill MUST continue with git diff and targeted file reads and clearly note the reduced confidence

### Requirement: Per-change memory sync report
The skill MUST write `openspec/changes/<change-id>/memory-sync.md` that records the docs changed, the doc types skipped as not applicable, the evidence used, and any remaining gaps before archive.

#### Scenario: Sync completes with updates
- **WHEN** the skill finishes updating memory docs
- **THEN** it MUST produce a memory-sync report that lists the changed files and the evidence behind each update

### Requirement: Archive gate on missing evidence
The skill MUST stop the archive flow when required evidence is missing, unless the user explicitly confirms a waiver.

#### Scenario: Intelligence summary is missing
- **WHEN** the implementation intelligence summary is missing
- **THEN** the skill MUST not silently continue to archive and MUST report that the archive is blocked unless the user waives the requirement
