#!/usr/bin/env python3
"""Idempotent workspace hydration for required runtime fixture directories.

Creates only the non-Git runtime fixture directories that tests require.
Does NOT copy or create workflow run state under the worktree.

Usage:

    python3 .ai/workflows/scripts/hydrate_workspace.py --root <worktree_path>
    python3 .ai/workflows/scripts/hydrate_workspace.py --root <worktree_path> --validate

The script discovers eval target manifests under
``<root>/.ai/evals/targets/*/manifest.yaml`` and creates the
``canonical_case_directories`` declared in each manifest. It is idempotent:
running it repeatedly is safe and reports only newly-created directories.

Forbidden paths (never created by hydration):

    .ai/workflows/runs/active
    .ai/workflows/runs/current.json
    .ai/workflows/runs/history
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


FORBIDDEN_PATHS = {
    ".ai/workflows/runs/active",
    ".ai/workflows/runs/current.json",
    ".ai/workflows/runs/history",
}

DEFAULT_CASE_DIRS = ("cases/inbox", "cases/accepted", "cases/rejected")


def _load_yaml(path: Path) -> dict | None:
    if yaml is None:
        # Fallback: minimal YAML parsing for the keys we need
        # This is a last-resort parser; prefer PyYAML.
        try:
            import importlib
            mod = importlib.import_module("yaml")
            return mod.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def discover_eval_targets(root: Path) -> list[Path]:
    """Discover eval target directories that contain a manifest.yaml."""
    targets_dir = root / ".ai" / "evals" / "targets"
    if not targets_dir.is_dir():
        return []
    return sorted(d for d in targets_dir.iterdir() if d.is_dir() and (d / "manifest.yaml").is_file())


def get_required_case_dirs(manifest: dict) -> list[str]:
    """Extract required case subdirectories from a target manifest."""
    canonical = manifest.get("canonical_case_directories", {})
    if isinstance(canonical, dict):
        dirs = [v for v in canonical.values() if isinstance(v, str)]
        if dirs:
            return dirs
    # Fallback to default case directories
    return list(DEFAULT_CASE_DIRS)


def hydrate(root: Path, validate_only: bool = False) -> tuple[int, list[str], list[str]]:
    """Hydrate required runtime fixture directories.

    Returns (returncode, created_paths, report_messages).
    """
    created: list[str] = []
    messages: list[str] = []

    targets = discover_eval_targets(root)
    if not targets:
        messages.append("no eval targets found; nothing to hydrate")
        return 0, created, messages

    for target_dir in targets:
        manifest_path = target_dir / "manifest.yaml"
        manifest = _load_yaml(manifest_path)
        if manifest is None:
            messages.append(f"WARNING: could not parse {manifest_path}; skipping")
            continue

        target_id = manifest.get("target_id", target_dir.name)
        case_dirs = get_required_case_dirs(manifest)

        for subdir in case_dirs:
            path = target_dir / subdir
            if path.exists():
                messages.append(f"exists: {path.relative_to(root)}")
                continue
            if validate_only:
                messages.append(f"MISSING (validate): {path.relative_to(root)}")
                continue
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path.relative_to(root)))
            messages.append(f"created: {path.relative_to(root)}")

    # Safety check: ensure no forbidden paths were created
    for forbidden in FORBIDDEN_PATHS:
        fpath = root / forbidden
        if fpath.exists():
            messages.append(f"WARNING: forbidden path exists: {forbidden}")

    rc = 0 if created or not validate_only else 0
    if validate_only and any("MISSING" in m for m in messages):
        rc = 1

    return rc, created, messages


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Idempotent workspace hydration for required runtime fixture directories."
    )
    parser.add_argument("--root", default=".", help="repository/worktree root path")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="validate hydration state without creating directories (non-zero if missing)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    rc, created, messages = hydrate(root, validate_only=args.validate)

    for msg in messages:
        print(msg)

    if created:
        print(f"\nHydrated {len(created)} director{'y' if len(created) == 1 else 'ies'}")
    elif not args.validate:
        print("\nHydration complete: all required directories already present")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())