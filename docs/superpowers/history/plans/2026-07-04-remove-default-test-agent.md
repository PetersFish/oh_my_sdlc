# Remove Default Test-Agent Role Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use Superpowers `executing-plans` for sequential implementation. Use `test-driven-development` when modifying executable behavior or deterministic tests. Use `requesting-code-review` before final completion. Do not introduce OpenSpec artifacts for this cleanup unless the reviewer explicitly escalates the work.

**Goal:** Remove `test-agent` from the default SDLC lifecycle and align active agent files, templates, eval assets, and docs with the Superpowers-style implementation loop: implement-agent owns normal verification and repair; review-agent owns test quality and overfitting review; optional independent verification remains non-default.

**Architecture:** Agent-first cleanup. Active runtime should center on `dev-orchestrator` and specialized agent files under `agents/`, with workflow state still owned by `workflow.py`. Delete active `test-agent` files, remove default test-agent references from dispatching/finishing contracts, add finish-agent commit/push checkpoints before hook synchronization and after workflow cleanup, and retire legacy `sdlc-orchestrator` skill assets if dependency audit confirms they are unused.

**Tech Stack:** Markdown agent specs, skill assets, EvalOps target manifests, repository search, existing pytest suite for deterministic workflow/runtime behavior.

---

## File Structure

Expected files to inspect and potentially modify:

- Modify: `agents/dev-orchestrator.md`
  - Responsibility: top-level SDLC dispatcher; remove `test-agent` from default dispatch model and boundaries.
- Modify: `.opencode/agents/dev-orchestrator.md`
  - Responsibility: OpenCode distributed copy.
- Modify: `.claude/agents/dev-orchestrator.md`
  - Responsibility: Claude distributed copy.
- Modify: `.cursor/agents/dev-orchestrator.md`
  - Responsibility: Cursor distributed copy.
- Modify: `agents/implement-agent.md`
  - Responsibility: normal TDD, focused/full regression, and failure-fix ownership.
- Modify: distributed implement-agent copies under `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`.
- Modify: `agents/review-agent.md`
  - Responsibility: test quality, overfitting, and verification evidence review.
- Modify: distributed review-agent copies under `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`.
- Modify: `agents/finish-agent.md`
  - Responsibility: finishing, pre-hook commit/push, hook resolution, workflow cleanup, post-cleanup dirty-tree commit/push.
- Modify: distributed finish-agent copies under `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`.
- Delete: `agents/test-agent.md`
  - Responsibility: active default test-agent must not load.
- Delete: `.opencode/agents/test-agent.md`
  - Responsibility: OpenCode distributed copy.
- Delete: `.claude/agents/test-agent.md`
  - Responsibility: Claude distributed copy.
- Delete: `.cursor/agents/test-agent.md`
  - Responsibility: Cursor distributed copy.
- Modify if needed: `.ai/roadmap/areas/workflow.sdlc-orchestrator/items/RM-ORCH-007-workflow-wrapper-abstraction.md`
  - Responsibility: active roadmap statement for agent-backed lifecycle wrapper architecture.
- Delete if dependency audit passes: `skills/sdlc-orchestrator/`
  - Responsibility: legacy skill entrypoint replaced by `dev-orchestrator`.
- Delete if dependency audit passes: `.opencode/skills/sdlc-orchestrator/`, `.claude/skills/sdlc-orchestrator/`, `.cursor/skills/sdlc-orchestrator/`
  - Responsibility: distributed legacy copies.
- Delete, archive, or migrate if dependency audit passes: `.ai/evals/targets/skill.sdlc-orchestrator/`
  - Responsibility: legacy skill EvalOps target; active coverage should move to `agent.dev-orchestrator` if still valuable.
- Modify if needed: `.ai/evals/manifest.yaml`
  - Responsibility: remove or retarget `skill.sdlc-orchestrator` entries.
- Modify if needed: `skills/sdlc-project-bootstrap/templates/AGENTS.md`
  - Responsibility: generated project-level behavior guidance.
- Modify if needed: distributed bootstrap templates under `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/`.
- Modify if needed: tests under `tests/`
  - Responsibility: expectations for agent installation, bootstrap, wrapper contracts, and workflow behavior.

Historical archive/snapshot files should not be modified unless an active template, active eval, or current instruction copies from them.

