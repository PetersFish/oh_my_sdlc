---
name: sdlc-roadmap
description: >-
  SDLC roadmap orchestration layer bridging long-term product roadmap with OpenSpec changes. Use ONLY when the user wants to capture long-term roadmap items (MVP/V2/V3/Later), review a roadmap idea, revise/insert/reorder/cancel/replan items, check roadmap status, or mark roadmap items done. Do NOT use for single OpenSpec change management (use openspec-propose/apply/verify), code execution (use Superpowers), or memory sync (use sdlc-repository-memory-sync).
license: MIT
---

# SDLC Roadmap

Thin orchestration layer between long-term product roadmap and single formal OpenSpec changes. Manages `.ai/roadmap/` file system and provides capability entry points.

## When to Use

- User wants to capture a long-term roadmap from conversation (MVP/V2/V3/Later planning).
- User wants to initialize `.ai/roadmap/` directory structure.
- User wants to see current roadmap status.
- User wants to review a roadmap idea and create OpenSpec artifacts when review passes.
- User wants to revise an existing roadmap item's content with traceable history.
- User wants to insert a new roadmap item at a specific position.
- User wants to reorder roadmap items by priority or position.
- User wants to cancel a roadmap item while preserving history.
- User wants to replan a whole area, replacing unfinished plans.
- User wants to mark a roadmap item as done and get follow-up prompts.
- User mentions "roadmap", "路线图", "review RM-xxx", "roadmap capture", "roadmap init", "roadmap revise", "roadmap insert", "roadmap reorder", "roadmap cancel", "roadmap replan".

## When Not to Use

- Single OpenSpec change management (use `openspec-propose`, `openspec-new-change`, `openspec-apply-change`).
- Code implementation or testing (use Superpowers: TDD, debugging, review).
- Repository memory sync (use `sdlc-repository-memory-sync`).
- Post-archive roadmap state sync trigger (owned by `sdlc-orchestrator`, not roadmap).

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
      revisions/      # Roadmap revision records: changelog.md, snapshots/, batch/
```

The canonical runtime path is `.ai/roadmap/`. Only the area-based layout is supported.

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
    "include_statuses": ["active", "ready", "idea"],
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
status: idea | ready | active | done | cancelled
stage: mvp | v2 | v3 | v4 | later
priority: p0 | p1 | p2 | p3
order: 10             # Numeric ordering key for sequencing (scoped within area)
depends_on: []        # List of prerequisite item IDs (may reference other areas)
openspec_change: null | "change-id"
created_at: YYYY-MM-DD
started_at: null | YYYY-MM-DD
completed_at: null | YYYY-MM-DD
```

Item IDs are scoped within their area using the area's `id_prefix`. Cross-area dependencies use the full prefixed ID (e.g., `RM-SDLC-001`).

### Roadmap Item Body Sections

- `# Goal` — What this phase aims to achieve.
- `# Scope` — `## In` and `## Out` lists.
- `# Acceptance Criteria` — Verifiable completion conditions.
- `# Promotion Notes` — Context for when this item gets promoted to OpenSpec.
- `# Completion Notes` — What was learned, follow-up items (filled on done).
- `# Design Reference` — Optional pointer to design docs.

## State Machine

```
idea ──→ ready ──→ active ──→ done
  │        │          │
  └────────┴──────────┴──→ cancelled
```

| Status    | Meaning |
|-----------|---------|
| idea      | Rough idea, not yet reviewed |
| ready     | Review passed, OpenSpec artifacts complete, ready to apply |
| active    | Implementation in progress (apply started) |
| done      | Completed and verified |
| cancelled | Explicitly cancelled, history preserved |

**Core flow:** `idea → ready → active → done`

**Cancellation:** any non-done status can go to `cancelled`.

### Migration from V1 Statuses

If existing roadmap data uses `planned`, `deferred`, or `superseded`:

| Old Status  | Migration |
|-------------|-----------|
| `planned`   | Map to `idea` (not yet reviewed) or `ready` (if artifacts exist) |
| `deferred`  | Map to `idea` with adjusted order; deferral intent recorded in revision notes |
| `superseded`| Map to `cancelled`; replacement item ID recorded in completion notes |

