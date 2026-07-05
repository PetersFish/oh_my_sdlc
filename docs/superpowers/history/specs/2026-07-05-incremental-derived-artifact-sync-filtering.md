# Incremental Derived Artifact Sync Filtering Spec

## Purpose

Make `scripts/sync_derived_artifacts.py` avoid unnecessary derived-artifact churn by synchronizing only the domains affected by the current change set.

The immediate problem is that drift detection and sync can currently refresh skill distribution metadata even when the current work does not modify any canonical skill. This creates noisy `.skill-install.json` files under `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/`, making review harder and increasing the risk that unrelated generated files enter commits.

## Context

`sync_derived_artifacts.py` is the repository-level aggregate entrypoint for derived artifacts. It composes workflow template sync, workflow template distribution, agent setup, and skill distribution checks/fixes.

The current `--fix` behavior is intentionally broad:

- sync live workflow files into canonical workflow templates;
- distribute canonical workflow templates into project-level skill copies;
- force-install and activate canonical agents into project-level targets;
- reinstall every canonical skill into `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/`.

This was safe for lifecycle hardening, but it is too coarse for normal iterative work. The skill install path rewrites `.skill-install.json` metadata, so a run caused by unrelated docs, tests, workflow history, or memory changes can create many unrelated generated files.

## Problem

The aggregate sync command lacks change-set awareness.

1. **Unrelated changes trigger skill distribution writes.**
   A change under docs, tests, workflow run history, memory, or other non-source areas can still cause all skills to be reinstalled.

2. **Single-skill changes trigger all-skill reinstall.**
   When only `skills/foo/...` changes, the current fix path reinstalls every canonical skill instead of only `foo`.

3. **Review diffs become noisy.**
   Unrelated `.skill-install.json` churn hides the actual implementation diff and makes review-agent/live-diff review less precise.

4. **Drift checks can block on unrelated domains.**
   If `--check` always checks all domains, an unrelated stale skill distribution can block a task that did not modify any skill.

5. **Current full-sync behavior is still needed sometimes.**
   Changes to sync scripts or installation rules should still support a conservative full sync/check path.

## Goals

- Add changed-file aware filtering to `scripts/sync_derived_artifacts.py`.
- Allow callers to run incremental `--check` and `--fix` based on the current Git worktree change set.
- Skip all derived sync/check work when the current change set does not affect canonical skills, canonical agents, governed workflow files, or sync/install rule files.
- When only one canonical skill changes, reinstall/check only that skill.
- When canonical agents change, run only agent distribution/activation checks or fixes.
- When governed workflow files change, run only workflow template sync/distribution checks or fixes.
- Preserve an explicit full-sync/full-check fallback for sync-script or install-rule changes.
- Preserve existing default full behavior unless an incremental mode is explicitly requested.
- Emit clear JSON/plain-text reports showing skipped domains and selected domains.

## Non-Goals

- Do not change `install_skill.py` metadata schema.
- Do not remove `.skill-install.json`; it remains valid distribution metadata.
- Do not modify generated `.opencode/`, `.claude/`, or `.cursor/` files directly by hand.
- Do not change the source-of-truth layout for canonical skills or agents.
- Do not add broad shell fallback permissions such as `find`, `cat`, `head`, `sed`, `awk`, or pipelines.
- Do not replace existing full `--check` / `--fix` behavior for callers that intentionally want a full run.
- Do not introduce external dependencies.

## Affected Domains

### Skill domain

Affected when a changed file is under:

- `skills/<skill-name>/...`

Behavior:

- Incremental check should run skill distribution check only for affected skill names.
- Incremental fix should install only affected skill names into `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/`.
- If multiple skills changed, operate only on that set.

### Agent domain

Affected when a changed file is under:

- `agents/*.md`
- `agents/config/...`

Behavior:

- Incremental check should run agent setup checks for all configured agent targets.
- Incremental fix should run agent setup force install/activation for all configured agent targets.
- Agent setup remains target-wide because the existing setup pipeline manages prompt install plus activation configuration across target directories.

### Workflow template domain

Affected when a changed file is one of the governed live workflow files:

- `.ai/workflows/scripts/workflow.py`
- `.ai/workflows/definitions/sdlc-main.yaml`

Behavior:

- Incremental check should run workflow live-to-canonical check and distributed-template check.
- Incremental fix should run workflow live-to-canonical sync and distribution.

### Sync-rule domain

Affected when a changed file modifies the sync/install/check implementation itself, including at least:

- `scripts/sync_derived_artifacts.py`
- `scripts/setup_agents.py`
- `scripts/install_agents.py`
- `scripts/activate_agents_config.py`
- `skills/meta-skill-lifecycle-governance/scripts/install_skill.py`
- `skills/meta-skill-lifecycle-governance/scripts/check_skill_distribution.py`
- `skills/sdlc-project-bootstrap/scripts/sync_templates.py`

Behavior:

- Incremental mode should fall back to full check/fix.
- The report should say that full mode was selected because sync rules changed.

### Ignored domain

Examples:

- `docs/...`
- `tests/...`, unless test changes are accompanied by source-domain changes
- `.ai/workflows/runs/...`
- `.ai/memory/...`
- `.gitignore`
- README-only changes
- unrelated planning/spec artifacts

Behavior:

- Incremental check/fix should skip all derived-artifact suites.
- Return code should be zero.
- Report status should be `skipped` or `ok`, not `drift`.

## CLI Design

Add explicit incremental inputs without changing existing default behavior.

