#!/usr/bin/env python3
"""Check that canonical skills/<name>/ match project-level distributed copies.

Compares full directory trees (SKILL.md, scripts/, templates/, schemas/)
between canonical skills/ and .opencode/, .claude/, .cursor/ skill copies.
Ignores .skill-install.json (distribution metadata, not source content).

Exit 0 when all copies match. Exit 1 + DRIFT lines when drift is found.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

DISTRIBUTED_DIRS = [
    ".opencode/skills",
    ".claude/skills",
    ".cursor/skills",
]

CANONICAL_DIR = "skills"

IGNORE_FILES = {".skill-install.json"}


def digest_tree(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.is_dir():
        return result
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel in IGNORE_FILES:
            continue
        if rel.startswith("__pycache__/") or "/__pycache__/" in rel:
            continue
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check canonical skill copies match project-level distributions"
    )
    parser.add_argument("--root", default=".",
                        help="repository root path")
    parser.add_argument("--json", action="store_true",
                        help="output report as JSON")
    parser.add_argument("--skills", default=None,
                        help="comma-separated skill names; when set, only check these skills")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    canonical_dir = root / CANONICAL_DIR
    drift_reports: list[dict] = []

    skill_filter: set[str] | None = None
    if args.skills:
        skill_filter = set(s.strip() for s in args.skills.split(",") if s.strip())

    for dist_rel in DISTRIBUTED_DIRS:
        dist_dir = root / dist_rel
        if not dist_dir.is_dir():
            continue

        for skill_dir in sorted(dist_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name

            if skill_filter and skill_name not in skill_filter:
                continue

            canonical = canonical_dir / skill_name

            if not canonical.is_dir():
                continue

            canonical_digest = digest_tree(canonical)
            dist_digest = digest_tree(skill_dir)

            only_canonical = sorted(set(canonical_digest) - set(dist_digest))
            only_dist = sorted(set(dist_digest) - set(canonical_digest))
            changed = sorted(
                k for k in set(canonical_digest) & set(dist_digest)
                if canonical_digest[k] != dist_digest[k]
            )

            if only_canonical or only_dist or changed:
                drift_reports.append({
                    "skill": skill_name,
                    "distribution": dist_rel,
                    "only_canonical": only_canonical,
                    "only_distribution": only_dist,
                    "changed": changed,
                })

    if drift_reports:
        if args.json:
            print(json.dumps(drift_reports, indent=2))
        else:
            for r in drift_reports:
                print(f"DRIFT: {r['skill']} -> {r['distribution']}")
                for f in r["only_canonical"]:
                    print(f"  missing in distribution: {f}")
                for f in r["only_distribution"]:
                    print(f"  extra in distribution: {f}")
                for f in r["changed"]:
                    print(f"  changed: {f}")
        return 1

    if not args.json:
        print("OK: all skill distributions match canonical")
    else:
        print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
