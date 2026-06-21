#!/usr/bin/env python3
"""Initialize .ai/workflows/ runtime directory structure in a project.

Creates the directory layout and copies workflow.py and sdlc-main.yaml
from sdlc-project-bootstrap skill templates. Idempotent — safe to run
multiple times.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

DIRS = [
    ".ai/workflows/definitions",
    ".ai/workflows/runs",
    ".ai/workflows/runs/history",
    ".ai/workflows/scripts",
]

COPIES = [
    ("workflow/workflow.py", ".ai/workflows/scripts/workflow.py"),
    ("workflow/sdlc-main.yaml", ".ai/workflows/definitions/sdlc-main.yaml"),
]


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize .ai/workflows/ runtime structure"
    )
    parser.add_argument("--root", default=".", help="repository root path")
    parser.add_argument("--templates", default=None,
                        help="path to templates/ directory (default: derived from script location)")
    parser.add_argument("--json", action="store_true",
                        help="output report as JSON")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    templates = Path(args.templates).resolve() if args.templates else _templates_dir()

    created: list[str] = []
    already_present: list[str] = []

    for d in DIRS:
        p = root / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(f"{d}/")
        else:
            already_present.append(f"{d}/")

    for tmpl_rel, live_rel in COPIES:
        src = templates / tmpl_rel
        dst = root / live_rel
        if not src.exists():
            print(f"ERROR: template not found: {src}", file=sys.stderr)
            return 2
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            created.append(live_rel)
        else:
            already_present.append(live_rel)

    report = {"created": created, "already_present": already_present}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in created:
            print(f"CREATED: {item}")
        for item in already_present:
            print(f"SKIPPED (already present): {item}")
        if not created:
            print("All foundations already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
