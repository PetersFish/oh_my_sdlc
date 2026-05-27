from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

FORMAL_DIRS = ("modules", "architecture", "decisions", "pitfalls", "specs", "evolution")
EXCLUDED_DIRS = ("sync-history", "sessions", "snapshots", "tmp", "cache")

INDEX_STATUSES = {"synced", "pending_commit"}

FRONTMATTER_DELIMITER = "---"


def _parse_frontmatter(content: str) -> dict | None:
    if not content.startswith(FRONTMATTER_DELIMITER):
        return None
    parts = content.split(FRONTMATTER_DELIMITER)
    if len(parts) < 3:
        return None
    frontmatter_text = parts[1].strip()
    parsed: dict = {}
    for line in frontmatter_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                if inner:
                    parsed[key] = [item.strip().strip("'\"") for item in inner.split(",")]
                else:
                    parsed[key] = []
            else:
                parsed[key] = value
    return parsed


def _extract_summary_from_body(body: str, fm_summary: str) -> str:
    if fm_summary and fm_summary != "None":
        return fm_summary
    for line in body.strip().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:200]
    return ""


def _scan_memory_files(memory_dir: Path) -> list[dict]:
    entries: list[dict] = []
    for dir_name in FORMAL_DIRS:
        dir_path = memory_dir / dir_name
        if not dir_path.is_dir():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)
            if fm is None:
                continue

            sync_status = fm.get("sync_status", "")
            if sync_status not in INDEX_STATUSES:
                continue

            relative_path = str(md_file.relative_to(memory_dir))
            entry_id = fm.get("id", md_file.stem)
            entry_type = fm.get("type", dir_name.rstrip("s"))
            if dir_name == "modules" and entry_type != "module":
                entry_type = "module"
            elif dir_name == "decisions":
                if entry_type not in ("decisions", "decision"):
                    entry_type = "decisions"
            elif dir_name == "pitfalls":
                if entry_type not in ("pitfalls", "pitfall"):
                    entry_type = "pitfalls"
            elif dir_name == "specs":
                if entry_type not in ("specs", "spec"):
                    entry_type = "specs"
            elif dir_name == "evolution":
                if entry_type not in ("evolution",):
                    entry_type = "evolution"
            elif dir_name == "architecture":
                if entry_type not in ("architecture",):
                    entry_type = "architecture"

            summary = str(fm.get("summary", ""))
            if not summary or summary == "None":
                parts = content.split(FRONTMATTER_DELIMITER)
                body = parts[2].strip() if len(parts) >= 3 else ""
                summary = _extract_summary_from_body(body, summary)

            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")] if tags else []
            elif not isinstance(tags, list):
                tags = []

            entries.append({
                "id": entry_id,
                "type": entry_type,
                "path": relative_path,
                "title": fm.get("title", md_file.stem),
                "summary": summary,
                "tags": tags,
                "updated_at": fm.get("updated_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
                "confidence": fm.get("confidence", "medium"),
                "status": sync_status,
            })

    return entries


def rebuild_index(root: Path, write: bool = False) -> dict:
    memory_dir = root / ".ai-memory"
    if not memory_dir.is_dir():
        return {
            "status": "error",
            "error": ".ai-memory/ directory not found",
            "entries": [],
        }

    entries = _scan_memory_files(memory_dir)

    index = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "entries": entries,
        "excluded_paths": [d + "/" for d in EXCLUDED_DIRS],
    }

    if write:
        index_path = memory_dir / "index.json"
        index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    return {
        "status": "ok",
        "entries": entries,
        "total": len(entries),
        "excluded_dirs": list(EXCLUDED_DIRS),
        "written": write,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild .ai-memory/index.json from memory files")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--write", action="store_true", help="Write rebuilt index to disk")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    result = rebuild_index(root, write=args.write)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["status"] == "error":
            print(f"Error: {result['error']}")
            return 1
        print(f"Rebuilt index: {result['total']} entries")
        for entry in result["entries"]:
            print(f"  - {entry['path']}: {entry['title']} [{entry['status']}]")
        print(f"Excluded dirs: {', '.join(result['excluded_dirs'])}")
        if result["written"]:
            print("Index written to disk.")

    return 0 if result["status"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())