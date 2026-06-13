from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import resolve_memory_dir  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "child-module"


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _parent_slug(parent_id: str, parent_path: str) -> str:
    if parent_id.startswith("modules/"):
        return _slug(parent_id.removeprefix("modules/"))
    return _slug(parent_path.rsplit("/", 1)[-1])


def _child_memory_path(candidate: dict) -> str:
    parent = _parent_slug(candidate.get("parent_id", ""), candidate.get("parent_path", ""))
    child = _slug(candidate.get("name") or candidate.get("path", "child").rsplit("/", 1)[-1])
    return f"modules/{parent}/{child}.md"


def _format_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(values) + "]"


def _child_content(candidate: dict, memory_path: str) -> str:
    parent_id = candidate.get("parent_id", "")
    title = str(candidate.get("name", "Child Module")).replace("-", " ").title()
    source_path = candidate.get("path", "")
    tags = [t for t in {"module", "child", _slug(title)} if t]
    path_hints = [source_path] if source_path else []
    top_level = candidate.get("top_level_files", [])
    key_files = [f"{source_path}/{item}" for item in top_level if not str(item).endswith("/")]

    return "\n".join([
        "---",
        f"id: {memory_path.removesuffix('.md')}",
        f"parent_id: {parent_id}",
        "type: module",
        f"title: {title}",
        f"summary: Child module for `{source_path}`. Load this memory for tasks that mention this path or its owned files.",
        "sync_status: synced",
        "evidence_mode: discovery",
        "linked_commits: []",
        "linked_specs: []",
        "linked_sessions: []",
        f"updated_at: {_now()}",
        f"confidence: {candidate.get('confidence_band', 'medium')}",
        f"tags: {_format_list(tags)}",
        f"owned_paths: {_format_list([source_path] if source_path else [])}",
        f"path_hints: {_format_list(path_hints)}",
        f"keywords: {_format_list([_slug(title), 'child-module'])}",
        "test_paths: []",
        "spec_paths: []",
        "---",
        "",
        f"# {title}",
        "",
        "## When To Load",
        "",
        f"Load this memory when work targets `{source_path}` or files owned by this child module.",
        "",
        "## Key Files",
        "",
        *(f"- `{path}`" for path in key_files),
        "",
        "## Entry Points",
        "",
        "- Derived from discovered entry markers and supporting files.",
        "",
        "## Tests",
        "",
        "- No direct test path detected during discovery.",
        "",
        "## Related Specs",
        "",
        "- No direct spec path detected during discovery.",
        "",
        "## Known Pitfalls",
        "",
        "- None recorded yet.",
        "",
    ])


def _update_discovery_prefs(root: Path, candidate: dict, memory_path: str, write: bool) -> None:
    prefs_path = resolve_memory_dir(root).path / "discovery-prefs.json"
    prefs = _load_json(prefs_path, {
        "schema_version": "1.0",
        "exclude_patterns": [],
        "scan_paths": None,
        "max_depth": 5,
        "module_map": {},
    })
    module_map = prefs.setdefault("module_map", {})
    source_path = candidate.get("path", "")
    module_map[source_path] = {
        "fs_path": source_path,
        "status": "accepted",
        "memory_id": memory_path.removesuffix(".md"),
        "memory_path": memory_path,
        "parent_id": candidate.get("parent_id"),
        "confirmed_at": _now(),
    }
    if write:
        _write_json(prefs_path, prefs)


def _update_parent_routing(root: Path, candidate: dict, memory_path: str, write: bool) -> None:
    parent_id = candidate.get("parent_id", "")
    if not parent_id.startswith("modules/"):
        return
    parent_file = resolve_memory_dir(root).path / (parent_id + ".md")
    if not parent_file.exists():
        return
    content = parent_file.read_text(encoding="utf-8")
    title = str(candidate.get("name", "Child Module")).replace("-", " ").title()
    entry = f"- `{memory_path}`: {title}"
    if "## Child Modules" not in content:
        content = content.rstrip() + "\n\n## Child Modules\n\n" + entry + "\n"
    elif entry not in content:
        content = content.rstrip() + "\n" + entry + "\n"
    if write:
        parent_file.write_text(content, encoding="utf-8")


def create_child_module(root: Path, candidate: dict, write: bool = False) -> dict:
    memory_path = _child_memory_path(candidate)
    child_file = resolve_memory_dir(root).path / memory_path
    content = _child_content(candidate, memory_path)
    if write:
        child_file.parent.mkdir(parents=True, exist_ok=True)
        child_file.write_text(content, encoding="utf-8")
    _update_discovery_prefs(root, candidate, memory_path, write)
    _update_parent_routing(root, candidate, memory_path, write)
    return {
        "created": True,
        "memory_path": memory_path,
        "parent_id": candidate.get("parent_id"),
    }


