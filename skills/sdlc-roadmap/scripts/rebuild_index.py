#!/usr/bin/env python3
"""Rebuild index.json from .roadmap/items/*.md frontmatter. Backs up existing index."""

import json
import re
import shutil
import sys
from pathlib import Path


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


def find_root() -> Path:
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".roadmap").is_dir():
            return parent
        if (parent / ".ai-memory").is_dir():
            return parent
        if (parent / "openspec").is_dir():
            return parent
    return cwd


def main():
    root = find_root()
    roadmap_dir = root / ".roadmap"
    items_dir = roadmap_dir / "items"
    index_path = roadmap_dir / "index.json"

    if not items_dir.is_dir():
        print("ERROR: .roadmap/items/ directory not found")
        return 1

    # Backup existing index if present
    if index_path.exists():
        backup_path = roadmap_dir / "index.json.bak"
        shutil.copy2(index_path, backup_path)
        print(f"Backed up existing index.json to index.json.bak")

    item_files = sorted(items_dir.glob("*.md"))
    items = []

    for item_file in item_files:
        content = item_file.read_text()
        fm = parse_frontmatter(content)
        item_id = fm.get("id", "")
        if not item_id:
            print(f"WARNING: {item_file.name} has no 'id' in frontmatter, skipping")
            continue

        order_raw = fm.get("order", 999)
        try:
            order = int(order_raw)
        except (ValueError, TypeError):
            order = 999

        items.append(
            {
                "id": item_id,
                "status": fm.get("status", "planned"),
                "title": fm.get("title", ""),
                "stage": fm.get("stage", ""),
                "priority": fm.get("priority", "p2"),
                "order": order,
                "depends_on": fm.get("depends_on", []) or [],
                "openspec_change": fm.get("openspec_change"),
                "patches": fm.get("patches", []) or [],
            }
        )

    # Sort by order
    items.sort(key=lambda x: x["order"])

    index = {"version": 1, "items": items}

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Rebuilt index.json with {len(items)} item(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
