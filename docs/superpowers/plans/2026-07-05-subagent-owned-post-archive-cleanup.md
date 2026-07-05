# Subagent-Owned Lifecycle Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace normal workflow runtime hooks with subagent-owned lifecycle cleanup while preserving `complete-hook` for legacy repair.

**Architecture:** The workflow definition becomes evidence-driven: normal phases no longer enqueue `post_hooks`, and `post_archive_actions` is completed by `finish-agent` evidence. `workflow.py` keeps the legacy hook machinery for old active runs but rejects premature cleanup claims during `archive_change` so the runtime has one normal-flow source of truth.

**Tech Stack:** Python workflow CLI, YAML workflow definition, unittest/pytest tests, Markdown agent prompts, derived artifact sync scripts.

---

## File Structure

- Modify `.ai/workflows/definitions/sdlc-main.yaml`: remove normal-path `post_hooks`, add cleanup evidence keys to `post_archive_actions`.
- Modify `.ai/workflows/scripts/workflow.py`: add an `after-dispatch` guard for premature `finish-agent` cleanup evidence; keep `complete-hook` behavior unchanged for legacy pending hooks.
- Modify `tests/test_workflow.py`: add executable workflow tests for no normal hook enqueue, post-archive cleanup evidence, premature cleanup rejection, and legacy repair.
- Modify `agents/finish-agent.md`: split `archive_change` and `post_archive_actions` responsibilities and evidence examples.
- Modify `agents/dev-orchestrator.md`: route normal cleanup through `finish-agent` in `post_archive_actions`; treat runtime hooks as legacy repair only.
- Modify `tests/test_wrapper_contracts.py`: update prompt-contract tests for hook-free normal flow and split finish-agent evidence.
- Sync derived workflow templates and distributed agent copies after canonical edits.

## Task 1: Add Workflow Behavior Tests For Hook-Free Normal Flow

**Files:**
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Add failing tests for archive and post-archive normal flow**

Add this test class after `class TestAdvanceGuarded(FixtureBase):` and before `class TestBranchPhase(FixtureBase):`.

```python
class TestSubagentOwnedLifecycleCleanup(FixtureBase):
    def _write_archive_ready_state(self, change_id="subagent-cleanup"):
        state = {
            "version": 1,
            "run_id": f"2026-07-05-{change_id}",
            "workflow": "sdlc-main",
            "flow_type": "lightweight-flow",
            "status": "running",
            "current_phase": "archive_change",
            "primary_subject": {"type": "spec_change", "id": change_id},
            "context": {"change_id": change_id},
            "phase_readiness": {
                "phase": "archive_change",
                "ready": True,
                "missing_required_inputs": [],
            },
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["apply_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-05T00:00:00",
        }
        self._write_current_state(state)
        return state

    def test_archive_change_completion_does_not_enqueue_normal_cleanup_hooks(self):
        self._write_archive_ready_state("no-hooks")
        rc, out, _ = run_workflow(
            self.tmp,
            "record-evidence",
            key="archive_path_exists",
            value="true",
        )
        self.assertEqual(rc, 0)

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("archive_change", data.get("completed_phases", []))
        self.assertEqual(data.get("pending_hooks"), [])
        self.assertNotIn("memory_sync", data.get("pending_hooks", []))
        self.assertNotIn("roadmap_done_if_relevant", data.get("pending_hooks", []))

    def test_archive_change_advances_to_post_archive_actions_without_hooks(self):
        self._write_archive_ready_state("advance-cleanup")
        run_workflow(
            self.tmp,
            "record-evidence",
            key="archive_path_exists",
            value="true",
        )
        run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="archive_path_exists",
        )

        rc, out, _ = run_workflow(self.tmp, "advance")

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "post_archive_actions")
        self.assertEqual(data.get("pending_hooks"), [])
        self.assertTrue(data["phase_readiness"]["ready"])

    def test_post_archive_actions_requires_cleanup_evidence(self):
        self._write_archive_ready_state("cleanup-required")
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["completed_phases"] = ["apply_change", "archive_change"]
        self._write_current_state(state)

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="cleanup_complete",
        )

        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("memory_sync_done", data["error"])
        self.assertIn("cleanup_complete", data["error"])

    def test_post_archive_actions_accepts_finish_agent_cleanup_evidence(self):
        self._write_archive_ready_state("cleanup-success")
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["completed_phases"] = ["apply_change", "archive_change"]
        self._write_current_state(state)
        finish_result = {
            "agent": "finish-agent",
            "status": "success",
            "phase": "post_archive_actions",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "memory_sync_done": True,
                "roadmap_done_checked": True,
                "derived_artifacts_synced": True,
                "post_hook_dirty_tree": False,
                "cleanup_complete": True,
                "criteria_satisfied": "cleanup_complete",
            },
            "artifacts": {},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(
            self.tmp,
            "after-dispatch",
            agent="finish-agent",
            phase="post_archive_actions",
            value=json.dumps(finish_result),
        )
        self.assertEqual(rc, 0)
        transition = json.loads(out)
        self.assertEqual(transition["workflow_command"], "workflow.py complete-phase")

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-phase",
            exit_criteria_satisfied="cleanup_complete",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("post_archive_actions", data.get("completed_phases", []))
        self.assertTrue(data["evidence"]["memory_sync_done"])
        self.assertTrue(data["evidence"]["roadmap_done_checked"])
        self.assertTrue(data["evidence"]["derived_artifacts_synced"])
        self.assertFalse(data["evidence"]["post_hook_dirty_tree"])
        self.assertTrue(data["evidence"]["cleanup_complete"])
```

