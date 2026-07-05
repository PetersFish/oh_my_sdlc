# Incremental Derived Artifact Sync Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scripts/sync_derived_artifacts.py` support changed-file aware incremental check/fix so unrelated changes do not refresh `.skill-install.json` or other derived artifacts.

**Architecture:** Keep existing full `--check` and `--fix` behavior as the default. Add an explicit incremental scope layer that classifies changed paths into workflow, agent, skill, full-fallback, or skipped domains before constructing check/fix suites. Reuse existing lower-level scripts wherever possible, especially `check_skill_distribution.py --skills` for skill-scoped checks and `install_skill.py --skill-name` for skill-scoped fixes.

**Tech Stack:** Python stdlib, subprocess-based script orchestration, existing sync/install/check scripts, unittest/pytest tests in `tests/test_sync_derived_artifacts.py`.

---

## File Structure

Expected files to inspect and potentially modify:

- Modify: `scripts/sync_derived_artifacts.py`
  - Responsibility: CLI options, Git changed-file discovery, affected-domain classification, incremental check/fix suite construction, JSON/plain-text reporting.
- Modify: `tests/test_sync_derived_artifacts.py`
  - Responsibility: behavioral coverage for full compatibility, skipped changes, skill-only filtering, agent-only filtering, workflow-only filtering, full fallback, Git changed-file discovery, and JSON output.
- Read: `skills/meta-skill-lifecycle-governance/scripts/check_skill_distribution.py`
  - Responsibility: confirm and reuse `--skills` filtering contract.
- Read: `skills/meta-skill-lifecycle-governance/scripts/install_skill.py`
  - Responsibility: confirm install command shape and metadata write behavior.
- Read: `skills/sdlc-project-bootstrap/scripts/sync_templates.py`
  - Responsibility: confirm governed workflow files and workflow check/fix commands.
- Read: `scripts/setup_agents.py`
  - Responsibility: confirm target-wide agent check/fix commands.
- Read: `docs/superpowers/specs/2026-07-05-incremental-derived-artifact-sync-filtering.md`
  - Responsibility: source requirements for this plan.

Do not directly edit generated target files under `.opencode/`, `.claude/`, or `.cursor/` by hand. Let the sync scripts generate derived copies when the relevant domain is affected.

---

## Task 1: Add Failing Incremental-Scope Tests

**Files:**
- Modify: `tests/test_sync_derived_artifacts.py`
- Read: `scripts/sync_derived_artifacts.py`

**Purpose:** Lock the desired behavior before implementation. Existing full-mode tests should keep passing; new incremental tests should fail before implementation.

- [x] **Step 1: Preserve existing full-mode compatibility tests**

Keep the existing tests that assert plain `run_aggregate(..., mode="fix")` installs all canonical skills. Do not weaken these tests. Full mode remains the compatibility baseline.

- [x] **Step 2: Add docs-only skipped fix test**

Add a test that calls the new incremental path with changed files equivalent to:

- `docs/superpowers/specs/example.md`

Expected:

- return code is `0`;
- no subprocess commands are executed;
- JSON report has `scope: skipped` or equivalent;
- `affected.skills` is empty;
- `affected.agents` is false;
- `affected.workflows` is false.

- [x] **Step 3: Add docs-only skipped check test**

Repeat the skipped behavior for `mode="check"`.

Expected:

- no workflow checks;
- no agent checks;
- no skill distribution checks;
- return code is `0`.

- [x] **Step 4: Add single-skill incremental fix test**

Create two canonical skill fixtures:

- `skills/demo-skill/SKILL.md`
- `skills/other-skill/SKILL.md`

Call incremental fix with changed files:

- `skills/demo-skill/SKILL.md`

Expected:

- exactly three `install_skill.py` commands for `demo-skill`, one per skill target;
- no `install_skill.py` commands for `other-skill`;
- no `setup_agents.py` commands;
- no `sync_templates.py` commands.

- [x] **Step 5: Add multi-skill incremental fix test**

Call incremental fix with changed files:

- `skills/demo-skill/SKILL.md`
- `skills/other-skill/templates/foo.md`

Expected:

- install commands only for `demo-skill` and `other-skill`;
- each affected skill is installed to all three skill targets;
- no unrelated skill is installed.

- [x] **Step 6: Add skill-scoped check test**

Call incremental check with changed files:

- `skills/demo-skill/scripts/tool.py`

Expected:

