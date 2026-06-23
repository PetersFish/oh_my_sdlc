# SDLC Orchestrator Workflow Roadmap

Area: workflow.sdlc-orchestrator

## Current Sequence

| ID | Status | Title | Stage | OpenSpec | Notes |
|---|---|---|---|---|---|
| RM-ORCH-001 | done | OpenCode Governance Validation | mvp | opencode-governance-validation | Validated governance-check and OpenCode plugin. |
| RM-ORCH-002 | idea | Cross-Platform Hook Adaptation | v2 | - | Add Claude Code and Cursor adapters (p3, deferred). |
| RM-ORCH-006 | done | Multi-Run Concurrent Support | v2 | multi-run-concurrent-support | Replace current.json with active/ directory + pointer. |
| RM-ORCH-004 | done | Verify Done Run Cleanup From Active Directory | v2 | - | Verified active/ cleanup + pointer clear (side-effect of RM-ORCH-006/005). |
| RM-ORCH-005 | done | Workflow Run Required For Roadmap And OpenSpec Actions | v2 | workflow-run-required-for-roadmap-and-openspec-actions | Required matching workflow run before all Roadmap and OpenSpec stateful mutations. |
| RM-ORCH-007 | idea | Workflow Wrapper Abstraction | v2 | - | Decouple workflow modules from concrete worker implementations. |
| RM-ORCH-003 | idea | Governance Remediation Auto-Dispatch | v2 | - | Auto-dispatch governance findings to LLM instead of requiring manual prompt sending. |

## Active Item

None.

## Next Recommended Action

Review the next `idea` item: `RM-ORCH-007` (Workflow Wrapper Abstraction).
