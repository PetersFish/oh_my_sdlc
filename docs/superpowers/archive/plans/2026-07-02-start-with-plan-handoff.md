# Start-With-Plan Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow `dev-orchestrator` to implement an existing OpenSpec or Superpowers plan by starting/resuming a governed workflow at the correct phase and dispatching `implement-agent` without rerunning `plan-agent`.

**Architecture:** Keep workflow runtime as the owner of phase state by passing `flow_type` into `_infer_phase`. `spec-flow` keeps OpenSpec artifact inference; `lightweight-flow` adds deterministic Superpowers plan matching. `dev-orchestrator` only collects `flow_type` and `primary_design_path`, derives `subject_id`, and dispatches the normal lifecycle agents.

**Tech Stack:** Python workflow runtime and tests, Markdown agent prompt contracts, agent distribution scripts, template sync scripts.

---

## File Structure

| Action | File | Responsibility |
|---|---|---|
| Modify | `.ai/workflows/scripts/workflow.py` | Flow-type-aware phase inference and Superpowers plan matching |
| Modify | `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` | Keep bootstrap workflow template synced with runtime |
| Modify | `tests/test_workflow.py` | Executable runtime coverage for phase inference |
| Modify | `agents/dev-orchestrator.md` | Start-with-plan handoff routing rules |
| Modify | `tests/test_wrapper_contracts.py` | Agent prompt contract assertions for canonical and distributed agents |
| Optional Modify | `tests/test_sdlc_orchestrator.py` | Static route behavior assertions if the legacy skill needs documentation updates |
| Generated | `.opencode/agents/dev-orchestrator.md`, `.claude/agents/dev-orchestrator.md`, `.cursor/agents/dev-orchestrator.md` | Distributed copies from canonical agent prompt |

Do not hand-edit distributed agent copies. Modify `agents/dev-orchestrator.md`, then run the agent setup scripts.

---

### Task 1: Add Runtime Tests For Flow-Type Phase Inference

**Files:**
- Modify: `tests/test_workflow.py`
- Modify later: `.ai/workflows/scripts/workflow.py`

**Context:** These are executable behavior tests. They must invoke `workflow.py start` and assert observable workflow state, not only check prompt strings.

- [ ] **Step 1: Add a helper for Superpowers plan files**

In `tests/test_workflow.py`, add this helper to `FixtureBase` near the existing OpenSpec helpers:

```python
    def _make_superpowers_plan(self, filename, content="# Plan\n"):
        plans_dir = os.path.join(self.tmp, "docs", "superpowers", "plans")
        os.makedirs(plans_dir, exist_ok=True)
        path = os.path.join(plans_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
```

- [ ] **Step 2: Add a failing test for lightweight-flow apply inference**

Append this test to `TestPhaseInference`:

```python
    def test_lightweight_flow_with_matching_superpowers_plan_starts_at_apply_change(self):
        self._make_superpowers_plan("2026-07-02-start-with-plan-handoff.md")

        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="spec_change",
            subject_id="start-with-plan-handoff",
            flow_type="lightweight-flow",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["flow_type"], "lightweight-flow")
        self.assertEqual(data["current_phase"], "apply_change")
```

- [ ] **Step 3: Add a failing test for no matching lightweight plan**

Append this test to `TestPhaseInference`:

```python
    def test_lightweight_flow_without_matching_superpowers_plan_starts_at_create_change(self):
        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="spec_change",
            subject_id="missing-plan",
            flow_type="lightweight-flow",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["flow_type"], "lightweight-flow")
        self.assertEqual(data["current_phase"], "create_change")
```

- [ ] **Step 4: Add a failing test for ambiguous lightweight plan matches**

Append this test to `TestPhaseInference`:

