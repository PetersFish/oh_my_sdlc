---
description: Config .opencode/agents/* model/variant from model-profiles.yaml via setup_agents.py
---

Sync `.opencode/agents/*` model/variant frontmatter from `.opencode/agents/config/model-profiles.yaml`.

This is a **derived-artifact sync** — no exploration or judgment needed. Run the exact commands below in order.

**Relationship**
- Canonical agents: `agents/*.md` + `agents/config/model-profiles.yaml`
- Target (this command's scope): `.opencode/agents/*.md` + `.opencode/agents/config/model-profiles.yaml`
- `setup_agents.py` = install (template sync from canonical) → activate (render model/variant from target config)

**Steps**

1. **Sync + activate** (single command, overwrites target agent files from canonical then renders model/variant):

   ```bash
   python3 scripts/setup_agents.py --target ./.opencode/agents --force
   ```

   Expected: `INSTALLED:` and `ACTIVATED:` lines for each agent. Exit 0.

2. **Verify** (must pass before claiming done):

   ```bash
   python3 scripts/setup_agents.py --target ./.opencode/agents --check
   ```

   Expected: `OK: agents fully in sync`. Exit 0. If exit 1, fix drift before proceeding.

3. **Commit + push** (only if user asked):

   Stage only files under `.opencode/agents/` — do NOT stage unrelated worktree changes:

   ```bash
   git add .opencode/agents/
   git commit -m "chore(opencode): sync agent model profiles"
   git push origin main
   ```

**Guardrails**
- Do NOT edit `.opencode/agents/config/model-profiles.yaml` to change model choices — that is a target-owned override file. To change model assignments, edit the target config directly first, then run step 1.
- Do NOT stage files outside `.opencode/agents/` when committing.
- The pre-commit hook runs `sync_derived_artifacts` checks automatically; let it pass/fail on its own.