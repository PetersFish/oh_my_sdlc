# Remove Default Test-Agent Role Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use Superpowers `executing-plans` for sequential implementation. Use `test-driven-development` when modifying executable behavior or deterministic tests. Use `requesting-code-review` before final completion. Do not introduce OpenSpec artifacts for this cleanup unless the reviewer explicitly escalates the work.

**Goal:** Remove `test-agent` from the default SDLC lifecycle and align active docs, templates, and agent responsibilities with the Superpowers-style implementation loop: implement-agent owns normal verification and repair; review-agent owns test quality and overfitting review; optional independent verification remains non-default.

**Architecture:** Documentation-first cleanup with search-based verification. Do not add a new agent. Do not modify workflow runtime unless search reveals an active hard-coded `test-agent` dependency. Preserve workflow gates and evidence requirements.

**Tech Stack:** Markdown docs, agent/skill templates, repository search, existing pytest suite for deterministic workflow/runtime behavior.

---

## File Structure

Expected files to inspect and potentially modify:

- Modify if needed: `.ai/roadmap/areas/workflow.sdlc-orchestrator/items/RM-ORCH-007-workflow-wrapper-abstraction.md`
  - Responsibility: active roadmap statement for agent-backed lifecycle wrapper architecture.
- Modify if needed: `skills/sdlc-orchestrator/SKILL.md`
  - Responsibility: active SDLC route and gate instructions.
- Modify if needed: `.opencode/skills/sdlc-orchestrator/SKILL.md`
  - Responsibility: distributed OpenCode copy of orchestrator skill.
- Modify if needed: `.claude/skills/sdlc-orchestrator/SKILL.md`
  - Responsibility: distributed Claude copy of orchestrator skill.
- Modify if needed: `.cursor/skills/sdlc-orchestrator/SKILL.md`
  - Responsibility: distributed Cursor copy of orchestrator skill.
- Modify if needed: `skills/sdlc-project-bootstrap/templates/AGENTS.md`
  - Responsibility: generated project-level behavior guidance.
- Modify if needed: `.opencode/skills/sdlc-project-bootstrap/templates/AGENTS.md`
  - Responsibility: distributed OpenCode template copy.
- Modify if needed: `.claude/skills/sdlc-project-bootstrap/templates/AGENTS.md`
  - Responsibility: distributed Claude template copy.
- Modify if needed: `.cursor/skills/sdlc-project-bootstrap/templates/AGENTS.md`
  - Responsibility: distributed Cursor template copy.
- Modify if needed: tests under `tests/`
  - Responsibility: expectations for bootstrap, templates, wrapper contracts, and workflow behavior.

Historical archive/snapshot files should not be modified unless an active template or current instruction copies from them.

---

## Task 1: Inventory Active `test-agent` References

**Files:**
- Read-only inventory first.

- [ ] **Step 1: Search exact `test-agent` references**

Run:

```bash
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules "test-agent" .
```

Expected:

- Active files may contain stale references.
- Archive or snapshot files may contain historical references.
- Record each active reference and classify it as one of:
  - `active-default-role` — must change.
  - `active-non-default-risk-trigger` — may keep if wording is explicit.
  - `historical-archive` — leave unchanged.
  - `test-fixture` — update only if it asserts default lifecycle behavior.

- [ ] **Step 2: Search spaced phrase references**

Run:

```bash
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules -E "test agent|testing agent|independent verification" .
```

Expected:

- Identify references that do not use the exact token `test-agent`.
- Classify each active reference using the same categories as Step 1.

- [ ] **Step 3: Search default lifecycle role lists**

Run:

```bash
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules -E "plan-agent.*implement-agent.*review-agent|implement-agent.*test-agent|planning, implementation, testing, review|plan-agent.*test-agent" .
```

Expected:

- Any active default role list containing `test-agent` must be changed.
- Active default role lists should converge to `plan-agent`, `implement-agent`, `review-agent`, and `finish-agent`.

---

## Task 2: Fix Active Roadmap Drift

**Files:**
- `.ai/roadmap/areas/workflow.sdlc-orchestrator/items/RM-ORCH-007-workflow-wrapper-abstraction.md`

- [ ] **Step 1: Update completion notes if they still mention landed `test-agent` split**

