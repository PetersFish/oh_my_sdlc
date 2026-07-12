# Repository Memory Structural Reconciliation Design

## Context

The repository memory system currently behaves primarily as an additive, change-driven summarizer. It can discover candidate directories and refresh existing memory content after code changes, but it does not reliably reconcile the memory model against the current repository structure.

This creates several concrete integrity failures:

- `skills/sdlc-orchestrator` has been deleted, but `.ai/memory/discovery-prefs.json` and `.ai/memory/modules/skills/sdlc.md` still describe it as an active skill.
- Multiple canonical skills are grouped into aggregate memories such as `modules/skills/sdlc.md` and `modules/skills/transform.md`, preventing precise ownership, deletion cleanup, and package-level documentation.
- Repository-level `scripts/` are not represented as first-class memory modules.
- `.ai` is excluded from discovery, so the modular workflow runtime under `.ai/workflows/scripts/workflow_runtime/` and its definition under `.ai/workflows/definitions/` cannot be discovered or owned by memory.
- `discovery-prefs.json` defines `scan_paths`, but `discover_modules.py` does not use it and always scans from the repository root.
- Skill support directories such as `scripts/`, `templates/`, `schemas/`, `references/`, and `tests/` influence discovery scoring but are not consistently described in the resulting skill memory.
- Deleted, renamed, or structurally changed modules are not reconciled against prior registry state.

The result is a memory graph that can remain syntactically valid while becoming structurally stale. Agents may then load obsolete skills, miss runtime scripts, misunderstand source-versus-derived ownership, or update the wrong aggregate memory.

This change makes repository memory a desired-state model of the canonical repository structure rather than an append-only record of previously discovered modules.

## Goals / Non-Goals

**Goals:**

- Reconcile active memory modules against the current canonical repository structure on every memory refresh.
- Detect and handle added, modified, structurally changed, renamed, and deleted modules.
- Ensure every canonical skill directory containing `SKILL.md` has exactly one active memory module.
- Make one skill package the default memory ownership boundary.
- Describe each skill package's `SKILL.md`, `scripts/`, `templates/`, `schemas/`, `references/`, and `tests/` content when present.
- Establish repository-level `scripts/` as first-class memory modules.
- Establish the workflow runtime and workflow definition as a first-class memory module despite `.ai` remaining excluded by default.
- Make configured `scan_paths` operational and support path-aware exclusions.
- Remove active memory references to deleted `skills/sdlc-orchestrator` while preserving historical decisions and archived artifacts.
- Distinguish canonical source modules from mechanically derived copies.
- Validate that memory ownership is complete, non-overlapping, and consistent with the filesystem.
- Update root `AGENTS.md` workflow sync guidance to reflect the modular workflow runtime and live-to-template source direction.

**Non-Goals:**

- Do not treat every individual source file as a separate memory module.
- Do not automatically create child memory modules for every skill script.
- Do not scan runtime outputs such as `.ai/workflows/runs/`, `.ai/memory/`, or `.ai/roadmap/` as code modules.
- Do not create independent memory modules for `.opencode/`, `.claude/`, or `.cursor/` distributed skill copies.
- Do not delete historical decisions, archived specs, archived plans, run history, or roadmap history merely because a live module was retired.
- Do not introduce an external database or a new memory storage format.
- Do not require LLM-based rename detection for deterministic refresh correctness.
- Do not redesign the public invocation contract of the repository memory skills beyond the minimum options required for structural reconciliation.

## Decisions

### Decision 1: Repository Memory Is a Desired-State Model

A memory refresh must derive the expected active module set from the current canonical repository structure and reconcile that set against the prior memory registry.

The refresh pipeline becomes:

```text
canonical repository inventory
    + previous module registry
    + changed-file evidence
    -> structural diff
    -> memory reconciliation
    -> validation
    -> index rebuild
```

Changed-file evidence remains useful for selecting which content requires semantic refresh, but it is not sufficient to determine whether the module registry is correct.

Every refresh must at least perform deterministic structural reconciliation, even when the changed-file set is narrow.

The structural diff must classify modules as:

- `added`
- `modified`
- `structure_changed`
- `renamed`
- `deleted`
- `unchanged`

