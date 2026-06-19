---
name: sdlc-openspec-memory-sync
description: OpenSpec post-verify memory sync gate. Use ONLY when a verified OpenSpec change needs durable docs (ADR, pitfall, module docs) updated before archive — specifically after openspec-verify-change and before openspec-archive-change. Also used as the worker for the mandatory post-archive memory_sync hook in sdlc-main workflow. Do NOT use for ordinary .ai/memory/ sync, session sync, code-change sync, or direct memory updates (use sdlc-repository-memory-sync for those).
license: MIT
---

# OpenSpec Memory Sync

OpenSpec adapter for repository memory sync. Collects OpenSpec change context, delegates to `sdlc-repository-memory-sync`, writes per-change report (when active directory available) or records workflow evidence (when change is already archived).

## Purpose

OpenSpec adapter for repository memory sync. This skill is a THIN WRAPPER that collects OpenSpec change context, delegates all memory operations to `sdlc-repository-memory-sync`, writes a per-change `memory-sync.md` report when the active change directory is available, or produces workflow evidence when the change has already been archived.

## When to Use

- After `openspec-verify-change` and before `openspec-archive-change` (traditional pre-archive gate).
- As the worker for the `memory_sync` post-archive hook in `sdlc-main` when invoked by the orchestrator after archive.
- When the user asks to sync memory for a verified OpenSpec change, or says "openspec-memory-sync" or "post-verify".
- When a verified change needs durable documentation of decisions, risks, or module responsibility changes.

**Do NOT use for:** ordinary code changes, session sync, or direct `.ai/memory/` updates after git commits — use `sdlc-repository-memory-sync` for those scenarios.

## Required Inputs

- OpenSpec change name or change directory.
- Verification evidence.
- Implementation Intelligence Summary.
- Git diff against the base branch.
- For post-archive runs: workflow-provided change context (archive path, evidence from `workflow.py`).

## Workflow

1. **Check manifest.** If `.ai/memory/manifest.json` exists, run `sdlc-repository-memory-load` first to hydrate context from existing memory. Do not skip this step when memory exists.
2. **Detect OpenSpec change ID** using this priority order:
   - User explicit specification (the user names a change ID directly).
   - Git diff touches one `openspec/changes/<id>/` — use that ID.
   - Current path inside `openspec/changes/<id>/` — use that ID.
   - Exactly one active (un-archived) OpenSpec change — use that ID.
   - Workflow-provided context (archive path, change id from `workflow.py` evidence).
   - Archive path (`openspec/changes/archive/<id>`) — use that archived ID.
   - None matched — ask the user to specify.
3. **Detect spec lineage.** If multiple active changes form a lineage (B refines A), ask the user to confirm the relationship before proceeding.
4. **Collect OpenSpec artifacts.** If the active change directory exists, read: `proposal.md`, `design.md`, `spec.md`, `tasks.md`, `verify.md`. For post-archive runs where the active directory no longer exists, use workflow-provided context and archive artifacts.
5. **Delegate to `sdlc-repository-memory-sync`.** Pass the OpenSpec context (change ID, artifacts, lineage) to the `sdlc-repository-memory-sync` workflow. This skill does NOT duplicate memory sync logic — all classification, per-type policy handling, and memory file creation is delegated.
6. **Apply per-type memory policies.** Follow `sdlc-repository-memory-sync` policies for each memory type (auto-update vs. candidate-only). For `decisions` and `architecture` types, present candidates and require user confirmation before writing formal memory.
7. **Handle `needs_user_review` items.** These are written to `.ai/memory/review-queue.json` only. Do NOT create formal memory files for them.
8. **Write per-change report or workflow evidence:**
   - **When active change directory exists:** Write `openspec/changes/<change-id>/memory-sync.md` with changed files, evidence used, OpenSpec context, memory deltas, residual gaps, and confidence notes.
   - **When change is already archived (`sdlc-main` post-archive hook):** Produce workflow evidence consumable by `workflow.py complete-hook --hook memory_sync`. The evidence must list changed files and the basis for the `memory_sync` resolution (`synced`, `not_needed`, or `user_deferred`).
9. **Resolution states for workflow runtime:**
   - `synced`: memory sync ran and produced evidence of durable memory updates.
   - `not_needed`: allowed only with an explicit reason explaining why no durable facts were produced.
   - `user_deferred`: allowed only with an explicit reason and residual risk recorded.

## Guardrails

- This skill is a WRAPPER, not the core memory system. Do NOT duplicate memory sync logic; delegate to `sdlc-repository-memory-sync`.
- Do NOT bypass `sdlc-repository-memory-load` when `.ai/memory/manifest.json` exists.
- Do NOT create formal memory for `needs_user_review` items.
- Do NOT allow archive to proceed silently when the implementation intelligence summary is missing (for pre-archive runs).
- Do NOT rewrite whole docs when a minimal targeted diff will do.
- Do NOT invent rationale not supported by evidence.
- For post-archive runs: accept workflow-provided change context when the active change directory is no longer available.

## Output

- **Pre-archive:** Per-change `memory-sync.md` report in `openspec/changes/<change-id>/` and repository memory updates via `sdlc-repository-memory-sync`.
- **Post-archive (sdlc-main hook):** Workflow evidence consumable by `workflow.py complete-hook --hook memory_sync --resolution <resolution> --reason <reason>`.

Return a concise summary naming the docs updated, doc types skipped, evidence used, pending items, and remaining gaps.