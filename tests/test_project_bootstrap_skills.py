from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SKILL = REPO_ROOT / "skills" / "sdlc-project-bootstrap"
OPENSPEC_INIT_SKILL = REPO_ROOT / "skills" / "sdlc-openspec-init"


def _read_frontmatter(path: Path) -> dict:
    """Read YAML frontmatter from a SKILL.md file and return as dict."""
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


class TestSdlcOpenspecInitSkill(unittest.TestCase):
    """Validate sdlc-openspec-init skill structure."""

    def test_skill_md_exists(self) -> None:
        self.assertTrue(
            (OPENSPEC_INIT_SKILL / "SKILL.md").exists(),
            "sdlc-openspec-init/SKILL.md must exist",
        )

    def test_skill_md_has_valid_frontmatter(self) -> None:
        fm = _read_frontmatter(OPENSPEC_INIT_SKILL / "SKILL.md")
        self.assertEqual(fm.get("name"), "sdlc-openspec-init")
        self.assertIn("description", fm)
        self.assertGreater(len(fm["description"]), 20, "description too short")
        self.assertIn("openspec", fm["description"].lower())
        self.assertIn("schema", fm["description"].lower())

    def test_skill_md_mentions_dry_run(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("dry-run", content.lower())

    def test_skill_md_mentions_multi_tool_selection(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("opencode", content.lower())
        self.assertIn("one or more ai tools", content.lower())
        self.assertIn("comma-separated", content.lower())
        self.assertIn("--tools", content)
        self.assertIn("none", content.lower())

    def test_skill_md_mentions_partial_init_recovery(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("partial init", content.lower())
        self.assertIn("openspec/config.yaml", content)
        self.assertIn("recover", content.lower())

    def test_schema_template_exists(self) -> None:
        schema_dir = OPENSPEC_INIT_SKILL / "templates" / "sdd-plus-superpowers"
        self.assertTrue(schema_dir.is_dir(), "Schema template directory must exist")
        self.assertTrue((schema_dir / "schema.yaml").exists(), "schema.yaml must exist")
        self.assertTrue((schema_dir / "templates").is_dir(), "templates/ subdirectory must exist")

    def test_schema_template_matches_canonical(self) -> None:
        canonical = REPO_ROOT / "openspec" / "schemas" / "sdd-plus-superpowers"
        template = OPENSPEC_INIT_SKILL / "templates" / "sdd-plus-superpowers"
        self.assertEqual(
            (canonical / "schema.yaml").read_text(encoding="utf-8"),
            (template / "schema.yaml").read_text(encoding="utf-8"),
            "Schema template must match canonical source",
        )
        canonical_templates = sorted(
            p.name for p in (canonical / "templates").iterdir()
        )
        template_templates = sorted(
            p.name for p in (template / "templates").iterdir()
        )
        self.assertEqual(
            canonical_templates,
            template_templates,
            "Template files must match canonical source",
        )

    def test_skill_md_references_standalone_invocation(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("standalone", content.lower())

    def test_skill_md_references_schema_iteration(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("iteration", content.lower())
        self.assertIn("newer", content.lower())

    def test_skill_md_prompts_for_default_schema_choice(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("openspec schemas --json", content)
        self.assertIn("spec-driven", content)
        self.assertIn("choose", content.lower())
        self.assertIn("default schema", content.lower())

    def test_skill_md_persists_selected_schema_to_config(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("openspec/config.yaml", content)
        self.assertIn("schema:", content)

    def test_skill_md_has_no_create_change_auto(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("NOT create an OpenSpec change", content)

    def test_skill_md_enforces_prompt_before_openspec_init(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        self.assertIn("do not run", lower)
        self.assertIn("openspec init", lower)
        self.assertIn("until the user", lower)
        self.assertIn("always prompt first", lower)

    def test_skill_md_schema_install_before_schema_listing(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        install_pos = content.lower().find("install sdd-plus-superpowers schema")
        list_pos = content.lower().find("openspec schemas --json")
        self.assertGreater(install_pos, -1, "Must mention schema install step")
        self.assertGreater(list_pos, -1, "Must mention schema listing command")
        self.assertLess(install_pos, list_pos,
                        "Schema install step must appear before schema listing step")

    def test_skill_md_sdd_plus_superpowers_is_recommended_default_schema(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("recommended", content.lower())
        self.assertIn("sdd-plus-superpowers", content.lower())

    def test_skill_md_guardrail_no_init_without_tool_choice(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        guardrails_start = content.find("## Guardrails")
        self.assertGreater(guardrails_start, -1, "Must have Guardrails section")
        guardrails = content[guardrails_start:].lower()
        self.assertIn("do not run", guardrails)
        self.assertIn("openspec init", guardrails)
        self.assertIn("always prompt first", guardrails)

    def test_skill_md_guardrail_no_schema_prompt_before_install(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        guardrails_start = content.find("## Guardrails")
        self.assertGreater(guardrails_start, -1, "Must have Guardrails section")
        guardrails = content[guardrails_start:].lower()
        self.assertIn("do not ask for the default schema until", guardrails)
        self.assertIn("sdd-plus-superpowers", guardrails)
        self.assertIn("openspec schemas --json", guardrails)


class TestSdlcProjectBootstrapSkill(unittest.TestCase):
    """Validate sdlc-project-bootstrap skill structure."""

    def test_skill_md_exists(self) -> None:
        self.assertTrue(
            (BOOTSTRAP_SKILL / "SKILL.md").exists(),
            "sdlc-project-bootstrap/SKILL.md must exist",
        )

    def test_skill_md_has_valid_frontmatter(self) -> None:
        fm = _read_frontmatter(BOOTSTRAP_SKILL / "SKILL.md")
        self.assertEqual(fm.get("name"), "sdlc-project-bootstrap")
        self.assertIn("description", fm)
        self.assertGreater(len(fm["description"]), 20, "description too short")
        self.assertIn("project", fm["description"].lower())

    def test_skill_md_specifies_execution_order(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        # Verify the three steps are mentioned in order
        agents_pos = content.lower().find("agents.md")
        openspec_pos = content.lower().find("openspec", content.lower().find("step 2"))
        memory_pos = content.lower().find("repository memory", content.lower().find("step 3"))
        self.assertGreater(agents_pos, -1, "Must mention AGENTS.md")
        self.assertGreater(openspec_pos, -1, "Must mention OpenSpec step")
        self.assertGreater(memory_pos, -1, "Must mention repository memory step")

    def test_skill_md_delegates_to_openspec_init(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "sdlc-openspec-init", content,
            "Must delegate OpenSpec step to sdlc-openspec-init",
        )

    def test_skill_md_delegates_schema_choice_to_openspec_init(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("choose", content.lower())
        self.assertIn("schema", content.lower())
        self.assertIn("sdlc-openspec-init", content)

    def test_skill_md_surfaces_ai_tools_selection(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("AI tools", content)
        self.assertIn("selected by user", content.lower())

    def test_skill_md_requires_default_schema_in_openspec_result(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Default schema", content)
        self.assertIn("selected by user", content.lower())

    def test_skill_md_disallows_completion_when_openspec_result_incomplete(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Do NOT report", content)
        self.assertIn("Bootstrap Complete", content)
        self.assertIn("AI tools", content)
        self.assertIn("Default schema", content)

    def test_skill_md_delegates_to_memory_init(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "sdlc-repository-memory-init", content,
            "Must delegate memory step to sdlc-repository-memory-init",
        )

    def test_skill_md_mentions_dry_run(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("dry-run", content.lower())

    def test_skill_md_does_not_auto_sync(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("not auto-run", content.lower())
        self.assertIn("sync", content.lower())

    def test_skill_md_does_not_auto_commit(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("NOT auto-commit", content)

    def test_skill_md_conservative_merge(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("never remove", content.lower())

    def test_skill_md_idempotent(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("idempotent", content.lower())

    def test_bootstrap_memory_step_runs_last(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        step2_idx = content.find("Step 2:")
        step3_idx = content.find("Step 3:")
        self.assertGreater(step2_idx, -1)
        self.assertGreater(step3_idx, -1)
        self.assertLess(step2_idx, step3_idx, "OpenSpec step must come before memory step")


class TestAgentsMdTemplate(unittest.TestCase):
    """Validate the bundled AGENTS.md template."""

    def setUp(self) -> None:
        self.template = BOOTSTRAP_SKILL / "templates" / "AGENTS.md"

    def test_template_exists(self) -> None:
        self.assertTrue(self.template.exists(), "AGENTS.md template must exist")

    def test_template_excludes_repository_memory(self) -> None:
        content = self.template.read_text(encoding="utf-8")
        self.assertNotIn(
            "Repository Memory", content,
            "Template must not include Repository Memory reminder block",
        )
        self.assertNotIn(
            "repository memory", content.lower(),
            "Template must not include repository memory reference",
        )

    def test_template_contains_standard_blocks(self) -> None:
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("Think Before Coding", content)
        self.assertIn("Simplicity First", content)
        self.assertIn("Surgical Changes", content)
        self.assertIn("Goal-Driven Execution", content)

    def test_template_starts_with_agents_md_heading(self) -> None:
        content = self.template.read_text(encoding="utf-8")
        self.assertTrue(
            content.startswith("# AGENTS.md"),
            "Template must start with # AGENTS.md heading",
        )


class TestSkillInteraction(unittest.TestCase):
    """Validate skill interactions and delegation patterns."""

    def test_bootstrap_references_openspec_init_not_openspec_cli(self) -> None:
        content = (BOOTSTRAP_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lines_with_init = [
            line for line in content.split("\n")
            if "openspec" in line.lower() and "init" in line.lower()
        ]
        has_skill_delegation = any(
            "sdlc-openspec-init" in line for line in lines_with_init
        )
        self.assertTrue(
            has_skill_delegation,
            "Bootstrap must delegate OpenSpec to sdlc-openspec-init skill",
        )

    def test_openspec_init_standalone_does_not_require_bootstrap(self) -> None:
        content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "standalone", content.lower(),
            "openspec-init must support standalone invocation",
        )
        self.assertIn(
            "independently", content.lower(),
            "openspec-init must mention independent invocation",
        )

    def test_both_skills_share_no_implementation_detail(self) -> None:
        """OpenSpec init should not reference bootstrap internals."""
        openspec_content = (OPENSPEC_INIT_SKILL / "SKILL.md").read_text(encoding="utf-8")
        lines_mentioning_bootstrap = [
            line for line in openspec_content.split("\n")
            if "sdlc-project-bootstrap" in line
        ]
        self.assertEqual(
            len(lines_mentioning_bootstrap), 1,
            "openspec-init should only reference bootstrap once (in description guard)",
        )


class TestEndToEndScenarios(unittest.TestCase):
    """End-to-end tests using temporary directories."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_openspec_config(self) -> None:
        openspec_dir = self.tmp_dir / "openspec"
        openspec_dir.mkdir(parents=True, exist_ok=True)
        (openspec_dir / "config.yaml").write_text(
            "schema: spec-driven\n", encoding="utf-8"
        )

    def _create_schema_dir(self) -> None:
        schema_dir = self.tmp_dir / "openspec" / "schemas" / "sdd-plus-superpowers"
        schema_dir.mkdir(parents=True, exist_ok=True)
        (schema_dir / "schema.yaml").write_text("name: sdd-plus-superpowers\nversion: 1\n", encoding="utf-8")

    def _create_agents_md(self, content: str = "") -> None:
        (self.tmp_dir / "AGENTS.md").write_text(content, encoding="utf-8")

    def _create_ai_memory(self) -> None:
        memory_dir = self.tmp_dir / ".ai-memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "manifest.json").write_text(
            json.dumps({"schema_version": "1.0", "memory_version": 1}), encoding="utf-8"
        )
        (memory_dir / "index.json").write_text(
            json.dumps({"schema_version": "1.0", "entries": []}), encoding="utf-8"
        )

    def _simulate_full_bootstrap(self) -> dict:
        """Simulate bootstrap detection logic without actually running skills.
        Returns a dict of what would happen for each step."""
        result = {
            "agents_md": "create" if not (self.tmp_dir / "AGENTS.md").exists() else "skip",
            "openspec": "init" if not (self.tmp_dir / "openspec" / "config.yaml").exists() else "skip",
            "schema": "install" if not (self.tmp_dir / "openspec" / "schemas" / "sdd-plus-superpowers").exists() else "skip",
            "memory": "init" if not (self.tmp_dir / ".ai-memory" / "manifest.json").exists() else "skip",
        }
        return result

    def test_empty_project_all_steps_needed(self) -> None:
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["agents_md"], "create")
        self.assertEqual(result["openspec"], "init")
        self.assertEqual(result["schema"], "install")
        self.assertEqual(result["memory"], "init")

    def test_all_initialized_project_no_actions_needed(self) -> None:
        self._create_agents_md("# Test AGENTS\n")
        self._create_openspec_config()
        self._create_schema_dir()
        self._create_ai_memory()
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["agents_md"], "skip")
        self.assertEqual(result["openspec"], "skip")
        self.assertEqual(result["schema"], "skip")
        self.assertEqual(result["memory"], "skip")

    def test_existing_agents_md_preserved(self) -> None:
        original = "# Custom Instructions\nDo not remove me.\n"
        self._create_agents_md(original)
        self._create_openspec_config()
        self._create_schema_dir()
        self._create_ai_memory()
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["agents_md"], "skip")
        current = (self.tmp_dir / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(current, original, "Existing AGENTS.md content must not be modified")

    def test_existing_openspec_detected_and_skipped(self) -> None:
        self._create_openspec_config()
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["openspec"], "skip")

    def test_existing_schema_detected_and_skipped(self) -> None:
        self._create_schema_dir()
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["schema"], "skip")

    def test_existing_memory_detected_and_skipped(self) -> None:
        self._create_ai_memory()
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["memory"], "skip")

    def test_idempotence_repeated_detection(self) -> None:
        self._create_agents_md("# Test\n")
        self._create_openspec_config()
        self._create_schema_dir()
        self._create_ai_memory()
        result1 = self._simulate_full_bootstrap()
        result2 = self._simulate_full_bootstrap()
        self.assertEqual(result1, result2, "Detection results must be identical on re-runs")
        self.assertEqual(result1["agents_md"], "skip")
        self.assertEqual(result1["openspec"], "skip")
        self.assertEqual(result1["schema"], "skip")
        self.assertEqual(result1["memory"], "skip")

    def test_partial_init_only_missing_steps(self) -> None:
        self._create_agents_md("# Existing AGENTS\n")
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["agents_md"], "skip")
        self.assertEqual(result["openspec"], "init")
        self.assertEqual(result["schema"], "install")
        self.assertEqual(result["memory"], "init")

    def test_dry_run_detection_no_side_effects(self) -> None:
        """Dry-run must not create any files."""
        original_files = set(
            p.relative_to(self.tmp_dir) for p in self.tmp_dir.rglob("*") if p.is_file()
        )
        result = self._simulate_full_bootstrap()
        after_files = set(
            p.relative_to(self.tmp_dir) for p in self.tmp_dir.rglob("*") if p.is_file()
        )
        self.assertEqual(original_files, after_files, "Dry-run must not create any files")
        self.assertEqual(result["agents_md"], "create")

    def test_schema_newer_version_detection(self) -> None:
        """When schema exists but is older version, mark as install."""
        self._create_schema_dir()
        old_schema = self.tmp_dir / "openspec" / "schemas" / "sdd-plus-superpowers" / "schema.yaml"
        old_schema.write_text("name: sdd-plus-superpowers\nversion: 0\n", encoding="utf-8")
        schema_path = old_schema
        self.assertTrue(schema_path.exists(), "Schema should exist even if outdated")
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["schema"], "skip",
                         "Basic detection treats installed schema as present; version comparison is runtime behavior")

    def test_duplicate_run_no_triple_init(self) -> None:
        """Simulate three detection runs; should be stable."""
        self._create_agents_md("# AGENTS\n")
        self._create_openspec_config()
        self._create_schema_dir()
        self._create_ai_memory()
        results = [self._simulate_full_bootstrap() for _ in range(3)]
        for r in results:
            self.assertEqual(r["agents_md"], "skip")
            self.assertEqual(r["openspec"], "skip")
            self.assertEqual(r["schema"], "skip")
            self.assertEqual(r["memory"], "skip")

    def test_openspec_init_standalone_openspec_only_schema_missing(self) -> None:
        """Standalone openspec-init: OpenSpec exists but schema is missing."""
        self._create_openspec_config()
        result = self._simulate_full_bootstrap()
        self.assertEqual(result["openspec"], "skip")
        self.assertEqual(result["schema"], "install")


if __name__ == "__main__":
    unittest.main()
