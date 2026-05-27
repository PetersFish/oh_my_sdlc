# repository-memory-init

One-time initialization of `.ai-memory/` in a repository. Creates directory structure, manifest, index, review-queue, discovery-prefs, and gitignore.

## Requirements

### Requirement: Initialize `.ai-memory/` directory structure
`repository-memory-init` SHALL create the `.ai-memory/` directory and all subdirectories: `modules/`, `architecture/`, `decisions/`, `pitfalls/`, `specs/`, `evolution/`, `sync-history/`, `sessions/`, `snapshots/`, `tmp/`, `cache/`.

#### Scenario: First-time initialization on a repository without `.ai-memory/`
- **WHEN** `repository-memory-init` runs on a repository that does not have `.ai-memory/`
- **THEN** it SHALL create `.ai-memory/` and all subdirectories

#### Scenario: Re-running init on a repository that already has `.ai-memory/`
- **WHEN** `repository-memory-init` runs on a repository where `.ai-memory/` already exists
- **THEN** it SHALL preserve all existing files and directories without overwriting them

### Requirement: Create manifest.json
`repository-memory-init` SHALL create `.ai-memory/manifest.json` with the following required fields: `schema_version`, `repository_id`, `memory_version`, `git` (containing `available`, `has_commits`, `head`, `last_synced_commit`, `worktree_state`), `pending_snapshots` (array), and `last_sync` (object or null).

#### Scenario: Initialize manifest in a git repository with commits
- **WHEN** `repository-memory-init` runs in a git repository with at least one commit
- **THEN** manifest SHALL have `git.available = true`, `git.has_commits = true`, `git.head` set to current HEAD, `git.last_synced_commit = null`, `git.worktree_state` reflecting the current state, `pending_snapshots = []`, `last_sync = null`

#### Scenario: Initialize manifest in a git repository without commits
- **WHEN** `repository-memory-init` runs in a git repository with no commits
- **THEN** manifest SHALL have `git.available = true`, `git.has_commits = false`, `git.head = null`, `git.last_synced_commit = null`

#### Scenario: Initialize manifest in a non-git directory
- **WHEN** `repository-memory-init` runs in a directory that is not a git repository
- **THEN** manifest SHALL have `git.available = false`

### Requirement: Create index.json
`repository-memory-init` SHALL create `.ai-memory/index.json` with `schema_version`, `generated_at`, and `entries` (empty array).

#### Scenario: First-time initialization creates empty index
- **WHEN** `repository-memory-init` runs and creates `.ai-memory/`
- **THEN** `.ai-memory/index.json` SHALL contain `schema_version = "1.0"`, `generated_at` set to the current timestamp, and `entries = []`

### Requirement: Create review-queue.json
`repository-memory-init` SHALL create `.ai-memory/review-queue.json` with `items` (empty array).

#### Scenario: First-time initialization creates empty review queue
- **WHEN** `repository-memory-init` runs and creates `.ai-memory/`
- **THEN** `.ai-memory/review-queue.json` SHALL contain `items = []`

### Requirement: Create `.ai-memory/.gitignore`
`repository-memory-init` SHALL create `.ai-memory/.gitignore` that excludes `sessions/`, `snapshots/`, `tmp/`, `cache/`, and `*.local.json`.

#### Scenario: Gitignore excludes local-only directories
- **WHEN** `.ai-memory/.gitignore` is created
- **THEN** it SHALL contain entries for `sessions/`, `snapshots/`, `tmp/`, `cache/`, and `*.local.json`

#### Scenario: Existing gitignore is not overwritten
- **WHEN** `.ai-memory/.gitignore` already exists
- **THEN** `repository-memory-init` SHALL NOT overwrite it

### Requirement: Optional AGENTS.md memory-load reminder
`repository-memory-init` SHALL check for `AGENTS.md` in the repository root. If it exists, `repository-memory-init` SHALL ask the user whether to append a memory-load reminder block. If `AGENTS.md` does not exist, `repository-memory-init` SHALL ask the user whether to create it with the reminder block.

#### Scenario: AGENTS.md exists and user approves
- **WHEN** `AGENTS.md` exists in the repository root and the user approves appending
- **THEN** `repository-memory-init` SHALL append the memory-load reminder block to `AGENTS.md`

#### Scenario: AGENTS.md does not exist and user approves creation
- **WHEN** `AGENTS.md` does not exist and the user approves creation
- **THEN** `repository-memory-init` SHALL create `AGENTS.md` with the memory-load reminder block

#### Scenario: User declines AGENTS.md modification
- **WHEN** the user declines AGENTS.md modification or creation
- **THEN** `repository-memory-init` SHALL proceed without modifying or creating `AGENTS.md`

### Requirement: Init does not modify workflow skills
`repository-memory-init` SHALL NOT modify any workflow skill files (such as `openspec-new-change`, `openspec-apply-change`, `openspec-verify-change`, `openspec-archive-change`). Workflow skill updates are implementation-time changes, not per-repository initialization behavior.

#### Scenario: Init runs without touching skill files
- **WHEN** `repository-memory-init` runs
- **THEN** it SHALL NOT create, modify, or delete any files under `.opencode/skills/`, `.claude/skills/`, or `.cursor/skills/`

### Requirement: Init outputs summary
`repository-memory-init` SHALL output a summary listing created files, skipped existing files, and the AGENTS.md reminder status.

#### Scenario: Successful initialization summary
- **WHEN** `repository-memory-init` completes
- **THEN** it SHALL output a list of created files, skipped files (already existing), and whether the AGENTS.md reminder was added, skipped, or declined

### Requirement: Script CLI for init_memory.py
The `init_memory.py` script SHALL accept `--root` (repository root path) and `--json` (JSON output mode) arguments. It SHALL create the directory structure, write template files, and report results without requiring user interaction.

#### Scenario: Running init_memory.py with JSON output
- **WHEN** `python init_memory.py --root /path/to/repo --json` is executed
- **THEN** it SHALL create `.ai-memory/` structure, write `manifest.json`, `index.json`, `review-queue.json`, `discovery-prefs.json`, `.gitignore`, and output a JSON summary
