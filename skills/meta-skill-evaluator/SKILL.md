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
8. Stop after producing the report. Do not edit files, create eval assets, or run eval commands. Do not route to another workflow directly.

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

- `ready`: no critical or high findings, average score at least 4.3, and no dimension below 4.
- `ready with concerns`: no critical or high findings, average score at least 3.7, and no dimension below 3.
- `needs revision`: any high-severity finding, any dimension below 3, average below 3.7, or multiple weak dimensions.
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
