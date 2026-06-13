from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from lifecycle_utils import build_install_metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a skill into a target directory.")
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--status", default="stable")
    args = parser.parse_args()

    source_skill = Path(args.source_repo) / "skills" / args.skill_name
    target_dir = Path(args.target)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_skill, target_dir)

    metadata = build_install_metadata(
        skill_name=args.skill_name,
        source_repo=args.source_repo,
        source_ref=args.source_ref,
        status=args.status,
        target=str(target_dir),
        source_skill_dir=source_skill,
    )
    (target_dir / ".skill-install.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
