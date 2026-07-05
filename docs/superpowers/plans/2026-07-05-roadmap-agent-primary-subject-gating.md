# Roadmap-Agent Primary Subject Gating Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` or `superpowers:subagent-driven-development`. Implement with focused TDD. Do not commit unless the user explicitly asks.

## Goal

Prevent `roadmap-agent` from being dispatched unless the active workflow run has:

```json
{
  "primary_subject": {
    "type": "roadmap_item"
  }
}
```

## Architecture

`workflow.py` remains the deterministic workflow state owner.

The implementation uses the existing `run.json.primary_subject.type` field as the single source of truth for whether roadmap-agent is enabled.

No new run.json top-level schema field is introduced.

## Task 1: Add Runtime Helper

**Files:**

- `.ai/workflows/scripts/workflow.py`
- `tests/test_workflow.py`

### Step 1.1: Add helper

In `.ai/workflows/scripts/workflow.py`, add near phase/dispatch helpers:

```python
def _roadmap_agent_enabled(state):
    return state.get("primary_subject", {}).get("type") == "roadmap_item"


def _is_roadmap_hook(hook):
    return str(hook).startswith("roadmap_")
```

## Task 2: Filter Roadmap Hooks

**Files:**

- `.ai/workflows/scripts/workflow.py`
- `tests/test_workflow.py`

### Step 2.1: Add failing test for spec_change run

Add test:

```python
def test_spec_change_run_does_not_enqueue_roadmap_hooks(self):
    ...
```

Setup:

- Start or construct a workflow run with `primary_subject.type == "spec_change"`
- Advance to a phase that normally has roadmap hooks, such as `apply_change` or `archive_change`

Expected:

```python
self.assertNotIn("roadmap_spec_link_if_ready", state["pending_hooks"])
self.assertNotIn("roadmap_apply_start_if_ready", state["pending_hooks"])
self.assertNotIn("roadmap_done_if_relevant", state["pending_hooks"])
```

For `archive_change`, also verify:

```python
self.assertIn("memory_sync", state["pending_hooks"])
```

### Step 2.2: Add failing test for roadmap_item run

Add test:

```python
def test_roadmap_item_run_can_enqueue_roadmap_hooks(self):
    ...
```

Setup:

- Start or construct a workflow run with `primary_subject.type == "roadmap_item"`
- Move through a phase with roadmap hooks

Expected:

```python
self.assertIn("roadmap_apply_start_if_ready", state["pending_hooks"])
```

or whichever roadmap hook is appropriate for the tested phase.

### Step 2.3: Implement hook filtering

Find the code that adds phase `post_hooks` into `state["pending_hooks"]`.

Change it so roadmap hooks are skipped unless `_roadmap_agent_enabled(state)` is true:

```python
for hook in phase_def.get("post_hooks", []):
    if _is_roadmap_hook(hook) and not _roadmap_agent_enabled(state):
        continue
    if hook not in state["pending_hooks"] and hook not in state["completed_hooks"]:
        state["pending_hooks"].append(hook)
```

## Task 3: Block Accidental Roadmap-Agent Dispatch

**Files:**

- `.ai/workflows/scripts/workflow.py`
- `tests/test_workflow.py`

### Step 3.1: Add failing test for blocked roadmap-agent dispatch

Add test:

```python
def test_before_dispatch_blocks_roadmap_agent_for_spec_change_run(self):
    ...
```

Setup:

- Active run has `primary_subject.type == "spec_change"`
- Call:

```bash
python3 .ai/workflows/scripts/workflow.py --root . before-dispatch --agent roadmap-agent
```

Expected:

```python
self.assertNotEqual(rc, 0)
self.assertEqual(data["status"], "blocked")
self.assertEqual(data["blockers"][0]["reason"], "roadmap_not_enabled")
```

### Step 3.2: Add allowed test for roadmap_item run

Add test:

```python
def test_before_dispatch_allows_roadmap_agent_for_roadmap_item_run(self):
    ...
```

Setup:

- Active run has `primary_subject.type == "roadmap_item"`
- Current phase allows roadmap-agent, for example `review_roadmap`

Expected:

```python
self.assertEqual(rc, 0)
self.assertEqual(data["status"], "dispatched")
```

### Step 3.3: Implement before-dispatch gate

In `cmd_before_dispatch`, after `canonical_agent` is computed and before returning success:

```python
if canonical_agent == "roadmap-agent" and not _roadmap_agent_enabled(state):
    blocker_reasons.append({
        "reason": "roadmap_not_enabled",
        "message": "roadmap-agent is disabled because primary_subject.type is not roadmap_item",
        "recommended_action": "continue the non-roadmap workflow path without dispatching roadmap-agent",
    })
```

Make sure this participates in the existing `blocker_reasons` flow instead of exiting separately.

## Task 4: Update dev-orchestrator Prompt

**Files:**

- `agents/dev-orchestrator.md`
- distributed copies if required

### Step 4.1: Update Roadmap-Governed Hook Dispatch section

Add this rule:

```md
Before dispatching `roadmap-agent`, inspect the active run state.

Dispatch `roadmap-agent` only when:

- `primary_subject.type == "roadmap_item"`

If `primary_subject.type != "roadmap_item"`, do not dispatch `roadmap-agent`, even if a roadmap hook appears in the workflow definition.
Continue with the non-roadmap lifecycle path.
```

### Step 4.2: Keep review_roadmap behavior

Add:

```md
`review_roadmap` is expected to run under `primary_subject.type == "roadmap_item"`, so roadmap-agent remains valid for roadmap review flows.
```

## Task 5: Sync Runtime and Agent Copies

If this repository distributes canonical files into `.opencode`, `.claude`, or `.cursor`, sync after tests pass.

Suggested checks:

```bash
git diff -- .ai/workflows/scripts/workflow.py
git diff -- agents/dev-orchestrator.md
```

If a sync script exists, run it. Otherwise manually sync equivalent changes to distributed copies.

## Task 6: Verification

Run focused tests:

```bash
python3 -m pytest tests/test_workflow.py -k "roadmap_agent or roadmap_hook or roadmap" -v
```

Run workflow tests:

```bash
python3 -m pytest tests/test_workflow.py -v
```

Run contract tests if prompt assertions changed:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
```

Run full suite if feasible:

```bash
python3 -m pytest tests/ -v
```

## Done Criteria

- `spec_change` runs no longer enqueue roadmap hooks
- `spec_change` runs cannot dispatch roadmap-agent
- `roadmap_item` runs can still dispatch roadmap-agent
- `review_roadmap` remains functional
- `memory_sync` still runs for non-roadmap flows
- Tests pass
