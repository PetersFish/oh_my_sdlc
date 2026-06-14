## 1. Runner Structure

- [x] 1.1 Add `scripts/run-eval-matrix.py` CLI with target-id argument, optional all-target mode, and model selection flags if needed.
- [x] 1.2 Load `.ai/evals/manifest.yaml`, `.ai/evals/model-matrix.yaml`, and target workspace manifests with clear errors for missing or invalid files.
- [x] 1.3 Resolve target selection from explicit CLI target id or `target_selection` defaults in `model-matrix.yaml`.
- [x] 1.4 Resolve model entries from `models[]` and fail clearly when no entries are configured.

## 2. Per-Model Export Generation

- [x] 2.1 Reuse or mirror golden-case export mapping from `scripts/export-promptfoo.py` while parameterizing provider and grader by matrix entry.
- [x] 2.2 Generate run-scoped Promptfoo files under `.ai/evals/targets/<target-id>/reports/<matrix-run-id>/<model-name>/promptfoo/`.
- [x] 2.3 Ensure matrix generation does not rewrite canonical `.ai/evals/targets/<target-id>/exports/promptfoo/` files.
- [x] 2.4 Preserve `apiKeyEnvar` and `headers.Accept-Encoding: identity` in generated per-model configs without writing raw API keys.

## 3. Matrix Execution and Reports

- [x] 3.1 Execute `promptfoo eval` for each target/model pair with `-o <per-model-report>/promptfoo-output.json`, `--max-concurrency 1`, and `--no-cache`.
- [x] 3.2 Write per-model `summary.md` and `failures.yaml` with total, pass, fail, and error counts.
- [x] 3.3 Write aggregate target-level matrix `summary.md` grouping results by model.
- [x] 3.4 Record configured provider/model metadata and observed metadata when available from generated config or Promptfoo output.
- [x] 3.5 Honor `run_policy.fail_fast` while still writing summaries for completed and failed runs.
- [x] 3.6 Exit non-zero if any model run fails or returns errors after writing available reports.

## 4. Documentation and Skill Distribution

- [x] 4.1 Update `skills/sdlc-evalops/SKILL.md` to document the matrix runner command, report layout, and boundaries.
- [x] 4.2 Distribute updated `sdlc-evalops` skill docs to `.opencode/`, `.claude/`, and `.cursor/` copies.
- [x] 4.3 Ensure documentation keeps CI integration and advanced analytics explicitly out of scope.

## 5. Tests

- [x] 5.1 Add tests that `scripts/run-eval-matrix.py` exists and reads model matrix fields.
- [x] 5.2 Add tests that generated per-model configs use the selected model entry's `promptfoo` and `grader` blocks.
- [x] 5.3 Add tests that canonical `exports/promptfoo/` files are not mutated by matrix config generation.
- [x] 5.4 Add tests that per-model and aggregate report paths are target-scoped and include model names.
- [x] 5.5 Add tests that raw API key values are not written and `Accept-Encoding: identity` is preserved.
- [x] 5.6 Add tests that distributed `sdlc-evalops` copies match canonical documentation.

## 6. Verification

- [x] 6.1 Run `python3 -m pytest tests/test_evalops_root.py tests/test_evalops_skill.py`.
- [x] 6.2 Run `python3 scripts/run-eval-matrix.py skill.sdlc-orchestrator --dry-run` or equivalent non-provider verification if implemented.
- [x] 6.3 If `OPENCODE_GO_API_KEY` is available, run a live matrix eval for `skill.sdlc-orchestrator`; otherwise document the blocked credential dependency.
- [x] 6.4 Run `openspec status --change add-eval-matrix-runner` and confirm implementation tasks are complete before verification/archive.
