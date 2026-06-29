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
| RM-ORCH-007 | done | Agent-Backed Lifecycle Wrapper Architecture | v2 | agent-backed-lifecycle-wrapper-architecture | Decouple workflow modules from concrete worker implementations through agent-backed wrapper contracts. |
| RM-ORCH-008 | idea | Workflow State Machine Contract Enhancements | v2 | - | Add minimal `flow_type`, evidence-key, and agent evidence contracts before wrapper implementation. |
| RM-ORCH-009 | idea | Workflow Runtime Modularization | v2 | - | Split workflow runtime responsibilities while preserving the `workflow.py` CLI facade. |
| RM-ORCH-010 | idea | Class-Based Workflow State Machine | v2 | - | Introduce a standard state-machine core after modularization. |
| RM-ORCH-003 | idea | Governance Remediation Auto-Dispatch | v2 | - | Auto-dispatch governance findings to LLM instead of requiring manual prompt sending. |

## Active Item

None.

## Next Recommended Action

Review or apply `RM-ORCH-008` (Workflow State Machine Contract Enhancements) next, followed by RM-ORCH-009 and RM-ORCH-010 for post-wrapper cleanup.
