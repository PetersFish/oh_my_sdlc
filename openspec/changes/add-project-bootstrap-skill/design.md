## Context

This repository already has `sdlc-repository-memory-init` for `.ai-memory/` setup and uses OpenSpec CLI for spec-driven development. AGENTS.md is manually maintained. A new project lacks all three, and the developer must know to run each one in the correct order.

Two new skills fill the gaps: `sdlc-openspec-init` handles OpenSpec initialization and schema installation, while `sdlc-project-bootstrap` orchestrates all three foundation steps with an AGENTS.md baseline template and dry-run support.

## Goals / Non-Goals

**Goals:**
- Provide a single entry point (`sdlc-project-bootstrap`) that initializes a new project's foundation (AGENTS.md, OpenSpec + schema, repository memory)
- Provide a standalone `sdlc-openspec-init` skill for reusable OpenSpec initialization, schema discovery, and schema management
- Enforce correct execution order: AGENTS.md -> OpenSpec/schema -> repository memory
- Support dry-run mode that previews planned actions without modifying files
- Be fully idempotent: safe to run repeatedly on the same project
- Use conservative merge for existing AGENTS.md
- Delegate OpenSpec/schema and memory initialization to their respective skills
- Bundle an AGENTS.md baseline template so bootstrap is self-contained for its first step
- Design an extensible step structure so future bootstrap steps can be added naturally

**Non-Goals:**
- Do not reimplement `.ai-memory/` initialization logic
- Do not reimplement OpenSpec CLI logic
- Do not auto-create OpenSpec changes
- Do not auto-run repository memory sync
- Do not auto-commit to git
- Do not overwrite existing AGENTS.md content
- Do not handle language-stack templates (package.json, tsconfig, etc.)

## Decisions

### Decision 1: Orchestration skill, not self-contained

The skill sequences existing tools and templates. OpenSpec/Schema initialization delegates to `sdlc-openspec-init`. Memory initialization delegates to `sdlc-repository-memory-init`. Only AGENTS.md initialization is handled inline because no existing skill covers it.

**Alternatives considered:**
- Self-contained implementation: rejected because it duplicates maintenance of OpenSpec and memory initialization logic.
- Single-skill all-in-one: rejected because OpenSpec schema management (installation, iteration) is a domain concern that benefits from independent testability and upgradeability.

### Decision 2: Fixed execution order

AGENTS.md is initialized first because subsequent tooling (OpenSpec, memory) runs under agent guidance that the AGENTS.md rules are meant to shape. OpenSpec/schema is initialized second because spec-driven development should be available before durable memory records project context. Repository memory is initialized last because memory init appends its reminder block to AGENTS.md after the baseline rules are in place.

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

### Decision 5: Separate `sdlc-openspec-init` skill for schema lifecycle

OpenSpec initialization and schema installation are handled by a dedicated `sdlc-openspec-init` skill. This skill:
- Detects whether OpenSpec is initialized at the project root
- Prompts the user to choose one or more OpenSpec AI tools before init, with `opencode` as the default/recommended selection
- Runs OpenSpec CLI init with `--tools <comma-separated-tools>` when missing
- Lists all available schemas with `openspec schemas --json`, including project-local and package-provided schemas such as `sdd-plus-superpowers` and `spec-driven`
- Prompts the user to choose the default schema when one is not already configured
- Persists the chosen schema to `openspec/config.yaml`
- Copies the `sdd-plus-superpowers` schema from its bundled templates to the project's `openspec/schemas/` directory
- Will support schema iteration (updating existing schemas in future versions)
- Can be invoked standalone or by `sdlc-project-bootstrap`
- Recovers from non-interactive init runs that create OpenSpec state without `openspec/config.yaml` by creating the config when the default schema is persisted

The schema template files are bundled in `skills/sdlc-openspec-init/templates/sdd-plus-superpowers/` and copied from this repository. Bootstrap does NOT own schema templates or lifecycle.

**Alternatives considered:**
- Inline in bootstrap: rejected because schema management is a domain concern; bootstrap should not own schema templates. Schema iteration would force bootstrap updates even when the user only wants to update schemas.
- Use OpenSpec CLI directly from bootstrap: rejected because the CLI does not install the `sdd-plus-superpowers` schema (it's a local schema only present in this repo). The init skill bridges the gap between CLI init and schema installation.

### Decision 6: Dry-run support in v1

`sdlc-project-bootstrap` supports a dry-run mode that reports all planned actions across all steps without modifying any files. This is essential because bootstrap touches multiple infrastructure files and users should be able to preview before committing changes.

`sdlc-openspec-init` also supports dry-run (separately or when invoked via bootstrap), reporting what would be initialized, created, or copied.

**Alternatives considered:**
- Defer to v2: rejected because bootstrap is a multi-step file-modifying operation; a preview mechanism is essential for first-use confidence.
- CLI flag only: rejected as too coupled to execution environment. The skill should support conversational dry-run invocation (e.g., "preview the bootstrap" or "what would this do?").

### Decision 7: Memory init delegated, sync not auto-run

The skill delegates `.ai-memory/` setup to `sdlc-repository-memory-init`. It does NOT auto-run `sdlc-repository-memory-sync` because sync may produce review-queue entries or pending memory that needs developer review before commitment.

**Alternatives considered:**
- Auto-sync after init: rejected because it produces un-reviewed memory artifacts.
- Skip memory entirely: rejected because repository memory is a core part of the project foundation.

## Risks / Trade-offs

- **Risk: AGENTS.md template drifts from this repository's actual AGENTS.md.** -> Mitigation: the template is a copy at creation time; a future sync mechanism or test could detect drift.
- **Risk: `sdd-plus-superpowers` schema bundled in openspec-init drifts from source.** -> Mitigation: the template directory is sourced from this repository; tests should compare against the canonical schema.
- **Risk: Conservative merge may miss intentional deletions.** -> Mitigation: the merge only appends missing blocks; it never removes content. Deleted blocks must be removed manually.
- **Risk: Future steps added without clear ordering.** -> Mitigation: the skill explicitly defines the step order and guards it with preconditions.
- **Risk: Two independent skills increase distribution surface.** -> Mitigation: both follow same canonical `skills/` structure; existing skill copy mechanisms already handle this.
