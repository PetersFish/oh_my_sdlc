## Context

The repository already has a deterministic SDLC workflow runtime in `.ai/workflows/scripts/workflow.py` and an `sdlc-main` workflow that coordinates OpenSpec, Roadmap, Memory, and EvalOps lifecycle phases. That runtime can enforce hooks once the orchestrator starts and advances a run, but it does not currently reconcile workflow governance when OpenSpec actions happen outside the orchestrator path.

The risky cases are narrow but high impact:

- An OpenSpec change is archived without a matching active run or completed workflow history run.
- An active workflow run retains unresolved `pending_hooks`, such as memory sync or roadmap completion, without the assistant noticing before returning control to the user.

Phase 1 targets OpenCode as the primary CLI. The governance logic should remain portable in `workflow.py`; the OpenCode plugin should be a thin adapter that triggers checks at safe times and presents actionable prompts.

## Goals / Non-Goals

**Goals:**

- Add a read-only `workflow.py governance-check` subcommand that detects dangling archives and unresolved pending hooks.
- Return structured JSON suitable for tests, OpenCode plugin parsing, and manual diagnosis.
- Treat active workflow runs and done workflow history runs as valid evidence for archived OpenSpec changes.
- Add deterministic tests for clean state, dangling archive, pending hooks, and combined findings.
- Add an OpenCode plugin that runs governance checks on `session.idle` and appends remediation prompts when findings block completion.
- Deduplicate prompt injection by finding identity so idle checks do not repeatedly inject the same remediation in a tight loop.
- Keep remediation manual and judgment-preserving: the assistant follows prompts, runs workers, and re-runs governance checks until `block=false`.

**Non-Goals:**

- Do not automatically mutate Roadmap, OpenSpec, Memory, EvalOps, or workflow state from `governance-check` or the plugin.
- Do not modify upstream `openspec-*` skills or the OpenSpec package.
- Do not add Claude Code or Cursor adapters in Phase 1.
- Do not create a broad policy engine beyond dangling archives and pending hooks.
- Do not use `file.watcher.updated` until idle-only behavior is validated.
- Do not guarantee OS/process exit or manual session switching will synchronously run remediation.

## Decisions

### Decision 1: Keep governance detection in `workflow.py`

`governance-check` will live in `.ai/workflows/scripts/workflow.py` and inspect repository state using the explicit `--root` argument already used by the workflow runtime.

Rationale: the diagnostic logic needs fixture-friendly tests and should be portable across CLIs. Keeping it in Python avoids duplicating archive/run matching logic in TypeScript plugin code.

Alternatives considered:

- Plugin-only detection: rejected because it would make governance behavior OpenCode-specific and harder to test with workflow fixtures.
- OpenSpec skill modification: rejected because upstream OpenSpec workers are not workflow lifecycle owners.

### Decision 2: Return a structured blocking diagnostic contract

The command will return JSON shaped for adapters:

```json
{
  "block": true,
  "findings": [
    {
      "type": "dangling_archive",
      "change_id": "demo-change",
      "archive_path": "openspec/changes/archive/2026-06-20-demo-change",
      "message": "Archived OpenSpec change has no matching workflow run.",
      "remediation": "Resume SDLC governance for this archived change, run required post-archive hooks, then re-run governance-check until block=false.",
      "hash": "..."
    }
  ]
}
```

`block=false` means no governance findings require assistant remediation. `block=true` means the adapter should surface prompts and the assistant should remediate before claiming lifecycle completion.

Rationale: adapters need a stable machine-readable contract, while humans need readable diagnostics.

### Decision 3: Archive matching counts active and done runs

For archived OpenSpec changes, `governance-check` will consider the archive governed when either:

- The active current run has `primary_subject.type=openspec_change` and the same change id.
- A history run under `.ai/workflows/runs/history/` has the same primary subject and status `done`.

If neither exists, the archive is a `dangling_archive` finding.

Rationale: an active run means the lifecycle can still be resumed; a done history run proves the lifecycle completed. Both are valid governance evidence.

### Decision 4: Pending hooks are finding-specific remediation prompts

For active runs, unresolved `pending_hooks` will produce a `pending_hooks` finding with run id, change id if available, hook names, responsible worker categories, and a stop condition.

The remediation text must name the expected follow-up pattern:

- Invoke the responsible worker, such as memory sync or roadmap mutation.
- Call `workflow.py complete-hook --hook <hook-name>` after evidence exists.
- Re-run `workflow.py governance-check` and continue only until `block=false`.

Rationale: the plugin should not make lifecycle decisions, but it can give the assistant enough context to do the right next action.

### Decision 5: OpenCode plugin is a thin idle adapter

`.opencode/plugins/sdlc-governance.ts` will subscribe to `session.idle`, run the Python command against the current project root, parse JSON, and append remediation prompts when `block` is true.

Rationale: `session.idle` is a safe reconciliation point after the assistant/tool loop completes and before the next user action. It minimizes interference compared with file watcher events.

### Decision 6: Deduplication is by finding hash

Each finding will include or derive a stable hash from at least finding type, change id, run id, archive path, and pending hook names. The plugin will keep a process/session-scoped set of injected hashes for Phase 1.

Rationale: repeated idle events are expected. Deduplication prevents tight prompt loops while keeping implementation minimal. Persisted deduplication can be revisited after idle behavior is validated.

## Risks / Trade-offs

- Idle events may fire later than file updates → Accept for Phase 1; validate idle reliability before enabling file watcher triggers.
- OpenCode prompt injection APIs may differ between TUI and non-TUI modes → Keep the adapter thin and include validation tasks for `session.idle` and prompt append behavior.
- Process-scoped deduplication may re-prompt after restart → Accept for Phase 1 because repeated prompts after a new process are safer than suppressing unresolved governance findings.
- Dangling archive remediation may require human judgment → Report findings and prompt the assistant; do not auto-mutates lifecycle state.
- JSON contract drift can break plugin parsing → Cover representative command outputs with tests and keep plugin parsing defensive.

## Migration Plan

1. Add `governance-check` as a read-only command with tests using temporary roots.
2. Add the OpenCode plugin behind idle-only triggering.
3. Verify `session.idle` fires after assistant turn completion in the target OpenCode mode.
4. Keep `file.watcher.updated` disabled/deferred until idle-only behavior is stable.

Rollback is straightforward: disable or remove `.opencode/plugins/sdlc-governance.ts`. The runtime command is read-only and can remain without affecting domain state.

## Open Questions

- Which OpenCode prompt injection mechanism is stable for this repository's target mode: `tui.prompt.append`, session message injection, or another SDK client method?
- Should deduplication remain process/session-scoped or move to persisted session state after Phase 1 validation?
- Does `session.idle` fire consistently in both TUI and non-TUI OpenCode modes used by this project?