```python
    def test_lightweight_flow_with_multiple_matching_superpowers_plans_does_not_guess(self):
        self._make_superpowers_plan("2026-07-02-start-with-plan-handoff.md")
        self._make_superpowers_plan("2026-07-03-start-with-plan-handoff-revision.md")

        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="spec_change",
            subject_id="start-with-plan-handoff",
            flow_type="lightweight-flow",
        )

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["current_phase"], "create_change")
```

- [ ] **Step 5: Confirm existing spec-flow behavior remains covered**

Keep the existing `TestPhaseInference.test_in_progress_change_starts_at_apply_change` unchanged. It proves `spec-flow` still enters `apply_change` from OpenSpec `tasks.md`.

- [ ] **Step 6: Run tests to verify the new lightweight-flow tests fail**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestPhaseInference -v
```

Expected: the new lightweight-flow matching test fails because `_infer_phase` does not yet inspect `docs/superpowers/plans/`.

---

### Task 2: Implement Flow-Type-Aware Phase Inference

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Test: `tests/test_workflow.py::TestPhaseInference`

**Context:** Do not add `--initial-phase`. The runtime should infer phase deterministically from `flow_type` and repository artifacts.

- [ ] **Step 1: Change `cmd_start` to compute `flow_type` before phase**

In `.ai/workflows/scripts/workflow.py`, replace the current ordering in `cmd_start`:

```python
    phase = _infer_phase(root, subject_type, subject_id)
    flow_type = args.flow_type or "spec-flow"
```

with:

```python
    flow_type = args.flow_type or "spec-flow"
    phase = _infer_phase(root, subject_type, subject_id, flow_type)
```

- [ ] **Step 2: Add helper to normalize dated plan stems**

Add this helper near `_infer_phase`:

```python
def _strip_leading_date_slug(stem):
    parts = stem.split("-", 3)
    if len(parts) == 4 and all(part.isdigit() for part in parts[:3]):
        return parts[3]
    return stem
```

- [ ] **Step 3: Add helper to find matching Superpowers plans**

Add this helper near `_strip_leading_date_slug`:

```python
def _matching_superpowers_plans(root, subject_id):
    plans_dir = root / "docs" / "superpowers" / "plans"
    if not plans_dir.is_dir():
        return []
    matches = []
    for path in sorted(plans_dir.glob("*.md")):
        stem = path.stem
        normalized = _strip_leading_date_slug(stem)
        if normalized == subject_id or subject_id in normalized:
            matches.append(path)
    return matches
```

- [ ] **Step 4: Change `_infer_phase` signature and add lightweight-flow branch**

Replace:

```python
def _infer_phase(root, subject_type, subject_id):
```

with:

```python
def _infer_phase(root, subject_type, subject_id, flow_type="spec-flow"):
```

Then in the `subject_type == "spec_change"` section, add the lightweight branch before OpenSpec status classification:

```python
    if flow_type == "lightweight-flow":
        matches = _matching_superpowers_plans(root, subject_id)
        if len(matches) == 1:
            return "apply_change"
        return "create_change"
```

Keep the existing OpenSpec classification logic for `spec-flow`.

- [ ] **Step 5: Run focused runtime tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestPhaseInference -v
```

Expected: PASS.

---

### Task 3: Sync Workflow Template

**Files:**
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Test: template sync check

**Context:** Repository instructions require `.ai/workflows/scripts/workflow.py` and bootstrap workflow templates to stay synchronized.

- [ ] **Step 1: Run the template sync command**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
```

Expected: the command updates `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` to match the live workflow runtime.

- [ ] **Step 2: Verify no workflow template drift remains**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
```

Expected: PASS with no drift reported.

---

### Task 4: Add Dev-Orchestrator Handoff Prompt Contract Tests

**Files:**
- Modify: `tests/test_wrapper_contracts.py`
- Modify later: `agents/dev-orchestrator.md`

**Context:** These tests are prompt contract tests because the behavior lives in the agent instructions. Runtime behavior is already covered in `tests/test_workflow.py`.

- [ ] **Step 1: Add tests for start-with-plan terminology**

Add this class near other dev-orchestrator prompt tests:

