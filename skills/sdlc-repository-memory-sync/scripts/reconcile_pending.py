from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import resolve_memory_dir  # noqa: E402

FRONTMATTER_DELIMITER = "---"
VALID_SYNC_STATUSES = {"synced", "pending_commit", "needs_user_review"}


def _run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


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


def _serialize_frontmatter(fm: dict) -> str:
    lines: list[str] = []
    for key, value in fm.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                formatted = ", ".join(str(v) for v in value)
                lines.append(f"{key}: [{formatted}]")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    return FRONTMATTER_DELIMITER + "\n" + "\n".join(lines) + "\n" + FRONTMATTER_DELIMITER


def _update_frontmatter_in_file(filepath: Path, updates: dict) -> None:
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith(FRONTMATTER_DELIMITER):
        return
    parts = content.split(FRONTMATTER_DELIMITER, 2)
    if len(parts) < 3:
        return

    fm = _parse_frontmatter(content)
    if fm is None:
        return

    fm.update(updates)
    new_frontmatter = _serialize_frontmatter(fm)
    new_content = new_frontmatter + "\n" + parts[2]
    if new_content.startswith("\n"):
        new_content = new_content
    filepath.write_text(new_content, encoding="utf-8")


def _check_file_committed(root: Path, filepath: str, head: str | None) -> bool:
    if head is None:
        return False
    result = _run_git(root, "log", "-1", "--format=%H", "--", filepath)
    return result is not None and result.strip() != ""


def _find_pending_files(memory_dir: Path) -> list[tuple[Path, dict]]:
    pending: list[tuple[Path, dict]] = []
    formal_dirs = ["modules", "architecture", "decisions", "pitfalls", "specs", "evolution"]
    for dir_name in formal_dirs:
        dir_path = memory_dir / dir_name
        if not dir_path.is_dir():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)
            if fm is None:
                continue
            if fm.get("sync_status") == "pending_commit":
                pending.append((md_file, fm))
    return pending


def reconcile_pending(root: Path, write: bool = False) -> dict:
    memory_dir = resolve_memory_dir(root).path
    manifest_path = memory_dir / "manifest.json"
    queue_path = memory_dir / "review-queue.json"

    manifest: dict = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest = {}

    pending_snapshots = manifest.get("pending_snapshots", [])
    head = None
    has_git = (root / ".git").exists()
    if has_git:
        head = _run_git(root, "rev-parse", "HEAD")

    pending_files = _find_pending_files(memory_dir)

    reconciled: list[dict] = []
    review_items: list[dict] = []

    for filepath, fm in pending_files:
        fm_id = fm.get("id", filepath.stem)
        snapshot_id = fm.get("snapshot_id", "")
        reconcile_commit = fm.get("reconcile_after_commit", "")
        linked_commits = fm.get("linked_commits", []) or []
        relative_path = str(filepath.relative_to(memory_dir))

        file_committed = False
        if has_git and head:
            committed_output = _run_git(root, "log", "-1", "--format=%H", "--", str(filepath.relative_to(root)))
            if committed_output:
                file_committed = True

        fully_matched = False
        partial_match = False

        if file_committed:
            if reconcile_commit:
                check = _run_git(root, "log", "--format=%H", f"{reconcile_commit}..HEAD", "--", str(filepath.relative_to(root)))
                if check:
                    fully_matched = True
                else:
                    partial_match = True
            else:
                fully_matched = True

        if fully_matched:
            updates = {
                "sync_status": "synced",
                "evidence_mode": "commit",
            }
            reconciled.append({
                "id": fm_id,
                "path": relative_path,
                "previous_status": "pending_commit",
                "new_status": "synced",
                "evidence_mode": "commit",
                "matched_commits": linked_commits,
            })
            if write:
                _update_frontmatter_in_file(filepath, updates)
        elif partial_match:
            review_id = f"review-{fm_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            review_items.append({
                "id": review_id,
                "type": fm.get("type", "module"),
                "source_sync_id": snapshot_id,
                "reason": "partial_reconcile",
                "title": fm.get("title", fm_id),
                "source_refs": {
                    "commits": linked_commits,
                    "specs": fm.get("linked_specs", []) or [],
                    "snapshot_id": snapshot_id or None,
                },
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            })
            if write:
                _update_frontmatter_in_file(filepath, {"sync_status": "needs_user_review", "review_reason": "partial_reconcile"})
        else:
            review_id = f"review-{fm_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            review_items.append({
                "id": review_id,
                "type": fm.get("type", "module"),
                "source_sync_id": snapshot_id,
                "reason": "no_matching_commit",
                "title": fm.get("title", fm_id),
                "source_refs": {
                    "commits": linked_commits,
                    "specs": fm.get("linked_specs", []) or [],
                    "snapshot_id": snapshot_id or None,
                },
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            })

    if write and review_items:
        existing_queue: dict = {"items": []}
        if queue_path.exists():
            try:
                existing_queue = json.loads(queue_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing_queue = {"items": []}

        existing_items = existing_queue.get("items", [])
        existing_ids = {item.get("id") for item in existing_items}
        for item in review_items:
            if item["id"] not in existing_ids:
                existing_items.append(item)
        existing_queue["items"] = existing_items

        queue_path.parent.mkdir(parents=True, exist_ok=True)
        queue_path.write_text(json.dumps(existing_queue, indent=2) + "\n", encoding="utf-8")

    return {
        "reconciled": reconciled,
        "review_items": review_items,
        "pending_snapshots_remaining": [s for s in pending_snapshots if s not in {r.get("id", "") for r in reconciled}],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile pending uncommitted snapshots against new commits")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--write", action="store_true", help="Write changes to memory files and review queue")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    result = reconcile_pending(root, write=args.write)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Reconciled: {len(result['reconciled'])} entries upgraded to synced")
        for r in result["reconciled"]:
            print(f"  - {r['id']}: {r['previous_status']} -> {r['new_status']}")
        print(f"Review items: {len(result['review_items'])} need user review")
        for item in result["review_items"]:
            print(f"  - {item['id']}: {item['reason']} ({item['title']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())