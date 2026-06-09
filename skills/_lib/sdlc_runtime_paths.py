from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


AI_DIR = ".ai"
MEMORY_SUBDIR = "memory"
ROADMAP_SUBDIR = "roadmap"
LEGACY_MEMORY_DIR = ".ai-memory"
LEGACY_ROADMAP_DIR = ".roadmap"


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