---

## Task 1: Inventory Active `test-agent` References

**Files:**
- Read-only inventory first.

- [x] **Step 1: Search exact `test-agent` references**

Run:

```bash
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules "test-agent" .
```

Expected:

- Active agent files currently contain stale default `test-agent` references.
- Archive or snapshot files may contain historical references.
- Record each active reference and classify it as one of:
  - `active-default-role` — must change or delete.
  - `active-non-default-risk-trigger` — may keep only if explicitly non-default.
  - `historical-archive` — leave unchanged.
  - `test-fixture` — update only if it asserts default lifecycle behavior.

- [x] **Step 2: Search spaced phrase references**

Run:

```bash
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules -E "test agent|testing agent|independent verification" .
```

Expected:

- Identify references that do not use the exact token `test-agent`.
- Classify each active reference using the same categories as Step 1.

- [x] **Step 3: Search default lifecycle role lists**

Run:

```bash
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules -E "plan-agent.*implement-agent.*test-agent|implement-agent.*test-agent|planning, implementation, testing, review|substitute your own verification for test-agent|Requires test-agent" agents .opencode/agents .claude/agents .cursor/agents .ai/roadmap docs/superpowers tests .ai/evals || true
```

Expected:

- Any active default role list containing `test-agent` must be changed.
- Active default role lists should converge to `plan-agent`, `implement-agent`, `review-agent`, and `finish-agent`.

---

## Task 2: Remove Active `test-agent` Runtime Files

**Files:**
- `agents/test-agent.md`
- `.opencode/agents/test-agent.md`
- `.claude/agents/test-agent.md`
- `.cursor/agents/test-agent.md`
- Agent install/config metadata discovered by search.

- [x] **Step 1: Confirm these are active runtime files, not examples**

Run:

```bash
find agents .opencode/agents .claude/agents .cursor/agents -maxdepth 2 -name '*test-agent*' -print
```

Expected:

- The files are active agent specs and should be removed from the runtime path.

- [x] **Step 2: Search config metadata for `test-agent` registrations**

Run:

```bash
grep -RIn --exclude-dir=.git "test-agent" agents .opencode/agents .claude/agents .cursor/agents scripts tests || true
```

Expected:

- Remove active registrations or update test expectations that still install `test-agent` by default.

- [x] **Step 3: Delete active test-agent files**

Remove:

```text
agents/test-agent.md
.opencode/agents/test-agent.md
.claude/agents/test-agent.md
.cursor/agents/test-agent.md
```

Expected:

- No active runtime path loads `test-agent`.
- Historical `.ai/workflows/runs/history/**/test-agent*` artifacts remain untouched.

---

## Task 3: Update Default Agent Responsibilities

**Files:**
- `agents/dev-orchestrator.md` and distributed copies.
- `agents/implement-agent.md` and distributed copies.
- `agents/review-agent.md` and distributed copies.
- `agents/finish-agent.md` and distributed copies.

- [x] **Step 1: Update dev-orchestrator default role list and boundaries**

In `agents/dev-orchestrator.md` and distributed copies:

- Remove `test-agent` from the description's default specialized subagent list.
- Replace any boundary such as `substitute your own verification for test-agent` with `substitute your own verification or test-quality judgment for implement-agent/review-agent`.
- Ensure dispatch language treats normal verification as part of the implement/review lifecycle, not as a separate default subagent.

Expected:

- `dev-orchestrator` routes normal `apply_change` work to `implement-agent` and then `review-agent`, not `test-agent`.

- [x] **Step 2: Update implement-agent verification ownership**

In `agents/implement-agent.md` and distributed copies, ensure it explicitly owns:

- TDD red/green loops.
- Focused tests for the slice.
- Full regression command set agreed by the plan.
- Failure-fix loop while implementation context is still fresh.
- Structured verification evidence.

Expected:

- `implement-agent` does not hand normal full regression to `test-agent`.

- [x] **Step 3: Update review-agent quality gate ownership**

In `agents/review-agent.md` and distributed copies, ensure it explicitly owns:

- Test quality review.
- Overfitting detection.
- Verification evidence review.
- Routing concrete remediation back to `implement-agent`.

Expected:

- `review-agent` does not become a broad debugging or full-regression executor.