`modified` means content changed without changing the owned package structure. `structure_changed` includes support-directory additions/removals and owned-path changes. `renamed` may be identified deterministically when explicit migration metadata or a high-confidence one-to-one path move is available. Ambiguous cases must fall back to one `deleted` plus one `added` result rather than guessing.

### Decision 2: One Canonical Skill Package Equals One Memory Module

Every canonical directory matching:

```text
skills/<skill-name>/SKILL.md
```

must have exactly one active memory module:

```text
.ai/memory/modules/skills/<skill-name>.md
```

The memory id is:

```text
skills/<skill-name>
```

The module owns the complete canonical skill package:

```text
skills/<skill-name>/
```

This replaces prefix-based aggregation such as:

```text
skills/sdlc-* -> modules/skills/sdlc.md
skills/transform-* -> modules/skills/transform.md
```

`modules/skills.md` remains a parent index and high-level overview. It must summarize and link active child skill modules but must not substitute for them.

Existing aggregate memories such as `modules/skills/sdlc.md` and `modules/skills/transform.md` must be migrated. Their durable skill-specific knowledge must be distributed into the corresponding per-skill modules. After migration they must either be removed or converted into non-owning category indexes. They must not retain ownership of canonical skill paths.

### Decision 3: A Skill Module Describes the Entire Skill Package

A generated or refreshed skill memory must describe all package sections that exist:

- `SKILL.md` — entry contract, invocation scope, inputs, outputs, and operational rules.
- `scripts/` — script responsibilities, CLI entrypoints, side effects, read/write paths, and callers.
- `templates/` — template purpose, source/derived status, and installation targets.
- `schemas/` — schema purpose, ownership, and validation role.
- `references/` — runtime reference material and how it is consumed.
- `tests/` — package-local tests and repository tests associated with the skill.

The canonical skill module frontmatter should support structured package metadata:

```yaml
---
id: skills/sdlc-project-bootstrap
type: module
title: SDLC Project Bootstrap
parent_id: skills
lifecycle_status: active
owned_paths:
  - skills/sdlc-project-bootstrap
entry_paths:
  - skills/sdlc-project-bootstrap/SKILL.md
script_paths:
  - skills/sdlc-project-bootstrap/scripts
template_paths:
  - skills/sdlc-project-bootstrap/templates
test_paths:
  - tests/test_sdlc_project_bootstrap.py
derived_targets:
  - .opencode/skills/sdlc-project-bootstrap
  - .claude/skills/sdlc-project-bootstrap
  - .cursor/skills/sdlc-project-bootstrap
---
```

Empty optional lists may be omitted.

A script inside a skill does not become a separate memory module by default. It may become a child module only when it has an independently governed lifecycle, is reused across multiple packages, exposes a substantial standalone CLI, or has a distinct test and state model.

### Decision 4: Repository-Level Scripts Are First-Class Modules

Repository-level scripts under `scripts/` must be represented by memory.

The parent module is:

```text
.ai/memory/modules/scripts.md
```

Complex script groups may receive child modules under:

```text
.ai/memory/modules/scripts/
```

The default grouping boundary is a cohesive operational responsibility, not one file per module. For example:

```text
scripts/derived-artifact-sync
scripts/repository-governance
```

A scripts module must document:

- owned script paths;
- public commands and arguments;
- side effects;
- canonical and derived path relationships;
- hooks and agents that invoke it;
- tests covering the contract;
- failure and rollback behavior.

Top-level utility scripts that do not justify an independent child module remain described in `modules/scripts.md`.

### Decision 5: Workflow Runtime Is a First-Class Module

The workflow runtime must be represented independently from skill memories.

Create:

```text
.ai/memory/modules/workflow.md
.ai/memory/modules/workflow/runtime.md
```

The runtime module owns:

```text
.ai/workflows/scripts/workflow.py
.ai/workflows/scripts/workflow_runtime/
.ai/workflows/definitions/sdlc-main.yaml
```

It must describe:

- `workflow.py` as the stable executable facade;
- the responsibility of each `workflow_runtime` module;
- state persistence ownership;
- workflow definition ownership;
- dispatch, lifecycle, policy, and governance contracts;
- authoritative tests;
- live-source to bootstrap-template synchronization.

The corresponding files under:

```text
skills/sdlc-project-bootstrap/templates/workflow/
```

are derived bootstrap assets. They are related paths but are not separately owned behavior sources.

