# meta-skill-evaluator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `meta-skill-evaluator`, a report-only static governance auditor for `SKILL.md` quality.

**Architecture:** Create one canonical skill directory with a single `SKILL.md` containing trigger rules, workflow, scorecard, output format, side-effect boundaries, and delegation boundaries. Add lightweight pytest coverage that validates the skill file exists, uses safe trigger language, includes the required rubric dimensions, preserves report-only behavior, and remains decoupled from EvalOps execution.

**Tech Stack:** Markdown skill instructions, YAML frontmatter, Python pytest file-content tests.

---

## File Structure

- Create: `skills/meta-skill-evaluator/SKILL.md`
  - Canonical skill source.
  - Contains frontmatter, trigger boundaries, workflow, scorecard, report format, side-effect policy, delegation boundary, and failure handling.
- Create: `tests/test_meta_skill_evaluator.py`
  - Verifies the skill file exists and preserves the approved design constraints.
- Do not modify: `.ai/evals/`
  - The skill is intentionally decoupled from durable eval assets.
- Do not modify distributed copies under `.opencode/`, `.claude/`, `.cursor/`, or global config.
  - Distribution is a separate lifecycle action.

## Task 1: Add Failing Structure Tests

**Files:**
- Create: `tests/test_meta_skill_evaluator.py`

- [x] **Step 1: Create the pytest file**

Create `tests/test_meta_skill_evaluator.py` with this content:

```python
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "meta-skill-evaluator"
SKILL_MD = SKILL_DIR / "SKILL.md"


def _read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    raw = text[3:end].strip()
    result: dict[str, str] = {}
    current_key: str | None = None
    current_value: list[str] = []
    for line in raw.split("\n"):
        if line.startswith(" ") and current_key:
            current_value.append(line.strip())
            continue
        if current_key:
            result[current_key] = " ".join(current_value).strip()
        key, _, value = line.partition(":")
        current_key = key.strip()
        current_value = [value.strip()]
    if current_key:
        result[current_key] = " ".join(current_value).strip()
    return result


class TestMetaSkillEvaluatorFrontmatter:
    def test_skill_md_exists(self):
        assert SKILL_MD.is_file(), "skills/meta-skill-evaluator/SKILL.md must exist"

    def test_frontmatter_name_and_description(self):
        fm = _read_frontmatter(SKILL_MD)
        assert fm.get("name") == "meta-skill-evaluator"
        desc = fm.get("description", "")
        assert len(desc) > 80
        assert "skill" in desc.lower()
        assert "review" in desc.lower() or "evaluate" in desc.lower()
        assert "do not" in desc.lower()

    def test_description_uses_folded_block_scalar(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        assert "description: >-" in frontmatter


class TestMetaSkillEvaluatorContract:
    def test_declares_static_report_only_purpose(self):
        content = SKILL_MD.read_text(encoding="utf-8").lower()
        assert "static governance auditor" in content
        assert "report-only" in content
        assert "does not create or run evals" in content

    def test_declares_use_and_do_not_use_boundaries(self):
        content = SKILL_MD.read_text(encoding="utf-8")
        assert "## When to Use" in content
        assert "## When Not to Use" in content
        lower = content.lower()
        assert "ordinary code review" in lower
        assert "sdlc-evalops" in lower
        assert "skill-creator" in lower
        assert "meta-skill-lifecycle-governance" in lower
        assert "sdlc-orchestrator" in lower

    def test_includes_all_scorecard_dimensions(self):
        content = SKILL_MD.read_text(encoding="utf-8").lower()
        dimensions = [
            "responsibility boundary",
            "trigger clarity",
            "required inputs",
            "output stability",
            "workflow operability",
            "completion criteria",
            "side-effect policy",
            "failure handling",
            "collaboration boundaries",
            "context loading policy",
            "testability",
            "maintainability",
        ]
        for dimension in dimensions:
            assert dimension in content, f"missing scorecard dimension: {dimension}"

    def test_includes_readiness_decisions(self):
        content = SKILL_MD.read_text(encoding="utf-8").lower()
        for decision in ["ready", "ready with concerns", "needs revision", "not ready"]:
            assert decision in content
        assert "4.3" in content
        assert "3.7" in content
        assert "2.8" in content

    def test_includes_required_report_sections(self):
        content = SKILL_MD.read_text(encoding="utf-8")
        sections = [
            "# Skill Evaluation: <skill-name>",
            "## Readiness",
            "## Scorecard",
            "## Findings",
            "## Boundary Analysis",
            "## Review Memo",
            "## Suggested Improvements",
            "## Eval Case Ideas",
        ]
        for section in sections:
            assert section in content, f"missing report section: {section}"

    def test_side_effect_policy_forbids_mutation_and_eval_execution(self):
        content = SKILL_MD.read_text(encoding="utf-8").lower()
        forbidden_actions = [
            "must not edit",
            "must not create or modify `.ai/evals/`",
            "must not run promptfoo",
            "must not install",
            "must not publish",
            "must not commit",
            "must not push",
        ]
        for action in forbidden_actions:
            assert action in content, f"missing side-effect boundary: {action}"

    def test_workflow_stops_after_report(self):
        content = SKILL_MD.read_text(encoding="utf-8").lower()
        assert "stop after producing the report" in content
        assert "do not route to another workflow directly" in content

    def test_eval_case_ideas_are_handoff_only(self):
        content = SKILL_MD.read_text(encoding="utf-8").lower()
        assert "handoff ideas only" in content
        assert "this skill does not create or run evals" in content
```

