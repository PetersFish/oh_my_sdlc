## Context

The repository now has an `sdlc-evalops` skill and existing EvalOps assets for `skill.sdlc-orchestrator` under a root `evals/` directory. That layout helped bootstrap coverage, but it mixes platform-level assets, target-level assets, derived exports, and run reports in a single root namespace.

This change establishes `.ai/evals/` as the long-term EvalOps root. The core design choice is to separate global platform policy from target-scoped workspaces: global manifests and schemas describe what targets exist and how EvalOps behaves by default; each target workspace owns its canonical cases, derived exports, and reports.

## Goals / Non-Goals

**Goals:**

- Establish `.ai/evals/` as the only long-term EvalOps root.
- Standardize `.ai/evals/targets/<target-id>/` as the namespace for target-owned EvalOps assets.
- Use non-underscored platform directories: `templates/`, `schemas/`, and `runners/`.
- Make `skill.sdlc-orchestrator` the reference target workspace.
- Define global and target manifest requirements.
- Add a Promptfoo export script that derives exports from canonical golden cases.
- Inject target skill source into Promptfoo prompts at export time.
- Preserve deterministic assertions and prohibit unconfigured `llm-rubric` assertions.
- Add `--check` freshness validation for generated Promptfoo exports.
- Define the model matrix schema now while deferring the full matrix runner.
- Update `sdlc-orchestrator` and `sdlc-evalops` behavior contracts around EvalOps gates and reporting.

**Non-Goals:**

- Do not implement the full multi-model matrix runner in this change.
- Do not add CI integration in this change.
- Do not integrate `skill-creator`; that belongs to `RM-EVAL-003`.
- Do not integrate `meta-skill-lifecycle-governance`; that belongs to `RM-EVAL-004`.
- Do not keep long-term dual-write compatibility between root `evals/` and `.ai/evals/`.
- Do not change OpenSpec schema behavior.

## Decisions

### Decision 1: `.ai/evals/` is the EvalOps root

All EvalOps source assets move under `.ai/evals/`. The old root `evals/` directory is migration input only, not a long-term alternate source of truth.

Alternative considered: keep root `evals/` as canonical and add `.ai/evals/` later. This was rejected because other SDLC state already lives under `.ai/`, and dual roots would make target discovery and freshness checks ambiguous.

### Decision 2: Target workspaces live under `targets/`

Each target gets a workspace at `.ai/evals/targets/<target-id>/`. For this batch, the reference target is `.ai/evals/targets/skill.sdlc-orchestrator/`.

The reference target workspace should contain:

- `manifest.yaml` for target metadata, source paths, export policy, and report policy.
- `coverage.yaml` for quality dimensions and required coverage.
- `cases/inbox/`, `cases/accepted/`, `cases/rejected/`, and `cases/golden/` for case lifecycle state.
- `exports/promptfoo/` for generated Promptfoo files.
- `reports/` for eval outputs and final golden eval summaries.

Alternative considered: group by artifact type globally, such as all golden cases under `.ai/evals/cases/golden/<target-id>/`. This was rejected because target workspaces make ownership, migration, and cleanup simpler as more skills and agents are evaluated.

### Decision 3: Platform directories are non-underscored

Global platform assets use `.ai/evals/templates/`, `.ai/evals/schemas/`, and `.ai/evals/runners/`. The names intentionally avoid leading underscores so they are easy to reference in docs, scripts, and user instructions.

### Decision 4: Global manifest plus target manifest

`.ai/evals/manifest.yaml` is the global registry and policy surface. It declares the EvalOps schema version, known targets, default export policy, default assertion policy, report retention expectations, and the model matrix file path.

Each target workspace has a `manifest.yaml` that declares target id, target type, source paths, canonical case directories, export outputs, report directory, assertion policy overrides, and freshness inputs for export checks.

Global policy may provide defaults, but target manifests must be explicit enough for `scripts/export-promptfoo.py <target-id>` to locate canonical golden cases, inject source files, and write exports without scanning unrelated targets.

### Decision 5: Canonical cases are source of truth; Promptfoo exports are derived

Canonical golden cases live in the target workspace under `cases/golden/`. Promptfoo files under `exports/promptfoo/` are generated outputs and must not become hand-edited sources of truth.

`scripts/export-promptfoo.py <target-id>` generates Promptfoo exports. `scripts/export-promptfoo.py <target-id> --check` exits non-zero when exports are missing or stale compared with the target manifest, golden cases, templates, or injected source files.

### Decision 6: Skill source is injected into Promptfoo prompt

Promptfoo export generation reads target source files from the target manifest, including `skills/sdlc-orchestrator/SKILL.md` for `skill.sdlc-orchestrator`, and injects that source into the prompt context. Golden cases specify behavior inputs and expected outcomes; they do not duplicate full skill source.

This keeps prompt evaluations aligned with the current skill implementation and avoids stale copied prompts in individual case files.

### Decision 7: Assertions must be target-local and deterministic by default

Promptfoo exports must not rely on global assertions that silently affect every target. Shared templates may define structure, but assertions that determine pass/fail belong in canonical cases or explicit target policy.

Deterministic assertions are preferred: contains, not-contains, regex, structural checks, explicit tool-use expectations, and exact values where appropriate. `llm-rubric` is prohibited unless the canonical case or target manifest configures the rubric text, grading model, and any required thresholds explicitly.

### Decision 8: Session eval and Promptfoo eval have different responsibilities

`sdlc-evalops` should distinguish interactive session eval from generated Promptfoo eval:

