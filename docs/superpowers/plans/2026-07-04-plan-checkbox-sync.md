# Plan Checkbox Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure superpowers plan checkboxes (`- [ ]`) are incrementally synced to `- [x]` as steps complete during execution, covering both build mode (direct skill invocation) and lightweight-flow (dev-orchestrator → implement-agent) paths, without modifying superpowers source.

**Architecture:** Three project-level additions — a validation script (`scripts/check_plan_checkboxes.py`), an AGENTS.md discipline section, and a one-line pointer in `agents/implement-agent.md`. No workflow runtime, agent prompt logic, or superpowers skill source changes.

**Tech Stack:** Python stdlib script, Markdown rule files, unittest.

**Repository Policy Note:** Do not commit during execution of this plan unless the user explicitly asks. Use `git status`/`git diff` checkpoints instead of commit steps.

---

## File Structure

- `scripts/check_plan_checkboxes.py`: NEW validation script (stdlib only).
- `AGENTS.md`: MODIFY — append `Plan Checkbox Sync Discipline` section.
- `agents/implement-agent.md`: MODIFY — add one-line pointer in `Design Artifact Reading Priority` section.
- `tests/test_check_plan_checkboxes.py`: NEW unittest file.

---

### Task 1: Write The Validation Script

**Files:**
- Create: `scripts/check_plan_checkboxes.py`

- [x] **Step 1: Create `scripts/check_plan_checkboxes.py`**

```python
#!/usr/bin/env python3
"""Check a superpowers plan file for unchecked checkboxes.

Usage:
    python3 scripts/check_plan_checkboxes.py <plan_path>

Exit codes:
    0 — all checkboxes checked (or no checkboxes found)
    1 — one or more unchecked checkboxes remain
    2 — file not found
"""

import re
import sys
from pathlib import Path

CHECKBOX_RE = re.compile(r"^\s*- \[ \]")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_plan_checkboxes.py <plan_path>", file=sys.stderr)
        return 2

    plan_path = Path(argv[1])
    if not plan_path.is_file():
        print(f"error: file not found: {plan_path}", file=sys.stderr)
        return 2

    unchecked: list[str] = []
    for lineno, line in enumerate(plan_path.read_text(encoding="utf-8").splitlines(), start=1):
        if CHECKBOX_RE.match(line):
            unchecked.append(f"{plan_path}:{lineno}: {line.strip()}")

    if unchecked:
        print(f"error: {len(unchecked)} unchecked checkbox(es) remain in {plan_path}:")
        for entry in unchecked:
            print(f"  {entry}")
        return 1

    print(f"ok: all checkboxes complete in {plan_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [x] **Step 2: Make the script executable**

Run:

```bash
chmod +x scripts/check_plan_checkboxes.py
```

- [x] **Step 3: Smoke-test the script against an existing plan**

Run:

```bash
python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-04-exit-criteria-evidence-key-satisfaction.md
```

Expected: exit 1 with a list of unchecked steps (that plan was executed without checkbox sync, so all steps should still be `- [ ]`).

---

### Task 2: Write Unittests For The Script

**Files:**
- Create: `tests/test_check_plan_checkboxes.py`

- [x] **Step 1: Create `tests/test_check_plan_checkboxes.py`**

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = os.path.join("scripts", "check_plan_checkboxes.py")


def run_script(plan_path: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, SCRIPT, plan_path],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestCheckPlanCheckboxes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.plan = Path(self.tmp) / "plan.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def test_all_checked_exit_0(self):
        self.plan.write_text(
            "# Plan\n\n"
            "- [x] **Step 1: do thing**\n\n"
            "- [x] **Step 2: do other thing**\n"
        )
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 0)
        self.assertIn("all checkboxes complete", out)

    def test_unchecked_exit_1(self):
        self.plan.write_text(
            "# Plan\n\n"
            "- [ ] **Step 1: do thing**\n\n"
            "- [x] **Step 2: do other thing**\n"
        )
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 1)
        self.assertIn("unchecked checkbox", out)
        self.assertIn("Step 1", out)

    def test_no_checkboxes_exit_0(self):
        self.plan.write_text("# Plan\n\nNo steps here.\n")
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 0)
        self.assertIn("all checkboxes complete", out)

    def test_missing_file_exit_2(self):
        rc, _, err = run_script(str(Path(self.tmp) / "nope.md"))
        self.assertEqual(rc, 2)
        self.assertIn("file not found", err)

    def test_mixed_checked_unchecked_exit_1(self):
        self.plan.write_text(
            "### Task 1\n\n"
            "- [x] **Step 1: write test**\n\n"
            "- [ ] **Step 2: run test**\n\n"
            "- [ ] **Step 3: implement**\n\n"
            "### Task 2\n\n"
            "- [x] **Step 1: commit**\n"
        )
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 1)
        self.assertIn("2 unchecked", out)
        self.assertIn("Step 2", out)
        self.assertIn("Step 3", out)
        self.assertNotIn("Step 1", out)

    def test_indented_checkbox_detected(self):
        self.plan.write_text(
            "# Plan\n\n"
            "  - [ ] **Step 1: indented**\n"
        )
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 1)
        self.assertIn("Step 1", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [x] **Step 2: Run the tests to verify green phase**

Run:

```bash
python3 -m pytest tests/test_check_plan_checkboxes.py -v
```

Expected: PASS — all 6 tests pass.

---

### Task 3: Add AGENTS.md Discipline Section

**Files:**
- Modify: `AGENTS.md`

- [x] **Step 1: Append `Plan Checkbox Sync Discipline` section to AGENTS.md**

Add the following section at the end of `AGENTS.md` (after the existing `Agent Updates Discipline` section):

```markdown
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
```

- [x] **Step 2: Verify the section was added correctly**

Run:

```bash
grep -n "Plan Checkbox Sync Discipline" AGENTS.md
```

Expected: one match at the end of the file.

---

### Task 4: Add Pointer In implement-agent.md

**Files:**
- Modify: `agents/implement-agent.md`

- [x] **Step 1: Add one-line pointer after `Design Artifact Reading Priority` section**

In `agents/implement-agent.md`, after the line:

```
Use `artifacts.primary_design_path` as the approved review entry, not as the
only source of implementation requirements.
```

Add:

```
Plan checkbox sync: when `artifacts.primary_design_path` matches
`docs/superpowers/plans/*.md`, follow AGENTS.md `Plan Checkbox Sync Discipline`
section — check off each step as it completes and run the validation script
before returning `tasks_complete: true`.
```

- [x] **Step 2: Verify the pointer was added**

Run:

```bash
grep -n "Plan checkbox sync" agents/implement-agent.md
```

Expected: one match.

---

### Task 5: Sync Distributed Agent Copies And Final Regression

**Files:**
- Distributed agent copies under `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`

- [x] **Step 1: Sync canonical agent definition to distributed copies**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
```

