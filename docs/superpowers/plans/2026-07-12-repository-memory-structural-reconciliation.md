# Repository Memory Structural Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make repository memory structurally reconcile against the current canonical repository so deleted modules are retired, every canonical skill receives one dedicated memory module, skill support directories are documented, repository scripts and the modular workflow runtime receive memory ownership, and stale entries such as the deleted `sdlc-orchestrator` cannot survive future refreshes.

**Architecture:** Extend the deterministic repository-memory pipeline from directory candidate discovery into a desired-state inventory and reconciliation flow. `discover_modules.py` will honor configured scan roots and path-aware exclusions. New inventory/diff helpers will classify active canonical modules, and reconciliation will update the registry, parent indexes, lifecycle state, and validation findings. Canonical skills map one-to-one to `modules/skills/<skill>.md`; repository scripts and workflow runtime receive independent modules. LLM-assisted semantic summaries may remain selective, but filesystem ownership, lifecycle, and package structure are deterministic.

**Tech Stack:** Python 3, pathlib, JSON/YAML-compatible Markdown frontmatter, pytest/unittest repository tests, existing `sdlc-repository-memory-*` skills, `.ai/memory/` registry and module files, and the derived-artifact synchronization pipeline.

---

## File Structure

### Canonical implementation files

| File | Responsibility | Planned change |
|---|---|---|
| `skills/sdlc-repository-memory-sync/scripts/discover_modules.py` | Filesystem module discovery | Honor `scan_paths`; add path-aware exclusions; preserve explicit `.ai/workflows` scan roots; emit richer package structure |
| `skills/sdlc-repository-memory-sync/scripts/detect_state.py` | Determine memory sync state and changed scope | Include structural inventory and deleted/renamed/structure-changed modules in refresh scope |
| `skills/sdlc-repository-memory-sync/scripts/reconcile_modules.py` | New deterministic desired-state reconciliation | Compare expected inventory with active registry; classify adds/deletes/renames; produce repair actions |
| `skills/sdlc-repository-memory-sync/scripts/module_inventory.py` | New canonical inventory model | Discover canonical skills, repository scripts, workflow runtime, agents, definitions, and tests |
| `skills/sdlc-repository-memory-sync/scripts/validate_memory.py` | Memory consistency validation | Add one-skill-one-module, stale-active, duplicate ownership, workflow/scripts ownership, support-directory coverage checks |
| `skills/sdlc-repository-memory-sync/scripts/rebuild_index.py` | Rebuild memory indexes | Rebuild active child indexes from reconciled registry and exclude retired modules by default |
| `skills/sdlc-repository-memory-sync/SKILL.md` | Memory sync operating contract | Document structural reconciliation, deletion handling, per-skill modules, scripts/workflow ownership |
| `skills/sdlc-repository-memory-init/scripts/init_memory.py` | Initial memory layout and preferences | Seed operational `scan_paths`, parent indexes, and updated registry schema/defaults |
| `skills/sdlc-repository-memory-init/SKILL.md` | Memory initialization contract | Document initial desired-state inventory and one-skill-one-module behavior |
| `skills/sdlc-repository-memory-load/scripts/load_memory.py` | Active memory loading | Exclude retired modules by default; optionally support explicit historical loading if existing CLI design allows |
| `skills/sdlc-repository-memory-load/SKILL.md` | Memory loading contract | Document active-versus-retired semantics |
| `.ai/memory/discovery-prefs.json` | Current repository discovery configuration and registry | Migrate to explicit scan roots and one-to-one canonical module mappings |
| `.ai/memory/modules/skills.md` | Parent skill index | Rebuild as non-owning active-skill index |
| `.ai/memory/modules/scripts.md` | New parent scripts module | Describe repository script responsibilities and link child modules |
| `.ai/memory/modules/workflow.md` | New parent workflow module | Describe workflow-related memory children |
| `.ai/memory/modules/workflow/runtime.md` | New workflow runtime module | Own live runtime facade, modular package, and definition |
| `.ai/memory/modules/skills/<skill>.md` | Per-skill memory modules | One active module for every canonical skill package |
| `.ai/memory/decisions/template-sync-and-distribution.md` | Workflow/template source-of-truth decision | Update modular runtime inventory and live-to-template-to-distribution semantics |
| `AGENTS.md` | Repository workflow synchronization guidance | Cover `workflow_runtime/**/*.py`, clarify live authoritative inputs, prefer aggregate sync entrypoint |

