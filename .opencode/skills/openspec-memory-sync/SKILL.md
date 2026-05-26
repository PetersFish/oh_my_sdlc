---
name: openspec-memory-sync
description: OpenSpec memory sync, memory-sync.md, verify, archive, ADR, pitfall, module docs. Use when a verified OpenSpec change needs durable docs updated before archive, or when the user says memory sync, openspec-memory-sync, post-verify, before archive, or wants to turn an OpenSpec change into evidence-backed repository memory. Do not use for ordinary code changes or broad documentation rewrites.
license: MIT
---

# OpenSpec Memory Sync

Use this skill to turn a verified OpenSpec change into durable project memory.

## Purpose

Capture evidence-backed repository memory after verification and before archive. Keep the updates targeted, reviewable, and limited to the MVP surfaces: ADRs, pitfalls, and module docs.

## When to Use

- After `openspec-verify-change` and before `openspec-archive-change`.
- When the user asks to sync memory, update docs after an OpenSpec change, or write `memory-sync.md`.
- When a verified change needs durable documentation of decisions, risks, or module responsibility changes.

## Required Inputs

- OpenSpec change name or change directory.
- Verification evidence.
- Implementation Intelligence Summary with: Design Decisions, New Complexity, Core Modules Touched, Potential Risks, and Known Tradeoffs.
- Git diff against the base branch.
- Existing docs paths for ADRs, pitfalls when real blockers occurred, and module docs.

## Workflow

1. Read the OpenSpec artifacts for the change.
2. Read the verification evidence and implementation intelligence summary.
3. Inspect the git diff and changed files.
4. Use CodeGraph by default when available:
   - changed symbols
   - callers and callees
   - impact radius
   - affected tests
5. Fall back to git diff plus targeted file reads when CodeGraph is unavailable or stale.
6. Classify the evidence into memory deltas.
7. Update only the docs that the evidence supports:
   - `docs/decisions/ADR-*.md` when the current evidence shows a durable design decision changed.
   - `docs/pitfalls.md` or `docs/pitfalls/*.md` when the current session produced an actual blocker, repeated failed attempt, debugging trap, or non-obvious workaround.
   - `docs/modules/*.md` when the current evidence shows module responsibility, public behavior, ownership, or integration boundary changed.
8. Write `openspec/changes/<change-id>/memory-sync.md` with:
    - changed files
    - evidence used
    - residual gaps
    - confidence notes if fallback analysis was required
9. Stop before archive if required evidence is missing, unless the user explicitly waives the gate.

## Guardrails

- Do not rewrite whole docs when a minimal targeted diff will do.
- Do not invent rationale that is not supported by evidence.
- Do not create or update ADR, pitfall, or module docs unless the current chat, OpenSpec artifacts, verification evidence, implementation summary, git diff, or changed files prove that memory type changed.
- If no ADR, pitfall, or module memory applies, still write `memory-sync.md` and explicitly say those doc types are not applicable for this change.
- Do not expand into V2 memory layers, indexes, or compression systems.
- Do not bloat `AGENTS.md`; keep long-lived details in the targeted docs instead.
- Do not allow archive to proceed silently when the implementation intelligence summary is missing.

## Output

Return a concise memory-sync summary that names the docs updated, the doc types skipped as not applicable, the evidence used, and any remaining gaps before archive.
