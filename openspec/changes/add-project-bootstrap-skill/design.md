## Context

This repository already has `sdlc-repository-memory-init` for `.ai-memory/` setup and uses OpenSpec CLI for spec-driven development. AGENTS.md is manually maintained. A new project lacks all three, and the developer must know to run each one in the correct order.

This skill fills the gap as a lightweight orchestrator. It does not reimplement existing capabilities; it sequences them and adds the one piece not covered by existing skills: AGENTS.md initialization.

## Goals / Non-Goals

**Goals:**
- Provide a single skill that initializes a new project's foundation (AGENTS.md, OpenSpec, repository memory)
- Enforce correct execution order: AGENTS.md -> OpenSpec -> repository memory
- Be fully idempotent: safe to run repeatedly on the same project
- Use conservative merge for existing AGENTS.md
- Delegate OpenSpec and memory initialization to their respective tools
- Bundle an AGENTS.md baseline template so the skill is self-contained for its first step
- Design an extensible step structure so future bootstrap steps (README, CI, .gitignore) can be added naturally

**Non-Goals:**
- Do not reimplement `.ai-memory/` initialization logic
- Do not reimplement OpenSpec initialization logic
- Do not auto-create OpenSpec changes
- Do not auto-run repository memory sync
- Do not auto-commit to git
- Do not overwrite existing AGENTS.md content
- Do not handle language-stack templates (package.json, tsconfig, etc.)

## Decisions

### Decision 1: Orchestration skill, not self-contained

The skill sequences existing tools and templates. OpenSpec initialization calls the OpenSpec CLI. Memory initialization delegates to `sdlc-repository-memory-init`. Only AGENTS.md initialization is handled inline because no existing skill covers it.

**Alternatives considered:**
- Self-contained implementation: rejected because it duplicates maintenance of OpenSpec and memory initialization logic.
- Multi-skill pipeline (one skill per step): rejected as premature for v1; structure allows future decomposition if individual steps grow complex.

### Decision 2: Fixed execution order

AGENTS.md is initialized first because subsequent tooling (OpenSpec, memory) runs under agent guidance that the AGENTS.md rules are meant to shape. OpenSpec is initialized second because spec-driven development should be available before durable memory records project context. Repository memory is initialized last because memory init appends its reminder block to AGENTS.md after the baseline rules are in place.

**Alternatives considered:**
- Parallel initialization: rejected because memory init modifies AGENTS.md, creating a race with the AGENTS step.
- Memory before OpenSpec: rejected because early spec artifacts can't be created without OpenSpec, and memory is less useful without specs to track.

### Decision 3: AGENTS.md template bundled in skill

The baseline AGENTS.md content (current repository AGENTS.md L1-61) lives in `skills/sdlc-project-bootstrap/templates/AGENTS.md`. The skill uses it to create a new AGENTS.md when one is missing. This keeps the skill self-contained for its first step without requiring an external reference.

**Alternatives considered:**
- Hardcode content in SKILL.md: rejected because it bloats the skill definition and makes content updates harder.
- Separate `sdlc-agents-init` skill: rejected as premature; AGENTS.md initialization is a single template copy plus conservative merge. If it grows more complex (multiple profiles, team templates, block merging), it can be extracted later.

### Decision 4: Conservative merge for existing AGENTS.md

When AGENTS.md already exists, the skill reads it and appends only standard blocks that are missing. It never replaces or removes existing content. Duplicate detection prevents appending a block that already appears in the file.

**Alternatives considered:**
- Always create fresh template: rejected because it would overwrite project-specific agent instructions.
- Prompt user on every conflict: rejected because it adds friction; existing content is always preserved by default.

### Decision 5: OpenSpec init delegates to CLI

The skill checks for `openspec/config.yaml` or equivalent markers. If OpenSpec is not initialized, the skill instructs the executor to run the OpenSpec CLI init command. After init, it suggests the next command for creating a change with the repository's preferred schema.

**Alternatives considered:**
- Create `openspec/config.yaml` from a template: rejected because it requires maintaining schema-specific templates and diverges from the canonical OpenSpec init path.
- Create `sdlc-openspec-init` skill: rejected as premature; the OpenSpec CLI is the canonical init tool.

### Decision 6: Memory init delegated, sync not auto-run

The skill delegates `.ai-memory/` setup to `sdlc-repository-memory-init`. It does NOT auto-run `sdlc-repository-memory-sync` because sync may produce review-queue entries or pending memory that needs developer review before commitment.

**Alternatives considered:**
- Auto-sync after init: rejected because it produces un-reviewed memory artifacts.
- Skip memory entirely: rejected because repository memory is a core part of the project foundation.

## Risks / Trade-offs

- **Risk: AGENTS.md template drifts from this repository's actual AGENTS.md.** -> Mitigation: the template is a copy at creation time; a future sync mechanism or test could detect drift.
- **Risk: OpenSpec CLI behavior changes break the skill.** -> Mitigation: the skill uses documented CLI entry points; breaking changes would be caught when the skill is tested.
- **Risk: Conservative merge may miss intentional deletions.** -> Mitigation: the merge only appends missing blocks; it never removes content. Deleted blocks must be removed manually.
- **Risk: Future steps added without clear ordering.** -> Mitigation: the skill explicitly defines the step order and guards it with preconditions.

## Open Questions

- Should the skill support a `--dry-run` flag to preview what would be initialized without making changes? (Defer to v2.)
- Should the skill detect and prompt for `sdd-plus-superpowers` schema availability during OpenSpec init? (Yes, suggestion only in v1.)
