from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an installed skill copy.")
    parser.add_argument("--target", required=True)
    parser.add_argument("--expected-source-ref", required=True)
    parser.add_argument("--expected-status", required=True)
    args = parser.parse_args()

    target = Path(args.target)
    metadata_path = target / ".skill-install.json"
    if not target.exists() or not metadata_path.exists():
        print(json.dumps({"ok": False, "reason": "missing-target-or-metadata"}, indent=2))
        return 1

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    ok = metadata.get("source_ref") == args.expected_source_ref and metadata.get("status") == args.expected_status
    print(json.dumps({"ok": ok, "metadata": metadata}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
