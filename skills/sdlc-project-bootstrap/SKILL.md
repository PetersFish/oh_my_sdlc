---
name: sdlc-project-bootstrap
description: Use when initializing a new project foundation, bootstrapping AGENTS.md, setting up OpenSpec and repository memory for a new project, preparing a project for spec-driven development, or when the user asks to set up, initialize, or bootstrap a project from scratch. Also use when the user needs a project foundation dry-run preview before making changes. Use ONLY for new-project setup; do NOT use for adding features to an already-initialized project unless the user explicitly asks to re-run foundation initialization.
license: MIT
---

# Project Bootstrap

Orchestrates project foundation initialization by sequencing three steps in fixed order:

1. `AGENTS.md` initialization
2. OpenSpec + schema initialization (delegates to `sdlc-openspec-init`)
3. Repository memory initialization (delegates to `sdlc-repository-memory-init`)

Each step is idempotent. Running bootstrap multiple times on the same project is safe and only adds what is missing.

## When to Use

- The user asks to initialize a new project, set up project foundation, or bootstrap a project.
- The user says "new project", "scaffold project", "init project", "project setup".
- The user asks to create AGENTS.md for a project that does not have one.
- The user asks to set up OpenSpec and repository memory together.
- Dry-run preview: user wants to see what would be initialized without making changes.

## Workflow

### Step 0: Detect project root

Determine the repository root. If ambiguous, ask the user.

### Step 1: Initialize AGENTS.md

Check whether `AGENTS.md` exists at the repository root.

**If AGENTS.md does not exist:**
- Create `AGENTS.md` from the bundled template at `skills/sdlc-project-bootstrap/templates/AGENTS.md`.
- Report: "AGENTS.md: created from baseline template".

**If AGENTS.md exists:**
- Read the existing file.
- Check whether it contains the standard agent behavior guidance (the content from the bundled template).
- If all standard blocks are present: report "AGENTS.md: already initialized, no changes needed".
- If some standard blocks are missing: append only the missing blocks. Never remove or replace existing content.
- Report: "AGENTS.md: appended missing standard blocks ([list of appended sections])".

**Duplicate detection:**
- Before appending any block, check if its heading or key content already appears in the file.
- Skip appending if the block is already present.

**Repository Memory reminder:**
The bundled AGENTS.md template does NOT include the Repository Memory reminder. This block will be added by `sdlc-repository-memory-init` in step 3 if the user agrees to the memory-load reminder prompt.

### Step 2: Initialize OpenSpec

Delegate to `sdlc-openspec-init` for OpenSpec CLI initialization, schema discovery, asking the user to choose a default schema, and schema installation. The bootstrap skill does NOT perform OpenSpec initialization directly.

Treat this as a delegation contract. The OpenSpec step is only complete when `sdlc-openspec-init` returns all of these fields:
- OpenSpec: [created / already present]
- AI tools: [selected by user]
- Default schema: [selected by user]

If the result is missing `AI tools` or `Default schema`, treat the OpenSpec step as incomplete, run standalone `sdlc-openspec-init` to recover, and stop if recovery still cannot produce those fields.

Report the result from `sdlc-openspec-init`:
- OpenSpec: [created / already present]
- AI tools: [selected by user]
- Default schema: [selected by user]

If `sdlc-openspec-init` fails, report the error and stop. Do NOT proceed to step 3.

### Step 3: Initialize Repository Memory

Check whether `.ai/memory/manifest.json` exists at the project root.

**If manifest.json exists:**
- Report "Repository memory: already initialized, no changes needed".
- Suggest running `sdlc-repository-memory-sync` separately if the user wants to populate memory.

**If manifest.json does not exist:**
- Delegate to `sdlc-repository-memory-init` to create the `.ai/memory/` directory structure, manifest, index, templates, and gitignore.
- Report the result from `sdlc-repository-memory-init`.
- Do NOT auto-run `sdlc-repository-memory-sync`. Only suggest it as a next step.

### Step 4: Summary

After all steps complete, output a summary:

```
Project Foundation Bootstrap Complete

AGENTS.md: [created | already present | appended missing blocks]
OpenSpec: [initialized | already present]
  AI tools: [selected]
  Default schema: [selected]
Repository Memory: [initialized | already present]

Suggested next steps:
  1. Create your first change: openspec new change <name>
  2. Populate repository memory: run sdlc-repository-memory-sync
```

## Dry-run Mode

When the user requests dry-run ("dry run", "preview", "what would this do", "--dry-run"), run the detection steps (check whether AGENTS.md, OpenSpec, schema, and memory exist) but do NOT modify any files. Report what would be done:

```
Dry-run preview:

AGENTS.md: [would create from template | would append missing blocks | already present]
OpenSpec: [would initialize via openspec init | already present]
  AI tools: [would prompt for selection | already selected]
  Default schema: [would prompt for selection | already selected]
Repository Memory: [would initialize via sdlc-repository-memory-init | already present]
```

## Guardrails

- Do NOT auto-commit to git under any circumstances.
- Do NOT auto-run `sdlc-repository-memory-sync` after initialization.
- Do NOT auto-create an OpenSpec change.
- Do NOT overwrite existing AGENTS.md content.
- Do NOT reimplement OpenSpec or memory initialization logic — always delegate.
- Do NOT run `openspec init` directly in bootstrap; always delegate to `sdlc-openspec-init`.
- Do NOT report "Project Foundation Bootstrap Complete" if the OpenSpec result does not include both `AI tools` and `Default schema`.
- Do NOT skip steps when a step fails; stop and report the error.
- Execute steps in order: AGENTS.md first, then OpenSpec, then memory.
