---
name: sdlc-roadmap
description: SDLC roadmap orchestration layer bridging long-term product roadmap with OpenSpec changes. Use ONLY when the user wants to capture long-term roadmap items (MVP/V2/V3/Later), promote a roadmap item to an OpenSpec change, check roadmap status, or mark roadmap items done. Do NOT use for single OpenSpec change management (use openspec-propose/apply/verify), code execution (use Superpowers), or memory sync (use sdlc-repository-memory-sync).
license: MIT
---

# SDLC Roadmap

Thin orchestration layer between long-term product roadmap and single formal OpenSpec changes. Manages `.ai/roadmap/` file system and provides capability entry points.

## When to Use

- User wants to capture a long-term roadmap from conversation (MVP/V2/V3/Later planning).
- User wants to initialize `.ai/roadmap/` directory structure.
- User wants to see current roadmap status.
- User wants to promote a roadmap item into an OpenSpec change.
- User wants to mark a roadmap item as done and get follow-up prompts.
- User mentions "roadmap", "路线图", "promote RM-xxx", "roadmap capture", "roadmap init".

## When Not to Use

- Single OpenSpec change management (use `openspec-propose`, `openspec-new-change`, `openspec-apply-change`).
- Code implementation or testing (use Superpowers: TDD, debugging, review).
- Repository memory sync (use `sdlc-repository-memory-sync`).
- One-off bugfix or prompt tweak recording (no dedicated system in V1; plan for V2 patch log).

## File Model

`.ai/roadmap/` lives at the project root, sibling to `openspec/`, `.ai/memory/`, `skills/`.

Uses an **area-based layout**: each functional area (skill, workflow, domain, etc.) owns its own roadmap items.

```
.ai/roadmap/
  manifest.json       # Root manifest: declares areas, global view settings
  roadmap.md          # Global human-readable overview (derived, not source of truth)
  index.json          # Global derived index aggregating all area items
  decisions.md        # Cross-area decision records
  areas/
    <area-id>/        # One directory per functional area
      manifest.json   # Area manifest: id, kind, title, id_prefix, owner_path
      roadmap.md      # Area-specific roadmap overview
      decisions.md    # Area-specific decision records
      items/          # Area-specific item files: RM-PREFIX-XXX-slug.md
      revisions/      # Roadmap adjustment records (V2+)
      patches/        # Lightweight patch records (V2+)
```

The canonical runtime path is `.ai/roadmap/`. For existing projects, scripts will read legacy `.roadmap/` when `.ai/roadmap/` is absent. New initialization writes only to `.ai/roadmap/` — do not create new `.roadmap/` directories.

Legacy flat layout (`.ai/roadmap/items/` directly under roadmap root) is read by scripts as a fallback with a migration warning, but new init creates area layout.

**Markdown item files are the source of truth.** `index.json` is a derived index. When they disagree, item files win. Use `rebuild_index.py` to repair with explicit user confirmation after reporting the diff.

### Root Manifest (`.ai/roadmap/manifest.json`)

```json
{
  "version": 1,
  "default_area": "<area-id>",
  "areas": [
    {
      "id": "<area-id>",
      "kind": "skill|workflow|agent|project|domain",
      "title": "<human-readable name>",
      "path": "areas/<area-id>",
      "owner_path": "<source-path>",
      "id_prefix": "<RM-PREFIX>"
    }
  ],
  "global_view": {
    "include_statuses": ["active", "ready", "planned"],
    "sort": ["priority", "order"]
  }
}
```

### Area Manifest (`areas/<area-id>/manifest.json`)

```json
{
  "version": 1,
  "id": "<area-id>",
  "kind": "skill|workflow|agent|project|domain",
  "title": "<human-readable name>",
  "owner_path": "<source-path>",
  "id_prefix": "<RM-PREFIX>"
}
```

### Roadmap Item Frontmatter Fields

```yaml
id: RM-PREFIX-001     # Unique identifier with area prefix
title: "..."          # Human-readable title
status: idea | planned | ready | active | done | deferred | cancelled | superseded
stage: mvp | v2 | v3 | v4 | later
priority: p0 | p1 | p2 | p3
order: 10             # Numeric ordering key for sequencing (scoped within area)
depends_on: []        # List of prerequisite item IDs (may reference other areas)
openspec_change: null | "change-id"
created_at: YYYY-MM-DD
started_at: null | YYYY-MM-DD
completed_at: null | YYYY-MM-DD
patches: []           # List of patch IDs (V2+)
```

Item IDs are scoped within their area using the area's `id_prefix`. Cross-area dependencies use the full prefixed ID (e.g., `RM-SDLC-001`).

