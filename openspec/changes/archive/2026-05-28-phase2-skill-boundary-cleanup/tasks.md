## 1. Rename research-ai-architecture → qa-ai-architecture

- [x] 1.1 Rename canonical directory `skills/research-ai-architecture/` → `skills/qa-ai-architecture/`
- [x] 1.2 Update frontmatter `name:` to `qa-ai-architecture` in canonical SKILL.md
- [x] 1.3 Update title (`# ...`) to reflect Q&A coach semantics
- [x] 1.4 Update frontmatter `description:` to Q&A-style description with "do not trigger for durable research topics"
- [x] 1.5 Update body: add "When Not to Use" section redirecting durable research to `research-general`
- [x] 1.6 Remove any old-name directories (`research-ai-architecture`) in `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/` if they exist

## 2. Update research-general description boundary

- [x] 2.1 Update canonical `skills/research-general/SKILL.md` description: add "use only for structured durable research topic lifecycle"
- [x] 2.2 Update body: clarify AI architecture Q&A goes to `qa-ai-architecture`, not this skill
- [x] 2.3 Sync updated file to `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`

## 3. Update sdlc-openspec-memory-sync description boundary

- [x] 3.1 Update canonical `skills/sdlc-openspec-memory-sync/SKILL.md` description: restrict to OpenSpec verified-before-archive gate only
- [x] 3.2 Update body guardrails: add "do not use for ordinary code changes or session sync (use sdlc-repository-memory-sync)"
- [x] 3.3 Sync updated file to `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`

## 4. Update sdlc-repository-memory-sync description boundary

- [x] 4.1 Update canonical `skills/sdlc-repository-memory-sync/SKILL.md` description: position as primary memory sync entry point
- [x] 4.2 Sync updated file to `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`

## 5. Update study-zybook-notes diagram format boundary

- [x] 5.1 Update canonical `skills/study-zybook-notes/SKILL.md` body: declare draw.io SVG as sole final diagram format; limit Mermaid to inline analysis sketches only
- [x] 5.2 Fix absolute path `/Users/yuping/.cursor/skills/transform-algo-render/SKILL.md` → skill name reference
- [x] 5.3 Sync updated file to `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`

## 6. Fix absolute paths in transform-markdown-svg

- [x] 6.1 Update canonical `skills/transform-markdown-svg/SKILL.md`: replace `/Users/yuping/.cursor/skills/.../embed_drawio_svg.py` with skill-base-relative path
- [x] 6.2 Sync updated file to `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/`

## 7. Add skills/TAXONOMY.md

- [x] 7.1 Create `skills/TAXONOMY.md` with prefix semantics table, skill type classification, and trigger conflict priority rules
- [x] 7.2 Verify file is valid markdown and covers all 9 prefixes

## 8. Verify and test

- [x] 8.1 Grep repo for old name `research-ai-architecture` — confirm no run-time references remain (spec/docs/test files updated as needed)
- [x] 8.2 Grep all `skills/*/SKILL.md` and installed copies for absolute path `/Users/` — confirm zero matches
- [x] 8.3 Run `python3 -m pytest tests/ -v` — confirm 96 tests pass
- [x] 8.4 Verify installed copies match canonical via `test_repository_memory_skill_copies` tests