The `patches` frontmatter field is removed. Existing patch data is not migrated; patch concepts are out of scope for V2.

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
   - `status`: `idea` for all captured items.
   - `stage`: match the phase label.
   - `order`: assign increments of 10 (10, 20, 30...) to allow insertion.
   - `id`: use the area's `id_prefix` (e.g., `RM-SDLC-001`).
   - Create frontmatter with all required fields.
5. Update the area `roadmap.md` overview table.
6. Append a changelog entry to `revisions/changelog.md` for each captured item.
7. Run `rebuild_index.py` to regenerate global `index.json`.
8. Output summary: "Created: RM-PREFIX-001 <title>, RM-PREFIX-002 <title>, ..."

**Rules:**
- Assign IDs sequentially within the area: RM-PREFIX-001, RM-PREFIX-002, ...
- If `.ai/roadmap/` not initialized, run init first.
- Only items that change product capability boundaries should enter roadmap. One-off bugfixes and prompt tweaks do not.
- If no area exists for the topic, prompt the user to create one (create `.ai/roadmap/areas/<area-id>/manifest.json` first).

### roadmap list

Show the current roadmap as a structured summary.

**Trigger:** User asks "what's the roadmap status", "roadmap list", "列出未完成的roadmap", "roadmap有哪些", "列举roadmap", or equivalent.

**Hard Rule:** The ONLY way to answer roadmap status questions is to run `skills/sdlc-roadmap/scripts/list.py` with appropriate flags. You MUST NOT read `.ai/roadmap/**/*.md` directly, read `index.json`, or infer status from design docs, OpenSpec history, or example tables. The script is the single source of truth for status queries.

**Workflow:**
1. Run `python3 skills/sdlc-roadmap/scripts/list.py` with appropriate flags:
   - No flags: global view, all items (done + incomplete).
   - `--incomplete`: exclude done, cancelled (returns ready/active/idea).
   - `--done`: show only done items.
   - `--status ready,active`: exact status match.
   - `python3 skills/sdlc-roadmap/scripts/list.py <area-id>`: single area view, can combine with flags.
2. Report the results to the user. Do not supplement from other sources.
3. If the script outputs "No roadmap found", say "No roadmap found. Use 'roadmap init' to create the roadmap structure."

### roadmap review

Guide review of roadmap ideas before they become ready OpenSpec-backed work. Combines `roadmap review RM-xxx` (specific) and `roadmap review` (prompt for selection).

**Trigger:** User says "review RM-xxx", "review roadmap", "roadmap review", or equivalent.

**Workflow for specified item (`roadmap review RM-xxx`):**
1. Read the item file for RM-xxx.
2. Verify the item status is `idea`. If not `idea`, report current status and ask whether to proceed.
3. Guide review across the following checklist:
   - **Goal**: Is the goal clear and achievable in one phase?
   - **Scope**: Are In/Out boundaries well-defined? Anything missing or over-scoped?
   - **Acceptance Criteria**: Are they verifiable and complete?
   - **Dependencies**: Are `depends_on` items identified and correct?
   - **Priority**: Is `p0`/`p1`/`p2`/`p3` appropriate?
   - **Order**: Does the order reflect implementation sequencing?
4. Surface any issues found. Ask the user for revisions or confirmation.
5. **If review does NOT pass:** Item remains `idea`. No OpenSpec change created. Summarize what needs improvement.
6. **If review passes:** Create complete OpenSpec artifacts (proposal, design, specs, tasks) for the item. Then:
   - Set `status: ready`
   - Set `openspec_change: <change-id>`
   - Append a changelog entry to `revisions/changelog.md`
   - No snapshot needed (content not overwritten)
7. After item becomes `ready`, check for remaining `idea` items:
   - If more `idea` items exist: ask "Continue reviewing next idea, or start applying a ready change?"
   - If no `idea` items remain: ask "Start applying a ready change?"

