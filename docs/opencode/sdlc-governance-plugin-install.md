# SDLC Governance Plugin Installation Guide

Agent-facing instructions for enabling or installing the `sdlc-governance` OpenCode plugin. Follow the mode that matches your task.

## Purpose

The `sdlc-governance` plugin runs `workflow.py governance-check` on every `session.idle` event and surfaces actionable remediation prompts through `tui.appendPrompt` when governance issues are detected. The plugin is read-only and never modifies Roadmap, OpenSpec, Memory, EvalOps, or workflow state.

## Prerequisites

Before enabling or installing this plugin, verify the target repository has:

- `.ai/workflows/scripts/workflow.py` — the SDLC workflow runtime (must support `governance-check` subcommand)
- OpenSpec directory layout under `openspec/changes/`
- OpenCode project with `.opencode/` directory

Verify the Python runtime is reachable:

```bash
python3 .ai/workflows/scripts/workflow.py --root . governance-check
# Expected: JSON output with "block" and "findings" fields
```

---

## Mode A: Enable in Current Repository

Use when the plugin file already exists at `.opencode/plugins/sdlc-governance.ts` and you only need to verify it is loaded.

### Steps

1. **Check plugin file exists**
   ```bash
   ls -la .opencode/plugins/sdlc-governance.ts
   ```

2. **Verify OpenCode loads repo-local plugins**
   OpenCode loads `.opencode/plugins/*.ts` files automatically if the directory exists. Confirm the plugin is listed in OpenCode's plugin status (if available):
   ```bash
   # Check plugin configuration if relevant
   cat .opencode/opencode.jsonc 2>/dev/null || echo "No opencode.jsonc"
   ```
   The default behavior loads all `.ts` files under `.opencode/plugins/` without explicit configuration.

3. **Verify governance-check is reachable**
   ```bash
   python3 .ai/workflows/scripts/workflow.py --root . governance-check
   ```

4. **Verify idle trigger behavior**
   After an assistant turn completes, the plugin should fire on `session.idle`. If `block=true`, a governance prompt should appear. If `block=false`, no prompt should appear.

5. **Verify deduplication**
   If the same finding persists across multiple idle events, the plugin should only inject the prompt once (not on every idle). A new process/session clears deduplication state.

### Post-Enablement Checklist

- [ ] Plugin file exists at `.opencode/plugins/sdlc-governance.ts`
- [ ] `python3 .ai/workflows/scripts/workflow.py --root . governance-check` runs successfully
- [ ] No governance prompt injected when `block=false`
- [ ] Governance prompt visible when `block=true`
- [ ] Repeated idle events do not inject duplicate prompts for the same finding hash

---

## Mode B: Install Into Another Repository

Use when copying the plugin from a source repository to a target repository that does not yet have it.

### Steps

1. **Copy plugin file**
   ```bash
   cp <source-repo>/.opencode/plugins/sdlc-governance.ts \
      <target-repo>/.opencode/plugins/sdlc-governance.ts
   ```

2. **Verify target has prerequisites**

   ```bash
   # Check Python runtime exists
   test -f <target-repo>/.ai/workflows/scripts/workflow.py && echo "workflow.py found" || echo "MISSING: workflow.py"

   # Check OpenSpec layout
   test -d <target-repo>/openspec/changes && echo "OpenSpec layout found" || echo "WARNING: no OpenSpec layout"

   # Check governance-check works
   python3 <target-repo>/.ai/workflows/scripts/workflow.py --root <target-repo> governance-check
   ```

3. **Record source metadata** (prevents stale copy issues)

   Create or update `.opencode/plugins/.install-metadata.yaml` in the target repo:
   ```yaml
   plugin: sdlc-governance
   source_repo: <source-repo-path>
   source_ref: <ref-or-version>
   installed_at: <UTC-ISO-8601>
   ```
   Example:
   ```yaml
   plugin: sdlc-governance
   source_repo: /Users/yuping/Documents/workspace/oh_my_skills
   source_ref: openspec/changes/opencode-governance-validation
   installed_at: 2026-06-20T00:00:00Z
   ```

4. **Run verification checklist** (see above)

### Post-Install Checklist

- [ ] Plugin file copied to target `target-repo/.opencode/plugins/sdlc-governance.ts`
- [ ] Target has `.ai/workflows/scripts/workflow.py`
- [ ] Target has OpenSpec layout under `openspec/changes/`
- [ ] Source metadata recorded in `.opencode/plugins/.install-metadata.yaml`
- [ ] All Post-Enablement Checklist items pass

---

## Verification Checklist

Run after installation or enablement:

- [ ] Plugin file exists at `.opencode/plugins/sdlc-governance.ts`
- [ ] `python3 .ai/workflows/scripts/workflow.py --root . governance-check` runs without error
- [ ] JSON output contains `block` (boolean) and `findings` (array)
- [ ] When `block=false`: no governance prompt injected
- [ ] When `block=true`: governance prompt is visible through the OpenCode prompt mechanism
- [ ] Repeated `session.idle` events do not re-inject prompts for the same finding hash
- [ ] Plugin does not mutate Roadmap, OpenSpec, Memory, EvalOps, or workflow state files

---

## Rollback

To disable the plugin:

```bash
# Option 1: Remove the plugin file
rm .opencode/plugins/sdlc-governance.ts

# Option 2: Move it out of the plugins directory
mv .opencode/plugins/sdlc-governance.ts .opencode/plugins/sdlc-governance.ts.disabled
```

The `workflow.py governance-check` command is read-only and can remain in the repository without the plugin. It does not affect any state.

---

## Troubleshooting

### `workflow.py` not found

**Symptom**: Plugin logs show `governance-check` command not found or Python traceback.

**Fix**: Ensure the target repository has `.ai/workflows/scripts/workflow.py`. If missing, bootstrap the SDLC workflow runtime into the target first (use `sdlc-project-bootstrap` skill).

### `session.idle` not firing

**Symptom**: Plugin appears loaded but never injects prompts even when `governance-check` returns `block=true`.

**Fix**:
- Verify OpenCode supports `session.idle` events (check OpenCode version).
- Check if `file.watcher.updated` is enabled in the plugin (Phase 1 does NOT use file watcher triggers).
- Confirm the plugin's `for await (const event of eventStream.stream)` loop is running (check plugin startup logs).

### Prompt append API unavailable

**Symptom**: Plugin logs show errors calling `tui.appendPrompt`.

**Fix**: The plugin uses `client.tui.appendPrompt({ body: { text: "..." }, query: { directory: "..." } })`. If this API is unavailable in the current OpenCode mode (e.g., non-TUI mode), the plugin cannot surface prompts. Verify OpenCode mode compatibility.

### Stale source copy

**Symptom**: Plugin behavior differs from expected even though the plugin file exists.

**Fix**: Check `.opencode/plugins/.install-metadata.yaml` for the source repo and ref. Compare `.opencode/plugins/sdlc-governance.ts` with the canonical source. Re-copy from the canonical source if stale.
