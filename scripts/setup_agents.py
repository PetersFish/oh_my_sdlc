#!/usr/bin/env python3
"""Aggregate agent setup entrypoint — template sync then activation.

Composes install_agents.py (canonical prompt + config template sync) followed by
activate_agents_config.py (effective model/variant rendering) in a single run.

Modes:
  (default)   Run template sync then activation for the target.
  --check     Report both template drift and activation drift.
  --dry-run   Report planned actions for both phases without modifying files.
  --force     Pass through to template sync for prompt overwrite.
  --activate-only  Skip template sync; run only activation (non-destructive config refresh).
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

# Dynamically import sibling scripts from the same directory
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import agent_config_lib  # noqa: E402

# Import sibling modules (these use the shared helper)
import install_agents  # noqa: E402
import activate_agents_config  # noqa: E402


def _canonical_source(script_dir: Path) -> Path:
    return (script_dir / ".." / "agents").resolve()


def _global_target() -> Path:
    return Path.home() / ".config" / "opencode" / "agents"


def do_setup_check(source: Path, target: Path) -> int:
    """Aggregate check: template drift + activation drift."""
    errors = 0

    # 1. Template sync check (normalized)
    rc_install = install_agents.do_check(source, target)
    if rc_install != 0:
        print("[setup] Template drift detected (see above)", file=sys.stderr)
        errors += 1

    # 2. Activation drift check
    rc_activate = activate_agents_config.do_check(target)
    if rc_activate != 0:
        print("[setup] Activation drift detected (see above)", file=sys.stderr)
        errors += 1

    if errors == 0:
        print("OK: setup in sync")
        return 0
    return 1


def do_setup(source: Path, target: Path, source_ref: str, source_repo: str,
             status: str, force: bool, dry_run: bool,
             activate_only: bool = False) -> int:
    """Aggregate setup: install then activate, or activate-only."""

    if activate_only:
        if dry_run:
            print("[setup] DRY-RUN: would activate only (skip template sync)")
            return activate_agents_config.do_activate(target, dry_run=True)
        print("[setup] Activate only (skip template sync)")
        return activate_agents_config.do_activate(target, dry_run=False)

    if dry_run:
        print("[setup] DRY-RUN: template sync would:")
        # Simulate install dry-run by checking what would happen
        src_files = install_agents._scan_dir(source)
        target.mkdir(parents=True, exist_ok=True)
        existing = [n for n in src_files if (target / n).exists()]
        for name in sorted(src_files):
            action = "overwrite" if name in existing else "install"
            print(f"  {name} ({action})")
        cfg_tgt = install_agents._target_config_path(target)
        cfg_src = install_agents._source_config_template(source)
        if cfg_src.is_file() and not cfg_tgt.is_file():
            print("  config/model-profiles.yaml (initialize)")

        print("[setup] DRY-RUN: activation would:")
        return activate_agents_config.do_activate(target, dry_run=True)

    # 1. Template sync
    rc_install = install_agents.do_install(
        source, target, source_repo, source_ref, status, force,
    )
    if rc_install != 0:
        print("[setup] Template sync failed — stopping", file=sys.stderr)
        return rc_install

    # 2. Activation
    print("[setup] Template sync complete; activating effective config...")
    rc_activate = activate_agents_config.do_activate(target, dry_run=False)
    return rc_activate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate agent setup: template sync then activation."
    )
    parser.add_argument("--source", default=None,
                        help="canonical agents/ directory (default: derived from script location)")
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--target", default=None,
                              help="target directory to set up agents in")
    target_group.add_argument("--global", dest="global_install", action="store_true",
                              help="set up ~/.config/opencode/agents/ (default)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing agent files during template sync")
    parser.add_argument("--check", action="store_true",
                        help="report template + activation drift (exit 1 on any drift)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report planned actions without modifying files")
    parser.add_argument("--activate-only", action="store_true",
                        help="skip template sync; run only activation (config refresh)")
    parser.add_argument("--source-ref", default=None,
                        help="git ref for metadata (default: auto-detect from HEAD)")
    parser.add_argument("--source-repo", default=None,
                        help="explicit source repo path for metadata (default: repo root above canonical agents/)")
    parser.add_argument("--status", default="stable",
                        help="install status tag for metadata (default: stable)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    source = Path(args.source).resolve() if args.source else _canonical_source(script_dir)

    if args.target:
        target = Path(args.target).resolve()
    else:
        target = _global_target()

    if not source.is_dir():
        print(f"ERROR: canonical source directory not found: {source}", file=sys.stderr)
        return 1

    repo_root = install_agents._source_repo_root(source)
    source_ref = args.source_ref or install_agents._git_source_ref(repo_root)
    source_repo = Path(args.source_repo).resolve() if args.source_repo else repo_root

    if args.check:
        return do_setup_check(source, target)

    return do_setup(
        source, target,
        source_ref=source_ref,
        source_repo=str(source_repo),
        status=args.status,
        force=args.force,
        dry_run=args.dry_run,
        activate_only=args.activate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
