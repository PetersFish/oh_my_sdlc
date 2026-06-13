#!/usr/bin/env python3
"""Output a roadmap summary table from roadmap items.

Usage:
  list.py              # Global view: all areas
  list.py <area-id>    # Single area view

Supports area-based layout (.ai/roadmap/areas/<area-id>/items/) and
legacy flat layout (.ai/roadmap/items/) with a migration warning.
"""

import re
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import (  # noqa: E402
    discover_areas,
    find_project_root,
    has_area_layout,
    has_flat_layout,
    resolve_roadmap_dir,
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


def collect_items_from(items_dir: Path, area_id: str | None) -> list[dict]:
    items = []
    if not items_dir.is_dir():
        return items
    for item_file in sorted(items_dir.glob("*.md")):
        content = item_file.read_text()
        fm = parse_frontmatter(content)
        item_id = fm.get("id", "")
        if not item_id:
            continue
        items.append(
            {
                "id": item_id,
                "status": fm.get("status", "?"),
                "title": fm.get("title", ""),
                "stage": fm.get("stage", "?"),
                "openspec_change": fm.get("openspec_change"),
                "order": int(fm.get("order", 999)),
                "area": area_id or "",
            }
        )
    return items


def print_table(items: list[dict], title: str | None = None):
    if not items:
        print("No roadmap items found. Use 'roadmap capture' to create items.")
        return

    if title:
        print(f"\n## {title}\n")

    items.sort(key=lambda x: x["order"])

    id_w = max(max(len(i["id"]) for i in items), 2)
    status_w = max(max(len(i["status"]) for i in items), 6)
    title_w = max(max(len(i["title"]) for i in items), 5)

    if any(i["area"] for i in items):
        area_w = max(max(len(i["area"]) for i in items), 4)
        header = f"{'ID':<{id_w}}  {'Area':<{area_w}}  {'Status':<{status_w}}  {'Title':<{title_w}}  {'Stage':<6}  {'OpenSpec'}"
        sep = f"{'-'*id_w}  {'-'*area_w}  {'-'*status_w}  {'-'*title_w}  {'-'*6}  {'-'*9}"
    else:
        header = f"{'ID':<{id_w}}  {'Status':<{status_w}}  {'Title':<{title_w}}  {'Stage':<6}  {'OpenSpec'}"
        sep = f"{'-'*id_w}  {'-'*status_w}  {'-'*title_w}  {'-'*6}  {'-'*9}"

    print(header)
    print(sep)
    for item in items:
        openspec = item["openspec_change"] or "-"
        marker = " *" if item["status"] == "active" else ""
        if item["area"]:
            print(
                f"{item['id']:<{id_w}}  {item['area']:<{area_w}}  {item['status']:<{status_w}}  {item['title']:<{title_w}}  {item['stage']:<6}  {openspec}{marker}"
            )
        else:
            print(
                f"{item['id']:<{id_w}}  {item['status']:<{status_w}}  {item['title']:<{title_w}}  {item['stage']:<6}  {openspec}{marker}"
            )

    if any(i["status"] == "active" for i in items):
        print("\n* = active item")


def main():
    root = find_project_root()

    area_filter = sys.argv[1] if len(sys.argv) > 1 else None

    if has_area_layout(root):
        if area_filter:
            items = collect_items_from(roadmap_area_items_dir(root, area_filter), area_filter)
            if not items:
                print(f"Area '{area_filter}' not found or has no items.")
                print(f"Available areas: {', '.join(discover_areas(root))}")
                return 1
            print_table(items, f"Roadmap - {area_filter}")
        else:
            all_items = []
            for area_id in discover_areas(root):
                area_items = collect_items_from(roadmap_area_items_dir(root, area_id), area_id)
                all_items.extend(area_items)
            all_items.sort(key=lambda x: x["order"])
            if not all_items:
                print("No roadmap items found. Use 'roadmap capture' to create items.")
                return 0
            print(f"## Roadmap (global, {len(all_items)} items)\n")
            print_table(all_items)
        return 0

    if has_flat_layout(root):
        print("WARNING: flat legacy layout detected (.ai/roadmap/items/).")
        print("Consider migrating to area-based layout (.ai/roadmap/areas/<area-id>/items/).\n")
        rdir = resolve_roadmap_dir(root).path
        items = collect_items_from(rdir / "items", None)
        print_table(items)
        return 0

    print("No roadmap found. Use 'roadmap init' to create the roadmap structure.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
