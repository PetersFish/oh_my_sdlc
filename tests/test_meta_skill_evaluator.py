from __future__ import annotations

from pathlib import Path

from support.frontmatter import read_frontmatter


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "meta-skill-evaluator"
SKILL_MD = SKILL_DIR / "SKILL.md"


def _frontmatter_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return []
    return lines[1:end]


class TestMetaSkillEvaluatorFrontmatter:
    def test_skill_md_exists(self):
        assert SKILL_MD.is_file(), "skills/meta-skill-evaluator/SKILL.md must exist"

    def test_frontmatter_name_and_description(self):
        fm = read_frontmatter(SKILL_MD)
        assert fm.get("name") == "meta-skill-evaluator"
        desc = fm.get("description", "")
        assert len(desc) > 80
        assert "skill" in desc.lower()
        assert "review" in desc.lower() or "evaluate" in desc.lower()
        assert "do not" in desc.lower()

    def test_description_uses_folded_block_scalar(self):
        frontmatter = "\n".join(_frontmatter_lines(SKILL_MD))
        assert "description: >-" in frontmatter

    def test_frontmatter_is_valid_yaml(self):
        fm = read_frontmatter(SKILL_MD)
        assert fm["name"] == "meta-skill-evaluator"
        assert isinstance(fm["description"], str)


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
        assert "dev-orchestrator" in lower

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

    def test_readiness_thresholds_do_not_over_approve_weak_skills(self):
        content = SKILL_MD.read_text(encoding="utf-8").lower()
        assert "`ready`: no critical or high findings" in content
        assert "`ready with concerns`: no critical or high findings" in content
        assert "no dimension below 3" in content
        assert "`needs revision`: any high-severity finding, any dimension below 3" in content
        assert "average below 3.7" in content

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
            "must not install, publish, distribute, commit, or push anything",
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