Expected: each command succeeds with activation.

- [x] **Step 2: Verify distributed copies contain the pointer**

Run:

```bash
grep -l "Plan checkbox sync" .opencode/agents/implement-agent.md .claude/agents/implement-agent.md .cursor/agents/implement-agent.md
```

Expected: all three paths listed.

- [x] **Step 3: Run the new script tests**

Run:

```bash
python3 -m pytest tests/test_check_plan_checkboxes.py -v
```

Expected: PASS — all 6 tests.

- [x] **Step 4: Run full test regression to confirm no breakage**

Run:

```bash
python3 -m pytest tests/ -v
```

Expected: PASS — all existing tests still pass, plus the 6 new tests.

- [x] **Step 5: Inspect final diff for scope control**

Run:

```bash
git status --short
git diff -- AGENTS.md agents/implement-agent.md
```

Expected: only `AGENTS.md` (new section), `agents/implement-agent.md` (one-line pointer), `scripts/check_plan_checkboxes.py` (new), `tests/test_check_plan_checkboxes.py` (new), and distributed agent copies (synced). No workflow.py, no superpowers skill source, no other agent definitions touched.

---

## Self-Review

**Spec coverage:** Covered both execution paths (build mode direct skill + lightweight-flow implement-agent), the trigger condition (path match `docs/superpowers/plans/*.md`), the non-trigger (spec-flow proposal.md), the sync procedure (incremental edit + pre-completion validation), and the validation script interface (exit codes 0/1/2).

**Placeholder scan:** No TODO/TBD placeholders. Script code, test code, AGENTS.md section text, and implement-agent.md pointer text are all explicit and complete.

**Type consistency:** Uses `plan_path`, `primary_design_path`, `tasks_complete`, `lightweight-flow`, `spec-flow`, `executing-plans`, `subagent-driven-development`, and `check_plan_checkboxes.py` consistently across tasks. Exit codes (0/1/2) are consistent between script, tests, and AGENTS.md procedure.

**Scope control:** No workflow runtime changes. No superpowers skill source changes. No phase definition or evidence-key changes. Only project-level files (AGENTS.md, one agent definition, one script, one test file) and derived distributed agent copies.