### Tests

| File | Responsibility | Planned change |
|---|---|---|
| `tests/test_sdlc_repository_memory_sync.py` or existing equivalent | End-to-end memory sync tests | Add scan-root, deletion, per-skill, scripts, workflow, migration, and validation scenarios |
| `tests/test_sdlc_repository_memory_init.py` or existing equivalent | Memory init tests | Assert new defaults and generated parent layout |
| `tests/test_sdlc_repository_memory_load.py` or existing equivalent | Memory load tests | Assert retired modules are excluded by default |
| `tests/fixtures/memory_reconciliation/` | Deterministic repository fixtures | Add canonical skills, deleted skill registry, scripts, workflow runtime, derived copies, and rename cases |
| `tests/test_wrapper_contracts.py` | Canonical/distributed skill wrapper consistency | Update only if skill documentation or installed wrappers require regenerated copies |

### Derived artifacts

After canonical skill changes, run:

```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
```

This may update repository-local `.opencode/`, `.claude/`, and `.cursor/` skill copies. These copies are derived and must not be edited first.

---

## Task 1: Capture the Current Failure as Tests

**Files:**
- Modify: existing repository memory sync test file(s)
- Create: `tests/fixtures/memory_reconciliation/` as needed

- [ ] **Step 1: Add a fixture containing a deleted accepted skill**

Create a temporary repository fixture with:

```text
skills/active-skill/SKILL.md
.ai/memory/discovery-prefs.json
.ai/memory/modules/skills.md
.ai/memory/modules/skills/deleted-skill.md
```

The registry must contain both `skills/active-skill` and nonexistent `skills/deleted-skill` as accepted active entries.

- [ ] **Step 2: Add a failing test for stale active module detection**

Assert that reconciliation reports:

```json
{
  "type": "stale_active_module",
  "module_id": "skills/deleted-skill",
  "path": "skills/deleted-skill"
}
```

- [ ] **Step 3: Add a failing test for active parent-index cleanup**

Assert that after repair the deleted skill is absent from the active skill index and registry.

- [ ] **Step 4: Add a failing test proving historical files are preserved**

Add an archived spec or decision mentioning the deleted skill and assert reconciliation does not delete or rewrite it.

- [ ] **Step 5: Run the focused tests and confirm RED**

Run the exact existing test entrypoint for repository memory sync, for example:

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py -k "stale_active or deleted_module" -v
```

Expected: failures because no deterministic stale-module reconciliation exists yet.

## Task 2: Make `scan_paths` Operational

**Files:**
- Modify: `skills/sdlc-repository-memory-sync/scripts/discover_modules.py`
- Modify: focused discovery tests

- [ ] **Step 1: Add tests for configured scan roots**

Cover:

- scanning only configured roots;
- missing optional roots are skipped;
- nested roots are deduplicated;
- repository-relative candidate paths remain stable;
- null `scan_paths` preserves legacy root scanning.

- [ ] **Step 2: Add a test for explicit `.ai/workflows/scripts` scanning**

The fixture should retain `.ai` in global exclusions but configure:

```json
{
  "scan_paths": [".ai/workflows/scripts"]
}
```

Assert `workflow.py` or `workflow_runtime/` is discovered.

- [ ] **Step 3: Refactor discovery entry roots**

Replace unconditional:

```python
walk(root, 1)
```

with normalized scan-root resolution:

```python
scan_roots = resolve_scan_roots(root, prefs.get("scan_paths"))
for scan_root in scan_roots:
    walk(scan_root, initial_depth_for(scan_root))
