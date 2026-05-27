## Context

The current `openspec-memory-sync` skill is an MVP that runs after OpenSpec verification and before archive. It updates three memory types (ADRs, pitfalls, module docs), requires OpenSpec change artifacts as input, and has no read/hydration mechanism. It explicitly forbids expanding into V2 memory layers, indexes, or compression systems.

This change replaces that MVP with a general-purpose repository memory system split across three lifecycle phases: init, load, and sync. The system must work without OpenSpec, support git commit and session linkage, handle dirty worktrees, and provide selective context hydration for AI agents.

## Goals / Non-Goals

**Goals:**

- Build a three-skill system: `repository-memory-init`, `repository-memory-load`, `repository-memory-sync`.
- Support eight formal memory types with per-type evidence and linkage policies.
- Support repositories without git commits and dirty working trees.
- Provide selective context hydration via `repository-memory-load`.
- Decouple memory synchronization from OpenSpec while preserving the `verify -> memory-sync -> archive` gate through `openspec-memory-sync` wrapper.
- Use deterministic Python scripts for state detection, validation, indexing, manifest updates, and pending reconciliation.
- Use YAML frontmatter per memory file for evidence linkage instead of a monolithic manifest.
- Support multi-client distribution (OpenCode, Claude Code, Cursor) with full self-contained copies and consistency verification.
- Provide a review queue for `needs_user_review` items without creating formal memory for them.
- Provide a sync-history audit trail committed to git but not indexed for agent loading.

**Non-Goals:**

- Vector retrieval, semantic embedding, or graph cognition.
- Automatic git commits.
- Automatic modification of workflow skills during per-repository initialization.
- Full patch engine with diff-based memory updates.
- Schema migration framework.
- CI hooks or git hooks for automatic sync triggers.
- SaaS storage or cloud synchronization.
- Session memory committed to git by default.

## Decisions

### D1: Three-skill separation (init / load / sync)

**Decision:** Split into `repository-memory-init`, `repository-memory-load`, and `repository-memory-sync`.

**Rationale:** Initialization is rare and modifies repository configuration (`.ai-memory/`, optional `AGENTS.md`). Sync is frequent and updates memory state. Load is frequent and read-only. Combining init into sync would waste tokens checking initialization state on every sync run. Combining load into sync would conflate reading and writing.

**Alternatives considered:**
- Single skill with modes: too much conditional logic, poor trigger semantics.
- Two skills (sync + load) with init embedded in sync: wastes tokens on init checks every run.

### D2: `.ai-memory/` as repository-local root

**Decision:** Store all memory under `.ai-memory/` in the repository root.

**Rationale:** Keeps AI memory separate from human documentation (`docs/`) and OpenSpec artifacts (`openspec/`). The dot-prefix signals it is infrastructure, not user-facing content.

**Alternatives considered:**
- `docs/memory/`: too close to human docs, confuses AI vs. human ownership.
- Mixed (`.ai-memory/` for state, `docs/` for ADR/pitfall): adds cross-directory coupling.

### D3: Manifest + per-memory frontmatter (not monolithic manifest)

**Decision:** `manifest.json` stores global sync state; each memory file uses YAML frontmatter for evidence linkage.

**Rationale:** Different memory types have different binding strategies. Pitfalls link to sessions, modules link to commits, specs link to change IDs. A monolithic manifest forces all memory to share one `last_synced_commit`, which breaks when some memory should be commit-linked and some should be session-linked.

**Alternatives considered:**
- Single `manifest.json` with all memory metadata: becomes large, requires full rewrite on any change, forces commit linkage on all types.
- Sidecar `.json` files per memory: doubles file count, harder to edit manually.

### D4: Dirty worktree allowed, no auto git commit

**Decision:** Memory sync proceeds on dirty working trees, marking affected memory as `pending_commit`. Git commits are never made automatically.

**Rationale:** Auto-committing would modify user git history without confirmation. Uncommitted snapshots are still valuable memory; they just need reconciliation when commits happen later.

**Alternatives considered:**
- Block sync on dirty worktree: too strict, prevents useful session/pitfall capture.
- Auto-commit before sync: modifies git history without user consent.

### D5: Three public sync statuses only

**Decision:** Expose only `synced`, `pending_commit`, and `needs_user_review` as public sync statuses.

**Rationale:** Fine-grained statuses like `partially_reconciled` or `no_matching_commit` increase cognitive load for AI models and risk misinterpretation. Detailed reasons belong in `review-queue.json` and `sync-history/`, not in memory frontmatter.

**Alternatives considered:**
- Full status surface (`partially_reconciled`, `no_matching_commit`, `skipped`, `candidate_only`): model misinterpretation risk, state explosion.
- Two statuses (`synced` / `pending`): too coarse, loses the distinction between "waiting for commit" and "needs human review".

### D6: `needs_user_review` does not create formal memory

**Decision:** Items requiring user review are tracked in `review-queue.json` and `sync-history/`, not as formal memory files.

**Rationale:** Creating draft memory files risks AI agents treating them as stable facts. The review queue provides recoverability (items are not lost) without pollution (items are not in `index.json` or formal memory directories).