- [ ] **Step 2: Run tests to verify current failure**

Run: `python3 -m pytest tests/test_workflow.py -k SubagentOwnedLifecycleCleanup -v`

Expected: at least the first two tests fail because `complete-phase archive_change` still enqueues `memory_sync`, and the post-archive evidence test fails until `post_archive_actions.evidence_keys` is added.

## Task 2: Make Workflow Definition Evidence-Driven

**Files:**
- Modify: `.ai/workflows/definitions/sdlc-main.yaml`
- Later sync: `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml` and distributed workflow definition copies if present

- [ ] **Step 1: Remove normal-path hook queues from `create_change`, `apply_change`, and `archive_change`**

Edit `.ai/workflows/definitions/sdlc-main.yaml` so these phase sections have no `post_hooks` entries. The affected sections should have this shape:

```yaml
  create_change:
    required_inputs:
      - context.change_id
    context_loaders:
      - spec_change_status
      - roadmap_linked_item
    allowed_workers:
      - dev-orchestrator
    exit_criteria:
      - spec_artifacts_done
    evidence_keys:
      - spec_artifacts_done
    next: apply_change

  apply_change:
    required_inputs:
      - context.change_id
    context_loaders:
      - spec_change_status
      - roadmap_item_status
    allowed_workers:
      - dev-orchestrator
    exit_criteria:
      - tasks_complete
      - tdd_passed
      - eval_passed_or_human_decision_recorded
    evidence_keys:
      - tasks_complete
      - tdd_passed
      - eval_passed_or_human_decision_recorded
    next: archive_change

  archive_change:
    required_inputs:
      - context.change_id
    context_loaders:
      - spec_archive_path
    allowed_workers:
      - dev-orchestrator
    exit_criteria:
      - archive_path_exists
    evidence_keys:
      - archive_path_exists
    next: post_archive_actions
```

- [ ] **Step 2: Change `post_archive_actions` to require cleanup evidence**

Replace the `post_archive_actions` section with:

```yaml
  post_archive_actions:
    required_inputs: []
    context_loaders:
      - spec_archive_path
      - roadmap_linked_item
      - roadmap_item_status
    allowed_workers:
      - dev-orchestrator
    exit_criteria:
      - cleanup_complete
    evidence_keys:
      - memory_sync_done
      - roadmap_done_checked
      - derived_artifacts_synced
      - post_hook_dirty_tree
      - cleanup_complete
    next: done
```

