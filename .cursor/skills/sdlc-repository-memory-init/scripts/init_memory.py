from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

SUBDIRS = [
    "modules",
    "architecture",
    "decisions",
    "pitfalls",
    "specs",
    "evolution",
    "sync-history",
    "sessions",
    "snapshots",
    "tmp",
    "cache",
]

GITIGNORE_CONTENT = """\
sessions/
snapshots/
tmp/
cache/
*.local.json
"""


def _load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


def init_memory(root: Path) -> dict:
    memory_dir = root / ".ai-memory"
    created: list[str] = []
    skipped: list[str] = []

    for subdir in SUBDIRS:
        d = memory_dir / subdir
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d.relative_to(root)))
        else:
            skipped.append(str(d.relative_to(root)))

    discovery_prefs_content = json.dumps({
        "schema_version": "1.0",
        "exclude_patterns": [
            ".git", ".ai-memory", "node_modules", "__pycache__",
            ".venv", "venv", ".pytest_cache", ".mypy_cache",
            ".ruff_cache", ".tox", "dist", "build", "target",
            ".idea", ".vscode",
        ],
        "scan_paths": None,
        "max_depth": 5,
        "module_map": {},
    }, indent=2) + "\n"

    template_files = {
        "manifest.json": _load_template("manifest.json"),
        "index.json": _load_template("index.json"),
        "review-queue.json": _load_template("review-queue.json"),
        "discovery-prefs.json": discovery_prefs_content,
    }

    for filename, content in template_files.items():
        filepath = memory_dir / filename
        if not filepath.exists():
            filepath.write_text(content, encoding="utf-8")
            created.append(str(filepath.relative_to(root)))
        else:
            skipped.append(str(filepath.relative_to(root)))

    gitignore_path = memory_dir / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        created.append(str(gitignore_path.relative_to(root)))
    else:
        skipped.append(str(gitignore_path.relative_to(root)))

    agents_md = root / "AGENTS.md"
    agents_status = "missing"
    if agents_md.exists():
        agents_status = "present"

    return {
        "created": created,
        "skipped": skipped,
        "agents_md_status": agents_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize .ai-memory/ in a repository.")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    result = init_memory(root)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Repository Memory initialized at {root}/.ai-memory/")
        print()
        if result["created"]:
            print("Created:")
            for item in result["created"]:
                print(f"  {item}")
        if result["skipped"]:
            print("Skipped (already existed):")
            for item in result["skipped"]:
                print(f"  {item}")
        print()
        if result["agents_md_status"] == "present":
            print("AGENTS.md: found at repository root")
        else:
            print("AGENTS.md: not found at repository root")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())