# Wrapper Dispatch Resolution Design

**Date:** 2026-06-28

## Goal

Refactor lifecycle wrappers so provider-backed modules resolve their implementation dynamically through Python registry/config logic, while `dev-orchestrator` performs the actual runtime invocation of `skill`, `task`, or `command` backends.

## Problem

The current wrapper prototype conflates three different concerns:

1. provider selection
2. backend execution
3. result validation

That shape pushed execution into Python (`wrapper_adapters.py`), which cannot directly call the live tool runtime. It also encouraged fake-success behavior and made provider-specific validation too rigid.

## Design Summary

The wrapper architecture is redefined as four explicit stages:

1. **Resolve** — Python loads provider registry + project config and returns a dispatch spec.
2. **Dispatch** — `dev-orchestrator` dynamically invokes the resolved implementation using `skill`, `task`, or `bash`.
3. **Verify** — provider-specific verifiers validate observable results after dispatch.
4. **Normalize** — verification output is mapped into a stable evidence envelope for `workflow.py after-dispatch`.

This is analogous to a Java service locator pattern:

- wrapper contract = stable service interface
- provider registry = implementation registry
- Python resolver = service locator
- `dev-orchestrator` = runtime caller
- skill/agent/command = concrete implementation

## Core Decisions

### 1. Python wrappers become resolution-only

`wrapper_adapters.py` is renamed to `wrapper_resolution.py`.

Its responsibility is limited to:

- reading provider registry
- reading `.opencode/.cursor/.claude/sdlc-providers.yaml`
- validating module/provider/capability
- returning `dispatch + verifier + contract`
- failing closed on mismatches or unsupported capabilities

It does **not** execute tools.

### 2. `dev-orchestrator` is the execution layer

Only `dev-orchestrator` can call live tools, so runtime execution moves there.

Execution flow:

```text
before_dispatch
-> resolve_wrapper_dispatch(...)
-> dispatch.kind switch (skill | agent | command)
-> provider-specific verifier
-> contract normalization
-> after_dispatch
```

### 3. Separate dispatch, verifier, and contract

These concerns are intentionally split:

- **dispatch** = how to invoke the implementation
- **verifier** = how to validate provider-specific results
- **contract** = the stable semantic result expected by workflow gates

This prevents provider-specific file layouts from leaking into shared contract logic.

### 4. Provider-specific verification is required

`spec_change` is a shared semantic contract, not a shared file check.

For example:

- `openspec.create` verifies OpenSpec change directories and artifacts
- `github/spec-kit.create` would verify that provider's own outputs

So verifier choice must vary by provider and capability.

## Registry Model

Provider registry moves from backend strings to structured dispatch metadata.

Example shape:

```yaml
version: 2

modules:
  spec:
    default_provider: openspec
    contract: spec_change
    providers:
      openspec:
        capabilities:
          create: true
          continue: true
          apply: true
          archive: true
        dispatch:
          create:
            kind: skill
            target: openspec-propose
          continue:
            kind: skill
            target: openspec-continue-change
          apply:
            kind: skill
            target: openspec-apply-change
          archive:
            kind: skill
            target: openspec-archive-change
        verifier:
          create:
            kind: provider
            target: openspec.create
          continue:
            kind: provider
            target: openspec.continue
          apply:
            kind: provider
            target: openspec.apply
          archive:
            kind: provider
            target: openspec.archive

  memory:
    default_provider: local
    contract: memory_sync
    providers:
      local:
        capabilities:
          load: true
          repository_sync: true
          spec_post_archive_sync: true
        dispatch:
          load:
            kind: skill
            target: sdlc-repository-memory-load
          repository_sync:
            kind: skill
            target: sdlc-repository-memory-sync
          spec_post_archive_sync:
            kind: skill
            target: sdlc-openspec-memory-sync
        verifier:
          load:
            kind: provider
            target: local.load
          repository_sync:
            kind: provider
            target: local.repository_sync
          spec_post_archive_sync:
            kind: provider
            target: local.spec_post_archive_sync
```

Project-level config remains lightweight:

```yaml
version: 1

spec:
  provider: openspec

memory:
  provider: local
```

## Dispatch Spec

Resolver output should be a structured execution spec, for example:

```json
{
  "module": "spec",
  "capability": "create",
  "provider": "openspec",
  "dispatch": {
    "kind": "skill",
    "target": "openspec-propose",
    "args": {}
  },
  "result_contract": "spec_change",
  "verifier": {
    "kind": "provider",
    "target": "openspec.create"
  }
}
```

## Initial Scope

### Supported in first implementation

- `spec` with provider `openspec`
  - `create`
  - `continue`
  - `apply`
  - `archive`
- `memory` with provider `local`
  - `load`
  - `repository_sync`
  - `spec_post_archive_sync`
- `dispatch.kind = skill`
- provider-specific verifiers
- normalized result envelopes consumed by `workflow.py`

### Explicitly deferred

- `github/spec-kit` live integration
- generic credential systems
- full `agent` / `command` execution support
- implementation/testing/review/finish wrapper execution cutover
- letting each skill produce final workflow envelopes directly

## Verification Model

Success must come from observable post-dispatch results, not from skill prose.

### `spec_change`

Verifier examples for `openspec`:

- `create`: change directory and expected artifacts exist
- `continue`: expected artifact progress or file updates occurred
- `apply`: task progress or implementation-side observable changes occurred
- `archive`: archive path exists and active change moved/removed

### `memory_sync`

Verifier examples for `local`:

- `load`: memory manifest/index can be read and relevant entries were loaded
- `repository_sync`: manifest/index/report/review queue changed as expected
- `spec_post_archive_sync`: memory evidence/report exists and resolution is observable

## Fail-Closed Rules

The system must block instead of faking success when any of the following occur:

- unknown module/provider
- unsupported capability
- distributed config mismatch across `.opencode/.cursor/.claude`
- unsupported dispatch kind
- dispatch target invocation failure
- verifier cannot prove success
- normalization cannot produce a valid evidence envelope

## File Structure Changes

### Rename

- `skills/_lib/wrapper_adapters.py` -> `skills/_lib/wrapper_resolution.py`

### Expected new/supporting modules

- `skills/_lib/wrapper_resolution.py`
- `skills/_lib/provider_verifiers.py`
- `skills/_lib/result_contracts.py`

## Testing Strategy

Behavior tests should prove:

1. provider resolution returns the expected dispatch/verifier/contract
2. config mismatch fails closed
3. `dev-orchestrator` selects the resolved skill dynamically instead of hardcoding names
4. provider-specific verifiers distinguish success from unverifiable/no-op execution
5. `after_dispatch` sees only normalized structured envelopes

## Risks

- skill backends are flexible and may not expose machine-readable results directly
- provider-specific verifiers can drift if provider behavior changes
- introducing structured dispatch without enforcement in orchestrator would recreate a half-implemented skeleton

## Mitigations

- require provider-specific post-dispatch verification
- keep workflow gates dependent on normalized envelopes only
- start with `spec` + `memory` and `kind=skill` only
- defer broader provider/runtime generalization until the first vertical slice is proven