```

Requirements:

- resolve all roots under the repository;
- reject `..` escapes;
- skip missing roots;
- sort roots deterministically;
- deduplicate roots covered by another configured root only when doing so does not change explicit exclusion semantics.

- [ ] **Step 4: Preserve explicit-root override semantics**

A broad `.ai` basename exclusion must not prevent walking an explicitly configured `.ai/workflows/scripts` root. Exclusions inside that root still apply.

- [ ] **Step 5: Run focused discovery tests and confirm GREEN**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py -k "scan_paths or explicit_ai_root" -v
```

## Task 3: Add Path-Aware Exclusion Matching

**Files:**
- Modify: `skills/sdlc-repository-memory-sync/scripts/discover_modules.py`
- Modify: discovery tests

- [ ] **Step 1: Add failing tests for relative-path and glob exclusions**

Cover:

```text
.ai/workflows/runs
.ai/memory
.ai/roadmap
**/__pycache__
```

Assert `.ai/workflows/scripts` remains discoverable while runtime state remains excluded.

- [ ] **Step 2: Implement a normalized exclusion matcher**

Add a helper with semantics equivalent to:

```python
def is_excluded(root: Path, path: Path, patterns: set[str]) -> bool:
    relative = path.relative_to(root).as_posix()
    return basename_matches(path.name, patterns) or relative_or_glob_matches(relative, patterns)
```

Maintain backward compatibility for simple-name exclusions such as `node_modules`.

- [ ] **Step 3: Use the matcher consistently**

Apply it in:

- recursive walking;
- accepted-parent child discovery;
- scan-root normalization where applicable.

