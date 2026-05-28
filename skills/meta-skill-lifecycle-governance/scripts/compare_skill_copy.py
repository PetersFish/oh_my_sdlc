from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest_tree(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two skill copies.")
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    args = parser.parse_args()

    left = digest_tree(Path(args.left))
    right = digest_tree(Path(args.right))
    diff = {
        "only_left": sorted(set(left) - set(right)),
        "only_right": sorted(set(right) - set(left)),
        "changed": sorted(k for k in set(left) & set(right) if left[k] != right[k]),
    }
    print(json.dumps(diff, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
