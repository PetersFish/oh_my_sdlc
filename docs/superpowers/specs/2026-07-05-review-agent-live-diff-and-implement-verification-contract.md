# Review Agent Live Diff And Implement Verification Contract Spec

## Purpose

Harden the `implement-agent` -> `review-agent` apply-change handoff so code review is based on the actual live implementation diff, while keeping executable regression ownership in `implement-agent` instead of duplicating broad verification in `review-agent`.

The change should make `implement-agent` deliver a complete, auditable change set and verification evidence; make `dev-orchestrator` forward that evidence as the review target; and make `review-agent` validate the live Git change set, review the patch, and inspect verification evidence before approving phase completion.

## Context

The repository uses a governed SDLC lifecycle with `dev-orchestrator` dispatching specialized subagents. During `apply_change`, `implement-agent` performs implementation and verification, then `review-agent` decides whether the phase can complete.

A recent lightweight-flow review exposed two workflow weaknesses:

- `review-agent` saw `git diff --stat` output but did not establish a complete live change set before reviewing. It moved into CodeGraph and hotspot file reads, which can miss untracked files, staged files, or unindexed new files.
- `review-agent` re-ran broad regression commands that `implement-agent` should already have run, turning review into duplicate verification while leaving the actual patch boundary under-specified.

Current agent contracts do not require `implement-agent` to return `changed_files`, `worktree_path`, or `diff_commands`, and the review dispatch prompt does not force `review-agent` to validate the live Git state against implement-agent handoff data.

## Problem

The apply-change review boundary is currently too implicit.

1. **Review scope can be incomplete.**
   `review-agent` may infer changed files from `git diff --stat`, CodeGraph, Grep, or known hotspots instead of a complete live Git change set. This risks missing untracked files, staged files, or worktree-local changes.

2. **CodeGraph can be used too early.**
   CodeGraph is useful for structural understanding, but it is not the source of truth for uncommitted code. It may not include new files or just-written changes.

3. **Verification ownership is blurred.**
   `implement-agent` should run focused tests and full project regression before reporting success. `review-agent` should inspect that evidence and only re-run tests when the evidence is missing, contradictory, stale, or review discovers a concrete risk.

4. **Review dispatch lacks a mandatory review target.**
   `dev-orchestrator` currently forwards workflow context and design artifacts, but not a structured changed-file contract that `review-agent` must validate and review.

5. **Final review envelopes can drift from the contract.**
   Review output must remain exactly one valid JSON object. Handoff markdown and final JSON must not be mixed in the final response.

## Goals

- Require `implement-agent` to include a structured implementation change set in its success output and handoff.
- Require `implement-agent` to run focused verification followed by full project regression before returning success, unless explicitly blocked or user-approved to skip.
- Require `dev-orchestrator` to forward implement-agent `changed_files`, `worktree_path`, `diff_commands`, and `verification_commands` to `review-agent` as the primary review target.
- Require `review-agent` to establish and validate the live Git change set before using CodeGraph for implementation review.
- Require `review-agent` to review every changed file in the live change set, including staged and untracked files.
- Make live Git diff the source of truth for uncommitted review scope.
- Make CodeGraph an auxiliary structural-understanding tool only after the live change set is known.
- Make `review-agent` inspect implement-agent verification evidence by default instead of re-running broad tests.
- Permit `review-agent` targeted test re-runs only under explicit conditions.
- Preserve review-agent ability to run minimal tests when evidence is incomplete or a concrete review concern requires executable confirmation.
- Ensure final review output is exactly one valid JSON object.

## Non-Goals

- Do not remove pytest permissions from `review-agent`; they remain useful for exception-path verification.
- Do not make `review-agent` responsible for fixing implementation failures.
- Do not make CodeGraph unavailable; constrain its role for uncommitted diff review.
- Do not introduce CI or change external automation in this spec.
- Do not require full regression for intentionally skipped or environment-blocked cases; those must return blocked evidence unless the user explicitly approves the skip.
- Do not directly edit `.opencode/agents/`, `.claude/agents/`, or `.cursor/agents/` as the source of truth; canonical changes belong under `agents/` and must be distributed afterward.