- one `check_skill_distribution.py` command;
- command includes `--skills demo-skill`;
- no agent or workflow commands.

- [x] **Step 7: Add agent-only fix and check tests**

Call incremental fix with changed files:

- `agents/implement-agent.md`

Expected:

- three `setup_agents.py --force` commands, one per agent target;
- no skill install commands;
- no workflow commands.

Call incremental check with changed files:

- `agents/config/model-profiles.yaml`

Expected:

- three `setup_agents.py --check` commands;
- no skill check commands;
- no workflow commands.

- [x] **Step 8: Add workflow-only fix and check tests**

Call incremental fix with changed files:

- `.ai/workflows/scripts/workflow.py`

Expected:

- `sync_templates.py --root <root>` default sync command;
- `sync_templates.py --root <root> --distribute` command;
- no agent setup commands;
- no skill install commands.

Call incremental check with changed files:

- `.ai/workflows/definitions/sdlc-main.yaml`

Expected:

- `sync_templates.py --check`;
- `sync_templates.py --check-distributed`;
- no agent checks;
- no skill checks.

- [x] **Step 9: Add sync-rule full-fallback test**

Call incremental fix with changed files:

- `scripts/sync_derived_artifacts.py`

Expected:

- behavior falls back to full `_fix_steps` composition;
- report scope is `full` with a reason such as sync-rule change;
- all current full-mode command categories are present.

- [x] **Step 10: Add Git changed-file discovery test**

Mock subprocess calls for Git discovery and verify `--changed-files-from-git` collects both:

- paths from `git diff --name-only HEAD`;
- paths from `git ls-files --others --exclude-standard`.

Expected:

- duplicate paths are de-duplicated;
- returned paths are sorted or otherwise deterministic;
- non-zero Git discovery returns a clear error when discovery was explicitly requested.

- [x] **Step 11: Run focused tests and confirm expected failures**

Run:

    python3 -m pytest tests/test_sync_derived_artifacts.py -v

Expected before implementation:

- existing tests pass;
- newly added incremental tests fail for missing API/options/behavior.

Do not weaken the assertions to match the current full-sync behavior.

---

## Task 2: Implement Changed-File Classification

**Files:**
- Modify: `scripts/sync_derived_artifacts.py`

**Purpose:** Add a deterministic classification layer that maps repository-relative paths to affected sync domains.

- [x] **Step 1: Add an affected-domain data structure**

Use a small stdlib-only structure, such as a dataclass or plain dict, with these logical fields:

- `workflows: bool`
- `agents: bool`
- `skills: set[str]`
- `full: bool`
- `skipped_paths: list[str]`
- `reason: str | None`

Keep the public JSON representation serializable and deterministic.

- [x] **Step 2: Add path normalization helper**

Normalize changed paths by:

- replacing backslashes with slashes;
- stripping whitespace;
- removing leading `./`;
- ignoring empty paths.

Do not resolve paths against the filesystem; classification should work for deleted files too.

- [x] **Step 3: Classify skill paths**

Map paths matching `skills/<skill-name>/...` to `affected.skills.add(<skill-name>)`.

Rules:

- require a non-empty second path segment;
- ignore bare `skills/` without a skill name;
- preserve exact skill directory name.

- [x] **Step 4: Classify agent paths**

Set `affected.agents = True` for:

- `agents/*.md`
- `agents/config/...`

Do not classify generated `.opencode/agents/...`, `.claude/agents/...`, or `.cursor/agents/...` as canonical agent changes.

- [x] **Step 5: Classify workflow governed files**

Set `affected.workflows = True` for exactly:

- `.ai/workflows/scripts/workflow.py`
- `.ai/workflows/definitions/sdlc-main.yaml`

Do not classify workflow run history under `.ai/workflows/runs/...` as workflow template changes.

- [x] **Step 6: Classify sync-rule fallback files**

Set `affected.full = True` and record a reason when changed paths include sync/install/check rule files such as:

- `scripts/sync_derived_artifacts.py`
- `scripts/setup_agents.py`
- `scripts/install_agents.py`
- `scripts/activate_agents_config.py`
- `skills/meta-skill-lifecycle-governance/scripts/install_skill.py`
- `skills/meta-skill-lifecycle-governance/scripts/check_skill_distribution.py`
- `skills/sdlc-project-bootstrap/scripts/sync_templates.py`

When `full` is true, suite construction should use existing full check/fix behavior.

- [x] **Step 7: Record ignored paths**

