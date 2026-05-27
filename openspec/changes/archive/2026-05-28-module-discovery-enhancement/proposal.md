## Why

The current `repository-memory-sync` relies entirely on LLM classification of git diff
changes to decide which modules deserve memory entries. When the LLM groups individual
skills under high-level umbrella modules (e.g., 15 skills grouped into 4 modules),
fine-grained module memories are never created. There is no filesystem-driven mechanism
to discover module candidates, no way to persist user decisions about which directories
should be modules, and no way to detect new modules that appear between syncs. This
leaves potential modules permanently undiscovered unless their files happen to appear
in a git diff.

## What Changes

- **New `discover_modules.py` script**: Recursively scans non-hidden directories
  (default max_depth=5) to discover module candidates. A directory qualifies if it
  contains direct files (leaf module) or 2+ subdirectories (aggregate parent module).
  Collects language-neutral metadata: file extension histogram, build-file detection,
  top-level file listing. Works in any repository — Python, Java, TypeScript, React, Go.
- **New `discovery-prefs.schema.json`**: JSON schema for the discovery preferences file.
- **New `.ai-memory/discovery-prefs.json`**: Persists user decisions about module
  candidates (accepted, rejected, pending) across syncs. Committed to git for team
  sharing. Configurable `exclude_patterns` and `max_depth` override.
- **New `test_module_discovery.py`**: Tests for discovery logic, preferences persistence,
  new-module detection, and multi-language scenarios.
- **Modified `SKILL.md` (repository-memory-sync)**: Step 6 extended with module
  discovery sub-workflow: scan → cross-reference prefs → LLM recommend → user confirm.
  Discovered candidates require user confirmation (unlike auto-update for changed modules).
- **Modified `SKILL.md` (repository-memory-init)**: Documents creation of
  `discovery-prefs.json` during initialization.
- **Modified `init_memory.py`**: Creates `.ai-memory/discovery-prefs.json` with default
  template during initialization.
- **Modified `rebuild_index.py`**: Recursive scanning of `modules/` directory
  (`**/*.md`) to support future nested module groups.
- **Modified spec `repository-memory-sync`**: Adds requirement for filesystem-driven
  module discovery with preference persistence and user confirmation flow.
- **Modified spec `repository-memory-init`**: Adds requirement to create
  `discovery-prefs.json` during init.

## Capabilities

### New Capabilities
- `module-discovery`: Recursive filesystem-driven module candidate discovery with
  language-neutral structural metadata, LLM recommendation, user confirmation, and
  preference persistence across syncs. Works in any repository language or framework.

### Modified Capabilities
- `repository-memory-sync`: Module classification step extended with discovery-based
  candidate flow. Discovered candidates require user confirmation before formal
  memory creation.
- `repository-memory-init`: Init now creates `discovery-prefs.json` alongside other
  memory infrastructure files.

## Impact

- New files: `skills/repository-memory-sync/scripts/discover_modules.py`,
  `skills/repository-memory-sync/schemas/discovery-prefs.schema.json`,
  `tests/test_module_discovery.py`
- Modified files: `skills/repository-memory-sync/SKILL.md`,
  `skills/repository-memory-sync/scripts/rebuild_index.py`,
  `skills/repository-memory-sync/scripts/init_memory.py`,
  `skills/repository-memory-init/SKILL.md`
- New spec: `specs/module-discovery/spec.md`
- Delta specs: `specs/repository-memory-sync/spec.md`,
  `specs/repository-memory-init/spec.md`
- Installed copies in `.opencode/`, `.claude/`, `.cursor/` will need regeneration.
- `discovery-prefs.json` is committed to git (team-shared, like `review-queue.json`).
