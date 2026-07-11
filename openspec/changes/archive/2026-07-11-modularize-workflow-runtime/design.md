## Context

`.ai/workflows/scripts/workflow.py` is an executable Python script of roughly 4,300 lines with more than 150 symbols. It currently combines low-level path and timestamp helpers, run-state persistence, workflow-definition interpretation, OpenSpec and roadmap loaders, policy registration, preflight decisions, lifecycle transitions, agent dispatch processing, governance diagnostics, final-commit support, foundation verification, parser construction, and process dispatch. `tests/test_workflow.py` provides broad subprocess-level regression coverage through temporary workspaces, but the monolith makes focused changes and isolated reasoning expensive.

This is a behavior-preserving prerequisite for the later class-based state-machine change. Existing callers must continue invoking `.ai/workflows/scripts/workflow.py`; no command, argument, exit code, JSON shape, state-file path, phase rule, or domain ownership may change. The live runtime is also a canonical input to bootstrap templates and project-level distributions, so a multi-file runtime requires inventory-aware synchronization and installation.

## Goals / Non-Goals

**Goals:**

- Keep `workflow.py` as a stable executable facade.
- Establish acyclic, responsibility-based modules that can be understood and tested independently.
- Preserve all observable CLI and persisted-state behavior.
- Keep runtime state mutation centralized behind the extracted state I/O API.
- Preserve broad CLI tests and add focused tests only for extraction-sensitive module contracts.
- Make bootstrap initialization, canonical template sync, distributed-copy checks, and aggregate derived-artifact checks cover every runtime module.

**Non-Goals:**

- Redesigning phases, transitions, gates, policies, evidence contracts, or command output.
- Introducing classes or a generic state-machine framework.
- Renaming public commands or moving the public script.
- Changing roadmap, OpenSpec, memory, EvalOps, or agent ownership.
- Adding third-party runtime dependencies.

## Decisions

### 1. Use a sibling package while retaining the script facade

Create `.ai/workflows/scripts/workflow_runtime/` with `__init__.py` and focused modules. Reduce `workflow.py` to the shebang, a short compatibility docstring, and delegation to `workflow_runtime.cli.main()`.

This is preferred over several loose sibling files because a package gives the extracted code an explicit namespace, mirrors cleanly into bootstrap templates, and avoids generic names such as `state.py` colliding with unrelated imports. Keeping everything in the original script was rejected because it does not solve the maintenance problem. Moving the executable into the package was rejected because it would break documented and automated callers.

### 2. Split by dependency direction and cohesive behavior

Use the following target layout; exact symbol movement may be adjusted to eliminate cycles, but responsibilities must remain stable:

- `workflow_runtime/core.py`: constants and pure generic helpers such as timestamps, hashes, path resolution, and decision factories.
- `workflow_runtime/state.py`: run pointer discovery, active/history run loading, validation, persistence, and context/state derivation. This is the only module that directly writes workflow run-state files.
- `workflow_runtime/definitions.py`: YAML definition loading, phase/transition interpretation, exit criteria, and definition validation.
- `workflow_runtime/domains.py`: read-only OpenSpec, archive, roadmap, memory, and EvalOps loaders.
- `workflow_runtime/policies.py`: policy registry metadata, decorators, policy functions, subject/run-context evaluation, preflight, and ensure-run behavior.
- `workflow_runtime/dispatch.py`: runtime-context assembly plus before-dispatch and after-dispatch validation/storage behavior.
- `workflow_runtime/lifecycle.py`: status/start/resume/readiness/resolve/record/complete/advance/block/cancel/done command handlers and transition helpers.
- `workflow_runtime/governance.py`: governance findings, foundation verification, archive diagnostics, and final-commit support.
- `workflow_runtime/cli.py`: parser construction, command registration, root resolution, handler dispatch, output, and exit-code mapping.

Dependencies flow from `core` to `state`/`definitions`/`domains`, then to `policies`, `dispatch`, `lifecycle`, and `governance`, with `cli` composing command handlers. Higher-level modules must not be imported by lower-level modules. Shared behavior moves downward only when it has a single stable meaning; this change must not introduce a service-container or plugin abstraction.

An alternative split into one module per command was rejected because it would create many tiny files with repeated wiring. A minimal split into `helpers.py`, `commands.py`, and `cli.py` was rejected because `commands.py` would remain a second monolith.

### 3. Preserve behavior through extraction-first migration

