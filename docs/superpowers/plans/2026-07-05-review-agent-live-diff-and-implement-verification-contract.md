# Review Agent Live Diff And Implement Verification Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `implement-agent` deliver auditable changed-file and verification evidence, make `review-agent` review the actual live Git change set, and prevent review from defaulting to duplicate broad regression that belongs to implementation.

**Architecture:** Keep canonical agent prompts under `agents/` as the source of truth. Add prompt-contract tests first, update canonical `implement-agent`, `review-agent`, and `dev-orchestrator` contracts, then redistribute derived agent copies through `scripts/setup_agents.py`. `implement-agent` owns focused verification and full regression. `review-agent` owns live diff review, verification evidence inspection, and targeted exception-path re-runs only.

**Tech Stack:** Markdown/YAML agent prompts, Python pytest prompt-contract tests, existing agent distribution scripts, existing workflow lifecycle contracts.

---

## File Structure

Expected files to inspect and potentially modify:

- Modify: `agents/implement-agent.md`
  - Responsibility: changed-file handoff contract, full regression gate, verification command evidence.
- Modify: `agents/review-agent.md`
  - Responsibility: live change review protocol, verification reuse protocol, read-only Git permission additions, final JSON contract discipline.
- Modify: `agents/dev-orchestrator.md`
  - Responsibility: review dispatch must forward implement-agent change-set and verification evidence.
- Modify after canonical sync: `.opencode/agents/implement-agent.md`, `.claude/agents/implement-agent.md`, `.cursor/agents/implement-agent.md`
  - Responsibility: derived copies must reflect canonical implement-agent changes.
- Modify after canonical sync: `.opencode/agents/review-agent.md`, `.claude/agents/review-agent.md`, `.cursor/agents/review-agent.md`
  - Responsibility: derived copies must reflect canonical review-agent changes and activated model/variant frontmatter.
- Modify after canonical sync: `.opencode/agents/dev-orchestrator.md`, `.claude/agents/dev-orchestrator.md`, `.cursor/agents/dev-orchestrator.md`
  - Responsibility: derived copies must reflect canonical dispatch-contract changes.
- Modify: `tests/test_wrapper_contracts.py`
  - Responsibility: prompt-contract tests for permissions, live diff protocol, verification reuse, implement full regression, and dev-orchestrator review dispatch.
- Read: `docs/superpowers/specs/2026-07-05-review-agent-live-diff-and-implement-verification-contract.md`
  - Responsibility: source requirements for this plan.
- Read if needed: `AGENTS.md`
  - Responsibility: canonical-vs-derived update discipline and sync commands.

---

## Task 1: Add Failing Prompt-Contract Tests

**Files:**
- Modify: `tests/test_wrapper_contracts.py`
- Read: `agents/implement-agent.md`
- Read: `agents/review-agent.md`
- Read: `agents/dev-orchestrator.md`

**Purpose:** Lock the intended behavior before prompt changes. The tests should initially fail for missing protocol text and missing review-agent Git allow rules.

- [x] **Step 1: Inspect existing prompt-contract test helpers**

Find existing helpers in `tests/test_wrapper_contracts.py` for reading agent frontmatter and prompt bodies. Use existing helper patterns rather than creating unrelated parsing code.

- [x] **Step 2: Add review-agent Git permission tests**

Add tests that assert `review-agent` bash rules contain all of the following after the catch-all deny rule:

```python
required = (
    "git status*",
    "git diff*",
    "git log*",
    "git ls-files*",
    "git check-ignore*",
    "git worktree*",
)
```

Assertions:

- every required command exists;
- every required command value is `allow`;
- every required command appears after `"*": deny`.

- [x] **Step 3: Add review-agent Live Change Review Protocol tests**

Add tests that inspect canonical `agents/review-agent.md` and assert it contains:

```text
Live Change Review Protocol
live Git working tree is the source of truth
CodeGraph may be used only after the live change set is known
git diff --name-status
git diff --cached --name-status
git ls-files --others --exclude-standard
review_change_set_missing
review_change_set_mismatch
```

- [x] **Step 4: Add review-agent Verification Reuse Protocol tests**

Add tests that inspect canonical `agents/review-agent.md` and assert it contains:

```text
Verification Reuse Protocol
Review-agent is not the primary test executor
Do not run full `tests/` by default
Run the smallest command set
broad regression
```

Also assert the prompt does not say or imply that broad regression is default review behavior.

- [x] **Step 5: Add review-agent final JSON contract tests**

Add tests that inspect canonical `agents/review-agent.md` and assert it contains:

```text
Final Output Contract Discipline
exactly one valid JSON object
artifacts.design_artifact_paths
must be a JSON array
Do not include handoff prose in the final response
```

