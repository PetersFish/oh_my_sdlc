# SDLC Orchestrator Workflow Roadmap

Area: workflow.sdlc-orchestrator

## Current Sequence

| ID | Status | Title | Stage | OpenSpec | Notes |
|---|---|---|---|---|---|
| RM-ORCH-001 | ready | OpenCode Governance Validation | mvp | opencode-governance-validation | Validate governance-check and OpenCode plugin trigger. |
| RM-ORCH-002 | idea | Cross-Platform Hook Adaptation | v2 | - | Add Claude Code and Cursor adapters after OpenCode validation. |
| RM-ORCH-004 | idea | Clear Current Run On Done | v2 | - | Remove current.json after workflow run reaches done; keep only history. |
| RM-ORCH-005 | idea | Workflow Run Required For Roadmap And OpenSpec Actions | v2 | - | Require matching workflow run before all Roadmap and OpenSpec stateful mutations. |
| RM-ORCH-003 | idea | Governance Remediation Auto-Dispatch | v2 | - | Auto-dispatch governance findings to LLM instead of requiring manual prompt sending. |

## Active Item

None.

## Next Recommended Action

Start applying `opencode-governance-validation` when ready to implement Phase 1.
