## Why

Phase 1 renamed 15 skills into domain-prefixed names (sdlc-*, research-*, transform-*, etc.) and achieved zero test failures. Phase 2 addresses the residual overlap between skills sharing a prefix or crossing semantic boundaries: (a) `research-ai-architecture` is a Q&A coach masquerading as a `research-*` durable-research skill, (b) `study-zybook-notes` still carries absolute paths and mixed Mermaid/draw.io rendering rules that confuse model routing, (c) `sdlc-openspec-memory-sync` and `sdlc-repository-memory-sync` have near-identical trigger descriptions causing the adapter to compete with the core sync skill, and (d) no taxonomy exists to document these boundaries for future skill additions.

## What Changes

- **Rename** `research-ai-architecture` → `qa-ai-architecture` (name reflects Q&A style; `qa-*` prefix separates it from `research-*` durable-research lifecycle). **BREAKING** for any caller referencing the old skill name.
- **Update description** for `research-general`: clarify it triggers ONLY when a durable local research topic workflow (`research/` directory, run/rerun/archive/wiki) is needed, not for instant Q&A.
- **Update description** for `qa-ai-architecture`: clarify it is an AI architecture Q&A/technical-decision coach that does NOT manage `research/` topics.
- **Update description** for `study-zybook-notes`: remove Mermaid-as-final-output ambiguity; declare draw.io SVG via `transform-markdown-svg` as the sole final diagram format; Mermaid is allowed only as transient text sketches.
- **Update description** for `sdlc-openspec-memory-sync`: restrict trigger to OpenSpec verified-before-archive gate only; generic `.ai-memory/` sync belongs to `sdlc-repository-memory-sync`.
- **Update description** for `sdlc-repository-memory-sync`: position it as the primary entry point for all non-OpenSpec-gate memory sync (code changes, session sync, explicit `.ai-memory/` updates).
- **Fix absolute paths**: remove `/Users/yuping/.cursor/...` references from `transform-markdown-svg/SKILL.md` and `study-zybook-notes/SKILL.md`. Use skill-name references or relative paths instead.
- **Add `skills/TAXONOMY.md`**: document prefix semantics, skill types (atomic/composite/adapter/qa), trigger conflict priorities, and the relationship between composite and atomic skills.
- **Sync installed copies** in `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/` for all modified canonical skills.

## Capabilities

### New Capabilities
- `qa-ai-architecture`: AI architecture Q&A coach skill (renamed from research-ai-architecture) with clarified trigger boundaries separating it from research-general durable research workflow
- `skill-taxonomy`: New TAXONOMY.md documenting skill prefix semantics, type classification, and trigger conflict resolution priorities
- `skill-boundary-cleanup`: Updated description/trigger boundaries across 5 overlapping skill pairs to prevent routing ambiguity
- `skill-absolute-path-fix`: Removal of machine-specific absolute paths from skill bodies and installed copies

### Modified Capabilities
<!-- No spec-level behavioral requirements change: the memory sync specs already define correct SHALL contracts. Only SKILL.md description metadata and naming are updated. -->

## Impact

- Affected files: 6 `skills/*/SKILL.md` (canonical), 1 new `skills/TAXONOMY.md`, ~12 installed-copy `SKILL.md` files across `.opencode/`, `.claude/`, `.cursor/`
- Test files: `test_research_skill.py` references `research-general` path; `test_ocr_router_skill.py` references `media-ocr-router` — both should remain correct after Phase 1 rename; verify no new test gaps
- No API, script, or schema changes
- No runtime behavior changes — all changes are naming, description metadata, and documentation
