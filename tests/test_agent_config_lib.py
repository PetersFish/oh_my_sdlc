"""Behavior tests for scripts/agent_config_lib.py — shared config resolution helper."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure the scripts/ directory is on sys.path for import
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# Will import after module creation
# import agent_config_lib as lib


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestConfigLoadValidate(unittest.TestCase):
    """WP1: config loading, schema validation, model-format checks."""

    def _make_config(self, tmp: str, yaml_text: str) -> Path:
        p = Path(tmp) / "model-profiles.yaml"
        _write_yaml(p, yaml_text)
        return p

    # --- Helpers for lazy import (only after lib exists) ---
    def _import_lib(self):
        import agent_config_lib
        return agent_config_lib

    def test_load_valid_model_profiles_config(self):
        lib = self._import_lib()
        yaml = """\
schema_version: 1
defaults:
  variant: medium
profiles:
  orch:
    model: openai/gpt-5.5
    variant: low
agents:
  dev-orchestrator:
    profile: orch
"""
        path = self._make_config(tempfile.mkdtemp(), yaml)
        cfg = lib.load_config(path)
        self.assertEqual(cfg["schema_version"], 1)
        self.assertIn("profiles", cfg)
        self.assertIn("agents", cfg)

    def test_rejects_invalid_schema_version(self):
        lib = self._import_lib()
        yaml = "schema_version: 99\ndefaults:\n  variant: medium\nprofiles: {}\nagents: {}\n"
        path = self._make_config(tempfile.mkdtemp(), yaml)
        errors = lib.validate_config(lib.load_config(path))
        self.assertTrue(any("schema_version" in e.lower() or "unsupported" in e.lower() for e in errors))

    def test_rejects_model_without_provider_prefix(self):
        lib = self._import_lib()
        yaml = "schema_version: 1\ndefaults:\n  variant: medium\nprofiles:\n  p1:\n    model: gpt-5.5\nagents: {}\n"
        path = self._make_config(tempfile.mkdtemp(), yaml)
        errors = lib.validate_config(lib.load_config(path))
        self.assertTrue(any("provider" in e.lower() or "slash" in e.lower() or "model" in e.lower() for e in errors))


class TestModelResolution(unittest.TestCase):
    """WP1: model + variant precedence resolution."""

    def _make_config(self, tmp: str, yaml_text: str) -> Path:
        p = Path(tmp) / "model-profiles.yaml"
        _write_yaml(p, yaml_text)
        return p

    def _import_lib(self):
        import agent_config_lib
        return agent_config_lib

    def test_resolves_agent_model_override_over_profile_model(self):
        lib = self._import_lib()
        yaml = """\
schema_version: 1
defaults:
  variant: medium
profiles:
  orch:
    model: openai/gpt-5.5
agents:
  dev-orchestrator:
    profile: orch
    model: openai/gpt-6
"""
        path = self._make_config(tempfile.mkdtemp(), yaml)
        cfg = lib.load_config(path)
        model = lib.resolve_model(cfg, "dev-orchestrator")
        self.assertEqual(model, "openai/gpt-6", "agent-level model override must win over profile model")

    def test_resolves_variant_priority_agent_then_profile_then_defaults_then_medium(self):
        lib = self._import_lib()
        # test 1: agent override
        yaml = """\
schema_version: 1
defaults:
  variant: low
profiles:
  p1:
    model: openai/gpt-5
    variant: high
agents:
  a1:
    profile: p1
    variant: turbo
"""
        path = self._make_config(tempfile.mkdtemp(), yaml)
        cfg = lib.load_config(path)
        self.assertEqual(lib.resolve_variant(cfg, "a1"), "turbo",
                         "agent.variant should win over profile and defaults")

        # test 2: profile override over defaults
        yaml2 = """\
schema_version: 1
defaults:
  variant: low
profiles:
  p1:
    model: openai/gpt-5
    variant: high
agents:
  a1:
    profile: p1
"""
        path2 = self._make_config(tempfile.mkdtemp(), yaml2)
        cfg2 = lib.load_config(path2)
        self.assertEqual(lib.resolve_variant(cfg2, "a1"), "high",
                         "profile.variant should win over defaults")

        # test 3: defaults used when nothing else
        yaml3 = """\
schema_version: 1
defaults:
  variant: low
profiles:
  p1:
    model: openai/gpt-5
agents:
  a1:
    profile: p1
"""
        path3 = self._make_config(tempfile.mkdtemp(), yaml3)
        cfg3 = lib.load_config(path3)
        self.assertEqual(lib.resolve_variant(cfg3, "a1"), "low",
                         "defaults.variant should be used when no other source")

        # test 4: implicit medium when nothing configured
        yaml4 = """\
schema_version: 1
defaults: {}
profiles:
  p1:
    model: openai/gpt-5
agents:
  a1:
    profile: p1
"""
        path4 = self._make_config(tempfile.mkdtemp(), yaml4)
        cfg4 = lib.load_config(path4)
        self.assertEqual(lib.resolve_variant(cfg4, "a1"), "medium",
                         "should default to 'medium' when no variant configured")


class TestFrontmatterMutation(unittest.TestCase):
    """WP1: frontmatter update/insert and normalized comparison."""

    def _import_lib(self):
        import agent_config_lib
        return agent_config_lib

    def test_update_frontmatter_preserves_existing_fields_and_body(self):
        lib = self._import_lib()
        original = """---
name: test-agent
mode: subagent
permission:
  edit: allow
---
# Test Agent

Some body content here.
"""
        result = lib.update_frontmatter(original, "openai/gpt-5", "high")
        self.assertIn("model: openai/gpt-5", result)
        self.assertIn("variant: high", result)
        self.assertIn("name: test-agent", result, "existing frontmatter fields preserved")
        self.assertIn("mode: subagent", result, "existing frontmatter fields preserved")
        self.assertIn("# Test Agent", result, "body preserved")
        self.assertIn("Some body content here.", result, "body preserved")
        # Should NOT have duplicate model/variant
        self.assertEqual(result.count("model: openai/gpt-5"), 1)

    def test_normalized_compare_ignores_model_and_variant_only(self):
        lib = self._import_lib()
        content_a = """---
name: test-agent
model: openai/gpt-5
variant: high
mode: subagent
permission:
  edit: allow
---
# Body
"""
        content_b = """---
name: test-agent
model: openai/gpt-6
variant: low
mode: subagent
permission:
  edit: allow
---
# Body
"""
        # Same after ignoring model/variant
        norm_a = lib.normalized_content(content_a)
        norm_b = lib.normalized_content(content_b)
        self.assertEqual(norm_a, norm_b, "normalized compare should ignore only model and variant")

        # Different body should differ
        content_c = """---
name: test-agent
model: openai/gpt-5
variant: high
mode: subagent
permission:
  edit: allow
---
# Body Changed
"""
        norm_c = lib.normalized_content(content_c)
        self.assertNotEqual(norm_a, norm_c, "different body should cause drift")

    def test_activation_can_insert_frontmatter_when_missing(self):
        lib = self._import_lib()
        body_only = "# No frontmatter here\n\nJust a body.\n"
        result = lib.update_frontmatter(body_only, "openai/gpt-5", "medium")
        self.assertTrue(result.startswith("---"), "should insert valid YAML frontmatter")
        self.assertIn("model: openai/gpt-5", result)
        self.assertIn("variant: medium", result)
        self.assertIn("# No frontmatter here", result, "body preserved")
        self.assertIn("Just a body.", result, "body preserved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
