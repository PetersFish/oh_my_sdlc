## 1. EvalOps Root Migration

- [x] 1.1 Create `.ai/evals/` with `manifest.yaml`, `model-matrix.yaml`, `templates/`, `schemas/`, `runners/`, and `targets/`.
- [x] 1.2 Define `.ai/evals/manifest.yaml` with schema version, registered targets, default export policy, default assertion policy, report policy, platform directories, and model matrix path.
- [x] 1.3 Define the `.ai/evals/model-matrix.yaml` schema contract for models, providers, environments, target selection, and run policy without implementing the full matrix runner.
- [x] 1.4 Migrate existing root `evals/` assets into `.ai/evals/` and remove root `evals/` as a long-term source of truth.
- [x] 1.5 Update any repository references that still point to root `evals/` after migration.

## 2. Target Workspace Standardization

- [x] 2.1 Create `.ai/evals/targets/skill.sdlc-orchestrator/` as the reference target workspace.
- [x] 2.2 Add target `manifest.yaml` for `skill.sdlc-orchestrator` with target id, type, source paths, canonical case directories, coverage file, Promptfoo export outputs, report directory, assertion policy, and export freshness inputs.
- [x] 2.3 Move or create `coverage.yaml` for `skill.sdlc-orchestrator` under its target workspace.
- [x] 2.4 Move canonical cases for `skill.sdlc-orchestrator` under `cases/inbox/`, `cases/accepted/`, `cases/rejected/`, and `cases/golden/` as appropriate.
- [x] 2.5 Ensure generated Promptfoo exports live under `.ai/evals/targets/skill.sdlc-orchestrator/exports/promptfoo/`.
- [x] 2.6 Ensure EvalOps reports live under `.ai/evals/targets/skill.sdlc-orchestrator/reports/`.

## 3. Promptfoo Export Script

- [x] 3.1 Implement `scripts/export-promptfoo.py <target-id>` to read `.ai/evals/manifest.yaml` and the target workspace manifest.
- [x] 3.2 Generate Promptfoo exports from canonical golden cases rather than hand-authored Promptfoo exports.
- [x] 3.3 Inject target skill source into generated Promptfoo prompts using source paths declared by the target manifest.
- [x] 3.4 Implement `scripts/export-promptfoo.py <target-id> --check` so missing or stale exports fail without rewriting files.
- [x] 3.5 Add validation that generated exports do not rely on hidden global assertions.
- [x] 3.6 Add validation that unconfigured `llm-rubric` assertions are rejected.
- [x] 3.7 Prefer deterministic assertions in canonical cases and generated Promptfoo outputs.

## 4. sdlc-evalops Skill Updates

- [x] 4.1 Update canonical `skills/sdlc-evalops/SKILL.md` to describe `.ai/evals/` as the EvalOps root and target workspaces under `.ai/evals/targets/`.
- [x] 4.2 Update `sdlc-evalops` instructions for global manifest and target manifest requirements.
- [x] 4.3 Update `sdlc-evalops` instructions to distinguish session eval from Promptfoo eval.
- [x] 4.4 Update `sdlc-evalops` instructions for reports policy and required final golden eval reporting fields.
- [x] 4.5 Update `sdlc-evalops` instructions for deterministic assertion preference, no global assertion pollution, and prohibited unconfigured `llm-rubric`.
- [x] 4.6 Update `sdlc-evalops` instructions to document `model-matrix.yaml` schema while noting the full matrix runner is deferred.
- [x] 4.7 Distribute the updated `sdlc-evalops` skill to `.opencode/`, `.claude/`, and `.cursor/` skill copies.

## 5. sdlc-orchestrator Skill Updates

- [x] 5.1 Update canonical `skills/sdlc-orchestrator/SKILL.md` so new AI skill development and material AI behavior changes identify an EvalOps target and require target-scoped coverage before implementation unless explicitly excepted.
- [x] 5.2 Add human confirmation boundaries for target registration, coverage acceptance, golden case promotion, and EvalOps exceptions.
- [x] 5.3 Update orchestrator route decisions so AI behavior changes name the target id when known or route to target identification as the next EvalOps step.
- [x] 5.4 Require final golden eval or explicitly reported blocked runner dependency before completion claims for EvalOps-gated changes.
- [x] 5.5 Require final summaries to report target id, case counts, export freshness status, eval command, pass/fail result count, and report path when available.
- [x] 5.6 Distribute the updated `sdlc-orchestrator` skill to `.opencode/`, `.claude/`, and `.cursor/` skill copies.

