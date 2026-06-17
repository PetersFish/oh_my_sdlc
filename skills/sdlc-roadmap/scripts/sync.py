#!/usr/bin/env python3
"""Report-oriented lifecycle mismatch diagnostics.

Compares OpenSpec change status against roadmap item status and reports
discrepancies. Does NOT trigger state transitions — that is owned by
sdlc-orchestrator (post-archive gate) and sdlc-roadmap done (mutation).

Usage:
  sync.py                       # Report all mismatches
  sync.py --change <change-id>  # Check specific OpenSpec change
  sync.py --item <RM-xxx>       # Check specific roadmap item
"""

import argparse
import json
import re
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import (  # noqa: E402
    canonical_roadmap_dir,
    discover_areas,
    find_project_root,
    has_area_layout,
    roadmap_area_items_dir,
)


def parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm_text = parts[1].strip()
    result = {}
    in_list = False
    list_key = None
    list_values = []
    for line in fm_text.split("\n"):
        if in_list and line.strip().startswith("- "):
            list_values.append(line.strip()[2:])
            continue
        else:
            if in_list and list_key:
                result[list_key] = list_values
                in_list = False
                list_key = None
                list_values = []

        match = re.match(r"^(\w+):\s*(.*)", line)
        if not match:
            continue
        key, raw_value = match.group(1), match.group(2).strip()

        if raw_value == "[]":
            result[key] = []
        elif raw_value == "":
            in_list = True
            list_key = key
            list_values = []
        elif raw_value == "null":
            result[key] = None
        elif raw_value == "true":
            result[key] = True
        elif raw_value == "false":
            result[key] = False
        elif raw_value.startswith('"') and raw_value.endswith('"'):
            result[key] = raw_value[1:-1]
        elif raw_value.startswith("'") and raw_value.endswith("'"):
            result[key] = raw_value[1:-1]
        else:
            result[key] = raw_value

    if in_list and list_key:
        result[list_key] = list_values
    return result


def collect_roadmap_items(root: Path) -> list[dict]:
    items = []
    if not has_area_layout(root):
        return items
    for area_id in discover_areas(root):
        items_dir = roadmap_area_items_dir(root, area_id)
        if not items_dir.is_dir():
            continue
        for item_file in sorted(items_dir.glob("*.md")):
            content = item_file.read_text()
            fm = parse_frontmatter(content)
            item_id = fm.get("id", "")
            if not item_id:
                continue
            items.append({
                "id": item_id,
                "status": fm.get("status", "?"),
                "title": fm.get("title", ""),
                "openspec_change": fm.get("openspec_change"),
                "area": area_id,
            })
    return items


def _find_archive_dir(root: Path, change_id: str) -> Path | None:
    archive_root = root / "openspec" / "changes" / "archive"
    if not archive_root.is_dir():
        return None
    for entry in archive_root.iterdir():
        if entry.is_dir() and (
            entry.name == change_id or entry.name.endswith(f"-{change_id}")
        ):
            return entry
    return None


def get_openspec_status(root: Path, change_id: str) -> str | None:
    change_path = root / "openspec" / "changes" / change_id
    archive_path = _find_archive_dir(root, change_id)

    if archive_path is not None:
        return "archived"

    if not change_path.is_dir():
        return None

    status_file = change_path / ".openspec.yaml"
    tasks_file = change_path / "tasks.md"

    if status_file.exists():
        content = status_file.read_text()
        if "status: archived" in content:
            return "archived"

    if tasks_file.exists():
        tasks_content = tasks_file.read_text()
        total = tasks_content.count("[ ]") + tasks_content.count("[x]")
        done = tasks_content.count("[x]")
        if total == 0:
            return "unknown"
        if done == total:
            return "complete"
        return "in_progress"

    return "unknown"


def main():
    parser = argparse.ArgumentParser(
        description="Report lifecycle mismatches between OpenSpec and roadmap"
    )
    parser.add_argument("--change", default=None, help="Check a specific OpenSpec change")
    parser.add_argument("--item", default=None, help="Check a specific roadmap item")
    args = parser.parse_args()

    root = find_project_root()

    if not has_area_layout(root):
        print("No roadmap found. Use 'roadmap init' to create the roadmap structure.")
        return 0

    roadmap_items = collect_roadmap_items(root)
    if not roadmap_items:
        print("No roadmap items found. Use 'roadmap capture' to create items.")
        return 0

    mismatches = []

    if args.item:
        roadmap_items = [i for i in roadmap_items if i["id"] == args.item]
        if not roadmap_items:
            print(f"Item '{args.item}' not found.")
            return 1

    for item in roadmap_items:
        change_id = item.get("openspec_change")
        if not change_id:
            continue

        if args.change and change_id != args.change:
            continue

        openspec_status = get_openspec_status(root, change_id)

        if openspec_status is None:
            mismatches.append(
                f"{item['id']} ({item['status']}): linked OpenSpec change "
                f"'{change_id}' not found on disk"
            )
            continue

        if openspec_status == "archived" and item["status"] != "done":
            mismatches.append(
                f"{item['id']} ({item['status']}): OpenSpec change "
                f"'{change_id}' is archived but roadmap item is not done"
            )
        elif openspec_status == "complete" and item["status"] not in ("done", "active"):
            mismatches.append(
                f"{item['id']} ({item['status']}): OpenSpec change "
                f"'{change_id}' is complete but roadmap item is not done or active"
            )
        elif openspec_status == "in_progress" and item["status"] not in ("active",):
            mismatches.append(
                f"{item['id']} ({item['status']}): OpenSpec change "
                f"'{change_id}' is in progress but roadmap item is not active"
            )

    if mismatches:
        print("Lifecycle mismatches found:")
        for m in mismatches:
            print(f"  - {m}")
        print("\nNote: sync.py is diagnostic-only. Use 'roadmap done' or let")
        print("sdlc-orchestrator route post-archive transitions to resolve mismatches.")
        return 0
    else:
        print("No lifecycle mismatches detected.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
