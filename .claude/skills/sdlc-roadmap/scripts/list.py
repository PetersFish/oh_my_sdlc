#!/usr/bin/env python3
"""Output a roadmap summary table from .roadmap/items/*.md frontmatter."""

import re
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import find_project_root, resolve_roadmap_dir  # noqa: E402


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


def main():
    root = find_project_root()
    items_dir = resolve_roadmap_dir(root).path / "items"

    if not items_dir.is_dir():
        print("No roadmap items found. Use 'roadmap capture' to create items.")
        return 0

    item_files = sorted(items_dir.glob("*.md"))
    if not item_files:
        print("No roadmap items found. Use 'roadmap capture' to create items.")
        return 0

    items = []
    for item_file in item_files:
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
            }
        )

    items.sort(key=lambda x: x["order"])

    # Column widths
    id_w = max(max(len(i["id"]) for i in items), 2)
    status_w = max(max(len(i["status"]) for i in items), 6)
    title_w = max(max(len(i["title"]) for i in items), 5)

    header = f"{'ID':<{id_w}}  {'Status':<{status_w}}  {'Title':<{title_w}}  {'Stage':<6}  {'OpenSpec'}"
    sep = f"{'-'*id_w}  {'-'*status_w}  {'-'*title_w}  {'-'*6}  {'-'*9}"

    print(header)
    print(sep)
    for item in items:
        openspec = item["openspec_change"] or "-"
        marker = " *" if item["status"] == "active" else ""
        print(
            f"{item['id']:<{id_w}}  {item['status']:<{status_w}}  {item['title']:<{title_w}}  {item['stage']:<6}  {openspec}{marker}"
        )

    if any(i["status"] == "active" for i in items):
        print("\n* = active item")

    return 0


if __name__ == "__main__":
    sys.exit(main())