- [x] **Step 6: Add implement-agent changed-file and full regression contract tests**

Add tests that inspect canonical `agents/implement-agent.md` and assert it contains:

```text
Implementation Change-Set Handoff Contract
changed_files
worktree_path
diff_commands
verification_commands
Full Regression Gate
python3 -m pytest tests/ -v
Do not return `status: success` until focused verification and full regression both pass
```

- [x] **Step 7: Add dev-orchestrator review dispatch contract tests**

Add tests that inspect canonical `agents/dev-orchestrator.md` and assert it contains:

```text
Review Dispatch Change-Set Contract
changed_files
worktree_path
diff_commands
verification_commands
review_change_set_missing
review_change_set_mismatch
Do not use CodeGraph as the source of truth for uncommitted changes
```

- [x] **Step 8: Run focused tests and confirm expected failures**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k "review_agent or implement_agent or dev_orchestrator" -v
```

Expected:

- FAIL for newly added contract tests that describe behavior not yet present.

Do not weaken the tests to pass against the current prompts.

---

## Task 2: Update Canonical Implement-Agent Contract

**Files:**
- Modify: `agents/implement-agent.md`

**Purpose:** Make implementation success depend on real changed-file evidence plus focused and full regression evidence.

- [x] **Step 1: Add Implementation Change-Set Handoff Contract section**

Add a section near the existing output contract:

```md
## Implementation Change-Set Handoff Contract

Before returning success, discover and report the implementation change set from the live worktree.

Required artifact fields:
- `worktree_path`
- `repo_root`
- `base_ref`
- `changed_files[]`
- `diff_commands[]`
- `verification_commands[]`

Rules:
- If implementation changed files, `changed_files` must be non-empty.
- Include unstaged tracked, staged, and untracked files.
- Include `covered_by` or equivalent verification coverage for changed files when available.
- If using a git worktree, report the exact `worktree_path` used for implementation.
```

- [x] **Step 2: Expand the JSON output example**

Update the implement-agent output contract so `artifacts` includes:

```json
{
  "worktree_path": "/path/to/worktree",
  "repo_root": "/path/to/repo",
  "base_ref": "HEAD",
  "changed_files": [
    {
      "path": "path/to/file.py",
      "status": "added|modified|deleted|renamed|untracked|staged",
      "source": "git diff|git diff --cached|git ls-files --others",
      "reason": "why this file changed",
      "covered_by": ["python3 -m pytest ..."]
    }
  ],
  "diff_commands": ["git diff -- path/to/file.py"],
  "verification_commands": [
    {
      "command": "python3 -m pytest tests/ -v",
      "scope": "full_regression",
      "result": "pass",
      "covers": ["tests/"]
    }
  ],
  "raw_log_paths": []
}
```

Keep the existing `handoff_path` and `raw_log_paths` fields.

- [x] **Step 3: Add Full Regression Gate section**

Add this section to `agents/implement-agent.md`. The outer fence below intentionally uses four backticks so the inner bash fence renders correctly.

````md
## Full Regression Gate

After all focused tests for the implementation pass, run the project-level regression suite before returning success.

Default full regression command:

```bash
python3 -m pytest tests/ -v
```

Rules:
- Do not return `status: success` until focused verification and full regression both pass.
- If full regression fails because of the current change, diagnose and fix it within the same implement-agent loop.
- If full regression fails for a pre-existing or environment-related reason, return `status: blocked` with evidence.
- If full regression is intentionally skipped, return `status: blocked` unless the user explicitly approved the skip.
- Include the full regression command and result in `artifacts.verification_commands`.
````

- [x] **Step 4: Update success conditions**

Update the existing success requirements so success requires:

- tasks complete;
- focused tests pass;
- full regression passes or an explicitly approved skip exists;
- provider verification passes when required;
- no blockers remain;
- changed-file evidence is complete.

- [x] **Step 5: Preserve implement-agent boundaries**

Do not make implement-agent responsible for final review or approval. It still returns `recommended_next_action: dispatch_review_agent` on success.

---

## Task 3: Update Canonical Review-Agent Contract

**Files:**
- Modify: `agents/review-agent.md`

**Purpose:** Make review diff-first, evidence-first, and targeted-test-only by default.

- [x] **Step 1: Add Git permission allow rules**

In `permission.bash`, add these specific allows after the existing Git allows or after `git log*`:

```yaml
"git ls-files*": allow
"git check-ignore*": allow
"git worktree*": allow
```

Preserve catch-all deny as the first bash rule.

- [x] **Step 2: Add Live Change Review Protocol**

Add a section under Tool Usage Policy:

```md
## Live Change Review Protocol

