# Lifecycle Hardening And Derived Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden review execution, safe in-repo deletion, derived-artifact synchronization, and handoff metadata validation while making `finish-agent` the default owner of derived drift closure.

**Architecture:** Keep canonical source files as the single source of truth and treat distributed copies as derived artifacts checked at finish time. Fix review execution by tightening agent bash-rule ordering and permission tests, introduce a repository-scoped deletion helper, add a single aggregate `sync_derived_artifacts.py` entrypoint that composes existing sync scripts, and reject mismatched handoff artifacts before they are copied into workflow history.

**Tech Stack:** Python CLI scripts, Markdown/YAML agent prompts, workflow runtime in `.ai/workflows/scripts/workflow.py`, pytest behavioral tests, existing sync/distribution helpers.

---

## File Structure

Expected files to inspect and potentially modify:

- Modify: `agents/review-agent.md`
  - Responsibility: review-agent command permissions, derived-drift boundary wording, aggregate derived-sync instructions.
- Modify: `agents/implement-agent.md`
  - Responsibility: safe-delete allowlist and removal of default derived-drift blocking language.
- Modify: `agents/finish-agent.md`
  - Responsibility: ownership of derived-artifact check/fix and aggregate entrypoint instructions.
- Modify: distributed agent copies under `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`
  - Responsibility: activated project-level copies must reflect canonical prompt updates.
- Modify: `AGENTS.md`
  - Responsibility: repository-wide guidance for workflow sync, skill sync, and agent sync should point to the aggregate entrypoint where applicable.
- Create: `scripts/safe_delete.py`
  - Responsibility: repository-scoped safe deletion helper for agent automation.
- Create: `scripts/sync_derived_artifacts.py`
  - Responsibility: aggregate `--check` / `--fix` entrypoint for workflow templates, agents, and all canonical skills.
- Modify: `.ai/workflows/scripts/workflow.py`
  - Responsibility: validate handoff metadata before history-copy preservation.
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
  - Responsibility: canonical template must stay in sync with live workflow runtime.
- Modify after canonical sync: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`, `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`, `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
  - Responsibility: distributed workflow template copies must match canonical.
- Modify: `tests/test_wrapper_contracts.py`
  - Responsibility: agent prompt contract tests for bash rules, aggregate-entrypoint wording, and derived-drift boundaries.
- Create: `tests/test_safe_delete.py`
  - Responsibility: behavioral tests for repository-scoped deletion rules.
- Create: `tests/test_sync_derived_artifacts.py`
  - Responsibility: behavioral tests for aggregate derived-artifact orchestration.
- Modify: `tests/test_workflow.py`
  - Responsibility: behavioral tests for handoff metadata validation and history-copy gating.
- Modify if needed: `tests/test_sync_templates.py`
  - Responsibility: preserve/extend skill distribution drift expectations used by the aggregate script.

---

### Task 1: Verify And Lock Agent Bash Rule Ordering And Permission Contracts

**Files:**
- Test: `tests/test_wrapper_contracts.py`
- Read-only inspection: `agents/review-agent.md`, `agents/implement-agent.md`, `agents/finish-agent.md`
- Read-only inspection: distributed copies under `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`

**Background:** opencode uses last-match-wins semantics for permission rules. The correct pattern is catch-all `"*": deny` first, specific allows after. The repository already follows this ordering. This task verifies and locks it with tests, and provides diagnostic direction for real-world review-command blocks.

- [x] **Step 1: Write failing permission-contract tests that lock the deny-first ordering**

Add tests like:

```python
def test_review_agent_bash_catch_all_deny_is_first_rule(self):
    fm = _read_agent_frontmatter(".opencode", "review-agent")
    bash_rules = list(fm["permission"]["bash"].items())
    self.assertEqual(
        bash_rules[0], ("*", "deny"),
        "review-agent: catch-all deny must be the first bash rule so specific allows after it take effect"
    )


def test_review_agent_bash_specific_allows_follow_catch_all_deny(self):
    fm = _read_agent_frontmatter(".opencode", "review-agent")
    bash_rules = list(fm["permission"]["bash"].items())
    keys = [k for k, _ in bash_rules]
    deny_index = keys.index("*")
    for command in (
        "python3 -m pytest*",
        "pytest*",
        "python3 .ai/workflows/scripts/workflow.py *",
        "python3 scripts/*",
        "python3 skills/*",
        "git status*",
        "git diff*",
        "git log*",
    ):
        self.assertIn(command, keys)
        self.assertGreater(
            keys.index(command), deny_index,
            f"review-agent: allow rule '{command}' must come after catch-all deny"
        )
        self.assertEqual(
            fm["permission"]["bash"][command], "allow",
            f"review-agent: {command} must be allow"
        )
```