## Desired Lifecycle Model

```text
implement-agent
  -> discovers changed files from the live worktree
  -> implements and updates tests
  -> runs focused tests until green
  -> runs full project regression before success
  -> returns changed_files + worktree_path + diff_commands + verification_commands

review-agent
  -> validates live Git change set against implement-agent handoff
  -> reviews unstaged, staged, and untracked files from the live change set
  -> uses CodeGraph only for surrounding structure after diff scope is known
  -> inspects implement-agent verification evidence by default
  -> re-runs only minimal targeted tests when justified
  -> returns one valid JSON acceptance/blocker envelope
```

## Design

### 1. Implement-Agent Change-Set Handoff Contract

`implement-agent` success output must include a structured change-set contract under `artifacts`.

Required artifact fields:

```json
{
  "worktree_path": "<absolute-or-repo-relative-worktree-path>",
  "repo_root": "<absolute-or-repo-relative-repo-root>",
  "base_ref": "HEAD",
  "changed_files": [
    {
      "path": "scripts/example.py",
      "status": "added|modified|deleted|renamed|untracked|staged",
      "source": "git diff|git diff --cached|git ls-files --others",
      "reason": "why this file changed",
      "covered_by": ["python3 -m pytest ..."]
    }
  ],
  "diff_commands": [
    "git diff -- scripts/example.py",
    "git diff --cached -- scripts/example.py"
  ],
  "verification_commands": [
    {
      "command": "python3 -m pytest tests/example_test.py -v",
      "scope": "focused|affected|full_regression|sync|plan_checkbox",
      "result": "pass|fail|not_run|blocked",
      "covers": ["scripts/example.py"]
    }
  ],
  "raw_log_paths": []
}
```

Rules:

- If implementation changed files, `changed_files` must be non-empty.
- If `changed_files` is empty for a behavior-changing task, `implement-agent` must return blocked.
- If a file is untracked, it must appear in `changed_files` with `source: git ls-files --others` or equivalent wording.
- If a file is staged, it must appear with a staged status/source and a cached diff command.
- If a git worktree is used, `worktree_path` must identify the exact worktree where changes were made.
- `verification_commands` must include all focused commands that proved the implemented behavior and the full regression command result.

### 2. Implement-Agent Full Regression Gate

After focused verification passes, `implement-agent` must run the repository-level full regression suite before returning success.

Default repository command:

```bash
python3 -m pytest tests/ -v
```

Rules:

- Do not return `status: success` until focused verification and full regression both pass.
- If full regression fails because of the current change, continue the implement loop and fix it.
- If full regression fails for a pre-existing, unrelated, or environment-related reason, return `status: blocked` with the failing command, failing tests, and recommended next action.
- If full regression is intentionally skipped, return `status: blocked` unless the user explicitly approved the skip.
- Include the full regression result in `artifacts.verification_commands` with `scope: full_regression`.

### 3. Dev-Orchestrator Review Dispatch Contract

When dispatching `review-agent` after successful `implement-agent`, `dev-orchestrator` must forward the implement-agent change-set and verification evidence as the exact review target.

The review dispatch prompt must instruct `review-agent` to:

- Use the implement-agent `changed_files` as the primary review target.
- Verify the current worktree matches `worktree_path` before reviewing.
- Verify the live Git changed-file set matches or explains the handoff changed-file set.
- Return blocker `review_change_set_missing` when change-set data is absent or empty for an implementation task.
- Return blocker `review_change_set_mismatch` when the live Git state contradicts the handoff.
- Inspect implement-agent verification evidence before deciding whether any test re-run is necessary.
- Avoid broad test re-runs by default.

### 4. Review-Agent Live Change Review Protocol

`review-agent` must establish the live review scope before CodeGraph usage.

Required discovery commands:

```bash
git status --short --branch
git diff --name-status
git diff --cached --name-status
git ls-files --others --exclude-standard
git diff --stat
git diff --cached --stat
```

Review rules:

- Use `git diff -- <path>` for unstaged tracked changes.
- Use `git diff --cached -- <path>` for staged changes.
- Use `Read` for untracked files discovered by `git ls-files --others --exclude-standard`.
- Review every changed file in the final live change set unless it is explicitly generated/derived and covered by an agreed lifecycle boundary.
- CodeGraph may be used only after the live change set is known.
- If CodeGraph disagrees with live Git, trust live Git for review scope.
- If no changed files are found but implement-agent reported implementation changes, return blocker `review_change_set_missing`.

### 5. Review-Agent Verification Reuse Protocol

`review-agent` is not the primary test executor.

Default behavior:

- Inspect implement-agent verification evidence first.
- Do not re-run focused tests that implement-agent already ran and reported passing.
- Do not run broad regression suites by default.
- Do not run full `tests/` by default.
- Do not run derived-artifact sync checks by default unless the changed files or plan requirements make that evidence necessary and implement-agent did not provide it.

`review-agent` may run tests only when one of these conditions is true:

1. implement-agent evidence is missing, incomplete, stale, or contradictory;
2. changed files are not covered by implement-agent verification evidence;
3. review identifies a concrete code risk that needs executable confirmation;
4. the implementation modifies test infrastructure, workflow dispatch, wrapper contracts, or verification tooling and evidence is insufficient;
5. the user explicitly asks review-agent to re-run verification;
6. a lightweight targeted smoke test is necessary before approval.

When re-running tests:

- Run the smallest command set that answers the review question.
- Prefer one targeted command over broad regression.
- Record why each re-run was necessary in the review handoff.
- If broad regression is needed, record the trigger explicitly.

### 6. Review-Agent Git Permission Additions

`review-agent` needs enough read-only Git access to discover live changed files.

Required bash allow rules:

```yaml
"git status*": allow
"git diff*": allow
"git log*": allow
"git ls-files*": allow
"git check-ignore*": allow
"git worktree*": allow
```

These rules must remain after the catch-all deny rule under the repository's last-match-wins permission convention.

### 7. Final JSON Output Contract

`review-agent` final output must be exactly one valid JSON object.

Rules:

- Do not include Markdown outside the final JSON object.
- Do not include handoff prose in the final response.
- If writing a handoff artifact, write Markdown to the artifact file only.
- `artifacts.design_artifact_paths` must be a JSON array.
- `artifacts.raw_log_paths` must be a JSON array.
- `blockers` must be a JSON array.
- `recommended_next_action` must match the allowed enum.

## Testing Requirements

Add or update tests that verify:

- `review-agent` bash permissions include `git ls-files*`, `git check-ignore*`, and `git worktree*` after the catch-all deny.
- `review-agent` prompt contains a Live Change Review Protocol.
- `review-agent` prompt states that live Git is the source of truth for uncommitted review scope.
- `review-agent` prompt states that CodeGraph may be used only after the live change set is known.
- `review-agent` prompt contains a Verification Reuse Protocol.
- `review-agent` prompt states that broad regression is not rerun by default.
- `implement-agent` prompt contains the Full Regression Gate and default full regression command.
- `implement-agent` output contract includes `changed_files`, `worktree_path`, `diff_commands`, and `verification_commands`.
- `dev-orchestrator` prompt forwards implement-agent change-set data to review-agent and names `review_change_set_missing` / `review_change_set_mismatch` blockers.
- final review output contract requires exactly one valid JSON object and array-valued `design_artifact_paths`.

## Acceptance Criteria

- `implement-agent` cannot report success for code changes without structured changed-file and verification evidence.
- `implement-agent` full regression is part of normal success evidence.
- `dev-orchestrator` review dispatch includes implement-agent change-set and verification evidence.
- `review-agent` validates live Git scope before CodeGraph-assisted review.
- `review-agent` can discover unstaged tracked, staged, and untracked files.
- `review-agent` reviews patch/file content for every changed file in scope.
- `review-agent` does not default to re-running full regression when implement-agent already provided passing evidence.
- `review-agent` still has permission and guidance for targeted verification re-runs when justified.
- canonical `agents/` updates are synced into `.opencode/`, `.claude/`, and `.cursor/` derived copies.
- focused prompt-contract tests and agent sync checks pass.
