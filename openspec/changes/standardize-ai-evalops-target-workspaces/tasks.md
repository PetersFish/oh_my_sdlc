## 1. EvalOps Root Migration

- [ ] 1.1 Create `.ai/evals/` with `manifest.yaml`, `model-matrix.yaml`, `templates/`, `schemas/`, `runners/`, and `targets/`.
- [ ] 1.2 Define `.ai/evals/manifest.yaml` with schema version, registered targets, default export policy, default assertion policy, report policy, platform directories, and model matrix path.
- [ ] 1.3 Define the `.ai/evals/model-matrix.yaml` schema contract for models, providers, environments, target selection, and run policy without implementing the full matrix runner.
- [ ] 1.4 Migrate existing root `evals/` assets into `.ai/evals/` and remove root `evals/` as a long-term source of truth.
- [ ] 1.5 Update any repository references that still point to root `evals/` after migration.

## 2. Target Workspace Standardization

- [ ] 2.1 Create `.ai/evals/targets/skill.sdlc-orchestrator/` as the reference target workspace.
- [ ] 2.2 Add target `manifest.yaml` for `skill.sdlc-orchestrator` with target id, type, source paths, canonical case directories, coverage file, Promptfoo export outputs, report directory, assertion policy, and export freshness inputs.
- [ ] 2.3 Move or create `coverage.yaml` for `skill.sdlc-orchestrator` under its target workspace.
- [ ] 2.4 Move canonical cases for `skill.sdlc-orchestrator` under `cases/inbox/`, `cases/accepted/`, `cases/rejected/`, and `cases/golden/` as appropriate.
- [ ] 2.5 Ensure generated Promptfoo exports live under `.ai/evals/targets/skill.sdlc-orchestrator/exports/promptfoo/`.
- [ ] 2.6 Ensure EvalOps reports live under `.ai/evals/targets/skill.sdlc-orchestrator/reports/`.

## 3. Promptfoo Export Script

- [ ] 3.1 Implement `scripts/export-promptfoo.py <target-id>` to read `.ai/evals/manifest.yaml` and the target workspace manifest.
- [ ] 3.2 Generate Promptfoo exports from canonical golden cases rather than hand-authored Promptfoo exports.
- [ ] 3.3 Inject target skill source into generated Promptfoo prompts using source paths declared by the target manifest.
- [ ] 3.4 Implement `scripts/export-promptfoo.py <target-id> --check` so missing or stale exports fail without rewriting files.
- [ ] 3.5 Add validation that generated exports do not rely on hidden global assertions.
- [ ] 3.6 Add validation that unconfigured `llm-rubric` assertions are rejected.
- [ ] 3.7 Prefer deterministic assertions in canonical cases and generated Promptfoo outputs.

## 4. sdlc-evalops Skill Updates

- [ ] 4.1 Update canonical `skills/sdlc-evalops/SKILL.md` to describe `.ai/evals/` as the EvalOps root and target workspaces under `.ai/evals/targets/`.
- [ ] 4.2 Update `sdlc-evalops` instructions for global manifest and target manifest requirements.
- [ ] 4.3 Update `sdlc-evalops` instructions to distinguish session eval from Promptfoo eval.
- [ ] 4.4 Update `sdlc-evalops` instructions for reports policy and required final golden eval reporting fields.
- [ ] 4.5 Update `sdlc-evalops` instructions for deterministic assertion preference, no global assertion pollution, and prohibited unconfigured `llm-rubric`.
- [ ] 4.6 Update `sdlc-evalops` instructions to document `model-matrix.yaml` schema while noting the full matrix runner is deferred.
- [ ] 4.7 Distribute the updated `sdlc-evalops` skill to `.opencode/`, `.claude/`, and `.cursor/` skill copies.

## 5. sdlc-orchestrator Skill Updates

- [ ] 5.1 Update canonical `skills/sdlc-orchestrator/SKILL.md` so new AI skill development and material AI behavior changes identify an EvalOps target and require target-scoped coverage before implementation unless explicitly excepted.
- [ ] 5.2 Add human confirmation boundaries for target registration, coverage acceptance, golden case promotion, and EvalOps exceptions.
- [ ] 5.3 Update orchestrator route decisions so AI behavior changes name the target id when known or route to target identification as the next EvalOps step.
- [ ] 5.4 Require final golden eval or explicitly reported blocked runner dependency before completion claims for EvalOps-gated changes.
- [ ] 5.5 Require final summaries to report target id, case counts, export freshness status, eval command, pass/fail result count, and report path when available.
- [ ] 5.6 Distribute the updated `sdlc-orchestrator` skill to `.opencode/`, `.claude/`, and `.cursor/` skill copies.

## 6. Tests and Verification

- [ ] 6.1 Add tests for `.ai/evals/` manifest presence, required global manifest fields, and target workspace layout.
- [ ] 6.2 Add tests for `skill.sdlc-orchestrator` target manifest fields and workspace directories.
- [ ] 6.3 Add tests for `scripts/export-promptfoo.py` generation from canonical golden cases.
- [ ] 6.4 Add tests for skill source injection into generated Promptfoo prompt content.
- [ ] 6.5 Add tests that `scripts/export-promptfoo.py skill.sdlc-orchestrator --check` detects stale exports.
- [ ] 6.6 Add tests prohibiting global assertion pollution in generated Promptfoo exports.
- [ ] 6.7 Add tests prohibiting unconfigured `llm-rubric` assertions.
- [ ] 6.8 Add tests or static checks that distributed `sdlc-evalops` and `sdlc-orchestrator` skill copies match canonical sources.
- [ ] 6.9 Run `scripts/export-promptfoo.py skill.sdlc-orchestrator --check` and verify exports are fresh.
- [ ] 6.10 Run the `skill.sdlc-orchestrator` Promptfoo golden eval and verify the migrated golden set passes, or document the blocked runner dependency with report path.
- [ ] 6.11 Run local tests and `openspec status --change standardize-ai-evalops-target-workspaces`.

## 7. Deferred Follow-Ups

- [ ] 7.1 Record that full model matrix runner implementation is deferred beyond this batch.
- [ ] 7.2 Record that `skill-creator` integration is deferred to `RM-EVAL-003`.
- [ ] 7.3 Record that `meta-skill-lifecycle-governance` integration is deferred to `RM-EVAL-004`.
