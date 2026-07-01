"""Behavior tests for scripts/agent_config_lib.py — shared config/helper layer."""

import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

# Add scripts/ to path for direct import
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
import sys
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from agent_config_lib import (
    load_model_profiles_config,
    validate_config,
    resolve_effective_model,
    resolve_effective_variant,
    update_frontmatter,
    normalized_content_hash,
    normalized_prompt_compare,
    scan_agent_markdown_files,
    get_target_config_path,
    ACTIVATION_MANAGED_FIELDS,
    MODEL_PATTERN,
    SCHEMA_VERSION,
)

VALID_CONFIG = {
    "schema_version": 1,
    "defaults": {"variant": "medium"},
    "profiles": {
        "orchestrator": {"model": "openai/gpt-5.4", "variant": "medium"},
        "planning": {"model": "openai/gpt-5.5"},
        "implementation": {"model": "opencode-go/deepseek-v4-pro", "variant": "medium"},
        "testing": {"model": "openai/gpt-5.4"},
        "review": {"model": "openai/gpt-5.5", "variant": "low"},
        "finish": {"model": "opencode-go/deepseek-v4-pro"},
    },
    "agents": {
        "dev-orchestrator": {"profile": "orchestrator"},
        "plan-agent": {"profile": "planning"},
        "implement-agent": {"profile": "implementation"},
        "test-agent": {"profile": "testing"},
        "review-agent": {"profile": "review"},
        "finish-agent": {"profile": "finish"},
    },
}