### Decision 6: `.ai` Remains Excluded by Default but Supports Explicit Scan Roots

The repository must not globally scan `.ai` because it contains runtime state and generated governance artifacts.

Instead, `scan_paths` becomes operational and defines explicit canonical discovery roots.

Recommended default repository configuration:

```json
{
  "scan_paths": [
    "skills",
    "scripts",
    "agents",
    ".ai/workflows/scripts",
    ".ai/workflows/definitions",
    "tests"
  ]
}
```

The discovery implementation must:

- scan each configured root independently;
- skip missing optional roots without failing;
- deduplicate nested roots;
- retain repository-relative candidate paths;
- prevent walking outside the repository root;
- preserve legacy root scanning when `scan_paths` is null.

The current `BUILTIN_EXCLUDE` behavior may continue excluding `.ai` during root-wide scanning. Explicit scan roots beneath `.ai` override the ancestor exclusion only for that exact configured subtree.

### Decision 7: Exclusions Are Repository-Relative and Path-Aware

Exclusion matching must support repository-relative paths and glob-style patterns, not only child basenames.

Valid examples include:

```text
.ai/workflows/runs
.ai/memory
.ai/roadmap
**/__pycache__
**/.pytest_cache
```

A path is excluded when either:

- its basename matches a legacy simple-name exclusion; or
- its repository-relative POSIX path matches an exact path or configured glob.

Explicit scan roots must still honor exclusions inside those roots.

### Decision 8: Deleted Modules Are Retired From the Active Graph

When an accepted module path no longer exists, refresh must not leave it active.

For a deleted canonical skill:

- remove its active `module_map` entry or mark it `retired` outside the active map;
- remove it from parent index child lists;
- remove its paths from all active `owned_paths` and `path_hints`;
- remove present-tense operational guidance that instructs agents to use it;
- preserve historical decisions, archived artifacts, and prior sync history;
- record retirement metadata when a durable module file is retained.

A retained retired module must use:

```yaml
lifecycle_status: retired
retired_at: YYYY-MM-DD
superseded_by: []
```

Retired modules must not be returned by normal active-memory loading unless explicitly requested for history.

For the existing `skills/sdlc-orchestrator` deletion, this change must:

- remove the active entry from `.ai/memory/discovery-prefs.json`;
- remove it from current `skills/sdlc` ownership and guidance;
- preserve archived design, plan, OpenSpec, roadmap, and run-history references as historical evidence;
- avoid deleting those historical artifacts.

### Decision 9: Refresh Must Detect Package Structure Changes

A module fingerprint must include more than direct file modification timestamps.

For skill packages, the structural fingerprint must include at least:

- canonical module path;
- `SKILL.md` presence;
- top-level support directories present;
- sorted relative file inventory for governed package sections;
- optionally content hashes for deterministic comparison.

Adding or removing `scripts/`, `templates/`, `schemas/`, `references/`, or `tests/` must produce `structure_changed`, even if no previously owned source file was modified.

This ensures a new script under an existing skill updates that skill's memory package description.

### Decision 10: Canonical and Derived Paths Have Different Memory Semantics

Canonical sources include:

```text
skills/<skill-name>/
scripts/
agents/
.ai/workflows/scripts/
.ai/workflows/definitions/
```

Derived copies include:

```text
.opencode/skills/
.claude/skills/
.cursor/skills/
skills/sdlc-project-bootstrap/templates/workflow/
```

A derived-only change must not create a new behavior module or duplicate semantic memory. It may update synchronization evidence or produce a drift finding.

When both a canonical source and its derived copy change, semantic memory is attributed to the canonical source module.

### Decision 11: Module Registry Entries Must Be One-to-One

The active module registry must satisfy:

- each canonical skill path maps to exactly one memory id;
- each active memory id has at least one existing canonical owned path;
- no canonical owned path is owned by more than one active module;
- parent indexes do not own child canonical paths;
- derived paths are never primary owned paths;
- active registry entries cannot reference missing memory files;
- active memory files cannot reference deleted owned paths.

The registry schema may retain `module_map`, but accepted entries should become explicit one-to-one records. For example:

```json
"skills/sdlc-project-bootstrap": {
  "status": "accepted",
  "memory_id": "skills/sdlc-project-bootstrap",
  "memory_path": "modules/skills/sdlc-project-bootstrap.md",
  "parent_id": "skills"
}
```

