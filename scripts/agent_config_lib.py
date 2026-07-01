#!/usr/bin/env python3
"""Shared helper library for agent model configuration.

Provides config loading/validation, effective model/variant resolution,
frontmatter mutation, and normalized prompt comparison used by:
  - install_agents.py (template sync)
  - activate_agents_config.py (effective-config activation)
  - setup_agents.py (aggregate orchestration)
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

# ---- constants ----

ACTIVATION_MANAGED_FIELDS = {"model", "variant"}
"""Frontmatter fields that activation manages; excluded from template drift checks."""

MODEL_PROFILES_FILENAME = "model-profiles.yaml"
"""Filename for both canonical template and target effective config."""

CONFIG_SUBDIR = "config"
"""Subdirectory under a target agent directory where effective config lives."""

SCHEMA_VERSION = 1
"""Only schema version 1 is accepted."""

MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")
"""Model identifiers must contain exactly one '/' separating provider from model name."""

SKIP_NAMES = {".agent-install.json", ".DS_Store"}
SKIP_SUFFIXES = (".pyc",)


# ---- config loading / validation ----

def load_model_profiles_config(path: Path) -> dict[str, Any]:
    """Load and validate a model-profiles.yaml file.  Raises ValueError on invalid data."""
    if not path.is_file():
        raise ValueError(f"config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"config file {path} must contain a YAML mapping, got {type(data).__name__}")
    errors = validate_config(data)
    if errors:
        raise ValueError(f"invalid config in {path}: {'; '.join(errors)}")
    return data


def validate_config(config: dict[str, Any]) -> list[str]:
    """Return a list of validation error strings (empty if valid)."""
    errors: list[str] = []

    if not isinstance(config, dict):
        return ["config must be a mapping"]

    # schema_version
    sv = config.get("schema_version")
    if sv is None:
        errors.append("missing required field: schema_version")
    elif sv != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {sv} (expected {SCHEMA_VERSION})")

    # defaults
    defaults = config.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        errors.append("defaults must be a mapping")

    # profiles
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        errors.append("profiles must be a mapping")
    else:
        for pname, pdata in profiles.items():
            if not isinstance(pdata, dict):
                errors.append(f"profiles.{pname} must be a mapping")
                continue
            model = pdata.get("model")
            if not isinstance(model, str):
                errors.append(f"profiles.{pname}: missing or invalid model")
            elif not MODEL_PATTERN.match(model):
                errors.append(f"profiles.{pname}: model '{model}' must be in provider/model format")

    # agents
    agents = config.get("agents")
    if not isinstance(agents, dict):
        errors.append("agents must be a mapping")
    else:
        for aname, adata in agents.items():
            if not isinstance(adata, dict):
                errors.append(f"agents.{aname} must be a mapping")
                continue
            profile = adata.get("profile")
            if not isinstance(profile, str):
                errors.append(f"agents.{aname}: missing or invalid profile reference")
                continue
            if profiles and isinstance(profiles, dict) and profile not in profiles:
                errors.append(f"agents.{aname}: references unknown profile '{profile}'")
            # Optional agent-level model override
            agent_model = adata.get("model")
            if agent_model is not None:
                if not isinstance(agent_model, str):
                    errors.append(f"agents.{aname}: model must be a string")
                elif not MODEL_PATTERN.match(agent_model):
                    errors.append(f"agents.{aname}: model '{agent_model}' must be in provider/model format")

    return errors


# ---- effective resolution ----

def _get_agent_entry(agent_name: str, config: dict[str, Any]) -> dict[str, Any]:
    agents = config.get("agents", {})
    if agent_name not in agents:
        raise ValueError(f"unknown agent: {agent_name}")
    entry = agents[agent_name]
    if not isinstance(entry, dict):
        raise ValueError(f"agents.{agent_name} is not a mapping")
    return entry


def _get_profile_entry(agent_entry: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    profile_name = agent_entry.get("profile")
    if not isinstance(profile_name, str):
        raise ValueError(f"agent entry missing profile reference")
    profiles = config.get("profiles", {})
    if profile_name not in profiles:
        raise ValueError(f"unknown profile: {profile_name}")
    entry = profiles[profile_name]
    if not isinstance(entry, dict):
        raise ValueError(f"profiles.{profile_name} is not a mapping")
    return entry


def resolve_effective_model(agent_name: str, config: dict[str, Any]) -> str:
    """Return the effective model for *agent_name*.

    Precedence: agents.<name>.model > profiles.<profile>.model.
    """
    agent_entry = _get_agent_entry(agent_name, config)

    # 1. agent-level override
    if "model" in agent_entry:
        return agent_entry["model"]

    # 2. profile-level model
    profile_entry = _get_profile_entry(agent_entry, config)
    if "model" not in profile_entry:
        raise ValueError(f"profile {agent_entry['profile']!r} has no model configured")
    return profile_entry["model"]


def resolve_effective_variant(agent_name: str, config: dict[str, Any]) -> str:
    """Return the effective variant for *agent_name*.

    Precedence: agents.<name>.variant > profiles.<profile>.variant
                > defaults.variant > "medium".
    """
    agent_entry = _get_agent_entry(agent_name, config)

    # 1. agent-level override
    if "variant" in agent_entry:
        return agent_entry["variant"]

    # 2. profile-level variant
    profile_entry = _get_profile_entry(agent_entry, config)
    if "variant" in profile_entry:
        return profile_entry["variant"]

    # 3. defaults.variant
    defaults = config.get("defaults", {})
    if isinstance(defaults, dict) and "variant" in defaults:
        return defaults["variant"]

    # 4. hardcoded fallback
    return "medium"


# ---- frontmatter mutation ----

def update_frontmatter(markdown_content: str, model: str, variant: str) -> str:
    """Return *markdown_content* with ``model`` and ``variant`` frontmatter fields
    set/updated.  All other frontmatter fields and the markdown body are preserved.
    If the content has no YAML frontmatter, one is inserted at the top."""
    if markdown_content.startswith("---"):
        # Has existing frontmatter — parse, update, and rebuild
        end = markdown_content.find("\n---", 3)
        if end == -1:
            # Malformed: starts with --- but no closing ---; treat as no frontmatter
            return _insert_frontmatter(markdown_content, model, variant)

        fm_text = markdown_content[3:end].rstrip()
        body = markdown_content[end + 4:]  # after the closing ---

        # Parse existing frontmatter
        try:
            fm_data = yaml.safe_load(fm_text)
        except yaml.YAMLError:
            # Can't parse — fall back to line-by-line replacement
            return _rebuild_frontmatter_line_by_line(fm_text, body, model, variant)

        if not isinstance(fm_data, dict):
            fm_data = {}

        # Update activation-managed fields
        fm_data["model"] = model
        fm_data["variant"] = variant

        # Rebuild frontmatter preserving all other fields
        new_fm = yaml.dump(fm_data, default_flow_style=False, allow_unicode=True).rstrip()
        return f"---\n{new_fm}\n---{body}"

    # No frontmatter — insert one
    return _insert_frontmatter(markdown_content, model, variant)


def _insert_frontmatter(body: str, model: str, variant: str) -> str:
    """Insert YAML frontmatter at the top of body-only content."""
    fm = {"model": model, "variant": variant}
    fm_text = yaml.dump(fm, default_flow_style=False, allow_unicode=True).rstrip()
    return f"---\n{fm_text}\n---\n{body}"


def _rebuild_frontmatter_line_by_line(
    fm_text: str, body: str, model: str, variant: str
) -> str:
    """Line-by-line fallback: replace/insert model and variant in raw YAML text."""
    lines = fm_text.split("\n")
    new_lines: list[str] = []
    seen_model = False
    seen_variant = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("model:") and not seen_model:
            new_lines.append(f"model: {model}")
            seen_model = True
        elif stripped.startswith("variant:") and not seen_variant:
            new_lines.append(f"variant: {variant}")
            seen_variant = True
        else:
            new_lines.append(line)

    if not seen_model:
        new_lines.append(f"model: {model}")
    if not seen_variant:
        new_lines.append(f"variant: {variant}")

    new_fm = "\n".join(new_lines)
    return f"---\n{new_fm}\n---{body}"


# ---- normalized comparison ----

def normalized_content_hash(content: str) -> str:
    """Return a SHA-256 hash of *content* after stripping activation-managed
    frontmatter fields (``model``, ``variant``).  Allows template-sync drift
    checks to ignore activation-only differences."""
    normalized = _strip_activation_fields(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalized_prompt_compare(canonical_text: str, target_text: str) -> bool:
    """Return True if *canonical_text* and *target_text* are equivalent after
    ignoring activation-managed frontmatter fields."""
    return _strip_activation_fields(canonical_text) == _strip_activation_fields(target_text)


def _strip_activation_fields(text: str) -> str:
    """Remove model and variant lines from frontmatter, leaving everything else intact."""
    if not text.startswith("---"):
        return text

    end = text.find("\n---", 3)
    if end == -1:
        return text

    fm_lines = text[3:end].split("\n")
    body = text[end + 4:]

    filtered_fm: list[str] = []
    for line in fm_lines:
        stripped = line.strip()
        # Only skip lines that are exactly "model:" or "variant:" keys
        if stripped.startswith("model:") or stripped.startswith("variant:"):
            continue
        filtered_fm.append(line)

    new_fm = "\n".join(filtered_fm)
    return f"---\n{new_fm}\n---{body}"


# ---- file scanning ----

def scan_agent_markdown_files(directory: Path) -> dict[str, str]:
    """Return {filename: sha256_hexdigest} for every ``*.md`` file in *directory*,
    excluding metadata files and subdirectories."""
    files: dict[str, str] = {}
    if not directory.is_dir():
        return files

    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        if entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith(SKIP_SUFFIXES):
            continue
        if entry.suffix == ".md":
            files[entry.name] = hashlib.sha256(entry.read_bytes()).hexdigest()

    return files


def get_target_config_path(target_dir: Path) -> Path:
    """Return the path where a target's effective model-profiles.yaml is expected."""
    return target_dir / CONFIG_SUBDIR / MODEL_PROFILES_FILENAME
