## MODIFIED Requirements

### Requirement: Per-type memory policy
`repository-memory-sync` SHALL apply different update policies per memory type:
`sessions` and `pitfalls` auto-update; `specs` auto-update when a spec/change ID
is identified; `modules` auto-update for modules detected through git diff changes
AND follow a discovery-confirm flow for modules detected through filesystem scan;
`decisions` and `architecture` produce candidates only; `evolution` updates only
with stable commit ranges; `schemas` never update during sync.

#### Scenario: Session memory auto-update
- **WHEN** `repository-memory-sync` processes session evidence
- **THEN** it SHALL auto-update `sessions/` memory without requiring user
  confirmation

#### Scenario: Decision memory candidate
- **WHEN** `repository-memory-sync` detects a potential design decision
- **THEN** it SHALL NOT create a formal `decisions/` memory file; it SHALL
  create a review queue item for user confirmation

#### Scenario: Architecture memory candidate
- **WHEN** `repository-memory-sync` detects a potential architecture change
- **THEN** it SHALL NOT create a formal `architecture/` memory file; it SHALL
  create a review queue item for user confirmation

#### Scenario: Evolution memory with dirty worktree
- **WHEN** `repository-memory-sync` runs on a dirty worktree and detects
  evolution-relevant changes
- **THEN** it SHALL NOT update `evolution/` formal memory; it SHALL record a
  pending timeline entry in sync-history only

## ADDED Requirements

### Requirement: Module discovery via filesystem scan
`repository-memory-sync` SHALL run `discover_modules.py` during module
classification to identify candidates from the filesystem that may not appear
in the git diff. It SHALL compare discovery results against `discovery-prefs.json`
and present new or previously-rejected candidates to the LLM with their
structural metadata for recommendation.

#### Scenario: New candidate with metadata presented to LLM
- **WHEN** `discover_modules.py` returns a candidate with `disposition: new`
  and metadata including `file_types` and `has_build_file`
- **THEN** `repository-memory-sync` SHALL present the candidate with full
  metadata to the LLM for analysis and recommendation

#### Scenario: Known module not in git diff is skipped
- **WHEN** a candidate has `disposition: known` but no files in the current
  git diff range
- **THEN** `repository-memory-sync` SHALL skip the candidate without presenting
  it (no relevant changes)

#### Scenario: Previously rejected candidate re-evaluated
- **WHEN** a candidate has `disposition: previously_rejected`
- **THEN** `repository-memory-sync` SHALL present it with a "previously
  rejected" label and the original `reason_rejected`, allowing user to
  re-evaluate

### Requirement: User confirmation for discovered module candidates
For each new or previously-rejected module candidate, `repository-memory-sync`
SHALL present the candidate with the LLM recommendation and ask the user to
Accept, Reject, or Merge into an existing module.

#### Scenario: User accepts a discovered module
- **WHEN** the user accepts a module candidate
- **THEN** `repository-memory-sync` SHALL create the corresponding memory file
  and update `discovery-prefs.json` with `status: accepted`

#### Scenario: User rejects a discovered module
- **WHEN** the user rejects a module candidate with a reason
- **THEN** `repository-memory-sync` SHALL NOT create a memory file; it SHALL
  record the rejection in `discovery-prefs.json` with `status: rejected` and
  `reason_rejected`

#### Scenario: User merges candidate into existing module
- **WHEN** the user chooses to merge a candidate into an existing module
- **THEN** `repository-memory-sync` SHALL update the existing module memory
  file and record the merge in `discovery-prefs.json`
