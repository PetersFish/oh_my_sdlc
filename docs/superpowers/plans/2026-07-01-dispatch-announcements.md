# User-Facing Dispatch Announcements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "User-Facing Dispatch Announcements" chapter to `agents/dev-orchestrator.md` so users see WHY agents are dispatched and WHAT they accomplished.

**Architecture:** Single markdown chapter insertion into an existing agent prompt file. No code, no dependencies — pure prompt engineering.

**Tech Stack:** Markdown (agent prompt file)

---

## File Structure

| Action | File | Lines Affected |
|---|---|---|
| Modify | `agents/dev-orchestrator.md` | Insert after line 208, before line 209 |

Only one file changes. No new files created.

---

### Task 1: Add "User-Facing Dispatch Announcements" Chapter

**Files:**
- Modify: `agents/dev-orchestrator.md:208-209` (insert between lines)

**Context:** The chapter goes after "Dispatch Lifecycle Hooks" (ends line 208) and before "Phase-Agent Mapping" (starts line 209). It must follow the existing markdown style: `##` for sections, `###` for subsections, tables with `|` delimiters, code blocks with triple backticks.

- [ ] **Step 1: Insert the chapter heading and Pre-Dispatch Announcement section**

Insert after line 208 (the blank line after the `after_dispatch` interpretation table):

```markdown
## User-Facing Dispatch Announcements

Before and after every subagent dispatch, output a brief announcement so the user
understands what is happening and why. These announcements are the user's only
visibility into orchestration — keep them concise but informative.

### Pre-Dispatch Announcement

Before calling the `task` tool to dispatch a subagent, output:

> **🔄 Dispatching {agent-name}**
> **Phase:** {current_phase}
> **Reason:** {one sentence why this agent is needed}
> **Task:** {brief description of what the agent will do}
```

- [ ] **Step 2: Insert the Post-Dispatch Announcement section**

Immediately after the Pre-Dispatch section, add:

```markdown
### Post-Dispatch Announcement

After receiving the agent result and calling `after-dispatch`:

**On success:**

> **✅ {agent-name} completed**
> **Result:** {key outcome summary}
> **Next:** {what happens next}

**On failure or blocker:**

> **⚠️ {agent-name} encountered issues**
> **Blocker:** {blocker reason}
> **Recommended action:** {what to do next}
```

- [ ] **Step 3: Insert the Agent Task Descriptions Table**

After the Post-Dispatch section, add:

```markdown
### Agent Task Descriptions

Use these descriptions for the **Task:** field in pre-dispatch announcements:

| Agent | Phase | Task Description |
|---|---|---|
| `plan-agent` | `create_change` | Generate implementation plan for the spec change |
| `implement-agent` | `apply_change` | Execute TDD red/green loops for the work package |
| `test-agent` | `apply_change` | Run focused tests and regression verification |
| `review-agent` | `apply_change` | Perform code review and verify-before-complete checks |
| `finish-agent` | `archive_change` | Archive the change and run post-archive hooks |
| `finish-agent` | `post_archive_actions` | Run post-archive cleanup and memory sync hooks |

**Fallback:** For general task agents not in this table, compose the Task description
from the task's `description` parameter.
```

- [ ] **Step 4: Insert the Result Summary Extraction Rules**

After the table section, add:

```markdown
### Post-Dispatch Result Summary Extraction

Extract the **Result:** field for post-dispatch announcements from agent results:

| Scenario | Extract From |
|---|---|
| plan-agent success | `evidence.plan_summary` (use `objective` + `approach`) |
| implement-agent success | `evidence.criteria_satisfied` or `recommended_next_action` |
| test-agent success | `evidence.focused_tests` (pass count) or `evidence.criteria_satisfied` |
| review-agent success | `evidence.review_decision` or `evidence.criteria_satisfied` |
| finish-agent success | `evidence.criteria_satisfied` or `recommended_next_action` |
| Any agent failure/blocker | `blockers[].reason` + `blockers[].message` (first blocker) |
| General agents | `status` + any `evidence` keys present |

**Next:** field maps to `recommended_next_action` from the agent result.
```

- [ ] **Step 5: Insert the Complete Lifecycle Example**

After the extraction rules, add:

```markdown
### Complete Lifecycle Example

A full dispatch cycle for `implement-agent` during `apply_change`:

```
User: "Implement the login feature"

dev-orchestrator:
  1. [Workflow entry: verify-foundations, status, resume]
  2. [before-dispatch: implement-agent]

  > **🔄 Dispatching implement-agent**
  > **Phase:** apply_change
  > **Reason:** Execute the TDD implementation for the approved plan
  > **Task:** Execute TDD red/green loops for the work package

  3. [Dispatch implement-agent via task tool]
  4. [Receive result]
  5. [after-dispatch: implement-agent → dispatch_test_agent]

  > **✅ implement-agent completed**
  > **Result:** All 3 work package tests passing, code implements login flow
  > **Next:** Dispatch test-agent for focused regression verification

  6. [before-dispatch: test-agent]

  > **🔄 Dispatching test-agent**
  > **Phase:** apply_change
  > **Reason:** Verify implementation passes focused tests and no regressions
  > **Task:** Run focused tests and regression verification

  7. [Dispatch test-agent via task tool]
  8. [Receive result]
  9. [after-dispatch: test-agent → dispatch_review_agent]

  > **✅ test-agent completed**
  > **Result:** 12/12 tests passing, no regressions detected
  > **Next:** Dispatch review-agent for code review

  ...and so on through review-agent and phase completion.
```
```

- [ ] **Step 6: Verify insertion integrity**

After all insertions, verify:
- The new chapter is ~80 lines (±10)
- `## Phase-Agent Mapping` still follows immediately after the new chapter
- No duplicate headings were introduced
- All markdown tables render correctly (pipe-delimited, header row, separator row)
- The file still starts with the YAML frontmatter and ends with the `## Raw Logs` section

Run: `wc -l agents/dev-orchestrator.md`
Expected: ~525 lines (444 original + ~80 new)

Run: `grep -n "^## " agents/dev-orchestrator.md`
Expected: "User-Facing Dispatch Announcements" appears between "Dispatch Lifecycle Hooks" and "Phase-Agent Mapping"

- [ ] **Step 7: Commit**

```bash
git add agents/dev-orchestrator.md
git commit -m "feat(agents): add user-facing dispatch announcements to dev-orchestrator"
```

---

## Self-Review Checklist

- [ ] Chapter heading is `## User-Facing Dispatch Announcements`
- [ ] Pre-dispatch format uses blockquote (`>`) with emoji and 4 fields
- [ ] Post-dispatch success format uses ✅ emoji with Result + Next fields
- [ ] Post-dispatch failure format uses ⚠️ emoji with Blocker + Recommended action fields
- [ ] Agent task descriptions table has all 6 rows (plan, implement, test, review, finish×2)
- [ ] Fallback rule for general agents is stated
- [ ] Result extraction table covers all 5 specialized agents + failure + general case
- [ ] Complete lifecycle example shows implement-agent → test-agent handoff
- [ ] Insertion point is between Dispatch Lifecycle Hooks and Phase-Agent Mapping
- [ ] No changes to any other section of the file
- [ ] Existing markdown style is preserved (## headings, | tables, ``` code blocks)
