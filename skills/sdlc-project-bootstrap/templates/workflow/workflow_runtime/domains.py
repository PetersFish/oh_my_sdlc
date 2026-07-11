"""domains.py — read-only domain loaders.

OpenSpec, archive, roadmap, memory, and EvalOps lookups. These loaders
MUST NOT mutate workflow or domain state.
"""

import datetime
import os

import yaml

from workflow_runtime.core import _resolve_path
from workflow_runtime.state import _list_dirs


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def _parse_yaml_frontmatter(content):
    """Parse YAML frontmatter between --- markers."""
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    try:
        raw = yaml.safe_load(content[3:end])
        if isinstance(raw, dict):
            return _sanitize_for_json(raw)
        return raw
    except Exception:
        return None


def _sanitize_for_json(obj):
    """Recursively convert YAML-parsed objects to JSON-serializable types."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if hasattr(obj, "__str__"):
        return str(obj)
    return obj


def _read_frontmatter_field(path, field):
    try:
        with open(path, "r") as f:
            content = f.read()
        fm = _parse_yaml_frontmatter(content)
        return fm.get(field) if fm else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Roadmap item helpers
# ---------------------------------------------------------------------------

def _find_roadmap_items(root, change_id):
    """Scan .ai/roadmap/areas/*/items/*.md for spec_change or openspec_change match."""
    items = []
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    if not os.path.isdir(areas_dir):
        return items
    for area in _list_dirs(areas_dir):
        items_dir = os.path.join(areas_dir, area, "items")
        if not os.path.isdir(items_dir):
            continue
        for fname in _list_dirs(items_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(items_dir, fname)
            try:
                with open(fpath, "r") as f:
                    content = f.read()
            except Exception:
                continue
            fm = _parse_yaml_frontmatter(content)
            if fm and (fm.get("spec_change") == change_id or fm.get("openspec_change") == change_id):
                item_id = (
                    fm.get("id")
                    or fm.get("item_id")
                    or fname.replace(".md", "")
                )
                status = fm.get("status", "")
                completed_at = fm.get("completed_at")
                started_at = fm.get("started_at")
                items.append({
                    "item_id": item_id,
                    "status": status,
                    "completed_at": completed_at,
                    "started_at": started_at,
                    "file": fpath,
                    "area": area,
                })
    return items


def _read_roadmap_item_spec_change(root, item_id):
    """Read provider-agnostic spec_change from a roadmap item file.
    Tries spec_change first, then falls back to openspec_change for legacy compatibility."""
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    for area in _list_dirs(areas_dir):
        items_dir = os.path.join(areas_dir, area, "items")
        if not os.path.isdir(items_dir):
            continue
        for fname in _list_dirs(items_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(items_dir, fname)
            fm_id = _read_frontmatter_field(fpath, "id")
            if fm_id == item_id:
                spec = _read_frontmatter_field(fpath, "spec_change")
                if spec:
                    return spec
                return _read_frontmatter_field(fpath, "openspec_change")
    return None


# ---------------------------------------------------------------------------
# OpenSpec / spec change loaders
# ---------------------------------------------------------------------------

def loader_openspec_change_status(root, change_id):
    """Classify an OpenSpec change as active, archived, missing, in-progress, complete, or unknown."""
    active_dir = _resolve_path(root, f"openspec/changes/{change_id}")
    archives = _resolve_path(root, "openspec/changes/archive")
    if os.path.isdir(active_dir):
        tasks_path = os.path.join(active_dir, "tasks.md")
        if os.path.exists(tasks_path):
            with open(tasks_path, "r") as f:
                content = f.read()
            incomplete = any(
                line.strip().startswith("- [ ]") for line in content.split("\n")
            )
            all_tasks = any(
                line.strip().startswith("- [") for line in content.split("\n")
            )
            if all_tasks and not incomplete:
                return {"classification": "complete", "source": "active"}
            return {"classification": "in-progress", "source": "active"}
        # directory exists but no tasks.md: not yet ready for implementation
        return {"classification": "scaffold", "source": "active"}

    if os.path.isdir(archives):
        for entry in _list_dirs(archives):
            e_path = os.path.join(archives, entry)
            if not os.path.isdir(e_path):
                continue
            parts = entry.split("-")
            if len(parts) >= 4 and "-".join(parts[3:]) == change_id:
                return {
                    "classification": "archived",
                    "source": e_path,
                }
    return {"classification": "missing", "source": None}


def loader_openspec_archive_path(root, change_id):
    """Find archive path for a change id."""
    archives = _resolve_path(root, "openspec/changes/archive")
    matches = []
    if os.path.isdir(archives):
        for entry in _list_dirs(archives):
            parts = entry.split("-")
            if len(parts) >= 4 and "-".join(parts[3:]) == change_id:
                matches.append(os.path.join(archives, entry))
    if len(matches) == 1:
        rel = os.path.relpath(matches[0], root) if root else matches[0]
        return rel
    return None


def loader_spec_change_status(root, change_id):
    return loader_openspec_change_status(root, change_id)


def loader_spec_archive_path(root, change_id):
    return loader_openspec_archive_path(root, change_id)


# ---------------------------------------------------------------------------
# Roadmap loaders
# ---------------------------------------------------------------------------

def loader_roadmap_linked_item(root, change_id):
    """Scan roadmap items for openspec_change match."""
    items = _find_roadmap_items(root, change_id)
    if len(items) == 0:
        return {"count": 0, "items": []}
    return {"count": len(items), "items": items}


def loader_roadmap_item_status(root, item_id):
    """Read the status of a specific roadmap item."""
    if not item_id:
        return None
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    for area in _list_dirs(areas_dir):
        items_dir = os.path.join(areas_dir, area, "items")
        if not os.path.isdir(items_dir):
            continue
        for fname in _list_dirs(items_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(items_dir, fname)
            fm_id = _read_frontmatter_field(fpath, "id")
            if fm_id == item_id:
                return {
                    "item_id": item_id,
                    "status": _read_frontmatter_field(fpath, "status"),
                    "completed_at": _read_frontmatter_field(fpath, "completed_at"),
                    "started_at": _read_frontmatter_field(fpath, "started_at"),
                }
    return None


# ---------------------------------------------------------------------------
# Phase inference
# ---------------------------------------------------------------------------

def _strip_leading_date_slug(stem):
    parts = stem.split("-", 3)
    if len(parts) == 4 and all(part.isdigit() for part in parts[:3]):
        return parts[3]
    return stem


def _matching_superpowers_plans(root, subject_id):
    plans_dir = os.path.join(root, "docs", "superpowers", "plans")
    if not os.path.isdir(plans_dir):
        return []

    matches = []
    for filename in sorted(os.listdir(plans_dir)):
        if not filename.endswith(".md"):
            continue
        stem = os.path.splitext(filename)[0]
        normalized = _strip_leading_date_slug(stem)
        if normalized == subject_id or subject_id in normalized:
            matches.append(os.path.join(plans_dir, filename))
    return matches


def _infer_phase(root, subject_type, subject_id, flow_type="spec-flow"):
    if subject_type == "roadmap_item":
        item_status = loader_roadmap_item_status(root, subject_id)
        if item_status:
            status = item_status.get("status", "")
            if status == "idea":
                return "review_roadmap"
            if status == "ready":
                linked_change = _read_roadmap_item_spec_change(root, subject_id)
                if linked_change and linked_change != "None":
                    return "create_change"
                return "review_roadmap"
            if status == "active":
                return "apply_change"
            # done, cancelled, or unknown: start new lifecycle
        return "create_roadmap"
    if subject_type != "spec_change":
        return "input"
    if flow_type == "lightweight-flow":
        matches = _matching_superpowers_plans(root, subject_id)
        if len(matches) == 1:
            return "apply_change"
        return "create_change"
    status = loader_openspec_change_status(root, subject_id)
    classification = status.get("classification", "missing")
    if classification == "archived":
        return "post_archive_actions"
    if classification == "complete":
        return "archive_change"
    if classification in ("active", "in-progress"):
        return "apply_change"
    # scaffold, missing, unknown: artifact creation still pending
    return "create_change"