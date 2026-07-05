# Workflow Final Tail Commit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure completed SDLC workflow runs end with a deterministic post-done governance-artifact commit or a safe noop after all runtime state writes, hook completions, and active-to-history moves have finished.

**Architecture:** Keep `workflow.py` as the owner of final Git publishing through a new `final-commit` command. Keep `dev-orchestrator` as a routing coordinator that calls the workflow runtime command after advancing the captured run to done. Do not define finish-agent terminal ownership or branch decision behavior in this plan; those are owned by `2026-07-05-finish-agent-branch-decision-and-terminal-ownership` and runtime evidence invariants.

**Tech Stack:** Python workflow runtime, Git subprocess calls, JSON CLI output, Markdown/YAML dev-orchestrator prompt, pytest workflow and prompt-contract tests, existing derived artifact sync scripts.

---

## File Structure

Expected files to inspect and potentially modify:

- Read: `docs/superpowers/specs/2026-07-05-workflow-final-tail-commit.md`
  - Responsibility: source requirements for this plan.
- Read as dependency: `docs/superpowers/specs/2026-07-05-finish-agent-branch-decision-and-terminal-ownership.md`
  - Responsibility: finish lifecycle boundary; do not duplicate finish-agent terminal ownership requirements here.
- Modify: `.ai/workflows/scripts/workflow.py`
  - Responsibility: add `final-commit` command, allowlist staging, structured JSON output, and argument parser wiring.
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
  - Responsibility: keep bootstrap workflow runtime template aligned with canonical runtime.
- Modify after sync or direct template propagation: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`, `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`, `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
  - Responsibility: derived workflow runtime templates must match canonical template.
- Modify: `agents/dev-orchestrator.md`
  - Responsibility: add Final Tail Commit Protocol after run-done advancement.
- Modify after agent sync: `.opencode/agents/dev-orchestrator.md`, `.claude/agents/dev-orchestrator.md`, `.cursor/agents/dev-orchestrator.md`
  - Responsibility: derived dev-orchestrator prompts reflect canonical prompt.
- Modify: `tests/test_workflow.py`
  - Responsibility: runtime tests for `final-commit` behavior.
- Modify if prompt-contract tests are kept separately: `tests/test_wrapper_contracts.py`
  - Responsibility: prompt tests for dev-orchestrator final-tail-commit wording.
- Read if needed: `AGENTS.md`
  - Responsibility: canonical-vs-derived update discipline and sync commands.

Out of scope for this plan:

- `agents/finish-agent.md` substantive changes.
- `.opencode/.claude/.cursor` finish-agent distributed prompt updates.
- Branch finish decision gates.
- Finish-agent final evidence requirements.

---

## Task 1: Add Failing Runtime Tests

**Files:**
- Modify: `tests/test_workflow.py`
- Read: `.ai/workflows/scripts/workflow.py`

**Purpose:** Lock desired `workflow.py final-commit` behavior before implementation.

- [ ] **Step 1: Inspect existing workflow test helpers**

Find existing helpers for creating temporary workflow roots, invoking `workflow.py`, initializing Git repositories, reading JSON command output, and asserting run state. Reuse existing patterns instead of inventing unrelated fixtures.

- [ ] **Step 2: Add test for rejecting incomplete or active runs**

Create a temporary repo with an active run or a history run whose `run.json` is not done.

Assert:

```text
workflow.py final-commit --run-id <run_id>
```

returns non-success JSON and does not create a commit.

Expected stable error values may include:

```text
missing_run_id
history_run_not_found
invalid_run_json
run_id_mismatch
run_not_done
```

Prefer one stable value per failure mode.

- [ ] **Step 3: Add test for noop when nothing allowlisted is dirty**

Create `.ai/workflows/runs/history/<run_id>/run.json` with `status: done` and `current_phase: done`, commit the baseline, then run:

```bash
python3 .ai/workflows/scripts/workflow.py --root <tmp> final-commit --run-id <run_id>
```

Assert JSON contains:

```json
{
  "status": "noop",
  "reason": "nothing_to_commit",
  "committed": false,
  "pushed": false,
  "staged_paths": []
}
```

- [ ] **Step 4: Add test for committing allowed workflow history files**

