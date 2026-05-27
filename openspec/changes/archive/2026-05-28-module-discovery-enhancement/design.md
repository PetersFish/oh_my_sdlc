## Context

The repository memory system (V2) creates module memories through LLM-driven
classification in Step 6 of the sync workflow. The LLM examines changed files and
session observations, then decides which modules deserve memory entries. This works
for modules already known to the LLM, but misses modules that haven't been touched
by recent commits. A filesystem-driven discovery mechanism is needed to surface
module candidates that would otherwise be invisible.

The discovery mechanism must work across diverse project types: Python skills repos,
Java monoliths with deep package paths, TypeScript monorepos, React component trees,
and Go microservices. It cannot assume flat directory structures or specific file
types.

### Current module classification flow (problem)

```
git diff → changed files → LLM classifies → modules created (auto-update)
```

Problem: Skills like `markdown-svg-generator` that haven't changed in the current
commit range are never surfaced as candidates. In a Java project,
`src/main/java/org/apache/common/` may never appear in a diff if only sibling
packages changed.

## Goals / Non-Goals

**Goals:**
- Add a deterministic script that discovers module candidates from the filesystem,
  working in any repository regardless of language or stack
- Collect language-neutral structural metadata (extension histogram, build files,
  top-level filenames) — the script gathers data, the LLM interprets
- Persist user module classification decisions across syncs
- Detect new modules that appear since the last discovery scan
- Support future nested module groups (subdirectories under `modules/`)

**Non-Goals:**
- Auto-create module memories from discovery without user confirmation
- The script deciding "this is a module" — that remains the LLM's responsibility
- Automatically organize modules into groups (future change)
- Replace LLM classification; discovery is additive, not a replacement

## Decisions

### D1: Separate `discover_modules.py` from `detect_state.py`

**Decision:** Create a standalone `discover_modules.py` script rather than
extending `detect_state.py`.

**Rationale:** `detect_state.py` focuses on git state and OpenSpec detection.
Module discovery is a filesystem concern, not a git concern. Separation follows
single responsibility and allows discovery to run independently of git state.

**Alternatives considered:**
- Extend `detect_state.py`: conflates git and filesystem scanning, harder to
  test independently.

### D2: `discovery-prefs.json` as a standalone file

**Decision:** Store module discovery preferences in `.ai-memory/discovery-prefs.json`
rather than adding a section to `manifest.json`.

**Rationale:** `manifest.json` tracks sync runtime state (last_synced_commit,
pending_snapshots). Discovery preferences are user knowledge, not derived state.
Separation keeps manifest schema stable and allows discovery-prefs to evolve
independently.

**Alternatives considered:**
- Add `module_map` to `manifest.json`: bloats manifest, mixes concerns, requires
  schema version bump.

### D3: User confirmation required for discovered candidates

**Decision:** Modules discovered via filesystem scan require user confirmation before
creating formal memory. This departs from the existing auto-update policy for modules
(which applies only to modules detected through git diffs).

**Rationale:** Discovery may surface directories that are not meaningful modules
(e.g., `scripts/`, deprecated packages, or build output dirs). The LLM recommends
but the human decides. This mirrors the `decisions`/`architecture` candidate flow.

**Alternatives considered:**
- Auto-create from discovery: risks creating module memories for non-modules.
- Only LLM decides (no confirmation): LLM may misclassify without human correction.

### D4: Recursive scan with content-based candidate rules

**Decision:** The discovery script recursively scans non-hidden directories (default
`max_depth=5`, configurable). A directory becomes a candidate if it satisfies either:

- **Rule A (leaf module):** Contains ≥ 1 direct file
- **Rule B (aggregate parent module):** Contains ≥ 2 direct subdirectories

The script does NOT decide "is this a module?". It flags candidates based on
structural heuristics and collects neutral metadata. The LLM interprets.

Pseudo-logic:

```
for each dir in recursive_walk(root, max_depth=5):
    skip if hidden or matches exclude_patterns
    if dir.direct_files ≥ 1 or dir.direct_subdirs ≥ 2:
        emit candidate
    always recurse into subdirectories (for nested module discovery)
```

**Rationale:** Rule A catches leaf modules in any language (a Java package with
.java files, a React component dir with .tsx files, a skill dir with SKILL.md).
Rule B catches aggregate parents like `skills/` (15 subdirs), `packages/` (5+ monorepo
packages), `src/main/java/org/` (multiple sub-packages). Pure intermediate paths
like `src/main/java/` (0 files, 1 subdir) are skipped. Rule B threshold of 2 avoids
false positives from accidentally-nested single directories.

**Coverage examples:**

```
Java deep packages:
  src/main/java/org/apache/common/   → .java ≥ 1 → Rule A → candidate ✓
  src/main/java/org/apache/          → 0 files, 1 subdir → skip

Monorepo:
  packages/                          → 5 subdirs → Rule B → candidate ✓
  packages/auth-service/             → .ts files ≥ 1 → Rule A → candidate ✓

Skills repo:
  skills/                            → 15 subdirs → Rule B → candidate ✓
  skills/markdown-svg-generator/     → SKILL.md present → Rule A → candidate ✓

Pure intermediate paths:
  src/          → 0 files, 1 subdir (main) → skip
  src/main/     → 0 files, 1 subdir (java) → skip
  src/main/java/→ 0 files, 1 subdir (org)  → skip
```