For paths that do not affect derived artifacts, append the normalized path to `skipped_paths`.

Examples:

- docs files;
- tests files;
- memory files;
- workflow run history files;
- README-only changes.

---

## Task 3: Add Incremental Suite Construction

**Files:**
- Modify: `scripts/sync_derived_artifacts.py`

**Purpose:** Build only the required check/fix command suites from the affected-domain result.

- [x] **Step 1: Refactor `_check_suites` to support selected domains**

Keep the existing full behavior available.

Add either a new function or optional parameters so incremental check can compose:

- workflow check suites only when `affected.workflows` is true;
- agent check suites only when `affected.agents` is true;
- skill check suite only when `affected.skills` is non-empty.

For skill check, pass the existing lower-level filter:

    --skills <comma-separated-sorted-skill-names>

- [x] **Step 2: Refactor `_fix_steps` to support selected domains**

Keep current full behavior when called without incremental scope.

Add either a new function or optional parameters so incremental fix can compose:

- workflow sync/distribute only when `affected.workflows` is true;
- agent force setup only when `affected.agents` is true;
- skill install only for `affected.skills`.

Use explicit semantics:

- `skills is None` means full all-skill install;
- `skills == set()` means install no skills;
- `skills == {"demo-skill"}` means install only that skill.

- [x] **Step 3: Validate affected skill directories during fix**

When an affected skill no longer exists because it was deleted or renamed, do not blindly call `install_skill.py` against a missing source directory.

Recommended behavior:

- for deleted canonical skill, return blocked/error unless deletion distribution semantics are explicitly implemented;
- include the missing skill name in the report;
- do not silently succeed.

This keeps the first implementation focused on changed/added/modified skills, not deletion cleanup.

- [x] **Step 4: Implement skipped mode**

If incremental mode has:

- `full == False`;
- `workflows == False`;
- `agents == False`;
- `skills` empty;

then return success with no subprocess calls.

JSON report should use `scope: skipped` and include `skipped_paths`.

Plain-text output should say no derived-artifact domains are affected.

- [x] **Step 5: Implement mixed-domain mode**

If a change set includes multiple affected domains, compose all relevant suites without falling back to full unless `affected.full` is true.

Example:

- `skills/demo-skill/SKILL.md` plus `agents/review-agent.md`
  - install/check `demo-skill` only;
  - run agent setup/check;
  - do not run workflow suites.

---

## Task 4: Add CLI Options and Git Discovery

**Files:**
- Modify: `scripts/sync_derived_artifacts.py`

**Purpose:** Expose incremental behavior to workflow wrappers and local users without breaking existing callers.

- [x] **Step 1: Add CLI options**

Add parser options:

- `--changed-files-from-git`, boolean;
- `--changed-file`, repeatable append option;
- optional `--full`, boolean alias for explicit full behavior.

Validation rules:

- `--check` and `--fix` remain mutually exclusive.
- Existing call shape with no changed-file options remains full behavior.
- `--full` must not be combined with changed-file options unless it intentionally overrides them with a clear message.

- [x] **Step 2: Add Git changed-file discovery helper**

When `--changed-files-from-git` is set, collect changed files with commands equivalent to:

    git -C <root> diff --name-only HEAD
    git -C <root> ls-files --others --exclude-standard

Rules:

- include staged and unstaged tracked changes via `git diff --name-only HEAD`;
- include untracked files via `git ls-files --others --exclude-standard`;
- de-duplicate paths;
- make output deterministic;
- if a Git command fails, return a clear error and non-zero exit because discovery was explicitly requested.

- [x] **Step 3: Update `run_aggregate` signature**

Extend `run_aggregate` to accept optional changed-file data for tests and wrappers.

Suggested shape:

- `changed_files: list[str] | None = None`
- `incremental: bool = False`

Semantics:

- `incremental=False` and `changed_files=None`: full current behavior;
- `incremental=True`: classify `changed_files` and build selected suites;
- `changed_files` supplied by tests should not require Git.

- [x] **Step 4: Update JSON reporting**

For all modes, JSON report should include:

- `mode`;
- `scope`;
- `status`;
- `returncode`;
- `affected` when incremental classification was used;
- `suites`.

Preserve existing `suites` fields for command results.

- [x] **Step 5: Update plain-text reporting**

Keep existing full-mode plain text stable.

For incremental mode:

- selected suites: print selected domains and suite count;
- skipped: print a concise skipped message;
- full fallback: print that sync-rule changes selected full mode.