After baseline commit, modify:

```text
.ai/workflows/runs/history/<run_id>/run.json
```

Run final-commit.

Assert:

- `status == "success"`
- `committed == true`
- `commit_id` is non-empty
- `staged_paths` includes the history run path
- `git status --short` is clean afterward

- [ ] **Step 5: Add test for not staging unrelated dirty files**

After baseline commit, modify both:

```text
.ai/workflows/runs/history/<run_id>/run.json
src/unrelated.py
```

Run final-commit.

Assert:

- allowed history file is committed;
- `src/unrelated.py` remains dirty;
- output contains `src/unrelated.py` in `residual_dirty_paths`;
- the commit diff does not include `src/unrelated.py`.

- [ ] **Step 6: Add test for allowlist scoped to the specific run id**

Create two done history runs:

```text
.ai/workflows/runs/history/<target_run_id>/run.json
.ai/workflows/runs/history/<other_run_id>/run.json
```

Modify both after baseline commit.

Run final-commit for `<target_run_id>`.

Assert:

- target run changes are committed;
- other run changes remain dirty and appear in `residual_dirty_paths` unless covered by another allowlist rule;
- final-commit does not stage all of `.ai/workflows/runs/history/` indiscriminately.

- [ ] **Step 7: Add test for committing Superpowers archive governance artifacts**

After baseline commit, create or modify:

```text
docs/superpowers/archive/plans/2026-07-05-example.md
docs/superpowers/archive/specs/2026-07-05-example.md
```

Run final-commit for a done run.

Assert:

- these archive paths are included in `staged_paths` when dirty;
- unrelated files under `docs/superpowers/plans/` or `docs/superpowers/specs/` are not staged unless they were moved into the archive path and reported by Git as archived destination paths;
- unrelated source files remain residual.

- [ ] **Step 8: Add test for push only after successful commit**

Use monkeypatch or the repository's existing command-runner abstraction if present. If no abstraction exists, introduce a small helper in `workflow.py` to execute Git commands so tests can stub push safely.

Assert:

- `--push` invokes `git push` when a commit succeeds;
- `--push` does not invoke `git push` on noop;
- push failure reports `status: failed`, `committed: true`, `pushed: false`, and preserves `commit_id`.

- [ ] **Step 9: Run focused tests and confirm expected failures**

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "final_commit" -v
```

Expected:

- FAIL for missing `final-commit` command and behavior.

Do not weaken the tests to pass against current code.

---

## Task 2: Implement `workflow.py final-commit`

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`

**Purpose:** Add deterministic final Git publishing after workflow completion.

- [ ] **Step 1: Add Git helper functions**

Add small helpers near existing workflow utility functions:

```python
def _run_git(root, args, *, check=False):
    ...

def _git_status_porcelain(root):
    ...

def _git_dirty_paths(root):
    ...
```

Rules:

- Use `subprocess.run` with `cwd=root`.
- Capture stdout/stderr.
- Do not shell-concatenate user input.
- Return enough information for structured JSON errors.

- [ ] **Step 2: Add dirty path parsing**

Parse `git status --porcelain` into paths.

Requirements:

- support modified, added, deleted, renamed, staged, unstaged, and untracked files;
- for rename entries, include the destination path as the dirty path;
- normalize paths to repository-relative POSIX-style strings;
- avoid absolute paths in JSON output unless an existing test helper requires them.

- [ ] **Step 3: Add final-commit allowlist logic**

Implement a helper like:

```python
def _final_commit_allowed_prefixes(run_id):
    return [
        f".ai/workflows/runs/history/{run_id}/",
        ".ai/workflows/runs/current.json",
        ".ai/roadmap/",
        ".ai/memory/",
        "openspec/changes/archive/",
        "docs/superpowers/archive/",
    ]
```

Implement path classification:

```python
allowed_dirty_paths, residual_dirty_paths = _classify_final_commit_paths(dirty_paths, run_id)
```

Rules:

- `.ai/workflows/runs/history/<run_id>/...` is allowed.
- Other run history directories are not allowed by the run-specific rule.
- `current.json`, roadmap, memory, archived OpenSpec paths, and archived Superpowers paths are allowed if dirty.
- Active Superpowers source directories such as `docs/superpowers/plans/` and `docs/superpowers/specs/` are not broadly allowlisted.
- All other paths are residual.

