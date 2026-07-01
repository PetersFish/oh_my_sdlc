#!/usr/bin/env python3
"""Install OpenCode agent files from canonical source to a target directory.

Canonical source: agents/ (relative to this script)
Target: --global => ~/.config/opencode/agents/ (default), --target <dir>

This script handles TEMPLATE SYNC only — it copies canonical prompts and the
config template but never renders activation-managed ``model`` / ``variant``
frontmatter fields.  Activation is a separate step (activate_agents_config.py).

Modes:
  (default)   Install agent markdown + config template to target.
  --check     Compare canonical vs target using normalized content (ignores
              model/variant), exit 0 if in sync, exit 1 on drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent_config_lib import (
    MODEL_PROFILES_FILENAME,
    CONFIG_SUBDIR,
    SKIP_NAMES,
    SKIP_SUFFIXES,
    scan_agent_markdown_files,
    normalized_prompt_compare,
    get_target_config_path,
)


def _canonical_source(script_dir: Path) -> Path:
    return (script_dir / ".." / "agents").resolve()


def _canonical_config_template(source: Path) -> Path:
    """Return path to the canonical config template, or None if missing."""
    path = source / CONFIG_SUBDIR / MODEL_PROFILES_FILENAME
    return path if path.is_file() else None


def _source_repo_root(source: Path) -> Path:
    return source.parent.resolve()


def _git_source_ref(repo_root: Path) -> str:
    """Get the HEAD commit hash for the source repo, or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _read_file(path: Path) -> str:
    """Read file content as text."""
    return path.read_text(encoding="utf-8")


def _write_metadata(target: Path, source_repo: str, source_ref: str,
                    status: str, files: dict[str, str]) -> None:
    metadata = {
        "source_repo": source_repo,
        "source_ref": source_ref,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "files": files,
    }
    (target / ".agent-install.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _global_target() -> Path:
    return Path.home() / ".config" / "opencode" / "agents"


# ---- guardrail for known CLI targets ----

_KNOWN_CLI_TARGET_SUFFIXES = (
    ".opencode/agents",
    ".opencode/agent",
    ".claude/agents",
    ".claude/agent",
    ".cursor/agents",
    ".cursor/agent",
)


def _is_known_cli_target(target: Path) -> bool:
    """Detect whether a target path looks like a real CLI agent directory.

    These targets require activation (model/variant rendering) after template
    sync.  Direct install without activation would silently wipe model config."""
    target_str = str(target)
    global_dir = str(Path.home() / ".config" / "opencode" / "agents")
    if target_str == global_dir:
        return True
    for suffix in _KNOWN_CLI_TARGET_SUFFIXES:
        if target_str.endswith(suffix) or target_str.endswith(suffix + "/"):
            return True
    return False


# ---- check mode (normalized) ----

def _check_target_config(target: Path) -> tuple[bool, list[str]]:
    """Verify that the target has an effective config initialized.

    Returns (ok, messages)."""
    config_path = get_target_config_path(target)
    if not config_path.is_file():
        return False, [f"target config missing: {config_path}"]
    return True, []


def do_check(source: Path, target: Path) -> int:
    """Compare canonical vs target using normalized content (ignore model/variant)."""
    src_dir = source
    tgt_dir = target

    if not src_dir.is_dir():
        print("ERROR: canonical source directory not found", file=sys.stderr)
        return 1

    # Read source files
    src_files: dict[str, str] = {}
    for name in sorted(src_dir.iterdir()):
        if name.name in SKIP_NAMES:
            continue
        if name.name.endswith(SKIP_SUFFIXES):
            continue
        if name.is_file() and name.suffix == ".md":
            src_files[name.name] = _read_file(name)

    if not src_files:
        print("WARNING: canonical source has no .md files", file=sys.stderr)
        return 0

    # Read target files
    tgt_files: dict[str, str] = {}
    if tgt_dir.is_dir():
        for entry in sorted(tgt_dir.iterdir()):
            if entry.name in SKIP_NAMES:
                continue
            if entry.name.endswith(SKIP_SUFFIXES):
                continue
            if entry.is_file() and entry.suffix == ".md":
                tgt_files[entry.name] = _read_file(entry)

    all_ok = True

    # Check each source file against target using normalized comparison
    for name, src_content in src_files.items():
        tgt_content = tgt_files.get(name)
        if tgt_content is None:
            print(f"DRIFT: {name} (missing)")
            all_ok = False
        elif not normalized_prompt_compare(src_content, tgt_content):
            print(f"DRIFT: {name} (changed)")
            all_ok = False

    # Check for extra files in target not in source
    for name in tgt_files:
        if name not in src_files:
            print(f"DRIFT: {name} (extra — not in canonical)")
            all_ok = False

    # Check target config exists
    config_ok, config_msgs = _check_target_config(target)
    if not config_ok:
        for msg in config_msgs:
            print(f"DRIFT: {msg}")
            all_ok = False

    if all_ok:
        print("OK: all agents in sync")
        return 0
    return 1


# ---- install mode ----

def _copy_config_template(source: Path, target: Path) -> tuple[bool, str]:
    """Copy canonical config template to target config path if it does not exist.

    Returns (copied, message)."""
    config_template = _canonical_config_template(source)
    if config_template is None:
        return False, "no canonical config template found"

    target_config = get_target_config_path(target)
    if target_config.is_file():
        return False, f"target config already exists, preserved: {target_config}"

    target_config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(config_template), str(target_config))
    return True, f"config template initialized: {target_config}"


