# Brainstorm

## Problem

OpenSpec changes are being verified, but the durable project memory that should follow them is still manual. That creates drift: important decisions, pitfalls, and module-level changes are easy to miss before archive, so future agents have less reliable context.

## Constraints

- MVP only: capture ADRs, pitfalls, and module intelligence, not a full long-term memory system.
- Must fit the existing OpenSpec flow and remain reviewable by a human.
- Must use evidence from the change, not invented rationale.
- Must prefer CodeGraph when available, but still work with git diff and targeted file reads.
- Must keep diffs minimal and avoid rewriting whole docs.

## Options

1. **Lightweight archive gate**
   - Only require a memory-sync note before archive.
   - Lowest effort, but it does not actually update durable docs.

2. **Targeted memory sync gate**
   - Classify evidence into ADR, pitfall, and module-doc updates.
   - Write a per-change memory-sync report and update only the affected docs.
   - Best balance of usefulness and reviewability.

3. **Full repository memory system**
   - Add indexes, evolution layers, and compressed lessons.
   - Too broad for the MVP and would add unnecessary complexity.

## Recommendation

Choose **Targeted memory sync gate**. It gives the repository durable memory with evidence-backed updates while staying small enough to adopt immediately in the `verify -> memory-sync -> archive` flow.