---

## Task 5: Verify Incremental Behavior

**Files:**
- Modify if needed: `tests/test_sync_derived_artifacts.py`
- Modify if needed: `scripts/sync_derived_artifacts.py`

**Purpose:** Complete red/green loop and verify no compatibility regression.

- [x] **Step 1: Run focused aggregate tests**

Run:

    python3 -m pytest tests/test_sync_derived_artifacts.py -v

Expected:

- all old full-mode tests pass;
- all new incremental tests pass.

- [x] **Step 2: Run related regression tests**

Run likely affected suites:

    python3 -m pytest tests/test_wrapper_contracts.py -v
    python3 -m pytest tests/test_agent_config_lib.py -v
    python3 -m pytest tests/test_install_agents.py -v
    python3 -m pytest tests/test_activate_agents_config.py -v
    python3 -m pytest tests/test_setup_agents.py -v
    python3 -m pytest tests/test_project_bootstrap_skills.py -v

Expected:

- no regressions in agent install/activation or wrapper contracts.

- [x] **Step 3: Run full project regression**

Run:

    python3 -m pytest tests/ -v

Expected:

- full test suite passes.

If failures are unrelated/pre-existing, document exact failing commands, failing tests, and evidence in the implement-agent handoff. Do not mark the task complete without clear blocked evidence.

- [x] **Step 4: Smoke-test skipped mode locally**

With only docs/spec/plan changes present, run:

    python3 scripts/sync_derived_artifacts.py --fix --changed-file docs/superpowers/specs/example.md --json

Expected:

- return code `0`;
- no subprocess suites;
- `scope` is `skipped`;
- no `.skill-install.json` churn.

- [x] **Step 5: Smoke-test single-skill mode locally**

Use a real changed skill path, or a temporary controlled fixture if appropriate:

    python3 scripts/sync_derived_artifacts.py --fix --changed-file skills/<skill-name>/SKILL.md --json

Expected:

- only that skill is installed to skill targets;
- unrelated skills are not installed.

- [x] **Step 6: Smoke-test Git discovery mode**

Run from a controlled worktree with known changed paths:

    python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git --json

Expected:

- changed tracked and untracked files are classified correctly;
- selected domains match the actual working tree.

---

## Task 6: Update Workflow Usage Guidance

**Files:**
- Modify if appropriate: `AGENTS.md`
- Modify if appropriate: relevant agent prompt or workflow wrapper documentation

**Purpose:** Make future agents use the incremental mode for normal finishing/sync checks, while preserving full mode for lifecycle hardening or sync-rule changes.

- [x] **Step 1: Document normal usage**

Add guidance that normal finish/drift checks should prefer:

    python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git
    python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git

when the intent is to sync only derived artifacts affected by the current change set.

- [x] **Step 2: Document full usage**

Document that plain full mode remains appropriate for:

- lifecycle hardening;
- sync-rule script changes;
- install/check script changes;
- intentional repository-wide drift repair.

Commands:

    python3 scripts/sync_derived_artifacts.py --check
    python3 scripts/sync_derived_artifacts.py --fix

- [x] **Step 3: Avoid broad bash fallback changes**

Do not solve this by opening broad shell permissions. The implementation should be native Python and existing allowlisted commands/scripts should remain sufficient.

---

## Task 7: Final Evidence and Handoff

**Files:**
- Modify if needed: implementation handoff artifact under workflow run directory
- Read: this plan

**Purpose:** Produce auditable completion evidence.

- [x] **Step 1: Record changed files**

Implementation handoff should list changed files, expected categories:

- `scripts/sync_derived_artifacts.py`
- `tests/test_sync_derived_artifacts.py`
- optional documentation/prompt files if Task 6 is implemented
- generated derived files only if relevant domains were actually affected

- [x] **Step 2: Record verification commands**

Handoff must include exact commands and pass/fail/blocked results for:

- focused aggregate sync tests;
- related regression tests;
- full project regression;
- incremental skipped smoke test;
- single-skill or Git discovery smoke test when practical.

- [x] **Step 3: Validate plan checkbox discipline**

When implementation is complete, check off completed steps and run the repository checkbox validator for this plan:

    python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-05-incremental-derived-artifact-sync-filtering.md

Expected:

- `ok: all checkboxes complete`

Only report `tasks_complete: true` after the plan checkbox validator passes, or return blocked with the exact reason.