**Workflow for unspecified review (`roadmap review`):**
1. List all `idea` items using `list.py --status idea`.
2. Ask the user to choose one.
3. Proceed with the specified review workflow above.

**Rules:**
- Only `idea` items can be reviewed. `ready` items already have complete OpenSpec artifacts.
- Review-passed artifact creation uses `openspec-propose` or `openspec-new-change` with the item's Goal, Scope, Acceptance Criteria, and Promotion Notes as input.
- Do NOT create OpenSpec artifacts manually; route through OpenSpec skills.

### roadmap revise RM-xxx

Revise a roadmap item's content with traceable history.

**Trigger:** User says "revise RM-xxx", "update RM-xxx goal/scope/AC", "修改 RM-xxx", or equivalent.

**Workflow:**
1. Read the item file for RM-xxx.
2. Save a full snapshot of the current item to `revisions/snapshots/RM-xxx-<timestamp>.md` before any changes.
3. Apply the requested content changes (Goal, Scope, Acceptance Criteria, Promotion Notes, Design Reference).
4. Append a changelog entry to `revisions/changelog.md` with: timestamp, action (`revise`), item id, reason, change summary, snapshot path.
5. Handle status-sensitive cases:
   - **`ready` item revised on core semantics**: Ask whether to keep `ready` or return to `idea` for re-review.
   - **`active` item revised**: Warn that the linked OpenSpec change may also need updating.
6. Run `rebuild_index.py`.

**Rules:**
- Snapshot-before-edit is mandatory for `revise`. The snapshot is the full item content before changes.
- Changelog entry is mandatory.
- Revise does not change status (except per the ready/active warnings above).

### roadmap insert

Add a new roadmap item with optional positional placement.

**Trigger:** User says "insert RM-xxx", "add roadmap item", "append RM-xxx", or equivalent.

**Workflow:**
1. Identify the target area. If unclear, ask or use `default_area`.
2. Collect item details: title, goal, scope, acceptance criteria, stage, priority.
3. Determine placement:
   - **No `--before` or `--after`**: Append to end of area (assign next `order` in increments of 10).
   - **`--before RM-xxx`**: Insert before the referenced item. Adjust `order` values in increments of 5 or renumber.
   - **`--after RM-xxx`**: Insert after the referenced item. Adjust `order` values accordingly.
4. Create the item file with `status: idea`.
5. Append a changelog entry to `revisions/changelog.md`.
6. Update area `roadmap.md` and run `rebuild_index.py`.

**Rules:**
- New items always start as `idea`.
- No snapshot is created for insert (new content, nothing overwritten).
- Assign IDs sequentially using the area's `id_prefix`.

### roadmap reorder

Change the priority or positional order of implementation items.

**Trigger:** User says "reorder RM-xxx", "reprioritize RM-xxx", "move RM-xxx before/after", or equivalent.

**Workflow:**
1. Read the item file for RM-xxx.
2. Apply the requested changes:
   - **`--priority p1`**: Update `priority` field only. Status unchanged.
   - **`--before RM-yyy`**: Move RM-xxx before RM-yyy. Update `order` values. `priority` unchanged.
   - **`--after RM-yyy`**: Move RM-xxx after RM-yyy. Update `order` values.
   - **Both flags**: Update both `priority` and positional `order`.
3. Append a changelog entry to `revisions/changelog.md` with action `reorder`.
4. Run `rebuild_index.py`.

**Rules:**
- No snapshot is needed (order/priority changes are tracked by changelog).
- Reorder does not change status.
- `priority` and `order` are independent: priority is business importance, order is sequencing position.

### roadmap cancel RM-xxx

Cancel a roadmap item while preserving history.

**Trigger:** User says "cancel RM-xxx", "取消 RM-xxx", or equivalent.

