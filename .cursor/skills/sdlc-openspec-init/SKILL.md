---
name: sdlc-openspec-init
description: Use when setting up OpenSpec in a new or existing project, initializing the openspec/ directory, selecting one or more AI tools with opencode as the default, installing or updating the sdd-plus-superpowers schema, listing available schemas, prompting the user to choose a default schema, or when the user asks to set up OpenSpec for spec-driven development. Use ONLY when the task involves OpenSpec configuration or schema management; do NOT use for general project initialization (see sdlc-project-bootstrap instead).
license: MIT
---

# OpenSpec Init

Initializes OpenSpec in a project, installs the `sdd-plus-superpowers` workflow schema when needed, asks the user to choose one or more AI tools with `opencode` as the default before running `openspec init`, and asks the user to choose the default schema from the available OpenSpec schema list before persisting `openspec/config.yaml`. Can be used standalone or as a delegate of a project bootstrap orchestrator.

## When to Use

- The user asks to set up OpenSpec in a new or existing project.
- The user asks to install or update the `sdd-plus-superpowers` schema.
- The user asks to choose or change the default OpenSpec schema.
- A project has OpenSpec CLI but is missing the `sdd-plus-superpowers` schema.
- A project bootstrap orchestrator delegates the OpenSpec step here.
- Schema iteration: the schema bundled in this skill is newer than the one installed in the target project.

## Workflow

### 1. Detect project root

Determine the repository root. If not clear, ask the user.

### 2. Detect OpenSpec state

Check whether `openspec/config.yaml` exists at the project root.

- **Exists**: Report "OpenSpec already initialized". Skip CLI init.
  - If `openspec/config.yaml` already contains `schema`, preserve it and skip schema prompting unless the user explicitly asks to change it.
- **Missing**: Proceed to step 3.

If `openspec/` exists but `openspec/config.yaml` does not, treat that as a partial init state and recover the config after schema selection instead of rerunning CLI init blindly.

### 3. Ask for AI tools BEFORE running openspec init

**HARD RULE:** Do NOT run `openspec init` until the user has chosen their AI tools. Always prompt first, execute after.

Prompt the user to choose one or more AI tools before initialization.

- Run `openspec init --help` to discover the currently supported tool list.
- Present the supported tool choices to the user.
- Default/recommended choice: `opencode`.
- When the user selects one or more tools, pass them as a comma-separated list to `--tools`.
- When the user chooses no tool integration, pass `--tools none`.
- When the user selects every tool, it's cleaner to pass `--tools all`.

Only after the user responds with their choice, run:

```bash
openspec init --tools <selected-tools>
```

After init completes, confirm `openspec/config.yaml` was created. If init succeeds but `openspec/config.yaml` is still missing, keep going and recover it when persisting the selected schema. If the init command fails, report the error and stop.

### 4. Install sdd-plus-superpowers schema (if missing)

Install the bundled schema BEFORE listing schemas so that `sdd-plus-superpowers` appears in the `openspec schemas --json` output.

Check whether `openspec/schemas/sdd-plus-superpowers/` exists at the project root.

- **Exists**: Report "sdd-plus-superpowers schema already installed". Skip installation.
- **Missing**: Copy the bundled schema template from this skill's `templates/sdd-plus-superpowers/` to the project's `openspec/schemas/` directory:

```
skills/sdlc-openspec-init/templates/sdd-plus-superpowers/
  → <project-root>/openspec/schemas/sdd-plus-superpowers/
```

The schema template includes:
- `schema.yaml`: Workflow schema definition
- `templates/`: Artifact templates (brainstorm.md, proposal.md, design.md, spec.md, tasks.md, plan.md, verify.md)
- `README.md`: Schema documentation

If the `openspec/schemas/` directory does not exist, create it first.

### 5. List available schemas and ask for the default

Now that the bundled schema is installed, run the OpenSpec schema listing command:

```bash
openspec schemas --json
```

Present every returned schema to the user, including package-provided schemas such as `spec-driven` and project-local schemas such as `sdd-plus-superpowers`, then ask which one should become the default schema.

- **Recommended/default**: `sdd-plus-superpowers`. Present it as the recommended choice.
- If only one schema is available and the spec requires user choice, still ask explicitly.
- If the user has already stated their schema preference earlier, skip this prompt.

### 6. Persist the chosen default schema

Write the user-selected schema name into `openspec/config.yaml` as the `schema` value.

If `openspec/config.yaml` is missing after non-interactive init, create it here while writing the selected schema.

If `openspec/config.yaml` already has a `schema` value and the user did not ask to change it, keep the existing value and skip this step.

### 7. Report result

After initialization, output a summary:

```
OpenSpec initialized: [created / already present]
AI tools: [selected tools]
Default schema: [selected schema name]
sdd-plus-superpowers schema: [installed / already present]

Suggested next step:
  openspec new change <name> --schema sdd-plus-superpowers
```

### 8. Dry-run mode

When the user requests dry-run (e.g., "dry run", "preview", "what would this do"), report planned actions without modifying any files:

```
Dry-run preview:

Planned actions:
  - [prompt] Ask user to choose one or more AI tools (default: opencode)
  - [init] OpenSpec: openspec init --tools <selected-tools> (not yet initialized)
  - [skip] OpenSpec: already initialized at openspec/config.yaml
  - [install] sdd-plus-superpowers schema: copy from templates to openspec/schemas/
  - [skip] sdd-plus-superpowers schema: already installed at openspec/schemas/sdd-plus-superpowers/
  - [list] Available schemas: openspec schemas --json
  - [prompt] Ask user to choose default schema (recommended: sdd-plus-superpowers)
```

Only show actions that would actually be taken (skip the skip entries if nothing is already present). Do NOT execute any actions in dry-run mode.

## Standalone Invocation

This skill can be invoked independently of any project bootstrap orchestrator. When invoked standalone:
- Run steps 1-7 as described above.
- The skill does NOT depend on bootstrap context.

## Schema Iteration

When the skill is invoked on a project that already has the schema installed, compare the bundled template version with the installed version. If the bundled version is newer:

1. Report that a newer schema version is available.
2. Ask the user whether to update.
3. If the user agrees, overwrite the installed schema with the bundled template.
4. If the user declines, skip.

## Guardrails

- Do NOT run `openspec init` until the user has chosen their AI tools. Always prompt first, execute after.
- Do NOT ask for the default schema until the `sdd-plus-superpowers` schema is installed and `openspec schemas --json` can include it.
- Do NOT create an OpenSpec change automatically. Initialization only.
- Do NOT overwrite existing `openspec/config.yaml` unless the user explicitly chooses a different default schema.
- Do NOT assume `openspec/config.yaml` exists after non-interactive init; recover it when persisting the chosen schema.
- Do NOT commit to git.
- Do NOT run `openspec new change` — only suggest it.
- Do NOT install schema to a project that does not have OpenSpec initialized (run CLI init first).

## Output Template

After completion, use this output format:

```
OpenSpec initialized: <created | already present>
AI tools: <selected tools | none>
Default schema: <selected schema name>
sdd-plus-superpowers schema: <installed | updated | already present>
Schema version: <bundled version from schema.yaml>

Suggested next step:
  openspec new change <name> --schema sdd-plus-superpowers
```
