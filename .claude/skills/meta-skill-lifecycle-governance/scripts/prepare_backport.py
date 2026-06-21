from __future__ import annotations

import argparse
import json

from lifecycle_utils import classify_backport_candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare backport review material.")
    parser.add_argument("--note", required=True)
    args = parser.parse_args()

    classification = classify_backport_candidate(args.note)
    print(json.dumps({"classification": classification, "note": args.note}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