For apply_change code review, the live Git working tree is the source of truth for uncommitted implementation changes.

Before using CodeGraph for implementation review, discover and validate the live change set:

1. `git status --short --branch`
2. `git diff --name-status`
3. `git diff --cached --name-status`
4. `git ls-files --others --exclude-standard`
5. `git diff --stat`
6. `git diff --cached --stat`

Rules:
- Use `git diff -- <path>` for unstaged tracked changes.
- Use `git diff --cached -- <path>` for staged changes.
- Use `Read` for untracked files discovered by `git ls-files --others --exclude-standard`.
- Review every file in the final changed file set unless explicitly marked generated/derived and covered by an agreed lifecycle boundary.
- CodeGraph may be used only after the live change set is known, and only to understand surrounding committed code.
- If CodeGraph disagrees with live Git, trust live Git for review scope.
- If no changed files are found but implement-agent reported implementation changes, return blocker `review_change_set_missing`.
- If the live change set contradicts implement-agent handoff evidence, return blocker `review_change_set_mismatch`.
```

- [x] **Step 3: Add Verification Reuse Protocol**

Add:

```md
## Verification Reuse Protocol

Review-agent is not the primary test executor.

Default behavior:
- Inspect implement-agent verification evidence first.
- Do not re-run focused tests that implement-agent already ran and reported passing.
- Do not run broad regression suites by default.
- Do not run full `tests/` by default.
- Do not run derived-artifact sync checks by default unless the changed files or plan requirements make that evidence necessary and implement-agent did not provide it.

Review-agent may run tests only when:
1. implement-agent evidence is missing, incomplete, stale, or contradictory;
2. changed files are not covered by implement-agent verification evidence;
3. review identifies a concrete code risk that needs executable confirmation;
4. the implementation modifies test infrastructure, workflow dispatch, wrapper contracts, or verification tooling and evidence is insufficient;
5. the user explicitly asks review-agent to re-run verification;
6. a lightweight targeted smoke test is necessary before approval.

When re-running tests:
- Run the smallest command set that answers the review question.
- Prefer one targeted command over broad regression.
- Record why each re-run was necessary.
- If broad regression is needed, record the trigger explicitly.
```

- [x] **Step 4: Add Final Output Contract Discipline**

Add:

```md
## Final Output Contract Discipline

Before returning, ensure the final response is exactly one valid JSON object.

Rules:
- Do not include Markdown outside the JSON object.
- Do not include handoff prose in the final response.
- If writing a handoff artifact, write Markdown to the artifact file only.
- `artifacts.design_artifact_paths` must be a JSON array.
- `artifacts.raw_log_paths` must be a JSON array.
- `blockers` must be a JSON array.
- `recommended_next_action` must match the allowed enum.
```

- [x] **Step 5: Update output examples if needed**

Ensure review-agent examples use:

```json
"design_artifact_paths": [
  "docs/superpowers/plans/example.md",
  "docs/superpowers/specs/example.md"
]
```

Do not leave any malformed array examples.

---

## Task 4: Update Canonical Dev-Orchestrator Review Dispatch Contract

**Files:**
- Modify: `agents/dev-orchestrator.md`

**Purpose:** Ensure review-agent receives the exact implement-agent change set and cannot silently infer review scope.

- [x] **Step 1: Add Review Dispatch Change-Set Contract section**

Under dispatch lifecycle or near the implement-agent success -> review-agent handoff wording, add:

```md
## Review Dispatch Change-Set Contract

When `implement-agent` succeeds and `after-dispatch` returns `dispatch_review_agent`, the review-agent task prompt MUST forward implement-agent change-set and verification evidence as the primary review target.

Forward at minimum:
- `artifacts.worktree_path`
- `artifacts.repo_root`
- `artifacts.base_ref`
- `artifacts.changed_files[]`
- `artifacts.diff_commands[]`
- `artifacts.verification_commands[]`
- `artifacts.handoff_path`