### Roadmap Item Body Sections

- `# Goal` — What this phase aims to achieve.
- `# Scope` — `## In` and `## Out` lists.
- `# Acceptance Criteria` — Verifiable completion conditions.
- `# Promotion Notes` — Context for when this item gets promoted to OpenSpec.
- `# Completion Notes` — What was learned, follow-up items (filled on done).
- `# Design Reference` — Optional pointer to design docs.

## Capabilities

### roadmap init

Initialize the `.ai/roadmap/` directory structure at project root.

**When:** First time using roadmap in a project, or user explicitly asks.

**Produces:**
```
.ai/roadmap/
  manifest.json (from template)
  roadmap.md (from template)
  index.json (empty version 1)
  decisions.md (from template)
  areas/
```

**Rules:**
- Do NOT overwrite existing `.ai/roadmap/` if already present. Report what exists and skip.
- If partial state exists (e.g., `roadmap.md` missing but `items/` present), report the incomplete state and ask whether to repair by generating missing files from available data.

### roadmap capture

Extract MVP/V2/V3/Later planning from conversation context and generate roadmap items.

**Trigger:** User describes a phased plan (e.g., "MVP does X, V2 adds Y, V3 adds Z") and says "capture into roadmap" or equivalent.

**Workflow:**
1. Read current conversation context for phased planning.
2. Identify which area the items belong to. If unclear, ask the user or use `default_area` from root manifest.
3. Identify each phase (MVP, V2, V3, Later) with goal, scope, and acceptance criteria.
4. For each phase, create `.ai/roadmap/areas/<area-id>/items/RM-PREFIX-XX-slug.md` with frontmatter populated:
   - `status`: `ready` for MVP, `planned` for later phases.
   - `stage`: match the phase label.
   - `order`: assign increments of 10 (10, 20, 30...) to allow insertion.
   - `id`: use the area's `id_prefix` (e.g., `RM-SDLC-001`).
   - Create frontmatter with all required fields.
5. Update the area `roadmap.md` overview table.
6. Run `rebuild_index.py` to regenerate global `index.json`.
7. Output summary: "Created: RM-PREFIX-001 <title>, RM-PREFIX-002 <title>, ..."

**Rules:**
- Assign IDs sequentially within the area: RM-PREFIX-001, RM-PREFIX-002, ...
- If `.ai/roadmap/` not initialized, run init first.
- Only items that change product capability boundaries should enter roadmap. One-off bugfixes and prompt tweaks do not.
- If no area exists for the topic, prompt the user to create one (create `.ai/roadmap/areas/<area-id>/manifest.json` first).

### roadmap list

Show the current roadmap as a structured summary.

**Trigger:** User asks "what's the roadmap status", "roadmap list", or equivalent.

**Workflow:**
1. Read items from `.ai/roadmap/areas/<area-id>/items/*.md` frontmatter (area view) or all areas (global view).
2. Output a table: ID, Area, Status, Title, Stage, Order.
3. Sort by `order` ascending.
4. Highlight or mark the `active` item if any.
5. If no items, say "No roadmap items found. Use roadmap capture to create items."
6. `roadmap list` defaults to global view (all areas); `roadmap list <area-id>` shows a single area.

### roadmap promote RM-XXX

Promote a roadmap item to an OpenSpec change — the orchestration entry point.

**Workflow:**
1. Read the item file for RM-XXX.
2. Check `depends_on`: if any prerequisite items are not `done`, output a warning: "Dependency RM-YYY is not yet done" but allow promotion.
3. Generate a **promotion context** from the item:
   - Summary of Goal and Scope (In/Out).
   - Key Acceptance Criteria.
   - Promotion Notes.
4. Present the promotion context to the user and **guide them to create an OpenSpec change**:
   - Suggest using `openspec-propose` or `openspec-new-change` with the promotion context as input.
   - Do NOT create `proposal.md`, `design.md`, `tasks.md`, or `spec.md` directly.
5. After the user confirms the OpenSpec change is created, update the item:
   - `status: active`
   - `openspec_change: <change-id>`
   - `started_at: <today>`
6. Update `roadmap.md` and run `rebuild_index.py`.

**Rules:**
- Do NOT generate OpenSpec artifact files. Roadmap promotes; OpenSpec specifies.
- Always output the promotion context to help the user transition smoothly.
- Run `validate.py` after updating to confirm consistency.

### roadmap done RM-XXX

Mark a roadmap item as done and prompt for follow-up actions.

**Workflow:**
1. Read the item file.
2. Check if associated `openspec_change` is archived or verified in `openspec/changes/` or `openspec/changes/archive/`.
3. Update item:
   - `status: done`
   - `completed_at: <today>`
