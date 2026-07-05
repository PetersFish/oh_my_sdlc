# Roadmap-Agent Primary Subject Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not commit unless the user explicitly asks.

**Goal:** Prevent `roadmap-agent` from being dispatched unless the active workflow run has `primary_subject.type == "roadmap_item"`.

**Architecture:** `workflow.py` remains the deterministic workflow state owner. The implementation uses the existing `run.json.primary_subject.type` field as the single source of truth for whether roadmap-agent is enabled. No new run.json top-level schema field is introduced.

**Tech Stack:** Python workflow runtime, YAML workflow definitions, Markdown agent prompts, pytest/unittest tests, project agent/skill distribution scripts.

**Repository Policy Note:** Do not commit during this plan unless the user explicitly asks. Use `git status`/`git diff` checkpoints instead of commit steps.

---

## File Structure

- `.ai/workflows/scripts/workflow.py`: Runtime phase helpers, hook filtering, and before-dispatch routing gate.
- `tests/test_workflow.py`: Behavior tests for roadmap hook filtering and roadmap-agent dispatch gating.
- `agents/dev-orchestrator.md`: Canonical primary agent prompt; document primary-subject based roadmap-agent routing.
- Distributed copies under `.opencode/`, `.claude/`, `.cursor/`: Sync if this repository requires generated agent/runtime copies.

---

## Task 1: Add Runtime Helper

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `tests/test_workflow.py`

- [ ] **Step 1.1: Add `_roadmap_agent_enabled` and `_is_roadmap_hook` helpers**

  In `.ai/workflows/scripts/workflow.py`, add near phase/dispatch helpers:

  ```python
  def _roadmap_agent_enabled(state):
      return state.get("primary_subject", {}).get("type") == "roadmap_item"


  def _is_roadmap_hook(hook):
      return str(hook).startswith("roadmap_")
  ```

  Keep the rule intentionally simple: only `roadmap_item` primary runs enable roadmap-agent.

---

## Task 2: Filter Roadmap Hooks

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `tests/test_workflow.py`

- [ ] **Step 2.1: Add failing test for `spec_change` run hook filtering**

  Add a test such as:

  ```python
  def test_spec_change_run_does_not_enqueue_roadmap_hooks(self):
      ...
  ```

  Setup:
  - Start or construct a workflow run with `primary_subject.type == "spec_change"`.
  - Advance to a phase that normally has roadmap hooks, such as `apply_change` or `archive_change`.

  Expected assertions:

  ```python
  self.assertNotIn("roadmap_spec_link_if_ready", state["pending_hooks"])
  self.assertNotIn("roadmap_apply_start_if_ready", state["pending_hooks"])
  self.assertNotIn("roadmap_done_if_relevant", state["pending_hooks"])
  ```

  For `archive_change`, also verify non-roadmap hooks still work:

  ```python
  self.assertIn("memory_sync", state["pending_hooks"])
  ```

- [ ] **Step 2.2: Add failing test for `roadmap_item` run hook preservation**

  Add a test such as:

  ```python
  def test_roadmap_item_run_can_enqueue_roadmap_hooks(self):
      ...
  ```

  Setup:
  - Start or construct a workflow run with `primary_subject.type == "roadmap_item"`.
  - Move through a phase with roadmap hooks.

  Expected assertion:

  ```python
  self.assertIn("roadmap_apply_start_if_ready", state["pending_hooks"])
  ```

  Use the roadmap hook appropriate for the tested phase if the fixture reaches a different phase.

- [ ] **Step 2.3: Implement post-hook filtering**

  Find the code that adds phase `post_hooks` into `state["pending_hooks"]`.

  Change it so roadmap hooks are skipped unless `_roadmap_agent_enabled(state)` is true:

  ```python
  for hook in phase_def.get("post_hooks", []):
      if _is_roadmap_hook(hook) and not _roadmap_agent_enabled(state):
          continue
      if hook not in state["pending_hooks"] and hook not in state["completed_hooks"]:
          state["pending_hooks"].append(hook)
  ```

- [ ] **Step 2.4: Run focused hook filtering tests**

  Run:

  ```bash
  python3 -m pytest tests/test_workflow.py -k "roadmap_hook or roadmap" -v
  ```

  Expected: new hook filtering tests pass after implementation.

---

## Task 3: Block Accidental Roadmap-Agent Dispatch

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `tests/test_workflow.py`

- [ ] **Step 3.1: Add failing test for blocked roadmap-agent dispatch on `spec_change` run**

  Add a test such as:

  ```python
  def test_before_dispatch_blocks_roadmap_agent_for_spec_change_run(self):
      ...
  ```

  Setup:
  - Active run has `primary_subject.type == "spec_change"`.
  - Call:

  ```bash
  python3 .ai/workflows/scripts/workflow.py --root . before-dispatch --agent roadmap-agent
  ```

  Expected assertions:

  ```python
  self.assertNotEqual(rc, 0)
  self.assertEqual(data["status"], "blocked")
  self.assertEqual(data["blockers"][0]["reason"], "roadmap_not_enabled")
  ```

