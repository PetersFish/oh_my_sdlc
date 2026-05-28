# qa-ai-architecture

AI architecture Q&A coach skill, renamed from `research-ai-architecture` to separate it from the durable-research lifecycle.

## ADDED Requirements

### Requirement: Skill uses qa-ai-architecture name and prefix

The skill directory, frontmatter `name`, and all references SHALL use `qa-ai-architecture`. The `qa-*` prefix SHALL identify this as an instant Q&A / coaching skill that does not manage durable research artifacts.

#### Scenario: Frontmatter name is qa-ai-architecture
- **WHEN** reading `skills/qa-ai-architecture/SKILL.md` frontmatter
- **THEN** `name: qa-ai-architecture` is present

#### Scenario: Old name no longer exists
- **WHEN** searching for `skills/research-ai-architecture/`
- **THEN** the directory does not exist

### Requirement: Skill description declares instant Q&A contract

The frontmatter `description` SHALL identify this skill as an AI architecture Q&A coach for instant technical questions. It SHALL NOT claim to manage `research/` topic lifecycle, durable research artifacts, or the `research-general` durable-research workflow.

#### Scenario: Description excludes durable research
- **WHEN** reading the `description:` field
- **THEN** it mentions AI architecture Q&A, technical decision making, or production review
- **AND** it does NOT reference `research/wishlist`, `research/running`, `research/done`, run/rerun/archive/wiki, or durable research topic lifecycle

### Requirement: Skill body separates itself from research-general

The skill body SHALL clarify that this skill answers architecture questions directly in chat without creating files under `research/`. It SHALL direct users needing a structured research lifecycle to `research-general`.

#### Scenario: Body redirects durable research to research-general
- **WHEN** reading the body of `SKILL.md`
- **THEN** a "When Not to Use" or equivalent section references `research-general` for durable research topics

### Requirement: No installed copies exist for old name

No installed copy directories (`research-ai-architecture`) SHALL remain in `.opencode/skills/`, `.claude/skills/`, or `.cursor/skills/`.

#### Scenario: Installed copies clean
- **WHEN** listing `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`
- **THEN** `research-ai-architecture` does not appear as a directory name
