## Why

OpenSpec archive and workflow hook completion can still be bypassed when actions are invoked outside the orchestrator path. This change validates Phase 1 of governance enforcement in OpenCode by adding deterministic runtime diagnostics and a thin OpenCode adapter that surfaces actionable remediation prompts after assistant turns.

## What Changes

- Add a `workflow.py governance-check` subcommand that reports governance diagnostics without mutating Roadmap, OpenSpec, Memory, or workflow state.
- Detect archived OpenSpec changes that have no matching active workflow run and no matching completed workflow history run.
- Detect unresolved `pending_hooks` in active workflow runs and report hook names with related run/change context.
- Define a structured JSON output contract with `block`, finding types, context fields, and remediation text suitable for adapters and tests.
- Add tests for clean state, dangling archive, pending hooks, and combined diagnostics using temporary fixtures.
- Add `.opencode/plugins/sdlc-governance.ts` as a thin OpenCode adapter that runs governance checks on `session.idle`.
- Have the plugin append finding-specific remediation prompts through an OpenCode prompt/UI mechanism such as `tui.prompt.append`.
- Deduplicate repeated prompt injection by a stable finding hash so idle checks do not create tight prompt loops.
- Defer `file.watcher.updated` triggering until idle-only behavior is proven stable.
- Include agent-facing plugin installation documentation (`docs/opencode/sdlc-governance-plugin-install.md`) covering current-repo enablement, cross-repo install, verification checklist, rollback, and stale copy protection.

## Capabilities

### New Capabilities
- `opencode-governance-adapter`: Defines the OpenCode idle-triggered adapter, prompt injection behavior, finding deduplication, and adapter validation expectations.

### Modified Capabilities
- `sdlc-orchestrator`: Adds runtime governance diagnostics for dangling archives and unresolved workflow hooks, plus the remediation contract the orchestrator should follow when checks block completion.

## Impact

- Affects `.ai/workflows/scripts/workflow.py` by adding a read-only governance diagnostic command and fixture-friendly output contract.
- Adds tests around workflow/OpenSpec archive fixtures and active run `pending_hooks` state.
- Adds `.opencode/plugins/sdlc-governance.ts` for OpenCode-specific idle integration.
- May add or update local OpenCode plugin configuration only as needed for plugin loading.
- Adds `docs/opencode/sdlc-governance-plugin-install.md` as agent-facing installation documentation.
- Does not alter upstream `openspec-*` skills, Roadmap lifecycle commands, Memory sync behavior, or workflow state mutation ownership.