- [ ] **Step 4: Add run completion precondition check**

Implement helper:

```python
def _load_done_history_run_for_final_commit(root, run_id):
    ...
```

Check:

- run id is present;
- `.ai/workflows/runs/history/<run_id>/run.json` exists;
- JSON loads successfully;
- `status == "done"` or `current_phase == "done"`;
- `run_json["run_id"]`, if present, equals `run_id`.

Return structured error codes such as:

- `missing_run_id`
- `history_run_not_found`
- `invalid_run_json`
- `run_id_mismatch`
- `run_not_done`

- [ ] **Step 5: Implement `cmd_final_commit`**

Algorithm:

```text
1. Validate done history run.
2. Read dirty paths.
3. Classify allowed vs residual dirty paths.
4. If allowed dirty paths is empty, return noop JSON with residual_dirty_paths.
5. For each allowed dirty path, run git add -- <path>.
6. Check staged diff with git diff --cached --name-only.
7. If staged diff is empty, return noop JSON.
8. Run git commit -m <message>.
9. Read commit id with git rev-parse HEAD.
10. If --push, run git push.
11. Read residual dirty paths again.
12. Return structured JSON.
```

Important:

- Never call `git add -A`.
- Never stage residual dirty paths.
- If `git commit` fails, return `status: failed`, `committed: false`.
- If `git push` fails after commit, return `status: failed`, `committed: true`, `pushed: false`, and the commit id.

- [ ] **Step 6: Add argparse wiring**

Add parser entry for:

```bash
workflow.py final-commit --run-id <run_id> [--message <message>] [--push]
```

Ensure command dispatch calls `cmd_final_commit`.

- [ ] **Step 7: Run focused runtime tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "final_commit" -v
```

Expected:

- PASS for final-commit tests.

---

## Task 3: Update Dev-Orchestrator Prompt Contract

**Files:**
- Modify: `agents/dev-orchestrator.md`
- Modify if prompt tests live here: `tests/test_wrapper_contracts.py`

**Purpose:** Make dev-orchestrator run final tail commit after the workflow reaches done without giving it direct Git write duties.

- [ ] **Step 1: Add failing prompt-contract test**

Add a test that asserts canonical `agents/dev-orchestrator.md` contains:

```text
Final Tail Commit Protocol
capture the active run_id before advancing to done
workflow.py final-commit --run-id
Do not run direct `git add`, `git commit`, or `git push`
git status --short
residual_dirty_paths
```

Run the focused test and confirm it fails before prompt update.

- [ ] **Step 2: Add Final Tail Commit Protocol section**

Add a section near dispatch lifecycle / terminal workflow handling:

```md
## Final Tail Commit Protocol

After the workflow reaches `done`, dev-orchestrator must publish final workflow/governance artifacts through the runtime command, not direct Git commands.

Required order:
1. Capture the active `run_id` before advancing to `done`, because `advance` may clear `.ai/workflows/runs/current.json`.
2. Ensure finish lifecycle evidence has already been recorded according to the runtime context and finish lifecycle specs.
3. Call `complete-phase` / `complete-hook` / `advance` as required until the run reaches `done` and the active run is moved to history.
4. Call `python3 .ai/workflows/scripts/workflow.py --root . final-commit --run-id <captured_run_id> --push`.
5. Call `git status --short` and report clean status or `residual_dirty_paths`.

Do not run direct `git add`, `git commit`, or `git push`; final Git publishing is owned by `workflow.py final-commit`.
```

Do not define finish-agent branch decision or terminal ownership rules in this section; reference the finish lifecycle spec for those rules.

- [ ] **Step 3: Update terminal success action table if needed**

Where the table says a run reaches done after finish/hook completion, extend the downstream action to include final tail commit after done.

Do not imply final-commit runs before hooks are completed.

- [ ] **Step 4: Run prompt-contract tests**

Run the relevant prompt tests:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k "dev_orchestrator" -v
```

---

## Task 4: Sync Runtime Templates and Derived Dev-Orchestrator