- [ ] **Step 3: Run focused workflow tests**

Run: `python3 -m pytest tests/test_workflow.py -k SubagentOwnedLifecycleCleanup -v`

Expected: the archive no-hook and post-archive evidence tests pass or only fail on the premature cleanup guard that is added in Task 3.

## Task 3: Reject Premature Cleanup Evidence During Archive Phase

**Files:**
- Modify: `tests/test_workflow.py`
- Modify: `.ai/workflows/scripts/workflow.py`

- [ ] **Step 1: Add failing test for premature cleanup evidence**

Append this method to `TestSubagentOwnedLifecycleCleanup`.

```python
    def test_archive_change_finish_agent_cannot_claim_cleanup_complete(self):
        self._write_archive_ready_state("premature-cleanup")
        finish_result = {
            "agent": "finish-agent",
            "status": "success",
            "phase": "archive_change",
            "slice_id": "default",
            "flow_type": "lightweight-flow",
            "evidence": {
                "archive_path_exists": True,
                "pending_hooks_empty": True,
                "cleanup_complete": True,
            },
            "artifacts": {},
            "blockers": [],
            "recommended_next_action": "complete_phase",
        }

        rc, out, _ = run_workflow(
            self.tmp,
            "after-dispatch",
            agent="finish-agent",
            phase="archive_change",
            value=json.dumps(finish_result),
        )

        self.assertEqual(rc, 0)
        transition = json.loads(out)
        self.assertEqual(transition["status"], "success")
        self.assertEqual(transition["workflow_command"], "workflow.py block")
        self.assertEqual(transition["blockers"][0]["reason"], "premature_cleanup_evidence")
        state = self._read_current_state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["block"]["type"], "worker_failed")
```

- [ ] **Step 2: Run the new test and verify failure**

Run: `python3 -m pytest tests/test_workflow.py::TestSubagentOwnedLifecycleCleanup::test_archive_change_finish_agent_cannot_claim_cleanup_complete -v`

Expected: FAIL because `after-dispatch` currently accepts `pending_hooks_empty` / `cleanup_complete` during `archive_change`.

- [ ] **Step 3: Add helper in `workflow.py`**

Add this helper near the other small dispatch helpers, before `cmd_after_dispatch`.

```python
ARCHIVE_PHASE_CLEANUP_ONLY_EVIDENCE = {
    "pending_hooks_empty",
    "cleanup_complete",
    "memory_sync_done",
    "roadmap_done_checked",
    "derived_artifacts_synced",
    "post_hook_dirty_tree",
}


def _premature_archive_cleanup_evidence(agent, phase, agent_evidence):
    if _canonical_agent_name(agent) != "finish-agent":
        return []
    if phase != "archive_change":
        return []
    if not isinstance(agent_evidence, dict):
        return []
    return sorted(
        key for key in ARCHIVE_PHASE_CLEANUP_ONLY_EVIDENCE
        if key in agent_evidence
    )
```

- [ ] **Step 4: Use helper in `cmd_after_dispatch`**

In `cmd_after_dispatch`, immediately after `agent_evidence`, `agent_blockers`, and `agent_recommended` are assigned, insert:

```python
    premature_cleanup_keys = _premature_archive_cleanup_evidence(
        canonical_agent,
        phase,
        agent_evidence,
    )
    if agent_status == "success" and premature_cleanup_keys:
        agent_blockers.append({
            "reason": "premature_cleanup_evidence",
            "message": (
                "finish-agent archive_change success claimed cleanup-only evidence "
                f"before post_archive_actions: {', '.join(premature_cleanup_keys)}"
            ),
            "recommended_action": "dispatch_finish_agent_for_post_archive_actions",
        })
```

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_workflow.py -k SubagentOwnedLifecycleCleanup -v`

Expected: PASS.

## Task 4: Preserve Legacy Hook Repair Behavior

**Files:**
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Add a legacy repair regression test**

Append this method to `TestSubagentOwnedLifecycleCleanup`.

```python
    def test_existing_pending_hooks_still_block_until_legacy_complete_hook_repairs_them(self):
        self._write_archive_ready_state("legacy-repair")
        state = self._read_current_state()
        state["current_phase"] = "post_archive_actions"
        state["completed_phases"] = ["apply_change", "archive_change", "post_archive_actions"]
        state["pending_hooks"] = ["memory_sync"]
        state["evidence"] = {
            "memory_sync_done": True,
            "roadmap_done_checked": True,
            "derived_artifacts_synced": True,
            "post_hook_dirty_tree": False,
            "cleanup_complete": True,
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["block"]["type"], "hook_blocked")

        rc, out, _ = run_workflow(
            self.tmp,
            "complete-hook",
            hook="memory_sync",
            resolution="synced",
        )
        self.assertEqual(rc, 0)
        repaired = json.loads(out)
        self.assertNotIn("memory_sync", repaired.get("pending_hooks", []))

        rc, out, _ = run_workflow(self.tmp, "advance")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "done")
