# meta-skill-evaluator Design

## Purpose

Create `meta-skill-evaluator`, a static governance auditor for AI skill definitions. The skill evaluates whether a `SKILL.md` behaves like a bounded, reusable task protocol rather than a broad prompt. It reviews skill quality, safety, maintainability, and testability, then produces a hybrid scorecard and review memo in chat by default.

The evaluator is intentionally decoupled from EvalOps and lifecycle orchestration. It may recommend follow-up work, but it does not create eval assets, run Promptfoo, edit the evaluated skill, release skills, or orchestrate other workflows.

## Context

The repository already has specialized skills for skill creation, lifecycle governance, EvalOps, OpenSpec workflows, and SDLC orchestration. A skill evaluator needs to fit this ecosystem without becoming another orchestrator.

The source research in `docs/manual/plans/good_skill.md` defines a good skill as a bounded protocol with clear triggers, required inputs, workflow, output format, quality gates, side-effect policy, failure handling, collaboration boundaries, context loading policy, and testability.

## Goals

- Evaluate `SKILL.md` files against a consistent quality rubric.
- Produce a stable chat-only report by default.
- Identify trigger ambiguity, responsibility overreach, missing side-effect boundaries, weak workflows, missing completion criteria, and poor testability.
- Surface conflicts with nearby skills and unclear delegation boundaries.
- Provide improvement recommendations without modifying files.
- Provide optional eval case ideas as handoff material only.

## Non-Goals

- Do not edit or rewrite the target skill.
- Do not create durable report files unless explicitly requested.
- Do not create or manage `.ai/evals/` assets.
- Do not run Promptfoo, model evals, or benchmark suites.
- Do not decide lifecycle actions such as pilot, release, distribute, or backport.
- Do not replace ordinary code review.
- Do not orchestrate multi-skill workflows.

## Skill Name

`meta-skill-evaluator`

## Triggering

Use this skill when the user asks to review, evaluate, score, audit, validate, or assess a skill or `SKILL.md`, especially before skill improvement, pilot, release, or distribution.

Do not use this skill when:

- The user asks for ordinary code review.
- The user asks to edit, create, or improve a skill directly; use `skill-creator` or the appropriate implementation workflow.
- The user asks to manage durable eval cases or run Promptfoo; use `sdlc-evalops`.
- The user asks to decide release, pilot, backport, install, or distribute actions; use `meta-skill-lifecycle-governance`.
- The user asks for overall SDLC routing; use `sdlc-orchestrator`.

## Inputs

Required input:

- Target skill path, skill name, or enough context to locate the target `SKILL.md`.

Optional inputs:

- Evaluation purpose, such as pre-release review, trigger audit, safety audit, maintainability review, or testability review.
- Known failure examples or user concerns.
- Nearby skill names that may conflict with the target.

If the target skill is unclear, the evaluator should ask one short clarifying question or inspect likely skill directories. It should not scan the entire repository unless the target cannot otherwise be located.

## Workflow

1. Identify the target skill and review scope.
2. Read the target `SKILL.md`.
3. Inspect nearby files only when needed to understand examples, references, or conflicts.
4. Evaluate the skill against the scorecard dimensions.
5. Identify findings ordered by severity.
6. Analyze boundaries with adjacent skills.
7. Produce the default chat report.
8. Stop. Do not edit files, create eval assets, run eval commands, or route to another workflow directly.

## Scorecard

Use a 1-5 score for each dimension:

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

The report must include one readiness decision:

- `ready`
- `ready with concerns`
- `needs revision`
- `not ready`

Default thresholds:

- `ready`: no critical findings, average score at least 4.3, and no dimension below 4.
- `ready with concerns`: no critical findings, average score at least 3.7, and at most two dimensions below 3.
- `needs revision`: any high-severity finding, average score at least 2.8, or multiple weak dimensions.
- `not ready`: any critical boundary or safety flaw, average below 2.8, or the skill is too broad or untestable.

The evaluator may override thresholds when justified, but it must explain why.

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

The evaluator can recommend follow-up ownership, but must not perform that follow-up itself.

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
- If the user requests changes during evaluation, stop the evaluation and clarify whether they want to switch to skill creation/improvement workflow.

## Skill File Structure

MVP structure:

```text
skills/meta-skill-evaluator/
└── SKILL.md
```

The first version should keep the rubric in `SKILL.md` rather than introducing reference files. If the rubric grows beyond a maintainable length, split detailed scoring guidance into `references/scorecard.md` later.

## Evaluation Plan

After drafting the skill, create realistic test prompts for skill quality review. The first eval set should cover:

1. A broad overreaching skill that tries to own development, testing, roadmap, memory, and evals.
2. A mostly good skill with weak do-not-use conditions and missing failure handling.
3. A skill with unsafe side-effect boundaries that allows editing, deleting, committing, or publishing without confirmation.
4. A near-miss prompt asking for ordinary code review, which should not trigger the evaluator.

Expected behavior:

- The evaluator uses the report format consistently.
- The evaluator does not modify files.
- The evaluator identifies overreach and skill conflicts.
- The evaluator gives 1-5 scores with rationales.
- The evaluator recommends follow-up ownership without invoking other workflows.

## Open Questions

None. The user approved the static governance auditor approach, 1-5 scale, chat-by-default output, report-only side effects, and `meta-skill-evaluator` name.