- [x] **Step 2: Run the focused test and confirm it fails**

Run:

```bash
pytest tests/test_meta_skill_evaluator.py -q
```

Expected result: fail because `skills/meta-skill-evaluator/SKILL.md` does not exist yet.

## Task 2: Add the Skill File

**Files:**
- Create: `skills/meta-skill-evaluator/SKILL.md`

- [x] **Step 1: Create the skill directory and file**

Create `skills/meta-skill-evaluator/SKILL.md` with this content:

```markdown
---
name: meta-skill-evaluator
description: >-
  Use when the user asks to review, evaluate, score, audit, validate, or assess
  an AI skill, SKILL.md, or skill design for quality, safety, trigger clarity,
  side-effect boundaries, maintainability, and testability. This is a static
  report-only governance auditor for skills. Do not use for ordinary code
  review, direct skill creation or editing, Promptfoo/eval execution,
  .ai/evals asset management, lifecycle release/distribution decisions, or
  overall SDLC routing.
---

# Meta Skill Evaluator

Evaluate AI skills as reusable task protocols. A good skill has a clear responsibility boundary, reliable triggers, required inputs, an executable workflow, stable output shape, quality gates, side-effect boundaries, failure handling, collaboration boundaries, context loading discipline, and testability.

This skill is a static governance auditor. It is report-only by default and does not create or run evals.

## When to Use

- The user asks to review, evaluate, score, audit, validate, or assess a skill or `SKILL.md`.
- The user wants to know whether a skill is ready for improvement, pilot, release, or distribution.
- The user wants to find trigger ambiguity, responsibility overreach, unsafe side effects, vague workflows, or missing completion criteria in a skill.
- The user wants sample eval case ideas for a skill review, as handoff ideas only.

## When Not to Use

- The user asks for ordinary code review.
- The user asks to create, edit, or improve a skill directly; use `skill-creator` or the selected implementation workflow.
- The user asks to manage durable eval cases, `.ai/evals/`, or Promptfoo runs; use `sdlc-evalops`.
- The user asks to decide pilot, release, backport, install, publish, or distribute actions; use `meta-skill-lifecycle-governance`.
- The user asks for overall SDLC task routing; use `sdlc-orchestrator`.

## Required Inputs

- Target skill path, skill name, or enough context to locate the target `SKILL.md`.

Optional inputs:

- Evaluation purpose, such as trigger audit, safety audit, maintainability review, pre-release review, or testability review.
- Known failure examples or user concerns.
- Nearby skills that may conflict with the target skill.

If the target skill is unclear, ask one short clarifying question or inspect likely skill directories. Do not scan the whole repository unless the target cannot otherwise be located.

## Workflow

1. Identify the target skill and review scope.
2. Read the target `SKILL.md`.
3. Inspect referenced or nearby files only when needed to understand examples, dependencies, or conflicts.
4. Evaluate the skill against the scorecard dimensions.
5. Identify findings ordered by severity.
6. Analyze boundaries with adjacent skills.
7. Produce the default chat report.
8. Stop after producing the report. Do not edit files, create eval assets, run eval commands, or route to another workflow directly.

## Scorecard

Use a 1-5 score for each dimension.

| Score | Meaning |
|---:|---|
| 1 | Missing or actively harmful |
| 2 | Present but vague, unsafe, or hard to execute |
| 3 | Usable but incomplete or inconsistent |
| 4 | Clear and operational with minor gaps |
| 5 | Strong, bounded, testable, and easy to maintain |

Dimensions:

- Responsibility boundary
- Trigger clarity
- Required inputs
- Output stability
- Workflow operability
- Completion criteria
- Side-effect policy
- Failure handling
- Collaboration boundaries
- Context loading policy
- Testability
- Maintainability

## Readiness Decision

Include one readiness decision:

- `ready`
- `ready with concerns`
- `needs revision`
- `not ready`

Default thresholds:

- `ready`: no critical findings, average score at least 4.3, and no dimension below 4.
- `ready with concerns`: no critical findings, average score at least 3.7, and at most two dimensions below 3.
- `needs revision`: any high-severity finding, average score at least 2.8, or multiple weak dimensions.
- `not ready`: any critical boundary or safety flaw, average below 2.8, or the skill is too broad or untestable.

You may override thresholds when the evidence justifies it, but explain the override.

## Report Format

Use this default chat report structure:

```md
# Skill Evaluation: <skill-name>

