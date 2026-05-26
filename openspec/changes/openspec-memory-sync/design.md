## Context

The repository already has a structured OpenSpec workflow and separate skills for applying, verifying, and archiving changes. This change adds a post-verify gate that turns a finished change into durable project memory with evidence-backed doc updates.

## Goals / Non-Goals

**Goals:**
- Capture durable memory immediately after verification.
- Keep the workflow evidence-backed and reviewable.
- Update only the docs that are actually affected.
- Produce a traceable `memory-sync.md` report for every synced change.

**Non-Goals:**
- Build a full repository memory system with indexes or compression layers.
- Rewrite docs wholesale.
- Add new runtime services or external dependencies.

## Decisions

- Use a single `openspec-memory-sync` skill as the post-verify gate.
  - This keeps the workflow easy to trigger and easy to explain.
  - Alternatives considered: a separate automation script, or embedding the logic in archive. The separate skill is easier to review and invoke explicitly.

- Treat CodeGraph as the default structural evidence source.
  - It gives symbol-level impact data when available.
  - Alternative: rely only on git diff. Rejected because it loses caller/callee context.

- Limit durable outputs to ADRs, pitfalls, and module docs.
  - These are the smallest useful long-lived memory surfaces for the MVP.
  - Alternative: add evolution and index layers now. Rejected as out of scope.

- Make archive blocking explicit when evidence is incomplete.
  - This prevents a weak or speculative memory sync from being treated as complete.
  - Alternative: always proceed with a warning. Rejected because it weakens the gate.

## Risks / Trade-offs

- CodeGraph may be unavailable or stale → fall back to diff and targeted reads, and label the result lower confidence.
- The skill may be too strict for quick cleanups → allow explicit user waivers when they want to archive without the full evidence set.
- Durable docs may accumulate noise over time → keep updates minimal and only touch docs that the evidence supports.

## Migration Plan

1. Add the skill under `skills/openspec-memory-sync/SKILL.md`.
2. Add the change artifacts under `openspec/changes/openspec-memory-sync/`.
3. Use the skill in the `verify -> memory-sync -> archive` flow for future OpenSpec changes.
4. If a change cannot produce the required evidence, pause the archive step until the gap is resolved or waived.

## Open Questions

- What exact format should `memory-sync.md` use once the skill is implemented?
- Which existing project doc paths should receive ADR, pitfall, and module updates in this repository?
