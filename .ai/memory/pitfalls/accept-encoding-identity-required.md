---
id: pitfalls/accept-encoding-identity-required
type: pitfalls
title: opencode-go OpenAI-compatible provider fails with TypeError terminated without Accept-Encoding identity
summary: Promptfoo's built-in openai:chat provider throws `TypeError: terminated` in 2-4 seconds when calling opencode-go endpoint if `Accept-Encoding: identity` is not set in provider config headers.
severity: critical
evidence_mode: session_observation
linked_commits: [65d7410]
linked_sessions: []
linked_specs: [standardize-ai-evalops-target-workspaces]
sync_status: synced
evidence:
  - error: "TypeError: terminated"
  - http_status: 0
  - response: "Unable to read response"
  - node_version: v26.0.0
  - promptfoo_version: 0.121.15
  - env_warning: "ExperimentalWarning: DecompressInterceptor is experimental"
  - repro_count: 7+ eval runs failed (smoke + full orchestrator)
  - fix: add headers.Accept-Encoding: identity to provider and grader config
  - root_cause: Node/undici decompress interceptor fails on compressed responses from opencode-go endpoint
tags: [promptfoo, openai, opencode-go, undici, TypeError, Accept-Encoding, compression, node]
updated_at: 2026-06-13T17:00:00Z
confidence: high
---

# opencode-go OpenAI-compatible provider fails with TypeError: terminated

## Symptom

Every Promptfoo eval case fails with `TypeError: terminated` in 2-4 seconds:

```
API call error: TypeError: terminated
```

The HTTP status is 0 (no response received). The error log shows:

```
responsePreview: {"error":"API call error: TypeError: terminated","metadata":{"http":{"status":0,"statusText":"Error"...
```

Node emits a warning:

```
ExperimentalWarning: DecompressInterceptor is experimental and subject to change
```

The failure is NOT a timeout — it occurs in 2-4 seconds regardless of `REQUEST_TIMEOUT_MS` or `PROMPTFOO_EVAL_TIMEOUT_MS` settings.

Curl and Python `urllib.request` call the same endpoint successfully (HTTP 200), confirming the issue is specific to Promptfoo's Node/undici HTTP client.

## Root Cause

The opencode-go endpoint (`https://opencode.ai/zen/go/v1/chat/completions`) may return compressed responses. Promptfoo/Node's `DecompressInterceptor` (undici) fails to decompress them, causing the connection to be terminated before any response content is read.

## Fix

Add `headers.Accept-Encoding: identity` to both the target provider and grader provider config in `.ai/evals/model-matrix.yaml`:

```yaml
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

This instructs the server to return uncompressed responses, bypassing the undici decompress bug entirely.

## Contract Requirements

When configuring opencode-go for Promptfoo eval:

1. `apiBaseUrl` must be `https://opencode.ai/zen/go/v1` — base URL only; do NOT append `/chat/completions`
2. `apiKeyEnvar` must reference `OPENCODE_GO_API_KEY`
3. `headers.Accept-Encoding: identity` is REQUIRED for both provider and grader
4. Provider id must be `openai:chat:<model>` (built-in), not a custom `file://` provider

## Verification

- Smoke test: `.ai/evals/smoke/promptfooconfig.yaml` with `Accept-Encoding: identity` passes (1/1)
- Full orchestrator eval: 6/6 golden cases pass with same header config
- Tests assert `Accept-Encoding: identity` in model-matrix, generated config, smoke config, and skill docs