4. Fill `# Completion Notes` with what was accomplished, what was deferred, and what follow-up items surfaced.
5. Update `roadmap.md` and run `rebuild_index.py`.
6. Prompt the user:
   - "Consider running `sdlc-repository-memory-sync` to preserve long-term facts."
   - "Any small improvements to record? (patch log available in V2)."
   - "Should the roadmap be re-planned? (replan available in V2)."

**Rules:**
- Only mark done if the associated OpenSpec change is complete (verified or archived). Otherwise warn and ask for confirmation.
- Do NOT auto-trigger memory sync — only prompt the user.

## State Machine

```
idea ──→ planned ──→ ready ──→ active ──→ done
  │        │           │          │
  └────────┴───────────┴──────────┴──→ deferred
  │        │           │
  └────────┴───────────┴──────────────→ cancelled
  │        │           │
  └────────┴───────────┴──────────────→ superseded
```

| Status     | Meaning |
|------------|---------|
| idea       | Rough idea, not yet in formal roadmap |
| planned    | Planned but not ready to execute |
| ready      | Ready to promote to OpenSpec change |
| active     | OpenSpec change created, being implemented |
| done       | Completed and verified |
| deferred   | Postponed, not deleted |
| cancelled  | Explicitly cancelled |
| superseded | Replaced by another item |

**Core flow:** `idea → planned → ready → active → done`

**Adjustment flows (V2+):**
- `planned → deferred`
- `ready → deferred`
- `planned → cancelled`
- `ready → cancelled`
- `planned → superseded`
- `ready → superseded`

## Boundary Rules

### Roadmap vs OpenSpec

| Roadmap | OpenSpec |
|---------|----------|
| What to build and when | How to build this change |
| Long-term sequencing | Single change lifecycle |
| Stage goals and priorities | Formal spec/design/tasks |
| Promotion entry point | Proposal → verify → archive |

**Rule:** Roadmap does not duplicate OpenSpec. Promote generates context and guides the user to OpenSpec; it never creates proposal/design/tasks/spec files directly.

### Roadmap vs Memory Sync

| Roadmap | Memory Sync |
|---------|-------------|
| What items exist and their status | What was learned and decided |
| Sequence and prioritization | Architecture, pitfalls, decisions |
| `.ai/roadmap/` directory | `.ai/memory/` directory |
| Transient planning state | Durable facts |

**Rule:** Roadmap is not a long-term knowledge store. Only completed capabilities, architecture decisions, pitfalls, and stable conventions go into `.ai/memory/`.

### Roadmap vs Superpowers

| Roadmap | Superpowers |
|---------|-------------|
| When and why to build | How to build correctly |
| Orchestration | Execution |

**Rule:** Roadmap does not execute code, run tests, or debug. Execution always delegates to Superpowers skills.

### What Goes Where

| Content | Destination |
|---------|-------------|
| Product phase goal (MVP contract review) | Roadmap item |
| Formal change spec for that phase | OpenSpec change |
| Implementation of the change | Superpowers execution |
| Architecture decision made during build | Memory sync (`.ai/memory/`) |
| Bug noticed after completion | Patch log (V2) |
| Roadmap reordered after learning | Revision (V2) |

## Guardrails

- Do NOT create OpenSpec proposal/design/tasks/spec files in promote. Only generate promotion context and guide user.
- Do NOT auto-trigger memory sync. Only prompt and let the user decide.
- Do NOT silently overwrite existing `.ai/roadmap/` files.
- Do NOT delete or remove items during capture. Use status transitions (deferred, cancelled, superseded) instead.
- Item files are the source of truth. When `index.json` disagrees, report the diff and offer to rebuild.
- Run `validate.py` after any item modification to catch inconsistency early.
- Assign order values in increments of 10 to allow insertion without full renumbering.
- Do NOT enter one-off bugfixes, prompt tweaks, or single-field changes into roadmap. Those belong in a patch log (V2) or are handled ad-hoc.

## Script Reference

- `scripts/validate.py` — Validate item frontmatter, index.json consistency, state legality, dangling depends_on references.
- `scripts/rebuild_index.py` — Rebuild `index.json` from `items/*.md` frontmatter (backups existing index as `.bak`).
- `scripts/list.py` — Output roadmap summary table sorted by `order`.

## Templates Reference

- `templates/roadmap.md` — `.ai/roadmap/roadmap.md` template with overview table and active/next sections.
- `templates/item.md` — Roadmap item template with frontmatter and body sections.
- `templates/decisions.md` — `.ai/roadmap/decisions.md` template for cross-item decision records.
