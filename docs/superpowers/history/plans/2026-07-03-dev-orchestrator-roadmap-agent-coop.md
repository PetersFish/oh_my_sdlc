# Dev-Orchestrator Roadmap-Agent Cooperation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route roadmap item review through `roadmap-agent`, redefine `ready` as review-passed, and hide OpenSpec-specific runtime vocabulary behind provider-agnostic `spec_*` names.

**Architecture:** `workflow.py` remains the deterministic state owner. `dev-orchestrator` routes `review_roadmap` to `roadmap-agent`; `roadmap-agent` performs review and marks roadmap items `ready` without creating spec artifacts; `plan-agent` creates spec artifacts later only after user confirmation. Runtime hooks validate/link `spec_change` rather than promoting roadmap status.

**Tech Stack:** Python workflow runtime, YAML workflow definitions, Markdown agent/skill prompts, pytest/unittest tests, project agent/skill distribution scripts.

**Repository Policy Note:** Do not commit during this plan unless the user explicitly asks. Use `git status`/`git diff` checkpoints instead of commit steps.

---

## File Structure

- `.ai/workflows/scripts/workflow.py`: Runtime policies, loaders, hook completion, phase inference, and provider-agnostic aliases.
- `.ai/workflows/definitions/sdlc-main.yaml`: Live workflow phase worker and hook configuration.
- `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml`: Canonical workflow template that must stay synced with the live workflow definition.
- `agents/dev-orchestrator.md`: Canonical primary agent prompt; add `review_roadmap` dispatch rules and update roadmap hook names.
- `agents/roadmap-agent.md`: Canonical roadmap subagent prompt; add review contract and update hook contract names.
- `skills/sdlc-roadmap/SKILL.md`: Canonical roadmap skill contract; update `ready` semantics and `spec_change` field docs.
- `skills/sdlc-roadmap/templates/item.md`: Roadmap item template; rename `openspec_change` to `spec_change` if present.
- `skills/_lib/wrapper_contracts.py`: Add `review_roadmap` to phase-agent mapping so contract validation allows `roadmap-agent` in the review phase.
- `tests/test_workflow.py`: Behavior tests for phase routing, spec aliases, hook semantics, and `ready + spec_change` phase inference.
- `tests/test_wrapper_contracts.py`: Prompt/static contract tests for roadmap-agent review contract and phase-agent mapping.
- Distributed copies under `.opencode/`, `.claude/`, `.cursor/`: generated from canonical agents/skills/templates after implementation.

---

### Task 1: Runtime Naming And Link Loader Compatibility

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Add failing behavior tests for `spec_change` roadmap frontmatter**

Add tests near the existing canonical-run promotion tests in `tests/test_workflow.py`:

```python
    def test_preflight_spec_create_finds_linked_roadmap_run_by_spec_change_frontmatter(self):
        self._make_roadmap_item("RM-PROMO-SPEC", "ready", spec_change="promo-spec")
        run_workflow(
            self.tmp,
            "start",
            subject_type="roadmap_item",
            subject_id="RM-PROMO-SPEC",
        )
        active_runs = self._list_active_runs_support()
        for _run_id, state in active_runs:
            if "RM-PROMO-SPEC" in _run_id:
                state["current_phase"] = "create_change"
                active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", _run_id)
                os.makedirs(active_dir, exist_ok=True)
                with open(os.path.join(active_dir, "run.json"), "w") as f:
                    json.dump(state, f)
                break

        rc, data, _ = self._run_preflight(
            "spec_create",
            subject_type="spec_change",
            subject_id="promo-spec",
        )

        self.assertEqual(rc, 0)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["reason"], "linked_roadmap_run_exists")

    def test_start_ready_roadmap_without_spec_change_starts_review_phase(self):
        self._make_roadmap_item("RM-READY-NOSPEC", "ready")

        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="roadmap_item",
            subject_id="RM-READY-NOSPEC",
        )

        self.assertEqual(rc, 0)
        state = json.loads(out)
        self.assertEqual(state["current_phase"], "review_roadmap")

    def test_start_ready_roadmap_with_spec_change_starts_create_change_phase(self):
        self._make_roadmap_item("RM-READY-SPEC", "ready", spec_change="ready-spec-change")

        rc, out, _ = run_workflow(
            self.tmp,
            "start",
            subject_type="roadmap_item",
            subject_id="RM-READY-SPEC",
        )

        self.assertEqual(rc, 0)
        state = json.loads(out)
        self.assertEqual(state["current_phase"], "create_change")
```