- [x] **Step 4: Update finish-agent preconditions**

In `agents/finish-agent.md` and distributed copies:

- Remove requirements for `test-agent` evidence.
- Require implementation verification evidence from `implement-agent` and review completion evidence from `review-agent`.
- Update failure modes so missing verification evidence points to `implement-agent` evidence, not `test-agent` completion.

Expected:

- `finish-agent` can proceed after implement-agent verification evidence and review-agent approval, without a test-agent handoff.

---

## Task 4: Add Finish-Agent Commit/Push Checkpoints

**Files:**
- `agents/finish-agent.md`
- `.opencode/agents/finish-agent.md`
- `.claude/agents/finish-agent.md`
- `.cursor/agents/finish-agent.md`
- Agent config tests if command allowlists are asserted.

- [x] **Step 1: Add required bash permissions**

Add allowlist entries needed by the finishing procedure:

```yaml
"git add*": allow
"git commit*": allow
"git push*": allow
"git rev-parse*": allow
```

Keep existing observational git permissions.

Expected:

- `finish-agent` can create and push closure commits.

- [x] **Step 2: Insert pre-hook commit procedure before memory/roadmap hooks**

Before resolving `memory_sync` or `roadmap_done_if_relevant`, `finish-agent` must:

1. Run `git status --short --branch`.
2. If the tree is dirty, stage approved implementation/archive changes, commit them, push, and record `git rev-parse HEAD` as `pre_hook_commit_id`.
3. If the tree is clean, record current `git rev-parse HEAD` as `pre_hook_commit_id` and verify the branch is not ahead of upstream.
4. Use `pre_hook_commit_id` as the commit id supplied to memory sync.

Expected:

- Memory sync records a stable commit id representing the reviewed implementation/archive state before sync-generated files are added.

- [x] **Step 3: Resolve hooks and complete workflow cleanup before the post-cleanup dirty-tree check**

Run hook work and workflow cleanup in this order:

1. `memory_sync` through `sdlc-openspec-memory-sync` or `sdlc-repository-memory-sync`.
2. `roadmap_done_if_relevant` through `roadmap-agent` / `sdlc-roadmap` boundary as currently required.
3. `workflow.py complete-hook --hook <hook-name>` after each hook's evidence is present.
4. Any remaining `workflow.py` cleanup required to satisfy `pending_hooks_empty` and phase completion evidence.

Expected:

- Hook outputs can reference the pre-hook commit id.
- Workflow cleanup has run before checking whether generated files remain.

- [x] **Step 4: Add post-cleanup dirty-tree commit procedure**

After all hook resolution, sync scripts, and workflow cleanup through `workflow.py` complete, `finish-agent` must:

1. Run `git status --short --branch` again.
2. If memory sync, roadmap sync, template sync, or workflow hook completion generated additional files, stage only those generated/approved artifacts.
3. Commit and push them.
4. Record `post_hook_commit_id`.
5. If the tree is clean, record `post_hook_commit_id: null` and `post_hook_dirty_tree: false`.

Expected:

- No generated memory/roadmap/workflow files remain uncommitted after finish-agent completes.
- The second commit happens after workflow cleanup, not before it.

- [x] **Step 5: Extend finish-agent evidence schema**

Add evidence fields:

```json
{
  "pre_hook_commit_id": "<sha>",
  "pre_hook_pushed": true,
  "post_hook_commit_id": "<sha|null>",
  "post_hook_pushed": "true|false",
  "post_hook_dirty_tree": false,
  "pending_hooks_empty": true
}
```

Expected:

- Reviewers can verify both commit checkpoints.

---

## Task 5: Fix Active Roadmap Drift

**Files:**
- `.ai/roadmap/areas/workflow.sdlc-orchestrator/items/RM-ORCH-007-workflow-wrapper-abstraction.md`

- [x] **Step 1: Update completion notes if they still mention landed `test-agent` split**

Look for wording equivalent to:

```text
Landed the dev-orchestrator / plan-agent / implement-agent / test-agent / review-agent / finish-agent lifecycle split
```

Replace with:

```text
Landed the dev-orchestrator / plan-agent / implement-agent / review-agent / finish-agent lifecycle split, with normal verification owned by implement-agent and test-quality review owned by review-agent. No default test-agent role is part of the first migration.
```

