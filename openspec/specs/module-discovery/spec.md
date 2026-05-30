# module-discovery

Filesystem-driven module candidate discovery for repository memory sync. Recursively scans non-hidden directories, collects language-neutral structural metadata, and supports preference persistence across syncs.

## Requirements

### Requirement: Discover module candidates via recursive scan
The `discover_modules.py` script SHALL recursively scan non-hidden directories from the repository root (default max_depth=5, configurable via `discovery-prefs.json`). A directory SHALL be emitted as a candidate if it satisfies Rule A (≥ 1 direct file) or Rule B (≥ 2 direct subdirectories). Directories matching `exclude_patterns` SHALL be skipped.

#### Scenario: Leaf module with direct files is discovered
- **WHEN** a directory `skills/markdown-svg-generator/` contains SKILL.md and `.py` files
- **THEN** it SHALL be emitted as a candidate (Rule A satisfied)

#### Scenario: Aggregate parent directory is discovered
- **WHEN** a directory `skills/` contains 15 subdirectories but no direct files
- **THEN** it SHALL be emitted as a candidate (Rule B satisfied)

#### Scenario: Pure intermediate path is skipped
- **WHEN** a directory `src/main/java/` contains exactly 1 subdirectory and no direct files
- **THEN** it SHALL NOT be emitted as a candidate

#### Scenario: Hidden directories are excluded
- **WHEN** a repository contains `.hidden-dir/` and `.ai-memory/`
- **THEN** the script SHALL exclude them from candidate output

#### Scenario: Exclude patterns from discovery-prefs are respected
- **WHEN** `discovery-prefs.json` specifies `exclude_patterns: ["target", "dist"]`
- **THEN** the script SHALL exclude directories matching those patterns in addition to built-in defaults

#### Scenario: max_depth limit is respected
- **WHEN** `discovery-prefs.json` specifies `max_depth: 3` and a directory `a/b/c/d/` is at depth 4
- **THEN** the script SHALL NOT scan or emit candidates beyond depth 3

### Requirement: Collect language-neutral structural metadata per candidate
For each discovered candidate, the script SHALL collect: `file_count`, `file_types` (extension histogram), `has_build_file` (detected build file name or null), `has_skill_md`, `frontmatter_name`, `frontmatter_description` (null if not a skill repo), `top_level_files` (first 10 direct children, dirs suffixed with `/`), `depth`, and `children_count`.

#### Scenario: Java Maven module metadata
- **WHEN** scanning `src/main/java/com/example/service/` containing 20 `.java` files, 8 `.sql` files, and `pom.xml`
- **THEN** the candidate SHALL have `file_types: {".java": 20, ".sql": 8}`, `has_build_file: "pom.xml"`, and `top_level_files` listing `["Service.java", "ServiceImpl.java", "pom.xml", "exception/", "util/"]`

#### Scenario: Skill repo candidate metadata
- **WHEN** scanning `skills/markdown-svg-generator/` with SKILL.md frontmatter containing `name: markdown-svg-generator` and a description
- **THEN** the candidate SHALL have `has_skill_md: true`, `frontmatter_name: "markdown-svg-generator"`, and `frontmatter_description` set to the frontmatter description

#### Scenario: Non-skill repo returns null frontmatter fields
- **WHEN** scanning a directory without SKILL.md
- **THEN** `frontmatter_name` and `frontmatter_description` SHALL be null

### Requirement: Mark candidates by disposition against discovery-prefs
The script SHALL compare each candidate's `path` against `discovery-prefs.json` `module_map` (matched by `fs_path`) and tag it: `new` (not in map), `known` (status: accepted), or `previously_rejected` (status: rejected).

#### Scenario: Previously accepted module is known
- **WHEN** `skills/ocr-router` is in `module_map` with `status: accepted`
- **THEN** the candidate SHALL have `disposition: known`

#### Scenario: Previously rejected is marked with reason
- **WHEN** `scripts/` is in `module_map` with `status: rejected` and `reason_rejected: "Utility scripts, not a module"`
- **THEN** the candidate SHALL have `disposition: previously_rejected`

#### Scenario: Unknown directory is new
- **WHEN** `skills/new-skill/` is NOT in `module_map`
- **THEN** the candidate SHALL have `disposition: new`