Also update `FixtureBase._make_roadmap_item` to accept both current and new names for the red phase:

```python
    def _make_roadmap_item(self, item_id, status, openspec_change=None, spec_change=None, area="area1", completed_at=None, started_at=None, slug=None):
        items_dir = os.path.join(
            self.tmp, ".ai", "roadmap", "areas", area, "items"
        )
        os.makedirs(items_dir, exist_ok=True)
        fm = f"id: {item_id}\nstatus: {status}\n"
        if spec_change:
            fm += f"spec_change: {spec_change}\n"
        if openspec_change:
            fm += f"openspec_change: {openspec_change}\n"
        if completed_at:
            fm += f"completed_at: {completed_at}\n"
        if started_at:
            fm += f"started_at: {started_at}\n"
        content = f"---\n{fm}---\n# {item_id}\n"
        fname = f"{item_id}-{slug}.md" if slug else f"{item_id}.md"
        fpath = os.path.join(items_dir, fname)
        with open(fpath, "w") as f:
            f.write(content)
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestPreflightEnsureRun -k "spec_change_frontmatter or ready_roadmap" -v
```

Expected: FAIL because `spec_create` is not registered and `_read_roadmap_item_openspec_change()` does not read `spec_change`.

- [ ] **Step 3: Add provider-agnostic runtime helpers and policy aliases**

In `.ai/workflows/scripts/workflow.py`, add provider-agnostic aliases while preserving OpenSpec backend helpers internally:

```python
def loader_spec_change_status(root, change_id):
    return loader_openspec_change_status(root, change_id)


def loader_spec_archive_path(root, change_id):
    return loader_openspec_archive_path(root, change_id)


def _read_roadmap_item_spec_change(root, item_id):
    """Read provider-agnostic spec_change from a roadmap item file."""
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    for area in _list_dirs(areas_dir):
        items_dir = os.path.join(areas_dir, area, "items")
        if not os.path.isdir(items_dir):
            continue
        for fname in _list_dirs(items_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(items_dir, fname)
            fm_id = _read_frontmatter_field(fpath, "id")
            if fm_id == item_id:
                return _read_frontmatter_field(fpath, "spec_change")
    return None
```

Then update `_find_linked_roadmap_run`, `_infer_phase`, and done-hook lookup to call `_read_roadmap_item_spec_change()` instead of `_read_roadmap_item_openspec_change()`.

Register new action aliases without removing old backend aliases yet:

```python
@register_policy(
    "spec_create", allowed_phases={"create_change", "input"},
)
@register_policy(
    "spec_continue", allowed_phases={"create_change", "apply_change"},
)
@register_policy(
    "spec_apply", allowed_phases={"apply_change"},
)
@register_policy(
    "spec_archive", allowed_phases={"archive_change"},
)
@register_policy(
    "openspec_create", allowed_phases={"create_change", "input"},
)
@register_policy(
    "openspec_continue", allowed_phases={"create_change", "apply_change"},
)
@register_policy(
    "openspec_apply", allowed_phases={"apply_change"},
)
@register_policy(
    "openspec_archive", allowed_phases={"archive_change"},
)
def _policy_spec_change(root, action, subject_type, subject_id):
    ...
```

Keep the function body from current `_policy_openspec_change`; rename local comments and messages from `openspec` to `spec` where they are user-facing.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestPreflightEnsureRun -k "spec_change_frontmatter or ready_roadmap" -v
```

Expected: PASS.

---

### Task 2: Workflow Phase And Hook Contract Changes

**Files:**
- Modify: `.ai/workflows/definitions/sdlc-main.yaml`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml`
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Add failing tests for review routing and renamed hook**

In `TestWorkflowDefinitionContracts`, add:

```python
    def test_review_roadmap_routes_through_dev_orchestrator(self):
        wf = load_yaml(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml")
        review_roadmap = wf["phases"]["review_roadmap"]

        self.assertEqual(review_roadmap.get("allowed_workers"), ["dev-orchestrator"])
        self.assertEqual(review_roadmap.get("exit_criteria"), ["review_decision_recorded"])

    def test_create_change_uses_spec_link_hook(self):
        wf = load_yaml(self.tmp, ".ai/workflows/definitions/sdlc-main.yaml")
        create_change = wf["phases"]["create_change"]

        self.assertIn("roadmap_spec_link_if_ready", create_change.get("post_hooks", []))
        self.assertNotIn("roadmap_status_ready_if_linked", create_change.get("post_hooks", []))
```

Add hook behavior tests near existing `complete-hook` tests:

```python
    def test_complete_hook_spec_link_blocks_when_item_not_ready(self):
        self._make_roadmap_item("RM-LINK-IDEA", "idea", spec_change="link-change")
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="link-change")
        state = self._read_current_state()
        state["pending_hooks"] = ["roadmap_spec_link_if_ready"]
        state["evidence"]["roadmap_link"] = {
            "count": 1,
            "items": [{"item_id": "RM-LINK-IDEA", "status": "idea"}],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "complete-hook", hook="roadmap_spec_link_if_ready")

        self.assertNotEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["block"]["type"], "domain_state_mismatch")
        self.assertIn("expected ready", data["block"]["message"])

    def test_complete_hook_spec_link_succeeds_for_ready_item(self):
        self._make_roadmap_item("RM-LINK-READY", "ready", spec_change="link-ready")
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="link-ready")
        state = self._read_current_state()
        state["pending_hooks"] = ["roadmap_spec_link_if_ready"]
        state["evidence"]["roadmap_link"] = {
            "count": 1,
            "items": [{"item_id": "RM-LINK-READY", "status": "ready"}],
        }
        self._write_current_state(state)

        rc, out, _ = run_workflow(self.tmp, "complete-hook", hook="roadmap_spec_link_if_ready")

        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("roadmap_spec_link_if_ready", data.get("completed_hooks", []))
        self.assertEqual(data["evidence"].get("roadmap_hook_resolution"), "spec_linked")
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestWorkflowDefinitionContracts tests/test_workflow.py -k "spec_link" -v
```

Expected: FAIL because workflow YAML and hook name still use `roadmap_status_ready_if_linked`.

- [ ] **Step 3: Update workflow YAML files**

In both `.ai/workflows/definitions/sdlc-main.yaml` and `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml`:

```yaml
  review_roadmap:
    required_inputs: []
    context_loaders: []
    allowed_workers:
      - dev-orchestrator
    exit_criteria:
      - review_decision_recorded
    post_hooks: []
    next: review_decision
```

Change create-change loaders/hooks:

```yaml
    context_loaders:
      - spec_change_status
      - roadmap_linked_item
...
    post_hooks:
      - roadmap_spec_link_if_ready
```

Change archive loader:

```yaml
    context_loaders:
      - spec_archive_path
```

- [ ] **Step 4: Update `complete-hook` runtime branch**

In `cmd_complete_hook`, replace the `roadmap_status_ready_if_linked` branch with:

```python
    elif hook_name == "roadmap_spec_link_if_ready":
        items, count = _resolve_roadmap_hook_linked_items(state)
        if count == 0:
            state.setdefault("evidence", {})["roadmap_hook_resolution"] = "no_linked_item"
        elif count == 1:
            item = items[0]
            item_id = item.get("item_id")
            current = loader_roadmap_item_status(root, item_id)
            if current and current.get("status") == "ready":
                state.setdefault("evidence", {})["roadmap_hook_resolution"] = "spec_linked"
            else:
                observed_status = current.get("status") if current else item.get("status", "unknown")
                _apply_roadmap_hook_block(
                    state, hook_name, "domain_state_mismatch",
                    f"roadmap item {item_id} has status {observed_status}, expected ready before spec link",
                    ["resolve", "record-evidence", "block"],
                )
                save_run_state(root, state)
                print(json.dumps(state, indent=2))
                sys.exit(1)
        else:
            _apply_roadmap_hook_block(
                state, hook_name, "user_decision_required",
                "multiple roadmap items linked to this change",
                ["choose one item to link to spec", "repair roadmap links manually"],
            )
            state["block"]["candidates"] = items
            save_run_state(root, state)
            print(json.dumps(state, indent=2))
            sys.exit(1)
```

Update `_run_loaders` to accept new loader names:

```python
        if loader_name in ("spec_change_status", "openspec_change_status"):
            change_id = state.get("context", {}).get("change_id", "")
            if change_id:
                result = loader_spec_change_status(root, change_id)
                state.setdefault("evidence", {})["spec_status"] = result
        elif loader_name in ("spec_archive_path", "openspec_archive_path"):
            change_id = state.get("context", {}).get("change_id", "")
            if change_id:
                ap = loader_spec_archive_path(root, change_id)
                if ap:
                    state.setdefault("evidence", {})["archive_path"] = ap
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestWorkflowDefinitionContracts tests/test_workflow.py -k "spec_link" -v
```

Expected: PASS.

---

### Task 3: Wrapper Contract Mapping And Prompt Contracts

**Files:**
- Modify: `skills/_lib/wrapper_contracts.py`
- Modify: `tests/test_wrapper_contracts.py`
- Modify: `agents/dev-orchestrator.md`
- Modify: `agents/roadmap-agent.md`

- [ ] **Step 1: Add failing wrapper mapping and prompt contract tests**

In `TestPhaseAgentMapping`, add:

```python
    def test_roadmap_agent_allowed_in_review_roadmap(self):
        self.assertTrue(is_agent_allowed_in_phase("roadmap-agent", "review_roadmap"))
        self.assertFalse(is_agent_allowed_in_phase("plan-agent", "review_roadmap"))
```

Add prompt tests near existing agent prompt tests:

```python
class TestRoadmapAgentReviewContract(unittest.TestCase):
    def test_roadmap_agent_documents_review_contract(self):
        body = (AGENTS_DIR / "roadmap-agent.md").read_text(encoding="utf-8")

        self.assertIn("roadmap_review", body)
        self.assertIn("review_roadmap", body)
        self.assertIn("roadmap_review_decision", body)
        self.assertIn("ask_user_next_step", body)
        self.assertIn("ask_user_for_clarification", body)

    def test_dev_orchestrator_maps_review_roadmap_to_roadmap_agent(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")

        self.assertIn("review_roadmap", body)
        self.assertIn("Review roadmap item", body)
        self.assertIn("roadmap_spec_link_if_ready", body)
        self.assertNotIn("roadmap_status_ready_if_linked", body)
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py::TestPhaseAgentMapping tests/test_wrapper_contracts.py::TestRoadmapAgentReviewContract -v
```

Expected: FAIL because `review_roadmap` is not in `PHASE_AGENT_MAP` and prompts lack review contract text.

- [ ] **Step 3: Update wrapper phase map**

In `skills/_lib/wrapper_contracts.py`, change `PHASE_AGENT_MAP` to:

```python
PHASE_AGENT_MAP: Dict[str, Set[str]] = {
    "review_roadmap": {"roadmap-agent"},
    "create_change": {"plan-agent", "roadmap-agent"},
    "apply_change": {"implement-agent", "test-agent", "review-agent", "roadmap-agent"},
    "archive_change": {"finish-agent", "roadmap-agent"},
    "post_archive_actions": {"finish-agent", "roadmap-agent"},
}
```

- [ ] **Step 4: Update `agents/dev-orchestrator.md`**

Apply these prompt edits:

- Add `review_roadmap` to phase-agent mapping with `roadmap-agent`.
- Add a task-description row: `roadmap-agent | review_roadmap | Review roadmap item and return review decision`.
- Replace `roadmap_status_ready_if_linked` with `roadmap_spec_link_if_ready`.
- Add review result handling rules:

```markdown
### Roadmap Review Dispatch

For `review_roadmap`, dispatch `roadmap-agent` through the lifecycle dispatch pipeline.

If roadmap-agent returns:
- `roadmap_review_decision: "passed"` — ask the user whether to create spec artifacts or review the next roadmap item.
- `roadmap_review_decision: "needs_discussion"` — ask the returned `open_questions`, then redispatch roadmap-agent with the user's answers.
- `recommended_next_action: "review_next_item"` — dispatch roadmap-agent to select the next idea item using the roadmap list rules.

Do not dispatch `plan-agent` until the user explicitly chooses to create spec artifacts.
```

- [ ] **Step 5: Update `agents/roadmap-agent.md`**

Add a `roadmap_review` input section and output examples from the approved spec. Update hook names:

```markdown
### roadmap_review

When dispatched for `review_roadmap`:
1. Load `sdlc-roadmap`.
2. Read the roadmap item by `roadmap_item_id`.
3. Review Goal, Problem Context, Scope, Design Notes, Acceptance Criteria, Dependencies, Priority, and Order.
4. If open questions remain, leave status as `idea` and return `blocked` with `roadmap_review_decision: "needs_discussion"` and `open_questions`.
5. If review passes, use `sdlc-roadmap` to mark the item `ready`, append changelog evidence, and do not create spec artifacts.
6. Return `recommended_next_action: "ask_user_next_step"`.
```

Rename `roadmap_status_ready_if_linked` to `roadmap_spec_link_if_ready` in the lifecycle hook contract.

- [ ] **Step 6: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py::TestPhaseAgentMapping tests/test_wrapper_contracts.py::TestRoadmapAgentReviewContract -v
```

Expected: PASS.

---

### Task 4: Roadmap Skill Semantics And Templates

**Files:**
- Modify: `skills/sdlc-roadmap/SKILL.md`
- Modify: `skills/sdlc-roadmap/templates/item.md`
- Modify: `tests/test_wrapper_contracts.py`

- [ ] **Step 1: Add failing static contract tests for roadmap skill docs/templates**

In `tests/test_wrapper_contracts.py`, add:

```python
class TestRoadmapSkillSpecChangeVocabulary(unittest.TestCase):
    def test_roadmap_skill_uses_review_passed_ready_semantics(self):
        body = (REPO_ROOT / "skills" / "sdlc-roadmap" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("ready     | Review passed", body)
        self.assertIn("spec_change", body)
        self.assertNotIn("openspec_change:", body)
        self.assertNotIn("Create complete OpenSpec artifacts", body)

    def test_roadmap_item_template_uses_spec_change(self):
        template = (REPO_ROOT / "skills" / "sdlc-roadmap" / "templates" / "item.md").read_text(encoding="utf-8")

        self.assertIn("spec_change:", template)
        self.assertNotIn("openspec_change:", template)
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py::TestRoadmapSkillSpecChangeVocabulary -v
```

Expected: FAIL because current skill docs/templates still describe `openspec_change` and automatic OpenSpec creation.

- [ ] **Step 3: Update `skills/sdlc-roadmap/SKILL.md`**

Make these focused edits:

- Frontmatter description: change “OpenSpec changes” to “spec changes”.
- Roadmap item field:

```yaml
spec_change: null | "change-id"
```

- Status table:

```markdown
| ready     | Review passed, eligible for spec creation |
```

- `roadmap review` workflow success branch:

```markdown
6. **If review passes:** Mark the item ready without creating spec artifacts:
   - Set `status: ready`
   - Leave `spec_change` unchanged unless it already exists
   - Append a changelog entry to `revisions/changelog.md`
   - No snapshot needed (content not overwritten)
7. After item becomes `ready`, ask whether to create spec artifacts or continue reviewing the next idea item.
```

- Boundary table: replace `openspec_change` references with `spec_change` where they are domain fields. Keep concrete `openspec-*` skill names only in sections that explicitly discuss the current provider backend.

- [ ] **Step 4: Update item template**

In `skills/sdlc-roadmap/templates/item.md`, replace:

```yaml
openspec_change: null
```

with:

```yaml
spec_change: null
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py::TestRoadmapSkillSpecChangeVocabulary -v
```

Expected: PASS.

---

### Task 5: Runtime Data Migration Surface And Existing Test Vocabulary

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `tests/test_workflow.py`
- Modify: `tests/test_wrapper_contracts.py`
- Modify: any canonical docs/prompts still using `openspec_change` as a domain subject name.

- [ ] **Step 1: Add/adjust tests that reject legacy subject type and accept provider-agnostic action names**

Update existing start/preflight tests to use `spec_*` action names for new behavior while keeping one explicit legacy rejection test for subject types:

```python
    def test_start_rejects_legacy_subject_type(self):
        rc, _, stderr = run_workflow(
            self.tmp, "start",
            subject_type="openspec_change",
            subject_id="demo-change",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("invalid choice", stderr.lower())

    def test_preflight_spec_apply_in_create_phase_blocks(self):
        run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="phase-test")
        rc, data, _ = self._run_preflight("spec_apply", subject_type="spec_change", subject_id="phase-test")
        self.assertEqual(rc, 1)
        self.assertFalse(data["allowed"])
        self.assertEqual(data["reason"], "wrong_phase")
```

For existing `openspec_*` action tests, either rename to `spec_*` or leave one compatibility test only if the implementation intentionally keeps action aliases during migration.

- [ ] **Step 2: Run targeted workflow tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py::TestStartAndStatus tests/test_workflow.py::TestPreflightEnsureRun -v
```

Expected: PASS after Task 1 aliases are in place.

- [ ] **Step 3: Rename user-facing runtime strings**

In `.ai/workflows/scripts/workflow.py`, change user-facing messages/comments from `openspec` to `spec` where they are not naming a concrete filesystem/provider helper. Examples:

```python
"A linked roadmap_item run already exists for this change. The roadmap_item run is the canonical run."
```

Avoid changing concrete filesystem paths like `openspec/changes/...` or provider helper names unless the code has a provider-neutral wrapper already.

- [ ] **Step 4: Run broader workflow tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py -v
```

Expected: PASS.

---

### Task 6: Distribution Sync

**Files:**
- Generated: `.opencode/agents/*`, `.claude/agents/*`, `.cursor/agents/*`
- Generated: `.opencode/skills/sdlc-roadmap/SKILL.md`, `.claude/skills/sdlc-roadmap/SKILL.md`, `.cursor/skills/sdlc-roadmap/SKILL.md`
- Generated: workflow templates under project-level distributed skill copies if sync scripts update them.

- [ ] **Step 1: Sync workflow templates**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
```

Expected: exits 0 and synchronizes live workflow/templates/distributed workflow copies.

- [ ] **Step 2: Sync agent distributions**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
```

Expected: all commands exit 0 and generated copies include valid `model` and `variant` frontmatter.

- [ ] **Step 3: Sync roadmap skill project-level distributions**

Run:

```bash
python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py --source-repo . --skill-name sdlc-roadmap --source-ref HEAD --target .opencode/skills/sdlc-roadmap --status stable
python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py --source-repo . --skill-name sdlc-roadmap --source-ref HEAD --target .claude/skills/sdlc-roadmap --status stable
python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py --source-repo . --skill-name sdlc-roadmap --source-ref HEAD --target .cursor/skills/sdlc-roadmap --status stable
```

Expected: all commands exit 0 and distributed copies match canonical skill content.

- [ ] **Step 4: Check sync drift**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
python3 scripts/setup_agents.py --target ./.opencode/agents --check
```

Expected: both commands exit 0.

---

### Task 7: Final Verification

**Files:**
- No planned edits.

- [ ] **Step 1: Run focused contract tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full tests**

Run:

```bash
python3 -m pytest tests/ -v
```

Expected: PASS.

- [ ] **Step 3: Inspect diff for accidental broad rewrites**

Run:

```bash
git status --short
git diff -- .ai/workflows/scripts/workflow.py .ai/workflows/definitions/sdlc-main.yaml skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml agents/dev-orchestrator.md agents/roadmap-agent.md skills/sdlc-roadmap/SKILL.md skills/sdlc-roadmap/templates/item.md skills/_lib/wrapper_contracts.py tests/test_workflow.py tests/test_wrapper_contracts.py docs/superpowers/specs/2026-07-02-dev-orchestrator-roadmap-agent-coop-design.md docs/superpowers/plans/2026-07-03-dev-orchestrator-roadmap-agent-coop.md
```

Expected: diff contains only planned runtime contract, prompt/docs, test, template, and distribution changes.

---

## Self-Review

**Spec coverage:** Covered review routing, `ready` semantics, `spec_change` naming, hook rename/semantics, run creation behavior via phase inference, prompt contracts, roadmap skill semantics, template sync, and distribution sync.

**Placeholder scan:** No TODO/TBD placeholders. Each task includes exact files, code snippets, commands, and expected outcomes.

**Type/name consistency:** Uses `spec_change`, `spec_*` action aliases, `roadmap_spec_link_if_ready`, `review_roadmap`, `roadmap_review_decision`, and `roadmap-agent` consistently. Concrete `openspec/changes` filesystem paths remain provider implementation details where no provider-neutral path exists.
