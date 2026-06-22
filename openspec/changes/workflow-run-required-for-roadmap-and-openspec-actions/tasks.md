## 1. Workflow Runtime Policies

- [ ] 1.1 Register governed roadmap actions in `.ai/workflows/scripts/workflow.py`: `roadmap_capture`, `roadmap_insert`, `roadmap_review`, `roadmap_revise`, `roadmap_cancel`, `roadmap_reorder`, `roadmap_replan`, and `roadmap_done`.
- [ ] 1.2 Add `roadmap_item` phase inference so new roadmap item runs start at `create_roadmap` and review-ready runs can reach `review_roadmap`.
- [ ] 1.3 Add or update shared policy helpers so non-phase-changing roadmap mutations require a matching active run without advancing phase.
- [ ] 1.4 Add a single-subject `cancel-run` runtime primitive for replanned roadmap item runs that removes the active run, clears `current.json` when needed, and does not write history.

## 2. Canonical-Run Promotion

- [ ] 2.1 Extend `openspec_create` preflight to find linked `roadmap_item` runs: scan active runs for one whose `context.change_id` or roadmap item frontmatter `openspec_change` matches the requested change id.
- [ ] 2.2 When a linked roadmap item run is found, set pointer to that run, validate against `create_change` phase, and return `allowed: true` without requiring a new `openspec_change` run.
- [ ] 2.3 Update `workflow.py start` subject-dedup logic to prevent duplicate runs when promotion creates a linked change.
- [ ] 2.4 Clean up existing duplicate runs: preserve `roadmap_item/RM-ORCH-005` as canonical, cancel `openspec_change/workflow-run-required-for-roadmap-and-openspec-actions`, and migrate its useful evidence (OpenSpec artifact paths, roadmap link) into the canonical run.

## 3. Orchestrator And Roadmap Skill Boundaries

- [ ] 3.1 Update `skills/sdlc-orchestrator/SKILL.md` so roadmap-first actions run `verify-foundations`, preflight, worker dispatch, evidence recording, phase/hook completion, and guarded advance.
- [ ] 3.2 Document `roadmap_replan` follow-up handling in `skills/sdlc-orchestrator/SKILL.md`: loop over cancelled old items with `cancel-run` and created new items with `workflow.py start`.
- [ ] 3.3 Document promotion canonical-run semantics in `skills/sdlc-orchestrator/SKILL.md`: roadmap item run is canonical, promotion writes `change_id` and advances to `create_change` without starting a second run.
- [ ] 3.4 Update `skills/sdlc-roadmap/SKILL.md` to state that roadmap workers do not own workflow lifecycle and must provide mutation evidence for governed actions.
- [ ] 3.5 Update `sdlc-roadmap` replan instructions to require evidence with cancelled old item IDs, created new item IDs, and batch revision path.

## 4. Governance Check

- [ ] 4.1 Extend `workflow.py governance-check` to detect active roadmap items without matching active run or done history.
- [ ] 4.2 Extend governance-check to detect archived OpenSpec changes linked from roadmap items without matching workflow evidence.
- [ ] 4.3 Detect duplicate runs where both a `roadmap_item` run and an `openspec_change` run exist for the same promotion, and report remediation.
- [ ] 4.4 Ensure governance-check findings include explicit remediation commands and a stop condition to rerun governance-check until `block=false`.
- [ ] 4.5 Keep governance-check read-only and avoid modifying roadmap, OpenSpec, or workflow run files.

## 5. Tests

- [ ] 5.1 Add `tests/test_workflow.py` coverage for all roadmap preflight actions returning valid decisions instead of `unknown_action`.
- [ ] 5.2 Add tests for roadmap action phase validation, especially `roadmap_review` wrong-phase behavior.
- [ ] 5.3 Add tests for `cancel-run`: removes active file, clears pointer when pointed, does not write history, and is safe when no matching run exists.
- [ ] 5.4 Add tests for canonical-run promotion: `openspec_create` preflight finds linked roadmap item run and returns `allowed: true`.
- [ ] 5.5 Add governance-check tests for ungoverned active roadmap items, archived linked items, and duplicate runs.
- [ ] 5.6 Run `python3 -m pytest tests/test_workflow.py -v`.

## 6. EvalOps

- [ ] 6.1 Add or update `skill.sdlc-orchestrator` EvalOps cases covering roadmap mutation preflight, roadmap replan follow-up loops, canonical-run promotion, and prevention of direct roadmap worker dispatch before preflight.
- [ ] 6.2 Triage any new EvalOps cases and promote accepted cases to golden before implementation is considered complete.
- [ ] 6.3 Export Promptfoo cases and run the golden eval for `skill.sdlc-orchestrator`; report target id, case counts, export freshness, eval command, result counts, and report path.

## 7. Template And Distribution Sync

- [ ] 7.1 Sync `.ai/workflows/scripts/workflow.py` changes to `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`.
- [ ] 7.2 Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` and fix any drift.
- [ ] 7.3 Redistribute modified canonical skills to `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/` where applicable.
- [ ] 7.4 Run relevant repository tests for skill distribution or frontmatter validation.

## 8. Roadmap Linkage

- [ ] 8.1 Update RM-ORCH-005 to `ready` with `openspec_change: workflow-run-required-for-roadmap-and-openspec-actions` after proposal artifacts are accepted.
- [ ] 8.2 Append a roadmap changelog entry documenting the review/promotion decision.
- [ ] 8.3 Rebuild and validate roadmap index after the status update.
