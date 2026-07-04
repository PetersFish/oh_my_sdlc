#!/usr/bin/env python3
"""Repository-scoped safe deletion helper for agent automation.

Accepts repository-relative paths only. Rejects absolute paths, paths
that escape the repository root, and protected locations (.git/, .ai/memory/).
Default mode deletes files only; --recursive is required for directories.

Emits JSON with arrays for ``deleted``, ``skipped``, and ``refused`` paths.
Exit code is 0 when nothing was refused, 1 when any path was refused.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROTECTED_PREFIXES = (Path(".git"), Path(".ai/memory"))


def resolve_repo_path(root: Path, raw: str) -> Path:
    """Resolve a raw path string into a safe in-repo absolute path.

    Raises ValueError with a stable reason code:
      - absolute_path_forbidden
      - path_escape_forbidden
      - protected_path
    """
    rel = Path(raw)
    if rel.is_absolute():
        raise ValueError("absolute_path_forbidden")
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path_escape_forbidden")
    repo_rel = candidate.relative_to(root)
    for prefix in PROTECTED_PREFIXES:
        if repo_rel == prefix or prefix in repo_rel.parents:
            raise ValueError("protected_path")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repository-scoped safe deletion helper."
    )
    parser.add_argument("paths", nargs="+", help="repository-relative paths to delete")
    parser.add_argument("--root", default=".", help="repository root path")
    parser.add_argument("--recursive", action="store_true",
                        help="required to delete directories")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report: dict = {"deleted": [], "skipped": [], "refused": []}

    for raw in args.paths:
        try:
            target = resolve_repo_path(root, raw)
        except ValueError as exc:
            report["refused"].append({"path": raw, "reason": str(exc)})
            continue

        if not target.exists():
            report["skipped"].append({"path": raw, "reason": "missing"})
            continue
        if target.is_dir() and not args.recursive:
            report["refused"].append({"path": raw, "reason": "recursive_required"})
            continue
        if target.is_dir():
            shutil.rmtree(target)
            report["deleted"].append({"path": raw, "kind": "directory"})
        else:
            target.unlink()
            report["deleted"].append({"path": raw, "kind": "file"})

    print(json.dumps(report, indent=2))
    return 1 if report["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())