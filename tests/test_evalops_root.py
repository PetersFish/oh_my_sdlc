"""Tests for .ai/evals/ root structure, target workspaces, and export-promptfoo.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALS_ROOT = REPO_ROOT / ".ai" / "evals"
TARGET_WS = EVALS_ROOT / "targets" / "skill.sdlc-orchestrator"
EVALOPS_TARGET_WS = EVALS_ROOT / "targets" / "skill.sdlc-evalops"
SKILL_SCRIPTS = REPO_ROOT / "skills" / "sdlc-evalops" / "scripts"
EXPORT_SCRIPT = SKILL_SCRIPTS / "export-promptfoo.py"
RUNNER_SCRIPT = SKILL_SCRIPTS / "run-promptfoo-eval.py"
MATRIX_RUNNER_SCRIPT = SKILL_SCRIPTS / "run-eval-matrix.py"


class TestEvalsRoot:
    """Validate .ai/evals/ root layout and global manifest."""

    def test_evals_root_exists(self):
        assert EVALS_ROOT.is_dir(), ".ai/evals/ must exist"

    def test_platform_directories_exist(self):
        """Only assert directories that current EvalOps scripts consume."""
        manifest = yaml.safe_load(
            (EVALS_ROOT / "manifest.yaml").read_text(encoding="utf-8")
        )
        declared = manifest.get("platform_directories", {})
        for name in list(declared.keys()) + ["targets"]:
            path = EVALS_ROOT / name
            assert path.is_dir(), f".ai/evals/{name}/ must exist"

    def test_runners_dir_does_not_exist(self):
        assert not (EVALS_ROOT / "runners").is_dir(), \
            ".ai/evals/runners/ must not exist because no custom provider is required"

    def test_global_manifest_exists(self):
        assert (EVALS_ROOT / "manifest.yaml").is_file(), \
            ".ai/evals/manifest.yaml must exist"

    def test_global_manifest_has_required_fields(self):
        manifest = yaml.safe_load(
            (EVALS_ROOT / "manifest.yaml").read_text(encoding="utf-8")
        )
        required = [
            "schema_version", "targets", "default_export_policy",
            "default_assertion_policy", "report_policy",
            "platform_directories", "model_matrix_path",
        ]
        for field in required:
            assert field in manifest, \
                f"Global manifest missing required field: {field}"

    def test_global_manifest_registers_orchestrator(self):
        manifest = yaml.safe_load(
            (EVALS_ROOT / "manifest.yaml").read_text(encoding="utf-8")
        )
        target_ids = [t["id"] for t in manifest.get("targets", [])]
        assert "skill.sdlc-orchestrator" in target_ids, \
            "Global manifest must register skill.sdlc-orchestrator"

    def test_model_matrix_exists(self):
        assert (EVALS_ROOT / "model-matrix.yaml").is_file(), \
            ".ai/evals/model-matrix.yaml must exist"

    def test_model_matrix_has_required_fields(self):
        mm = yaml.safe_load(
            (EVALS_ROOT / "model-matrix.yaml").read_text(encoding="utf-8")
        )
        for field in ["schema_version", "models", "environments",
                       "target_selection", "run_policy"]:
            assert field in mm, \
                f"model-matrix.yaml missing required field: {field}"


class TestTargetWorkspace:
    """Validate skill.sdlc-orchestrator target workspace."""

    def test_target_workspace_exists(self):
        assert TARGET_WS.is_dir(), \
            ".ai/evals/targets/skill.sdlc-orchestrator/ must exist"

    def test_target_manifest_exists(self):
        assert (TARGET_WS / "manifest.yaml").is_file(), \
            "Target manifest.yaml must exist"

    def test_target_manifest_has_required_fields(self):
        manifest = yaml.safe_load(
            (TARGET_WS / "manifest.yaml").read_text(encoding="utf-8")
        )
        required = [
            "target_id", "target_type", "source_paths",
            "canonical_case_directories", "coverage_file",
            "promptfoo_export_outputs", "report_directory",
            "assertion_policy", "export_freshness_inputs",
        ]
        for field in required:
            assert field in manifest, \
                f"Target manifest missing required field: {field}"

    def test_target_manifest_has_valid_source_paths(self):
        manifest = yaml.safe_load(
            (TARGET_WS / "manifest.yaml").read_text(encoding="utf-8")
        )
        for sp in manifest.get("source_paths", []):
            assert (REPO_ROOT / sp).is_file(), \
                f"Source path not found: {sp}"

    def test_workspace_has_required_directories(self):
        required = [
            "cases/inbox", "cases/accepted", "cases/rejected",
            "cases/golden", "exports/promptfoo", "reports",
        ]
        for d in required:
            path = TARGET_WS / d
            assert path.is_dir(), \
                f"Target workspace missing directory: {d}"

    def test_coverage_file_exists(self):
        assert (TARGET_WS / "coverage.yaml").is_file(), \
            "Target workspace must have coverage.yaml"

    def test_golden_cases_exist(self):
        golden = TARGET_WS / "cases" / "golden"
        cases = list(golden.glob("*.yaml"))
        assert len(cases) >= 6, \
            f"Expected at least 6 golden cases, found {len(cases)}"

    def test_promptfoo_exports_exist(self):
        exports = TARGET_WS / "exports" / "promptfoo"
        assert (exports / "promptfooconfig.yaml").is_file()
        assert (exports / "cases.yaml").is_file()
        assert (exports / "prompt.md").is_file()


class TestExportPromptfooScript:
    """Validate skills/sdlc-evalops/scripts/export-promptfoo.py behavior."""

    def test_script_exists(self):
        assert EXPORT_SCRIPT.is_file(), \
            "skills/sdlc-evalops/scripts/export-promptfoo.py must exist"

    def test_export_generates_from_golden_cases(self):
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "skill.sdlc-orchestrator"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, \
            f"Export failed: {result.stderr}"
        assert "Loaded" in result.stderr and "golden cases" in result.stderr, \
            "Export must report loaded golden cases"

    def test_export_check_passes_after_export(self):
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "skill.sdlc-orchestrator", "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, \
            f"Freshness check failed: {result.stderr}"

    def test_prompt_injects_skill_source(self):
        prompt_path = TARGET_WS / "exports" / "promptfoo" / "prompt.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "skill.sdlc-orchestrator" in prompt, \
            "Prompt must reference the target skill name"
        assert "Route decisions are action-binding" in prompt, \
            "Prompt must inject current skill source content"
        assert "{{input}}" in prompt, \
            "Prompt must contain input variable placeholder"

    def test_cases_no_global_assertion_pollution(self):
        config = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "promptfooconfig.yaml")
            .read_text(encoding="utf-8")
        )
        default_asserts = config.get("defaultTest", {}).get("assert", [])
        assert not default_asserts, \
            "Promptfoo config must not contain global defaultTest.assert"

    def test_cases_no_unconfigured_llm_rubric(self):
        cases = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "cases.yaml")
            .read_text(encoding="utf-8")
        )
        for case in cases:
            for assertion in case.get("assert", []):
                if assertion.get("type") == "llm-rubric":
                    assert assertion.get("value", "").strip(), \
                        "llm-rubric assertion must have configured rubric text"

    def test_cases_prefer_deterministic_assertions(self):
        """Verify the export contains deterministic assertion types."""
        cases = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "cases.yaml")
            .read_text(encoding="utf-8")
        )
        deterministic_types = {"contains", "not-contains", "regex", "javascript"}
        for case in cases:
            for assertion in case.get("assert", []):
                assert assertion.get("type") in deterministic_types | {"llm-rubric"}, \
                    f"Unknown assertion type: {assertion.get('type')}"

    def test_provider_uses_openai_chat_provider(self):
        config = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "promptfooconfig.yaml")
            .read_text(encoding="utf-8")
        )
        provider_id = config["providers"][0]["id"]
        assert provider_id.startswith("openai:chat:"), \
            f"Provider id must use openai:chat: prefix, got: {provider_id}"
        assert "deepseek-v4-pro" in provider_id, \
            f"Provider id must reference deepseek-v4-pro, got: {provider_id}"

    def test_provider_has_openai_chat_config(self):
        config = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "promptfooconfig.yaml")
            .read_text(encoding="utf-8")
        )
        provider_config = config["providers"][0]["config"]
        assert provider_config.get("apiBaseUrl") == "https://opencode.ai/zen/go/v1", \
            f"apiBaseUrl mismatch: {provider_config.get('apiBaseUrl')}"
        assert provider_config.get("apiKeyEnvar") == "OPENCODE_GO_API_KEY", \
            f"apiKeyEnvar mismatch: {provider_config.get('apiKeyEnvar')}"
        assert provider_config.get("temperature") == 0
        assert provider_config.get("max_tokens") == 4096

    def test_grader_configured_for_llm_rubric(self):
        config = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "promptfooconfig.yaml")
            .read_text(encoding="utf-8")
        )
        grader = config.get("defaultTest", {}).get("options", {}).get("provider", {})
        assert grader, "defaultTest.options.provider must be configured for llm-rubric grading"
        assert grader.get("id", "").startswith("openai:chat:"), \
            "Grader must use openai:chat: provider"
        assert grader.get("config", {}).get("apiBaseUrl") == "https://opencode.ai/zen/go/v1", \
            "Grader must use opencode-go endpoint"
        assert grader.get("config", {}).get("apiKeyEnvar") == "OPENCODE_GO_API_KEY", \
            "Grader must use OPENCODE_GO_API_KEY"

    def test_provider_config_has_no_api_key_value(self):
        config_content = (TARGET_WS / "exports" / "promptfoo" / "promptfooconfig.yaml") \
            .read_text(encoding="utf-8")
        assert "apiKey:" not in config_content, \
            "Promptfoo config must not contain raw apiKey value"
        assert "apiKeyEnvar" in config_content, \
            "Promptfoo config must reference apiKeyEnvar for credential injection"

    def test_provider_uses_opencode_go_endpoint(self):
        config = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "promptfooconfig.yaml")
            .read_text(encoding="utf-8")
        )
        for p in config.get("providers", []):
            assert p["id"].startswith("openai:chat:"), \
                "Provider must use openai:chat: id for opencode-go"
            assert p["config"].get("apiBaseUrl") == "https://opencode.ai/zen/go/v1", \
                "Provider must use opencode-go endpoint"


    def test_provider_has_accept_encoding_identity(self):
        config = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "promptfooconfig.yaml")
            .read_text(encoding="utf-8")
        )
        provider_config = config["providers"][0]["config"]
        headers = provider_config.get("headers", {})
        assert headers.get("Accept-Encoding") == "identity", \
            "Provider must set Accept-Encoding: identity"

    def test_grader_has_accept_encoding_identity(self):
        config = yaml.safe_load(
            (TARGET_WS / "exports" / "promptfoo" / "promptfooconfig.yaml")
            .read_text(encoding="utf-8")
        )
        grader = config.get("defaultTest", {}).get("options", {}).get("provider", {})
        headers = grader.get("config", {}).get("headers", {})
        assert headers.get("Accept-Encoding") == "identity", \
            "Grader must set Accept-Encoding: identity"

    def test_model_matrix_has_accept_encoding_identity(self):
        mm = yaml.safe_load(
            (EVALS_ROOT / "model-matrix.yaml").read_text(encoding="utf-8")
        )
        for model in mm.get("models", []):
            pf = model.get("promptfoo", {})
            pf_headers = pf.get("config", {}).get("headers", {})
            assert pf_headers.get("Accept-Encoding") == "identity", \
                f"Model {model.get('name')} promptfoo provider must set Accept-Encoding: identity"
            gr = model.get("grader", {})
            if gr:
                gr_headers = gr.get("config", {}).get("headers", {})
                assert gr_headers.get("Accept-Encoding") == "identity", \
                    f"Model {model.get('name')} grader must set Accept-Encoding: identity"

    def test_smoke_config_has_accept_encoding_identity(self):
        smoke = yaml.safe_load(
            (EVALS_ROOT / "smoke" / "promptfooconfig.yaml").read_text(encoding="utf-8")
        )
        for p in smoke.get("providers", []):
            headers = p.get("config", {}).get("headers", {})
            assert headers.get("Accept-Encoding") == "identity", \
                "Smoke test config must set Accept-Encoding: identity"


class TestExportPromptfooCheck:
    """Validate --check freshness detection."""

    def test_check_fails_on_missing_executable_target(self):
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "nonexistent.target", "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0, \
            "Check should fail for nonexistent target"

    def test_check_passes_when_exports_fresh(self):
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "skill.sdlc-orchestrator", "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, \
            f"Freshness check should pass: {result.stderr}"


class TestDistributedSkillCopies:
    """Validate distributed copies match canonical after update."""

    def _canonical(self, skill_name):
        return (REPO_ROOT / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")

    def test_opencode_evalops_copy_matches(self):
        canonical = self._canonical("sdlc-evalops")
        copy = REPO_ROOT / ".opencode" / "skills" / "sdlc-evalops" / "SKILL.md"
        assert copy.read_text(encoding="utf-8") == canonical, \
            ".opencode sdlc-evalops copy must match canonical"

    def test_claude_evalops_copy_matches(self):
        canonical = self._canonical("sdlc-evalops")
        copy = REPO_ROOT / ".claude" / "skills" / "sdlc-evalops" / "SKILL.md"
        assert copy.read_text(encoding="utf-8") == canonical, \
            ".claude sdlc-evalops copy must match canonical"

    def test_cursor_evalops_copy_matches(self):
        canonical = self._canonical("sdlc-evalops")
        copy = REPO_ROOT / ".cursor" / "skills" / "sdlc-evalops" / "SKILL.md"
        assert copy.read_text(encoding="utf-8") == canonical, \
            ".cursor sdlc-evalops copy must match canonical"

    def test_opencode_orchestrator_copy_matches(self):
        canonical = self._canonical("sdlc-orchestrator")
        copy = REPO_ROOT / ".opencode" / "skills" / "sdlc-orchestrator" / "SKILL.md"
        assert copy.read_text(encoding="utf-8") == canonical, \
            ".opencode sdlc-orchestrator copy must match canonical"

    def test_claude_orchestrator_copy_matches(self):
        canonical = self._canonical("sdlc-orchestrator")
        copy = REPO_ROOT / ".claude" / "skills" / "sdlc-orchestrator" / "SKILL.md"
        assert copy.read_text(encoding="utf-8") == canonical, \
            ".claude sdlc-orchestrator copy must match canonical"

    def test_cursor_orchestrator_copy_matches(self):
        canonical = self._canonical("sdlc-orchestrator")
        copy = REPO_ROOT / ".cursor" / "skills" / "sdlc-orchestrator" / "SKILL.md"
        assert copy.read_text(encoding="utf-8") == canonical, \
            ".cursor sdlc-orchestrator copy must match canonical"

    def test_evalops_skill_does_not_mention_fallback_provider(self):
        canonical = self._canonical("sdlc-evalops")
        assert "opencode_go_provider.py" not in canonical, \
            "Canonical SKILL.md must not reference opencode_go_provider.py"
        assert "Python Provider Fallback" not in canonical, \
            "Canonical SKILL.md must not have Python Provider Fallback section"

    def test_opencode_evalops_copy_does_not_mention_fallback(self):
        content = (REPO_ROOT / ".opencode" / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "opencode_go_provider.py" not in content, \
            ".opencode copy must not reference opencode_go_provider.py"

    def test_claude_evalops_copy_does_not_mention_fallback(self):
        content = (REPO_ROOT / ".claude" / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "opencode_go_provider.py" not in content, \
            ".claude copy must not reference opencode_go_provider.py"

    def test_cursor_evalops_copy_does_not_mention_fallback(self):
        content = (REPO_ROOT / ".cursor" / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "opencode_go_provider.py" not in content, \
            ".cursor copy must not reference opencode_go_provider.py"


class TestOrchestratorSkillMentionsTargetWorkspaces:
    """Validate skill files reference new EvalOps structure."""

    def test_evalops_skill_mentions_evals_root(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "targets/" in content, "sdlc-evalops must mention target workspaces"
        assert "export-promptfoo.py" in content, \
            "sdlc-evalops must mention export script"

    def test_evalops_skill_mentions_session_vs_promptfoo(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        lower = content.lower()
        assert "session eval" in lower, \
            "sdlc-evalops must distinguish session eval"
        assert "promptfoo eval" in lower, \
            "sdlc-evalops must distinguish Promptfoo eval"

    def test_evalops_skill_mentions_assertion_policy(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "global assertion pollution" in content.lower(), \
            "sdlc-evalops must prohibit global assertion pollution"
        assert "unconfigured" in content.lower() and "llm-rubric" in content.lower(), \
            "sdlc-evalops must mention unconfigured llm-rubric prohibition"

    def test_evalops_skill_mentions_target_manifest(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "target manifest" in content.lower(), \
            "sdlc-evalops must mention target manifest"

    def test_evalops_skill_mentions_model_matrix(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "model-matrix" in content.lower(), \
            "sdlc-evalops must mention model-matrix.yaml"

    def test_evalops_skill_init_produces_gitignore(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert ".ai/evals/.gitignore" in content, \
            "sdlc-evalops init must produce .ai/evals/.gitignore"
        assert "targets/*/reports/" in content, \
            "sdlc-evalops .gitignore must ignore targets/*/reports/"

    def test_orchestrator_skill_mentions_evalops_target_id(self):
        content = (REPO_ROOT / "skills" / "sdlc-orchestrator" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "target id" in content.lower() or "target-id" in content.lower(), \
            "sdlc-orchestrator must mention EvalOps target id"

    def test_orchestrator_skill_mentions_human_confirmation(self):
        content = (REPO_ROOT / "skills" / "sdlc-orchestrator" / "SKILL.md") \
            .read_text(encoding="utf-8")
        lower = content.lower()
        assert "human confirmation" in lower or "user explicitly confirms" in lower, \
            "sdlc-orchestrator must mention human confirmation boundaries"

    def test_orchestrator_skill_mentions_golden_eval_reporting(self):
        content = (REPO_ROOT / "skills" / "sdlc-orchestrator" / "SKILL.md") \
            .read_text(encoding="utf-8")
        lower = content.lower()
        assert "case counts" in lower or "case count" in lower, \
            "sdlc-orchestrator must mention case counts in reporting"
        assert "export freshness" in lower, \
            "sdlc-orchestrator must mention export freshness in reporting"


class TestEvalRunnerScript:
    """Validate skills/sdlc-evalops/scripts/run-promptfoo-eval.py and report writing contracts."""




    def test_runner_script_exists(self):
        assert RUNNER_SCRIPT.is_file(), \
            "skills/sdlc-evalops/scripts/run-promptfoo-eval.py must exist"

    def test_runner_script_references_reports_dir(self):
        content = RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "reports" in content, \
            "runner script must reference reports directory"
        assert "summary.md" in content, \
            "runner script must write summary.md"
        assert "failures.yaml" in content, \
            "runner script must write failures.yaml"
        assert "promptfoo-output.json" in content, \
            "runner script must reference promptfoo-output.json"

    def test_runner_script_uses_o_flag(self):
        content = RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert '"-o"' in content or "'-o'" in content or "-o" in content, \
            "runner script must pass -o flag to promptfoo eval"

    def test_runner_script_references_export_script(self):
        content = RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "export-promptfoo.py" in content, \
            "runner script must chain export-promptfoo.py"

    def test_runner_script_uses_max_concurrency(self):
        content = RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "--max-concurrency" in content, \
            "runner script must use --max-concurrency"

    def test_evalops_skill_eval_command_includes_o_flag(self):
        skill_paths = [
            REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".opencode" / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".claude" / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".cursor" / "skills" / "sdlc-evalops" / "SKILL.md",
        ]
        for sp in skill_paths:
            if sp.is_file():
                content = sp.read_text(encoding="utf-8")
                assert "-o" in content, \
                    f"{sp.relative_to(REPO_ROOT)} Eval Command must include -o flag"

    def test_evalops_skill_mentions_runner_script(self):
        skill_paths = [
            REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".opencode" / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".claude" / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".cursor" / "skills" / "sdlc-evalops" / "SKILL.md",
        ]
        for sp in skill_paths:
            if sp.is_file():
                content = sp.read_text(encoding="utf-8")
                assert "run-promptfoo-eval.py" in content, \
                    f"{sp.relative_to(REPO_ROOT)} must mention run-promptfoo-eval.py"

    def test_evalops_skill_run_steps_reference_runner(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "run-promptfoo-eval.py" in content, \
            "sdlc-evalops run steps must reference run-promptfoo-eval.py"


class TestEvalMatrixRunner:
    """Validate skills/sdlc-evalops/scripts/run-eval-matrix.py behavior and output contracts."""

    def test_runner_script_exists(self):
        assert MATRIX_RUNNER_SCRIPT.is_file(), \
            "skills/sdlc-evalops/scripts/run-eval-matrix.py must exist"

    def test_matrix_runner_reads_model_matrix(self):
        content = MATRIX_RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "model-matrix.yaml" in content, \
            "matrix runner must read model-matrix.yaml"
        assert "models" in content, \
            "matrix runner must reference models[]"

    def test_matrix_runner_dry_run_generates_plan(self):
        result = subprocess.run(
            [sys.executable, str(MATRIX_RUNNER_SCRIPT),
             "skill.sdlc-orchestrator", "--dry-run"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, \
            f"Matrix dry-run failed: {result.stderr}"
        assert "Dry-run" in result.stderr, \
            "Dry-run must print Dry-run mode indicator"
        assert "skill.sdlc-orchestrator" in result.stderr, \
            "Dry-run must reference the target"

    def test_matrix_runner_dry_run_does_not_mutate_canonical_exports(self):
        export_dir = TARGET_WS / "exports" / "promptfoo"
        config_before = (export_dir / "promptfooconfig.yaml").read_text(encoding="utf-8")
        cases_before = (export_dir / "cases.yaml").read_text(encoding="utf-8")
        prompt_before = (export_dir / "prompt.md").read_text(encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(MATRIX_RUNNER_SCRIPT),
             "skill.sdlc-orchestrator", "--dry-run"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0

        config_after = (export_dir / "promptfooconfig.yaml").read_text(encoding="utf-8")
        cases_after = (export_dir / "cases.yaml").read_text(encoding="utf-8")
        prompt_after = (export_dir / "prompt.md").read_text(encoding="utf-8")

        assert config_before == config_after, \
            "Canonical promptfooconfig.yaml must not be mutated by matrix dry-run"
        assert cases_before == cases_after, \
            "Canonical cases.yaml must not be mutated by matrix dry-run"
        assert prompt_before == prompt_after, \
            "Canonical prompt.md must not be mutated by matrix dry-run"

    def test_matrix_runner_mentions_api_key_env_var_not_raw_key(self):
        content = MATRIX_RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "OPENCODE_GO_API_KEY" in content, \
            "matrix runner must reference OPENCODE_GO_API_KEY"
        assert "apiKey:" not in content, \
            "matrix runner must not hardcode raw apiKey values"
        assert "Canonical exports" in content, \
            "matrix runner must state canonical exports are not mutated"

    def test_matrix_runner_supports_all_flag(self):
        content = MATRIX_RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "--all" in content, \
            "matrix runner must support --all flag"

    def test_matrix_runner_mentions_from_auth(self):
        content = MATRIX_RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "--from-auth" in content, \
            "matrix runner must support --from-auth"

    def test_matrix_runner_handles_fail_fast(self):
        content = MATRIX_RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "fail_fast" in content, \
            "matrix runner must read run_policy.fail_fast"

    def test_matrix_runner_exits_nonzero_on_missing_target(self):
        result = subprocess.run(
            [sys.executable, str(MATRIX_RUNNER_SCRIPT),
             "nonexistent.target", "--dry-run"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0, \
            "matrix runner must exit non-zero for nonexistent target"

    def test_matrix_runner_exits_nonzero_on_missing_args(self):
        result = subprocess.run(
            [sys.executable, str(MATRIX_RUNNER_SCRIPT)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0, \
            "matrix runner must exit non-zero when no target or --all provided"

    def test_evalops_skill_mentions_matrix_runner(self):
        skill_paths = [
            REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".opencode" / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".claude" / "skills" / "sdlc-evalops" / "SKILL.md",
            REPO_ROOT / ".cursor" / "skills" / "sdlc-evalops" / "SKILL.md",
        ]
        for sp in skill_paths:
            if sp.is_file():
                content = sp.read_text(encoding="utf-8")
                assert "run-eval-matrix.py" in content, \
                    f"{sp.relative_to(REPO_ROOT)} must mention run-eval-matrix.py"

    def test_evalops_skill_matrix_section_has_report_layout(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "SKILL.md") \
            .read_text(encoding="utf-8")
        assert "## Matrix Eval" in content, \
            "SKILL.md must have Matrix Eval section"
        assert "matrix-run-id" in content or "<matrix-run-id>" in content, \
            "Matrix section must describe matrix run-id report layout"
        assert "summary.md" in content, \
            "Matrix section must reference aggregate summary.md"
        assert "failures.yaml" in content, \
            "Matrix section must reference failures.yaml"


class TestEvalopsTargetInGlobalManifest:
    """Validate sdlc-evalops is a registered EvalOps target."""

    def test_global_manifest_registers_evalops(self):
        manifest = yaml.safe_load(
            (EVALS_ROOT / "manifest.yaml").read_text(encoding="utf-8")
        )
        target_ids = [t["id"] for t in manifest.get("targets", [])]
        assert "skill.sdlc-evalops" in target_ids, \
            "Global manifest must register skill.sdlc-evalops"

    def test_evalops_target_workspace_exists(self):
        assert EVALOPS_TARGET_WS.is_dir(), \
            ".ai/evals/targets/skill.sdlc-evalops/ must exist"

    def test_evalops_target_manifest_has_source_paths(self):
        manifest = yaml.safe_load(
            (EVALOPS_TARGET_WS / "manifest.yaml").read_text(encoding="utf-8")
        )
        assert "source_paths" in manifest, "Target manifest must have source_paths"
        assert "skills/sdlc-evalops/SKILL.md" in manifest.get("source_paths", []), \
            "sdlc-evalops target must reference its own SKILL.md"


class TestModelMatrixNoStaleDocs:
    """Validate model-matrix.yaml files no longer claim runner is deferred."""

    def test_live_model_matrix_not_deferred(self):
        content = (EVALS_ROOT / "model-matrix.yaml").read_text(encoding="utf-8")
        assert "deferred" not in content.lower(), \
            ".ai/evals/model-matrix.yaml must not claim runner is deferred"

    def test_template_model_matrix_not_deferred(self):
        content = (REPO_ROOT / "skills" / "sdlc-evalops" / "templates" / "model-matrix.yaml") \
            .read_text(encoding="utf-8")
        assert "deferred" not in content.lower(), \
            "model-matrix template must not claim runner is deferred"


class TestExportMatrixParity:
    """Validate export script and matrix runner share assertion type contracts."""

    def test_both_scripts_support_same_assertion_types(self):
        export_content = EXPORT_SCRIPT.read_text(encoding="utf-8")
        matrix_content = MATRIX_RUNNER_SCRIPT.read_text(encoding="utf-8")
        for atype in ["contains", "not-contains", "llm-rubric"]:
            assert atype in export_content, \
                f"export-promptfoo.py must support {atype}"
            assert atype in matrix_content, \
                f"run-eval-matrix.py must support {atype}"

    def test_both_scripts_use_api_key_env_var(self):
        for script in [EXPORT_SCRIPT, MATRIX_RUNNER_SCRIPT]:
            content = script.read_text(encoding="utf-8")
            assert "apiKey:" not in content, \
                f"{script.name} must not hardcode apiKey"

    def test_matrix_runner_states_canonical_exports_not_mutated(self):
        content = MATRIX_RUNNER_SCRIPT.read_text(encoding="utf-8")
        assert "NOT mutated" in content, \
            "matrix runner must state canonical exports are not mutated"
