# Retire Legacy sdlc-orchestrator Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use Superpowers `executing-plans` for sequential implementation. Use `behavioral-test-design` when rewriting tests so active behavior coverage is preserved. Do not rewrite historical archive/spec files as part of this plan.

**Goal:** Delete the legacy `sdlc-orchestrator` skill family and make active tests, EvalOps metadata, roadmap ownership, and active skill docs consistent with the current `dev-orchestrator` architecture.

**Architecture:** Runtime-first cleanup. Active routing already belongs to `dev-orchestrator` and `workflow.py`. This plan removes the obsolete skill and its active EvalOps target, rewrites active ownership references, preserves active script/test behavior by moving checks to live targets, and leaves historical archives untouched.

**Tech Stack:** Markdown skills and plans, YAML/JSON manifests, Python helper scripts, existing pytest coverage, repository search.

**Repository Policy Note:** Do not commit during execution of this plan unless the user explicitly asks.

---

## File Structure

- Delete: `skills/sdlc-orchestrator/`
- Delete: `.opencode/skills/sdlc-orchestrator/`
- Delete: `.claude/skills/sdlc-orchestrator/`
- Delete: `.cursor/skills/sdlc-orchestrator/`
- Modify: `skills/meta-skill-evaluator/SKILL.md`
- Modify: `skills/sdlc-roadmap/SKILL.md`
- Modify: `skills/sdlc-roadmap/scripts/sync.py`
- Modify: `skills/sdlc-evalops/SKILL.md`
- Modify: `skills/sdlc-evalops/scripts/export-promptfoo.py`
- Modify: `skills/sdlc-evalops/scripts/run-promptfoo-eval.py`
- Modify: `skills/sdlc-evalops/scripts/run-eval-matrix.py`
- Modify: `.ai/evals/manifest.yaml`
- Delete: `.ai/evals/targets/skill.sdlc-orchestrator/`
- Modify: `.ai/roadmap/manifest.json`
- Modify: `.ai/roadmap/areas/workflow.sdlc-orchestrator/manifest.json`
- Delete: `tests/test_sdlc_orchestrator.py`
- Modify: `tests/test_evalops_root.py`
- Modify: `tests/test_project_bootstrap_skills.py`
- Modify: `tests/test_wrapper_contracts.py`
- Modify: `tests/test_sdlc_roadmap.py`
- Modify: `tests/test_meta_skill_evaluator.py`

Historical `openspec/changes/archive/**` and old `docs/superpowers/**` files are read-only context for this plan.

---

### Task 1: Confirm Active Dependency Boundaries

**Files:**
- Read-only inventory in active paths.

- [x] **Step 1: Search active paths for `sdlc-orchestrator` references**

Search these active paths only:

- `skills/`
- `tests/`
- `.ai/evals/`
- `.ai/roadmap/`
- `.opencode/skills/`
- `.claude/skills/`
- `.cursor/skills/`

Expected:

- Classify each hit as one of:
  - `delete-with-skill`
  - `rewrite-to-dev-orchestrator`
  - `rewrite-to-workflow-runtime`
  - `keep-historical`

- [x] **Step 2: Confirm active workflow runtime does not depend on the skill**

Inspect:

- `agents/dev-orchestrator.md`
- `.ai/workflows/definitions/sdlc-main.yaml`

Expected:

- Active routing already uses `dev-orchestrator`.
- No active workflow phase requires `sdlc-orchestrator`.

---

### Task 2: Delete Legacy Skill Assets

**Files:**
- `skills/sdlc-orchestrator/`
- `.opencode/skills/sdlc-orchestrator/`
- `.claude/skills/sdlc-orchestrator/`
- `.cursor/skills/sdlc-orchestrator/`

- [x] **Step 1: Delete canonical legacy skill directory**

Expected:

- `skills/sdlc-orchestrator/` no longer exists.

- [x] **Step 2: Delete project-level distributed copies**

Expected:

- No project-level distributed skill copy remains under `.opencode/skills/`, `.claude/skills/`, or `.cursor/skills/`.

---

### Task 3: Delete Active EvalOps Target

**Files:**
- `.ai/evals/manifest.yaml`
- `.ai/evals/targets/skill.sdlc-orchestrator/`

- [x] **Step 1: Remove `skill.sdlc-orchestrator` from the global manifest**

Expected:

- `.ai/evals/manifest.yaml` still registers active targets such as `skill.sdlc-evalops`, `skill.sdlc-roadmap`, and `agent.dev-orchestrator`.
- `.ai/evals/manifest.yaml` no longer registers `skill.sdlc-orchestrator`.

- [x] **Step 2: Delete `.ai/evals/targets/skill.sdlc-orchestrator/` directly**

Expected:

- The target workspace is removed entirely.
- No archive or migration workspace is created as part of this plan.

---

### Task 4: Rewrite Active Ownership References

**Files:**
- `skills/meta-skill-evaluator/SKILL.md`
- `skills/sdlc-roadmap/SKILL.md`
- `skills/sdlc-roadmap/scripts/sync.py`
- `skills/sdlc-evalops/SKILL.md`
- `skills/sdlc-evalops/scripts/export-promptfoo.py`
- `skills/sdlc-evalops/scripts/run-promptfoo-eval.py`
- `skills/sdlc-evalops/scripts/run-eval-matrix.py`