- Session eval captures real failures, drafts cases, reviews coverage, and gets human approval before promotion to golden.
- Promptfoo eval runs canonical golden cases through exported deterministic configs and records reports.

Session eval is not a substitute for final Promptfoo golden eval when implementation changes affect AI behavior.

### Decision 9: Reports are retained under target workspaces

Run outputs and final summaries live under `.ai/evals/targets/<target-id>/reports/`. The final implementation summary for an EvalOps-gated change should name the target, case counts, export freshness status, eval command, result count, report path, and any blocked runner dependency.

### Decision 10: Model matrix schema exists before runner implementation

`.ai/evals/model-matrix.yaml` is introduced with a schema contract for named models, providers, environments, target selection, and run policy. The full runner that executes every target across the matrix is deferred, but schema and validation tasks are included so future work has a stable contract.

### Decision 11: Orchestrator gates new AI skill development through EvalOps

For new AI skill development and material AI behavior changes, `sdlc-orchestrator` should route through these phases:

1. Classify the request and identify the AI behavior target.
2. Require EvalOps coverage definition before implementation unless the user explicitly confirms an exception.
3. Require human confirmation before promoting drafted cases to golden.
4. Route implementation through the selected OpenSpec or Superpowers path.
5. Require final golden eval or a clearly reported blocked eval state before completion.

The orchestrator coordinates these gates but does not duplicate detailed `sdlc-evalops` workflows.

### Decision 12: opencode Go models use Python provider for Promptfoo

opencode Go (`opencode-go`) paid-plan models are accessible via an OpenAI-compatible endpoint at `https://opencode.ai/zen/go/v1/chat/completions`. However, Promptfoo's built-in `openai:chat:*` provider encounters a `TypeError: terminated` when reading responses from this endpoint due to an undici/Node HTTP client compatibility issue.

- The default eval model for this repo is `opencode-go/deepseek-v4-pro`.
- The Promptfoo provider is a Python provider at `.ai/evals/runners/opencode_go_provider.py`, using the standard library `urllib` to call the endpoint and returning `{ "output": text }`.
- The provider path is relative to the generated `promptfooconfig.yaml`: `file://../../../../runners/opencode_go_provider.py`.
- Provider configuration (`model`, `temperature`, `max_tokens`) lives in `.ai/evals/model-matrix.yaml` under `models[].promptfoo`.
- The same provider is configured as the grader (`models[].grader`) in `defaultTest.options.provider` so `llm-rubric` assertions can be evaluated through the same endpoint.
- The grader model should be one with stable JSON output (e.g., GLM, Qwen, Kimi), not a reasoning-oriented model. Reasoning models may put output in `reasoning_content` instead of `content`, causing `llm-rubric` JSON extraction failures.
- The API key is read from `OPENCODE_GO_API_KEY` environment variable by the Python provider. Keys MUST NOT be written into repository files.
- `scripts/export-promptfoo.py` reads the provider block from `model-matrix.yaml` and generates the `providers` and `defaultTest.options.provider` sections of `promptfooconfig.yaml`.
- `opencode run --model opencode-go/deepseek-v4-pro "hello"` may be used as a manual smoke test but is not the Promptfoo runner.

### Decision 13: Eval runner script bridges export, eval, and report writing

The `scripts/export-promptfoo.py` script handles only export generation. The `promptfoo eval` command must be run with `-o <output-path>` to write repo-pinned reports. Without a runner script that chains export → eval → report, reports end up in Promptfoo's default local store (`~/.promptfoo/promptfoo.db`) rather than in the repo's `reports/` directory.

- `scripts/run-promptfoo-eval.py <target-id>` chains:
  1. `scripts/export-promptfoo.py <target-id>` (ensures freshness)
  2. `promptfoo eval -c <config> -o <reports-dir>/promptfoo-output.json --max-concurrency 1 --no-cache`
  3. Parses the JSON output and writes `summary.md` (pass/fail counts, case details) and `failures.yaml` (failed case ids with severity)
- Reports land under `.ai/evals/targets/<target-id>/reports/<run-id>/`
- The `run-id` format is `<target-id>-<timestamp>` (e.g., `skill.sdlc-orchestrator-20260613T090000Z`)
- The `sdlc-evalops` Eval Command example must include the `-o` flag and reference the runner script as the canonical way to run and record eval
- The runner script uses `OPENCODE_GO_API_KEY` from environment (same as the Python provider)
- If `promptfoo eval` fails, the runner exits non-zero and reports the error to stderr

Alternative considered: keep `export-promptfoo.py` as the single entry point and add a `--run` mode. Rejected because that bleeds run orchestration into a script whose existing contract is pure export generation, making `--check` guarantees harder to reason about.

## Target Workspace Layout

The standardized layout is:

```text
.ai/evals/
  manifest.yaml
  model-matrix.yaml
  templates/
  schemas/
  runners/
  targets/
    skill.sdlc-orchestrator/
      manifest.yaml
      coverage.yaml
      cases/
        inbox/
        accepted/
        rejected/
        golden/
      exports/
        promptfoo/
      reports/
```

The layout is a contract for implementation. This proposal does not migrate files or implement code.

## Risks / Trade-offs

- Migration can break local scripts that assume root `evals/` paths. Mitigation: make migration tasks explicit and update tests/scripts in one batch rather than dual-writing indefinitely.
- Generated exports can be mistaken for canonical files. Mitigation: document exports as derived and enforce `--check` freshness.
- Deterministic assertions may miss nuanced quality regressions. Mitigation: allow configured rubrics only when rubric text, grading model, and thresholds are explicit.
- Full model matrix support is deferred. Mitigation: define schema now and keep runner implementation as a later bounded task.
