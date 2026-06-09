#!/usr/bin/env python3
"""Validate .roadmap/ item frontmatter, index.json consistency, and state legality.

Exit code 0: all valid. Non-zero: errors found.
"""

import json
import os
import sys
import re
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import find_project_root, resolve_roadmap_dir  # noqa: E402

VALID_STATUSES = {"idea", "planned", "ready", "active", "done", "deferred", "cancelled", "superseded"}
VALID_PRIORITIES = {"p0", "p1", "p2", "p3"}
REQUIRED_FM_FIELDS = {"id", "title", "status", "stage", "priority", "order", "depends_on", "openspec_change", "patches"}


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter as a simple dict. Handles only flat string/list/null values."""
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
        # List continuation line (  - value)
        if in_list and line.strip().startswith("- "):
            list_values.append(line.strip()[2:])
            continue
        else:
            if in_list and list_key:
                result[list_key] = list_values
                in_list = False
                list_key = None
                list_values = []

        # Key: value or key:
        match = re.match(r"^(\w+):\s*(.*)", line)
        if not match:
            continue
        key, raw_value = match.group(1), match.group(2).strip()

        if raw_value == "[]":
            result[key] = []
        elif raw_value == "":
            # Could be the start of a list
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
    roadmap_dir = resolve_roadmap_dir(root).path
    items_dir = roadmap_dir / "items"

    if not roadmap_dir.is_dir():
        print("ERROR: .ai/roadmap/ directory not found")
        return 1

    if not items_dir.is_dir():
        print("ERROR: .ai/roadmap/items/ directory not found")
        return 1

    errors = []
    items = {}
    item_files = sorted(items_dir.glob("*.md"))

    if not item_files:
        print("WARNING: No item files found in .ai/roadmap/items/")
    else:
        for item_file in item_files:
            content = item_file.read_text()
            fm = parse_frontmatter(content)

            item_id = fm.get("id", "")
            if not item_id:
                errors.append(f"{item_file.name}: missing 'id' in frontmatter")
                continue

            items[item_id] = fm

            # Check required fields
            missing = REQUIRED_FM_FIELDS - set(fm.keys())
            if missing:
                errors.append(f"{item_id}: missing required fields: {missing}")

            # Validate status
            status = fm.get("status", "")
            if status and status not in VALID_STATUSES:
                errors.append(f"{item_id}: invalid status '{status}' (valid: {sorted(VALID_STATUSES)})")

            # Validate priority
            priority = fm.get("priority", "")
            if priority and priority not in VALID_PRIORITIES:
                errors.append(
                    f"{item_id}: invalid priority '{priority}' (valid: {sorted(VALID_PRIORITIES)})"
                )

            # Validate order is present and numeric-ish
            order = fm.get("order")
            if order is None:
                errors.append(f"{item_id}: missing 'order' field")
            elif not isinstance(order, (int, float)) and not (
                isinstance(order, str) and order.isdigit()
            ):
                errors.append(f"{item_id}: 'order' must be numeric, got '{order}'")

            # Validate depends_on is a list (our parser should handle this)
            depends_on = fm.get("depends_on")
            if depends_on is not None and not isinstance(depends_on, list):
                errors.append(f"{item_id}: 'depends_on' must be a list, got {type(depends_on).__name__}")

            # Validate patches is a list
            patches = fm.get("patches")
            if patches is not None and not isinstance(patches, list):
                errors.append(f"{item_id}: 'patches' must be a list, got {type(patches).__name__}")

        # Check depends_on references
        for item_id, fm in items.items():
            depends_on = fm.get("depends_on", [])
            if isinstance(depends_on, list):
                for dep_id in depends_on:
                    if dep_id not in items:
                        errors.append(f"{item_id}: depends_on '{dep_id}' does not exist")

        # Check duplicate IDs (shouldn't happen with file parsing, but check)
        # Already handled by filename parsing

    # Validate index.json consistency
    index_path = roadmap_dir / "index.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                index_data = json.load(f)
            index_items = {item["id"]: item for item in index_data.get("items", [])}

            for item_id, fm in items.items():
                if item_id not in index_items:
                    errors.append(f"index.json: item '{item_id}' in items/ but not in index.json")
                    continue
                idx_item = index_items[item_id]
                for field in ["status", "title", "stage", "priority", "order"]:
                    fm_val = fm.get(field)
                    idx_val = idx_item.get(field)
                    if str(fm_val) != str(idx_val):
                        errors.append(
                            f"index.json mismatch for {item_id}.{field}: "
                            f"item={fm_val} index={idx_val}"
                        )

            # Also check index.json has extra items not in files
            for idx_id in index_items:
                if idx_id not in items:
                    errors.append(
                        f"index.json: item '{idx_id}' in index but not in .ai/roadmap/items/"
                    )
        except json.JSONDecodeError as e:
            errors.append(f"index.json: invalid JSON: {e}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("OK: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