**Alternatives considered:**
- Create memory files with `status: proposed`: agents may still read and act on unconfirmed content.
- Create to `.ai-memory/review/`: adds a directory that agents might scan, slightly increasing pollution risk.

### D7: `review-queue.json` committed to git, not default-loaded

**Decision:** `review-queue.json` is committed to git for team sharing but excluded from `repository-memory-load` default loading.

**Rationale:** Review items need to be visible across agents and machines. But they should not influence normal agent reasoning until a human confirms them. Only `repository-memory-sync` reads `review-queue.json` to process pending reviews.

### D8: Spec lineage for related OpenSpec changes

**Decision:** When multiple active OpenSpec changes form a lineage (B refines A), they map to a single spec memory file with lineage metadata.

**Rationale:** Creating separate spec memories for related changes produces duplication and potential conflict. A single memory with lineage metadata preserves intent evolution.

**Alternatives considered:**
- One memory per change: leads to duplication and conflict.
- Only track the latest change: loses intent history.

### D9: `index.json` with 2-3 sentence summaries

**Decision:** `index.json` entries contain short 2-3 sentence summaries explaining when an agent should load the memory file.

**Rationale:** Full memory bodies in the index would exceed token budgets. Single-word titles are not enough for agents to decide relevance. 2-3 sentences provides enough routing information.

**Alternatives considered:**
- One-sentence summary: often insufficient for relevance decisions.
- Structured key_points array: increases index size without proportional value for simple routing.

### D10: Decisions and architecture require user confirmation

**Decision:** `decisions` and `architecture` memory types only produce candidates, not formal memory. The user must confirm or modify before formal creation.

**Rationale:** Architectural decisions and system-level cognition are high-impact. AI-generated candidates may be wrong or incomplete. User confirmation prevents false architectural conclusions from entering durable repository memory.

**Alternatives considered:**
- Auto-create with low confidence: still pollutes memory with potentially wrong information.
- Auto-create and flag: agents may ignore the flag.

### D11: Multi-client full copy distribution

**Decision:** Each client directory (`.opencode/`, `.claude/`, `.cursor/`) receives a complete self-contained copy of all skill files including scripts, schemas, and templates.

**Rationale:** Self-contained copies ensure any client can run the skill without cross-directory dependencies. Consistency is verified via payload hashes in `.skill-install.json`.

**Alternatives considered:**
- Canonical source with symlinks: breaks on Windows, some clients don't resolve symlinks.
- Canonical source with path references: fragile, different clients have different working directory assumptions.

### D12: Sessions local-only by default

**Decision:** `.ai-memory/sessions/` is listed in `.ai-memory/.gitignore` and not committed to git.

**Rationale:** Session memory contains temporary context, unfinished tasks, and potentially private information. It is useful locally for session continuity but should not be shared across the team by default.

**Alternatives considered:**
- Commit sessions: noise in git history, privacy risk.
- Commit only curated handoff: adds complexity with selection rules.

## Risks / Trade-offs

- **Multi-copy drift**: Full copies across `.opencode/`, `.claude/`, `.cursor/` can diverge if not kept in sync. Mitigation: `.skill-install.json` payload hashes and `test_repository_memory_skill_copies.py` consistency tests.
- **Token cost of index loading**: Even with 2-3 sentence summaries, a large repository may have many index entries. Mitigation: `select_memory.py` limits to 5 results by default; index stays small for typical repositories.
- **Uncommitted snapshot staleness**: Memory marked `pending_commit` may become stale if commits never happen. Mitigation: `reconcile_pending.py` runs on every sync; `review-queue.json` tracks unresolvable items.
- **AI model misinterpreting `pending_commit` memory**: Agents might treat uncommitted memory as stable fact. Mitigation: `index.json` includes `status` field; `repository-memory-load` flags pending items in the context pack.
- **Review queue accumulation**: If users never confirm candidates, `review-queue.json` grows indefinitely. Mitigation: each sync checks open review items and surfaces them; items can be dismissed.
- **Python script dependency**: Scripts use Python standard library only, but some environments may lack Python. Mitigation: scripts are simple and could be reimplemented in other languages; skill text describes the expected behavior so AI agents can perform the logic manually if scripts fail.

## Migration Plan

1. Create new skill directories under `skills/` for `repository-memory-init`, `repository-memory-load`, `repository-memory-sync`.
2. Rewrite `openspec-memory-sync` as a thin wrapper that delegates to the new core skills.
3. Add `repository-memory-load` reminder blocks to OpenSpec workflow skills.
4. Install full copies to `.opencode/`, `.claude/`, `.cursor/`.
5. Add `.skill-install.json` with payload hashes.
6. Repositories with existing `openspec-memory-sync` usage can continue using the wrapper; new repos should use `repository-memory-init` and `repository-memory-sync` directly.

## Open Questions

- Should `repository-memory-init` also initialize a sample memory file to demonstrate the format, or should it only create the empty structure?
- Should the Python scripts use `argparse` or a simpler argument parsing approach for CLI consistency?
- Should `repository-memory-load` accept a `--types` flag to filter memory types, or should type filtering be handled entirely by the skill text?