Move symbols in dependency order without semantic rewrites: core helpers, state/definitions/domains, policies, dispatch, lifecycle, governance/finalization, then CLI. At each step, imports replace moved definitions and focused plus end-to-end tests run. Function signatures and command handler conventions (`cmd_<command>(root, args)`) remain unchanged unless an internal-only signature must accept an explicit dependency to avoid a cycle; such changes must not affect CLI behavior.

Rollback is a normal source rollback: because persisted formats and commands do not change, reverting the modular files and restoring the monolithic script requires no data migration.

### 4. Keep end-to-end tests authoritative and add a small focused module suite

`tests/test_workflow.py` remains the authoritative compatibility suite and continues invoking the public script in subprocesses against temporary workspaces. Do not mechanically redistribute its existing scenarios among module tests.

Add `tests/test_workflow_modules.py` for extraction-specific contracts that are cheaper and clearer at module level:

- all package modules import without circular-import failures;
- state save/load and pointer round trips retain schema and path behavior in a temporary workspace;
- definition validation accepts the current definition and rejects malformed input through the extracted API;
- policy decorators store per-action metadata in `POLICY_META` without function-attribute leakage;
- domain loaders remain read-only;
- `workflow.py` delegates to the package while the existing CLI harness proves command compatibility.

Tests must assert executable behavior, not source-string presence. For example, state ownership is proven by invoking state operations and observing the expected run files, while read-only loaders are exercised against snapshots and asserted not to alter the workspace.

### 5. Treat the runtime module tree as one governed bootstrap asset

Mirror the package under `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/`. Update `init_foundations.py` so new projects receive `workflow.py`, the complete package tree, and `sdlc-main.yaml`. Update `sync_templates.py` to derive or explicitly enumerate the complete runtime module inventory, compare live-to-canonical and canonical-to-each-distribution, copy nested files, and report missing or stale files.

Prefer a deterministic explicit inventory or a narrowly scoped `workflow_runtime/**/*.py` inventory with sorted paths and stale-file detection. A broad copy of all `.ai/workflows/` content is rejected because runtime state and unrelated files must never enter templates. Existing aggregate `scripts/sync_derived_artifacts.py` behavior remains the top-level verification entrypoint.

### 6. Keep AI EvalOps out of the required gate

This change affects deterministic Python runtime behavior, not model-generated behavior. No durable AI eval suite is required. The EvalOps candidate is a future agent regression case only if downstream agents begin misrouting because module paths changed; normal unit and integration tests are sufficient for this refactor.

## Risks / Trade-offs

- **Circular imports between policies, state, and command handlers** → Enforce the dependency direction above, move shared constants/factories downward, and add an import-all smoke test before moving behavior.
- **Behavior drift during symbol movement** → Use extraction-only commits, preserve signatures, run focused tests after each module and the full CLI suite after each responsibility group.
- **Hidden reliance on module globals or monkeypatch targets** → Inventory test patches and global registries before moving each symbol; preserve a compatibility re-export only when an existing executable test or external contract requires it.
- **State writes escape the state module** → Route run pointer/state persistence through `workflow_runtime.state`; cover round trips and use repository search during review to confirm no other extracted module opens `.ai/workflows/runs/` for writing.
- **Bootstrap installs an incomplete package** → Add initialization tests that execute the bootstrapped `workflow.py`, plus missing/stale nested-file drift tests.
- **Large refactor obscures review** → Implement in dependency-ordered test/implement pairs and avoid formatting or semantic cleanup unrelated to extraction.
- **More files increase synchronization churn** → Make the package tree a single governed inventory and rely on aggregate derived-artifact sync rather than manual copy lists in multiple places.

## Migration Plan

1. Capture the current focused and full test baseline without changing source.
2. Add failing package-import and state/definition module tests.
3. Create the package and extract low-level modules in dependency order, running focused tests after each extraction.
4. Extract policy, dispatch, lifecycle, and governance groups while continuously running corresponding `tests/test_workflow.py` classes.
5. Replace `workflow.py` with the thin facade only after all handlers are composed by `workflow_runtime.cli`.
6. Extend bootstrap initialization and template sync/distribution inventories, then regenerate canonical and project-level derived copies through repository tooling.
7. Run the full workflow suite, bootstrap/sync tests, full repository tests, and aggregate derived-artifact check.

Rollback requires reverting source and template changes together. No persisted run migration or cleanup is needed.

## Open Questions

None. The roadmap questions are resolved as follows: modules use a sibling `workflow_runtime/` package, and existing end-to-end coverage remains authoritative with a small extraction-focused unit suite.