- [x] **Step 1: Rewrite SDLC routing references to `dev-orchestrator`**

In active skill docs:

- Replace overall routing ownership claims that still name `sdlc-orchestrator`.
- Keep the scope narrow: only update active docs and active messaging.

Expected:

- `meta-skill-evaluator` points to `dev-orchestrator` for overall SDLC routing.
- `sdlc-evalops` integration text describes active agent/runtime ownership, not the retired skill.

- [x] **Step 2: Rewrite roadmap post-archive owner references**

Expected:

- `skills/sdlc-roadmap/SKILL.md` describes `dev-orchestrator` plus `workflow.py` as the lifecycle trigger owners.
- `skills/sdlc-roadmap/scripts/sync.py` no longer tells the user to let `sdlc-orchestrator` resolve mismatches.

- [x] **Step 3: Replace legacy example target ids in EvalOps scripts**

Expected:

- Script help text no longer uses `skill.sdlc-orchestrator` as the example target id.
- Example ids point at active targets.

---

### Task 5: Update Active Roadmap Ownership Metadata

**Files:**
- `.ai/roadmap/manifest.json`
- `.ai/roadmap/areas/workflow.sdlc-orchestrator/manifest.json`

- [x] **Step 1: Update workflow area owner path**

Expected:

- `owner_path` no longer references `skills/sdlc-orchestrator`.
- The owner path points at an active orchestration surface, such as `agents/dev-orchestrator.md`.

- [x] **Step 2: Keep area continuity without renaming items**

Expected:

- Existing roadmap item files remain in place.
- This plan does not rename the area directory or move its item history.

---

### Task 6: Rewrite Tests Around Active Contracts

**Files:**
- `tests/test_evalops_root.py`
- `tests/test_project_bootstrap_skills.py`
- `tests/test_wrapper_contracts.py`
- `tests/test_sdlc_roadmap.py`
- `tests/test_meta_skill_evaluator.py`
- Delete: `tests/test_sdlc_orchestrator.py`

- [x] **Step 1: Delete dedicated legacy skill tests**

Expected:

- `tests/test_sdlc_orchestrator.py` is removed.
- No test requires `skills/sdlc-orchestrator/SKILL.md` to exist.

- [x] **Step 2: Remove or rewrite legacy existence assertions**

Expected:

- `tests/test_project_bootstrap_skills.py` no longer validates the retired skill.
- `tests/test_wrapper_contracts.py` no longer checks manual-trigger text for a deleted skill.
- `tests/test_sdlc_roadmap.py` and `tests/test_meta_skill_evaluator.py` now expect active ownership names.

- [x] **Step 3: Preserve EvalOps script behavior coverage using a live target**

Expected:

- `tests/test_evalops_root.py` uses an active target, preferably `skill.sdlc-evalops`, for export/check/dry-run behavior.
- The test still proves export freshness, Promptfoo config generation, and matrix dry-run behavior.
- The test does not overfit to the deleted target id.

---

### Task 7: Re-Distribute Modified Active Skills

**Files:**
- Project-level distributed copies for modified active skills.

- [x] **Step 1: Re-distribute changed skills to project-level targets**

Expected:

- Updated canonical content for:
  - `sdlc-roadmap`
  - `sdlc-evalops`
  - `meta-skill-evaluator`
  is reflected under `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/`.

- [x] **Step 2: Confirm retired skill is not reinstalled by distribution**

Expected:

- No distribution step recreates `sdlc-orchestrator` project-level copies.

---

### Task 8: Verify Active State

**Files:**
- Verification only.

- [x] **Step 1: Run focused pytest for modified areas**

Run at minimum:

```bash
python3 -m pytest \
  tests/test_evalops_root.py \
  tests/test_project_bootstrap_skills.py \
  tests/test_wrapper_contracts.py \
  tests/test_sdlc_roadmap.py \
  tests/test_meta_skill_evaluator.py \
  tests/test_workflow.py -v
```

Expected:

- Updated tests pass.
- `tests/test_workflow.py` still proves active phases do not route through legacy `sdlc-orchestrator`.

- [x] **Step 2: Run active EvalOps export verification**

Run:

```bash
python3 skills/sdlc-evalops/scripts/export-promptfoo.py skill.sdlc-evalops --check
```

Expected:

- Freshness check passes for an active target.

- [x] **Step 3: Run active EvalOps matrix dry-run**

Run:

```bash
python3 skills/sdlc-evalops/scripts/run-eval-matrix.py skill.sdlc-evalops --dry-run
```

Expected:

- Dry-run succeeds without mutating canonical exports.

- [x] **Step 4: Validate roadmap metadata**

Run the roadmap validation command used by the active roadmap skill.

Expected:

- Roadmap metadata remains valid after owner path updates.

- [x] **Step 5: Re-run active-path search for `sdlc-orchestrator`**

Expected:

- No hits remain in active paths except intentional historical names such as the roadmap area id if preserved.
- Historical archive/spec/design paths may still contain the old name.

---

## Done Criteria

- The legacy skill and its project-level distributed copies are deleted.
- The legacy EvalOps target is deleted and de-registered.
- Active skills and active scripts no longer describe `sdlc-orchestrator` as the current owner.
- Active roadmap metadata no longer points to deleted skill files.
- Active tests prove the current architecture instead of the retired one.
- Verification commands pass.
