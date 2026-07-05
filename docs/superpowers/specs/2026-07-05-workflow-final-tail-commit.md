# Workflow Final Tail Commit Spec

## Purpose

Ensure governed SDLC workflows can complete with a deterministic post-done governance-artifact commit or safe noop after all lifecycle state transitions, hook completions, and active-to-history artifact moves are finished.

This spec owns only the `workflow.py final-commit` runtime tail command and its safe Git staging/push behavior. Finish-stage ownership, branch decisions, and finish-agent terminal boundaries are owned by `2026-07-05-finish-agent-branch-decision-and-terminal-ownership`.

## Context

The workflow runtime continues to write governance artifacts after lifecycle agents return. These writes include `run.json`, hook state, handoff/history artifacts, `.ai/workflows/runs/current.json`, roadmap or memory artifacts, and the active-to-history run move.

A final Git publishing step is needed after the run is already done so those governance artifacts can be committed deterministically without staging unrelated user or implementation work.

This spec depends on the finish lifecycle spec to ensure finish-agent evidence has already been recorded and terminal ownership has already been resolved before `final-commit` runs.

## Problem

The workflow needs a safe final governance-artifact publisher.

1. **Runtime writes final artifacts late.**
   `after-dispatch`, `complete-phase`, `complete-hook`, and `advance` can write or move workflow files before the run reaches done.

2. **The final dirty tree may be left to the user.**
   Files under `.ai/workflows/runs/history/`, `.ai/workflows/runs/current.json`, `.migrated`, handoffs, memory sync output, roadmap state, or archived spec artifacts may remain uncommitted.

3. **Broad `git add -A` would be unsafe.**
   A naive final commit could accidentally stage unrelated local source changes, user scratch files, or work-in-progress outside workflow governance scope.

4. **dev-orchestrator should remain a routing coordinator.**
   It should not gain direct `git add`, `git commit`, or `git push` responsibility. Git publishing should be exposed through a deterministic workflow runtime command.

## Goals

- Add a deterministic `workflow.py final-commit` command that runs only after the workflow run is done.
- Make final commit/push happen after `after-dispatch`, `complete-phase`, `complete-hook`, `advance`, and active-to-history movement.
- Preserve `dev-orchestrator` as a routing coordinator that calls allowed workflow runtime commands rather than direct Git commands.
- Stage only an allowlisted set of workflow/governance artifacts.
- Report unrelated residual dirty files without staging or committing them.
- Return structured JSON for success, noop, or failure.
- Update `dev-orchestrator` prompt so it captures `run_id` before pointer cleanup and invokes the final tail commit after done.
- Add tests proving final commit behavior, allowlist safety, noop behavior, and push behavior.
- Sync canonical changes into derived workflow template and dev-orchestrator copies.

## Non-Goals

- Do not define finish-agent terminal ownership, branch decision gates, or finish-agent final evidence rules; those belong to `2026-07-05-finish-agent-branch-decision-and-terminal-ownership` and `2026-07-05-workflow-runtime-execution-context-and-agent-result-integrity`.
- Do not update finish-agent prompt in this spec except where generated sync requires non-substantive propagation from other specs.
- Do not let `dev-orchestrator` run raw `git add`, `git commit`, or `git push`.
- Do not use `git add -A` or stage the entire repository.
- Do not commit allowlist-external dirty files.
- Do not change the SDLC phase model or phase names.
- Do not introduce external CI/CD automation.
- Do not make final-commit responsible for deciding whether implementation code is correct; that remains implement/review responsibility.

## Desired Lifecycle Model

```text
finish lifecycle and runtime evidence invariants completed by dependent specs
  -> dev-orchestrator captures run_id before pointer cleanup
  -> workflow.py complete-phase / complete-hook as needed
  -> workflow.py advance until done
  -> workflow.py final-commit --run-id <captured_run_id> --push
  -> final git status is clean or residual_dirty_paths are reported
```

The final commit is a post-done tail operation owned by `workflow.py final-commit`.

## Design

### 1. Final Commit Runtime Command

Add a new workflow runtime command:

```bash
python3 .ai/workflows/scripts/workflow.py --root . final-commit \
  --run-id <run_id> \
  --message "chore(workflow): finalize <run_id>" \
  --push
```

Arguments:

- `--run-id <run_id>`: required. Identifies the workflow run to finalize.
- `--message <message>`: optional. Defaults to `chore(workflow): finalize <run_id>`.
- `--push`: optional. Pushes only after a commit succeeds.

The command must be callable through the existing `python3 .ai/workflows/scripts/workflow.py *` permission boundary.

### 2. Completion Preconditions

`final-commit` must verify that the run has reached a final state before staging anything.

Required checks:

- `.ai/workflows/runs/history/<run_id>/run.json` exists.
- The loaded `run.json` has `status == "done"` or `current_phase == "done"`.
- The run id in `run.json`, if present, matches `--run-id`.