- [ ] **Step 4: Run focused tests**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py -k "path_exclusion" -v
```

## Task 4: Introduce a Canonical Module Inventory

**Files:**
- Create: `skills/sdlc-repository-memory-sync/scripts/module_inventory.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/discover_modules.py`
- Modify: tests

- [ ] **Step 1: Define the inventory data contract**

Represent each canonical module with stable structured fields:

```python
{
    "module_id": "skills/sdlc-project-bootstrap",
    "kind": "skill",
    "path": "skills/sdlc-project-bootstrap",
    "parent_id": "skills",
    "entry_paths": ["skills/sdlc-project-bootstrap/SKILL.md"],
    "support_paths": {
        "scripts": [...],
        "templates": [...],
        "schemas": [...],
        "references": [...],
        "tests": [...],
    },
    "fingerprint": "...",
}
```

- [ ] **Step 2: Inventory canonical skills one-to-one**

Discover each direct `skills/*/SKILL.md` package independently, even when names share a prefix.

Add a test proving:

```text
skills/sdlc-project-bootstrap
skills/sdlc-repository-memory-sync
```

produce two module ids rather than one `skills/sdlc` aggregate.

- [ ] **Step 3: Capture skill support directories**

For each skill, inventory existing:

- `scripts/`
- `templates/`
- `schemas/`
- `references/`
- `tests/`

Use sorted repository-relative file paths.

- [ ] **Step 4: Inventory repository scripts**

Add a parent `scripts` module and deterministic child candidates for cohesive script groups. At minimum, ensure `scripts/sync_derived_artifacts.py` has an owner.

Do not force one child module per script. Expose enough inventory metadata for configured or deterministic grouping.

- [ ] **Step 5: Inventory workflow runtime**

Create the canonical module record:

```text
module_id: workflow/runtime
owned paths:
  .ai/workflows/scripts/workflow.py
  .ai/workflows/scripts/workflow_runtime/
  .ai/workflows/definitions/sdlc-main.yaml
```

Treat bootstrap template copies as related derived paths, not owned behavior sources.

- [ ] **Step 6: Add structural fingerprints**

Fingerprint must change when a support directory or governed file is added or removed.

- [ ] **Step 7: Run inventory tests**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py -k "canonical_inventory or support_paths or workflow_runtime" -v
```

## Task 5: Add Desired-State Reconciliation

**Files:**
- Create: `skills/sdlc-repository-memory-sync/scripts/reconcile_modules.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/detect_state.py`
- Modify: tests

- [ ] **Step 1: Define reconciliation classifications**

Return deterministic collections for:

```text
added
modified
structure_changed
renamed
deleted
unchanged
```

- [ ] **Step 2: Compare inventory with active registry**

Use canonical path and module id as primary identity. A missing accepted path becomes `deleted`. A new canonical inventory entry becomes `added`.

- [ ] **Step 3: Add safe rename handling**

Auto-classify `renamed` only when there is deterministic one-to-one evidence, such as explicit migration metadata or an exact unique fingerprint move.

Ambiguous cases must remain `deleted` plus `added`.

- [ ] **Step 4: Classify support-directory changes**

When a skill keeps the same canonical path but adds/removes support content, classify `structure_changed`.

- [ ] **Step 5: Feed reconciliation into sync scope**

`detect_state.py` must include deleted and structure-changed modules even when changed-file detection alone would skip them.

- [ ] **Step 6: Add machine-readable findings**

Each repair item must include:

- finding type;
- module id;
- canonical path;
- recommended action;
- optional replacement module id.

- [ ] **Step 7: Run focused reconciliation tests**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py -k "reconcile or rename or structure_changed" -v
```

## Task 6: Enforce One Skill per Memory Module

**Files:**
- Modify: memory sync generation/update code used by the skill
- Modify: `skills/sdlc-repository-memory-sync/SKILL.md`
- Modify: tests

- [ ] **Step 1: Add a failing registry-generation test**

Given two canonical skills with the same prefix, expect:

```json
"skills/sdlc-project-bootstrap": {
  "memory_id": "skills/sdlc-project-bootstrap",
  "memory_path": "modules/skills/sdlc-project-bootstrap.md"
}
```

and a separate mapping for `skills/sdlc-repository-memory-sync`.

- [ ] **Step 2: Generate one-to-one module mappings**

Remove prefix grouping from new registry generation. Parent category `skills` remains, but child skills own their own paths.

- [ ] **Step 3: Standardize skill module frontmatter**

Support:

- `lifecycle_status`;
- `owned_paths`;
- `entry_paths`;
- `script_paths`;
- `template_paths`;
- `schema_paths`;
- `reference_paths`;
- `test_paths`;
- `derived_targets`.

- [ ] **Step 4: Standardize skill module body sections**

Ensure the module explains present package sections:

```markdown
## Purpose
## Entry Contract
## Package Structure
## Dependencies
## Operational Flow
## Invariants
## Known Pitfalls
## Update Notes
```

Omit empty subsection details rather than inventing content.

- [ ] **Step 5: Add package-structure coverage tests**

A skill with `scripts/` and `templates/` must mention both in metadata and body. A skill without them must not claim they exist.

- [ ] **Step 6: Update the memory sync skill contract**

Document that the skill package is the default module boundary and skill-local scripts remain inside the parent module unless independently governed.

- [ ] **Step 7: Run focused tests**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py -k "one_skill_one_module or package_structure" -v
```

## Task 7: Add Repository Scripts and Workflow Runtime Memory Modules

**Files:**
- Modify: module generation code
- Create during migration: `.ai/memory/modules/scripts.md`
- Create during migration: `.ai/memory/modules/workflow.md`
- Create during migration: `.ai/memory/modules/workflow/runtime.md`
- Modify: tests

- [ ] **Step 1: Add a failing test for unowned repository scripts**

A fixture containing `scripts/sync_derived_artifacts.py` but no scripts memory owner must fail validation.

- [ ] **Step 2: Add a failing test for unowned workflow runtime**

A fixture containing `workflow.py`, `workflow_runtime/`, and `sdlc-main.yaml` but no `workflow/runtime` module must fail validation.

- [ ] **Step 3: Generate the scripts parent module**

Describe repository-level scripts, entry commands, side effects, callers, tests, and child modules.

- [ ] **Step 4: Generate or maintain cohesive scripts child modules**

At minimum, create a derived-artifact synchronization child module when current repository structure justifies it. Keep trivial utilities in the parent rather than creating one file per module.

- [ ] **Step 5: Generate the workflow runtime module**

Include:

- stable `workflow.py` facade;
- responsibilities of `core`, `state`, `definitions`, `domains`, `policies`, `dispatch`, `lifecycle`, `governance`, and `cli`;
- state write ownership;
- workflow definition ownership;
- test paths;
- live-to-template synchronization.

- [ ] **Step 6: Mark template copies as derived relationships**

Do not add independent module mappings for `skills/sdlc-project-bootstrap/templates/workflow/` or installed client copies.

- [ ] **Step 7: Run focused tests**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py -k "scripts_owner or workflow_runtime_owner" -v
```

## Task 8: Add Retirement and Active-Graph Cleanup

**Files:**
- Modify: `skills/sdlc-repository-memory-sync/scripts/reconcile_modules.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/rebuild_index.py`
- Modify: `skills/sdlc-repository-memory-load/scripts/load_memory.py`
- Modify: related SKILL.md files
- Modify: tests

- [ ] **Step 1: Implement deleted-module retirement actions**

For a deleted canonical module:

- remove or retire the active registry mapping;
- remove it from active parent indexes;
- remove stale owned paths and path hints;
- preserve historical artifacts;
- optionally retain a retired module file with lifecycle metadata.

- [ ] **Step 2: Exclude retired modules from normal active loading**

`load_memory.py` must not return retired modules in default active context.

- [ ] **Step 3: Preserve explicit historical access**

If the loader already has a compatible filtering mechanism, add or document a history-inclusive mode. Do not expand the CLI unnecessarily solely for this task.

- [ ] **Step 4: Rebuild parent child lists from active registry**

Do not trust stale prose or prior child lists as the source of truth.

- [ ] **Step 5: Add deletion regression tests**

Cover:

- deleted module removed from active graph;
- retired module excluded by default load;
- historical decision remains;
- re-adding a formerly deleted path creates or reactivates exactly one module.

- [ ] **Step 6: Run focused tests**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py tests/test_sdlc_repository_memory_load.py -k "retired or deleted_module" -v
```

## Task 9: Strengthen Memory Validation

**Files:**
- Modify: `skills/sdlc-repository-memory-sync/scripts/validate_memory.py`
- Modify: tests

- [ ] **Step 1: Add one-skill-one-module validation**

For every canonical `skills/*/SKILL.md`, assert exactly one active module mapping.

- [ ] **Step 2: Add stale-active validation**

Every active module must own at least one existing canonical path.

- [ ] **Step 3: Add duplicate ownership validation**

No canonical path may appear in two active modules. Parent indexes may link children but may not own their paths.

- [ ] **Step 4: Add support-directory coverage validation**

When a skill contains a governed support directory, its module metadata and package structure must represent it.

- [ ] **Step 5: Add scripts and workflow ownership validation**

Require active ownership for repository scripts and workflow runtime.

- [ ] **Step 6: Add derived-path ownership validation**

Reject `.opencode/skills`, `.claude/skills`, `.cursor/skills`, and workflow bootstrap template copies as primary canonical module paths.

- [ ] **Step 7: Emit structured findings**

Output type, module id, path, and recommended repair action in JSON mode.

- [ ] **Step 8: Run focused validation tests**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_sync.py -k "validation or duplicate_owned or missing_skill_memory" -v
```

