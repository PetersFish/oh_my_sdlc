---
name: sdlc-openspec-init
description: Use when setting up OpenSpec in a new or existing project, initializing the openspec/ directory, installing or updating the sdd-plus-superpowers schema, or when the user asks to set up OpenSpec for spec-driven development. Use ONLY when the task involves OpenSpec configuration or schema management; do NOT use for general project initialization (see sdlc-project-bootstrap instead).
license: MIT
---

# OpenSpec Init

Initializes OpenSpec in a project and installs the `sdd-plus-superpowers` workflow schema. Can be used standalone or as a delegate of a project bootstrap orchestrator.

## When to Use

- The user asks to set up OpenSpec in a new or existing project.
- The user asks to install or update the `sdd-plus-superpowers` schema.
- A project has OpenSpec CLI but is missing the `sdd-plus-superpowers` schema.
- A project bootstrap orchestrator delegates the OpenSpec step here.
- Schema iteration: the schema bundled in this skill is newer than the one installed in the target project.

## Workflow

### 1. Detect project root

Determine the repository root. If not clear, ask the user.

### 2. Detect OpenSpec state

Check whether `openspec/config.yaml` exists at the project root.

- **Exists**: Report "OpenSpec already initialized". Skip CLI init.
- **Missing**: Proceed to step 3.

### 3. Initialize OpenSpec (if missing)

Run OpenSpec CLI initialization:

```bash
openspec init
```

After init completes, confirm `openspec/config.yaml` was created. If the init command fails, report the error and stop.

### 4. Detect schema state

Check whether `openspec/schemas/sdd-plus-superpowers/` exists at the project root.

- **Exists**: Report "sdd-plus-superpowers schema already installed". Skip installation.
- **Missing**: Proceed to step 5.

### 5. Install schema (if missing)

Copy the bundled schema template from this skill's `templates/sdd-plus-superpowers/` to the project's `openspec/schemas/` directory:

```
skills/sdlc-openspec-init/templates/sdd-plus-superpowers/
  → <project-root>/openspec/schemas/sdd-plus-superpowers/
```

The schema template includes:
- `schema.yaml`: Workflow schema definition
- `templates/`: Artifact templates (brainstorm.md, proposal.md, design.md, spec.md, tasks.md, plan.md, verify.md)
- `README.md`: Schema documentation

If the `openspec/schemas/` directory does not exist, create it first.

### 6. Report result

After initialization, output a summary:

```
OpenSpec initialized: [created / already present]
sdd-plus-superpowers schema: [installed / already present]

Suggested next step:
  openspec new change <name> --schema sdd-plus-superpowers
```

### 7. Dry-run mode

When the user requests dry-run (e.g., "dry run", "preview", "what would this do"), report planned actions without modifying any files:

```
Dry-run preview:

Planned actions:
  - [init] OpenSpec: openspec init (not yet initialized)
  - [skip] OpenSpec: already initialized at openspec/config.yaml
  - [install] sdd-plus-superpowers schema: copy from templates to openspec/schemas/
  - [skip] sdd-plus-superpowers schema: already installed at openspec/schemas/sdd-plus-superpowers/
```

Only show actions that would actually be taken (skip the skip entries if nothing is already present). Do NOT execute any actions in dry-run mode.

## Standalone Invocation

This skill can be invoked independently of any project bootstrap orchestrator. When invoked standalone:
- Run steps 1-6 as described above.
- The skill does NOT depend on bootstrap context.

## Schema Iteration

When the skill is invoked on a project that already has the schema installed, compare the bundled template version with the installed version. If the bundled version is newer:

1. Report that a newer schema version is available.
2. Ask the user whether to update.
3. If the user agrees, overwrite the installed schema with the bundled template.
4. If the user declines, skip.

## Guardrails

- Do NOT create an OpenSpec change automatically. Initialization only.
- Do NOT overwrite existing `openspec/config.yaml`.
- Do NOT commit to git.
- Do NOT run `openspec new change` — only suggest it.
- Do NOT install schema to a project that does not have OpenSpec initialized (run CLI init first).

## Output Template

After completion, use this output format:

```
OpenSpec initialized: <created | already present>
sdd-plus-superpowers schema: <installed | updated | already present>
Schema version: <bundled version from schema.yaml>

Suggested next step:
  openspec new change <name> --schema sdd-plus-superpowers
```
