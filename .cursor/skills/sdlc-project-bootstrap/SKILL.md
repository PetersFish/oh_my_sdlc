---
name: sdlc-project-bootstrap
description: Use when initializing a new project foundation, bootstrapping AGENTS.md, setting up OpenSpec and repository memory for a new project, preparing a project for spec-driven development, or when the user asks to set up, initialize, or bootstrap a project from scratch. Also use when the user needs a project foundation dry-run preview before making changes. Use ONLY for new-project setup; do NOT use for adding features to an already-initialized project unless the user explicitly asks to re-run foundation initialization.
license: MIT
---

# Project Bootstrap

Orchestrates project foundation initialization by sequencing steps in fixed order:

1. `AGENTS.md` initialization
2. Agent installation (via `setup_agents.py` script, only for selected AI tools)
3. OpenSpec + schema initialization (delegates to `sdlc-openspec-init`)
4. Repository memory initialization (delegates to `sdlc-repository-memory-init`)

Each step is idempotent. Running bootstrap multiple times on the same project is safe and only adds what is missing.

Agent model configuration is handled separately through the canonical `agents/config/model-profiles.yaml` template. Bootstrap does NOT parse YAML or edit agent frontmatter directly; it routes through the script entrypoint `scripts/setup_agents.py`.

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

### Step 2: Install and Activate Agent Prompts

After OpenSpec initialization has determined which AI tools are selected, install the canonical agent prompt files and activate per-agent model configuration for each selected target.

**For each selected AI tool target** (e.g., opencode, claude, cursor):
- Run the aggregate setup script:
  ```bash
  python3 scripts/setup_agents.py --target <.opencode|.claude|.cursor>/agents
  ```
- This performs template sync (copies canonical prompts + initializes target config) followed by activation (renders effective `model` and `variant` from the target config into markdown frontmatter).
- Report: "Agents for <tool>: installed and activated".

**Restart reminder:** After initial agent installation or after refreshing agent config, remind the user to restart their AI tool for the new agent prompts and model settings to take effect.

**Do NOT** edit agent markdown frontmatter directly or parse the YAML config manually. Always route through `setup_agents.py`.

**Refresh after config changes:** If the user later edits `<target>/config/model-profiles.yaml`, they can rerun activation without reinstalling prompts:
```bash
python3 scripts/setup_agents.py --target <.opencode|.claude|.cursor>/agents --activate-only
```
This is a non-destructive config refresh path. Bootstrap itself is initialization-only; ongoing config refreshes are script-routed operations, not a new durable skill contract.

### Step 3: Initialize OpenSpec

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

If `sdlc-openspec-init` fails, report the error and stop. Do NOT proceed to step 5.

### Step 4: Initialize Repository Memory

Check whether `.ai/memory/manifest.json` exists at the project root.

**If manifest.json exists:**
- Report "Repository memory: already initialized, no changes needed".
- Suggest running `sdlc-repository-memory-sync` separately if the user wants to populate memory.

**If manifest.json does not exist:**
- Delegate to `sdlc-repository-memory-init` to create the `.ai/memory/` directory structure, manifest, index, templates, and gitignore.
- Report the result from `sdlc-repository-memory-init`.
- Do NOT auto-run `sdlc-repository-memory-sync`. Only suggest it as a next step.

### Step 5: Initialize SDLC Workflow Runtime

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

### Step 6: Summary

After all steps complete, output a summary:

```
Project Foundation Bootstrap Complete

AGENTS.md: [created | already present | appended missing blocks]
Agents: [installed and activated for <tool>, ... | skipped (no AI tools selected)]
OpenSpec: [initialized | already present]
  AI tools: [selected]
  Default schema: [selected]
Repository Memory: [initialized | already present]
SDLC Workflow Runtime: [initialized | already present]

Suggested next steps:
  1. Restart your AI tools for new agent prompts to take effect.
  2. Create your first change: openspec new change <name>
  3. Populate repository memory: run sdlc-repository-memory-sync
```

## Dry-run Mode

When the user requests dry-run ("dry run", "preview", "what would this do", "--dry-run"), run the detection steps (check whether AGENTS.md, OpenSpec, schema, and memory exist) but do NOT modify any files. Report what would be done:

```
Dry-run preview:

AGENTS.md: [would create from template | would append missing blocks | already present]
Agents: [would install and activate for <tool>, ... | skipped (no AI tools selected)]
OpenSpec: [would initialize via openspec init | already present]
  AI tools: [would prompt for selection | already selected]
  Default schema: [would prompt for selection | already selected]
Repository Memory: [would initialize via sdlc-repository-memory-init | already present]
SDLC Workflow Runtime: [would initialize with sdlc-main workflow | already present]
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
- Execute steps in order: AGENTS.md first, then agents, then OpenSpec, then memory.
- Do NOT edit agent frontmatter or parse YAML directly — route agent setup through `scripts/setup_agents.py`.