## Task 10: Update Memory Initialization Defaults

**Files:**
- Modify: `skills/sdlc-repository-memory-init/scripts/init_memory.py`
- Modify: `skills/sdlc-repository-memory-init/SKILL.md`
- Modify: init tests

- [ ] **Step 1: Seed explicit scan roots**

Initialize repository-appropriate defaults equivalent to:

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

Only include roots supported by the generic init contract; missing roots must be safe.

- [ ] **Step 2: Seed parent module layout**

Initialize parent indexes for skills, scripts, workflow, agents, and tests as appropriate.

- [ ] **Step 3: Stop seeding prefix-based aggregate skill mappings**

All discovered skills must receive independent mappings.

- [ ] **Step 4: Update initialization documentation**

Document that structural reconciliation completes or repairs the initial active graph.

- [ ] **Step 5: Run init tests**

```bash
python3 -m pytest tests/test_sdlc_repository_memory_init.py -v
```

## Task 11: Migrate the Current Repository Memory

**Files:**
- Modify: `.ai/memory/discovery-prefs.json`
- Modify: `.ai/memory/modules/skills.md`
- Create/modify: `.ai/memory/modules/skills/*.md`
- Create: `.ai/memory/modules/scripts.md`
- Create as justified: `.ai/memory/modules/scripts/*.md`
- Create: `.ai/memory/modules/workflow.md`
- Create: `.ai/memory/modules/workflow/runtime.md`
- Remove or convert: aggregate ownership modules such as `.ai/memory/modules/skills/sdlc.md` and `.ai/memory/modules/skills/transform.md`

