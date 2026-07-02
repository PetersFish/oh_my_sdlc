# Review Agent Handoff

## Metadata
- Run ID: 2026-07-01-roadmap-hook-governance-hardening
- Slice ID: default
- Agent: review-agent
- Phase: apply_change
- Flow Type: spec-flow
- Status: blocked

## Verification Evidence Reviewed
- test-agent handoff reports full verification passed: focused roadmap hook/routing tests, wrapper contract tests, `tests/test_sdlc_roadmap.py`, and full `tests/` suite.

## Review Findings

### Blocking: workflow template/distributed template drift remains
The live workflow runtime `.ai/workflows/scripts/workflow.py` is still not synced to the canonical bootstrap workflow template `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`.

Observed drift includes executable roadmap-governance behavior:
- `started_at` propagation in roadmap item loading/status helpers exists in live runtime but not canonical template.
- `roadmap-agent` validation and phase mapping exists in live runtime but not canonical template.
- `roadmap_status_ready_if_linked` and `roadmap_apply_start_if_ready` complete-hook validation exists in live runtime but not canonical template.
- Shared roadmap hook helpers exist in live runtime but not canonical template.

The project-level distributed bootstrap workflow templates also remain stale relative to the canonical template: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`, `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`, and `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` are missing the canonical `roadmap-agent` after-dispatch branch.

This is actionable and blocking because repository policy requires `.ai/workflows/scripts/workflow.py` changes to be synced to `skills/sdlc-project-bootstrap/templates/workflow/`, and skill changes to be distributed to project-level `.opencode`, `.claude`, and `.cursor` copies. Without this, freshly bootstrapped/distributed workflows would miss the roadmap governance behavior even though live-runtime tests pass.

## Prior Findings Re-Review
- roadmap-agent after-dispatch semantics: resolved in live runtime and covered by behavioral tests, but not fully propagated to distributed bootstrap templates.
- stale distributed agent copies: resolved for agent prompts checked (`dev-orchestrator`, `finish-agent`, `roadmap-agent`).
- tasks checklist honesty: no blocking code issue found; remaining unchecked items reflect commands/artifacts not completed in the task file.

## Recommended Fix
Route back to implement-agent to sync live workflow changes into the canonical bootstrap workflow template, distribute the canonical skill template to `.opencode`, `.claude`, and `.cursor`, then re-run template consistency checks plus the already-passing verification set.
