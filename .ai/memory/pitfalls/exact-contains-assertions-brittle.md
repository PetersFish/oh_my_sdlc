---
id: pitfalls/exact-contains-assertions-brittle
type: pitfalls
title: Exact phrase contains assertions are brittle for LLM outputs
summary: Deterministic `contains` assertions like `"OpenSpec proposal"` fail when the model uses semantically equivalent but lexically different terms (e.g. "OpenSpec change", "OpenSpec artifacts").
severity: medium
evidence_mode: session_observation
linked_commits: []
linked_sessions: []
linked_specs: [standardize-ai-evalops-target-workspaces]
sync_status: synced
evidence:
  - eval_run: eval-1m5-2026-06-13T08:40:31
  - failed_case: propose-route-no-direct-exec (test_idx=4)
  - assertion: "Expected output to contain OpenSpec proposal"
  - model_used_terms: "openspec-propose", "OpenSpec artifacts", "proposal.md"
tags: [promptfoo, assertion, contains, robustness, llm]
updated_at: 2026-06-13T08:50:00Z
confidence: high
---

# Exact phrase contains assertions are brittle for LLM outputs

## Symptom

A deterministic `contains` assertion fails with:

```
Expected output to contain "OpenSpec proposal"
```

The model output correctly routes to `openspec-propose` and mentions `OpenSpec artifacts`, `proposal.md`, but doesn't use the exact string `"OpenSpec proposal"`.

## Root Cause

LLM outputs are variable by nature. Requiring exact lexical matches (e.g. `"OpenSpec proposal"`) catches trivial word-choice differences instead of evaluating semantic correctness.

## Fix

- Use `llm-rubric` assertions for semantic/behavioral checks (e.g., "does the response route to OpenSpec proposal creation?")
- Reserve deterministic `contains` assertions for stable, non-negotiable tokens like calibrated skill names (`openspec-propose`, `openspec-new-change`)
- Remove brittle exact-phrase assertions; the rubric already covers the semantics

## Verification

After removing `"OpenSpec proposal"` from `must_include` in the golden case, all 6 cases passed in eval-e80.