**Alternatives considered:**
- Flat first-level only: misses all Java deep packages, monorepo sub-packages.
- Walk with no depth limit: could traverse into `node_modules` or `__pycache__` forever.
- Scan by file extension: requires hardcoding language-specific extensions, fragile.

### D5: Language-neutral structural metadata

**Decision:** The script collects metadata that applies to any language:

| Field | Type | Purpose |
|-------|------|---------|
| `file_count` | int | Recursive file count |
| `file_types` | dict | Extension histogram: `{".java": 20, ".sql": 8}` |
| `has_build_file` | str\|null | Detected build/config file name |
| `has_skill_md` | bool | SKILL.md present (skill repos only) |
| `frontmatter_*` | str\|null | Parsed from SKILL.md frontmatter |
| `top_level_files` | list | First 10 direct children (files + dirs with `/`) |
| `depth` | int | Directory depth from root |
| `children_count` | int | Count of direct children (files + subdirs) |

The script detects these build files: `pom.xml`, `build.gradle`, `build.gradle.kts`,
`package.json`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Cargo.toml`, `go.mod`,
`Makefile`, `CMakeLists.txt`, `tsconfig.json`, `.csproj`, `build.sbt`, `Dockerfile`.

**Rationale:** The script gathers data; the LLM interprets. An LLM seeing
`file_types: {".java": 20, ".sql": 8}` and `has_build_file: "pom.xml"` can conclude
"this is a Java Maven module" without the script needing to know Java.

### D6: `rebuild_index.py` recursive scan of `modules/`

**Decision:** `_scan_memory_files()` in `rebuild_index.py` uses `**/*.md` glob
instead of `*.md` for FORMAL_DIRS. This allows future nested module groups
(e.g., `modules/repository-memory-system/repository-memory-init.md`) without
breaking index generation.

**Rationale:** The user plans to organize skills into groups. Recursive scanning is
a one-line change that gates nothing today but prevents index breakage when groups
are introduced.

### D7: `discovery-prefs.json` committed to git

**Decision:** `discovery-prefs.json` is committed to git (like `review-queue.json`),
not gitignored (like `sessions/`). User confirmed team sharing is desired.

### Data Flow

```
discover_modules.py                          discovery-prefs.json
      │                                            │
      │ recursive scan (max_depth=5)                │ load module_map
      │ Rule A: direct files ≥ 1                    │ load exclude_patterns
      │ Rule B: direct subdirs ≥ 2                  │ load max_depth override
      │                                            │
      ▼                                            ▼
  candidates + metadata                        ┌─────────────┐
  [{name, path, depth,                           │ disposition  │
    file_types, has_build_file,              ──► │  - new       │
    top_level_files, disposition}]               │  - known     │
                                                 │  - prev_rej  │
                                                 └──────┬──────┘
                                                        │
     ┌──────────────────────────────────────────────────┘
     ▼
  LLM analyzes metadata, recommends
  (Accept as independent / Reject / Merge into existing)
     │
     ▼
  User confirms (Accept / Reject / Merge)
     │
     ├── Accept  → create modules/<name>.md + update discovery-prefs.json
     ├── Reject  → update discovery-prefs.json (status: rejected)
     └── Merge   → update existing module memory + update discovery-prefs.json
```

### Updated Sync Step 6

```
6a. Run detect_state.py → changed files (existing)
6b. Run discover_modules.py → candidates with metadata (NEW)
6c. Cross-reference with discovery-prefs.json → disposition (NEW)
6d. For known candidates with changed files → auto-update (existing)
6e. For new/rejected candidates → LLM evaluates metadata, recommends (NEW)
6f. User confirmation → Accept/Reject/Merge (NEW)
6g. Write decisions to discovery-prefs.json (NEW)
6h. For accepted: create module memory file (NEW)
```

## Risks / Trade-offs

- **Token cost**: Deep repos may produce many candidates (e.g., 50+). Mitigation:
  known modules skip confirmation; max_depth=5 caps traversal; LLM only reviews
  new/rejected candidates.
- **Parent module noise**: `skills/` flagged as aggregate parent may conflict with
  a user preferring flat structure. Mitigation: user can reject any candidate.
- **max_depth limitation**: Very deep package structures (>5 levels) may be
  truncated. Mitigation: configurable via `discovery-prefs.json`.
- **Build file detection**: Non-standard build systems won't be recognized (e.g.,
  Bazel `BUILD` files). Mitigation: `top_level_files` still surfaces unusual files;
  LLM can infer from filenames. Detection list is extensible.
- **Rule B false positives**: A legitimate intermediate path with 2+ subdirs but
  no files of its own will be flagged. Mitigation: LLM can recognize and recommend
  rejection; no memory is created without user confirmation.

## Open Questions

None — all design points resolved through user discussion.