def do_install(source: Path, target: Path, source_repo: str, source_ref: str,
               status: str, force: bool) -> int:
    """Install canonical agent markdown files to target (template sync only).

    Also initializes the target config template if missing.  Activation-managed
    fields (model/variant) are never injected by this step."""
    src_dir = source
    tgt_dir = target

    if not src_dir.is_dir():
        print("ERROR: canonical source directory not found", file=sys.stderr)
        print("Is this script inside the oh_my_skills repo?", file=sys.stderr)
        return 1

    # Collect source .md files (top-level only)
    src_files: dict[str, Path] = {}
    for entry in sorted(src_dir.iterdir()):
        if entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith(SKIP_SUFFIXES):
            continue
        if entry.is_file() and entry.suffix == ".md":
            src_files[entry.name] = entry

    if not src_files:
        print("WARNING: no .md files found in canonical source", file=sys.stderr)
        return 0

    tgt_dir.mkdir(parents=True, exist_ok=True)

    # Check for pre-existing agent files
    existing_conflicts = [
        name for name in src_files if (tgt_dir / name).exists()
    ]
    if existing_conflicts and not force:
        print("ERROR: target already contains agent files. Re-run with --force to overwrite:", file=sys.stderr)
        for name in existing_conflicts:
            print(f"  - {name}", file=sys.stderr)
        return 1

    # Copy agent markdown files
    installed: dict[str, str] = {}
    for name, src_path in src_files.items():
        tgt_path = tgt_dir / name
        action = "overwritten" if tgt_path.exists() else "installed"
        shutil.copy2(str(src_path), str(tgt_path))
        # Hash the installed file for metadata
        installed[name] = hashlib.sha256(tgt_path.read_bytes()).hexdigest()
        print(f"INSTALLED: {name} ({action})")

    # Initialize target config template if missing (preserve existing)
    copied, config_msg = _copy_config_template(src_dir, tgt_dir)
    if copied:
        print(config_msg)

    _write_metadata(tgt_dir, source_repo, source_ref, status, installed)
    return 0


# ---- main ----

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install OpenCode agent files from canonical source to target (template sync only)."
    )
    parser.add_argument("--source", default=None,
                        help="canonical agents/ directory (default: derived from script location)")
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--target", default=None,
                              help="target directory to install agents into")
    target_group.add_argument("--global", dest="global_install", action="store_true",
                              help="install to ~/.config/opencode/agents/ (default)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing agent files")
    parser.add_argument("--check", action="store_true",
                        help="compare canonical vs target (normalized), exit 1 on drift (no copy)")
    parser.add_argument("--install-only", action="store_true",
                        help="allow install to known CLI targets without activation (use setup_agents.py instead)")
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
        print("Is this script inside the oh_my_skills repo?", file=sys.stderr)
        return 1

    repo_root = _source_repo_root(source)
    source_ref = args.source_ref or _git_source_ref(repo_root)
    source_repo = str(Path(args.source_repo).resolve()) if args.source_repo else str(repo_root)

    if args.check:
        return do_check(source, target)

    if not args.install_only and _is_known_cli_target(target):
        print(f"ERROR: target looks like a real CLI agent directory: {target}", file=sys.stderr)
        print("Direct install would wipe activated model/variant config.", file=sys.stderr)
        print("Use setup_agents.py instead (install + activation):", file=sys.stderr)
        print(f"  python3 scripts/setup_agents.py --target {args.target or '--global'} --force", file=sys.stderr)
        print("Or pass --install-only to skip activation (template sync only).", file=sys.stderr)
        return 1

    return do_install(source, target, source_repo, source_ref, args.status, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
