from __future__ import annotations

import argparse
import json
import subprocess
import sys
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


def _detect_git(root: Path) -> dict:
    git_dir = root / ".git"
    if not git_dir.exists():
        return {
            "available": False,
            "has_commits": False,
            "head": None,
            "worktree_state": "unknown",
            "last_synced_commit": None,
            "committed_range": None,
            "dirty_files": [],
            "staged_files": [],
        }

    count = _run_git(root, "rev-list", "--count", "HEAD")
    has_commits = count is not None and int(count) > 0

    head = None
    if has_commits:
        head = _run_git(root, "rev-parse", "HEAD")

    manifest_path = resolve_memory_dir(root).path / "manifest.json"
    last_synced_commit = None
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            last_synced_commit = manifest.get("git", {}).get("last_synced_commit")
        except (json.JSONDecodeError, OSError):
            pass

    committed_range = None
    if last_synced_commit and head:
        committed_range = f"{last_synced_commit}..{head}"

    worktree_state = "unknown"
    if has_commits:
        status_output = _run_git(root, "status", "--porcelain")
        if status_output is not None:
            worktree_state = "dirty" if status_output else "clean"

    dirty_files: list[str] = []
    staged_files: list[str] = []

    if has_commits:
        diff_output = _run_git(root, "diff", "--name-only", "HEAD")
        if diff_output:
            dirty_files.extend(diff_output.splitlines())

        diff_cached = _run_git(root, "diff", "--cached", "--name-only")
        if diff_cached:
            staged_files.extend(diff_cached.splitlines())
            for f in diff_cached.splitlines():
                if f not in dirty_files:
                    dirty_files.append(f)

    return {
        "available": True,
        "has_commits": has_commits,
        "head": head,
        "worktree_state": worktree_state,
        "last_synced_commit": last_synced_commit,
        "committed_range": committed_range,
        "dirty_files": sorted(set(dirty_files)),
        "staged_files": sorted(set(staged_files)),
    }


def _detect_openspec_candidates(
    root: Path, committed_range: str | None, dirty_files: list[str], staged_files: list[str]
) -> dict:
    candidates: list[dict] = []
    change_ids: set[str] = set()
    seen_sources: dict[str, str] = {}

    all_files = set(dirty_files + staged_files)
    if committed_range and ".." in committed_range:
        log_output = _run_git(root, "diff", "--name-only", committed_range)
        if log_output:
            all_files.update(log_output.splitlines())

    for filepath in all_files:
        parts = Path(filepath).parts
        found = False
        for i, part in enumerate(parts):
            if part == "changes" and i > 0 and parts[i - 1] == "openspec":
                if i + 1 < len(parts):
                    change_id = parts[i + 1]
                    if change_id not in seen_sources:
                        seen_sources[change_id] = "git_diff"
                        change_ids.add(change_id)
                    found = True
                    break
        if not found:
            normalized = filepath.replace("\\", "/")
            if "openspec/changes/" in normalized:
                start = normalized.index("openspec/changes/") + len("openspec/changes/")
                rest = normalized[start:]
                change_id = rest.split("/")[0]
                if change_id not in seen_sources:
                    seen_sources[change_id] = "git_diff"
                    change_ids.add(change_id)

    for change_id in change_ids:
        candidates.append({
            "change_id": change_id,
            "source": seen_sources.get(change_id, "git_diff"),
            "confidence": "high",
        })

    active_changes: list[str] = []
    openspec_dir = root / "openspec" / "changes"
    if openspec_dir.is_dir():
        for entry in sorted(openspec_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                active_changes.append(entry.name)

    return {
        "candidates": candidates,
        "active_changes": active_changes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect git and OpenSpec state for memory sync")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    git_state = _detect_git(root)
    openspec_state = _detect_openspec_candidates(
        root,
        git_state.get("committed_range"),
        git_state.get("dirty_files", []),
        git_state.get("staged_files", []),
    )

    manifest_path = resolve_memory_dir(root).path / "manifest.json"
    pending_snapshots: list[str] = []
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            pending_snapshots = manifest.get("pending_snapshots", [])
        except (json.JSONDecodeError, OSError):
            pass

    result = {
        "git": git_state,
        "openspec": openspec_state,
        "pending_snapshots": pending_snapshots,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Git State:")
        for key, value in git_state.items():
            print(f"  {key}: {value}")
        print("OpenSpec Candidates:")
        for c in openspec_state["candidates"]:
            print(f"  - {c['change_id']} (source: {c['source']}, confidence: {c['confidence']})")
        if openspec_state["active_changes"]:
            print(f"Active Changes: {', '.join(openspec_state['active_changes'])}")
        print(f"Pending Snapshots: {pending_snapshots}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())