#!/usr/bin/env python3
"""Activate effective per-agent model/variant from target config into markdown frontmatter.

Loads <target>/config/model-profiles.yaml, resolves each agent's effective model and
variant, and writes those values into the target markdown frontmatter via the shared
agent_config_lib helper.

Modes:
  (default)   Activate all agent *.md files in target.
  --check     Report activation drift (exit 1 when markdown does not match effective config).
  --dry-run   Report planned activation actions without modifying files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import agent_config_lib


def _target_config(target: Path) -> Path:
    return target / "config" / "model-profiles.yaml"


def _global_target() -> Path:
    return Path.home() / ".config" / "opencode" / "agents"


def _agent_files(target: Path) -> list[Path]:
    """Return sorted list of *.md agent files in target (excluding hidden/metadata)."""
    if not target.is_dir():
        return []
    result: list[Path] = []
    for entry in sorted(target.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_file() and entry.suffix == ".md":
            result.append(entry)
    return result


def _should_render(target_path: Path, config: dict) -> str | None:
    """Compute what the resolved model/variant should be for target_path.

    Returns the expected full content with activation applied, or None
    if the agent is not found in config.
    """
    agent_name = target_path.stem  # e.g., "implement-agent" from "implement-agent.md"
    try:
        model = agent_config_lib.resolve_model(config, agent_name)
        variant = agent_config_lib.resolve_variant(config, agent_name)
    except KeyError:
        return None  # agent not in config — skip

    current = target_path.read_text(encoding="utf-8")
    return agent_config_lib.update_frontmatter(current, model, variant)


def do_check(target: Path) -> int:
    """Check activation drift: compare current markdown vs what effective config prescribes."""
    cfg_path = _target_config(target)
    if not cfg_path.is_file():
        print("DRIFT: config/model-profiles.yaml (missing)", file=sys.stderr)
        return 1

    config = agent_config_lib.load_config(cfg_path)
    errors = agent_config_lib.validate_config(config)
    if errors:
        for e in errors:
            print(f"DRIFT: invalid config — {e}", file=sys.stderr)
        return 1

    all_ok = True
    for agent_file in _agent_files(target):
        expected = _should_render(agent_file, config)
        if expected is None:
            continue  # agent not in config — nothing to check
        current = agent_file.read_text(encoding="utf-8")
        if current != expected:
            print(f"DRIFT: {agent_file.name} (activation out of sync)")
            all_ok = False

    if all_ok:
        print("OK: activation in sync")
        return 0
    return 1


def do_activate(target: Path, dry_run: bool = False) -> int:
    """Activate: write effective model/variant into each agent markdown file."""
    cfg_path = _target_config(target)
    if not cfg_path.is_file():
        print(f"ERROR: target config not found at {cfg_path}", file=sys.stderr)
        print("Run install_agents.py first to initialize the target config.", file=sys.stderr)
        return 1

    config = agent_config_lib.load_config(cfg_path)
    errors = agent_config_lib.validate_config(config)
    if errors:
        for e in errors:
            print(f"ERROR: invalid config — {e}", file=sys.stderr)
        return 1

    activated = 0
    for agent_file in _agent_files(target):
        expected = _should_render(agent_file, config)
        if expected is None:
            continue  # agent not in config

        current = agent_file.read_text(encoding="utf-8")
        if current == expected:
            print(f"SKIP: {agent_file.name} (already up to date)")
            continue

        if dry_run:
            print(f"WOULD ACTIVATE: {agent_file.name}")
        else:
            agent_file.write_text(expected, encoding="utf-8")
            print(f"ACTIVATED: {agent_file.name}")
        activated += 1

    if activated == 0 and not dry_run:
        print("OK: all agents already up to date")
    elif dry_run and activated > 0:
        print(f"DRY-RUN: {activated} agent(s) would be activated")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Activate effective per-agent model/variant from target config into markdown."
    )
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--target", default=None,
                              help="target agent directory")
    target_group.add_argument("--global", dest="global_install", action="store_true",
                              help="activate ~/.config/opencode/agents/ (default)")
    parser.add_argument("--check", action="store_true",
                        help="report activation drift (exit 1 when out of sync)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report planned actions without modifying files")
    args = parser.parse_args()

    if args.target:
        target = Path(args.target).resolve()
    else:
        target = _global_target()

    if not target.is_dir():
        print(f"ERROR: target directory not found: {target}", file=sys.stderr)
        return 1

    if args.check:
        return do_check(target)

    return do_activate(target, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