**Files:**
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Modify: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Modify: `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Modify: `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Modify: `.opencode/agents/dev-orchestrator.md`
- Modify: `.claude/agents/dev-orchestrator.md`
- Modify: `.cursor/agents/dev-orchestrator.md`

**Purpose:** Keep canonical sources and generated/activated copies aligned without touching finish-agent prompt copies for this plan.

- [ ] **Step 1: Inspect existing sync commands**

Read existing repo guidance and scripts:

```bash
python3 scripts/sync_derived_artifacts.py --check
python3 scripts/sync_derived_artifacts.py --fix
python3 scripts/setup_agents.py --help
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --help
```

Use the repository's established sync path rather than manually editing every derived file unless the sync tool requires manual follow-up.

- [ ] **Step 2: Sync workflow runtime template**

Propagate `.ai/workflows/scripts/workflow.py` changes to:

```text
skills/sdlc-project-bootstrap/templates/workflow/workflow.py
.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py
.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py
.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py
```

- [ ] **Step 3: Sync dev-orchestrator prompt**

Propagate canonical dev-orchestrator prompt changes to:

```text
.opencode/agents/dev-orchestrator.md
.claude/agents/dev-orchestrator.md
.cursor/agents/dev-orchestrator.md
```

Do not edit or sync finish-agent prompt copies as part of this plan unless another already-approved spec requires it in the same work package.

- [ ] **Step 4: Run derived artifact check**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --check
```

If drift is reported and safe:

```bash
python3 scripts/sync_derived_artifacts.py --fix
python3 scripts/sync_derived_artifacts.py --check
```

---

## Task 5: Full Verification

**Files:**
- Read/modify as needed based on test failures.

**Purpose:** Prove runtime, prompt contracts, and derived sync all pass.

- [ ] **Step 1: Run focused workflow tests**

```bash
python3 -m pytest tests/test_workflow.py -k "final_commit" -v
```

- [ ] **Step 2: Run full workflow tests**

```bash
python3 -m pytest tests/test_workflow.py -v
```

- [ ] **Step 3: Run prompt-contract tests**

```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
```

- [ ] **Step 4: Run full test suite**

```bash
python3 -m pytest tests/ -v
```

- [ ] **Step 5: Run final sync check**

```bash
python3 scripts/sync_derived_artifacts.py --check
```

- [ ] **Step 6: Inspect final Git state**

Run:

```bash
git status --short
```

Expected:

- only intended implementation artifacts are dirty before manual/development commit;
- no unexpected generated drift remains;
- no unrelated files were modified by tests or sync commands.

---

## Task 6: Handoff and Acceptance Evidence

**Files:**
- Write workflow handoff if running inside governed workflow.

**Purpose:** Return enough evidence for review-agent and dev-orchestrator to validate the implementation.

- [ ] **Step 1: Summarize changed files**

Report:

- workflow runtime files changed;
- dev-orchestrator prompt files changed;
- derived/template files changed;
- tests changed.

- [ ] **Step 2: Summarize final-commit behavior**

Include:

- command syntax;
- precondition checks;
- allowlist paths, including `docs/superpowers/archive/`;
- residual dirty path handling;
- push semantics.

- [ ] **Step 3: Summarize verification commands**

Include exact command/result pairs for:

```bash
python3 -m pytest tests/test_workflow.py -k "final_commit" -v
python3 -m pytest tests/test_workflow.py -v
python3 -m pytest tests/test_wrapper_contracts.py -v
python3 -m pytest tests/ -v
python3 scripts/sync_derived_artifacts.py --check
```

- [ ] **Step 4: Confirm acceptance criteria**

Acceptance checklist:

- `workflow.py final-commit` exists and is parser-wired.
- It rejects missing/not-done history runs.
- It commits allowlisted workflow governance files after done.
- It includes `docs/superpowers/archive/` in the governance allowlist.
- It never uses `git add -A`.
- It leaves unrelated dirty files unstaged and reports `residual_dirty_paths`.
- It pushes only after a successful commit.
- `dev-orchestrator` captures run id before done and calls final-commit after runtime closure.
- Derived workflow template and dev-orchestrator files are synced.
- Focused and full tests pass.
