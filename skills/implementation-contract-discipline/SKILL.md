---
name: implementation-contract-discipline
description: >-
  Use when implementing code from a spec, design, task list, CLI option,
  config field, state file, runner workflow, or other behavior contract where
  shallow implementation could parse inputs or write fields without making the
  behavior actually work.
---

# Implementation Contract Discipline

Implement behavior contracts end to end. A parsed flag, config field, helper name, or output field is not done until it changes the execution path and can be consumed by the next step that depends on it.

## When To Use

- Implementing from OpenSpec, design docs, acceptance criteria, or scenario lists.
- Adding CLI flags, config fields, feature toggles, runner modes, or workflow options.
- Writing state files, indexes, caches, reports, manifests, or audit metadata.
- Connecting multiple scripts, runners, exports, or lifecycle steps.
- Fixing a failure caused by code that satisfied tests by shape but not behavior.

## Contract Checklist

Before calling implementation complete, verify each new contract item:

| Contract item | Completion proof |
|---|---|
| CLI flag or config | Parsed value reaches the operation it is supposed to change |
| Selection/filter | Selected set affects the final command, generated file, query, or output |
| State file/index | Data written now can drive the documented future read path |
| Identity field | Uses stable domain identity, not array index, preview text, timestamp, or display label |
| Report field | Reflects actual runtime behavior, not just the requested mode |
| Error path | Exits or reports exactly as the contract says |

## Data-Flow Rule

Trace the value from source to observable effect:

```text
input/config/flag -> normalized value -> core logic -> side effect/output -> later consumer
```

If the trace stops at a local variable, parser, helper, or summary string, the implementation is incomplete.

## State Round-Trip Rule

For indexes and state files, prove a round trip:

```text
write stable state -> load state later -> select/decide using that state -> execute correct behavior
```

Do not use unstable keys such as `case-0`, input previews, array positions, generated report names, or localized display text when the next command must map back to canonical source. Prefer IDs declared in source files, repo-relative paths, and content hashes.

## Reuse Boundary

When two entry points implement the same contract, share the contract logic. CLI scripts may parse different arguments, but case selection, identity normalization, state entry construction, and schema interpretation should live in one helper. Divergent duplicate logic is a smell because one path will drift.

## Common Smells

- A flag is accepted but never changes generated files or subprocess arguments.
- A subset is computed but a downstream full export/config is still used.
- A state field exists but contains placeholders or values that cannot be mapped back.
- Tests assert strings such as `--only-new` or `ThreadPoolExecutor` instead of observable behavior.
- Two runners build different identifiers for the same domain object.
- A summary claims incremental mode while the actual command ran all cases.

## Implementation Review Questions

Ask these before finishing:

- What exact observable output would be different if this flag/config were removed?
- Can a later run consume the state I wrote without guessing?
- Is every spec scenario represented by executable logic, not just documentation text?
- Did I reuse existing helpers or create a second interpretation of the same contract?
- Would a behavior test fail if the value were parsed but unused?