def _make_yaml_file(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


class TestConfigLoading(unittest.TestCase):
    """Tests for model-profiles.yaml loading and validation."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _make_config(self, data: dict) -> str:
        path = os.path.join(self.tmp, "model-profiles.yaml")
        _make_yaml_file(path, data)
        return path

    def test_load_valid_model_profiles_config(self):
        """Verifies a valid config with defaults/profiles/agents loads successfully."""
        config_path = self._make_config(VALID_CONFIG)
        loaded = load_model_profiles_config(Path(config_path))
        self.assertIn("schema_version", loaded)
        self.assertEqual(loaded["schema_version"], 1)
        self.assertIn("defaults", loaded)
        self.assertIn("profiles", loaded)
        self.assertIn("agents", loaded)

    def test_rejects_invalid_schema_version(self):
        """Verifies schema_version != 1 is rejected."""
        bad_config = copy.deepcopy(VALID_CONFIG)
        bad_config["schema_version"] = 99
        config_path = self._make_config(bad_config)
        with self.assertRaises(ValueError):
            load_model_profiles_config(Path(config_path))

    def test_rejects_missing_schema_version(self):
        """Verifies missing schema_version is rejected."""
        bad_config = copy.deepcopy(VALID_CONFIG)
        del bad_config["schema_version"]
        config_path = self._make_config(bad_config)
        with self.assertRaises(ValueError):
            load_model_profiles_config(Path(config_path))

    def test_rejects_model_without_provider_prefix(self):
        """Verifies provider/model validation rejects model without '/'."""
        bad_config = copy.deepcopy(VALID_CONFIG)
        bad_config["profiles"]["orchestrator"]["model"] = "just-amodel-name"
        config_path = self._make_config(bad_config)
        errors = validate_config(yaml.safe_load(open(config_path, encoding="utf-8")))
        self.assertTrue(any("model" in e.lower() for e in errors),
                        f"Expected model validation error, got: {errors}")

    def test_validate_config_accepts_valid_config(self):
        """Verifies a valid config produces no validation errors."""
        errors = validate_config(VALID_CONFIG)
        self.assertEqual(errors, [], f"Valid config should have no errors, got: {errors}")


class TestModelResolution(unittest.TestCase):
    """Tests for effective model and variant resolution."""

    def test_resolves_agent_model_override_over_profile_model(self):
        """Verifies agents.<name>.model wins over profile model."""
        config = copy.deepcopy(VALID_CONFIG)
        config["agents"]["implement-agent"]["model"] = "openai/gpt-5-override"
        model = resolve_effective_model("implement-agent", config)
        self.assertEqual(model, "openai/gpt-5-override")

    def test_resolves_model_from_profile(self):
        """Verifies profile model is used when no agent override."""
        model = resolve_effective_model("plan-agent", VALID_CONFIG)
        self.assertEqual(model, "openai/gpt-5.5")

    def test_resolves_variant_priority_agent_then_profile_then_defaults_then_medium(self):
        """Verifies the full variant fallback chain."""
        config = copy.deepcopy(VALID_CONFIG)

        # review-agent: profile has variant "low", agent has no override
        variant = resolve_effective_variant("review-agent", config)
        self.assertEqual(variant, "low")

        # planning: no profile variant, defaults says "medium"
        variant = resolve_effective_variant("plan-agent", config)
        self.assertEqual(variant, "medium")

        # Add agent-level override
        config["agents"]["review-agent"]["variant"] = "high"
        variant = resolve_effective_variant("review-agent", config)
        self.assertEqual(variant, "high")

    def test_resolves_variant_fallback_to_medium_when_nothing_configured(self):
        """Verifies variant falls back to 'medium' when nothing is set."""
        config = {
            "schema_version": 1,
            "defaults": {},
            "profiles": {
                "test": {"model": "openai/gpt-4"},
            },
            "agents": {
                "test-agent": {"profile": "test"},
            },
        }
        variant = resolve_effective_variant("test-agent", config)
        self.assertEqual(variant, "medium")

    def test_resolve_model_raises_for_unknown_agent(self):
        """Verifies resolution raises for unknown agent names."""
        with self.assertRaises(ValueError):
            resolve_effective_model("no-such-agent", VALID_CONFIG)

    def test_resolve_variant_raises_for_unknown_agent(self):
        """Verifies resolution raises for unknown agent names."""
        with self.assertRaises(ValueError):
            resolve_effective_variant("no-such-agent", VALID_CONFIG)


class TestFrontmatterMutation(unittest.TestCase):
    """Tests for frontmatter update/insert behavior."""

    def test_update_frontmatter_preserves_existing_fields_and_body(self):
        """Verifies model/variant insertion does not alter other fields or body."""
        markdown = """---
name: test-agent
mode: subagent
description: A test agent
model: old/model
variant: low
permission:
  edit: allow
---
# Test Agent

This is the body content.
"""
        result = update_frontmatter(markdown, "new/model", "high")

        from support.frontmatter import read_frontmatter

        tmp_path = os.path.join(tempfile.mkdtemp(), "test.md")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(result)

        fm = read_frontmatter(Path(tmp_path))
        self.assertEqual(fm.get("model"), "new/model")
        self.assertEqual(fm.get("variant"), "high")
        self.assertEqual(fm.get("name"), "test-agent")
        self.assertEqual(fm.get("mode"), "subagent")
        self.assertEqual(fm.get("description"), "A test agent")
        self.assertEqual(fm.get("permission"), {"edit": "allow"})
        self.assertIn("# Test Agent", result)
        self.assertIn("This is the body content.", result)

        shutil.rmtree(os.path.dirname(tmp_path))

    def test_update_frontmatter_adds_model_and_variant_when_missing(self):
        """Verifies model/variant are added when frontmatter has neither."""
        markdown = """---
name: test-agent
mode: subagent
---
# Body
"""
        result = update_frontmatter(markdown, "openai/gpt-4", "medium")
        from support.frontmatter import read_frontmatter

        tmp_path = os.path.join(tempfile.mkdtemp(), "test.md")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(result)

        fm = read_frontmatter(Path(tmp_path))
        self.assertEqual(fm.get("model"), "openai/gpt-4")
        self.assertEqual(fm.get("variant"), "medium")
        self.assertIn("# Body", result)
        shutil.rmtree(os.path.dirname(tmp_path))

    def test_insert_frontmatter_when_body_only(self):
        """Verifies body-only markdown gets frontmatter inserted."""
        body_only = "# Test Agent\n\nThis agent has no frontmatter.\n"
        result = update_frontmatter(body_only, "openai/gpt-4", "medium")
        self.assertTrue(result.startswith("---\n"), f"Expected frontmatter start, got: {result[:50]}")

        from support.frontmatter import read_frontmatter
        tmp_path = os.path.join(tempfile.mkdtemp(), "test.md")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(result)
        fm = read_frontmatter(Path(tmp_path))
        self.assertEqual(fm.get("model"), "openai/gpt-4")
        self.assertEqual(fm.get("variant"), "medium")
        self.assertIn("This agent has no frontmatter.", result)
        shutil.rmtree(os.path.dirname(tmp_path))


class TestNormalizedComparison(unittest.TestCase):
    """Tests for normalized prompt comparison (activation-drift)."""

    def test_normalized_prompt_compare_ignores_model_and_variant_only(self):
        """Verifies comparison ignores only model/variant differences."""
        canonical = """---
name: test-agent
mode: subagent
description: A test agent
model: openai/gpt-5.4
variant: medium
---
# Body content
"""
        target = """---
name: test-agent
mode: subagent
description: A test agent
model: openai/gpt-5.5
variant: low
---
# Body content
"""
        # Only model/variant differ — should compare as equal
        self.assertTrue(normalized_prompt_compare(canonical, target))

    def test_normalized_prompt_compare_detects_real_drift(self):
        """Verifies comparison fails when other fields differ."""
        canonical = """---
name: test-agent
mode: subagent
---
# Body
"""
        target = """---
name: test-agent
mode: primary
---
# Body
"""
        self.assertFalse(normalized_prompt_compare(canonical, target))

    def test_normalized_prompt_compare_detects_body_drift(self):
        """Verifies comparison fails when body differs."""
        canonical = """---
name: test-agent
---
# Body A
"""
        target = """---
name: test-agent
---
# Body B
"""
        self.assertFalse(normalized_prompt_compare(canonical, target))

    def test_normalized_content_hash_ignores_activation_fields(self):
        """Verifies content hash is stable regardless of model/variant."""
        a = """---
name: test
model: openai/gpt-5.4
variant: medium
---
# Body
"""
        b = """---
name: test
model: openai/gpt-5.5
variant: low
---
# Body
"""
        self.assertEqual(normalized_content_hash(a), normalized_content_hash(b))

    def test_normalized_content_hash_differs_for_different_bodies(self):
        """Verifies hash differs when bodies differ."""
        a = """---
name: test
---
# Body A
"""
        b = """---
name: test
---
# Body B
"""
        self.assertNotEqual(normalized_content_hash(a), normalized_content_hash(b))


class TestFileScanning(unittest.TestCase):
    """Tests for agent directory scanning and path helpers."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_scan_agent_markdown_files_returns_md_only(self):
        """Verifies scan returns only .md files, excluding metadata."""
        for fname in ("dev-orchestrator.md", "plan-agent.md", ".agent-install.json", "notes.txt"):
            with open(os.path.join(self.tmp, fname), "w", encoding="utf-8") as f:
                f.write(f"content of {fname}")

        files = scan_agent_markdown_files(Path(self.tmp))
        self.assertIn("dev-orchestrator.md", files)
        self.assertIn("plan-agent.md", files)
        self.assertNotIn(".agent-install.json", files)
        self.assertNotIn("notes.txt", files)

    def test_scan_agent_markdown_files_excludes_subdirs(self):
        """Verifies scan does not recurse into subdirs."""
        os.makedirs(os.path.join(self.tmp, "config"))
        with open(os.path.join(self.tmp, "agent.md"), "w") as f:
            f.write("content")
        with open(os.path.join(self.tmp, "config", "nested.md"), "w") as f:
            f.write("nested")

        files = scan_agent_markdown_files(Path(self.tmp))
        self.assertIn("agent.md", files)
        self.assertNotIn("nested.md", files)

    def test_get_target_config_path(self):
        """Verifies target config path is constructed correctly."""
        path = get_target_config_path(Path("/some/target"))
        self.assertEqual(str(path), "/some/target/config/model-profiles.yaml")


if __name__ == "__main__":
    unittest.main(verbosity=2)
