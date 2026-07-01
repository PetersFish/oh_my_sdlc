#!/usr/bin/env python3
"""Install OpenCode agent files from canonical source to a target directory.

Canonical source: agents/ (relative to this script)
Target: --global => ~/.config/opencode/agents/ (default), --target <dir>

Template-sync semantics:
- Copies canonical *.md prompts verbatim (model-agnostic).
- Copies canonical config template to <target>/config/model-profiles.yaml
  only when the target config does not already exist (preserves user edits).
- --check compares normalized content (ignoring activation-managed model/variant)
  and also verifies the target config exists.

Modes:
  (default)   Install agents to target, writing .agent-install.json metadata.
  --check     Compare canonical vs target: exit 0 if in sync, exit 1 on drift.
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

# Shared helper from the same scripts/ directory
import agent_config_lib

SKIP_NAMES = {".agent-install.json", ".DS_Store"}
SKIP_SUFFIXES = (".pyc",)
CONFIG_TEMPLATE_NAME = "model-profiles.yaml"
CONFIG_SUBDIR = "config"


def _canonical_source(script_dir: Path) -> Path:
    return (script_dir / ".." / "agents").resolve()


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


def _scan_dir(directory: Path, normalize: bool = False) -> dict[str, str]:
    """Scan directory for *.md files, returning {filename: sha256}.

    When normalize=True, hashes are computed on content with model/variant
    stripped (activation-managed fields ignored).
    """
    files: dict[str, str] = {}
    if not directory.is_dir():
        return files
    for entry in sorted(directory.iterdir()):
        if entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith(SKIP_SUFFIXES):
            continue
        if entry.is_file() and entry.suffix == ".md":
            raw = entry.read_bytes()
            if normalize:
                text = raw.decode("utf-8")
                text = agent_config_lib.normalized_content(text)
                raw = text.encode("utf-8")
            files[entry.name] = hashlib.sha256(raw).hexdigest()
    return files


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


# ---------------------------------------------------------------------------
# Config template helpers
# ---------------------------------------------------------------------------

def _source_config_template(source: Path) -> Path:
    """Path to the canonical config template under source/."""
    return source / CONFIG_SUBDIR / CONFIG_TEMPLATE_NAME


def _target_config_path(target: Path) -> Path:
    """Path to the target effective config."""
    return target / CONFIG_SUBDIR / CONFIG_TEMPLATE_NAME


def _init_target_config(source: Path, target: Path) -> bool:
    """Copy canonical config template to target if target config does not exist.

    Returns True if config was copied, False if it already existed (preserved).
    """
    src_cfg = _source_config_template(source)
    tgt_cfg = _target_config_path(target)

    if tgt_cfg.exists():
        return False  # preserve existing target config

    if not src_cfg.is_file():
        return False  # no canonical template to copy

    tgt_cfg.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src_cfg), str(tgt_cfg))
    return True


def do_check(source: Path, target: Path) -> int:
    """Compare canonical vs target using normalized content (ignores model/variant).

    Also verifies the target config exists.
    """
    src_files = _scan_dir(source, normalize=True)
    tgt_files = _scan_dir(target, normalize=True)

    if not src_files:
        print("WARNING: canonical source has no .md files", file=sys.stderr)
        return 0

    all_ok = True

    # Check prompt files
    for name, src_hash in src_files.items():
        tgt_hash = tgt_files.get(name)
        if tgt_hash is None:
            print(f"DRIFT: {name} (missing)")
            all_ok = False
        elif tgt_hash != src_hash:
            print(f"DRIFT: {name} (changed)")
            all_ok = False

    for name in tgt_files:
        if name not in src_files:
            print(f"DRIFT: {name} (extra — not in canonical)")
            all_ok = False

    # Check target config exists
    tgt_cfg = _target_config_path(target)
    src_cfg = _source_config_template(source)
    if src_cfg.is_file() and not tgt_cfg.is_file():
        print("DRIFT: config/model-profiles.yaml (missing — target config not initialized)")
        all_ok = False

    if all_ok:
        print("OK: all agents in sync")
        return 0
    return 1


def do_install(source: Path, target: Path, source_repo: str, source_ref: str,
               status: str, force: bool) -> int:
    src_files = _scan_dir(source)

    if not src_files:
        print("WARNING: no .md files found in canonical source", file=sys.stderr)
        return 0

    target.mkdir(parents=True, exist_ok=True)

    existing_conflicts = [name for name in src_files if (target / name).exists()]
    if existing_conflicts and not force:
        print("ERROR: target already contains agent files. Re-run with --force to overwrite:", file=sys.stderr)
        for name in existing_conflicts:
            print(f"  - {name}", file=sys.stderr)
        return 1

    installed: dict[str, str] = {}
    for name, src_hash in src_files.items():
        src_path = source / name
        tgt_path = target / name
        action = "overwritten" if tgt_path.exists() else "installed"
        shutil.copy2(str(src_path), str(tgt_path))
        installed[name] = src_hash
        print(f"INSTALLED: {name} ({action})")

    # Initialize target config if missing
    cfg_copied = _init_target_config(source, target)
    if cfg_copied:
        print("INSTALLED: config/model-profiles.yaml (initialized)")

    _write_metadata(target, source_repo, source_ref, status, installed)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install OpenCode agent files from canonical source to target."
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
                        help="compare canonical vs target, exit 1 on drift (no copy)")
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
    source_repo = Path(args.source_repo).resolve() if args.source_repo else repo_root

    if args.check:
        return do_check(source, target)

    return do_install(source, target, str(source_repo), source_ref, args.status, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
