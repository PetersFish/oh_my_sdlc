#!/usr/bin/env python3
"""Check a superpowers plan file for unchecked checkboxes.

Usage:
    python3 scripts/check_plan_checkboxes.py <plan_path>

Exit codes:
    0 — all checkboxes checked (or no checkboxes found)
    1 — one or more unchecked checkboxes remain
    2 — file not found
"""

import re
import sys
from pathlib import Path

CHECKBOX_RE = re.compile(r"^\s*- \[ \]")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_plan_checkboxes.py <plan_path>", file=sys.stderr)
        return 2

    plan_path = Path(argv[1])
    if not plan_path.is_file():
        print(f"error: file not found: {plan_path}", file=sys.stderr)
        return 2

    unchecked: list[str] = []
    for lineno, line in enumerate(plan_path.read_text(encoding="utf-8").splitlines(), start=1):
        if CHECKBOX_RE.match(line):
            unchecked.append(f"{plan_path}:{lineno}: {line.strip()}")

    if unchecked:
        print(f"error: {len(unchecked)} unchecked checkbox(es) remain in {plan_path}:")
        for entry in unchecked:
            print(f"  {entry}")
        return 1

    print(f"ok: all checkboxes complete in {plan_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
