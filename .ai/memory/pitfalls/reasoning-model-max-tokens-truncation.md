---
id: pitfalls/reasoning-model-max-tokens-truncation
type: pitfalls
title: Low max_tokens causes output truncation for reasoning models
summary: DeepSeek V4 Pro consumes reasoning tokens from the max_tokens budget, leaving insufficient quota for content. With max_tokens=2000, outputs can be truncated to as few as 136 characters.
severity: high
evidence_mode: session_observation
linked_commits: []
linked_sessions: []
linked_specs: [standardize-ai-evalops-target-workspaces]
sync_status: synced
evidence:
  - eval_run: eval-1m5-2026-06-13T08:40:31
  - truncated_output_chars: 136
  - case: execute-plan-after-propose-route (test_idx=2)
  - max_tokens_setting: 2000
tags: [promptfoo, max_tokens, deepseek, reasoning, truncation]
updated_at: 2026-06-13T08:50:00Z
confidence: high
---

# Low max_tokens causes output truncation for reasoning models

## Symptom

LLM outputs are truncated mid-sentence. For example, a response expected to contain route instructions stops after partial phrase:

```
## SDLC Route Decision Follow-up
Route: spec-driven-propose-flow
You asked to execute the plan. Since the previous classification is `
```

The grader then fails because the output lacks the expected content.

## Root Cause

DeepSeek V4 Pro's reasoning tokens count against the `max_tokens` budget. With `max_tokens: 2000`, the model may spend most tokens on internal reasoning (visible in `reasoning_content`), leaving very few tokens for actual `content`. In one observed case, only 136 characters of content were produced.

## Fix

Increase `max_tokens` for reasoning model targets to at least 4096 to leave room for both reasoning and content output:

```yaml
config:
  model: deepseek-v4-pro
  temperature: 0
  max_tokens: 4096
```

## Verification

6/6 golden cases passed in eval-e80 with max_tokens=4096, all outputs complete with proper route instructions.