Recommended options:

- `--changed-files-from-git`
  - Collect changed paths from the current Git worktree.
  - Include tracked modified/staged changes and untracked files.
- `--changed-file <path>`
  - Repeatable manual changed-file input for tests and wrapper integrations.
- `--full`
  - Optional explicit full mode alias for clarity.
  - Existing `--check` / `--fix` without changed-file options should continue to behave as full mode.

Git collection should use repository-relative paths equivalent to:

- `git diff --name-only HEAD`
- `git ls-files --others --exclude-standard`

The command should fail with a clear error only if Git changed-file discovery was explicitly requested and cannot be performed.

## Internal Design

Introduce a small classification layer before suite construction.

Conceptual data model:

- `Affected.workflows: bool`
- `Affected.agents: bool`
- `Affected.skills: set[str]`
- `Affected.full: bool`
- `Affected.skipped_paths: list[str]`
- `Affected.reason: str | None`

Classification rules:

- Normalize paths to repository-relative POSIX form.
- Strip leading `./`.
- Ignore empty paths.
- Map `skills/<name>/...` to `skills.add(name)`.
- Map canonical agent paths to `agents = True`.
- Map governed live workflow files to `workflows = True`.
- Map sync-rule files to `full = True`.
- Everything else is ignored for derived-artifact sync purposes.

Suite construction rules:

- Full mode:
  - preserve current `_check_suites(root)` and `_fix_steps(root)` behavior.
- Incremental skipped mode:
  - return no suites;
  - report skipped paths/domains;
  - return success.
- Incremental skill-only mode:
  - check/fix only affected skills.
- Incremental agent-only mode:
  - check/fix only agents.
- Incremental workflow-only mode:
  - check/fix only workflow suites.
- Mixed mode:
  - compose the selected domain suites.

## Check Behavior

`check_skill_distribution.py` already supports `--skills` as a comma-separated filter. The aggregate script should pass that option when incremental mode has affected skills.

Expected examples:

- Changed `skills/demo-skill/SKILL.md`:
  - run `check_skill_distribution.py --root <root> --skills demo-skill`
- Changed `agents/review-agent.md`:
  - run `setup_agents.py --target <target> --check` for each agent target
- Changed `.ai/workflows/scripts/workflow.py`:
  - run `sync_templates.py --check`
  - run `sync_templates.py --check-distributed`
- Changed `docs/foo.md` only:
  - run no suites, report skipped

## Fix Behavior

Expected examples:

- Changed `skills/demo-skill/SKILL.md`:
  - run `install_skill.py --skill-name demo-skill` for each skill target
  - do not install unrelated skills
- Changed `agents/review-agent.md`:
  - run `setup_agents.py --force` for each agent target
  - do not install skills unless a skill also changed
- Changed `.ai/workflows/scripts/workflow.py`:
  - run `sync_templates.py --root <root>`
  - run `sync_templates.py --root <root> --distribute`
  - do not run agent setup unless agents also changed
  - do not run skill install unless skills also changed
- Changed `scripts/sync_derived_artifacts.py`:
  - fall back to full fix

## Reporting Contract

JSON reports should include enough detail for agents and tests to determine what happened.

Required fields:

- `mode`: `check` or `fix`
- `scope`: `full`, `incremental`, or `skipped`
- `status`: `ok`, `drift`, `skipped`, or `error`
- `returncode`
- `affected`
  - `workflows`
  - `agents`
  - `skills`
  - `full`
  - `skipped_paths`
- `suites`

Plain-text output should be concise:

- full: preserve current summary format;
- incremental with suites: state selected domains and suite count;
- skipped: state that no derived artifacts are affected by the current change set.

## Testing Requirements

Add or update tests in `tests/test_sync_derived_artifacts.py`.

Required cases:

- Full `--fix` without incremental inputs preserves existing all-skill behavior.
- Incremental fix with only `docs/foo.md` runs no suites and returns success.
- Incremental check with only `docs/foo.md` runs no suites and returns success.
- Incremental fix with `skills/demo-skill/SKILL.md` installs only `demo-skill` into all skill targets.
- Incremental check with `skills/demo-skill/SKILL.md` invokes `check_skill_distribution.py --skills demo-skill`.
- Incremental fix with multiple skill changes installs only those skills.
- Incremental fix with `agents/implement-agent.md` runs agent force setup only.
- Incremental check with `agents/config/model-profiles.yaml` runs agent checks only.
- Incremental fix with `.ai/workflows/scripts/workflow.py` runs workflow sync/distribute only.
- Incremental check with `.ai/workflows/definitions/sdlc-main.yaml` runs workflow checks only.
- Incremental mode with `scripts/sync_derived_artifacts.py` falls back to full behavior.
- `--changed-files-from-git` includes tracked and untracked files.
- JSON output includes `scope`, `affected`, and `suites`.

## Acceptance Criteria

- Running incremental fix for docs-only/test-only changes does not create or refresh `.skill-install.json` files.
- Running incremental fix for one changed skill refreshes only that skill's distributed copies.
- Running incremental check for one changed skill checks only that skill distribution.
- Running incremental fix for agent changes does not reinstall skills.
- Running incremental fix for governed workflow changes does not reinstall unrelated skills.
- Full `--check` and full `--fix` behavior remains available and compatible with existing callers.
- Sync-rule changes force full mode in incremental execution.
- The structured JSON report makes skipped and selected domains explicit.
- Focused tests for aggregate sync behavior pass.
