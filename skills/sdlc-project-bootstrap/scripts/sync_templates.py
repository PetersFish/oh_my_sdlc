#!/usr/bin/env python3
"""Sync live .ai/workflows/ files to canonical skill templates, and manage
distribution across project-level AI CLI skill directories.

Governed files (live -> canonical template):
  .ai/workflows/scripts/workflow.py    -> <templates>/workflow/workflow.py
  .ai/workflows/definitions/sdlc-main.yaml -> <templates>/workflow/sdlc-main.yaml

Distribution targets (canonical -> project-level copies):
  skills/sdlc-project-bootstrap/templates/  (canonical)
    -> .opencode/skills/sdlc-project-bootstrap/templates/
    -> .claude/skills/sdlc-project-bootstrap/templates/
    -> .cursor/skills/sdlc-project-bootstrap/templates/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

GOVERNED = [
    (".ai/workflows/scripts/workflow.py", "workflow/workflow.py"),
    (".ai/workflows/definitions/sdlc-main.yaml", "workflow/sdlc-main.yaml"),
]

# Project-level distributed skill directories (canonical -> these)
DISTRIBUTED_DIRS = [
    ".opencode/skills/sdlc-project-bootstrap/templates",
    ".claude/skills/sdlc-project-bootstrap/templates",
    ".cursor/skills/sdlc-project-bootstrap/templates",
]

SKILL_NAME = "sdlc-project-bootstrap"
TEMPLATES_SUBDIR = "templates"


def _hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_templates_dir(root: Path) -> Path:
    """Return the canonical templates directory: skills/sdlc-project-bootstrap/templates."""
    return root / "skills" / SKILL_NAME / TEMPLATES_SUBDIR


def _default_templates_dir(root: Path) -> str:
    return str(_canonical_templates_dir(root))


def check_drift(root: Path, templates: Path) -> tuple[list[str], list[str]]:
    drifted = []
    in_sync = []
    for live_rel, tmpl_rel in GOVERNED:
        live = root / live_rel
        tmpl = templates / tmpl_rel
        if _hash(live) != _hash(tmpl):
            drifted.append(f"{live_rel} -> {tmpl_rel}")
        else:
            in_sync.append(f"{live_rel} -> {tmpl_rel}")
    return drifted, in_sync


def sync_files(root: Path, templates: Path) -> tuple[list[str], list[str]]:
    synced = []
    unchanged = []
    for live_rel, tmpl_rel in GOVERNED:
        live = root / live_rel
        tmpl = templates / tmpl_rel
        if not live.exists():
            print(f"WARNING: live file not found: {live}", file=sys.stderr)
            continue
        if _hash(live) != _hash(tmpl):
            tmpl.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(live), str(tmpl))
            synced.append(f"{live_rel} -> {tmpl_rel}")
        else:
            unchanged.append(f"{live_rel} -> {tmpl_rel}")
    return synced, unchanged


def check_distributed(root: Path, templates: Path) -> tuple[list[str], list[str]]:
    drifted = []
    in_sync = []
    for live_rel, tmpl_rel in GOVERNED:
        canonical = templates / tmpl_rel
        if not canonical.exists():
            drifted.append(f"canonical missing: {tmpl_rel}")
            continue
        canonical_hash = _hash(canonical)
        for dist_dir_rel in DISTRIBUTED_DIRS:
            dist_file = root / dist_dir_rel / tmpl_rel
            if not dist_file.exists():
                drifted.append(f"{dist_dir_rel}/{tmpl_rel} (missing)")
            elif _hash(dist_file) != canonical_hash:
                drifted.append(f"{dist_dir_rel}/{tmpl_rel}")
            else:
                in_sync.append(f"{dist_dir_rel}/{tmpl_rel}")
    return drifted, in_sync


def distribute_to_all(root: Path, templates: Path) -> tuple[list[str], list[str]]:
    synced = []
    unchanged = []
    for live_rel, tmpl_rel in GOVERNED:
        canonical = templates / tmpl_rel
        if not canonical.exists():
            print(f"WARNING: canonical file not found: {canonical}", file=sys.stderr)
            continue
        for dist_dir_rel in DISTRIBUTED_DIRS:
            dist_file = root / dist_dir_rel / tmpl_rel
            if not dist_file.exists() or _hash(dist_file) != _hash(canonical):
                dist_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(canonical), str(dist_file))
                synced.append(f"{dist_dir_rel}/{tmpl_rel}")
            else:
                unchanged.append(f"{dist_dir_rel}/{tmpl_rel}")
    return synced, unchanged


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync live .ai/workflows/ files to canonical skill templates, "
                    "and manage distribution across CLI skill directories"
    )
    parser.add_argument("--root", default=".", help="repository root path")
    parser.add_argument("--templates", default=None,
                        help="path to templates/ directory (default: canonical skills/sdlc-project-bootstrap/templates)")
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if live != canonical (read-only)")
    parser.add_argument("--check-distributed", action="store_true",
                        help="exit non-zero if canonical != distributed copies (read-only)")
    parser.add_argument("--distribute", action="store_true",
                        help="push canonical templates to all project-level distributed copies")
    parser.add_argument("--json", action="store_true",
                        help="output report as JSON")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    templates = Path(args.templates).resolve() if args.templates else Path(_default_templates_dir(root))

    if not templates.exists():
        report = {"error": f"templates directory not found: {templates}"}
        print(json.dumps(report, indent=2) if args.json else report["error"], file=sys.stderr)
        return 2

    if args.check:
        drifted, in_sync = check_drift(root, templates)
        if args.json:
            print(json.dumps({"drifted": drifted, "in_sync": in_sync}, indent=2))
        else:
            if drifted:
                for d in drifted:
                    print(f"DRIFT: {d}")
            else:
                print("OK: all governed files in sync with canonical")
        return 1 if drifted else 0

    if args.check_distributed:
        drifted, in_sync = check_distributed(root, templates)
        if args.json:
            print(json.dumps({"drifted": drifted, "in_sync": in_sync}, indent=2))
        else:
            if drifted:
                for d in drifted:
                    print(f"DRIFT: {d}")
            else:
                print("OK: all distributed copies match canonical")
        return 1 if drifted else 0

    if args.distribute:
        synced, unchanged = distribute_to_all(root, templates)
        report = {"synced": synced, "unchanged": unchanged}
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for s in synced:
                print(f"DISTRIBUTED: {s}")
            for u in unchanged:
                print(f"OK: {u}")
            if not synced:
                print("All distributed copies already in sync")
        return 0

    # Default behavior: sync live -> canonical
    synced, unchanged = sync_files(root, templates)
    report = {"synced": synced, "unchanged": unchanged}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if synced:
            for s in synced:
                print(f"SYNCED: {s}")
        if unchanged:
            for u in unchanged:
                print(f"OK: {u}")
        if not synced:
            print("All governed files already in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
