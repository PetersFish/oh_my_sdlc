#!/usr/bin/env python3
"""Stub sync_derived_artifacts.py for pre-commit hook / policy test fixtures.

Provides two behaviors so tests get evidence_ok=True from the policy's
sync-check subprocess while still allowing evaluate_policy to import the
module for path attribution:

1. CLI: ``python3 sync_derived_artifacts.py --check --json`` emits
   ``{"status": "ok", "suites": []}`` — valid structured output with no
   stale paths.
2. Import: exposes ``classify_changes`` and ``Affected`` mirroring the
   real module's interface used by ``derived_sync_hook_policy.py``.

This avoids the need for a full repository fixture with all distribution
targets and dependent scripts just to exercise the policy's allow/defer
logic.
"""
from __future__ import annotations

import argparse
import json
import sys


class Affected:
    """Minimal Affected class mirroring the real module's interface.

    Uses a plain class (not @dataclass) to avoid Python 3.14 dataclass
    issues when loaded via importlib.util without sys.modules registration.
    """

    def __init__(self):
        self.agents = set()
        self.skills = set()
        self.workflows = set()
        self.full = False
        self.skipped_paths = []
        self.staged_canonical_paths = []
        self.reason = None


def _normalize_path(path: str) -> str:
    p = path.replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return p


def classify_changes(changed_files: list[str]) -> Affected:
    """Minimal classifier: mark agents/skills/workflows domains."""
    affected = Affected()
    for raw in changed_files:
        p = _normalize_path(raw)
        if not p:
            continue
        if p.startswith("agents/"):
            affected.agents.add(p)
            affected.staged_canonical_paths.append(p)
        elif p.startswith("skills/"):
            skill_name = p.split("/")[1] if "/" in p else ""
            if skill_name:
                affected.skills.add(skill_name)
            affected.staged_canonical_paths.append(p)
        elif p.startswith(".ai/workflows/scripts/") or p.startswith(".ai/workflows/definitions/"):
            affected.workflows.add(p)
            affected.staged_canonical_paths.append(p)
        else:
            affected.skipped_paths.append(p)
    return affected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--changed-files-from-git", action="store_true")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    report = {"status": "ok", "suites": [], "scope": "full"}
    if args.json:
        json.dump(report, sys.stdout)
    else:
        print("OK: stub sync_derived_artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())