### Decision 12: Reconciliation Is Deterministic; Semantic Refresh Is Selective

Structural inventory, diffing, registry updates, retirement, index rebuilding, and validation must be deterministic Python behavior.

LLM-assisted content refresh may still be used to summarize changed implementation semantics, but deterministic reconciliation decides:

- which modules exist;
- which paths they own;
- whether a module is active or retired;
- which package sections are present;
- which parent indexes include each module.

This prevents an LLM from preserving a deleted skill or omitting a newly added script package.

### Decision 13: Validation Is a Required Gate

Memory sync must fail before reporting success when any of these conditions hold:

- a canonical skill lacks an active memory module;
- an active skill module points to a missing skill directory;
- two active modules own the same canonical path;
- a skill's existing support directory is absent from its package metadata and generated structure section;
- a deleted module remains in an active parent index;
- configured scan roots were ignored;
- workflow runtime has no active memory owner;
- repository-level scripts have no active memory owner;
- a derived path is registered as an independent canonical module.

Validation output must be machine-readable and include finding type, module id, path, and recommended repair action.

### Decision 14: Existing Memory Is Migrated, Not Blindly Regenerated

The initial rollout must migrate current durable knowledge.

Migration steps:

1. Inventory all canonical skills.
2. Create one target memory module per canonical skill.
3. Split relevant content from aggregate memories into target modules.
4. Remove deleted `sdlc-orchestrator` from the active graph.
5. Create scripts and workflow runtime parent/child modules.
6. Rewrite `discovery-prefs.json` to one-to-one mappings.
7. Rebuild parent indexes.
8. Validate ownership and active paths.

Existing decisions and pitfalls remain independent memory artifacts and are not duplicated into every module. Skill modules may link them by id.

### Decision 15: Workflow Sync Guidance Must Reflect the Modular Runtime

Root `AGENTS.md` workflow synchronization guidance must identify these live authoritative inputs:

```text
.ai/workflows/scripts/workflow.py
.ai/workflows/scripts/workflow_runtime/**/*.py
.ai/workflows/definitions/sdlc-main.yaml
```

It must state that corresponding files under:

```text
skills/sdlc-project-bootstrap/templates/workflow/
```

are derived bootstrap templates.

Routine synchronization must prefer:

```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
```

The lower-level `sync_templates.py` command remains a workflow-only escape hatch.

The existing `template-sync-and-distribution` memory decision must also be updated so "source of truth" is unambiguous:

- live `.ai/workflows/` is the workflow behavior source;
- canonical `skills/` content is the distribution source for installed copies;
- installed copies are derived and never edited directly.

## Proposed Memory Layout

```text
.ai/memory/modules/
├── skills.md
├── skills/
│   ├── <one canonical skill per file>.md
│   └── ...
├── scripts.md
├── scripts/
│   ├── derived-artifact-sync.md
│   └── ...
├── workflow.md
├── workflow/
│   └── runtime.md
├── agents.md
└── tests.md
```

Category files are indexes and summaries. Leaf modules own canonical paths.

## Invariants

1. Every canonical `skills/*/SKILL.md` has exactly one active memory module.
2. A skill module owns the entire canonical skill package.
3. Existing skill support directories are represented in that module's metadata and body.
4. Deleted canonical modules cannot remain active.
5. Repository-level scripts have memory ownership.
6. Workflow runtime and definitions have memory ownership.
7. `.ai` remains excluded from broad scans, but explicit workflow scan roots are honored.
8. Parent indexes summarize children without owning child paths.
9. Derived copies never receive independent behavior modules.
10. Structural reconciliation runs on every refresh.
11. Ambiguous rename detection never silently guesses.
12. Historical artifacts survive live module retirement.

## Error Model

Structural reconciliation should emit findings such as:

```json
{
  "type": "stale_active_module",
  "module_id": "skills/sdlc-orchestrator",
  "path": "skills/sdlc-orchestrator",
  "recommended_action": "retire_module"
}
```

```json
{
  "type": "missing_skill_memory",
  "module_id": "skills/sdlc-project-bootstrap",
  "path": "skills/sdlc-project-bootstrap",
  "recommended_action": "create_module"
}
```