```python
class TestDevOrchestratorStartWithPlanHandoff(unittest.TestCase):
    """dev-orchestrator documents governed implementation from existing design artifacts."""

    def test_documents_start_with_plan_handoff_inputs(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("start-with-plan", content)
        self.assertIn("flow_type", content)
        self.assertIn("primary_design_path", content)
        self.assertIn("design_artifact_paths", content)

    def test_documents_four_handoff_input_cases(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("Provides both `flow_type` and `primary_design_path`", content)
        self.assertIn("Provides only `flow_type`", content)
        self.assertIn("Provides only `primary_design_path`", content)
        self.assertIn("Provides neither", content)

    def test_start_with_plan_is_governed_not_direct_execution(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("not `superpowers-direct`", content)
        self.assertIn("before-dispatch", content)
        self.assertIn("implement-agent", content)
        self.assertIn("skip `plan-agent`", content)
```

- [ ] **Step 2: Run tests to verify they fail before prompt update**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py::TestDevOrchestratorStartWithPlanHandoff -v
```

Expected: FAIL because `dev-orchestrator.md` does not yet document start-with-plan handoff.

---

### Task 5: Update Canonical Dev-Orchestrator Prompt

**Files:**
- Modify: `agents/dev-orchestrator.md`
- Test: `tests/test_wrapper_contracts.py::TestDevOrchestratorStartWithPlanHandoff`

**Context:** Keep `dev-orchestrator` within routing boundaries. It may collect routing inputs and list candidate design artifacts, but it must not redesign the solution or execute implementation itself.

- [ ] **Step 1: Add start-with-plan to allowed responsibilities**

In `agents/dev-orchestrator.md`, update the responsibilities list to include collecting existing design artifact handoff inputs:

```markdown
- collecting `flow_type` and `primary_design_path` for start-with-plan handoff requests
```

- [ ] **Step 2: Add a Start-With-Plan Handoff section**

Insert this section after `Workflow Entry First` and before `Dispatch Lifecycle Hooks`:

```markdown
## Start-With-Plan Handoff

Use this branch when the user asks to implement an existing design, plan, or OpenSpec change instead of creating a new plan.

This branch is governed workflow execution, not `superpowers-direct`. It MUST still use workflow start/resume, `before-dispatch`, `implement-agent`, `test-agent`, and `review-agent`. It only skips `plan-agent` after existing design artifacts are selected.

Required routing inputs:
- `flow_type`: `spec-flow` or `lightweight-flow`
- `primary_design_path`: the selected main design artifact

Forward related artifacts through `design_artifact_paths[]`.

Input cases:

| User input | Action |
|---|---|
| Provides both `flow_type` and `primary_design_path` | Validate that the path belongs to the flow, derive `subject_id`, then start/resume and dispatch implementation. |
| Provides only `flow_type` | List apply-ready candidates for that flow and ask the user to select `primary_design_path`. |
| Provides only `primary_design_path` | Infer `flow_type` by path rules; ask if ambiguous. |
| Provides neither | Ask for `flow_type` first, then list candidates for that flow. |

Path rules:
- `openspec/changes/<change-id>/...` -> `spec-flow`
- `docs/superpowers/plans/...` -> `lightweight-flow`
- `docs/superpowers/specs/...` -> `lightweight-flow`, but a related `kind=plan` artifact must be found or selected before implementation

Candidate rules:
- `spec-flow`: list OpenSpec changes with apply-ready `tasks.md` artifacts.
- `lightweight-flow`: list `docs/superpowers/plans/*.md` candidates.

After inputs are resolved:
1. Run `verify-foundations`.
2. Run `status` for the derived subject.
3. Start or resume the workflow with the selected `flow_type`.
4. Confirm the active phase is `apply_change`.
5. Call `before-dispatch --agent implement-agent`.
6. Dispatch `implement-agent` with `primary_design_path` and `design_artifact_paths[]` in the task prompt.

