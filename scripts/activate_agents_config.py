#!/usr/bin/env python3
"""Activate effective model configuration into target agent markdown files.

Reads the target ``config/model-profiles.yaml``, resolves effective ``model``
and ``variant`` for each agent, and writes those values into the target agent
markdown frontmatter.  All other frontmatter fields and body content are preserved.
If a target file has no frontmatter, one is inserted.

Modes:
  (default)   Activate (render model/variant into target .md files).
  --check     Compare effective config vs rendered frontmatter; exit 1 on drift.
  --dry-run   Report which files would change without writing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_config_lib import (
    get_target_config_path,
    load_model_profiles_config,
    resolve_effective_model,
    resolve_effective_variant,
    update_frontmatter,
    scan_agent_markdown_files,
    SKIP_NAMES,
    SKIP_SUFFIXES,
)


def _global_target() -> Path:
    return Path.home() / ".config" / "opencode" / "agents"


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _agent_stem_to_name(filename: str) -> str:
    """Convert 'dev-orchestrator.md' to 'dev-orchestrator'."""
    return filename[:-3] if filename.endswith(".md") else filename


def do_activate(target: Path, dry_run: bool = False) -> int:
    """Render effective model/variant from target config into target .md files.

    Returns 0 on success, 1 if config missing."""
    config_path = get_target_config_path(target)
    if not config_path.is_file():
        print(f"ERROR: target config not found: {config_path}", file=sys.stderr)
        print("Run install_agents.py first to initialize the config template.", file=sys.stderr)
        return 1

    try:
        config = load_model_profiles_config(config_path)
    except ValueError as exc:
        print(f"ERROR: invalid target config: {exc}", file=sys.stderr)
        return 1

    agent_names = set(config.get("agents", {}).keys())
    if not agent_names:
        print("WARNING: no agents defined in config", file=sys.stderr)
        return 0

    changes = 0
    for entry in sorted(target.iterdir()):
        if entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith(SKIP_SUFFIXES):
            continue
        if not entry.is_file() or not entry.suffix == ".md":
            continue

        stem = _agent_stem_to_name(entry.name)
        if stem not in agent_names:
            continue

        try:
            model = resolve_effective_model(stem, config)
            variant = resolve_effective_variant(stem, config)
        except ValueError as exc:
            print(f"WARNING: skipping {entry.name}: {exc}", file=sys.stderr)
            continue

        original = _read_file(entry)
        updated = update_frontmatter(original, model, variant)

        if updated != original:
            changes += 1
            if dry_run:
                print(f"[DRY-RUN] would activate: {entry.name} -> model={model} variant={variant}")
            else:
                entry.write_text(updated, encoding="utf-8")
                print(f"ACTIVATED: {entry.name} -> model={model} variant={variant}")

    if changes == 0:
        print("OK: all agents already activated with current config")
    return 0


def _extract_model_variant_from_markdown(content: str) -> tuple[str | None, str | None]:
    """Extract model and variant from frontmatter using simple line scanning."""
    model = None
    variant = None
    if not content.startswith("---"):
        return model, variant
    end = content.find("\n---", 3)
    if end == -1:
        return model, variant
    fm = content[3:end]
    for line in fm.split("\n"):
        stripped = line.strip()
        if stripped.startswith("model:"):
            model = stripped[len("model:"):].strip().strip('"').strip("'")
        elif stripped.startswith("variant:"):
            variant = stripped[len("variant:"):].strip().strip('"').strip("'")
    return model, variant


def do_check(target: Path) -> int:
    """Compare effective config against rendered frontmatter.

    Returns 0 if in sync, 1 if drift detected."""
    config_path = get_target_config_path(target)
    if not config_path.is_file():
        print(f"DRIFT: target config missing: {config_path}")
        return 1

    try:
        config = load_model_profiles_config(config_path)
    except ValueError as exc:
        print(f"DRIFT: invalid target config: {exc}")
        return 1

    agent_names = set(config.get("agents", {}).keys())
    if not agent_names:
        print("WARNING: no agents defined in config")
        return 0

    all_ok = True
    for entry in sorted(target.iterdir()):
        if entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith(SKIP_SUFFIXES):
            continue
        if not entry.is_file() or not entry.suffix == ".md":
            continue

        stem = _agent_stem_to_name(entry.name)
        if stem not in agent_names:
            continue

        try:
            expected_model = resolve_effective_model(stem, config)
            expected_variant = resolve_effective_variant(stem, config)
        except ValueError as exc:
            print(f"DRIFT: {entry.name}: {exc}")
            all_ok = False
            continue

        content = _read_file(entry)
        actual_model, actual_variant = _extract_model_variant_from_markdown(content)

        if actual_model != expected_model:
            print(f"DRIFT: {entry.name}: model={actual_model!r} expected={expected_model!r}")
            all_ok = False
        if actual_variant != expected_variant:
            print(f"DRIFT: {entry.name}: variant={actual_variant!r} expected={expected_variant!r}")
            all_ok = False

    if all_ok:
        print("OK: all agent activation in sync with config")
        return 0
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Activate effective model config into target agent markdown files."
    )
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--target", default=None,
                              help="target agents directory")
    target_group.add_argument("--global", dest="global_install", action="store_true",
                              help="use ~/.config/opencode/agents/ (default)")
    parser.add_argument("--check", action="store_true",
                        help="compare effective config vs rendered frontmatter, exit 1 on drift")
    parser.add_argument("--dry-run", action="store_true",
                        help="report planned changes without writing files")
    args = parser.parse_args()

    if args.target:
        target = Path(args.target).resolve()
    else:
        target = _global_target()

    if not target.is_dir():
        print(f"ERROR: target directory not found: {target}", file=sys.stderr)
        print("Run install_agents.py first to set up the target.", file=sys.stderr)
        return 1

    if args.check:
        return do_check(target)

    return do_activate(target, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
