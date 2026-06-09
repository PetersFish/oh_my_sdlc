# 背景
我现在要对openspec-memory-sync进行迭代

# 新增核心需求
- 记忆要和git commit版本 或 spec id关联，需要定义manifest文件
- memory sync要和openspec工作流解耦，方便轻量优化不依赖openspec的场景的记忆同步（涉及skill名称调整）
- pitfalls是不是应该解耦出来，因为这个和commit版本可能关系性不强，反而和某个具体的会话强相关（类似的其他文件也帮忙审查一下
- 提示skill的提升性能和稳定性


# 调研资料参考（来自网页端chatgpt）
````md
# Role

You are a senior AI-native software architect and repository cognition engineer.

Your task is to design and implement a production-grade "Repository Memory Sync Skill System" for AI-assisted software engineering workflows.

The target environment is:

- OpenCode / Codex-style agent workflows
- OpenSpec-driven SDLC
- Git-based repositories
- Long-term AI repository cognition
- Session continuity and architectural memory

The system must prioritize:

- determinism
- low token cost
- long-term maintainability
- extensibility
- agent interoperability
- idempotent execution
- incremental sync
- context compression
- high stability under long project evolution

---

# Core Goal

Design a formalized AI memory synchronization system that:

```text
Git Repository
  → diff analysis
  → structured cognition extraction
  → repository memory update
  → future-agent context loading
````

The system must NOT be a toy demo.

It must be production-oriented and suitable for long-term evolution of medium-to-large AI-native repositories.

---

# Critical Design Principles

## 1. Decouple OpenSpec and Memory System

OpenSpec is NOT the memory system.

OpenSpec represents:

* intent memory
* requirement evolution
* planned change sets

Repository Memory represents:

* repository cognition
* architectural understanding
* module understanding
* long-term engineering knowledge

The final design MUST keep them loosely coupled.

OpenSpec may serve as:

* optional input source
* semantic augmentation source

But memory-sync must also work WITHOUT OpenSpec.

---

## 2. Incremental Sync Architecture

The system MUST support incremental sync.

Do NOT assume memory sync runs on every commit.

Instead:

```text
manifest.last_synced_commit
  ↓
git diff
  ↓
targeted cognition update
```

The system must avoid full-repository rescans whenever possible.

---

## 3. Distinguish Different Memory Types

The design MUST explicitly separate:

```text
Repository Cognition
Execution Memory
Experiential Memory
Intent Memory
```

Specifically:

| Memory Type  | Description                       |
| ------------ | --------------------------------- |
| modules      | module-level cognition            |
| architecture | system-level cognition            |
| decisions    | ADR and design decisions          |
| sessions     | session continuity memory         |
| pitfalls     | experiential failure memory       |
| evolution    | repository evolution timeline     |
| specs        | OpenSpec-derived semantic mapping |
| index        | agent-loadable fast index         |
| manifest     | synchronization metadata          |

The system MUST NOT incorrectly bind all memory to commits.

Example:

* pitfalls may relate to sessions rather than commits
* sessions are execution-state memory
* architecture is semi-versioned cognition
* modules are strongly version-coupled

---

# Required Deliverables

Generate a complete technical design document containing:

---

# Part 1 — System Architecture

Design the overall architecture.

Include:

* component diagram
* data flow
* sync pipeline
* memory lifecycle
* incremental update strategy
* session integration strategy
* OpenSpec integration strategy
* Git integration strategy

Explain tradeoffs.

---

# Part 2 — Repository Structure

Design the full repository layout.

Example areas to include:

```text
.skills/
.ai-memory/
scripts/
templates/
schema/
```

Define responsibilities of each directory.

---

# Part 3 — Memory Data Model

Design ALL memory file schemas.

At minimum include:

## manifest.json

Must include:

* schema_version
* last_synced_commit
* last_synced_at
* sync_strategy
* active_specs
* memory_version
* repository_id

## index.json

Must support fast agent loading.

## module memory schema

## architecture memory schema

## pitfall schema

Pitfalls MUST support:

* session linkage
* commit linkage
* spec linkage
* severity
* status
* mitigation
* recurrence risk

## session schema

Must support:

* unfinished tasks
* temporary context
* pending risks
* recovery hints

---

# Part 4 — Skill Architecture

Design the skill system itself.

The solution MUST NOT rely only on pure-text prompts.

Design a hybrid architecture:

```text
Skill Instructions
+ Scripts
+ Templates
+ Schema Validation
+ Patch Engine
```

Explain:

* what should be deterministic
* what should be AI-generated
* what should be script-driven

---

# Part 5 — Sync Pipeline

Design the exact sync execution flow.

Must include:

```text
1. Load manifest
2. Detect sync range
3. Analyze git diff
4. Detect affected cognition domains
5. Load relevant memory only
6. Generate memory patches
7. Validate schema
8. Apply updates
9. Update manifest
10. Generate summary
```

Design:

* rollback strategy
* dry-run mode
* partial sync
* retry strategy
* corruption prevention
* concurrency handling

---

# Part 6 — Performance Optimization

This section is CRITICAL.

Design strategies for:

* token minimization
* context compression
* selective loading
* memory indexing
* chunking
* stale memory cleanup
* archive strategy
* lazy loading
* fast context hydration

The system must scale to large repositories.

---

# Part 7 — Stability Engineering

Design production-grade safeguards.

Must include:

* idempotent execution
* schema validation
* deterministic scripts
* patch-based updates
* corruption recovery
* malformed memory detection
* sync conflict handling
* duplicate memory prevention

Explain failure modes.

---

# Part 8 — AI-Native Evolution Strategy

Design how the system evolves over time.

Include:

* schema migration strategy
* memory refactoring strategy
* context aging
* memory pruning
* summarization
* long-term compression
* historical archival

---

# Part 9 — Hook and Trigger Strategy

Design integration with:

* git hooks
* manual commands
* CI workflows
* OpenCode sessions
* session handoff

Must support:

```text
pre-commit
post-merge
manual-sync
session-end
checkpoint-save
```

---

# Part 10 — Future Extensibility

Design future expansion capability.

Potential future areas:

* vector retrieval
* graph cognition
* semantic dependency maps
* architectural drift detection
* AI-generated ADR evolution
* automatic anti-regression memory
* multi-agent memory coordination

---

# Implementation Constraints

The design MUST:

* be repository-local first
* work offline
* avoid SaaS dependence
* support git versioning
* support human editing
* support AI editing
* remain understandable by developers
* avoid overengineering

---

# Output Requirements

The final output must be:

* highly structured
* deeply technical
* implementation-oriented
* pragmatic
* production-grade
* explicit about tradeoffs

Avoid vague conceptual discussion.

Prefer:

* architecture
* workflows
* schemas
* execution logic
* operational concerns
* engineering constraints

over philosophical discussion.

Use:

* markdown
* tables
* diagrams
* pseudo-code
* JSON examples
* directory trees

where appropriate.

The output should resemble a serious internal engineering RFC / architecture proposal.

```
```



