## Context

The current EvalOps and Orchestrator skills define rules for eval asset lifecycle and gate enforcement, but they lack explicit forced-interaction checkpoints. After capturing a regression case to inbox, the assistant may stop without asking the user to triage/accept/promote. After implementation completes, the orchestrator may claim completion without running golden eval. When golden eval fails, there is no mandatory failure-analysis step before modifying the target.

The existing `.ai/evals/` infrastructure (manifests, coverage, cases, exports, reports) is stable. The current `sdlc-orchestrator` routing model (superpowers-direct, spec-driven-propose-flow, spec-driven-incremental-flow, roadmap-first, evalops-gated, memory-sync) is proven. This change adds gates within the existing flow, not a new routing path.

## Goals / Non-Goals

**Goals:**
- After `capture` or `generate-cases`, the assistant MUST offer triage actions (accept/revise/reject/keep-in-inbox) before proceeding.
- After `accept`, the assistant MUST offer promotion to golden as a separate step with explicit user confirmation.
- After `run` returns failures, the assistant MUST classify the failure category, present analysis, and require user confirmation before modifying the target or its eval assets.
- The orchestrator MUST enforce that EvalOps lifecycle gates (triage, promote, golden eval) are satisfied before claiming completion for EvalOps-gated changes.
- The orchestrator MUST treat golden eval failure as a blocking gate, not a soft warning.

**Non-Goals:**
- Changing the Promptfoo export/runner scripts.
- Adding automatic fix logic for eval failures.
- Changing the file model of eval assets (manifests, coverage, case YAML).
- Changing the orchestrator route classification logic.

## Decisions

### Decision 1: Triage interaction is a mandatory workflow step, not a suggestion

**Choice:** After `capture` or `generate-cases` writes to inbox, the assistant MUST ask the user which triage action to take (accept/revise/reject/keep-in-inbox) using the `question` tool when available. The assistant SHALL NOT continue to implementation or close the interaction without this prompt.

**Alternatives considered:**
- Text-only prompting without `question` tool: rejected because free-text responses are ambiguous.
- Proactive accept without asking: rejected because AI-generated cases need human review per EvalOps Hard Rule 2.
- Skip triage for critical cases: rejected because EvalOps Hard Rule 7 requires all cases to enter inbox first.

**Rationale:** The `question` tool provides mutually-exclusive options that eliminate ambiguity. This is the same pattern used by the orchestrator for route choices and verification disambiguation.

### Decision 2: Promotion to golden is a separate, explicit confirmation step

**Choice:** After the user selects "accept", the assistant MUST separately ask "Promote `<case-id>` to golden?" The user must explicitly confirm. The assistant SHALL NOT auto-promote even for critical-severity cases.

**Rationale:** EvalOps Hard Rule 3 ("Golden Dataset MUST require human confirmation"). Accept means "this case is valid." Golden means "this case should be a permanent regression gate." These are distinct decisions with different consequences.

### Decision 3: Failure analysis uses a five-category classification

**Choice:** When golden eval returns failures, the assistant MUST classify each failure into one of:
1. **target-behavior-bug**: The target skill's behavior is wrong.
2. **case-expectation-bug**: The eval case's expected behavior is wrong.
3. **evaluator-issue**: The rubric or grader model produces invalid results.
4. **runner-config-issue**: The Promptfoo config, provider, or API key is misconfigured.
5. **model-variance**: The target model output varies within acceptable ranges.

The assistant MUST present the classification and a suggested fix plan, then require user confirmation before modifying anything.

**Rationale:** Different failure causes require different fixes. Auto-fixing without classification risks fixing the wrong thing. This is consistent with EvalOps Hard Rule 6 ("Eval failure MUST NOT trigger automatic fixes").

### Decision 4: Orchestrator EvalOps gate becomes a lifecycle state machine

**Choice:** The orchestrator tracks EvalOps state across the lifecycle:
```
No coverage → coverage reviewed → cases in inbox → cases accepted → cases golden → implementation → pytest pass → golden eval run → golden eval pass → completion
```

Each transition requires either:
- User confirmation (human gates: coverage acceptance, golden promotion, fix plan approval).
- Tool evidence (automated gates: pytest output, golden eval output, export freshness check).

The orchestrator SHALL NOT claim completion if the current state is before `golden eval pass` for EvalOps-gated changes.

**Rationale:** The orchestrator already manages gates for route classification, OpenSpec steps, and roadmap sync. Adding EvalOps lifecycle tracking to this existing gate model is consistent with its role.

## Risks / Trade-offs

- **Risk**: Too many interaction prompts slow down development. → **Mitigation**: Gates apply only to EvalOps-gated targets. Non-AI-behavior changes (pure code, config, docs) are unaffected.
- **Risk**: `question` tool unavailable in some environments. → **Mitigation**: Provide text-based fallback that still requires explicit multi-choice user response.
- **Risk**: Failure classification may be wrong, leading to incorrect fix plan. → **Mitigation**: Classification is presented for user review before any modification. The user can override.
- **Risk**: Golden eval for newly created targets has no golden cases yet. → **Mitigation**: The orchestrator reports "no golden cases available" as a blocked state, not a failure. This is already an existing rule in the orchestrator spec.