- [x] **Step 2: Run the focused contract tests and confirm they fail before the tests exist**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k "review_agent_bash or verification_commands" -v
```

Expected:

- FAIL because the new tests do not exist yet.

- [x] **Step 3: Confirm existing frontmatter ordering is correct and do NOT reorder**

Inspect the canonical prompts:

```bash
grep -n '"\*": deny' agents/review-agent.md agents/implement-agent.md agents/finish-agent.md
```

Expected:

- `"*": deny` appears as the first bash rule in each file, followed by specific allows.

If the ordering is already deny-first (it should be), no frontmatter changes are needed. The tests added in Step 1 lock this ordering. Do NOT move `"*": deny` to the end — that would cause it to override all allows under last-match-wins semantics.

If any agent file has `"*": deny` not in the first position, fix it to be first. Do not change the allow set.

- [x] **Step 4: Verify distributed copies match canonical for bash rule ordering**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --check
python3 scripts/setup_agents.py --target ./.claude/agents --check
python3 scripts/setup_agents.py --target ./.cursor/agents --check
```

Expected:

- PASS, confirming distributed copies have the same deny-first ordering as canonical.

If any distributed copy has drifted, re-distribute:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
```

- [x] **Step 5: Re-run the focused permission-contract tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k "review_agent_bash or verification_commands or observational_git" -v
```

Expected:

- PASS for the new deny-first ordering tests.
- PASS for existing observational git contract tests.

- [x] **Step 6: Commit the permission contract tests**

```bash
git add tests/test_wrapper_contracts.py
git commit -m "test: lock agent bash deny-first ordering per last-match-wins"
```

---

### Task 2: Add Repository-Scoped Safe Deletion

**Files:**
- Create: `scripts/safe_delete.py`
- Modify: `agents/implement-agent.md`
- Modify: `agents/finish-agent.md`
- Modify: distributed implement/finish copies under `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`
- Create: `tests/test_safe_delete.py`

- [x] **Step 1: Write failing behavior tests for safe deletion**

Create `tests/test_safe_delete.py` with cases like:

```python
def test_safe_delete_removes_repo_relative_file(tmp_path):
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")
    rc, out, _ = run_safe_delete(tmp_path, "victim.txt")
    assert rc == 0
    assert not target.exists()


def test_safe_delete_rejects_absolute_path(tmp_path):
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")
    rc, out, _ = run_safe_delete(tmp_path, str(target.resolve()))
    assert rc == 1
    assert "absolute_path_forbidden" in out


def test_safe_delete_rejects_protected_memory_path(tmp_path):
    protected = tmp_path / ".ai" / "memory" / "keep.md"
    protected.parent.mkdir(parents=True)
    protected.write_text("keep", encoding="utf-8")
    rc, out, _ = run_safe_delete(tmp_path, ".ai/memory/keep.md")
    assert rc == 1
    assert "protected_path" in out
```

- [x] **Step 2: Run the safe-delete tests to verify they fail before implementation**

Run:

```bash
python3 -m pytest tests/test_safe_delete.py -v
```

Expected:

- FAIL because the script and helper do not exist yet.

- [x] **Step 3: Implement `scripts/safe_delete.py` with repository boundary checks**

Start with a minimal script shape like:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROTECTED_PREFIXES = (Path(".git"), Path(".ai/memory"))


