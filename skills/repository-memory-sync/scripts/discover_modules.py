from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BUILTIN_EXCLUDE = {
    ".git",
    ".ai-memory",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
}

BUILD_FILES = [
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Cargo.toml",
    "go.mod",
    "Makefile",
    "CMakeLists.txt",
    "tsconfig.json",
    ".csproj",
    "build.sbt",
    "Dockerfile",
]


def _parse_skill_frontmatter(skill_md_path: Path) -> tuple[str | None, str | None]:
    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except OSError:
        return None, None

    if not content.startswith("---"):
        return None, None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, None

    frontmatter: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()

    return frontmatter.get("name"), frontmatter.get("description")


def _load_prefs(memory_dir: Path) -> dict:
    prefs_path = memory_dir / "discovery-prefs.json"
    if not prefs_path.exists():
        return {
            "exclude_patterns": [],
            "scan_paths": None,
            "max_depth": 5,
            "module_map": {},
        }

    try:
        return json.loads(prefs_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "exclude_patterns": [],
            "scan_paths": None,
            "max_depth": 5,
            "module_map": {},
        }


def _count_recursive_files(dir_path: Path) -> int:
    count = 0
    try:
        for child in dir_path.iterdir():
            if child.name.startswith("."):
                continue
            if child.is_file():
                count += 1
            elif child.is_dir():
                count += _count_recursive_files(child)
    except PermissionError:
        pass
    return count


def _collect_file_types(dir_path: Path) -> Counter:
    counter: Counter[str] = Counter()
    try:
        for child in dir_path.iterdir():
            if child.name.startswith("."):
                continue
            if child.is_file():
                counter[child.suffix] += 1
            elif child.is_dir():
                counter.update(_collect_file_types(child))
    except PermissionError:
        pass
    return counter


def _detect_build_file(dir_path: Path) -> str | None:
    for bf in BUILD_FILES:
        if (dir_path / bf).is_file():
            return bf
    return None


def _scan_top_level(dir_path: Path) -> list[str]:
    entries: list[str] = []
    try:
        children = sorted(dir_path.iterdir(), key=lambda c: c.name)
        for child in children:
            if child.name.startswith("."):
                continue
            if child.is_file():
                entries.append(child.name)
            elif child.is_dir():
                entries.append(child.name + "/")
            if len(entries) >= 10:
                break
    except PermissionError:
        pass
    return entries


def _compute_disposition(path: str, module_map: dict) -> dict:
    for key, entry in module_map.items():
        if entry.get("fs_path") == path:
            status = entry.get("status", "pending")
            if status == "accepted":
                return {"disposition": "known", "reason": None}
            if status == "rejected":
                return {
                    "disposition": "previously_rejected",
                    "reason": entry.get("reason_rejected"),
                }
            return {"disposition": "new", "reason": None}
    return {"disposition": "new", "reason": None}


def discover_modules(root: Path) -> dict:
    prefs = _load_prefs(root / ".ai-memory")
    exclude_patterns = set(BUILTIN_EXCLUDE) | set(prefs.get("exclude_patterns", []))
    max_depth = prefs.get("max_depth", 5)
    module_map = prefs.get("module_map", {})

    total_dirs = 0
    excluded = 0
    candidates: list[dict] = []

    root = root.resolve()

    def walk(dir_path: Path, depth: int):
        nonlocal total_dirs, excluded

        if depth > max_depth:
            return

        try:
            children = list(dir_path.iterdir())
        except PermissionError:
            return

        for child in sorted(children, key=lambda c: c.name):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name in exclude_patterns:
                excluded += 1
                continue

            total_dirs += 1
            sub_children = sorted(
                [c for c in child.iterdir() if not c.name.startswith(".")],
                key=lambda c: c.name,
            )
            direct_files = [c for c in sub_children if c.is_file()]
            direct_subdirs = [c for c in sub_children if c.is_dir()]

            is_candidate = len(direct_files) >= 1 or len(direct_subdirs) >= 2

            if is_candidate:
                rel_path = str(child.relative_to(root))
                file_count = _count_recursive_files(child)
                file_types = dict(_collect_file_types(child))
                has_skill_md = (child / "SKILL.md").is_file()
                fm_name, fm_desc = None, None
                if has_skill_md:
                    fm_name, fm_desc = _parse_skill_frontmatter(child / "SKILL.md")
                disp = _compute_disposition(rel_path, module_map)
                build_file = _detect_build_file(child)
                top_level = _scan_top_level(child)
                children_count = len(direct_files) + len(direct_subdirs)

                candidates.append({
                    "name": child.name,
                    "path": rel_path,
                    "depth": depth,
                    "file_count": file_count,
                    "file_types": file_types,
                    "has_build_file": build_file,
                    "has_skill_md": has_skill_md,
                    "frontmatter_name": fm_name,
                    "frontmatter_description": fm_desc,
                    "top_level_files": top_level,
                    "children_count": children_count,
                    "disposition": disp["disposition"],
                })

            walk(child, depth + 1)

    walk(root, 1)

    known = [c for c in candidates if c["disposition"] == "known"]
    previously_rejected = [c for c in candidates if c["disposition"] == "previously_rejected"]
    new_candidates = [c for c in candidates if c["disposition"] == "new"]

    return {
        "candidates": candidates,
        "stats": {
            "total_dirs": total_dirs,
            "excluded": excluded,
            "candidates": len(candidates),
            "known": len(known),
            "previously_rejected": len(previously_rejected),
            "new": len(new_candidates),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover module candidates from filesystem.")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    result = discover_modules(root)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        stats = result["stats"]
        print(f"Module Discovery: {stats['total_dirs']} dirs scanned, "
              f"{stats['candidates']} candidates")
        print(f"  Known: {stats['known']}  Previously rejected: {stats['previously_rejected']}  "
              f"New: {stats['new']}")
        print()
        for c in result["candidates"]:
            disp = c["disposition"]
            marker = {"known": "✓", "previously_rejected": "✗", "new": "?"}.get(disp, " ")
            build = f" [{c['has_build_file']}]" if c["has_build_file"] else ""
            print(f"  {marker} {c['path']} ({c['file_count']} files, depth={c['depth']}){build}"
                  f" [{disp}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
