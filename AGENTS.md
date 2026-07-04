# AGENTS.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Skill Frontmatter

When writing or editing skill `SKILL.md` frontmatter, use folded block scalar syntax for long `description` values:

```yaml
description: >-
  Use when ...
  Trigger for ...
```

Do not use unquoted plain scalar descriptions for long natural-language text. `: ` inside values such as `Triggers include: ...` or `.ai/evals/: ...` breaks YAML parsing and causes skills to be silently filtered out.

## Contract And Test Discipline

Keep global routing short; load detailed norms only when needed.

- When implementing behavior from a spec, design, task list, CLI flag, config field, state file, runner, or workflow contract, load `implementation-contract-discipline` before editing code.
- When writing or reviewing tests for executable behavior, load `behavioral-test-design` before adding or accepting tests.
- Do not treat string-presence checks as proof of executable behavior unless the subject is static documentation, templates, frontmatter, or copy.

## Skill Taxonomy

When creating, renaming, or classifying skills, read `skills/TAXONOMY.md` first.

## Repository Memory

If `.ai/memory/index.json` exists and the task involves planning, editing, reviewing, or continuing work in this repository, load relevant repository memory first using `sdlc-repository-memory-load`.

Do not load `.ai/memory/sync-history/`, `.ai/memory/sessions/`, `.ai/memory/snapshots/`, `.ai/memory/tmp/`, `.ai/memory/cache/`, or `.ai/memory/review-queue.json` by default.

## Hidden Directory Discovery

**Never conclude a hidden directory doesn't exist based on Glob returning empty results.** Glob excludes dotfiles and hidden directories by default. An empty result for patterns like `.ai/roadmap/*`, `.ai/evals/*`, or `.ai/memory/*` does NOT mean those directories are absent — it means Glob didn't match visible entries inside them.

When checking for the existence of `.ai/roadmap/`, `.ai/evals/`, `.ai/memory/`, or any other hidden runtime directory:
- Use `Read` on the directory path directly, or
- Use `Bash ls -d <path>` to confirm presence/absence.

This applies to all tooling and skill workflows that inspect `.ai/` state, including SDLC roadmap, EvalOps, and repository memory gates.

## Workflow Template Sync

When modifying files under `.ai/workflows/scripts/workflow.py` or `.ai/workflows/definitions/sdlc-main.yaml`, the corresponding templates in `sdlc-project-bootstrap/templates/workflow/` MUST be synced before commit. The pre-commit hook enforces this.

**Install the hook (one-time per clone):**

```bash
git config core.hooksPath .githooks
```

**Sync command:**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
```

**Check for drift (read-only):**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
```

**Check distributed copies (read-only):**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed
```

**Distribute canonical to all project-level copies:**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute
```

## Skill Updates Discipline

Skills under `skills/<name>/` are canonical. Distributed copies live in `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/` (project-level), plus user-level directories managed by `meta-skill-lifecycle-governance`.

**Rules:**
- Modifications to skill content (SKILL.md, scripts/, templates/, schemas/) MUST be made in canonical `skills/<name>/` first.
- After canonical changes, re-distribute to all AI CLI targets:
  - **Project-level**: `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`
  - **User-level**: invoke `meta-skill-lifecycle-governance` with the DISTRIBUTE action (handles OS-specific paths)
- Do NOT edit distributed copies directly — they are derived from canonical.
- For `sdlc-project-bootstrap/templates/workflow/`, the pre-commit hook enforces consistency: live ↔ canonical ↔ all project-level distributed copies.

**Distribution command (per skill, project-level):**
```bash
python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py \
  --source-repo . --skill-name <skill> --source-ref HEAD \
  --target .opencode/skills/<skill> --status stable
# Repeat for .claude/skills/<skill> and .cursor/skills/<skill>
```

**For user-level distribution**, invoke `meta-skill-lifecycle-governance` (covers OS-specific paths).

## Agent Updates Discipline

Agents under `agents/` are canonical. Distributed copies live in `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/` (project-level), plus user-level via `--global` (`~/.config/opencode/agents/`).

**Rules:**
- Modifications to agent files MUST be made in canonical `agents/` first.
- After canonical changes, re-distribute to all AI CLI targets:
  - **Project-level**:
    ```bash
    python3 scripts/setup_agents.py --target ./.opencode/agents --force
    python3 scripts/setup_agents.py --target ./.claude/agents --force
    python3 scripts/setup_agents.py --target ./.cursor/agents --force
    ```
  - **User-level**:
    ```bash
    python3 scripts/setup_agents.py --global --force
    ```
  - **Other projects**: from the project root, run:
    ```bash
    python3 /path/to/oh_my_skills/scripts/setup_agents.py --target ./.opencode/agents --force
    ```
- `setup_agents.py` runs template sync then activation (model/variant rendering). Do NOT use `install_agents.py` directly for CLI targets — it would wipe activated model config.
- **Distribution is NOT complete until activation succeeds.** A distributed copy must have valid `model` and `variant` frontmatter written by `setup_agents.py`. Template sync alone (prompt text only) does not count as a finished distribution.
- Do NOT edit distributed copies directly — they are derived from canonical.
- The pre-commit hook enforces consistency when `agents/` files are staged.

**Verification (agent updates):**

```bash
# Full sync (install + activate) all project-level targets
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force

# Verify template + activation consistency (exit 1 on drift)
python3 scripts/setup_agents.py --target ./.opencode/agents --check
```

## Plan Checkbox Sync Discipline

When executing a superpowers plan (path matches `docs/superpowers/plans/*.md`),
the executor MUST sync plan checkboxes to reflect actual progress.

Applies to:
- Primary session executing `executing-plans` or `subagent-driven-development`
  (build mode — direct skill invocation)
- Lifecycle subagents dispatched for lightweight-flow `apply_change`
  (implement-agent reading `artifacts.primary_design_path`)

Does NOT apply to spec-flow (`openspec/changes/.../proposal.md` has no
checkboxes).

Procedure:
1. After completing each step (`- [ ] **Step N: ...**`), use the `edit` tool
   to change that line to `- [x] **Step N: ...**`. Match the exact line by
   Task heading context and Step text.
2. Before declaring work complete — calling `finishing-a-development-branch`,
   returning `tasks_complete: true`, or calling `complete-phase` — run:

   ```bash
   python3 scripts/check_plan_checkboxes.py <plan_path>
   ```

3. If exit 1: some steps were not checked. Go back and check them.
   If exit 0: proceed to completion.

This rule exists because superpowers skills update in-session TodoWrite state
but never write checkbox state back to the plan file. The plan file is the
durable record; without sync, a new session cannot tell what was completed.
