## 1. Create discover_modules.py script

- [x] Create `skills/repository-memory-sync/scripts/discover_modules.py`
  - CLI: `--root`, `--json` arguments
  - Recursive walk from root, skip hidden dirs (starts with `.`)
  - Skip dirs matching `exclude_patterns` from `discovery-prefs.json` or
    built-in defaults (`.git`, `.ai-memory`, `node_modules`, `__pycache__`,
    `.venv`, `venv`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`,
    `dist`, `build`, `target`, `.idea`, `.vscode`)
  - Respect `max_depth` from `discovery-prefs.json` (default 5)
  - Candidate rules: direct files ≥ 1 (Rule A) OR direct subdirs ≥ 2 (Rule B)
  - Per candidate, collect:
    - `name`: directory basename
    - `path`: relative path from root
    - `depth`: directory depth from root
    - `file_count`: recursive file count
    - `file_types`: `Counter` of file extensions
    - `has_build_file`: detect `pom.xml`, `build.gradle`, `build.gradle.kts`,
      `package.json`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Cargo.toml`,
      `go.mod`, `Makefile`, `CMakeLists.txt`, `tsconfig.json`, `.csproj`,
      `build.sbt`, `Dockerfile` — return filename or null
    - `has_skill_md`: boolean
    - `frontmatter_name`, `frontmatter_description`: parsed from SKILL.md
      frontmatter, null if not present or parse fails
    - `top_level_files`: first 10 children (files as-is, dirs with `/` suffix),
      sorted alphabetically
    - `children_count`: total direct children (files + subdirs)
    - `disposition`: `new` / `known` / `previously_rejected` from
      cross-referencing against `discovery-prefs.json` module_map
  - Stats output: `total_dirs`, `excluded`, `candidates`, `known`,
    `previously_rejected`, `new`
  - No external dependencies (stdlib only)
- Verify: Run against current repo, confirm `skills/` (Rule B) and each
  `skills/*/` (Rule A) appear as candidates, `src/main/java/`-style paths
  are skipped, stats summary is correct
- Verify: Create mock Java repo with `src/main/java/org/apache/common/` →
  confirm leaf at depth 5 is discovered with `has_build_file: "pom.xml"`

## 2. Create discovery-prefs.schema.json

- [x] Create `skills/repository-memory-sync/schemas/discovery-prefs.schema.json`
  - Required top-level: `schema_version`, `exclude_patterns`, `scan_paths`,
    `max_depth`, `module_map`
  - Module map entries validate `fs_path` (required), `status` (enum:
    accepted/rejected/pending), and conditionally `memory_id`, `memory_path`,
    `confirmed_at`, `reason_rejected`
- Verify: `validate_memory.py` accepts valid discovery-prefs.json, rejects
  invalid (missing `status`, invalid `fs_path`)

## 3. Modify rebuild_index.py for recursive modules/ scanning

- [x] Update `_scan_memory_files()` in `scripts/rebuild_index.py`
  - Change `dir_path.glob("*.md")` to `dir_path.glob("**/*.md")` for
    FORMAL_DIRS iteration
  - Ensure `relative_path` computation works for nested files
    (e.g., `modules/group-name/some-module.md` → relative to memory_dir)
- Verify: Existing tests pass. Add test with nested
  `modules/group-name/some-module.md` → confirm entry appears in index.

## 4. Modify init_memory.py to create discovery-prefs.json

- [x] Update `scripts/init_memory.py`
  - Add creation of `.ai-memory/discovery-prefs.json` with default values
  - Report in summary output under "Created"
  - Do NOT overwrite existing file
- Verify: Init in temp dir → file created with correct defaults. Re-init →
  file preserved.

## 5. Update SKILL.md for repository-memory-sync

- [x] Expand Step 6 with module discovery sub-steps:
  ```
  6a. Run detect_state.py → changed files (existing)
  6b. Run discover_modules.py → candidates with metadata (NEW)
  6c. Cross-reference with discovery-prefs.json → disposition (NEW)
  6d. For known candidates with changed files: auto-update (existing)
  6e. For new/rejected candidates: LLM evaluates, recommends (NEW)
  6f. User confirmation: Accept / Reject / Merge into existing (NEW)
  6g. Write decisions to discovery-prefs.json (NEW)
  6h. For accepted: create module memory file with YAML frontmatter (NEW)
  ```
- [x] Update Per-Type Policy Table: note modules follow discovery-confirm flow
  for discovered candidates (still auto-update for diff-detected changes)
- [x] Add guardrail: \"Do NOT create module memory for candidates marked as
  rejected in discovery-prefs.json without explicit user re-confirmation"
- [x] Add guardrail: \"Modules from discovery must use `evidence_mode: discovery`
  and `linked_sessions` to reference the current session"

## 6. Update SKILL.md for repository-memory-init

- [x] In Workflow Step 2: add `discovery-prefs.json` to the list of files
  created by `init_memory.py`
- [x] In Output section: add `discovery-prefs.json` to the created files
  listing

## 7. Write tests (test_module_discovery.py)

- [x] Test: Rule A — directory with files is candidate, with correct metadata
- [x] Test: Rule B — directory with 2+ subdirs, no files is candidate
- [x] Test: Intermediate path with 1 subdir, 0 files is NOT a candidate
- [x] Test: Hidden directories and deny-list patterns excluded
- [x] Test: max_depth limits traversal
- [x] Test: Candidates correctly marked as new/known/previously_rejected based
- [x] Test: Java deep package scenario — leaf at depth 5 discovered with
- [x] Test: `init_memory.py` creates discovery-prefs.json with defaults
- [x] Test: Re-init does not overwrite existing discovery-prefs.json
- [x] Test: `rebuild_index.py` scans nested modules/ subdirectories via
- [x] Test: `validate_memory.py` accepts valid discovery-prefs.json, rejects
  invalid
- Verify: `python -m pytest tests/test_module_discovery.py -v` passes

## 8. Distribute skill copies to CLI targets

- [x] Run skill-lifecycle-governance install for `repository-memory-sync` and
  `repository-memory-init` to `.opencode/skills/`, `.claude/skills/`,
  `.cursor/skills/`
- Verify: `python -m pytest tests/test_repository_memory_skill_copies.py -v`
  passes

## 9. Run full test suite

- [x] `python -m pytest tests/ -v` — all tests pass
- [x] `python skills/repository-memory-sync/scripts/discover_modules.py --root . --json`
  — produces expected candidate list with valid stats
- Verify: Zero failures, candidate output matches expectations