Expected:

- The active roadmap item should not simultaneously say `test-agent` is non-default and that a `test-agent` split was landed.

- [x] **Step 2: Verify active roadmap no longer contains default `test-agent` wording**

Run:

```bash
grep -n "test-agent" .ai/roadmap/areas/workflow.sdlc-orchestrator/items/RM-ORCH-007-workflow-wrapper-abstraction.md
```

Expected:

- Allowed only if wording explicitly says `No default test-agent` or explains optional future non-default verification.
- No role list should include `test-agent` as a default participant.

---

## Task 6: Audit and Retire Legacy `sdlc-orchestrator` Skill

**Files:**
- `skills/sdlc-orchestrator/`
- `.opencode/skills/sdlc-orchestrator/`
- `.claude/skills/sdlc-orchestrator/`
- `.cursor/skills/sdlc-orchestrator/`
- `.ai/evals/targets/skill.sdlc-orchestrator/`
- `.ai/evals/manifest.yaml`
- tests and scripts that reference the legacy skill.

- [x] **Step 1: Confirm dev-orchestrator does not depend on the legacy skill**

Run:

```bash
grep -RIn --exclude-dir=.git "sdlc-orchestrator" agents/dev-orchestrator.md .opencode/agents/dev-orchestrator.md .claude/agents/dev-orchestrator.md .cursor/agents/dev-orchestrator.md || true
```

Expected:

- No required skill, allowed skill, or dispatch dependency on `sdlc-orchestrator`.
- References in historical prose or comments must be inspected manually before deletion.

- [x] **Step 2: Confirm workflow definitions use dev-orchestrator**

Run:

```bash
grep -RIn --exclude-dir=.git "allowed_workers:" -A5 .ai/workflows/definitions skills/sdlc-project-bootstrap/templates/workflow .opencode/skills/sdlc-project-bootstrap/templates/workflow .claude/skills/sdlc-project-bootstrap/templates/workflow .cursor/skills/sdlc-project-bootstrap/templates/workflow | grep -E "sdlc-orchestrator|dev-orchestrator" || true
```

Expected:

- Active workflow definitions and bootstrap workflow templates use `dev-orchestrator`, not `sdlc-orchestrator`.

- [x] **Step 3: Audit installation, activation, and tests**

Run:

```bash
grep -RIn --exclude-dir=.git "sdlc-orchestrator\|skill.sdlc-orchestrator" scripts tests skills .opencode .claude .cursor .ai/evals .ai/workflows docs/superpowers || true
```

Expected:

- Active references are either migrated, deleted, or documented as blockers.
- Archive references are ignored unless they are copied into active templates.

- [x] **Step 4: Delete legacy skill directories if no blockers remain**

Delete:

```text
skills/sdlc-orchestrator/
.opencode/skills/sdlc-orchestrator/
.claude/skills/sdlc-orchestrator/
.cursor/skills/sdlc-orchestrator/
```

Expected:

- Legacy skill is no longer installed or distributed as an active skill.

- [x] **Step 5: Retire legacy EvalOps target**

If no active eval pipeline still requires `skill.sdlc-orchestrator`, either delete it or migrate useful cases to `agent.dev-orchestrator`:

```text
.ai/evals/targets/skill.sdlc-orchestrator/
```

Then update `.ai/evals/manifest.yaml` accordingly.

Expected:

- Eval manifest no longer points at a deleted skill target.
- Useful behavioral coverage is preserved under `agent.dev-orchestrator` when still relevant.

---

## Task 7: Update Bootstrap Templates If Needed

**Files:**
- `skills/sdlc-project-bootstrap/templates/AGENTS.md`
- `.opencode/skills/sdlc-project-bootstrap/templates/AGENTS.md`
- `.claude/skills/sdlc-project-bootstrap/templates/AGENTS.md`
- `.cursor/skills/sdlc-project-bootstrap/templates/AGENTS.md`
- Workflow templates under `skills/sdlc-project-bootstrap/templates/workflow/` and distributed copies.

- [x] **Step 1: Inspect generated behavior templates**

Run:

```bash
grep -RIn --exclude-dir=.git "test-agent\|test agent\|sdlc-orchestrator\|full regression\|overfitting" skills/sdlc-project-bootstrap/templates .opencode/skills/sdlc-project-bootstrap/templates .claude/skills/sdlc-project-bootstrap/templates .cursor/skills/sdlc-project-bootstrap/templates || true
```

Expected:

- Templates must not reinstall default `test-agent` or legacy `sdlc-orchestrator`.
- Templates should describe implement-agent/review-agent verification ownership only if they already describe subagent lifecycle behavior.

- [x] **Step 2: Run or update template sync only after inspecting convention**

Run read-only checks first:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --help >/dev/null 2>&1 || true
```

Expected:

- If project convention requires editing canonical files first and then syncing distributed copies, follow that convention.
- Do not blindly run a sync script if it modifies unrelated files.

---

## Task 8: Update Tests and Eval Expectations

**Files:**
- `tests/`
- `.ai/evals/targets/`
- `.ai/evals/manifest.yaml`

- [x] **Step 1: Search tests for default `test-agent` assumptions**

Run:

```bash
grep -RIn --exclude-dir=.git "test-agent\|plan-agent.*implement-agent.*test-agent\|testing, review\|skill.sdlc-orchestrator\|sdlc-orchestrator" tests .ai/evals || true
```

Expected:

- If tests assert default lifecycle role lists, update expected values to remove `test-agent`.
- If tests assert installed skill lists, update them to remove legacy `sdlc-orchestrator` when deletion is performed.
- If eval cases use `test-agent` historically but do not assert current default behavior, leave them unchanged only when they are under archive/history paths.

- [x] **Step 2: Add regression checks only if there is deterministic code behavior**

Add pytest only if implementation modifies:

- template generation logic,
- agent installation logic,
- workflow role mapping logic,
- wrapper registry code,
- deterministic routing code,
- EvalOps manifest generation.

Expected:

- Pure agent/doc cleanup can rely on grep verification plus existing tests.
- Runtime or template generation changes require pytest updates.

---

## Task 9: Verification Commands

- [x] **Step 1: Verify no active default `test-agent` role remains**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

active_roots = [
    Path('agents'),
    Path('.opencode/agents'),
    Path('.claude/agents'),
    Path('.cursor/agents'),
    Path('skills'),
    Path('.opencode/skills'),
    Path('.claude/skills'),
    Path('.cursor/skills'),
    Path('.ai/roadmap/areas/workflow.sdlc-orchestrator/items'),
    Path('docs/superpowers'),
    Path('tests'),
]

bad = []
for root in active_roots:
    if not root.exists():
        continue
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        text = path.read_text(errors='ignore')
        suspicious = [
            'plan-agent`, `implement-agent`, `test-agent`',
            'plan-agent / implement-agent / test-agent',
            'planning, implementation, testing, review, and finish as specialized agents',
            '`test-agent` performs independent verification',
            'Requires test-agent',
            'evidence.verification_passed` from test-agent',
            'substitute your own verification for test-agent',
        ]
        if path.name == 'test-agent.md' and '.ai/workflows/runs/history' not in str(path):
            bad.append((str(path), 'active test-agent file remains'))
        for needle in suspicious:
            if needle in text:
                bad.append((str(path), needle))

if bad:
    print('default test-agent references remain:')
    for path, needle in bad:
        print(f'- {path}: {needle}')
    raise SystemExit(1)
print('no default test-agent role references found in active roots')
PY
```

Expected:

- Command exits 0.

- [x] **Step 2: Verify finish-agent commit checkpoints**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

paths = [
    Path('agents/finish-agent.md'),
    Path('.opencode/agents/finish-agent.md'),
    Path('.claude/agents/finish-agent.md'),
    Path('.cursor/agents/finish-agent.md'),
]
required = [
    'git commit',
    'git push',
    'pre_hook_commit_id',
    'post_hook_commit_id',
    'memory_sync',
    'roadmap_done_if_relevant',
    'workflow.py complete-hook',
]
missing = []
for path in paths:
    text = path.read_text(errors='ignore')
    for needle in required:
        if needle not in text:
            missing.append((str(path), needle))
if missing:
    print('finish-agent commit checkpoint requirements missing:')
    for path, needle in missing:
        print(f'- {path}: {needle}')
    raise SystemExit(1)
print('finish-agent commit checkpoint requirements present')
PY
```