- [ ] **Step 1: Inventory all current canonical skills**

Generate the exact list from `skills/*/SKILL.md`. Do not rely on the existing registry.

- [ ] **Step 2: Create one module per canonical skill**

For each skill, include package structure and migrate relevant durable content from aggregate memories.

- [ ] **Step 3: Remove active `sdlc-orchestrator` residue**

Remove:

- active registry mapping;
- current owned/path hints;
- present-tense operational guidance;
- active parent child entry.

Preserve archived specs, plans, OpenSpec artifacts, roadmap history, run history, decisions, and sync history.

- [ ] **Step 4: Split aggregate SDLC memory**

Move skill-specific content from `modules/skills/sdlc.md` into modules such as:

```text
skills/sdlc-project-bootstrap
skills/sdlc-repository-memory-sync
skills/sdlc-repository-memory-init
skills/sdlc-repository-memory-load
skills/sdlc-repository-memory-reset
skills/sdlc-openspec-memory-sync
skills/sdlc-openspec-init
skills/sdlc-roadmap
skills/sdlc-evalops
```

Use the current canonical inventory as authority; do not recreate deleted skills.

- [ ] **Step 5: Split other aggregate skill memories**

Convert `transform-*` and any other grouped canonical skills into one module per skill.

- [ ] **Step 6: Create scripts memory**

Document repository script ownership, including the derived-artifact synchronization entrypoint and its relationship to lower-level template sync.

- [ ] **Step 7: Create workflow runtime memory**

Use the current modular runtime layout and authoritative tests.

- [ ] **Step 8: Rewrite the registry one-to-one**

Every active canonical skill path maps to its own memory id and file.

- [ ] **Step 9: Rebuild indexes**

Generate active child listings for skills, scripts, workflow, agents, and tests.

- [ ] **Step 10: Validate the migrated repository**

Run the repository memory validator in strict mode and require zero structural findings.

## Task 12: Correct Workflow Sync Governance Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `.ai/memory/decisions/template-sync-and-distribution.md`
- Modify: related tests if documentation contracts are asserted

- [ ] **Step 1: Update `AGENTS.md` governed runtime paths**

Replace single-file wording with:

```text
.ai/workflows/scripts/workflow.py
.ai/workflows/scripts/workflow_runtime/**/*.py
.ai/workflows/definitions/sdlc-main.yaml
```

- [ ] **Step 2: Clarify source direction**

State:

```text
live .ai/workflows implementation
    -> canonical bootstrap templates
    -> installed client copies
```

- [ ] **Step 3: Prefer the aggregate sync command**

Document:

```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
```

as the routine entrypoint. Keep `sync_templates.py` as a specialized workflow-only command.

- [ ] **Step 4: Update the template-sync decision**

Replace outdated governed-files and source-of-truth wording with the modular runtime inventory and layered source semantics.

- [ ] **Step 5: Verify no governance prose still claims only `workflow.py` is governed**

Use a repository search and manually assess historical documents separately from active guidance.

## Task 13: Update Skill Documentation and Derived Copies

**Files:**
- Modify: canonical `skills/sdlc-repository-memory-*` SKILL.md files
- Derived: `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`

- [ ] **Step 1: Update canonical skill docs**

Ensure init, sync, and load documentation agree on:

- desired-state reconciliation;
- active versus retired modules;
- one skill per module;
- package support-directory descriptions;
- scripts and workflow ownership;
- deterministic validation.

