---
id: pitfalls/deepseek-v4-pro-grader-json-extraction-failure
type: pitfalls
title: DeepSeek V4 Pro causes llm-rubric JSON extraction failures
summary: Reasoning models like deepseek-v4-pro put output in `reasoning_content` instead of `content`, causing Promptfoo llm-rubric to fail with "Could not extract JSON from llm-rubric response".
severity: high
evidence_mode: session_observation
linked_commits: []
linked_sessions: []
linked_specs: [standardize-ai-evalops-target-workspaces]
sync_status: synced
evidence:
  - eval_run: eval-11a-2026-06-13T08:16:34
  - failed_case_count: 2
  - error: "Could not extract JSON from llm-rubric response"
  - grader_model: deepseek-v4-pro
  - target_model: deepseek-v4-pro
tags: [promptfoo, llm-rubric, grader, deepseek, json, reasoning]
updated_at: 2026-06-13T17:00:00Z
confidence: high
---

# DeepSeek V4 Pro causes llm-rubric grader JSON extraction failures

## Symptom

Promptfoo `llm-rubric` assertions fail with:

```
Could not extract JSON from llm-rubric response
```

The grader provider returns HTTP 200 but Promptfoo cannot parse the response as JSON.

## Root Cause

DeepSeek V4 Pro is a reasoning model. It may put generated text in `reasoning_content` rather than `content` in the OpenAI-compatible response. Promptfoo's `llm-rubric` assertion expects a JSON object in the response body, but reasoning content is unstructured text.

## Fix

Use a non-reasoning model as the grader for `llm-rubric` assertions. In `.ai/evals/model-matrix.yaml`, separate the target provider from the grader provider:

```yaml
models:
  - name: opencode-go-deepseek-v4-pro
    provider: opencode-go
    model: deepseek-v4-pro
    promptfoo:
      id: openai:chat:deepseek-v4-pro
      config:
        apiBaseUrl: https://opencode.ai/zen/go/v1
        apiKeyEnvar: OPENCODE_GO_API_KEY
        headers:
          Accept-Encoding: identity
        temperature: 0
        max_tokens: 4096
    grader:
      id: openai:chat:glm-5.1
      config:
        apiBaseUrl: https://opencode.ai/zen/go/v1
        apiKeyEnvar: OPENCODE_GO_API_KEY
        headers:
          Accept-Encoding: identity
        temperature: 0
        max_tokens: 4096
```

Note: `apiBaseUrl` must be the base URL only; Promptfoo appends `/chat/completions`. `headers.Accept-Encoding: identity` prevents `TypeError: terminated` from Node/undici decompress interceptor.

Recommended grader models: GLM-5.1, Qwen3.7 Max, Kimi K2.7.

## Verification

6/6 golden cases passed in eval-e80 with GLM-5.1 grader, 0 errors.