- [ ] **Step 3.2: Add allowed dispatch test for `roadmap_item` run**

  Add a test such as:

  ```python
  def test_before_dispatch_allows_roadmap_agent_for_roadmap_item_run(self):
      ...
  ```

  Setup:
  - Active run has `primary_subject.type == "roadmap_item"`.
  - Current phase allows roadmap-agent, for example `review_roadmap`.

  Expected assertions:

  ```python
  self.assertEqual(rc, 0)
  self.assertEqual(data["status"], "dispatched")
  ```

- [ ] **Step 3.3: Implement `cmd_before_dispatch` roadmap-agent gate**

  In `cmd_before_dispatch`, after `canonical_agent` is computed and before returning success, add:

  ```python
  if canonical_agent == "roadmap-agent" and not _roadmap_agent_enabled(state):
      blocker_reasons.append({
          "reason": "roadmap_not_enabled",
          "message": "roadmap-agent is disabled because primary_subject.type is not roadmap_item",
          "recommended_action": "continue the non-roadmap workflow path without dispatching roadmap-agent",
      })
  ```

  Make sure this participates in the existing `blocker_reasons` flow instead of exiting separately.

- [ ] **Step 3.4: Run focused dispatch gate tests**

  Run:

  ```bash
  python3 -m pytest tests/test_workflow.py -k "roadmap_agent or before_dispatch" -v
  ```

  Expected: roadmap-agent is blocked for `spec_change` runs and allowed for valid `roadmap_item` runs.

---

## Task 4: Update dev-orchestrator Prompt

**Files:**
- Modify: `agents/dev-orchestrator.md`
- Modify: distributed copies if required

- [ ] **Step 4.1: Update Roadmap-Governed Hook Dispatch section**

  Add this rule to `agents/dev-orchestrator.md`:

  ```md
  Before dispatching `roadmap-agent`, inspect the active run state.

  Dispatch `roadmap-agent` only when:

  - `primary_subject.type == "roadmap_item"`

  If `primary_subject.type != "roadmap_item"`, do not dispatch `roadmap-agent`, even if a roadmap hook appears in the workflow definition.
  Continue with the non-roadmap lifecycle path.
  ```

- [ ] **Step 4.2: Preserve `review_roadmap` behavior**

  Add this clarification:

  ```md
  `review_roadmap` is expected to run under `primary_subject.type == "roadmap_item"`, so roadmap-agent remains valid for roadmap review flows.
  ```

- [ ] **Step 4.3: Add or update static prompt contract test if applicable**

  If `tests/test_wrapper_contracts.py` already checks dev-orchestrator prompt routing contracts, add assertions that the canonical prompt mentions:
  - `primary_subject.type == "roadmap_item"`
  - `roadmap-agent`
  - `review_roadmap`

---

## Task 5: Sync Runtime and Agent Copies

**Files:**
- Modify: distributed runtime and agent copies if the repository requires them

- [ ] **Step 5.1: Inspect changed canonical files**

  Run:

  ```bash
  git diff -- .ai/workflows/scripts/workflow.py
  git diff -- agents/dev-orchestrator.md
  ```

- [ ] **Step 5.2: Sync distributed copies**

  If this repository distributes canonical files into `.opencode`, `.claude`, or `.cursor`, sync after tests pass.

  Use the project sync script if available. Otherwise manually sync equivalent changes to distributed copies.

- [ ] **Step 5.3: Inspect distribution diff**

  Run:

  ```bash
  git diff -- .opencode .claude .cursor skills/sdlc-project-bootstrap/templates
  ```

  Confirm only intended runtime/prompt/template copies changed.

---

## Task 6: Verification

**Files:**
- Verify: workflow runtime, prompt contract, distributed copies

- [ ] **Step 6.1: Run focused roadmap tests**

  Run:

  ```bash
  python3 -m pytest tests/test_workflow.py -k "roadmap_agent or roadmap_hook or roadmap" -v
  ```

- [ ] **Step 6.2: Run workflow tests**

  Run:

  ```bash
  python3 -m pytest tests/test_workflow.py -v
  ```

- [ ] **Step 6.3: Run contract tests if prompt assertions changed**

  Run:

  ```bash
  python3 -m pytest tests/test_wrapper_contracts.py -v
  ```

- [ ] **Step 6.4: Run full suite if feasible**

  Run:

  ```bash
  python3 -m pytest tests/ -v
  ```

- [ ] **Step 6.5: Confirm done criteria**

  Verify:
  - `spec_change` runs no longer enqueue roadmap hooks.
  - `spec_change` runs cannot dispatch roadmap-agent.
  - `roadmap_item` runs can still dispatch roadmap-agent.
  - `review_roadmap` remains functional.
  - `memory_sync` still runs for non-roadmap flows.
  - Tests pass.
