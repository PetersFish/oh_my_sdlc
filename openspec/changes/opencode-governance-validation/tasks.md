## 1. EvalOps Gate

- [ ] 1.1 Identify the EvalOps target id for this change, likely `workflow.sdlc-orchestrator` or another repository-standard target for SDLC governance behavior
- [ ] 1.2 Review or define EvalOps coverage for governance prompt behavior, including dangling archive prompts, pending hook prompts, deduplication, and stop condition language
- [ ] 1.3 Generate or update candidate EvalOps cases for the affected target and complete required triage/golden promotion before implementation, unless the user explicitly grants an EvalOps exception

## 2. Governance Check Command

- [ ] 2.1 Add `governance-check` to `.ai/workflows/scripts/workflow.py` as a read-only subcommand with explicit `--root` support
- [ ] 2.2 Implement archived OpenSpec change discovery under `openspec/changes/archive/`
- [ ] 2.3 Implement matching workflow evidence detection for the active current run and done history runs
- [ ] 2.4 Emit `dangling_archive` findings with change id, archive path, message, remediation text, and stable hash
- [ ] 2.5 Implement active-run `pending_hooks` detection with run id, change id when available, pending hook names, remediation text, and stable hash
- [ ] 2.6 Return a structured JSON contract with `block` and `findings`, using `block=false` when no governance remediation is required
- [ ] 2.7 Preserve read-only behavior so the command does not mutate workflow run state or domain files

## 3. Governance Tests

- [ ] 3.1 Add temporary-root fixtures for clean state, dangling archived change, active run pending hooks, and combined findings
- [ ] 3.2 Test clean state returns `block=false` with no blocking findings
- [ ] 3.3 Test dangling archive returns `block=true` with `dangling_archive`, change id, archive path, remediation text, and stable hash
- [ ] 3.4 Test archived change with matching active run is not classified as dangling
- [ ] 3.5 Test archived change with matching done history run is not classified as dangling
- [ ] 3.6 Test pending hooks return `block=true` with hook names, run/change context, remediation text, and stable hash
- [ ] 3.7 Test combined diagnostics return both dangling archive and pending hook findings
- [ ] 3.8 Test `governance-check` write boundaries so it does not mutate fixture Roadmap, OpenSpec, Memory, EvalOps, or workflow state files

## 4. OpenCode Plugin

- [ ] 4.1 Add `.opencode/plugins/sdlc-governance.ts` as a thin adapter for the Python governance command
- [ ] 4.2 Subscribe to `session.idle` as the Phase 1 trigger and keep `file.watcher.updated` disabled/deferred
- [ ] 4.3 Run `python3 .ai/workflows/scripts/workflow.py --root <project-root> governance-check` from the plugin and parse JSON output
- [ ] 4.4 Append remediation prompts only when `block=true` using the selected OpenCode prompt/UI mechanism
- [ ] 4.5 Include finding-specific prompt text for dangling archives and pending hooks, including the `governance-check` stop condition
- [ ] 4.6 Deduplicate prompt injection by stable finding hash for the current process/session scope
- [ ] 4.7 Handle command failures or malformed JSON without mutating state or creating repeated prompt loops

## 5. OpenCode Adapter Validation

- [ ] 5.1 Verify `session.idle` fires after assistant turn completion in the target OpenCode mode
- [ ] 5.2 Verify the selected prompt/UI mechanism appends a visible actionable remediation prompt
- [ ] 5.3 Verify repeated idle events do not inject duplicate prompts for the same finding hash
- [ ] 5.4 Verify the plugin remains silent when `governance-check` returns `block=false`

## 6. Final Verification

- [ ] 6.1 Run the relevant Python test suite for workflow governance diagnostics
- [ ] 6.2 Run any relevant OpenCode plugin TypeScript checks or repository lint/typecheck commands if available
- [ ] 6.3 Run `python3 .ai/workflows/scripts/workflow.py --root . governance-check` and confirm the output contract is usable by the plugin
- [ ] 6.4 Run `openspec status --change opencode-governance-validation` and confirm artifacts remain complete before implementation begins
- [ ] 6.5 Run the Promptfoo golden eval for the affected EvalOps target and confirm required governance behavior cases pass, unless an explicit EvalOps exception is recorded
- [ ] 6.6 Report golden eval evidence in the final summary, including target id, case counts, command, pass/fail result, and report path when available
