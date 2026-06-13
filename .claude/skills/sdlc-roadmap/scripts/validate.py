#!/usr/bin/env python3
"""Validate roadmap item frontmatter, manifest consistency, and state legality.

Supports area-based layout (.ai/roadmap/areas/<area-id>/items/*.md) and
legacy flat layout (.ai/roadmap/items/*.md).

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

from sdlc_runtime_paths import (  # noqa: E402
    discover_areas,
    find_project_root,
    has_area_layout,
    has_flat_layout,
    load_area_manifest,
    load_roadmap_manifest,
    resolve_roadmap_dir,
    roadmap_area_items_dir,
)

VALID_STATUSES = {"idea", "planned", "ready", "active", "done", "deferred", "cancelled", "superseded"}
VALID_PRIORITIES = {"p0", "p1", "p2", "p3"}
REQUIRED_FM_FIELDS = {"id", "title", "status", "stage", "priority", "order", "depends_on", "openspec_change", "patches"}
REQUIRED_ROOT_MANIFEST_KEYS = {"version", "areas"}
REQUIRED_AREA_MANIFEST_KEYS = {"id", "kind", "title", "owner_path"}
REQUIRED_ITEM_KEYS_PER_AREA = {"id_prefix"}


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


def validate_item_fm(item_id: str, fm: dict, errors: list[str]):
    missing = REQUIRED_FM_FIELDS - set(fm.keys())
    if missing:
        errors.append(f"{item_id}: missing required fields: {missing}")

    status = fm.get("status", "")
    if status and status not in VALID_STATUSES:
        errors.append(f"{item_id}: invalid status '{status}' (valid: {sorted(VALID_STATUSES)})")

    priority = fm.get("priority", "")
    if priority and priority not in VALID_PRIORITIES:
        errors.append(f"{item_id}: invalid priority '{priority}' (valid: {sorted(VALID_PRIORITIES)})")

    order = fm.get("order")
    if order is None:
        errors.append(f"{item_id}: missing 'order' field")
    elif not isinstance(order, (int, float)) and not (isinstance(order, str) and order.isdigit()):
        errors.append(f"{item_id}: 'order' must be numeric, got '{order}'")

    depends_on = fm.get("depends_on")
    if depends_on is not None and not isinstance(depends_on, list):
        errors.append(f"{item_id}: 'depends_on' must be a list, got {type(depends_on).__name__}")

    patches = fm.get("patches")
    if patches is not None and not isinstance(patches, list):
        errors.append(f"{item_id}: 'patches' must be a list, got {type(patches).__name__}")


def validate_area_layout(root: Path, roadmap_dir: Path, errors: list[str]):
    manifest = load_roadmap_manifest(root)
    if manifest is None:
        errors.append("root manifest.json missing")
        return

    missing = REQUIRED_ROOT_MANIFEST_KEYS - set(manifest.keys())
    if missing:
        errors.append(f"root manifest.json: missing required keys: {missing}")

    if "version" in manifest and not isinstance(manifest["version"], int):
        errors.append("root manifest.json: 'version' must be an integer")

    area_ids_from_disk = set(discover_areas(root))
    if "areas" in manifest and isinstance(manifest["areas"], list):
        manifest_area_ids = set()
        for area_entry in manifest["areas"]:
            if not isinstance(area_entry, dict):
                errors.append("root manifest.json: 'areas' entry is not an object")
                continue
            area_id = area_entry.get("id", "")
            if area_id:
                manifest_area_ids.add(area_id)

        for area_id in manifest_area_ids - area_ids_from_disk:
            errors.append(f"root manifest.json: area '{area_id}' listed but directory not found")
        for area_id in area_ids_from_disk - manifest_area_ids:
            errors.append(f"root manifest.json: area '{area_id}' exists on disk but not in manifest")

    all_items = {}
    area_prefixes = {}

    for area_id in area_ids_from_disk:
        area_manifest = load_area_manifest(root, area_id)
        if area_manifest is None:
            errors.append(f"area '{area_id}': manifest.json missing")
        else:
            missing = REQUIRED_AREA_MANIFEST_KEYS - set(area_manifest.keys())
            if missing:
                errors.append(f"area '{area_id}' manifest.json: missing required keys: {missing}")
            if area_manifest.get("id") != area_id:
                errors.append(
                    f"area '{area_id}' manifest.json: 'id' field "
                    f"({area_manifest.get('id')}) does not match directory name"
                )

        id_prefix = area_manifest.get("id_prefix", "") if area_manifest else ""
        area_prefixes[area_id] = id_prefix

        items_dir = roadmap_area_items_dir(root, area_id)
        if not items_dir.is_dir():
            errors.append(f"area '{area_id}': items/ directory not found")
            continue

        item_files = sorted(items_dir.glob("*.md"))
        if not item_files:
            errors.append(f"area '{area_id}': no item files in items/")
            continue

        for item_file in item_files:
            content = item_file.read_text()
            fm = parse_frontmatter(content)
            item_id = fm.get("id", "")
            if not item_id:
                errors.append(f"{area_id}/{item_file.name}: missing 'id' in frontmatter")
                continue

            all_items[item_id] = fm
            validate_item_fm(item_id, fm, errors)

            if id_prefix and not item_id.startswith(id_prefix):
                errors.append(f"{item_id}: ID must start with prefix '{id_prefix}' (area '{area_id}')")

    duplicate_ids = set()
    for area_id in area_ids_from_disk:
        items_dir = roadmap_area_items_dir(root, area_id)
        if not items_dir.is_dir():
            continue
        seen = set()
        for item_file in sorted(items_dir.glob("*.md")):
            content = item_file.read_text()
            fm = parse_frontmatter(content)
            item_id = fm.get("id", "")
            if not item_id:
                continue
            if item_id in seen:
                duplicate_ids.add(item_id)
            seen.add(item_id)
    for dup_id in sorted(duplicate_ids):
        errors.append(f"{dup_id}: duplicate item ID within same area")

    for item_id, fm in all_items.items():
        depends_on = fm.get("depends_on", [])
        if isinstance(depends_on, list):
            for dep_id in depends_on:
                if dep_id not in all_items:
                    errors.append(f"{item_id}: depends_on '{dep_id}' does not exist in any area")

    index_path = roadmap_dir / "index.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                index_data = json.load(f)
            index_items = {item["id"]: item for item in index_data.get("items", [])}

            for item_id, fm in all_items.items():
                if item_id not in index_items:
                    errors.append(f"index.json: item '{item_id}' in areas but not in index.json")
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

            for idx_id in index_items:
                if idx_id not in all_items:
                    errors.append(f"index.json: item '{idx_id}' in index but not in any area")
        except json.JSONDecodeError as e:
            errors.append(f"index.json: invalid JSON: {e}")

    return all_items


def validate_flat_layout(root: Path, roadmap_dir: Path, errors: list[str]) -> dict:
    items_dir = roadmap_dir / "items"
    if not items_dir.is_dir():
        errors.append("ERROR: .ai/roadmap/items/ directory not found")
        return {}

    item_files = sorted(items_dir.glob("*.md"))
    if not item_files:
        print("WARNING: No item files found in .ai/roadmap/items/")
        return {}

    items = {}
    for item_file in item_files:
        content = item_file.read_text()
        fm = parse_frontmatter(content)
        item_id = fm.get("id", "")
        if not item_id:
            errors.append(f"{item_file.name}: missing 'id' in frontmatter")
            continue
        items[item_id] = fm
        validate_item_fm(item_id, fm, errors)

    for item_id, fm in items.items():
        depends_on = fm.get("depends_on", [])
        if isinstance(depends_on, list):
            for dep_id in depends_on:
                if dep_id not in items:
                    errors.append(f"{item_id}: depends_on '{dep_id}' does not exist")

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

            for idx_id in index_items:
                if idx_id not in items:
                    errors.append(f"index.json: item '{idx_id}' in index but not in .ai/roadmap/items/")
        except json.JSONDecodeError as e:
            errors.append(f"index.json: invalid JSON: {e}")

    return items


def main():
    root = find_project_root()
    roadmap_dir = resolve_roadmap_dir(root).path

    if not roadmap_dir.is_dir():
        print("ERROR: .ai/roadmap/ directory not found")
        return 1

    errors = []

    if has_area_layout(root):
        validate_area_layout(root, roadmap_dir, errors)
    elif has_flat_layout(root):
        print("NOTE: flat legacy layout detected (.ai/roadmap/items/).")
        print("      Consider migrating to area-based layout.\n")
        validate_flat_layout(root, roadmap_dir, errors)
    else:
        print("WARNING: No roadmap items directory found (neither areas/ nor items/).")
        return 0

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("OK: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
