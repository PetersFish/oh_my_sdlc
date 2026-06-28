## Metadata

- **Run ID:** wrapper-dispatch-resolution
- **Slice ID:** task-6
- **Agent:** implement-agent
- **Phase:** apply_change
- **Flow Type:** lightweight-flow
- **Status:** success
- **Recommended Next Agent:** test-agent

## Objective

Teach dev-orchestrator to resolve, dispatch, verify, and normalize wrapper-backed lifecycle modules (kind=skill) using the `resolve_wrapper_dispatch` flow instead of hardcoding backend skill names.

## Work Completed

### 1. CLI Helper (`skills/_lib/resolve_dispatch_cli.py`)
Created a minimal Python CLI shim that surfaces `resolve_wrapper_dispatch(...)` output as JSON. Accepts module, capability, run_id, phase, action, flow_type, and optional repo_root as positional args. Outputs `kind`, `target`, `verifier_target`, and `result_contract` for downstream consumption by dev-orchestrator.

Verified with both spec and memory resolution paths:
- `spec create` → kind=skill, target=openspec-propose, verifier_target=openspec.create, result_contract=spec_change
- `memory repository_sync` → kind=skill, target=sdlc-repository-memory-sync, verifier_target=local.repository_sync, result_contract=memory_sync

### 2. Dev-Orchestrator Prompt (`dev-orchestrator.md`)
Added `## Wrapper Dispatch Resolution (kind=skill)` section describing the 5-step flow:
1. **Resolve** — Call `resolve_dispatch_cli.py` to get the dispatch spec
2. **Dispatch** — Read `kind`/`target`, invoke the resolved skill (for kind=skill)
3. **Verify** — Run the provider-specific verifier via `provider_verifiers.py`
4. **Normalize** — Pass through the resolved `result_contract` normalizer
5. **Send** — Only the normalized envelope goes to `after_dispatch`

Also added bash permission for `python3 skills/_lib/resolve_dispatch_cli.py *` in frontmatter.

Updated all three agent directories: `.opencode/`, `.claude/`, `.cursor/`.

### 3. Tests (`tests/test_wrapper_contracts.py`)
Added `TestDevOrchestratorWrapperDispatch` test class with 6 focused tests:
- `test_dev_orchestrator_references_wrapper_dispatch_resolution`
- `test_dev_orchestrator_wrapper_dispatch_mentions_kind_and_target`
- `test_dev_orchestrator_wrapper_dispatch_mentions_verifier`
- `test_dev_orchestrator_wrapper_dispatch_mentions_normalize_and_result_contract`
- `test_dev_orchestrator_dynamic_resolution_displaces_hardcoded_routing`
- `test_dev_orchestrator_claude_cursor_copies_match_opencode_for_wrapper_dispatch`

## Files / Artifacts Changed

| File | Action |
|---|---|
| `skills/_lib/resolve_dispatch_cli.py` | Created (new CLI helper) |
| `.opencode/agents/dev-orchestrator.md` | Modified (frontmatter + body) |
| `.claude/agents/dev-orchestrator.md` | Modified (frontmatter + body) |
| `.cursor/agents/dev-orchestrator.md` | Modified (frontmatter + body) |
| `tests/test_wrapper_contracts.py` | Modified (added 6 new tests) |

## Commands Run

```bash
# RED phase - confirm tests fail
python3 -m pytest tests/test_wrapper_contracts.py::TestDevOrchestratorWrapperDispatch -v
# Result: 6 failed (expected)

# GREEN phase - confirm all pass
python3 -m pytest tests/test_wrapper_contracts.py::TestDevOrchestratorWrapperDispatch -v
# Result: 6 passed

# Regression - all existing tests still pass
python3 -m pytest tests/test_wrapper_contracts.py -v
# Result: 118 passed

# CLI shim - spec resolution
python3 skills/_lib/resolve_dispatch_cli.py spec create run-1 create_change create spec-flow
# Result: {"module":"spec","capability":"create","provider":"openspec","kind":"skill","target":"openspec-propose","verifier_target":"openspec.create","result_contract":"spec_change"}

# CLI shim - memory resolution
python3 skills/_lib/resolve_dispatch_cli.py memory repository_sync run-1 apply_change repository_sync spec-flow
# Result: {"module":"memory","capability":"repository_sync","provider":"local","kind":"skill","target":"sdlc-repository-memory-sync","verifier_target":"local.repository_sync","result_contract":"memory_sync"}
```

## Evidence Summary

- **TDD passed:** true (6 tests, all failing→green cycle)
- **Regression passed:** true (118 total tests passing, 0 failures)
- **CLI shim validated:** true (both spec and memory resolution, workdir-independent)

## Blockers

None.

## Assumptions

- The prompt changes are additive — they don't remove the subagent dispatch flow (plan-agent → implement-agent → test-agent → review-agent → finish-agent).
- The CLI shim imports directly from `_lib/*` with path setup. This works because the shim is at `skills/_lib/resolve_dispatch_cli.py` and sets up `sys.path`.
- The `.claude/` and `.cursor/` copies are byte-identical mirrors of `.opencode/` for the new section.

## Risks / Follow-Ups

- The CLI shim needs to exist at `skills/_lib/` in the repo root. If the orchestration runs from a different directory, the resolver's repo_root logic handles this via the CLI's explicit `repo_root` parameter.
- Future work: implement kind=agent and kind=command dispatch in dev-orchestrator.
- The `--value` JSON escaping for after_dispatch hook may need special handling in bash (single quotes + nested JSON). The prompt describes this pattern but the actual invocation may need shell escaping care.
