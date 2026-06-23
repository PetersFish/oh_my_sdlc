from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from lifecycle_utils import build_install_metadata


def _compute_payload(target_dir: Path) -> tuple[str, list[str]]:
    files = sorted(
        str(p.relative_to(target_dir))
        for p in target_dir.rglob("*")
        if p.is_file()
        and p.name not in (".skill-install.json", ".DS_Store")
        and "__pycache__" not in p.parts
    )
    hasher = hashlib.sha256()
    for f in files:
        hasher.update((target_dir / f).read_bytes())
        hasher.update(b"\x00")
    return hasher.hexdigest(), files


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

    payload_hash, files = _compute_payload(target_dir)
    metadata = build_install_metadata(
        skill_name=args.skill_name,
        source_repo=args.source_repo,
        source_ref=args.source_ref,
        status=args.status,
        target=str(target_dir),
        payload_hash=payload_hash,
        files=files,
    )
    (target_dir / ".skill-install.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