## 6. Tests and Verification

- [x] 6.1 Add tests for `.ai/evals/` manifest presence, required global manifest fields, and target workspace layout.
- [x] 6.2 Add tests for `skill.sdlc-orchestrator` target manifest fields and workspace directories.
- [x] 6.3 Add tests for `scripts/export-promptfoo.py` generation from canonical golden cases.
- [x] 6.4 Add tests for skill source injection into generated Promptfoo prompt content.
- [x] 6.5 Add tests that `scripts/export-promptfoo.py skill.sdlc-orchestrator --check` detects stale exports.
- [x] 6.6 Add tests prohibiting global assertion pollution in generated Promptfoo exports.
- [x] 6.7 Add tests prohibiting unconfigured `llm-rubric` assertions.
- [x] 6.8 Add tests or static checks that distributed `sdlc-evalops` and `sdlc-orchestrator` skill copies match canonical sources.
- [x] 6.9 Run `scripts/export-promptfoo.py skill.sdlc-orchestrator --check` and verify exports are fresh.
- [x] 6.10 Run the `skill.sdlc-orchestrator` Promptfoo golden eval and verify the migrated golden set passes, or document the blocked runner dependency with report path.
  - **Status: done** - Evaluated 6 golden cases with opencode-go provider; 6/6 pass (0 errors, 0 failures, 2m32s). Repo reports not written on initial run due to missing `-o` flag and runner script gap (see Section 9).
- [x] 6.11 Run local tests and `openspec status --change standardize-ai-evalops-target-workspaces`.

## 7. Deferred Follow-Ups

- [x] 7.1 Record that full model matrix runner implementation is deferred beyond this batch.
- [x] 7.2 Record that `skill-creator` integration is deferred to `RM-EVAL-003`.
- [x] 7.3 Record that `meta-skill-lifecycle-governance` integration is deferred to `RM-EVAL-004`.

## 8. opencode Go OpenAI-Compatible Provider Integration

- [x] 8.1 Update `.ai/evals/model-matrix.yaml` with `opencode-go-deepseek-v4-pro` model entry including `promptfoo` block with `apiBaseUrl`, `apiKeyEnvar`, `temperature`, and `max_tokens`.
- [x] 8.2 Modify `scripts/export-promptfoo.py` to read Promptfoo provider config from `.ai/evals/model-matrix.yaml` default model instead of hardcoding `id: opencode`.
- [x] 8.3 Update canonical `skills/sdlc-evalops/SKILL.md` with opencode Go provider rules: model matrix is provider source, OpenAI-compatible endpoint, `OPENCODE_GO_API_KEY`, no key in repo.
- [x] 8.4 Distribute updated `sdlc-evalops` skill to `.opencode/`, `.claude/`, and `.cursor/` skill copies.
- [x] 8.5 Add tests: generated `promptfooconfig.yaml` uses `openai:chat:deepseek-v4-pro` with `apiBaseUrl` and `apiKeyEnvar`.
- [x] 8.6 Run `scripts/export-promptfoo.py skill.sdlc-orchestrator --check` and verify exports are fresh.

## 9. Report Writing Gap Fix

The Promptfoo eval run command in `sdlc-evalops` and the `scripts/export-promptfoo.py` tool chain did not force writing run reports into the repo. The eval command example omitted `-o <report-path>` and no runner script bridged export + eval + report writing.

- [x] 9.1 Update `sdlc-evalops` Eval Command example to include `-o .ai/evals/targets/<target-id>/reports/<run-id>/promptfoo-output.json` and clarify that `--output` is required for repo-pinned reports.
- [x] 9.2 Create `scripts/run-promptfoo-eval.py <target-id>` that chains export, `promptfoo eval -o <report-path>`, and writes a structured `summary.md` plus `failures.yaml` under `.ai/evals/targets/<target-id>/reports/<run-id>/`.
- [x] 9.3 Add tests: runner script produces `reports/<run-id>/promptfoo-output.json`, `summary.md`, `failures.yaml`; Eval Command in all `sdlc-evalops` copies includes `-o` flag.
- [x] 9.4 Run `scripts/run-promptfoo-eval.py skill.sdlc-orchestrator` and verify reports land in `.ai/evals/targets/skill.sdlc-orchestrator/reports/`.
  - **Status: done** — 6/6 passed, reports written to `reports/skill.sdlc-orchestrator-20260613T092502Z/`
- [x] 9.5 Distribute updated `sdlc-evalops` skill to `.opencode/`, `.claude/`, and `.cursor/` skill copies.
