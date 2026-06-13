from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


AI_DIR = ".ai"
MEMORY_SUBDIR = "memory"
ROADMAP_SUBDIR = "roadmap"
LEGACY_MEMORY_DIR = ".ai-memory"
LEGACY_ROADMAP_DIR = ".roadmap"
ROADMAP_AREAS_SUBDIR = "areas"
ROADMAP_MANIFEST_FILE = "manifest.json"


@dataclass(frozen=True)
class RuntimePath:
    path: Path
    kind: str
    legacy: bool


def canonical_memory_dir(root: Path) -> Path:
    return root / AI_DIR / MEMORY_SUBDIR


def canonical_roadmap_dir(root: Path) -> Path:
    return root / AI_DIR / ROADMAP_SUBDIR


def resolve_memory_dir(root: Path) -> RuntimePath:
    canonical = canonical_memory_dir(root)
    if canonical.exists():
        return RuntimePath(canonical, "canonical", False)
    legacy = root / LEGACY_MEMORY_DIR
    if legacy.exists():
        return RuntimePath(legacy, "legacy", True)
    return RuntimePath(canonical, "canonical", False)


def resolve_roadmap_dir(root: Path) -> RuntimePath:
    canonical = canonical_roadmap_dir(root)
    if canonical.exists():
        return RuntimePath(canonical, "canonical", False)
    legacy = root / LEGACY_ROADMAP_DIR
    if legacy.exists():
        return RuntimePath(legacy, "legacy", True)
    return RuntimePath(canonical, "canonical", False)


def roadmap_manifest_path(root: Path) -> Path:
    return canonical_roadmap_dir(root) / ROADMAP_MANIFEST_FILE


def roadmap_areas_dir(root: Path) -> Path:
    return canonical_roadmap_dir(root) / ROADMAP_AREAS_SUBDIR


def roadmap_area_dir(root: Path, area_id: str) -> Path:
    return roadmap_areas_dir(root) / area_id


def roadmap_area_items_dir(root: Path, area_id: str) -> Path:
    return roadmap_area_dir(root, area_id) / "items"


def roadmap_area_manifest_path(root: Path, area_id: str) -> Path:
    return roadmap_area_dir(root, area_id) / ROADMAP_MANIFEST_FILE


def load_roadmap_manifest(root: Path) -> dict | None:
    path = roadmap_manifest_path(root)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_area_manifest(root: Path, area_id: str) -> dict | None:
    path = roadmap_area_manifest_path(root, area_id)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def has_area_layout(root: Path) -> bool:
    return roadmap_manifest_path(root).exists() and roadmap_areas_dir(root).is_dir()


def has_flat_layout(root: Path) -> bool:
    rdir = resolve_roadmap_dir(root).path
    return (rdir / "items").is_dir()


def discover_areas(root: Path) -> list[str]:
    areas_dir = roadmap_areas_dir(root)
    if not areas_dir.is_dir():
        return []
    result = []
    for entry in sorted(areas_dir.iterdir()):
        if entry.is_dir() and (entry / ROADMAP_MANIFEST_FILE).exists():
            result.append(entry.name)
    return result


def find_project_root(start: Path | None = None) -> Path:
    cwd = (start or Path.cwd()).resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / AI_DIR / MEMORY_SUBDIR).is_dir():
            return parent
        if (parent / AI_DIR / ROADMAP_SUBDIR).is_dir():
            return parent
        if (parent / LEGACY_MEMORY_DIR).is_dir():
            return parent
        if (parent / LEGACY_ROADMAP_DIR).is_dir():
            return parent
        if (parent / "openspec").is_dir():
            return parent
        if (parent / ".git").is_dir():
            return parent
    return cwd
