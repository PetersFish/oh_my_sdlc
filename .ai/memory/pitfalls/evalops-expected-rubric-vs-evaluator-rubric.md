---
id: pitfalls/evalops-expected-rubric-vs-evaluator-rubric
type: pitfalls
title: EvalOps golden case expected.rubric is the Promptfoo assertion value — evaluators.llm_judge.rubric is ignored by export
summary: >-
  The `export-promptfoo.py` script maps `expected.rubric` to the promptfoo `llm-rubric` assertion value.
  The `evaluators.llm_judge.rubric` field is NOT used by the export script. Updating only
  `evaluators.llm_judge.rubric` while leaving `expected.rubric` strict has zero effect on golden eval results.
severity: medium
evidence_mode: session_observation
linked_commits: []
linked_sessions: []
linked_specs: [strengthen-evalops-orchestrator-lifecycle-gates]
sync_status: synced
evidence:
  - eval_run: eval-Uyw-2026-06-16T09:46:11
  - eval_run: eval-G5K-2026-06-16T10:19:15
  - eval_run: eval-uwh-2026-06-16T10:22:00
  - eval_run: eval-jh0-2026-06-16T10:44:05
  - eval_run: eval-I5P-2026-06-16T10:47:03
  - eval_run: eval-rpt-2026-06-16T10:48:29
  - case: skill.sdlc-evalops.regression.capture-mandatory-triage
  - root_cause: Updated evaluators.llm_judge.rubric to loosen grading criteria but Promptfoo grader continued using the strict expected.rubric as the assertion value.
  - fix: Update expected.rubric — that is what export-promptfoo.py reads to generate the llm-rubric assertion in cases.yaml
tags: [promptfoo, evals, evalops, rubric, export, llm-rubric]
updated_at: 2026-06-16T11:00:00Z
confidence: high
---

# expected.rubric Is the Promptfoo Assertion Value — evaluators.llm_judge.rubric Is Ignored

## Symptom

Golden eval cases keep failing with the same grader reasoning even after updating the `evaluators.llm_judge.rubric` field to be more lenient. Multiple re-runs produce identical grader scores and failure reasons.

## Root Cause

The canonical export script (`export-promptfoo.py`) reads `expected.rubric` from each golden case YAML and maps it to the Promptfoo `llm-rubric` assertion `value`. The `evaluators.llm_judge.rubric` field is not consumed by the export script and has no effect on the generated `cases.yaml`.

### Mapping (from SKILL.md Promptfoo Export Mapping table)

| Internal Field | Promptfoo Mapping |
|----------------|-------------------|
| `expected.rubric` (configured) | `assert.type: llm-rubric` |

The `evaluators.llm_judge.enabled` flag controls whether an llm-rubric assertion is generated at all, but the actual rubric text comes exclusively from `expected.rubric`.

## How to Detect

1. Make a change to `evaluators.llm_judge.rubric` in a golden case
2. Run `export-promptfoo.py <target-id>`
3. Check the generated `cases.yaml` — the llm-rubric `value` will still be the old `expected.rubric` text unchanged

## Fix

Update `expected.rubric` — not `evaluators.llm_judge.rubric` — when adjusting grading criteria for golden eval cases. After updating `expected.rubric`, re-run `export-promptfoo.py` to regenerate `cases.yaml` with the updated rubric text.

## Prevention

When loosening grader criteria for a golden case:
1. Identify the correct field: `expected.rubric` (not `evaluators.llm_judge.rubric`)
2. Update `expected.rubric`
3. Re-export with `export-promptfoo.py <target-id>`
4. Verify the generated `cases.yaml` has the updated rubric text before re-running eval