def save_child_candidate_review(root: Path, candidate: dict, write: bool = False) -> dict:
    queue_path = resolve_memory_dir(root).path / "review-queue.json"
    queue = _load_json(queue_path, {"items": []})
    item = {
        "id": "child-module-" + _slug(candidate.get("path", candidate.get("name", "candidate"))),
        "type": "module",
        "source_sync_id": "child-module-discovery",
        "reason": "medium_confidence_child_candidate",
        "title": str(candidate.get("name", "Child Module")).replace("-", " ").title(),
        "source_refs": [candidate.get("path", "")],
        "status": "open",
        "created_at": _now(),
        "candidate": candidate,
    }
    queue.setdefault("items", []).append(item)
    if write:
        _write_json(queue_path, queue)
    return {"queued": True, "item": item}


def group_by_prefix(candidates: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for c in candidates:
        name = c.get("name", "")
        parts = name.rsplit("-", 1)
        if len(parts) > 1 and len(parts[0]) > 2:
            prefix = parts[0]
            groups.setdefault(prefix, []).append(c)
    return groups


def _grouped_memory_path(parent_id: str, parent_path: str, group_name: str) -> str:
    parent = _parent_slug(parent_id, parent_path)
    child = _slug(group_name)
    return f"modules/{parent}/{child}.md"


def _grouped_child_content(candidates: list[dict], memory_path: str, group_name: str) -> str:
    if not candidates:
        return ""
    parent_id = candidates[0].get("parent_id", "")
    all_paths = [c.get("path", "") for c in candidates if c.get("path")]
    tags = ["module", "child", _slug(group_name), "grouped"]
    title = group_name.replace("-", " ").title()

    rows: list[str] = []
    for c in candidates:
        name = c.get("name", "")
        path = c.get("path", "")
        desc = c.get("frontmatter_description", "")[:120]
        top_level = c.get("top_level_files", [])
        key_files = [f"{path}/{item}" for item in top_level if not str(item).endswith("/")]
        rows.append(f"| `{name}` | {desc} | {', '.join(key_files[:3]) if key_files else '—'} |")

    return "\n".join([
        "---",
        f"id: {memory_path.removesuffix('.md')}",
        f"parent_id: {parent_id}",
        "type: module",
        f"title: {title}",
        f"summary: Grouped child module covering {len(candidates)} related packages under `{group_name}`. Load this memory for tasks targeting any owned path in this group.",
        "sync_status: synced",
        "evidence_mode: discovery",
        "linked_commits: []",
        "linked_specs: []",
        "linked_sessions: []",
        f"updated_at: {_now()}",
        f"confidence: {max((c.get('confidence_band') or 'medium' for c in candidates), key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x, 0))}" if candidates else "confidence: medium",
        f"tags: {_format_list(tags)}",
        f"owned_paths: {_format_list(all_paths)}",
        f"path_hints: {_format_list(all_paths)}",
        f"keywords: {_format_list([_slug(group_name), 'child-module', 'grouped'])}",
        "test_paths: []",
        "spec_paths: []",
        "---",
        "",
        f"# {title}",
        "",
        "## When To Load",
        "",
        f"Load this memory when work targets any path owned by the `{group_name}` child module group.",
        "",
        "## Grouped Packages",
        "",
        "| Name | Description | Key Files |",
        "|------|-------------|-----------|",
        *rows,
        "",
        "## Entry Points",
        "",
        "- Each grouped package has its own SKILL.md entry point.",
        "",
        "## Tests",
        "",
        "- See individual package test paths.",
        "",
        "## Related Specs",
        "",
        "- See individual package spec paths.",
        "",
        "## Known Pitfalls",
        "",
        "- None recorded yet.",
        "",
    ])


def create_grouped_child_module(root: Path, candidates: list[dict], group_name: str, write: bool = False) -> dict:
    if not candidates:
        return {"created": False, "error": "no candidates"}
    parent_id = candidates[0].get("parent_id", "")
    parent_path = candidates[0].get("parent_path", "")
    memory_path = _grouped_memory_path(parent_id, parent_path, group_name)
    child_file = resolve_memory_dir(root).path / memory_path
    content = _grouped_child_content(candidates, memory_path, group_name)
    if write:
        child_file.parent.mkdir(parents=True, exist_ok=True)
        child_file.write_text(content, encoding="utf-8")
    for c in candidates:
        _update_discovery_prefs(root, c, memory_path, write)
    _update_parent_routing(root, candidates[0], memory_path, write)
    return {
        "created": True,
        "memory_path": memory_path,
        "parent_id": parent_id,
        "grouped_count": len(candidates),
    }