Look for wording equivalent to:

```text
Landed the dev-orchestrator / plan-agent / implement-agent / test-agent / review-agent / finish-agent lifecycle split
```

Replace with:

```text
Landed the dev-orchestrator / plan-agent / implement-agent / review-agent / finish-agent lifecycle split, with normal verification owned by implement-agent and test-quality review owned by review-agent. No default test-agent role is part of the first migration.
```

Expected:

- The active roadmap item should not simultaneously say `test-agent` is non-default and that a `test-agent` split was landed.

- [ ] **Step 2: Verify active roadmap no longer contains default `test-agent` wording**

Run:

```bash
grep -n "test-agent" .ai/roadmap/areas/workflow.sdlc-orchestrator/items/RM-ORCH-007-workflow-wrapper-abstraction.md
```

Expected:

- Allowed only if wording explicitly says `No default test-agent` or explains optional future non-default verification.
- No role list should include `test-agent` as a default participant.

---

## Task 3: Update Orchestrator Guidance If Needed

**Files:**
- `skills/sdlc-orchestrator/SKILL.md`
- `.opencode/skills/sdlc-orchestrator/SKILL.md`
- `.claude/skills/sdlc-orchestrator/SKILL.md`
- `.cursor/skills/sdlc-orchestrator/SKILL.md`

- [ ] **Step 1: Inspect route and verification sections**

Search:

```bash
grep -nE "test-agent|test agent|independent verification|verification-before-completion|tdd_passed|full regression|overfitting" skills/sdlc-orchestrator/SKILL.md
```

Expected:

- If no `test-agent` references exist, do not edit solely for style.
- If verification guidance is incomplete, add a concise responsibility rule rather than a large rewrite.

- [ ] **Step 2: Add or normalize default verification responsibility wording if needed**

Use this wording if the orchestrator skill needs an explicit rule:

```md
### Default Verification Ownership

Normal implementation verification stays with the implementation worker. For behavior-changing work, the implementation worker owns TDD red/green loops, focused tests, the agreed full regression command set, and failure-fix loops while implementation context is still fresh.

Review owns quality judgment over that evidence: test adequacy, overfitting risk, assertion strength, edge-case coverage, mock realism, and whether verification evidence is credible. Do not introduce a default `test-agent` session between implementation and review. Independent verification may be requested only for high-risk changes, repeated verification failures, suspected flaky/environmental issues, release/integration gates, or EvalOps regression capture.
```

Expected:

- The rule should be placed near route, apply, or verification guidance.
- The same content should be synchronized to `.opencode`, `.claude`, and `.cursor` copies if those are generated live copies.

