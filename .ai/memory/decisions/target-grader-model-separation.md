---
id: decisions/target-grader-model-separation
type: decisions
title: Separate target eval model from grader model in Promptfoo config
summary: The target model (deepseek-v4-pro) and the llm-rubric grader model (glm-5.1) are configured independently in model-matrix.yaml, driven by separate `promptfoo` and `grader` blocks. This avoids JSON extraction failures when reasoning models are used as graders.
status: accepted
evidence_mode: session_observation
linked_sessions: []
sync_status: synced
rationale: >
  DeepSeek V4 Pro is a strong target model but a poor grader because its reasoning output
  format breaks Promptfoo's llm-rubric JSON parser. GLM-5.1 has stable structured output
  and works reliably as a grader. Separating the two in the configuration allows each to
  be tuned independently (different models, temperature, max_tokens).
alternatives_considered:
  - "Use same model for both target and grader (rejected: JSON extraction failures)"
  - "Remove llm-rubric from cases (rejected: loses semantic grading capability)"
linked_commits: []
linked_specs: [standardize-ai-evalops-target-workspaces]
tags: [promptfoo, grader, model-matrix, evalops, deepseek, glm]
updated_at: 2026-06-13T17:00:00Z
confidence: high
---

# Separate target eval model from grader model

## Context

Promptfoo `promptfooconfig.yaml` has two model configuration points:
- `providers[].config` — the target model being evaluated
- `defaultTest.options.provider.config` — the grader model for `llm-rubric` assertions

## Decision

Target model: `deepseek-v4-pro` (reasoning model, good at task classification)
Grader model: `glm-5.1` (non-reasoning model, stable JSON output)

Both use Promptfoo's built-in OpenAI-compatible provider (`openai:chat:<model>`) calling the OpenAI-compatible endpoint at `https://opencode.ai/zen/go/v1`. No custom Python provider is needed.

## Configuration

In `.ai/evals/model-matrix.yaml`:

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

`scripts/export-promptfoo.py` reads both blocks and generates the appropriate provider sections.

## Consequences

- Target model can be upgraded independently (e.g., to a newer DeepSeek version)
- Grader model can be swapped if JSON stability degrades
- Both use the built-in `openai:chat:` provider; no custom Python provider required
- `max_tokens` can differ between target and grader if needed
- `headers.Accept-Encoding: identity` is required for opencode-go endpoint to prevent Node/undici `TypeError: terminated`
