# Skill Taxonomy

This document defines the classification system for skills in this repository. It serves as a reference for naming conventions, trigger boundaries, and conflict resolution priorities.

## Prefix Semantics

| Prefix | Meaning | Examples |
|--------|---------|----------|
| `qa-*` | Instant Q&A / coaching skills. Answer questions directly in chat, do not create durable file artifacts. | `qa-ai-architecture` |
| `research-*` | Durable local research topic lifecycle management. Creates and manages files under `research/` directory with run/rerun/archive/wiki workflows. | `research-general` |
| `sdlc-*` | Software development lifecycle skills. Repository memory management, OpenSpec workflow gates, code-change tracking. | `sdlc-repository-memory-init`, `sdlc-repository-memory-load`, `sdlc-repository-memory-sync`, `sdlc-openspec-memory-sync` |
| `transform-*` | Atomic content transformation / rendering skills. Single-purpose: convert text to diagram, enforce format rules, render pseudocode. | `transform-algo-render`, `transform-markdown-svg`, `transform-math-formula`, `transform-xmind` |
| `study-*` | Composite skills that orchestrate learning note generation. Delegate rendering to atomic `transform-*` skills. | `study-zybook-notes` |
| `media-*` | Media reading, routing, and OCR skills. Handle clipboard images, screenshot processing, Markdown-embedded media inspection. | `media-ocr-router` |
| `integration-*` | External service integration skills. Sync data to/from third-party platforms. | `integration-notion-sync` |
| `ops-*` | Operational / backup skills. Filesystem backup and configuration management. | `ops-mackup-backup` |
| `meta-skill-*` | Skills about managing skills themselves. Lifecycle governance, creation, evaluation. | `meta-skill-lifecycle-governance` |
| discipline-oriented names | Cross-cutting engineering guardrails that are loaded only at the relevant work phase. | `implementation-contract-discipline`, `behavioral-test-design` |

## Skill Types

| Type | Description | Identified by |
|------|-------------|---------------|
| **atomic** | Single-purpose transform/render. Takes input, produces output. No delegation to other skills. | `transform-*` skills |
| **composite** | Orchestrates multiple atomic skills to produce a complete artifact. Owns the output structure; delegates rendering. | `study-*` skills |
| **adapter** | Thin wrapper that collects domain-specific context and delegates to a core skill. Does not duplicate the core's logic. | `sdlc-openspec-memory-sync` |
| **qa** | Conversational coaching. Answers questions with structured analysis. No file artifact creation. | `qa-*` skills |
| **lifecycle** | Manages a stateful workflow with multiple phases (init, create, run, archive). Filesystem is the source of truth. | `research-*`, `sdlc-*` skills |
| **utility** | Performs a specific operational task. Stateless or minimal state. | `ops-*`, `integration-*`, `media-*` skills |
| **discipline** | Enforces cross-cutting engineering quality rules for implementation or test design. Loaded on demand to avoid bloating global instructions. | `implementation-contract-discipline`, `behavioral-test-design` |

## Trigger Conflict Priorities

When multiple skills could match a user request, resolve conflicts in this order:

1. **Explicit skill name invocation wins.** If the user names a skill directly, use it regardless of description overlap.

2. **Adapter-gate skills before core skills.** When a skill is a thin wrapper around a core skill (e.g., `sdlc-openspec-memory-sync` wraps `sdlc-repository-memory-sync`), the adapter triggers only in its specific gate scenario (verified-before-archive). The core skill handles all other invocations.

3. **Composite orchestrators before atomic renderers.** When a user asks for a complete output (e.g., "summarize this chapter with diagrams and pseudocode"), the composite skill (`study-zybook-notes`) takes precedence over individual atomic skills (`transform-algo-render`, `transform-markdown-svg`). When only a single transformation is requested (e.g., "draw this flowchart"), the atomic skill triggers directly.

4. **Specific-domain skills before general-purpose skills.** A domain-specific skill (e.g., `qa-ai-architecture` for AI architecture questions) takes precedence over a general lifecycle skill (e.g., `research-general`), unless the user explicitly wants a durable research topic.

5. **Durable artifact skills require explicit lifecycle intent.** Skills that create files and manage state (research, memory sync) should only trigger when the user's intent clearly involves the lifecycle workflow, not when they ask a simple question in the same domain.

## Skill Relationship Map

```
study-zybook-notes (composite)
├── delegates to → transform-algo-render (atomic)
├── delegates to → transform-markdown-svg (atomic)
└── delegates to → transform-math-formula (atomic)

sdlc-openspec-memory-sync (adapter)
├── delegates to → sdlc-repository-memory-load (lifecycle)
└── delegates to → sdlc-repository-memory-sync (lifecycle)

sdlc-repository-memory-sync (lifecycle)
├── depends on → sdlc-repository-memory-init (lifecycle)
└── depends on → sdlc-repository-memory-load (lifecycle)
```