**Workflow:**
1. Read the item file for RM-xxx.
2. Save a full snapshot of the current item to `revisions/snapshots/RM-xxx-<timestamp>.md`.
3. Handle by current status:
   - **`idea` or `ready`**: Mark `status: cancelled`. Append changelog entry.
   - **`active`**: Ask the user to choose:
     - `keep active`: Do not cancel. Exit.
     - `cancel and remove OpenSpec change`: Record the change id and path in revision notes. Remove the linked OpenSpec change. Mark `status: cancelled`.
   - **`done`**: Refuse. Done items are terminal history. Suggest `replan` if needed.
4. Append a changelog entry to `revisions/changelog.md` with action `cancel`, reason, and snapshot path.
5. Update area `roadmap.md` and run `rebuild_index.py`.

**Rules:**
- Snapshot-before-cancel is mandatory.
- Cancelled item files are preserved, not deleted.
- Active items require explicit OpenSpec change handling to avoid dangling changes.

### roadmap replan

Replace unfinished roadmap plans for a whole area while preserving completed and cancelled history.

**Trigger:** User says "replan <area>", "重新规划", "replan roadmap", or equivalent.

**Workflow:**
1. Identify the target area. If not specified, list areas and ask.
2. Read all items in the area. Categorize them:
   - **Preserve**: `done` and `cancelled` items. They remain untouched.
   - **Archive**: `idea` and `ready` items. They are recorded in a batch revision.
   - **Decide**: `active` items. For each, ask the user:
     - `keep active`: Item stays as-is.
     - `cancel and remove OpenSpec change`: Record change id/path. Cancel the item. Remove the OpenSpec change.
3. Create a batch revision file at `revisions/batch/RM-<area>-replan-<timestamp>.md` listing:
   - Preserved items (done, cancelled).
   - Archived items (idea, ready) with their former state.
   - Active decisions (kept or cancelled).
   - New plan overview.
4. Create new `idea` items for the replanned phases.
5. Append a changelog entry summarizing the replan: timestamp, action (`replan`), area, archived/preserved/new counts, batch revision path.
6. Update area `roadmap.md` and run `rebuild_index.py`.

**Rules:**
- Replan uses a batch revision file, not per-item snapshots.
- Done and cancelled items are never deleted or modified by replan.
- Active items require explicit decisions per item, not a blanket rule.

### roadmap done RM-xxx

Mark a roadmap item as done. This is the roadmap-side mutation invoked either directly by the user or by `sdlc-orchestrator` from the post-archive gate.

**Workflow:**
1. Read the item file.
2. Verify the item is `active`. If not, report current status and ask for confirmation.
3. Update item:
   - `status: done`
   - `completed_at: <today>`
4. Fill `# Completion Notes` with what was accomplished, what was deferred, and what follow-up items surfaced.
5. Append a changelog entry to `revisions/changelog.md` with action `done`.
6. Update area `roadmap.md` and run `rebuild_index.py`.
7. Run `validate.py`.
8. Prompt the user:
   - "Consider running `sdlc-repository-memory-sync` to preserve long-term facts."
   - "Should the roadmap be re-planned? Use `roadmap replan`."

**Rules:**
- `sdlc-orchestrator` owns the post-archive gate. When OpenSpec archive succeeds, the orchestrator finds the matching `active` roadmap item and routes to `sdlc-roadmap done <item-id>`. Roadmap only executes the mutation after being invoked.
- Manual `roadmap done` is also supported for items without a linked OpenSpec change.
- Do NOT auto-trigger memory sync — only prompt the user.

### apply-start transition

When apply or implementation begins for a `ready` item, transition it to `active`.

**Workflow:**
1. When `openspec-apply-change` or equivalent starts for a `ready` roadmap item:
   - Set `status: active`
   - Set `started_at: <today>`
2. Append a changelog entry with action `apply-start`.
3. Run `rebuild_index.py`.

**Rules:**
- `idea` items cannot be applied. If the user attempts to apply an `idea` item, prompt them to complete review first.
- No snapshot is needed for apply-start (status change only).

## Orchestrator Post-Archive Boundary

The `sdlc-orchestrator` owns the post-archive gate that triggers roadmap completion:

