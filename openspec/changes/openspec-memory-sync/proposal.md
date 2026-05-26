## Why

Verified OpenSpec changes still leave durable memory updates to manual follow-up, which makes architectural decisions, pitfalls, and module changes easy to lose before archive. This change adds a lightweight memory-sync gate so the repository captures evidence-backed knowledge while the change context is fresh.

## What Changes

- Add a new `openspec-memory-sync` skill under `skills/` for post-verify memory sync.
- Require the skill to run after verification and before archive.
- Have the skill read change artifacts, verification evidence, and the implementation intelligence summary.
- Use CodeGraph as the default structural evidence source when available, with a git diff and targeted file-read fallback.
- Update only targeted durable docs: ADRs, pitfalls, and module docs.
- Write `openspec/changes/<change-id>/memory-sync.md` with traceability, changed docs, and residual gaps.
- Block archive when required evidence is missing unless the user explicitly waives the gate.

## Capabilities

### New Capabilities
- `openspec-memory-sync`: evidence-backed memory sync for verified OpenSpec changes; updates durable docs and records a per-change sync report.

### Modified Capabilities
- None.

## Impact

- New skill file at `skills/openspec-memory-sync/SKILL.md`.
- New spec, design, tasks, plan, and verify artifacts under `openspec/changes/openspec-memory-sync/`.
- Potential updates to project docs that store ADRs, pitfalls, and module intelligence.
- Archive workflow now expects a memory-sync report before finalizing a meaningful change.
