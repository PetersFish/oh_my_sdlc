---
name: meta-skill-lifecycle-governance
description: Govern the lifecycle of personal AI skills across development, repo evaluation, project pilots, project-originated iteration, backporting, release, and multi-CLI distribution. Use this skill when the user wants to create, improve, pilot, release, distribute, or backport a skill, especially when the work spans a canonical skill repo and real project usage.
---

# Skill Lifecycle Governance

Use this skill to orchestrate the full lifecycle of a personal AI skill.

## Core idea

Keep the skill repo canonical. Allow project-local iteration when real usage exposes gaps. Promote only reviewed generic improvements back into the skill repo.

## When to use

- Developing a new skill in the canonical repo.
- Evaluating a skill in-repo before release.
- Piloting a candidate skill in a real project.
- Improving a stable skill from project feedback.
- Preparing a backport candidate.
- Releasing a stable version.
- Distributing a stable skill to Claude Code, OpenCode, Codex, Cursor, or Gemini CLI.
- Deciding whether a change belongs in the skill repo or only in a project overlay.

## Lifecycle actions

### DEVELOP

- Create or modify the skill in the canonical repo.
- Keep the repo as the source of truth.
- Use `skill-creator` for drafting individual skills when the content itself is still being formed.

### EVALUATE-IN-REPO

- Validate action routing, safety boundaries, examples, metadata, and output shape inside the canonical repo.
- Run the local evaluation loop before release.

### PILOT-IN-PROJECT

- Copy a candidate skill into a real project for validation.
- Write install metadata and keep the candidate status explicit.
- Treat feedback from this phase as a release gate, not a release.

### ITERATE-FROM-PROJECT

- Start from an installed stable skill when the user discovers missing behavior during project use.
- Keep the current project context intact.
- Mark the workspace as a local iteration, not canonical truth.

### BACKPORT

- Classify project-local changes before promoting them.
- Promote only generic improvements into the skill repo.
- Keep project overlays and temporary workarounds out of the stable skill by default.

### RELEASE

- Update version metadata and changelog notes.
- Require repo-side evaluation before the skill becomes stable.
- Create or tag a stable ref only after confirmation.

### DISTRIBUTE

- Install stable releases to the selected AI CLI targets.
- Verify the installed version or source ref where possible.
- Default to stable refs, not candidate refs.

## Decision rules

- If feedback appears in a project, prefer local iteration there first.
- If a change is project-specific, keep it in a project overlay.
- If a change is generic, backport it to the skill repo.
- If a release is requested without repo-side evaluation, warn first.
- If marketplace or plugin publication is requested, treat it as a separate explicit path.

## Scripted helpers

Use the bundled scripts for repetitive mechanical work:

- `scripts/install_skill.py` for pilot or stable installs.
- `scripts/compare_skill_copy.py` for diffs between repo and project copies.
- `scripts/prepare_backport.py` for backport classification and review material.
- `scripts/verify_install.py` for install-target checks and metadata validation.

## Output discipline

- Explain the selected lifecycle action before making changes.
- Ask for confirmation before destructive installs, overwrites, or tag creation.
- Record metadata so installed copies can be traced back to their source ref.

## References

- `references/lifecycle-actions.md`
- `references/cli-targets.md`
- `references/backport-classification.md`
- `templates/install-metadata.yaml`
- `templates/release-notes.md`
- `templates/backport-review.md`
