# AI-PEAC Reference: Reusable Analysis Lenses

This file extends [SKILL.md](SKILL.md) with reusable reasoning patterns. Its purpose is not to collect tool names, but to help answer AI architecture questions consistently through stable dimensions, capability-boundary checks, risk lenses, and evolution-path thinking.

---

## Common analysis dimensions

Use these dimensions to decompose AI engineering questions before recommending any framework or implementation path.

### 1. Orchestration and control flow

- How is the workflow expressed: chain, DAG, state machine, planner-executor, multi-agent, or event-driven flow?
- Where is control deterministic, and where is it model-driven?
- What is the rollback or recovery model when a step fails?

### 2. Model access and governance

- How are models routed, versioned, rate-limited, and observed?
- Where do retries, fallbacks, quotas, and policy checks live?
- Is governance embedded in application code, middleware, or a dedicated platform layer?

### 3. Retrieval and knowledge access

- Is the retrieval path single-stage or multi-stage?
- How are chunking, filtering, reranking, freshness, and semantic cache handled?
- What part is static data retrieval versus dynamic business-state lookup?

### 4. State and memory

- What state must persist across turns, workflows, or sessions?
- Is state needed only for context continuity, or also for execution recovery and audit?
- What should remain in business systems instead of being moved into agent memory?

### 5. Observability and debugging

- Can the system explain the path from user request to model/tool decision?
- Are trace, token, latency, and cost visible by request, tenant, and feature?
- Is debugging designed as a first-class capability or added after incidents begin?

### 6. Evaluation and quality control

- What is the gold dataset or benchmark set?
- How are retrieval quality, answer quality, and task completion measured?
- Are quality checks offline only, or also part of release gates and runtime monitoring?

### 7. Safety and compliance

- Where are prompt injection, output filtering, PII control, and tool execution guardrails enforced?
- Which controls are technical, and which rely on workflow or approval process?
- What classes of operations require human confirmation?

### 8. Performance, latency, and cost

- What dominates latency: retrieval, model inference, orchestration, or downstream tools?
- What is the batching, caching, and streaming strategy?
- Is the architecture optimized for median latency, p99 latency, throughput, or cost efficiency?

### 9. Organizational fit

- Which responsibilities belong to product teams, platform teams, and security/governance teams?
- What can be adopted by one service team, and what needs cross-team standards?
- Does the proposed design fit the user's existing Java and microservice operating model?

---

## Capability-boundary checklist

When discussing a framework, platform, or pattern, always classify capabilities into these buckets:

### Native capability

- Fully provided by the framework or platform as a first-class feature
- Low integration friction
- Usually safe to mention as core strength

### Extensible capability

- The framework enables it, but only via plugin, middleware, wrapper, callback, or composition
- Should not be presented as "already solved"
- Requires engineering ownership and testing

### Platform capability

- Should live in a shared gateway, policy layer, evaluation platform, tracing stack, or deployment platform
- Not ideal to duplicate inside each application

### Organizational capability

- Requires process, governance, human review, release discipline, or compliance workflow
- Cannot be solved by framework choice alone

Use this checklist to avoid a common mistake: confusing "possible with customization" with "available out of the box."

---

## Risk lenses

Do not analyze risks only from one angle. Prefer classifying them by lifecycle stage.

### Design-time risks

- Wrong abstraction boundary: putting governance, audit, or policy logic inside ad hoc application code
- Misplaced state: storing business truth in agent memory instead of source-of-truth systems
- Over-coupling to one framework before validating actual workload and org constraints

### Implementation-time risks

- Tool misuse: valid schema but semantically wrong action or parameter
- State explosion: excessive checkpointing, memory growth, or persistence IO in long workflows
- Hidden extension cost: too many critical features depend on custom wrappers or glue code

### Runtime risks

- Trace gaps: no end-to-end visibility across LLM calls, tool calls, retries, and user turns
- Cost drift: token, inference, or retrieval cost increases without clear ownership
- Reliability erosion: fallback loops, cache inconsistency, stale knowledge, or downstream tool flakiness

For each answer, map at least 3 major risks to mitigations.

---

## "ilities" audit prompts

Use these prompts when reviewing an architecture proposal.

## Observability

- Can we reconstruct the full decision path of one request?
- Can we correlate model output, tool invocation, retry, and final response?
- Do we expose token, cost, latency, and failure metrics in business context?

## Safety

- Where is prompt injection handled?
- Where are PII detection, redaction, and retention boundaries enforced?
- Which tools or operations require approval, sandboxing, or human confirmation?

## Testability

- What is the regression dataset?
- How do we measure retrieval quality, answer quality, and task completion separately?
- What is the release gate before prompt, model, or retrieval changes go live?

## Performance

- What is the dominant latency component?
- What is the strategy for warm-up, streaming, backpressure, and cancellation?
- Where do batching, cache, and rate-limiting decisions live?

## Cost

- Which layer owns token and infrastructure cost optimization?
- Is there tenant-level or feature-level cost attribution?
- Do we have a budget guardrail for experimentation versus production?

## Operability

- Who owns incident response when the root cause is ambiguous across model, retrieval, tool, and app layers?
- What can be toggled, rolled back, or degraded safely during production incidents?
- What parts of the system can evolve independently?

---

## Evolution-path template

When the user asks how to adopt AI capabilities in an existing system, prefer a staged path:

### Stage 1: Additive adoption

- Keep core business truth in existing services
- Add a narrow AI capability with clear scope and measurable value
- Avoid introducing broad platform abstractions too early

### Stage 2: Standardize repeated patterns

- Extract shared concerns such as tracing, gateway policy, evaluation, and prompt/version management
- Reduce per-team reinvention
- Define interfaces between business services and AI-facing layers

### Stage 3: Platform consolidation

- Move cross-cutting AI capabilities into shared platform layers
- Establish governance, cost control, release standards, and reusable components
- Reserve advanced orchestration patterns for workflows that truly need them

### Stage 4: AI-native optimization

- Optimize long-session state, model routing, inference efficiency, evaluation loops, and organizational operating model
- Tune for scale, cost, and operability rather than early feature velocity

This template is especially important for senior Java architects, because the right answer is often "evolve the platform boundary" rather than "replace the stack."

---

## Heuristic expansion examples

Use these as prompts to suggest 1–2 follow-up deep topics at the end of a reply:

1. **RAG / retrieval**: "Since we discussed RAG recall, are you interested in how hybrid search balances precision and semantics at B2B scale?"
2. **Agent / transactions**: "In Agent workflows, how can we apply TCC or Saga-style compensation when tool calls have side effects?"
3. **Evaluation loop**: "After introducing evaluation, how do we feed offline and online quality signals back into retrieval, prompts, and release gates?"
4. **Inference / latency**: "With modern inference engines, how do we trade off batching, scheduling, and long context under high QPS?"
5. **Platform boundary**: "Which AI capabilities belong in each application team, and which should become shared platform services?"
6. **Migration path**: "If you start from a Spring Boot microservice landscape, what is the minimum viable AI platform boundary to introduce first?"

Add or vary topics based on the current conversation so the suggestion feels relevant.
