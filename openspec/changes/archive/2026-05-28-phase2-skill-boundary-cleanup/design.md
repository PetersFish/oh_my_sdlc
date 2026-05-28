## Context

Phase 1 renamed 15 skills in `skills/` and their installed copies (`.opencode/`, `.claude/`, `.cursor/`) into domain-prefixed names. All 96 tests pass. The rename was a direct directory migration — no aliases, no backward-compat stubs.

Phase 2 is a metadata-level cleanup that does not change any script, schema, or API behavior. The work is: one rename (`research-ai-architecture` → `qa-ai-architecture`), description/title tightening in 5 SKILL.md files, removal of 2 absolute path strings from 2 skill bodies, and addition of one taxonomy document. All changes propagate from canonical `skills/<name>/SKILL.md` to installed copies via direct file copy (matching the Phase 1 pattern).

Currently `qa-ai-architecture` (as `research-ai-architecture`) exists only as a canonical skill under `skills/` — it has no installed copies in `.opencode/`, `.claude/`, or `.cursor/`. This was true before Phase 1 as well; the skill was not part of the installed set.

## Goals / Non-Goals

**Goals:**
- Eliminate trigger ambiguity between `research-general` (durable research workflow) and the AI-architecture Q&A coach by moving the latter to the `qa-*` prefix
- Remove absolute machine-specific paths (`/Users/yuping/.cursor/...`) from all skill bodies and installed copies
- Clarify `sdlc-openspec-memory-sync` as adapter-only (OpenSpec verified-before-archive gate), not a general memory sync entry point
- Clarify `sdlc-repository-memory-sync` as the primary memory sync entry point for all non-OpenSpec-gate scenarios
- Remove Mermaid-as-final-output ambiguity from `study-zybook-notes`
- Provide a single-source taxonomy document for future skill boundary decisions

**Non-Goals:**
- No script, schema, or API changes
- No alias or backward-compat legacy directories
- No changes to `media-ocr-router` or `transform-markdown-svg` (explicitly excluded per user decision to avoid unrelated inter-skill coupling)
- No changes to `~/.agents/`, `~/.config/opencode/`, or `~/.claude/skills/` global directories
- No creation of installed copies for `qa-ai-architecture` unless explicitly requested

## Decisions

### D1: `qa-ai-architecture` as new prefix family

**Choice:** Rename `research-ai-architecture` → `qa-ai-architecture`, establishing `qa-*` as the prefix for instant Q&A / coaching skills that do not manage durable research artifacts.

**Rationale:** The `research-*` prefix implies durable local research topics (create topic, run, rerun, archive, wiki) as defined by `research-general`. The AI architecture coach is a conversational Q&A tool — it answers architecture questions directly in-chat without creating `research/` directory structure or topic lifecycle artifacts. Using `qa-*` prevents AI from confusing "ask an architecture question" with "create a durable research topic for architecture."

**Alternatives considered:**
- `coach-ai-architecture` — introduces yet another prefix family for a single skill; overkill
- Keep `research-ai-architecture` with tightened description — still shares `research-*` prefix space, which is the root cause of ambiguity

### D2: Boundary clarification via description narrowing only

**Choice:** Tighten each SKILL.md description (the frontmatter field used for trigger routing) and the body's "When to Use" / "Do Not Use" sections. Do not modify spec-level SHALL contracts.

**Rationale:** The behavioral contracts in `openspec/specs/` already define correct behavior. The problem is purely routing: the model reads `description:` and `name:` to decide which skill to invoke. A tighter description is sufficient to fix misrouting without touching spec or script logic.

### D3: Description patterns for each skill pair

**`research-general`:**
```yaml
description: Manage durable local research topics...Use only when the user wants a structured research lifecycle (run, rerun, archive, wiki)...
Do not use for one-off factual Q&A, instant architecture coaching (use qa-ai-architecture), ...
```

**`qa-ai-architecture`:**
```yaml
description: AI architecture Q&A coach for senior engineers...

importantly: Only trigger this for questions about AI-native architecture, RAG, Agent systems, LLMOps, etc.
Do not trigger for creating/managing research topics (use research-general).
```

**`sdlc-openspec-memory-sync`:**
```yaml
description: OpenSpec post-verify memory sync...

only when a verified OpenSpec change needs memory updated before archive.
Do not use for ordinary .ai-memory/ sync after code changes (use sdlc-repository-memory-sync).
```

**`sdlc-repository-memory-sync`:**
```yaml
description: Sync repository memory after code changes...

This is the primary sync entry point.
For OpenSpec verified-before-archive workflows, sdlc-openspec-memory-sync will delegate to this skill.
```

**`study-zybook-notes`:**
Body update: Replace "Mermaid or draw.io" ambiguity with:
- Final output diagrams: draw.io SVG via `transform-markdown-svg` only
- Mermaid: allowed only as transient inline text sketches during analysis, never as final rendered output

### D4: Absolute path remediation

**Choice:** Replace machine-specific absolute paths with skill-name references. In `transform-markdown-svg/SKILL.md`, replace the hardcoded script path with a relative reference from the skill base directory. In `study-zybook-notes/SKILL.md`, replace the absolute path to `transform-algo-render/SKILL.md` with a skill-name reference.

**Pattern:**
- BEFORE: `python3 "/Users/yuping/.cursor/skills/transform-markdown-svg/scripts/embed_drawio_svg.py"`
- AFTER: Reference the script relative to the installed skill directory (the skill system auto-resolves `<skill-base>/scripts/`)

For `study-zybook-notes` references to atomic skills, use skill names rather than filesystem paths:
- BEFORE: `/Users/yuping/.cursor/skills/transform-algo-render/SKILL.md`
- AFTER: `transform-algo-render` (the model resolves via skill name lookup, not filesystem path)

### D5: TAXONOMY.md structure

**Choice:** A concise reference document, not an exhaustive spec. Contents:
1. Prefix semantics table (`qa-*`, `research-*`, `sdlc-*`, `transform-*`, `study-*`, `media-*`, `integration-*`, `ops-*`, `meta-skill-*`)
2. Skill type classification (atomic, composite, adapter, qa)
3. Trigger conflict priority rules (ordered by specificity: explicit name > adapter-gate > composite-orchestrator > atomic-renderer > general)

### D6: Installed copy sync strategy

**Choice:** After editing canonical SKILL.md files, copy them to existing installed copy directories using the same direct-copy pattern as Phase 1. For `qa-ai-architecture`, create new installed copies only if the skill was previously installed under its old name in that target — otherwise leave it canonical-only.

**Rationale:** `research-ai-architecture` has no installed copies in `.opencode/`, `.claude/`, or `.cursor/`. The skill currently lives in `~/.agents/skills/ai-architecture-coach/` (user's global config), outside this repo's scope.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Old `research-ai-architecture` references left in test files, spec docs, or config JSON | `grep -r "research-ai-architecture"` across repo before commit; verify tests pass |
| Installed copy drift after manual edits | `test_repository_memory_skill_copies.py` verifies content consistency; run immediately after sync |
| `qa-ai-architecture` has no installed copies, so skill registry may not list it when invoked from this repo | Expected — the skill is canonical-only in this repo; global user config provides the installed copy separately |
| Description narrowing could cause under-triggering (skill not invoked when it should be) | Monitor in real usage; descriptions err on the side of specificity per Phase 2 goal |
| `transform-markdown-svg` script path change might break if the script is invoked from a different working directory | Use `__file__`-relative or skill-base-relative resolution in the script invocation instruction |
