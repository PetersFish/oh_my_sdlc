---
name: behavioral-test-design
description: >-
  Use when writing, reviewing, or modifying tests for behavior described by a
  spec, design, CLI flag, config field, state file, runner workflow, or bug fix,
  especially when tests might overfit to strings, symbols, or implementation
  shape instead of executable behavior.
---

# Behavioral Test Design

Tests should fail when the behavior is broken, even if the code contains the right words. Prefer executable behavior, observable outputs, and state round trips over string-presence checks.

## When To Use

- Writing or reviewing unit, integration, script, runner, or workflow tests.
- Translating OpenSpec scenarios or acceptance criteria into tests.
- Adding coverage for CLI flags, config fields, generated files, indexes, reports, or retries.
- Investigating a green test suite that missed a broken feature.

## Core Rule

Test the contract, not the vocabulary.

String-presence tests are acceptable for docs, templates, frontmatter, and static copy. They are not acceptable as the only proof for executable behavior such as flags, branching, filtering, concurrency, state updates, or subprocess commands.

## Behavior Test Shape

Use the smallest executable harness that proves the behavior:

```text
fixture/workspace -> invoke function or CLI -> observe command/file/state/output -> assert contract
```

For scripts and runners, build a temporary workspace and fake expensive dependencies. Mock `subprocess.run` or put a fake executable on `PATH` when the point is to inspect generated commands or outputs.

## Spec Scenario Mapping

For each spec scenario, record one of these verification modes:

| Mode | Meaning |
|---|---|
| unit | Focused helper or function behavior is asserted |
| integration | Script/CLI/workflow runs against a fixture |
| manual | Requires live external service or human judgment |
| not covered | Explicitly accepted gap with reason |

Avoid task wording like "add test for flag presence". Prefer "add behavior test proving `--only-new` exports and runs only changed golden cases".

## Anti-Overfit Checks

Before accepting a test, ask whether it would fail for these broken implementations:

- The flag is parsed but unused.
- The selected subset is computed but the full config is still executed.
- The state file has the right fields but cannot drive the next command.
- The implementation uses array indexes or preview text instead of stable IDs.
- Parallel code imports `ThreadPoolExecutor` but does not enforce limits or failure behavior.

If the test would still pass, it is not a behavior test.

## Runner And State Tests

For runner-like tools, prefer tests that assert:

- The final command receives the expected config, subset, concurrency, or mode.
- Generated files contain only the selected cases or expected transformed inputs.
- `run-index.json`, manifests, reports, or caches use stable identities and can be read back.
- Failure and no-op paths exit with the documented code and message.
- Retry, fail-fast, and concurrency behavior is observable without real external calls.

## Common Mistakes

- Checking that a source file contains a flag string instead of invoking the parser and behavior.
- Checking that a function name exists instead of asserting its output.
- Testing implementation structure so tightly that a correct refactor fails.
- Treating full-suite green as proof when the new behavior has no failing-first test.
- Marking manual external evals complete when they were not run.

## Review Output

When reviewing tests, report gaps in this form:

```text
Scenario: <contract being tested>
Current test proves: <what it actually proves>
Missing behavior proof: <what could still be broken>
Suggested test: <minimal fixture/invocation/assertion>
```
