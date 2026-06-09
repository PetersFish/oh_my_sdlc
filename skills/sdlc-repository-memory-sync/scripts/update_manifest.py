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


SYNC_HISTORY_TEMPLATE = """# Sync History: {sync_id}

## Changed Files

## Evidence Used

## Memory Deltas

## Review Required

## Confidence
"""


def update_manifest(root: Path, sync_id: str | None = None, write: bool = False) -> dict:
    memory_dir = resolve_memory_dir(root).path
    manifest_path = memory_dir / "manifest.json"

    manifest: dict = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest = {}
    else:
        manifest = {
            "schema_version": "1.0",
            "repository_id": root.name,
            "memory_version": 1,
            "git": {},
            "pending_snapshots": [],
            "last_sync": None,
        }

    head = None
    worktree_state = "unknown"
    has_git = (root / ".git").exists()

    if has_git:
        head = _run_git(root, "rev-parse", "HEAD")
        status_output = _run_git(root, "status", "--porcelain")
        if status_output is not None:
            worktree_state = "dirty" if status_output else "clean"

    git = manifest.get("git", {})
    if not isinstance(git, dict):
        git = {}

    previous_head = git.get("head")
    git["available"] = has_git
    git["has_commits"] = head is not None
    git["head"] = head
    git["last_synced_commit"] = head
    git["worktree_state"] = worktree_state
    manifest["git"] = git

    if sync_id:
        manifest["last_sync"] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "commit": head or "",
            "snapshot_id": sync_id,
        }
    else:
        manifest["last_sync"] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "commit": head or "",
            "snapshot_id": "",
        }

    manifest.setdefault("schema_version", "1.0")
    manifest.setdefault("repository_id", root.name)
    manifest.setdefault("memory_version", 1)
    manifest.setdefault("pending_snapshots", [])

    if write:
        memory_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        if sync_id:
            sync_history_dir = memory_dir / "sync-history"
            sync_history_dir.mkdir(parents=True, exist_ok=True)
            sync_history_path = sync_history_dir / f"{sync_id}.md"
            if not sync_history_path.exists():
                sync_history_path.write_text(
                    SYNC_HISTORY_TEMPLATE.format(sync_id=sync_id),
                    encoding="utf-8",
                )

    return {
        "status": "ok",
        "manifest": manifest,
        "written": write,
        "sync_id": sync_id,
        "previous_head": previous_head,
        "new_head": head,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Update .ai/memory/manifest.json after sync")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--write", action="store_true", help="Write updated manifest to disk")
    parser.add_argument("--sync-id", default=None, help="Sync ID for this sync operation")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    result = update_manifest(root, sync_id=args.sync_id, write=args.write)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Manifest updated: {result['status']}")
        print(f"  HEAD: {result.get('previous_head', 'unknown')} -> {result.get('new_head', 'unknown')}")
        if result.get("sync_id"):
            print(f"  Sync ID: {result['sync_id']}")
        if result["written"]:
            print("  Manifest written to disk.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())