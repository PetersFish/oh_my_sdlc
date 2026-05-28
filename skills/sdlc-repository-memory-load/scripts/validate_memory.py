from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_SYNC_STATUSES = {"synced", "pending_commit", "needs_user_review"}
VALID_MEMORY_TYPES = {"module", "architecture", "decisions", "pitfalls", "specs", "evolution", "sessions"}

FORMAL_DIRS = {"modules", "architecture", "decisions", "pitfalls", "specs", "evolution"}

REQUIRED_INDEX_FIELDS = {"title", "summary", "path", "type", "tags"}
REQUIRED_MANIFEST_FIELDS = {"schema_version", "memory_version", "git"}
REQUIRED_QUEUE_ITEM_FIELDS = {"id", "path", "action", "status"}

FRONTMATTER_DELIMITER = "---"


def _validate_manifest(manifest_path: Path) -> list[str]:
    errors: list[str] = []
    if not manifest_path.exists():
        errors.append(f"manifest.json not found at {manifest_path}")
        return errors
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"manifest.json is invalid JSON: {e}")
        return errors

    missing = REQUIRED_MANIFEST_FIELDS - set(data.keys())
    if missing:
        errors.append(f"manifest.json missing fields: {', '.join(sorted(missing))}")
    return errors


def _validate_index(index_path: Path) -> list[str]:
    errors: list[str] = []
    if not index_path.exists():
        errors.append(f"index.json not found at {index_path}")
        return errors
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"index.json is invalid JSON: {e}")
        return errors

    entries = data.get("entries", [])
    if not isinstance(entries, list):
        errors.append("index.json 'entries' is not a list")
        return errors

    for i, entry in enumerate(entries):
        missing = REQUIRED_INDEX_FIELDS - set(entry.keys())
        if missing:
            errors.append(f"index.json entry {i} missing fields: {', '.join(sorted(missing))}")
        status = entry.get("status", entry.get("sync_status"))
        if status is None:
            errors.append(f"index.json entry {i} missing fields: status")
        elif status not in VALID_SYNC_STATUSES:
            errors.append(f"index.json entry {i} invalid status: {status}")
        if "type" in entry and entry["type"] not in VALID_MEMORY_TYPES:
            errors.append(f"index.json entry {i} invalid type: {entry['type']}")
    return errors


def _validate_review_queue(queue_path: Path) -> list[str]:
    errors: list[str] = []
    if not queue_path.exists():
        return errors
    try:
        data = json.loads(queue_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"review-queue.json is invalid JSON: {e}")
        return errors

    items = data.get("items", [])
    for i, item in enumerate(items):
        missing = REQUIRED_QUEUE_ITEM_FIELDS - set(item.keys())
        if missing:
            errors.append(f"review-queue.json item {i} missing fields: {', '.join(sorted(missing))}")
    return errors


def _validate_frontmatter(filepath: Path) -> list[str]:
    errors: list[str] = []
    if not filepath.exists():
        errors.append(f"file not found: {filepath}")
        return errors
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith(FRONTMATTER_DELIMITER):
        errors.append(f"{filepath.name}: missing opening frontmatter delimiter")
        return errors
    parts = content.split(FRONTMATTER_DELIMITER)
    if len(parts) < 3:
        errors.append(f"{filepath.name}: missing closing frontmatter delimiter")
        return errors
    try:
        frontmatter_text = parts[1]
        json.loads("{}")
        import yaml
    except Exception:
        pass
    if "sync_status" not in parts[1] or "type" not in parts[1]:
        pass
    return errors


def _validate_memory_files(memory_dir: Path) -> list[str]:
    errors: list[str] = []
    for formal_dir in FORMAL_DIRS:
        dir_path = memory_dir / formal_dir
        if not dir_path.is_dir():
            continue
        for md_file in sorted(dir_path.glob("**/*.md")):
            content = md_file.read_text(encoding="utf-8")
            if not content.startswith(FRONTMATTER_DELIMITER):
                errors.append(f"{md_file.relative_to(memory_dir)}: missing opening frontmatter delimiter")
                continue
            parts = content.split(FRONTMATTER_DELIMITER)
            if len(parts) < 3:
                errors.append(f"{md_file.relative_to(memory_dir)}: missing closing frontmatter delimiter")
                continue
            frontmatter = parts[1].strip()
            if "sync_status:" not in frontmatter:
                errors.append(f"{md_file.relative_to(memory_dir)}: missing sync_status in frontmatter")
            if "type:" not in frontmatter:
                errors.append(f"{md_file.relative_to(memory_dir)}: missing type in frontmatter")
            else:
                for line in frontmatter.splitlines():
                    if line.startswith("sync_status:"):
                        status = line.split(":", 1)[1].strip()
                        if status not in VALID_SYNC_STATUSES:
                            errors.append(f"{md_file.relative_to(memory_dir)}: invalid sync_status '{status}'")
                    if line.startswith("type:"):
                        mem_type = line.split(":", 1)[1].strip()
                        if mem_type not in VALID_MEMORY_TYPES:
                            errors.append(f"{md_file.relative_to(memory_dir)}: invalid type '{mem_type}'")
    return errors


def validate_memory(root: Path) -> dict:
    memory_dir = root / ".ai-memory"
    all_errors: list[str] = []

    manifest_errors = _validate_manifest(memory_dir / "manifest.json")
    all_errors.extend(manifest_errors)

    index_errors = _validate_index(memory_dir / "index.json")
    all_errors.extend(index_errors)

    queue_errors = _validate_review_queue(memory_dir / "review-queue.json")
    all_errors.extend(queue_errors)

    file_errors = _validate_memory_files(memory_dir)
    all_errors.extend(file_errors)

    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "checked": {
            "manifest": (memory_dir / "manifest.json").exists(),
            "index": (memory_dir / "index.json").exists(),
            "review_queue": (memory_dir / "review-queue.json").exists(),
            "memory_files": len(all_errors) == len(manifest_errors) + len(index_errors) + len(queue_errors) and len(file_errors) == 0 or len(file_errors) > 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate .ai-memory/ structure and content")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    result = validate_memory(root)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["valid"]:
            print("All memory files are valid.")
        else:
            print(f"Found {len(result['errors'])} error(s):")
            for err in result["errors"]:
                print(f"  - {err}")

    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