If any check fails, return `status: "failed"` and do not stage files.

### 3. Stage Allowlist

`final-commit` must never run `git add -A`.

Initial allowlist:

```text
.ai/workflows/runs/history/<run_id>/
.ai/workflows/runs/current.json
.ai/roadmap/
.ai/memory/
openspec/changes/archive/
docs/superpowers/archive/
```

Rules:

- Stage only paths that exist and are dirty.
- Scope the workflow run history path to the specific `run_id`.
- Leave unrelated source, tests, docs, scratch files, and non-allowlisted paths unstaged.
- Report non-allowlisted dirty paths in `residual_dirty_paths`.

### 4. Structured Output Contract

`final-commit` must output exactly one JSON object.

Success example:

```json
{
  "status": "success",
  "run_id": "2026-07-05-example",
  "committed": true,
  "commit_id": "abc123",
  "pushed": true,
  "staged_paths": [
    ".ai/workflows/runs/history/2026-07-05-example/run.json"
  ],
  "residual_dirty_paths": []
}
```

Noop example:

```json
{
  "status": "noop",
  "reason": "nothing_to_commit",
  "run_id": "2026-07-05-example",
  "committed": false,
  "commit_id": null,
  "pushed": false,
  "staged_paths": [],
  "residual_dirty_paths": []
}
```

Failure example:

```json
{
  "status": "failed",
  "run_id": "2026-07-05-example",
  "committed": false,
  "commit_id": null,
  "pushed": false,
  "staged_paths": [],
  "residual_dirty_paths": ["src/unrelated.py"],
  "error": "run_not_done"
}
```

### 5. Git Operation Rules

`final-commit` must:

1. inspect dirty paths;
2. stage only allowlisted paths;
3. check staged diff;
4. return noop if staged diff is empty;
5. commit when staged diff exists;
6. obtain the resulting commit id;
7. push only when `--push` is provided and commit succeeded;
8. report residual dirty paths after the operation.

If `git push` fails after a successful commit, the output should report `status: "failed"`, `committed: true`, `pushed: false`, and the commit id.

### 6. Dev-Orchestrator Tail Commit Contract

Update `dev-orchestrator` so that, after the workflow is advanced to done, it invokes `workflow.py final-commit`.

Required prompt rules:

- Capture the active `run_id` before `advance` clears `.ai/workflows/runs/current.json`.
- Ensure finish lifecycle evidence has already been recorded according to the runtime context and finish lifecycle specs.
- Run `complete-phase`, `complete-hook`, and `advance` as required until the run is done.
- After the run is done, call `workflow.py final-commit --run-id <captured_run_id> --push`.
- Run `git status --short` after final-commit and report either clean state or residual dirty files.
- Do not run direct `git add`, `git commit`, or `git push` from `dev-orchestrator`.

### 7. Canonical and Derived File Sync

Canonical sources must be updated first, then derived copies synchronized.

Expected canonical files:

- `.ai/workflows/scripts/workflow.py`
- `.ai/workflows/definitions/sdlc-main.yaml` if command documentation or lifecycle metadata requires it
- `agents/dev-orchestrator.md`
- `tests/test_workflow.py`
- relevant prompt-contract tests if command/prompt behavior is asserted there

Expected derived/template files:

- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `skills/sdlc-project-bootstrap/templates/workflow/sdlc-main.yaml` if touched
- `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.opencode/agents/dev-orchestrator.md`
- `.claude/agents/dev-orchestrator.md`
- `.cursor/agents/dev-orchestrator.md`

## Testing Requirements

Add or update tests that verify:

- `final-commit` rejects a missing run id.
- `final-commit` rejects a run that is not in history or not done.
- `final-commit` returns noop when there are no allowlisted staged changes.
- `final-commit` commits dirty files under `.ai/workflows/runs/history/<run_id>/`.
- `final-commit` can commit allowlisted governance archive paths such as `docs/superpowers/archive/` without staging unrelated files.
- `final-commit` does not stage allowlist-external dirty files.
- `final-commit` reports allowlist-external files in `residual_dirty_paths`.
- `final-commit --push` invokes push only after a successful commit.
- `final-commit --push` does not invoke push on noop.
- `dev-orchestrator` prompt includes the Final Tail Commit Protocol and captures `run_id` before pointer cleanup.
- derived workflow template and dev-orchestrator sync checks pass.

## Acceptance Criteria

- A completed workflow run can be advanced to done and then finalized with one deterministic final commit or a noop.
- Files written after lifecycle agents return are included in the final workflow artifact commit when they are inside the allowlist.
- `dev-orchestrator` does not need direct Git write permissions.
- `final-commit` never stages unrelated dirty files.
- Residual dirty files outside the allowlist are reported instead of silently committed.
- `--push` only runs after a successful commit.
- Final user-facing status can accurately say the repository is clean or list residual dirty paths.
- Focused workflow tests and full test suite pass.