### Requirement: Script CLI for discover_modules.py
The `discover_modules.py` script SHALL accept `--root` (repo root path) and `--json` (JSON output mode) arguments. Output SHALL include a `candidates` array and a `stats` object with `total_dirs`, `excluded`, `candidates`, `known`, `previously_rejected`, and `new` counts.

#### Scenario: JSON output with candidates and stats
- **WHEN** `python discover_modules.py --root . --json` is executed
- **THEN** it SHALL output JSON with `candidates` array and `stats` object containing summary counts

#### Scenario: No external dependencies required
- **WHEN** `python discover_modules.py` runs
- **THEN** it SHALL use only Python standard library modules

### Requirement: Persist user module decisions
The sync workflow SHALL write user decisions (accepted/rejected) for each presented candidate to `discovery-prefs.json` during the confirmation step.

#### Scenario: Accept writes to module_map
- **WHEN** user accepts a candidate `skills/new-skill/`
- **THEN** workflow SHALL add entry with `status: accepted`, `memory_id`, `memory_path`, `fs_path`, and `confirmed_at`

#### Scenario: Reject writes to module_map with reason
- **WHEN** user rejects a candidate `scripts/` with reason "Utility scripts"
- **THEN** workflow SHALL add entry with `status: rejected`, `reason_rejected`, and `rejected_at`

#### Scenario: Update existing entry on re-decision
- **WHEN** a candidate is already in `module_map` and the user changes their decision (e.g., from rejected to accepted)
- **THEN** workflow SHALL update the existing entry rather than creating a duplicate

### Requirement: Discovery prefs initialized during memory init
`sdlc-repository-memory-init` SHALL create `.ai-memory/discovery-prefs.json` with default `exclude_patterns`, `max_depth: 5`, `scan_paths: null`, and `module_map: {}`.

#### Scenario: First-time init creates discovery prefs
- **WHEN** `sdlc-repository-memory-init` creates `.ai-memory/` for the first time
- **THEN** `.ai-memory/discovery-prefs.json` SHALL be created with defaults

#### Scenario: Re-init preserves existing prefs
- **WHEN** `init_memory.py` runs and `discovery-prefs.json` already exists
- **THEN** it SHALL NOT overwrite the existing file

### Requirement: Discovery prefs committed to git
`discovery-prefs.json` SHALL be tracked by git (NOT gitignored), consistent with the team-sharing policy applied to `review-queue.json`.

#### Scenario: Discovery prefs not in gitignore
- **WHEN** `.ai-memory/.gitignore` is created by init
- **THEN** `discovery-prefs.json` SHALL NOT appear in ignore patterns

### Requirement: Discover child module candidates for accepted parent modules
The `discover_modules.py` workflow SHALL support a child discovery mode that evaluates candidate directories beneath accepted parent modules recorded in `.ai-memory/discovery-prefs.json`.

#### Scenario: Child discovery uses accepted parent paths
- **WHEN** `discovery-prefs.json` contains an accepted module with a filesystem path
- **THEN** child discovery SHALL scan that path for child candidates using the same hidden-directory and exclude-pattern rules as top-level discovery

#### Scenario: Child discovery reports parent linkage
- **WHEN** child discovery emits a candidate beneath an accepted parent module
- **THEN** the candidate metadata SHALL include the parent module identifier and parent filesystem path

### Requirement: Emit child candidate scoring metadata
The module discovery output SHALL include child candidate scoring metadata sufficient for sync to auto-create high-confidence children and present medium-confidence children interactively.

#### Scenario: Child candidate includes score and confidence band
- **WHEN** a child candidate is emitted by discovery
- **THEN** the candidate metadata SHALL include its numeric score, confidence band, positive signals, and negative signals

#### Scenario: Discovery output remains dependency-free
- **WHEN** child discovery runs
- **THEN** it SHALL use only Python standard library modules

### Requirement: Respect existing discovery preferences for child candidates
The module discovery workflow SHALL compare child candidates against `.ai-memory/discovery-prefs.json` and mark them as `new`, `known`, or `previously_rejected` using the same disposition model as top-level candidates.

#### Scenario: Known child candidate is marked known
- **WHEN** a child path is already accepted in `discovery-prefs.json`
- **THEN** child discovery SHALL emit the candidate with disposition `known`

#### Scenario: Previously rejected child candidate is marked previously rejected
- **WHEN** a child path is rejected in `discovery-prefs.json`
- **THEN** child discovery SHALL emit the candidate with disposition `previously_rejected` and the rejection reason
