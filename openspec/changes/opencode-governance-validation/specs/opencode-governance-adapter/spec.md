## ADDED Requirements

### Requirement: OpenCode Governance Plugin
The system SHALL provide an OpenCode plugin that runs SDLC governance diagnostics at a safe turn-end reconciliation point and surfaces actionable remediation prompts without mutating domain state.

#### Scenario: Plugin runs on idle
- **WHEN** an OpenCode session reaches `session.idle`
- **THEN** the plugin SHALL run `python3 .ai/workflows/scripts/workflow.py --root <project-root> governance-check`

#### Scenario: Plugin does not use file watcher trigger in Phase 1
- **WHEN** files are updated during Phase 1 governance validation
- **THEN** the plugin SHALL NOT use `file.watcher.updated` as a governance trigger

#### Scenario: Plugin remains a thin adapter
- **WHEN** governance diagnostics return findings
- **THEN** the plugin SHALL parse and present the findings without directly modifying Roadmap, OpenSpec, Memory, EvalOps, or workflow state

### Requirement: Governance Prompt Injection
The OpenCode governance plugin SHALL append finding-specific remediation prompts when governance diagnostics block completion.

#### Scenario: Blocking diagnostics append prompt
- **WHEN** `governance-check` returns `block=true` with one or more findings
- **THEN** the plugin SHALL append an actionable prompt through an OpenCode prompt/UI mechanism such as `tui.prompt.append`

#### Scenario: Non-blocking diagnostics stay silent
- **WHEN** `governance-check` returns `block=false`
- **THEN** the plugin SHALL NOT append a remediation prompt

#### Scenario: Prompt includes stop condition
- **WHEN** the plugin appends a remediation prompt
- **THEN** the prompt SHALL instruct the assistant to re-run `workflow.py governance-check` and continue remediation only until `block=false`

#### Scenario: Dangling archive prompt names context
- **WHEN** a finding has type `dangling_archive`
- **THEN** the prompt SHALL include the change id, archive path, and instruction to restore or resume SDLC governance for the archived change

#### Scenario: Pending hooks prompt names hooks
- **WHEN** a finding has type `pending_hooks`
- **THEN** the prompt SHALL include the run id, change id when available, pending hook names, responsible worker categories, and required `complete-hook` follow-up

### Requirement: Prompt Deduplication
The OpenCode governance plugin SHALL avoid repeatedly injecting the same governance prompt in a tight loop.

#### Scenario: Duplicate finding is suppressed
- **WHEN** an idle check returns a finding whose deduplication hash was already injected in the current deduplication scope
- **THEN** the plugin SHALL NOT append another prompt for that same finding

#### Scenario: New finding is injected
- **WHEN** an idle check returns a finding with a new deduplication hash
- **THEN** the plugin SHALL append a remediation prompt for that finding

#### Scenario: Deduplication hash includes stable identity fields
- **WHEN** the plugin computes or consumes a finding hash
- **THEN** the hash SHALL account for at least finding type, change id, run id, archive path, and pending hook names when those fields are present

### Requirement: OpenCode Adapter Validation
The OpenCode adapter SHALL be validated against the target OpenCode mode before Phase 1 is considered complete.

#### Scenario: Idle behavior is verified
- **WHEN** implementation verification runs for the adapter
- **THEN** verification SHALL prove `session.idle` fires after assistant turn completion for the target OpenCode mode

#### Scenario: Prompt mechanism is verified
- **WHEN** implementation verification runs for the adapter
- **THEN** verification SHALL prove the selected OpenCode prompt/UI mechanism appends a visible actionable remediation prompt