```json
{
  "type": "unowned_support_directory",
  "module_id": "skills/sdlc-project-bootstrap",
  "path": "skills/sdlc-project-bootstrap/scripts",
  "recommended_action": "refresh_package_structure"
}
```

```json
{
  "type": "duplicate_owned_path",
  "path": "skills/sdlc-project-bootstrap",
  "module_ids": [
    "skills/sdlc",
    "skills/sdlc-project-bootstrap"
  ],
  "recommended_action": "remove_parent_ownership"
}
```

## Testing Strategy

### Discovery tests

- configured `scan_paths` are used;
- explicit `.ai/workflows/scripts` scan works despite `.ai` default exclusion;
- `.ai/workflows/runs` remains excluded;
- missing optional scan roots are skipped;
- nested scan roots are deduplicated;
- path-aware exclusions match relative paths and globs.

### Skill inventory tests

- every `skills/*/SKILL.md` becomes one candidate module;
- two skills sharing a prefix remain separate modules;
- skill support directories are captured in structured inventory;
- adding `scripts/` changes the structural fingerprint;
- distributed skill copies are ignored.

### Reconciliation tests

- deleted skill is removed from active module map;
- deleted skill is removed from parent indexes;
- historical artifacts are not deleted;
- unambiguous rename migrates the registry without duplicate active modules;
- ambiguous rename becomes delete plus add;
- structural changes refresh the existing module rather than creating a duplicate.

### Validation tests

- missing skill module fails validation;
- stale active module fails validation;
- duplicate ownership fails validation;
- unowned workflow runtime fails validation;
- unowned repository scripts fail validation;
- derived path ownership fails validation;
- a complete reconciled fixture passes.

### Migration regression tests

- current `sdlc-orchestrator` residue is removed;
- each current canonical skill receives a distinct memory mapping;
- aggregate `skills/sdlc` and `skills/transform` ownership is eliminated;
- workflow runtime module contains the modular package paths;
- script modules include `scripts/sync_derived_artifacts.py` and related responsibilities;
- memory load returns active modules and excludes retired modules by default.

## Risks / Trade-offs

- **Large one-time memory churn** — Splitting aggregate memories will create many files. Mitigate with deterministic generation, stable ordering, and one migration fixture representing the current repository.
- **Loss of durable knowledge during splitting** — Preserve aggregate content until target modules are generated and validated. Add migration assertions for known decisions, pitfalls, and update notes.
- **False rename detection** — Only auto-migrate deterministic one-to-one moves; otherwise represent deletion and addition explicitly.
- **Over-scanning `.ai`** — Keep broad exclusion and permit only explicit scan roots.
- **Memory file proliferation** — Accept one file per canonical skill because the repository intentionally treats each skill as an independently governed package.
- **Duplicated script descriptions** — Canonical package ownership determines the primary module; related modules link rather than duplicate behavior descriptions.
- **Stale hand-written index prose** — Rebuild child listings deterministically while preserving a bounded manually maintained overview section.
- **Refresh cost** — Structural inventory is deterministic filesystem work and should remain cheap; semantic refresh remains limited to changed modules.

## Migration Plan

1. Add failing discovery tests for operational `scan_paths`, path-aware exclusions, and explicit workflow roots.
2. Add a canonical inventory model for skills, scripts, agents, workflow runtime, definitions, and tests.
3. Add structural fingerprints and desired-versus-current module diffing.
4. Add deletion and retirement reconciliation with active-index cleanup.
5. Add one-skill-one-module registry generation and package structure metadata.
6. Add scripts and workflow runtime module generation.
7. Add ownership and completeness validation.
8. Migrate current aggregate skill memories into per-skill modules.
9. Remove active `sdlc-orchestrator` residue while preserving historical artifacts.
10. Update `AGENTS.md` and template-sync memory decisions for modular workflow ownership.
11. Rebuild indexes and run the full memory, workflow, wrapper, and repository test suites.

## Open Questions

None. The agreed boundaries are:

- one canonical skill package per memory module;
- skill-local support directories are documented inside that module;
- repository-level scripts are first-class modules;
- workflow runtime is a first-class module;
- deleted modules are reconciled out of the active graph;
- historical artifacts are retained;
- `.ai` is scanned only through explicit canonical roots.