1. When OpenSpec archive succeeds, the orchestrator checks if any roadmap item has `openspec_change` matching the archived change and `status: active`.
2. If exactly one match is found, the orchestrator routes to `sdlc-roadmap done <item-id>`.
3. If no match is found, the orchestrator reports a sync mismatch and does not guess an item.
4. If a matching item exists but is not `active`, the orchestrator reports a sync mismatch and does not overwrite the status.

`sdlc-roadmap` only owns the safe mutation after being invoked by the orchestrator. It does not watch archives or initiate state transitions.

## Revision History Model

### Changelog

Every mutation appends to `revisions/changelog.md`. Each entry includes:

```markdown
| Timestamp | Action | Item(s) | Reason | Summary | Snapshot/Revision | OpenSpec Change |
|-----------|--------|---------|--------|---------|-------------------|-----------------|
| 2026-06-17T15:00:00 | revise | RM-SDLC-002 | Scope clarification | Updated In/Out scope | snapshots/RM-SDLC-002-20260617T150000.md | - |
```

### Snapshots

Snapshots are created only when semantic content is overwritten or an item is terminated:
- `revise`: full item snapshot before content changes.
- `cancel`: full item snapshot before status change.

Snapshots are NOT created for: insert, review, reorder, apply-start, or done (unless content is also revised).

Snapshots are stored under `revisions/snapshots/` as `RM-xxx-<timestamp>.md`.

### Batch Revisions

`replan` creates a single batch revision file at `revisions/batch/RM-<area>-replan-<timestamp>.md` documenting the old and new plans, active decisions, and preserved items.

## Boundary Rules

### Roadmap vs OpenSpec

| Roadmap | OpenSpec |
|---------|----------|
| What to build and when | How to build this change |
| Long-term sequencing | Single change lifecycle |
| Stage goals and priorities | Formal spec/design/tasks |
| Review creates OpenSpec artifacts | Proposal → verify → archive |

**Rule:** Roadmap does not duplicate OpenSpec. Review routes to OpenSpec skills for artifact creation. Roadmap owns the item status and history.

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
| Roadmap item content correction | `roadmap revise` with snapshot |
| Roadmap reordered after learning | `roadmap reorder` |
| Area-level replan after major discovery | `roadmap replan` |

## Guardrails

- Do NOT create OpenSpec proposal/design/tasks/spec files directly. Route through OpenSpec skills via review workflow.
- Do NOT auto-trigger memory sync. Only prompt and let the user decide.
- Do NOT silently overwrite existing `.ai/roadmap/` files.
- Do NOT delete or remove items. Use `cancel` with snapshot or `replan` for area-level changes.
- Item files are the source of truth. When `index.json` disagrees, report the diff and offer to rebuild.
- Run `validate.py` after any item modification to catch inconsistency early.
- Assign order values in increments of 10 to allow insertion without full renumbering.
- Changelog entries are mandatory for all mutations. Snapshots are mandatory for revise and cancel.
- The orchestrator, not roadmap, triggers post-archive roadmap done.

## Script Reference

- `scripts/validate.py` — Validate item frontmatter, index.json consistency, state legality, dangling depends_on references. Enforces minimal status model (idea/ready/active/done/cancelled).
- `scripts/rebuild_index.py` — Rebuild `index.json` from `items/*.md` frontmatter (backups existing index as `.bak`).
- `scripts/list.py` — Output roadmap summary table sorted by `order`.
- `scripts/sync.py` — Report-oriented lifecycle mismatch diagnostics comparing OpenSpec status to roadmap item status. Does NOT trigger state transitions.

## Templates Reference

- `templates/roadmap.md` — `.ai/roadmap/roadmap.md` template with overview table and active/next sections.
- `templates/item.md` — Roadmap item template with frontmatter and body sections.
- `templates/decisions.md` — `.ai/roadmap/decisions.md` template for cross-item decision records.
- `templates/changelog.md` — `revisions/changelog.md` template with table headers.
- `templates/snapshot-item.md` — `revisions/snapshots/` item snapshot template.
- `templates/batch-revision.md` — `revisions/batch/` batch replan revision template.
