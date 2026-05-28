---
name: sdlc-openspec-memory-sync
description: OpenSpec memory sync, memory-sync.md, verify, archive, ADR, pitfall, module docs. Use when a verified OpenSpec change needs durable docs updated before archive, or when the user says memory sync, openspec-memory-sync, post-verify, before archive, or wants to turn an OpenSpec change into evidence-backed repository memory. Do not use for ordinary code changes or broad documentation rewrites.
license: MIT
---

# OpenSpec Memory Sync

OpenSpec adapter for repository memory sync. Collects OpenSpec change context, delegates to `sdlc-repository-memory-sync`, preserves the archive gate, writes per-change report.

## Purpose

OpenSpec adapter for repository memory sync. This skill is a THIN WRAPPER that collects OpenSpec change context, delegates all memory operations to `sdlc-repository-memory-sync`, preserves the `verify -> memory-sync -> archive` gate, and writes a per-change `memory-sync.md` report.

## When to Use

- After `openspec-verify-change` and before `openspec-archive-change`.
- When the user asks to sync memory for an OpenSpec change, or says "memory sync", "openspec-memory-sync", or "post-verify".
- When a verified change needs durable documentation of decisions, risks, or module responsibility changes.

## Required Inputs

- OpenSpec change name or change directory.
- Verification evidence.
- Implementation Intelligence Summary.
- Git diff against the base branch.

## Workflow

1. **Check manifest.** If `.ai-memory/manifest.json` exists, run `sdlc-repository-memory-load` first to hydrate context from existing memory. Do not skip this step when memory exists.
2. **Detect OpenSpec change ID** using this priority order:
   - User explicit specification (the user names a change ID directly).
   - Git diff touches one `openspec/changes/<id>/` — use that ID.
   - Current path inside `openspec/changes/<id>/` — use that ID.
   - Exactly one active (un-archived) OpenSpec change — use that ID.
   - Archive path (`openspec/archive/<id>`) — use that archived ID.
   - None matched — ask the user to specify.
3. **Detect spec lineage.** If multiple active changes form a lineage (B refines A), ask the user to confirm the relationship before proceeding.
4. **Collect OpenSpec artifacts.** Read the change directory for: `proposal.md`, `design.md`, `spec.md`, `tasks.md`, `verify.md`.
5. **Delegate to `sdlc-repository-memory-sync`.** Pass the OpenSpec context (change ID, artifacts, lineage) to the `sdlc-repository-memory-sync` workflow. This skill does NOT duplicate memory sync logic — all classification, per-type policy handling, and memory file creation is delegated.
6. **Apply per-type memory policies.** Follow `sdlc-repository-memory-sync` policies for each memory type (auto-update vs. candidate-only). For `decisions` and `architecture` types, present candidates and require user confirmation before writing formal memory.
7. **Handle `needs_user_review` items.** These are written to `.ai-memory/review-queue.json` only. Do NOT create formal memory files for them.
8. **Preserve archive gate.** Do not proceed if required evidence (verification results, implementation intelligence summary) is missing, unless the user explicitly waives.
9. **Write `openspec/changes/<change-id>/memory-sync.md`** with:
   - Changed files
   - Evidence used
   - OpenSpec context (change ID, lineage, artifacts referenced)
   - Memory deltas (what was written, to which memory type)
   - Residual gaps
   - Confidence notes

## Guardrails

- This skill is a WRAPPER, not the core memory system. Do NOT duplicate memory sync logic; delegate to `sdlc-repository-memory-sync`.
- Do NOT bypass `sdlc-repository-memory-load` when `.ai-memory/manifest.json` exists.
- Do NOT create formal memory for `needs_user_review` items.
- Do NOT allow archive to proceed silently when the implementation intelligence summary is missing.
- Do NOT rewrite whole docs when a minimal targeted diff will do.
- Do NOT invent rationale not supported by evidence.

## Output

Per-change `memory-sync.md` report in `openspec/changes/<change-id>/` and repository memory updates via `sdlc-repository-memory-sync`. Return a concise summary naming the docs updated, doc types skipped, evidence used, pending items, and remaining gaps before archive.