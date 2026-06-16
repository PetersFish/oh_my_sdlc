from __future__ import annotations

import json
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR_SKILL = REPO_ROOT / "skills" / "sdlc-orchestrator"


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


class TestOrchestratorSkillFrontmatter:
    """Validate sdlc-orchestrator frontmatter and basic structure."""

    def test_skill_md_exists(self):
        assert (ORCHESTRATOR_SKILL / "SKILL.md").is_file(), \
            "sdlc-orchestrator/SKILL.md must exist"

    def test_skill_md_has_valid_frontmatter(self):
        fm = _read_frontmatter(ORCHESTRATOR_SKILL / "SKILL.md")
        assert fm.get("name") == "sdlc-orchestrator", \
            f"Expected name=sdlc-orchestrator, got {fm.get('name')}"
        assert "description" in fm, "description must exist in frontmatter"
        assert len(fm["description"]) > 50, \
            f"description too short: {len(fm['description'])} chars"

    def test_skill_md_mentions_routing_paths(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8")
        paths = ["superpowers-direct", "spec-driven-propose-flow",
                 "spec-driven-incremental-flow", "roadmap-first",
                 "evalops-gated", "memory-sync"]
        lower = content.lower()
        for path in paths:
            assert path.lower() in lower, f"SKILL.md must mention routing path: {path}"


class TestOrchestratorRouteBinding:
    """Validate route decisions are action-binding in SKILL.md."""

    def test_spec_driven_propose_binds_to_openspec_propose(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "openspec-propose" in content, \
            "SKILL.md must reference openspec-propose for spec-driven-propose-flow"
        assert "action-binding" in content or "must follow" in content or \
               ("next action" in content and "openspec-propose" in content), \
            "Route decision must be binding, not advisory"

    def test_spec_driven_incremental_binds_to_openspec_new_change(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "openspec-new-change" in content, \
            "SKILL.md must reference openspec-new-change for spec-driven-incremental-flow"

    def test_route_decision_output_includes_next_action(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "Next action" in content, \
            "Route Decision Output must include Next action field"


class TestOrchestratorPlanModeHandoff:
    """Validate Plan Mode handoff rules align with selected route."""

    def test_handoff_rules_for_spec_driven_routes(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "plan mode" in content, \
            "SKILL.md must reference Plan Mode handoff behavior"

    def test_direct_execution_only_for_superpowers_direct(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "superpowers-direct" in content.lower(), \
            "SKILL.md must preserve direct execution for superpowers-direct route"


class TestOrchestratorAmbiguousExecution:
    """Validate ambiguous execution requests respect prior route."""

    def test_execute_plan_continues_selected_route(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "execute plan" in content or "continue the selected route" in content or \
               "ambiguous" in content, \
            "SKILL.md must address ambiguous execution requests like 'execute plan'"

    def test_explicit_opt_out_mentioned(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "opt out" in content or "explicit" in content, \
            "SKILL.md must document explicit user opt-out from route governance"


class TestOrchestratorQuestionTool:
    """Validate Question Tool usage rules for execution path choices."""

    def test_question_tool_mentioned_for_choices(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "question" in content, \
            "SKILL.md must mention question tool for execution path choices"

    def test_text_fallback_when_tool_unavailable(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "text" in content or "fallback" in content, \
            "SKILL.md must document text fallback when question tool is unavailable"


class TestOrchestratorEvalOpsGates:
    """Validate EvalOps lifecycle gate enforcement in SKILL.md."""

    def test_evalops_gated_section_has_lifecycle_states(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "cases in inbox" in content, \
            "evalops-gated must reference cases in inbox state"
        assert "cases accepted" in content, \
            "evalops-gated must reference cases accepted state"
        assert "cases golden" in content, \
            "evalops-gated must reference cases golden state"
        assert "triage" in content, \
            "evalops-gated must reference triage gate"
        assert "golden eval" in content, \
            "evalops-gated must reference golden eval gate"

    def test_evalops_gated_mandates_golden_eval_before_completion(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "pytest" in content and "golden eval" in content, \
            "evalops-gated must require both pytest and golden eval before completion"
        assert "completion cannot be claimed" in content or \
               "shall not claim completion" in content, \
            "evalops-gated must forbid completion claim before golden eval pass"

    def test_evalops_gated_blocks_on_golden_eval_failure(self):
        content = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "failure analysis" in content, \
            "evalops-gated must route to failure analysis when golden eval fails"
        assert "fix plan" in content, \
            "evalops-gated must require fix plan after golden eval failure"
        assert "shall not permit direct fix" in content or \
               "not permit direct" in content, \
            "evalops-gated must prohibit direct fix without failure analysis"


class TestOrchestratorEvalOpsAssets:
    """Validate EvalOps coverage and golden cases exist for orchestrator."""

    TARGET_WORKSPACE = REPO_ROOT / ".ai" / "evals" / "targets" / "skill.sdlc-orchestrator"

    def test_coverage_matrix_exists(self):
        coverage = self.TARGET_WORKSPACE / "coverage.yaml"
        assert coverage.is_file(), \
            ".ai/evals/targets/skill.sdlc-orchestrator/coverage.yaml must exist"

    def test_coverage_matrix_is_reviewed(self):
        coverage = self.TARGET_WORKSPACE / "coverage.yaml"
        content = coverage.read_text(encoding="utf-8")
        assert "reviewed_by_user: true" in content, \
            "Coverage matrix must have reviewed_by_user: true"

    def test_golden_case_count(self):
        golden_dir = self.TARGET_WORKSPACE / "cases" / "golden"
        assert golden_dir.is_dir(), \
            ".ai/evals/targets/skill.sdlc-orchestrator/cases/golden/ must exist"
        cases = list(golden_dir.glob("*.yaml"))
        assert len(cases) >= 6, \
            f"Expected at least 6 golden cases, found {len(cases)}"

    def test_golden_cases_have_required_fields(self):
        golden_dir = self.TARGET_WORKSPACE / "cases" / "golden"
        for case_file in golden_dir.glob("*.yaml"):
            case = yaml.safe_load(case_file.read_text(encoding="utf-8"))
            assert "id" in case, f"Missing id in {case_file.name}"
            assert "target" in case, f"Missing target in {case_file.name}"
            assert "status" in case, f"Missing status in {case_file.name}"
            assert case["status"] == "golden", \
                f"Case {case['id']} must have status golden, got {case['status']}"
            assert "expected" in case, f"Missing expected in {case_file.name}"
            assert "input" in case, f"Missing input in {case_file.name}"

    def test_target_index_includes_orchestrator(self):
        index = REPO_ROOT / ".ai" / "evals" / "manifest.yaml"
        assert index.is_file(), ".ai/evals/manifest.yaml must exist"
        targets = yaml.safe_load(index.read_text(encoding="utf-8"))
        target_ids = [t["id"] for t in targets.get("targets", [])]
        assert "skill.sdlc-orchestrator" in target_ids, \
            "manifest.yaml must include skill.sdlc-orchestrator"

    def test_promptfoo_export_exists(self):
        export_dir = self.TARGET_WORKSPACE / "exports" / "promptfoo"
        assert export_dir.is_dir(), \
            ".ai/evals/targets/skill.sdlc-orchestrator/exports/promptfoo/ must exist"
        assert (export_dir / "promptfooconfig.yaml").is_file(), \
            "promptfooconfig.yaml must exist"
        assert (export_dir / "cases.yaml").is_file(), \
            "cases.yaml must exist"


class TestOrchestratorPromptfooExport:
    """Validate Promptfoo export evaluates activated skill behavior."""

    EXPORT_DIR = REPO_ROOT / ".ai" / "evals" / "targets" / "skill.sdlc-orchestrator" / "exports" / "promptfoo"

    def test_promptfoo_config_does_not_have_global_openspec_assertion(self):
        config = yaml.safe_load((self.EXPORT_DIR / "promptfooconfig.yaml").read_text(encoding="utf-8"))
        default_asserts = config.get("defaultTest", {}).get("assert", [])
        assert not any(
            assertion.get("type") == "contains" and assertion.get("value") == "openspec-propose"
            for assertion in default_asserts
        ), "Global openspec-propose assertion breaks superpowers-direct positive cases"

    def test_promptfoo_prompt_injects_current_skill(self):
        config_text = (self.EXPORT_DIR / "promptfooconfig.yaml").read_text(encoding="utf-8")
        prompt_path = self.EXPORT_DIR / "prompt.md"
        assert "prompt.md" in config_text, "Promptfoo config must use a skill-injected prompt file"
        assert prompt_path.is_file(), "Promptfoo export must include prompt.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "sdlc-orchestrator" in prompt
        assert "Route decisions are action-binding" in prompt
        assert "{{input}}" in prompt

    def test_promptfoo_cases_do_not_depend_on_unconfigured_llm_rubric_grader(self):
        """Verify any llm-rubric assertions have configured rubric text."""
        cases = yaml.safe_load((self.EXPORT_DIR / "cases.yaml").read_text(encoding="utf-8"))
        for case in cases:
            for assertion in case.get("assert", []):
                if assertion.get("type") == "llm-rubric":
                    assert assertion.get("value", "").strip(), \
                        "llm-rubric assertions must have configured rubric text"


class TestOrchestratorDistributedCopies:
    """Validate distributed orchestrator copies match canonical."""

    def test_opencode_copy_matches_canonical(self):
        canonical = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8")
        opencode = (REPO_ROOT / ".opencode" / "skills" / "sdlc-orchestrator" / "SKILL.md")
        if opencode.is_file():
            assert opencode.read_text(encoding="utf-8") == canonical, \
                ".opencode orchestrator copy must match canonical"

    def test_claude_copy_matches_canonical(self):
        canonical = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8")
        claude = (REPO_ROOT / ".claude" / "skills" / "sdlc-orchestrator" / "SKILL.md")
        if claude.is_file():
            assert claude.read_text(encoding="utf-8") == canonical, \
                ".claude orchestrator copy must match canonical"

    def test_cursor_copy_matches_canonical(self):
        canonical = (ORCHESTRATOR_SKILL / "SKILL.md").read_text(encoding="utf-8")
        cursor = (REPO_ROOT / ".cursor" / "skills" / "sdlc-orchestrator" / "SKILL.md")
        if cursor.is_file():
            assert cursor.read_text(encoding="utf-8") == canonical, \
                ".cursor orchestrator copy must match canonical"