## Readiness
<ready | ready with concerns | needs revision | not ready>

## Scorecard
| Dimension | Score | Rationale |
|---|---:|---|

## Findings
| Severity | Area | Finding | Recommendation |
|---|---|---|---|

## Boundary Analysis
<conflicts with nearby skills, overreach, missing do-not-use cases>

## Review Memo
<short engineering judgment>

## Suggested Improvements
<prioritized recommendations, no patch>

## Eval Case Ideas
<optional handoff ideas only; this skill does not create or run evals>
```

If no serious issues are found, say so explicitly and list residual risks or testing gaps.

## Side-Effect Policy

Default behavior is report-only:

- May read the target `SKILL.md`.
- May read nearby referenced files only when needed.
- Must not edit the target skill.
- Must not create report files unless explicitly requested.
- Must not create or modify `.ai/evals/` assets.
- Must not run Promptfoo or model eval commands.
- Must not install, publish, distribute, commit, or push anything.

If the user asks for a saved report, write only the requested report file and preserve the chat summary.

## Delegation Boundary

You can recommend follow-up ownership, but must not perform that follow-up yourself.

- `sdlc-orchestrator` decides whether findings should route into OpenSpec, EvalOps, lifecycle governance, or implementation.
- `sdlc-evalops` owns durable semantic eval cases and eval runs.
- `meta-skill-lifecycle-governance` owns pilot, release, backport, install, and distribution decisions.
- `skill-creator` owns drafting and iterative improvement of skills.
- `test-driven-development` owns deterministic implementation tests when skill changes require code-level validation.

## Failure Handling

- If the target skill cannot be located, ask for the path or name.
- If `SKILL.md` is malformed or unreadable, report the parse/read issue as a finding and continue with available evidence.
- If the skill depends on missing referenced files, score maintainability and workflow operability accordingly.
- If evidence is insufficient for a dimension, mark it as uncertain in the rationale rather than inventing conclusions.
- If the user requests changes during evaluation, stop and clarify whether they want to switch to skill creation or improvement workflow.
```

- [x] **Step 2: Run the focused tests and confirm they pass**

Run:

```bash
pytest tests/test_meta_skill_evaluator.py -q
```

Expected result: all tests in `tests/test_meta_skill_evaluator.py` pass.

## Task 3: Run Targeted Verification

**Files:**
- Verify: `skills/meta-skill-evaluator/SKILL.md`
- Verify: `tests/test_meta_skill_evaluator.py`

- [x] **Step 1: Run the new focused test file**

Run:

```bash
pytest tests/test_meta_skill_evaluator.py -q
```

Expected result: pass.

- [x] **Step 2: Run nearby skill structure tests**

Run:

```bash
pytest tests/test_meta_skill_evaluator.py tests/test_evalops_skill.py tests/test_sdlc_orchestrator.py -q
```

Expected result: pass, or any pre-existing failure is reported with file and reason.

- [x] **Step 3: Inspect the final diff**

Run:

```bash
git diff -- docs/superpowers/specs/2026-06-15-meta-skill-evaluator-design.md docs/superpowers/plans/2026-06-15-meta-skill-evaluator.md skills/meta-skill-evaluator/SKILL.md tests/test_meta_skill_evaluator.py
```

Expected result: diff only contains the approved spec, implementation plan, new skill, and new test file.

## Self-Review

Spec coverage:

- Static governance auditor: Task 2 implements this in Purpose and Workflow.
- Chat-only report by default: Task 2 implements report format and report-only side-effect policy.
- 1-5 scorecard: Task 2 implements score meanings and dimensions; Task 1 tests them.
- Readiness decision: Task 2 implements thresholds; Task 1 tests decisions and threshold literals.
- Decoupled from EvalOps: Task 2 forbids `.ai/evals/` mutation and Promptfoo runs; Task 1 tests this.
- No direct orchestration: Task 2 requires stopping after report and only recommending ownership; Task 1 tests this.
- Frontmatter folded description: Task 2 uses `description: >-`; Task 1 tests this.

Placeholder scan:

- No placeholder-only implementation steps remain.
- Angle-bracket placeholders appear only inside the required report template shown to the skill user.

Type consistency:

- Test paths, skill paths, and frontmatter names consistently use `meta-skill-evaluator`.
- The tests check strings that appear verbatim in the planned `SKILL.md`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-15-meta-skill-evaluator.md`.

Two execution options:

1. Subagent-Driven (recommended) - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints.

No git commit is included because commits require explicit user approval in this environment.
