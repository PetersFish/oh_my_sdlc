#!/usr/bin/env python3
"""Aggregate agent setup: install (template sync) then activate (render model/variant).

Provides a single user-facing entrypoint that composes install_agents.py and
activate_agents_config.py in order.  Supports unified --check, --dry-run, and
--force modes.

Modes:
  (default)   Install canonical prompts (template sync), then activate config.
  --check     Report both template drift and activation drift.
  --dry-run   Preview install and activation actions without writing files.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


INSTALL_SCRIPT = Path(__file__).resolve().parent / "install_agents.py"
ACTIVATE_SCRIPT = Path(__file__).resolve().parent / "activate_agents_config.py"

if not INSTALL_SCRIPT.is_file():
    print(f"ERROR: install script not found: {INSTALL_SCRIPT}", file=sys.stderr)
    sys.exit(1)
if not ACTIVATE_SCRIPT.is_file():
    print(f"ERROR: activate script not found: {ACTIVATE_SCRIPT}", file=sys.stderr)
    sys.exit(1)


def _global_target() -> Path:
    return Path.home() / ".config" / "opencode" / "agents"


def _run_script(script: Path, target: Path, extra_args: list[str]) -> tuple[int, str, str]:
    """Run a script with --target and capture output."""
    args = [
        sys.executable,
        str(script),
        "--target", str(target),
        *extra_args,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def do_setup(target: Path, force: bool = False, dry_run: bool = False) -> int:
    """Run install then activate for a target.

    Returns 0 on success, non-zero on failure."""
    # Step 1: Template sync (install)
    install_args = []
    if force:
        install_args.append("--force")
    if dry_run:
        # For dry-run, we run activate --dry-run but install has no dry-run mode.
        # We report what install would do by checking first, then plan activation.
        print("[DRY-RUN] would run install (template sync)")
        rc_install = 0
    else:
        rc_install, stdout_install, stderr_install = _run_script(
            INSTALL_SCRIPT, target, install_args
        )
        if stdout_install:
            print(stdout_install)
        if stderr_install:
            print(stderr_install, file=sys.stderr)
        if rc_install != 0:
            print("ERROR: install step failed", file=sys.stderr)
            return rc_install

    # Step 2: Activation
    activate_args = []
    if dry_run:
        activate_args.append("--dry-run")
    rc_activate, stdout_activate, stderr_activate = _run_script(
        ACTIVATE_SCRIPT, target, activate_args
    )
    if stdout_activate:
        print(stdout_activate)
    if stderr_activate:
        print(stderr_activate, file=sys.stderr)

    if rc_activate != 0 and not dry_run:
        print("ERROR: activation step failed", file=sys.stderr)

    return rc_activate if not dry_run else 0


def do_check(target: Path) -> int:
    """Run install --check and activate --check. Exit 1 if either reports drift."""
    overall = 0

    # Template drift check
    rc_install, stdout_install, stderr_install = _run_script(
        INSTALL_SCRIPT, target, ["--check"]
    )
    if stdout_install:
        print(stdout_install)
    if stderr_install:
        print(stderr_install, file=sys.stderr)

    if rc_install != 0:
        print("--- template drift detected (install --check) ---")
        overall = 1

    # Activation drift check
    rc_activate, stdout_activate, stderr_activate = _run_script(
        ACTIVATE_SCRIPT, target, ["--check"]
    )
    if stdout_activate:
        print(stdout_activate)
    if stderr_activate:
        print(stderr_activate, file=sys.stderr)

    if rc_activate != 0:
        print("--- activation drift detected (activate --check) ---")
        overall = 1

    if overall == 0:
        print("OK: agents fully in sync")
    return overall


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate agent setup: install (template sync) then activate (render model/variant)."
    )
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--target", default=None,
                              help="target agents directory")
    target_group.add_argument("--global", dest="global_install", action="store_true",
                              help="use ~/.config/opencode/agents/ (default)")
    parser.add_argument("--force", action="store_true",
                        help="force overwrite existing agent files during install")
    parser.add_argument("--check", action="store_true",
                        help="report template drift and activation drift, exit 1 on either")
    parser.add_argument("--dry-run", action="store_true",
                        help="preview planned install and activation actions without writing files")
    args = parser.parse_args()

    if args.target:
        target = Path(args.target).resolve()
    else:
        target = _global_target()

    if args.check:
        return do_check(target)

    return do_setup(target, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
