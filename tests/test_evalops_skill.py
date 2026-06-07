from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALOPS_SKILL = REPO_ROOT / "skills" / "meta-skill-evalops"


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    raw = text[3:end].strip()
    result = {}
    for line in raw.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


class TestEvalopsSkillFrontmatter:
    """Validate meta-skill-evalops frontmatter and basic structure."""

    def test_skill_md_exists(self):
        assert (EVALOPS_SKILL / "SKILL.md").is_file(), \
            "meta-skill-evalops/SKILL.md must exist"

    def test_skill_md_has_valid_frontmatter(self):
        fm = _read_frontmatter(EVALOPS_SKILL / "SKILL.md")
        assert fm.get("name") == "meta-skill-evalops", \
            f"Expected name=meta-skill-evalops, got {fm.get('name')}"
        assert "description" in fm, "description must exist in frontmatter"
        assert len(fm["description"]) > 50, \
            f"description too short: {len(fm['description'])} chars"
        desc = fm["description"].lower()
        assert "eval" in desc, "description must reference eval"
        assert "skill" in desc or "agent" in desc or "target" in desc, \
            "description must reference eval targets"

    def test_skill_md_has_compatibility(self):
        fm = _read_frontmatter(EVALOPS_SKILL / "SKILL.md")
        assert "compatibility" in fm, "compatibility must exist in frontmatter"

    def test_skill_md_mentions_all_seven_commands(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        commands = ["init", "define-coverage", "capture", "generate-cases",
                     "triage", "promote", "run"]
        lower = content.lower()
        for cmd in commands:
            assert cmd.lower() in lower, f"SKILL.md must mention command: {cmd}"

    def test_skill_md_mentions_three_workflows(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        workflows = ["create-eval-suite", "capture-regression", "run-regression"]
        lower = content.lower()
        for wf in workflows:
            assert wf.lower() in lower, f"SKILL.md must mention workflow: {wf}"

    def test_skill_md_mentions_target_id_format(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "target-type" in content.lower(), \
            "SKILL.md must define target-id format"
        assert "skill.research-general" in content.lower(), \
            "SKILL.md must include a target-id example"

    def test_skill_md_defines_dir_structure(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "evals/" in content, "SKILL.md must reference evals/ directory"
        assert "coverage/" in content, "SKILL.md must reference coverage/ directory"
        assert "inbox" in content.lower(), "SKILL.md must reference inbox"
        assert "golden" in content.lower(), "SKILL.md must reference golden"

    def test_skill_md_has_promptfoo_mapping(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "promptfoo" in lower, "SKILL.md must reference Promptfoo"
        assert "promptfooconfig.yaml" in lower, \
            "SKILL.md must reference promptfooconfig.yaml"
        assert "contains" in lower, "SKILL.md must reference contains assertion"
        assert "llm-rubric" in lower, "SKILL.md must reference llm-rubric"


class TestEvalopsSkillHardRules:
    """Validate hard rules are present and enforced."""

    def test_hard_rules_section_exists(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "## Hard Rules" in content, "SKILL.md must have Hard Rules section"

    def test_coverage_is_planning_layer(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "coverage matrix is the planning layer" in lower, \
            "Hard rule: coverage is planning layer"

    def test_ai_cases_inbox_first(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "ai-generated cases" in lower, \
            "Hard rule: AI-generated cases must be mentioned"
        assert "inbox" in lower, "Hard rule: inbox must be mentioned"

    def test_golden_requires_human_approval(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "human confirmation" in lower or "human approval" in lower, \
            "Hard rule: golden requires human approval"

    def test_coverage_review_before_generation(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "reviewed_by_user" in lower, \
            "Hard rule: must check reviewed_by_user before generate"
        assert "before" in lower, "Hard rule: gate must be before generation"

    def test_promptfoo_derived_not_source(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "derived" in lower, "Hard rule: exports are derived artifacts"

    def test_no_auto_fix_on_failure(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "not" in lower and "auto" in lower and "fix" in lower, \
            "Hard rule: no automatic fix on eval failure"

    def test_pre_implementation_eval_asset_gate(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "## Pre-Implementation Eval Asset Gate" in content, \
            "SKILL.md must have Pre-Implementation Eval Asset Gate section"
        lower = content.lower()
        assert "required before implementation" in lower, \
            "Pre-implementation gate must list required items"
        assert "reviewed_by_user" in lower, \
            "Pre-implementation gate must require reviewed coverage"
        assert "golden" in lower, \
            "Pre-implementation gate must reference golden cases"


class TestEvalopsSkillTemplates:
    """Validate bundled templates exist and are well-formed."""

    def test_coverage_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "default-coverage.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_case_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "default-case.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_eval_policy_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "eval-policy.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_target_index_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "target-index.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_promptfoo_config_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "promptfooconfig.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_promptfoo_cases_template_exists(self):
        path = EVALOPS_SKILL / "templates" / "promptfoo-cases.yaml"
        assert path.is_file(), f"Missing template: {path}"

    def test_coverage_template_has_required_sections(self):
        content = (EVALOPS_SKILL / "templates" / "default-coverage.yaml") \
            .read_text(encoding="utf-8")
        assert "target:" in content, "Coverage template must have target section"
        assert "coverage:" in content, "Coverage template must have coverage section"
        assert "review:" in content, "Coverage template must have review section"

    def test_case_template_has_required_sections(self):
        content = (EVALOPS_SKILL / "templates" / "default-case.yaml") \
            .read_text(encoding="utf-8")
        assert "target:" in content, "Case template must have target section"
        assert "status:" in content, "Case template must have status field"
        assert "expected:" in content, "Case template must have expected section"
        assert "evaluators:" in content, "Case template must have evaluators section"

    def test_policy_template_golden_requires_approval(self):
        content = (EVALOPS_SKILL / "templates" / "eval-policy.yaml") \
            .read_text(encoding="utf-8")
        assert "golden_requires_human_approval: true" in content, \
            "Policy must enforce golden requires human approval"

    def test_policy_template_ai_cases_default_inbox(self):
        content = (EVALOPS_SKILL / "templates" / "eval-policy.yaml") \
            .read_text(encoding="utf-8")
        assert "ai_generated_cases_default_status: inbox" in content, \
            "Policy must default AI cases to inbox"


class TestEvalopsSkillEvals:
    """Validate evals/evals.json covers routing scenarios."""

    def test_evals_json_exists(self):
        path = EVALOPS_SKILL / "evals" / "evals.json"
        assert path.is_file(), f"Missing: {path}"

    def test_evals_json_has_three_scenarios(self):
        data = json.loads(
            (EVALOPS_SKILL / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        assert data["skill_name"] == "meta-skill-evalops"
        assert len(data["evals"]) >= 3, \
            f"Expected at least 3 eval scenarios, got {len(data['evals'])}"

    def test_evals_cover_all_three_workflows(self):
        data = json.loads(
            (EVALOPS_SKILL / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        outputs = " ".join(e["expected_output"] for e in data["evals"]).lower()
        assert "create-eval-suite" in outputs, \
            "Evals must cover create-eval-suite workflow"
        assert "capture" in outputs, \
            "Evals must cover capture-regression workflow"
        assert "run" in outputs, \
            "Evals must cover run-regression workflow"


class TestEvalopsSkillWorkflowIntegration:
    """Validate workflow integration mentions exist."""

    def test_mentions_openspec_integration(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "openspec" in content.lower(), \
            "SKILL.md must mention OpenSpec integration"

    def test_mentions_skill_lifecycle_integration(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "evaluate-in-repo" in lower, \
            "SKILL.md must mention EVALUATE-IN-REPO"

    def test_mentions_brainstorming_integration(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "brainstorming" in lower, \
            "SKILL.md must mention brainstorming integration"

    def test_openspec_integration_distinguishes_new_and_existing_targets(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "new" in lower and "target" in lower, \
            "OpenSpec section must distinguish new targets"
        assert "existing" in lower, \
            "OpenSpec section must distinguish existing targets"
        assert "define-coverage" in lower, \
            "New target flow must include define-coverage before implementation"
        assert "inspect" in lower or "update coverage" in lower, \
            "Existing target flow must include inspecting/updating coverage"

    def test_lifecycle_governance_is_not_listed_as_superpowers_core(self):
        content = (EVALOPS_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "## skill lifecycle governance" not in content.lower(), \
            "SKILL.md must not use misleading section title"
        assert "with skill lifecycle governance" in lower, \
            "SKILL.md must have separate Skill Lifecycle Governance section"
        assert "repository skill lifecycle governance capability" in lower or \
               "not a superpowers core workflow" in lower, \
            "Must clarify that skill lifecycle governance is not Superpowers core"
