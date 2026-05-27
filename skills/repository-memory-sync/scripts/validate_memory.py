from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_SYNC_STATUSES = {"synced", "pending_commit", "needs_user_review"}
INDEX_STATUSES = {"synced", "pending_commit"}
VALID_MEMORY_TYPES = {"module", "architecture", "decisions", "pitfalls", "specs", "evolution", "sessions"}
VALID_EVIDENCE_MODES = {"commit", "uncommitted_snapshot", "session_observation", "spec_reference"}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_WORKTREE_STATES = {"clean", "dirty", "unknown"}
VALID_QUEUE_STATUSES = {"open", "resolved", "dismissed"}

FORMAL_DIRS = {"modules", "architecture", "decisions", "pitfalls", "specs", "evolution"}

REQUIRED_MANIFEST_FIELDS = {"schema_version", "repository_id", "memory_version", "git", "pending_snapshots"}
REQUIRED_GIT_FIELDS = {"available", "has_commits", "head", "last_synced_commit", "worktree_state"}
REQUIRED_INDEX_FIELDS = {"id", "type", "path", "title", "summary", "tags", "updated_at", "confidence", "status"}
REQUIRED_QUEUE_FIELDS = {"id", "type", "source_sync_id", "reason", "title", "source_refs", "status", "created_at"}
REQUIRED_FRONTMATTER_FIELDS = {"id", "type", "title", "summary", "sync_status", "evidence_mode", "linked_commits", "linked_specs", "linked_sessions", "updated_at", "confidence", "tags"}

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
        errors.append(f"manifest.json missing required fields: {', '.join(sorted(missing))}")

    git_data = data.get("git", {})
    if isinstance(git_data, dict):
        git_missing = REQUIRED_GIT_FIELDS - set(git_data.keys())
        if git_missing:
            errors.append(f"manifest.json git section missing fields: {', '.join(sorted(git_missing))}")
        if "worktree_state" in git_data and git_data["worktree_state"] not in VALID_WORKTREE_STATES:
            errors.append(f"manifest.json git.worktree_state invalid: {git_data['worktree_state']} (must be one of: {', '.join(sorted(VALID_WORKTREE_STATES))})")

    if "pending_snapshots" in data and not isinstance(data["pending_snapshots"], list):
        errors.append("manifest.json pending_snapshots must be an array")

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

    for field in ("schema_version", "generated_at", "entries"):
        if field not in data:
            errors.append(f"index.json missing required field: {field}")

    entries = data.get("entries", [])
    if not isinstance(entries, list):
        errors.append("index.json 'entries' is not a list")
        return errors

    for i, entry in enumerate(entries):
        missing = REQUIRED_INDEX_FIELDS - set(entry.keys())
        if missing:
            errors.append(f"index.json entry {i} missing fields: {', '.join(sorted(missing))}")
        if "status" in entry and entry["status"] not in INDEX_STATUSES:
            errors.append(f"index.json entry {i} invalid status '{entry['status']}' (must be one of: {', '.join(sorted(INDEX_STATUSES))})")
        if "type" in entry and entry["type"] not in VALID_MEMORY_TYPES:
            errors.append(f"index.json entry {i} invalid type '{entry['type']}' (must be one of: {', '.join(sorted(VALID_MEMORY_TYPES))})")
        if "confidence" in entry and entry["confidence"] not in VALID_CONFIDENCE:
            errors.append(f"index.json entry {i} invalid confidence '{entry['confidence']}'")

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

    if "items" not in data:
        errors.append("review-queue.json missing required field: items")
        return errors

    items = data["items"]
    if not isinstance(items, list):
        errors.append("review-queue.json 'items' is not a list")
        return errors

    for i, item in enumerate(items):
        missing = REQUIRED_QUEUE_FIELDS - set(item.keys())
        if missing:
            errors.append(f"review-queue.json item {i} missing fields: {', '.join(sorted(missing))}")
        if "status" in item and item["status"] not in VALID_QUEUE_STATUSES:
            errors.append(f"review-queue.json item {i} invalid status '{item['status']}' (must be one of: {', '.join(sorted(VALID_QUEUE_STATUSES))})")

    return errors


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


def _validate_frontmatter_files(memory_dir: Path) -> list[str]:
    errors: list[str] = []
    for formal_dir in FORMAL_DIRS:
        dir_path = memory_dir / formal_dir
        if not dir_path.is_dir():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            relative = str(md_file.relative_to(memory_dir))
            content = md_file.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)
            if fm is None:
                if not content.startswith(FRONTMATTER_DELIMITER):
                    errors.append(f"{relative}: missing opening frontmatter delimiter")
                else:
                    errors.append(f"{relative}: missing closing frontmatter delimiter")
                continue

            missing = REQUIRED_FRONTMATTER_FIELDS - set(fm.keys())
            if missing:
                errors.append(f"{relative}: missing frontmatter fields: {', '.join(sorted(missing))}")

            if "type" in fm and fm["type"] not in VALID_MEMORY_TYPES:
                errors.append(f"{relative}: invalid type '{fm['type']}' (must be one of: {', '.join(sorted(VALID_MEMORY_TYPES))})")

            if "sync_status" in fm and fm["sync_status"] not in VALID_SYNC_STATUSES:
                errors.append(f"{relative}: invalid sync_status '{fm['sync_status']}' (must be one of: {', '.join(sorted(VALID_SYNC_STATUSES))})")

            if "evidence_mode" in fm and fm["evidence_mode"] not in VALID_EVIDENCE_MODES:
                errors.append(f"{relative}: invalid evidence_mode '{fm['evidence_mode']}' (must be one of: {', '.join(sorted(VALID_EVIDENCE_MODES))})")

            if "confidence" in fm and fm["confidence"] not in VALID_CONFIDENCE:
                errors.append(f"{relative}: invalid confidence '{fm['confidence']}' (must be one of: {', '.join(sorted(VALID_CONFIDENCE))})")

    return errors


def _validate_sync_history_not_in_index(memory_dir: Path, index_path: Path) -> list[str]:
    errors: list[str] = []
    sync_history_dir = memory_dir / "sync-history"
    if not sync_history_dir.is_dir():
        return errors

    index_entries: set[str] = set()
    if index_path.exists():
        try:
            index_data = json.loads(index_path.read_text(encoding="utf-8"))
            for entry in index_data.get("entries", []):
                path = entry.get("path", "")
                index_entries.add(path)
        except (json.JSONDecodeError, OSError):
            pass

    for md_file in sorted(sync_history_dir.glob("*.md")):
        relative = str(md_file.relative_to(memory_dir))
        if relative in index_entries:
            errors.append(f"sync-history entry {relative} must not be in index.json")

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

    frontmatter_errors = _validate_frontmatter_files(memory_dir)
    all_errors.extend(frontmatter_errors)

    sync_history_errors = _validate_sync_history_not_in_index(memory_dir, memory_dir / "index.json")
    all_errors.extend(sync_history_errors)

    manifest_valid = len(manifest_errors) == 0
    index_valid = len(index_errors) == 0
    queue_valid = len(queue_errors) == 0
    frontmatter_valid = len(frontmatter_errors) == 0
    sync_history_valid = len(sync_history_errors) == 0

    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "counts": {
            "manifest": {"valid": manifest_valid, "invalid": not manifest_valid},
            "index": {"valid": index_valid, "invalid": not index_valid},
            "review_queue": {"valid": queue_valid, "invalid": not queue_valid},
            "frontmatter": {"valid": frontmatter_valid, "invalid": not frontmatter_valid},
            "sync_history": {"valid": sync_history_valid, "invalid": not sync_history_valid},
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