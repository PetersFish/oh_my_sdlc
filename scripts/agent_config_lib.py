#!/usr/bin/env python3
"""Shared helper library for agent model-profile configuration.

Consumed by install_agents.py, activate_agents_config.py, and setup_agents.py.
Provides config loading/validation, effective model/variant resolution,
frontmatter mutation, and normalized content comparison.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

DEFAULT_VARIANT = "medium"
SUPPORTED_SCHEMA_VERSION = 1

# model must be of form provider/model with at least one character before and after slash
MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*/[a-zA-Z0-9][a-zA-Z0-9_.-]*$")


# ---------------------------------------------------------------------------
# Config loading / validation
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict[str, Any]:
    """Load a model-profiles.yaml file and return the parsed dict."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Config at {path} is not a valid YAML mapping")
    return data


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate a model-profiles config dict. Returns a list of error messages (empty = valid)."""
    errors: list[str] = []

    # schema_version
    sv = config.get("schema_version")
    if sv != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {sv!r} (expected {SUPPORTED_SCHEMA_VERSION})")

    # profiles
    profiles = config.get("profiles", {})
    if not isinstance(profiles, dict):
        errors.append("'profiles' must be a mapping")
    else:
        for pname, pdata in profiles.items():
            if not isinstance(pdata, dict):
                errors.append(f"Profile {pname!r}: value must be a mapping")
                continue
            model = pdata.get("model")
            if model is not None:
                if not isinstance(model, str) or not MODEL_PATTERN.match(model):
                    errors.append(
                        f"Profile {pname!r}: model {model!r} is not a valid provider/model (e.g. openai/gpt-5)"
                    )

    # agents
    agents = config.get("agents", {})
    if not isinstance(agents, dict):
        errors.append("'agents' must be a mapping")
    else:
        for aname, adata in agents.items():
            if not isinstance(adata, dict):
                errors.append(f"Agent {aname!r}: value must be a mapping")
                continue
            model = adata.get("model")
            if model is not None:
                if not isinstance(model, str) or not MODEL_PATTERN.match(model):
                    errors.append(
                        f"Agent {aname!r}: model {model!r} is not a valid provider/model"
                    )
            profile = adata.get("profile")
            if profile is not None and profile not in profiles:
                errors.append(f"Agent {aname!r}: references unknown profile {profile!r}")

    return errors


# ---------------------------------------------------------------------------
# Effective resolution
# ---------------------------------------------------------------------------

def _resolve_agent_config(config: dict[str, Any], agent_name: str) -> dict[str, Any]:
    """Return the merged agent-level dict (including profile defaults)."""
    agents = config.get("agents", {})
    profiles = config.get("profiles", {})
    agent_entry = agents.get(agent_name)
    if not isinstance(agent_entry, dict):
        raise KeyError(f"Agent {agent_name!r} not found in config.agents")

    profile_name = agent_entry.get("profile")
    profile_data: dict[str, Any] = {}
    if profile_name:
        profile_data = profiles.get(profile_name, {})
        if not isinstance(profile_data, dict):
            profile_data = {}

    # Merge: profile provides defaults, agent entry overrides
    merged: dict[str, Any] = dict(profile_data)
    merged.update(agent_entry)
    return merged


def resolve_model(config: dict[str, Any], agent_name: str) -> str:
    """Resolve the effective model for an agent.

    Precedence: agents.<agent>.model > profiles.<profile>.model
    """
    merged = _resolve_agent_config(config, agent_name)
    model = merged.get("model")
    if model:
        return str(model)
    raise KeyError(f"No model configured for agent {agent_name!r}")


def resolve_variant(config: dict[str, Any], agent_name: str) -> str:
    """Resolve the effective variant for an agent.

    Precedence: agents.<agent>.variant > profiles.<profile>.variant > defaults.variant > 'medium'
    """
    defaults = config.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}

    merged = _resolve_agent_config(config, agent_name)

    variant = merged.get("variant")
    if variant:
        return str(variant)

    variant = defaults.get("variant")
    if variant:
        return str(variant)

    return DEFAULT_VARIANT


# ---------------------------------------------------------------------------
# Frontmatter mutation
# ---------------------------------------------------------------------------

def update_frontmatter(content: str, model: str, variant: str) -> str:
    """Insert or update 'model' and 'variant' in a Markdown file's YAML frontmatter.

    - If the file already has YAML frontmatter (starts with '---'), replace/add
      the model/variant lines while preserving all other frontmatter fields.
    - If the file has no frontmatter, insert a new frontmatter block with only
      model and variant before the body.
    """
    if content.startswith("---"):
        # Find end of frontmatter
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            # Malformed: starts with --- but no closing ---
            # Treat as no frontmatter and insert
            return f"---\nmodel: {model}\nvariant: {variant}\n---\n{content}"

        fm_text = content[3:end_idx]
        body = content[end_idx + 4:]  # after the closing ---
        new_fm = _merge_frontmatter_lines(fm_text, model, variant)
        return f"---{new_fm}---{body}"
    else:
        # No frontmatter — insert one
        return f"---\nmodel: {model}\nvariant: {variant}\n---\n{content}"


def _merge_frontmatter_lines(fm_text: str, model: str, variant: str) -> str:
    """Replace or append model/variant in frontmatter text, preserving order and other fields."""
    lines = fm_text.split("\n")
    result: list[str] = []
    has_model = False
    has_variant = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this line starts a model or variant key
        if stripped.startswith("model:"):
            result.append(f"model: {model}")
            has_model = True
            i += 1
            continue
        if stripped.startswith("variant:"):
            result.append(f"variant: {variant}")
            has_variant = True
            i += 1
            continue

        # Handle multi-line values (indented continuation)
        if line and not line[0].isspace():
            result.append(line)
            i += 1
        else:
            result.append(line)
            i += 1

    # Append model/variant at end if not found
    if not has_model:
        result.append(f"model: {model}")
    if not has_variant:
        result.append(f"variant: {variant}")

    return "\n".join(result) + "\n"


# ---------------------------------------------------------------------------
# Normalized comparison (ignoring activation-managed fields)
# ---------------------------------------------------------------------------

def normalized_content(text: str) -> str:
    """Return content with model and variant lines removed from frontmatter.

    This lets template-sync drift checks ignore only activation-managed fields
    while still detecting genuine prompt/body differences.
    """
    if not text.startswith("---"):
        return text

    end_idx = text.find("\n---", 3)
    if end_idx == -1:
        return text

    fm_text = text[3:end_idx]
    body = text[end_idx + 4:]

    # Remove model and variant lines from frontmatter
    lines = fm_text.split("\n")
    filtered: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("model:") or stripped.startswith("variant:"):
            continue
        filtered.append(line)

    return "---" + "\n".join(filtered) + "---" + body


def scan_agent_files(directory: Path, normalize: bool = False) -> dict[str, str]:
    """Scan a directory for *.md agent files, returning {filename: sha256}.

    When normalize=True, the hash is computed on normalized_content (ignoring
    model/variant).  When False, the hash covers the raw file bytes.
    """
    files: dict[str, str] = {}
    if not directory.is_dir():
        return files
    for entry in sorted(directory.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.suffix != ".md":
            continue
        if entry.is_file():
            raw = entry.read_bytes()
            if normalize:
                text = raw.decode("utf-8")
                text = normalized_content(text)
                raw = text.encode("utf-8")
            files[entry.name] = hashlib.sha256(raw).hexdigest()
    return files
