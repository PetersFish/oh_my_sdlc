# skill-boundary-cleanup

Updated description and trigger boundaries across 5 overlapping skill pairs to prevent routing ambiguity. No behavioral spec changes — only SKILL.md frontmatter `description` and body content.

## ADDED Requirements

### Requirement: research-general description excludes instant Q&A

The `description` field in `skills/research-general/SKILL.md` SHALL clarify that this skill triggers ONLY when a structured durable research topic lifecycle (`research/` directory, run/rerun/archive/wiki) is required. It SHALL direct instant AI architecture questions to `qa-ai-architecture`.

#### Scenario: Description mentions durable research only
- **WHEN** reading `research-general` description
- **THEN** it references `research/` directory workflow, topic lifecycle, or run/rerun/archive/wiki
- **AND** it does NOT claim to handle AI architecture Q&A or instant technical evaluation without durable artifacts

### Requirement: sdlc-openspec-memory-sync restricts to OpenSpec gate

The `description` field in `skills/sdlc-openspec-memory-sync/SKILL.md` SHALL restrict triggering to OpenSpec verified-before-archive scenarios. It SHALL NOT claim to handle generic `.ai-memory/` sync, session sync, or post-code-change sync.

#### Scenario: Description only mentions OpenSpec verified-before-archive
- **WHEN** reading `sdlc-openspec-memory-sync` description
- **THEN** it references `verified`, `before archive`, `post-verify`, or `OpenSpec change`
- **AND** it does NOT claim to handle general repository memory sync, session sync, or code-change sync

### Requirement: sdlc-repository-memory-sync positioned as primary sync entry

The `description` field in `skills/sdlc-repository-memory-sync/SKILL.md` SHALL identify this skill as the primary entry point for repository memory synchronization. It SHALL claim handling of code changes, git commits, session work, and explicit `.ai-memory/` updates.

#### Scenario: Description claims primary sync role
- **WHEN** reading `sdlc-repository-memory-sync` description
- **THEN** it references code changes, git commits, session work, or `.ai-memory/` updates
- **AND** it does NOT exclude non-OpenSpec scenarios from its scope

### Requirement: study-zybook-notes resolves diagram format ambiguity

The body of `skills/study-zybook-notes/SKILL.md` SHALL declare that final output diagrams use draw.io SVG via `transform-markdown-svg` exclusively. Mermaid SHALL be permitted only as transient inline text sketches during analysis, never as rendered output saved to `images/`.

#### Scenario: Body restricts Mermaid to analysis only
- **WHEN** reading `study-zybook-notes` SKILL.md body
- **THEN** a diagram format section states final diagrams are draw.io SVG
- **AND** Mermaid is described as permitted for inline analysis sketches only

### Requirement: Installed copies match canonical after boundary updates

After boundary updates to canonical SKILL.md files, the corresponding installed copies in `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/` SHALL be synchronized to match.

#### Scenario: Installed copies verified
- **WHEN** running `test_repository_memory_skill_copies.py` after sync
- **THEN** tests for SKILL.md content consistency pass