- [ ] **Step 2: Run canonical skill-specific tests**

Use the existing skill contract test entrypoints.

- [ ] **Step 3: Sync derived artifacts**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git
```

- [ ] **Step 4: Check for drift**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

Expected: no canonical/distributed drift.

## Task 14: Run Focused and Full Verification

**Files:**
- No source changes unless failures expose defects

- [ ] **Step 1: Run repository memory focused suites**

Run all existing tests for:

- repository memory init;
- repository memory discovery/sync;
- repository memory load;
- repository memory reset if registry schema interactions exist;
- wrapper contracts.

- [ ] **Step 2: Run workflow tests**

Because workflow runtime ownership and AGENTS/template governance changed, run:

```bash
python3 -m pytest tests/test_workflow.py tests/test_workflow_modules.py -v
```

- [ ] **Step 3: Run full repository tests**

```bash
python3 -m pytest -v
```

- [ ] **Step 4: Run strict memory validation against the live repository**

Expected invariants:

- every canonical skill has one active module;
- `skills/sdlc-orchestrator` is absent from the active graph;
- repository scripts are owned;
- workflow runtime is owned;
- no duplicate canonical ownership;
- no missing active paths;
- no derived paths registered as canonical modules.

- [ ] **Step 5: Run aggregate derived-artifact check**

```bash
python3 scripts/sync_derived_artifacts.py --check
```

- [ ] **Step 6: Inspect the final diff for accidental generated-state changes**

Confirm no `.ai/workflows/runs/`, unrelated roadmap content, or ephemeral runtime outputs were added.

## Task 15: Record Migration Evidence

**Files:**
- Modify/create: appropriate `.ai/memory/evolution/`, decision, pitfall, or sync-history artifacts according to the repository memory workflow

- [ ] **Step 1: Record the structural reconciliation decision**

Capture:

- desired-state model;
- one-skill-one-module invariant;
- deletion retirement semantics;
- explicit `.ai/workflows` scan roots;
- scripts/workflow ownership;
- canonical-versus-derived distinction.

- [ ] **Step 2: Record the stale-deleted-module pitfall**

Document the previous failure mode where a deleted skill remained active because refresh only processed additions and modifications.

- [ ] **Step 3: Record migration evidence**

Include:

- number of canonical skills inventoried;
- modules created;
- aggregate modules split;
- deleted active entries retired;
- validation result;
- test commands and outcomes.

- [ ] **Step 4: Re-run memory sync once more**

This final run must be idempotent: it should produce no new structural changes after the migration has converged.

---

## Acceptance Criteria

The implementation is complete only when all of the following are true:

- [ ] `scan_paths` changes actual discovery behavior.
- [ ] Explicit `.ai/workflows/scripts` and `.ai/workflows/definitions` roots are scanned without opening the rest of `.ai`.
- [ ] Path-aware exclusions prevent runtime state and memory directories from becoming modules.
- [ ] Every canonical skill has exactly one active memory module.
- [ ] Every skill module describes existing package support directories.
- [ ] Repository-level scripts have active memory ownership.
- [ ] Workflow runtime and definition have active memory ownership.
- [ ] Deleted `skills/sdlc-orchestrator` is absent from active registry, active indexes, and current operational guidance.
- [ ] Historical orchestrator artifacts remain intact.
- [ ] Prefix-based aggregate modules no longer own multiple canonical skill packages.
- [ ] Retired modules are excluded from default memory load.
- [ ] Derived skill and workflow template copies do not receive independent behavior modules.
- [ ] Strict memory validation passes against the live repository.
- [ ] A second memory refresh is idempotent.
- [ ] Focused and full repository tests pass.
- [ ] Derived-artifact drift check passes.

## Rollback

Rollback should revert implementation code, generated/migrated memory modules, registry changes, documentation, and derived skill copies together.

Because the memory format remains file-based, no database migration is required. If the migration must be reverted, restore the prior `.ai/memory/discovery-prefs.json` and module tree from source control, then revert the discovery/reconciliation code in the same change. Do not partially revert only the registry or only the module files, because that would recreate ownership drift.