def resolve_repo_path(root: Path, raw: str) -> Path:
    rel = Path(raw)
    if rel.is_absolute():
        raise ValueError("absolute_path_forbidden")
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path_escape_forbidden")
    repo_rel = candidate.relative_to(root)
    for prefix in PROTECTED_PREFIXES:
        if repo_rel == prefix or prefix in repo_rel.parents:
            raise ValueError("protected_path")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--root", default=".")
    parser.add_argument("--recursive", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = {"deleted": [], "skipped": [], "refused": []}
    for raw in args.paths:
        try:
            target = resolve_repo_path(root, raw)
            if not target.exists():
                report["skipped"].append({"path": raw, "reason": "missing"})
            elif target.is_dir() and not args.recursive:
                report["refused"].append({"path": raw, "reason": "recursive_required"})
            elif target.is_dir():
                shutil.rmtree(target)
                report["deleted"].append({"path": raw, "kind": "directory"})
            else:
                target.unlink()
                report["deleted"].append({"path": raw, "kind": "file"})
        except ValueError as exc:
            report["refused"].append({"path": raw, "reason": str(exc)})
    print(json.dumps(report, indent=2))
    return 1 if report["refused"] else 0
```

Use JSON output with arrays for `deleted`, `skipped`, and `refused`.

- [x] **Step 4: Allow the safe-delete script in executable agents and re-distribute**

Add this bash allow-rule to `implement-agent.md` and `finish-agent.md`:

```yaml
"python3 scripts/safe_delete.py *": allow
```

Then run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
```

- [x] **Step 5: Re-run the safe-delete tests and prompt-contract tests**

Run:

```bash
python3 -m pytest tests/test_safe_delete.py tests/test_wrapper_contracts.py -k "safe_delete or finish_agent or implement_agent" -v
```

Expected:

- PASS for repo-relative deletion, protected-path refusal, non-existent-file skip, and recursive guard behavior.

- [x] **Step 6: Commit the safe-delete change**

```bash
git add scripts/safe_delete.py tests/test_safe_delete.py \
  agents/implement-agent.md agents/finish-agent.md \
  .opencode/agents/ .claude/agents/ .cursor/agents/ tests/test_wrapper_contracts.py
git commit -m "feat: add safe repository delete helper"
```

---

### Task 3: Add Aggregate Derived-Artifact Check And Fix Entry Point

**Files:**
- Create: `scripts/sync_derived_artifacts.py`
- Create: `tests/test_sync_derived_artifacts.py`
- Modify if needed: `tests/test_sync_templates.py`

- [x] **Step 1: Write failing behavior tests for aggregate `--check` and `--fix` orchestration**

Create `tests/test_sync_derived_artifacts.py` with subprocess-mocking behavior tests like:

```python
def test_check_runs_workflow_agent_and_skill_checks(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, capture_output, text):
        calls.append(args)
        return CompletedProcess(args, 0, "OK", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc, out, _ = run_sync_derived(tmp_path, "--check", "--json")
    assert rc == 0
    assert any("sync_templates.py" in " ".join(cmd) and "--check" in cmd for cmd in calls)
    assert any("setup_agents.py" in " ".join(cmd) and "--check" in cmd for cmd in calls)
    assert any("check_skill_distribution.py" in " ".join(cmd) for cmd in calls)


def test_fix_installs_all_canonical_skills(tmp_path, monkeypatch):
    calls = []
    def fake_run(args, capture_output, text):
        calls.append(args)
        return CompletedProcess(args, 0, "OK", "")

    (tmp_path / "skills" / "demo-skill").mkdir(parents=True)
    (tmp_path / "skills" / "demo-skill" / "SKILL.md").write_text("# demo\n", encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", fake_run)
    rc, out, _ = run_sync_derived(tmp_path, "--fix", "--json")
    assert rc == 0
    assert any(cmd[-1].endswith(".opencode/skills/demo-skill") for cmd in calls)
    assert any(cmd[-1].endswith(".claude/skills/demo-skill") for cmd in calls)
    assert any(cmd[-1].endswith(".cursor/skills/demo-skill") for cmd in calls)
```

- [x] **Step 2: Run the aggregate-sync tests to verify they fail before implementation**

Run:

```bash
python3 -m pytest tests/test_sync_derived_artifacts.py -v
```

Expected:

- FAIL because the script and test helpers do not exist yet.

- [x] **Step 3: Implement `scripts/sync_derived_artifacts.py --check` and `--fix`**

Structure the script around explicit suites:

```python
CHECK_TARGETS = (
    ("workflow_templates", [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--check"]),
    ("workflow_distributed", [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--check-distributed"]),
    ("agents_opencode", [sys.executable, str(SETUP_AGENTS), "--target", str(root / ".opencode/agents"), "--check"]),
    ("agents_claude", [sys.executable, str(SETUP_AGENTS), "--target", str(root / ".claude/agents"), "--check"]),
    ("agents_cursor", [sys.executable, str(SETUP_AGENTS), "--target", str(root / ".cursor/agents"), "--check"]),
    ("skills", [sys.executable, str(CHECK_SKILLS), "--root", str(root)]),
)
```

For `--fix`, compose:

```python
FIX_TARGETS = (
    [sys.executable, str(SYNC_TEMPLATES), "--root", str(root)],
    [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--distribute"],
    [sys.executable, str(SETUP_AGENTS), "--target", str(root / ".opencode/agents"), "--force"],
    [sys.executable, str(SETUP_AGENTS), "--target", str(root / ".claude/agents"), "--force"],
    [sys.executable, str(SETUP_AGENTS), "--target", str(root / ".cursor/agents"), "--force"],
)
```

Then iterate every canonical skill under `skills/` and call:

```python
[sys.executable, str(INSTALL_SKILL),
 "--source-repo", str(root),
 "--skill-name", skill_name,
 "--source-ref", source_ref,
 "--target", str(root / f".opencode/skills/{skill_name}"),
 "--status", "stable"]
```

Repeat for `.claude` and `.cursor`.

- [x] **Step 4: Re-run aggregate-sync tests and existing sync regressions**

Run:

```bash
python3 -m pytest tests/test_sync_derived_artifacts.py tests/test_sync_templates.py -v
```

Expected:

- PASS for aggregate orchestration behavior.
- PASS for existing workflow-template and skill-distribution drift checks.

- [x] **Step 5: Commit the aggregate sync entrypoint**

```bash
git add scripts/sync_derived_artifacts.py tests/test_sync_derived_artifacts.py tests/test_sync_templates.py
git commit -m "feat: add aggregate derived artifact sync"
```

---

### Task 4: Move Derived Drift Ownership To Finish And Replace Scattered Instructions

**Files:**
- Modify: `agents/implement-agent.md`
- Modify: `agents/review-agent.md`
- Modify: `agents/finish-agent.md`
- Modify: `.opencode/agents/implement-agent.md`, `.claude/agents/implement-agent.md`, `.cursor/agents/implement-agent.md`
- Modify: `.opencode/agents/review-agent.md`, `.claude/agents/review-agent.md`, `.cursor/agents/review-agent.md`
- Modify: `.opencode/agents/finish-agent.md`, `.claude/agents/finish-agent.md`, `.cursor/agents/finish-agent.md`
- Modify: `AGENTS.md`
- Test: `tests/test_wrapper_contracts.py`

- [x] **Step 1: Write failing prompt-contract tests for the new responsibility boundary**

Add tests like:

```python
def test_implement_agent_states_distributed_drift_is_not_default_blocker(self):
    body = self._read_agent_body("implement-agent")
    self.assertIn(
        "Do not treat distributed-copy drift as a default apply-change blocker",
        body,
        "implement-agent must state that distributed drift is not a default apply-change blocker"
    )


def test_review_agent_states_distributed_drift_is_finish_followup(self):
    body = self._read_agent_body("review-agent")
    self.assertIn(
        "derived drift as a finish follow-up",
        body,
        "review-agent must state that derived drift is a finish follow-up, not an apply-change blocker"
    )


def test_finish_agent_mentions_sync_derived_artifacts_entrypoint(self):
    body = self._read_agent_body("finish-agent")
    self.assertIn("python3 scripts/sync_derived_artifacts.py --check", body)
    self.assertIn("python3 scripts/sync_derived_artifacts.py --fix", body)


def test_agents_md_uses_aggregate_derived_sync_entrypoint(self):
    content = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    self.assertIn("python3 scripts/sync_derived_artifacts.py --check", content)
```

- [x] **Step 2: Run the focused prompt-contract tests and confirm they fail**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k "sync_derived_artifacts or distributed_drift or agents_md" -v
```

Expected:

- FAIL because the aggregate-entrypoint wording and boundary updates do not exist yet.

- [x] **Step 3: Update canonical subagent prompts so finish owns derived drift**

Make these content changes:

For `agents/implement-agent.md`, find the section describing when to return `blocked`. After the existing blocked-condition lines, add a new line:

```md
- Do not treat project-level distributed-copy drift as a default apply-change blocker; report it for finish-phase closure.
```

For `agents/review-agent.md`, in the Tool Usage Policy section or a new Short Boundary section, add:

```md
- Review may note derived drift as a finish follow-up, but should not reject otherwise-sufficient implementation evidence solely for project-level redistribution lag.
```

For `agents/finish-agent.md`, in the Required Skills section or a new Derived Artifact Sync section, add:

```md
## Derived Artifact Sync

Before declaring closure complete, run:

- `python3 scripts/sync_derived_artifacts.py --check`

If drift is reported and safe remediation is allowed, run:

- `python3 scripts/sync_derived_artifacts.py --fix`

Re-run `python3 scripts/sync_derived_artifacts.py --check` and keep the run blocked until it passes.
```

- [x] **Step 4: Replace scattered repository guidance with the aggregate entrypoint**

In `AGENTS.md`, replace default operator guidance like:

```md
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed
python3 scripts/setup_agents.py --target ./.opencode/agents --check
python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py \
  --source-repo . --skill-name <skill> --source-ref HEAD \
  --target .opencode/skills/<skill> --status stable
```

with primary guidance like:

```md
python3 scripts/sync_derived_artifacts.py --check
python3 scripts/sync_derived_artifacts.py --fix
```

Keep the lower-level commands only as implementation details or specialized escape hatches.

- [x] **Step 5: Re-distribute updated agent prompts and re-run prompt-contract tests**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
python3 -m pytest tests/test_wrapper_contracts.py -k "sync_derived_artifacts or distributed_drift or finish_agent or implement_agent or review_agent" -v
```

Expected:

- PASS for new aggregate-entrypoint wording and derived-boundary expectations.

- [x] **Step 6: Commit the lifecycle-boundary and instruction updates**

```bash
git add AGENTS.md agents/implement-agent.md agents/review-agent.md agents/finish-agent.md \
  .opencode/agents/ .claude/agents/ .cursor/agents/ tests/test_wrapper_contracts.py
git commit -m "docs: route derived drift checks through finish"
```

---

### Task 5: Reject Mismatched Handoff Metadata Before History Copy

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Modify after distribute: `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`, `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`, `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- Modify: `tests/test_workflow.py`

- [x] **Step 1: Write failing workflow tests for metadata mismatch blocking**

Add tests like:

```python
def test_after_dispatch_blocks_when_review_handoff_metadata_phase_mismatches(self):
    run_workflow(self.tmp, "start", subject_type="spec_change", subject_id="demo-change")
    state = self._read_current_state()
    state["current_phase"] = "apply_change"
    state.setdefault("context", {})["change_id"] = "demo-change"
    self._write_current_state(state)
    run_id = state["run_id"]
    handoff_path = f".ai/workflows/runs/active/{run_id}/handoffs/default/review-agent.md"
    with open(os.path.join(self.tmp, handoff_path), "w", encoding="utf-8") as f:
        f.write(
            "# Review Agent Handoff\n\n"
            "## Metadata\n\n"
            "- **Run ID**: demo-run\n"
            "- **Slice ID**: default\n"
            "- **Agent**: review-agent\n"
            "- **Phase**: archive_change\n"
            "- **Flow Type**: lightweight-flow\n"
            "- **Status**: success\n"
        )
    result = {
        "status": "success",
        "phase": "apply_change",
        "slice_id": "default",
        "flow_type": "lightweight-flow",
        "evidence": {
            "tasks_complete": True,
            "tdd_passed": True,
            "review_complete": True,
            "verification_passed": True,
            "review_decision": "accepted",
            "criteria_satisfied": "tasks_complete,tdd_passed,review_complete,verification_passed",
        },
        "artifacts": {"handoff_path": handoff_path},
        "blockers": [],
        "recommended_next_action": "complete_phase",
    }
    rc, out, _ = run_workflow(self.tmp, "after-dispatch", agent="review-agent", value=json.dumps(result))
    data = json.loads(out)
    self.assertEqual(data["status"], "blocked")
    self.assertIn("handoff_metadata_mismatch", json.dumps(data))
```

Add a passing companion case proving a valid metadata block still writes the history copy.

- [x] **Step 2: Run the new workflow tests to verify they fail before implementation**

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "handoff_metadata or history_copy" -v
```

Expected:

- FAIL because the runtime currently copies handoff history without metadata validation.

- [x] **Step 3: Add handoff metadata parsing and validation to `workflow.py`**

Implement a helper with a narrow contract, for example:

```python
def _read_handoff_metadata(path):
    content = open(path, encoding="utf-8").read()
    metadata = {}
    current = None
    for line in content.splitlines():
        if line.strip() == "## Metadata":
            current = "metadata"
            continue
        if current == "metadata" and line.startswith("## "):
            break
        if current == "metadata" and line.startswith("- **") and "**:" in line:
            key, value = line[4:].split("**:", 1)
            metadata[key.strip()] = value.strip()
    return metadata
```

Before `_write_handoff_history_copy(...)`, compare the parsed metadata against the current run context and block on mismatches with a structured blocker reason such as `handoff_metadata_mismatch`.

- [x] **Step 4: Sync live workflow to canonical template and distribute the template copies**

Run:

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute
```

Expected:

- Canonical and distributed workflow template copies match the updated runtime.

- [x] **Step 5: Re-run workflow and template-sync tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py -k "handoff_metadata or history_copy" -v
python3 -m pytest tests/test_sync_all_distributed.py tests/test_sync_templates.py -v
```

Expected:

- PASS for metadata mismatch blocking and valid history-copy preservation.
- PASS for live/canonical/distributed workflow template sync checks.

- [x] **Step 6: Commit the handoff validation change**

```bash
git add .ai/workflows/scripts/workflow.py skills/sdlc-project-bootstrap/templates/workflow/workflow.py \
  .opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py \
  .claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py \
  .cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py \
  tests/test_workflow.py tests/test_sync_all_distributed.py tests/test_sync_templates.py
git commit -m "fix: validate handoff metadata before history copy"
```

---

### Task 6: Run Final Regression And Derived Sync Verification

**Files:**
- No new source files; this task verifies the combined change set.

- [x] **Step 1: Run the focused regression suite for changed areas**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py tests/test_safe_delete.py \
  tests/test_sync_derived_artifacts.py tests/test_sync_templates.py \
  tests/test_sync_all_distributed.py tests/test_workflow.py -v
```

Expected:

- PASS for all directly modified script, prompt, distribution, and workflow tests.

- [x] **Step 2: Run the aggregate derived fix once, then verify clean derived state**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --fix
python3 scripts/sync_derived_artifacts.py --check --json
```

Expected:

- `--fix` completes without error.
- `--check --json` reports success for workflow templates, agents, and skills.

- [x] **Step 3: Run the broader repository regression most likely to catch collateral drift**

Run:

```bash
python3 -m pytest tests/test_precommit_hook.py tests/test_install_agents.py tests/test_setup_agents.py -v
```

Expected:

- PASS for pre-commit enforcement, agent distribution, and aggregate setup behavior.

- [x] **Step 4: Commit the final integrated state**

```bash
git add AGENTS.md agents/ .opencode/agents/ .claude/agents/ .cursor/agents/ \
  .ai/workflows/scripts/workflow.py skills/sdlc-project-bootstrap/templates/workflow/ \
  .opencode/skills/ .claude/skills/ .cursor/skills/ scripts/safe_delete.py \
  scripts/sync_derived_artifacts.py tests/
git commit -m "feat: harden lifecycle sync and handoff validation"
```

---

## Self-Review

- Spec coverage check:
  - review permission hardening (verify and lock deny-first ordering): Task 1
  - safe deletion: Task 2
  - aggregate derived sync: Task 3
  - finish-owned drift boundary + instruction replacement: Task 4
  - handoff metadata validation: Task 5
  - final integrated verification: Task 6
- Placeholder scan:
  - no `TODO`, `TBD`, or “similar to above” instructions remain
- Type/command consistency:
  - aggregate entrypoint uses `scripts/sync_derived_artifacts.py --check|--fix`
  - safe deletion uses `python3 scripts/safe_delete.py *`
  - workflow template sync continues to use `sync_templates.py`