```

- [ ] **Step 2: Run legacy repair focused tests**

Run: `python3 -m pytest tests/test_workflow.py -k "SubagentOwnedLifecycleCleanup or MemorySyncHook" -v`

Expected: PASS. This proves normal new runs avoid hook queues while old runs with `pending_hooks` still require explicit legacy repair.

## Task 5: Update Agent Prompt Contracts

**Files:**
- Modify: `agents/finish-agent.md`
- Modify: `agents/dev-orchestrator.md`
- Modify: `tests/test_wrapper_contracts.py`

- [ ] **Step 1: Add prompt-contract tests**

In `tests/test_wrapper_contracts.py`, near the existing finish-agent prompt tests, replace `test_finish_agent_mentions_hooks` with these tests:

```python
    def test_finish_agent_separates_archive_and_post_archive_cleanup(self):
        body = self._read_agent_body("finish-agent")
        self.assertIn("archive_change", body)
        self.assertIn("post_archive_actions", body)
        self.assertIn("memory_sync_done", body)
        self.assertIn("roadmap_done_checked", body)
        self.assertIn("derived_artifacts_synced", body)
        self.assertIn("cleanup_complete", body)
        self.assertIn("must not claim cleanup_complete during archive_change", body.lower())

    def test_dev_orchestrator_describes_subagent_owned_cleanup(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("post_archive_actions", body)
        self.assertIn("finish-agent", body)
        self.assertIn("cleanup evidence", body.lower())
        self.assertIn("legacy complete-hook", body.lower())
```

- [ ] **Step 2: Run prompt tests and verify failure**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -k "finish_agent_separates_archive or dev_orchestrator_describes_subagent_owned_cleanup" -v`

Expected: FAIL until prompt text is updated.

- [ ] **Step 3: Update `agents/finish-agent.md` archive responsibilities**

Edit `agents/finish-agent.md` so the `archive_change` section says:

```markdown
## Archive Change Responsibilities

During `archive_change`, finish-agent owns only archive/finalization work:

- verify implement-agent and review-agent evidence exists
- run provider-backed archive work for spec-flow
- finalize lightweight-flow plan/archive artifacts when applicable
- write the finish-agent handoff artifact
- return `archive_path_exists`

finish-agent must not claim cleanup_complete during archive_change. It must not
return cleanup-only evidence during archive_change, including
`pending_hooks_empty`, `cleanup_complete`, `memory_sync_done`,
`roadmap_done_checked`, `derived_artifacts_synced`, or `post_hook_dirty_tree`.
Those belong to `post_archive_actions`.
```

- [ ] **Step 4: Update `agents/finish-agent.md` post-archive responsibilities**

Add or replace the cleanup section with:

````markdown
## Post-Archive Actions Responsibilities

During `post_archive_actions`, finish-agent owns normal-flow cleanup. Runtime
`post_hooks` are legacy repair only and must not be used as the normal cleanup
source of truth.

Required cleanup work:

1. Run the pre-cleanup commit checkpoint when implementation/archive changes are
   present.
2. Run repository memory sync for lightweight-flow or OpenSpec memory sync for
   spec-flow.
3. Check roadmap completion. If `primary_subject.type == "roadmap_item"`,
   coordinate with roadmap-agent / sdlc-roadmap as required. If not, record that
   roadmap completion was checked and not required.
4. Run derived artifact sync:
   `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git`
   and, when needed,
   `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git`.
5. Commit and push generated memory, roadmap, workflow, or derived artifacts
   when generated files remain.
6. Verify the final tree is clean.

Successful post_archive_actions evidence must include:

```json
{
  "memory_sync_done": true,
  "roadmap_done_checked": true,
  "derived_artifacts_synced": true,
  "post_hook_dirty_tree": false,
  "cleanup_complete": true
}
```
````

- [ ] **Step 5: Update `agents/dev-orchestrator.md` routing guidance**

Add this routing rule near archive/post-archive dispatch guidance:

```markdown
### Subagent-Owned Cleanup

Normal `sdlc-main` cleanup is owned by subagents, not by runtime `post_hooks`.
After `archive_change` succeeds with `archive_path_exists`, complete the phase
and advance to `post_archive_actions`. Dispatch `finish-agent` in
`post_archive_actions` and use its cleanup evidence as the source of truth:
`memory_sync_done`, `roadmap_done_checked`, `derived_artifacts_synced`,
`post_hook_dirty_tree`, and `cleanup_complete`.

Use legacy complete-hook only when repairing a pre-existing run that already has
`pending_hooks`. Do not expect new normal-flow runs to enqueue `memory_sync` or
`roadmap_*` runtime hooks.
```

- [ ] **Step 6: Run prompt-contract tests**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -k "finish_agent_separates_archive or dev_orchestrator_describes_subagent_owned_cleanup" -v`

Expected: PASS.

## Task 6: Sync Workflow Templates And Distributed Artifacts

**Files:**
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml`
- Modify as generated: `.opencode/`, `.claude/`, `.cursor/` derived copies

- [ ] **Step 1: Run targeted derived-artifact check**

Run: `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git`

Expected: FAIL and list drift for workflow definitions/templates and agent copies changed in earlier tasks.

- [ ] **Step 2: Fix derived artifacts**

Run: `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git`

Expected: command exits 0 and updates only affected workflow template / distributed agent artifacts.

- [ ] **Step 3: Re-run derived-artifact check**

Run: `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git`

Expected: PASS.

## Task 7: Full Verification And Plan Checkbox Sync

**Files:**
- Modify: `docs/superpowers/plans/2026-07-05-subagent-owned-post-archive-cleanup.md`

- [ ] **Step 1: Run focused workflow regression**

Run: `python3 -m pytest tests/test_workflow.py -k "SubagentOwnedLifecycleCleanup or MemorySyncHook or PostArchiveHooks" -v`

Expected: PASS.

- [ ] **Step 2: Run workflow regression file**

Run: `python3 -m pytest tests/test_workflow.py --tb=short -q`

Expected: PASS.

- [ ] **Step 3: Run prompt-contract regression**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -v`

Expected: PASS.

- [ ] **Step 4: Run full test suite**

Run: `python3 -m pytest tests/ --tb=short -q`

Expected: PASS.

- [ ] **Step 5: Check plan checkbox sync**

Run: `python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-05-subagent-owned-post-archive-cleanup.md`

Expected: PASS after the executor has checked off all completed steps in this file.

- [ ] **Step 6: Inspect final changed files**

Run: `git status --short`

Expected: only intended workflow, agent, tests, spec/plan, template, and distributed artifact files are modified.

## Self-Review Notes

- Spec coverage: Tasks cover normal hook-free lifecycle, post-archive cleanup evidence, premature cleanup rejection, legacy repair retention, prompt contracts, template/distribution sync, and verification.
- Behavioral tests: Workflow tests invoke `workflow.py` against temporary workspaces and assert state transitions / persisted evidence rather than source string presence.
- Static tests: Prompt-contract tests intentionally use string assertions because they validate static Markdown agent contracts.