If the active phase is `create_change`, do not force implementation. Surface the missing or ambiguous artifact selection and ask the user to choose a valid existing plan, or route to `plan-agent` only if the user wants new planning.
```

- [ ] **Step 3: Add explicit workflow run initialization commands**

In the same `Start-With-Plan Handoff` section, add this subsection after the path rules:

```markdown
### Workflow Run Initialization

After `flow_type` and `primary_design_path` are resolved, derive the workflow subject from the selected artifact:

| Flow | Path | subject_type | subject_id |
|---|---|---|---|
| `spec-flow` | `openspec/changes/<change-id>/...` | `spec_change` | `<change-id>` |
| `lightweight-flow` | `docs/superpowers/plans/YYYY-MM-DD-<slug>.md` | `spec_change` | `<slug>` |

For dated Superpowers plan filenames, strip the leading `YYYY-MM-DD-` prefix when deriving `<slug>`.

Run workflow entry commands in this order:

1. `python3 .ai/workflows/scripts/workflow.py --root . verify-foundations`
2. `python3 .ai/workflows/scripts/workflow.py --root . status --subject-type <subject_type> --subject-id <subject_id>`
3. If no matching active run exists: `python3 .ai/workflows/scripts/workflow.py --root . start --workflow sdlc-main --subject-type <subject_type> --subject-id <subject_id> --flow-type <flow_type>`
4. If a matching active run exists: `python3 .ai/workflows/scripts/workflow.py --root . resume --subject-type <subject_type> --subject-id <subject_id>`
5. Continue only if the active phase is `apply_change`; otherwise surface the missing or ambiguous artifact selection.
```

- [ ] **Step 4: Run prompt contract tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py::TestDevOrchestratorStartWithPlanHandoff -v
```

Expected: PASS.

---

### Task 6: Distribute Agent Prompt Updates

**Files:**
- Generated: `.opencode/agents/dev-orchestrator.md`
- Generated: `.claude/agents/dev-orchestrator.md`
- Generated: `.cursor/agents/dev-orchestrator.md`
- Test: distributed copy checks

**Context:** Agent files under `agents/` are canonical. Distributed copies must be generated by setup scripts, not edited by hand.

- [ ] **Step 1: Run project-level agent setup for all targets**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
```

Expected: all three commands complete successfully and activate model/variant frontmatter.

- [ ] **Step 2: Verify opencode distributed agent consistency**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --check
```

Expected: PASS with no drift.

- [ ] **Step 3: Run wrapper contract tests for agent distribution**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
```

Expected: PASS.

---

### Task 7: Run Focused And Regression Verification

**Files:**
- Test only

**Context:** Before reporting completion, verify both runtime behavior and prompt/distribution contracts.

- [ ] **Step 1: Run focused workflow tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestPhaseInference tests/test_workflow.py::TestFlowType tests/test_workflow.py::TestDispatchHooks -v
```

Expected: PASS.

- [ ] **Step 2: Run prompt and wrapper contract tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py tests/test_sdlc_orchestrator.py -v
```

Expected: PASS.

- [ ] **Step 3: Run workflow template drift check**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
```

Expected: PASS.

- [ ] **Step 4: Run full test suite if time allows**

Run:

```bash
python3 -m pytest tests/ -v
```

Expected: PASS.

---

## Self-Review Checklist

- [ ] No `--initial-phase` API was added.
- [ ] `_infer_phase` receives `flow_type` and owns phase selection.
- [ ] `spec-flow` behavior remains unchanged for existing OpenSpec changes.
- [ ] `lightweight-flow` only enters `apply_change` when exactly one matching Superpowers plan exists.
- [ ] `dev-orchestrator` uses `primary_design_path`, not `plan_path`.
- [ ] Start-with-plan is documented as governed workflow execution, not `superpowers-direct`.
- [ ] Distributed agent files are generated by setup scripts, not hand-edited.
- [ ] Workflow runtime template is synced.
