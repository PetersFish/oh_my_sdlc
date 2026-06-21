# Revision Changelog

Every roadmap mutation appends to this file.

| Timestamp | Action | Item(s) | Reason | Summary | Snapshot/Revision | OpenSpec Change |
|-----------|--------|---------|--------|---------|-------------------|-----------------|
| 2026-06-20T13:14:06Z | insert | RM-ORCH-001 | Capture SDLC governance Phase 1 | Added OpenCode validation roadmap item for governance-check and plugin trigger. | - | - |
| 2026-06-20T13:14:06Z | insert | RM-ORCH-002 | Capture SDLC governance Phase 2 | Added cross-platform hook adaptation roadmap item for Claude Code and Cursor adapters. | - | - |
| 2026-06-20T13:35:36Z | revise | RM-ORCH-001 | Capture resolved governance-check design decisions | Recorded valid archive evidence rules, idle gate semantics, watcher deferral, prompt stop condition, and remaining OpenCode plugin uncertainties. | snapshots/RM-ORCH-001-20260620T133536Z.md | - |
| 2026-06-20T13:42:31Z | revise | RM-ORCH-001 | Clarify remaining uncertainty type | Renamed remaining OpenCode adapter uncertainties from Open Questions to Validation Questions to distinguish them from resolved design decisions. | snapshots/RM-ORCH-001-20260620T134231Z.md | - |
| 2026-06-20T14:09:54Z | revise | RM-ORCH-002 | Resolve cross-platform adapter design questions | Recorded Cursor conditional support model, explicit per-platform command selection, and Cursor support verification matrix. | snapshots/RM-ORCH-002-20260620T140954Z.md | - |
| 2026-06-20T14:18:39Z | revise | RM-ORCH-002 | Capture Cursor validation results | Recorded Cursor 3.8.11 on macOS Tahoe 26.5.1 as first target, remediation-driving stop-hook feedback, and `python3` as Windows-native command choice. | snapshots/RM-ORCH-002-20260620T141839Z.md | - |
| 2026-06-20T22:24:00Z | review | RM-ORCH-001 | Roadmap review passed; promote to OpenSpec | Created OpenSpec artifacts and marked item ready for apply. | - | opencode-governance-validation |
| 2026-06-21T19:30:00Z | insert | RM-ORCH-003 | Capture governance UX improvement | Added roadmap item for auto-dispatching governance remediation to LLM assistant. | - | - |
| 2026-06-21T19:30:00Z | insert | RM-ORCH-004 | Capture workflow state cleanup | Added roadmap item for clearing current.json on workflow run done. | - | - |
| 2026-06-21T20:00:00Z | insert | RM-ORCH-005 | Capture workflow governance gap | Added roadmap item requiring workflow run before all Roadmap and OpenSpec stateful mutations. | - | - |
| 2026-06-21T20:00:00Z | reorder | RM-ORCH-004, RM-ORCH-003 | Update priority and dependency sequence | RM-ORCH-004 order 30 (first), RM-ORCH-005 order 40 (second), RM-ORCH-003 order 50 (third). RM-ORCH-003 now depends on RM-ORCH-005. | - | - |