The review-agent task prompt MUST instruct review-agent to:
- verify the current worktree matches `worktree_path`;
- validate live Git state against `changed_files`;
- return blocker `review_change_set_missing` if change-set evidence is absent or empty for an implementation task;
- return blocker `review_change_set_mismatch` if live Git state contradicts the handoff;
- inspect implement-agent verification evidence before deciding whether any test re-run is necessary;
- not use CodeGraph as the source of truth for uncommitted changes.
```

- [x] **Step 2: Update review-agent task description guidance**

Where `dev-orchestrator` describes dispatching review-agent, include a concise task phrase such as:

```text
Review the implement-agent live change set, validate verification evidence, and decide apply_change acceptance.
```

- [x] **Step 3: Preserve lifecycle hook behavior**

Do not bypass `before-dispatch` or `after-dispatch`. The new contract changes the task prompt content, not the workflow hook sequence.

---

## Task 5: Run Focused Tests, Fix Prompt Drift, And Sync Derived Agents

**Files:**
- Modify if needed: `tests/test_wrapper_contracts.py`
- Generated/updated by script: `.opencode/agents/*`, `.claude/agents/*`, `.cursor/agents/*`

- [x] **Step 1: Run focused prompt-contract tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py -k "review_agent or implement_agent or dev_orchestrator" -v
```

Expected:

- PASS for all newly added prompt-contract tests.

If tests fail because exact wording differs, prefer updating prompt wording to include the explicit contract terms rather than weakening the tests.

- [x] **Step 2: Sync derived agent artifacts**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
python3 scripts/setup_agents.py --target ./.claude/agents --force
python3 scripts/setup_agents.py --target ./.cursor/agents --force
```

Expected:

- Project-level derived agent copies are regenerated and activated.
- Activated copies include valid `model` and `variant` frontmatter.

- [x] **Step 3: Check derived agent sync**

Run:

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --check
python3 scripts/setup_agents.py --target ./.claude/agents --check
python3 scripts/setup_agents.py --target ./.cursor/agents --check
```

Expected:

- PASS for all targets.

- [x] **Step 4: Run broader relevant tests**

Run:

```bash
python3 -m pytest tests/test_wrapper_contracts.py tests/test_install_agents.py tests/test_setup_agents.py -v
```

Expected:

- PASS.

---

## Task 6: Optional Manual Simulation Of Review Behavior

**Files:**
- No required file changes unless the simulation exposes a defect.

**Purpose:** Exercise the updated prompt behavior with a small local change before relying on it in a real apply_change flow.

- [x] **Step 1: Create a temporary uncommitted change in a safe scratch file**

Use a harmless test fixture or documentation scratch file. Do not use production source files unless needed.

- [x] **Step 2: Confirm live Git discovery commands expose the change**

Run:

```bash
git status --short --branch
git diff --name-status
git diff --cached --name-status
git ls-files --others --exclude-standard
```

Expected:

- The live change appears in the appropriate command output.

- [x] **Step 3: Confirm review-agent prompt would require diff-first review**

Inspect `agents/review-agent.md` and `.opencode/agents/review-agent.md` to confirm the distributed copy contains:

```text
Live Change Review Protocol
Verification Reuse Protocol
Final Output Contract Discipline
```

- [x] **Step 4: Clean up the temporary scratch change**

Revert or delete the temporary scratch change using the normal safe cleanup path.

---

## Task 7: Final Verification And Evidence

**Files:**
- Read-only unless failures require fixes.

- [x] **Step 1: Run focused contract suite**

```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
```

Expected:

- PASS.

- [x] **Step 2: Run agent setup/distribution suites**

```bash
python3 -m pytest tests/test_install_agents.py tests/test_setup_agents.py -v
```

Expected:

- PASS.

- [x] **Step 3: Run full project regression**

```bash
python3 -m pytest tests/ -v
```

Expected:

- PASS.

This is required because this change modifies agent contracts and tests, and it establishes the policy that implement-agent must run full regression before success.

- [x] **Step 4: Check derived artifacts**

Run:

```bash
python3 scripts/sync_derived_artifacts.py --check --json
```

Expected:

- PASS / status ok.

If this fails only because newly edited canonical agent files have not been redistributed, run the setup commands from Task 5 and retry.

---

## Acceptance Checklist

- [x] `agents/implement-agent.md` requires changed-file evidence in success handoff.
- [x]`agents/implement-agent.md` requires focused verification plus full regression before success.
- [x]`agents/review-agent.md` can discover unstaged, staged, and untracked changes.
- [x]`agents/review-agent.md` states live Git is the source of truth for uncommitted review scope.
- [x]`agents/review-agent.md` constrains CodeGraph to post-diff structural understanding.
- [x]`agents/review-agent.md` defaults to inspecting implement-agent verification evidence instead of re-running broad tests.
- [x]`agents/review-agent.md` still permits targeted test re-runs when justified.
- [x]`agents/review-agent.md` requires exactly one valid JSON final response.
- [x]`agents/dev-orchestrator.md` forwards implement-agent change-set and verification evidence to review-agent.
- [x]`tests/test_wrapper_contracts.py` locks the new contracts.
- [x]`.opencode/`, `.claude/`, and `.cursor/` derived agent copies are synced.
- [x]Focused contract tests pass.
- [x]Agent setup/distribution checks pass.
- [x]Full project regression passes.
