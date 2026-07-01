---
name: sdlc-project-bootstrap
description: Use when initializing a new project foundation, bootstrapping AGENTS.md, setting up OpenSpec and repository memory for a new project, preparing a project for spec-driven development, or when the user asks to set up, initialize, or bootstrap a project from scratch. Also use when the user needs a project foundation dry-run preview before making changes. Use ONLY for new-project setup; do NOT use for adding features to an already-initialized project unless the user explicitly asks to re-run foundation initialization.
license: MIT
---

# Project Bootstrap

Orchestrates project foundation initialization by sequencing steps in fixed order:

1. `AGENTS.md` initialization
2. OpenSpec + schema initialization (delegates to `sdlc-openspec-init`)
3. Repository memory initialization (delegates to `sdlc-repository-memory-init`)
4. SDLC Workflow Runtime initialization
5. Agent setup via `setup_agents.py` (template sync + model config activation)

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

### Step 4: Initialize SDLC Workflow Runtime

Check whether `.ai/workflows/scripts/workflow.py` exists at the project root.

**If workflow.py does not exist:**
- Run the deterministic init script:
  ```bash
  python3 .opencode/skills/sdlc-project-bootstrap/scripts/init_foundations.py --root <root>
  ```
  This creates `.ai/workflows/{definitions,runs,runs/history,scripts}/` directories and copies `workflow.py` and `sdlc-main.yaml` from skill templates. It is idempotent — safe to run multiple times.
- Report: "SDLC Workflow Runtime: initialized with sdlc-main workflow".

**If workflow.py exists:**
- Report "SDLC Workflow Runtime: already initialized, no changes needed".

The workflow runtime is a project SDLC foundation asset alongside `.ai/roadmap/` and `.ai/memory/`. It is not OpenCode configuration and lives under `.ai/workflows/`, not `.opencode/`.

### Step 5: Setup SDLC Agent Files

Initialize agent configuration for each AI tool target selected by the user in Step 2.

Check whether the target agent directories contain agent markdown files and effective model config files.

**For each selected target (e.g., `.opencode`, `.claude`, `.cursor`):**
- Run the aggregate setup entrypoint:
  ```bash
  python3 scripts/setup_agents.py --target <project_root>/.opencode/agents
  ```
  This runs template sync (copies canonical prompts and config template), then activation (renders effective `model` and `variant` from target config into agent markdown).
- Report: "Agent setup <target>: [initialized | already present]".

**If target config exists:**
- Rerunning setup_agents.py is idempotent. The install step preserves existing target `config/model-profiles.yaml`, and activation only rewrites `model`/`variant` frontmatter fields.

**Post-initialization config changes:**
- After editing a target's `config/model-profiles.yaml`, rerun the activation step to refresh agent frontmatter:
  ```bash
  python3 scripts/activate_agents_config.py --target <project_root>/.opencode/agents
  ```
- Notify the user that they must restart the AI CLI for agent changes to take effect.

**Guardrails for this step:**
- Do NOT parse YAML or edit frontmatter directly — always route through the script entrypoints.
- Do NOT create a new `sdlc-agent-config` skill. This change does not introduce a separate maintenance skill.
- This step is initialization-time only. Bootstrap does not become a general agent maintenance or refresh skill.

### Step 6: Summary

After all steps complete, output a summary:

```
Project Foundation Bootstrap Complete

AGENTS.md: [created | already present | appended missing blocks]
OpenSpec: [initialized | already present]
  AI tools: [selected]
  Default schema: [selected]
Repository Memory: [initialized | already present]
SDLC Workflow Runtime: [initialized | already present]
Agent Setup: [initialized | already present for each target]

Suggested next steps:
  1. Restart your AI CLI so agent changes take effect
  2. Create your first change: openspec new change <name>
  3. Populate repository memory: run sdlc-repository-memory-sync
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
SDLC Workflow Runtime: [would initialize with sdlc-main workflow | already present]
Agent Setup: [would initialize for each target | already present]
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
- Execute steps in order: AGENTS.md first, then OpenSpec, then memory, then workflow runtime, then agent setup.
- Do NOT parse agent config YAML or edit agent frontmatter directly — always route through script entrypoints (`setup_agents.py`, `activate_agents_config.py`).
- Do NOT create a new `sdlc-agent-config` skill. Agent setup and refresh remain script-routed in this change.
- After agent setup, remind the user to restart their AI CLI for agent changes to take effect.