Expected:

- Command exits 0.
- Manual review confirms the second commit/push is after `workflow.py` cleanup, not before it.

- [x] **Step 3: Verify legacy `sdlc-orchestrator` removal or blocker**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
legacy = [
    Path('skills/sdlc-orchestrator'),
    Path('.opencode/skills/sdlc-orchestrator'),
    Path('.claude/skills/sdlc-orchestrator'),
    Path('.cursor/skills/sdlc-orchestrator'),
]
existing = [str(p) for p in legacy if p.exists()]
if existing:
    print('legacy sdlc-orchestrator skill directories still exist:')
    for path in existing:
        print(f'- {path}')
    print('If retained, final summary must document the active dependency blocker.')
else:
    print('legacy sdlc-orchestrator skill directories removed')
PY
```

Expected:

- Either no legacy directories exist, or the final summary documents an exact active dependency blocker.

- [x] **Step 4: Run relevant deterministic tests**

Run targeted tests:

```bash
python3 -m pytest tests/test_agent_config_lib.py -v
python3 -m pytest tests/test_install_agents.py -v
python3 -m pytest tests/test_activate_agents_config.py -v
python3 -m pytest tests/test_setup_agents.py -v
python3 -m pytest tests/test_project_bootstrap_skills.py -v
python3 -m pytest tests/test_wrapper_contracts.py -v
python3 -m pytest tests/test_workflow.py -v
```

If those pass, optionally run:

```bash
python3 -m pytest tests/ -v
```

Expected:

- Targeted tests pass.
- If full suite is not run, final summary must state that explicitly.

- [x] **Step 5: Confirm final diff is scoped**

Run:

```bash
git diff -- agents .opencode/agents .claude/agents .cursor/agents docs/superpowers .ai/roadmap skills .opencode/skills .claude/skills .cursor/skills .ai/evals tests scripts
```

Expected:

- Diff only touches files required by this plan.
- No generated archive snapshots are rewritten unless explicitly approved.

---

## Task 10: Review Handoff

- [x] **Step 1: Produce review summary**

The final implementation summary must include:

- Files changed.
- Files deleted.
- Whether any active `test-agent` references remain.
- Whether active `test-agent` files were deleted from all runtime distributions.
- Whether legacy `sdlc-orchestrator` skill directories were deleted or which active dependency blocked deletion.
- Whether legacy `skill.sdlc-orchestrator` EvalOps assets were deleted, archived, or migrated.
- Finish-agent pre-hook and post-cleanup commit/push behavior added.
- Verification commands run and results.
- Whether historical/archive references were intentionally left untouched.
- Any follow-up decisions needed from the reviewer.

- [x] **Step 2: Request code/doc review**

Use Superpowers `requesting-code-review` after the cleanup, with emphasis on:

- Responsibility boundary correctness.
- Whether the common path remains efficient.
- Whether optional independent verification is clear enough without reintroducing default `test-agent`.
- Whether finish-agent commit/push checkpoints are safe and auditable.
- Whether legacy `sdlc-orchestrator` deletion is justified by dependency evidence.
- Whether implement-agent and review-agent responsibilities are too broad.

---

## Done Criteria

- [x] The spec in `docs/superpowers/specs/2026-07-04-remove-default-test-agent.md` has been reviewed.
- [x] Active default lifecycle docs no longer include `test-agent`.
- [x] Active `test-agent` runtime files are deleted or explicitly disabled as non-default examples.
- [x] Normal verification ownership is assigned to `implement-agent`.
- [x] Test quality and overfitting review ownership is assigned to `review-agent`.
- [x] `finish-agent` performs a pre-hook commit/push checkpoint before memory and roadmap hooks.
- [x] `finish-agent` completes workflow cleanup through `workflow.py`, then performs a post-cleanup dirty-tree check and commits/pushes generated files if needed.
- [x] Optional independent verification is non-default and risk-triggered.
- [x] Legacy `sdlc-orchestrator` skill assets are deleted or exact dependency blockers are documented.
- [x] Legacy `skill.sdlc-orchestrator` EvalOps assets are deleted, archived, or migrated.
- [x] Relevant grep checks pass.
- [x] Relevant pytest commands pass or skipped commands are explicitly reported.
- [x] Review handoff is complete.