- [ ] **Step 3: Check distributed copies remain synchronized**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --help >/dev/null 2>&1 || true
```

Then inspect the repository's existing template sync tests or scripts before running any write-generating sync command. Do not blindly run a sync script if it modifies many unrelated files.

Expected:

- If project convention requires editing canonical `skills/` first and then syncing copies, follow that convention.
- If no safe sync path is clear, update canonical file only and list distributed copies as follow-up blockers.

---

## Task 4: Update Agent or Bootstrap Templates If Needed

**Files:**
- `skills/sdlc-project-bootstrap/templates/AGENTS.md`
- `.opencode/skills/sdlc-project-bootstrap/templates/AGENTS.md`
- `.claude/skills/sdlc-project-bootstrap/templates/AGENTS.md`
- `.cursor/skills/sdlc-project-bootstrap/templates/AGENTS.md`
- Any actual agent files discovered by search.

- [ ] **Step 1: Inspect generated behavior templates**

Run:

```bash
grep -RIn --exclude-dir=.git "test-agent\|test agent\|full regression\|overfitting" skills/sdlc-project-bootstrap/templates .opencode/skills/sdlc-project-bootstrap/templates .claude/skills/sdlc-project-bootstrap/templates .cursor/skills/sdlc-project-bootstrap/templates
```

Expected:

- If templates do not mention subagent lifecycle roles, leave them unchanged.
- If they mention default `test-agent`, update them.

- [ ] **Step 2: Update actual agent specs if present**

If search finds files such as:

```text
.opencode/agents/test-agent.md
.opencode/agent/test-agent.md
agents/test-agent.md
```

then remove or de-register them only after confirming they are active runtime files. If they are sample docs, mark them non-default instead of deleting without review.

Expected:

- No active runtime agent file should cause OpenCode to load a default `test-agent` unless the reviewer explicitly chooses to keep it.

---

## Task 5: Update Tests and Eval Expectations If Needed

**Files:**
- `tests/`
- `.ai/evals/targets/`

- [ ] **Step 1: Search tests for default `test-agent` assumptions**

Run:

```bash
grep -RIn --exclude-dir=.git "test-agent\|plan-agent.*implement-agent.*test-agent\|testing, review" tests .ai/evals || true
```

Expected:

- If tests assert default lifecycle role lists, update expected values to remove `test-agent`.
- If eval cases use `test-agent` historically but do not assert current default behavior, leave them unchanged or annotate as historical.

- [ ] **Step 2: Add regression checks only if there is deterministic code behavior**

Do not add pytest just for documentation wording. Add pytest only if implementation modifies:

- template generation logic,
- agent installation logic,
- workflow role mapping logic,
- wrapper registry code,
- deterministic routing code.

Expected:

- Documentation-only cleanup should rely on grep verification and existing tests.
- Runtime or template generation changes require pytest.

---

## Task 6: Verification Commands

- [ ] **Step 1: Verify no active default `test-agent` role remains**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

active_roots = [
    Path('skills'),
    Path('.opencode/skills'),
    Path('.claude/skills'),
    Path('.cursor/skills'),
    Path('.ai/roadmap/areas/workflow.sdlc-orchestrator/items'),
    Path('docs/superpowers'),
]

bad = []
for root in active_roots:
    if not root.exists():
        continue
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        text = path.read_text(errors='ignore')
        suspicious = [
            'plan-agent`, `implement-agent`, `test-agent`',
            'plan-agent / implement-agent / test-agent',
            'planning, implementation, testing, review, and finish as specialized agents',
            '`test-agent` performs independent verification',
        ]
        for needle in suspicious:
            if needle in text:
                bad.append((str(path), needle))

if bad:
    print('default test-agent references remain:')
    for path, needle in bad:
        print(f'- {path}: {needle}')
    raise SystemExit(1)
print('no default test-agent role references found in active roots')
PY
```

Expected:

- Command exits 0.

- [ ] **Step 2: Run relevant deterministic tests**

For docs-only changes:

```bash
python3 -m pytest tests/test_project_bootstrap_skills.py -v
python3 -m pytest tests/test_sync_templates.py -v
python3 -m pytest tests/test_workflow.py -v
```

If those pass, optionally run:

```bash
python3 -m pytest tests/ -v
```

Expected:

- Targeted tests pass.
- If full suite is not run, final summary must state that explicitly.

- [ ] **Step 3: Confirm final diff is scoped**

Run:

```bash
git diff -- docs/superpowers .ai/roadmap skills .opencode .claude .cursor tests
```

Expected:

- Diff only touches files required by this plan.
- No generated archive snapshots are rewritten unless explicitly approved.

---

## Task 7: Review Handoff

- [ ] **Step 1: Produce review summary**

The final implementation summary must include:

- Files changed.
- Whether any active `test-agent` references remain.
- Whether historical/archive references were intentionally left untouched.
- Verification commands run and results.
- Any follow-up decisions needed from the reviewer.

- [ ] **Step 2: Request code/doc review**

Use Superpowers `requesting-code-review` after the cleanup, with emphasis on:

- Responsibility boundary correctness.
- Whether the common path remains efficient.
- Whether optional independent verification is clear enough without reintroducing default `test-agent`.
- Whether implement-agent and review-agent responsibilities are too broad.

---

## Done Criteria

- [ ] The spec in `docs/superpowers/specs/2026-07-04-remove-default-test-agent.md` has been reviewed.
- [ ] Active default lifecycle docs no longer include `test-agent`.
- [ ] Normal verification ownership is assigned to `implement-agent`.
- [ ] Test quality and overfitting review ownership is assigned to `review-agent`.
- [ ] Optional independent verification is non-default and risk-triggered.
- [ ] Relevant grep checks pass.
- [ ] Relevant pytest commands pass or skipped commands are explicitly reported.
- [ ] Review handoff is complete.
