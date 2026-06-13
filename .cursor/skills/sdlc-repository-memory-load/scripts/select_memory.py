from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import resolve_memory_dir  # noqa: E402

EXCLUDED_PREFIXES = (
    "sync-history/",
    "sessions/",
    "snapshots/",
    "tmp/",
    "cache/",
)
EXCLUDED_FILES = {"review-queue.json"}


def _tokenize(text: str) -> set[str]:
    return set(t for t in re.split(r"[^a-z0-9_\-]+", text.lower()) if t)


def _list_tokens(values: object) -> set[str]:
    if not isinstance(values, list):
        return set()
    tokens: set[str] = set()
    for value in values:
        tokens.update(_tokenize(str(value)))
    return tokens


def _score_entry(entry: dict, query_tokens: set[str]) -> int:
    if not query_tokens:
        return 1
    score = 0
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    tags = entry.get("tags", [])
    path = entry.get("path", "")
    mem_type = entry.get("type", "")
    owned_paths = entry.get("owned_paths", [])
    path_hints = entry.get("path_hints", [])
    keywords = entry.get("keywords", [])
    test_paths = entry.get("test_paths", [])
    spec_paths = entry.get("spec_paths", [])

    title_tokens = _tokenize(title)
    summary_tokens = _tokenize(summary)
    tag_tokens = _list_tokens(tags)
    path_tokens = _tokenize(path)
    type_tokens = _tokenize(mem_type)
    owned_path_tokens = _list_tokens(owned_paths)
    path_hint_tokens = _list_tokens(path_hints)
    keyword_tokens = _list_tokens(keywords)
    test_path_tokens = _list_tokens(test_paths)
    spec_path_tokens = _list_tokens(spec_paths)

    score += len(query_tokens & title_tokens) * 3
    score += len(query_tokens & summary_tokens) * 2
    score += len(query_tokens & tag_tokens) * 2
    score += len(query_tokens & path_tokens)
    score += len(query_tokens & type_tokens)
    score += len(query_tokens & keyword_tokens) * 4
    score += len(query_tokens & path_hint_tokens) * 3
    score += len(query_tokens & owned_path_tokens) * 3
    score += len(query_tokens & test_path_tokens) * 2
    score += len(query_tokens & spec_path_tokens) * 2
    return score


def _is_excluded(path: str) -> bool:
    if any(path.startswith(p) for p in EXCLUDED_PREFIXES):
        return True
    filename = path.rsplit("/", 1)[-1] if "/" in path else path
    return filename in EXCLUDED_FILES


def select_memory(root: Path, query: str = "", max_results: int = 5) -> dict:
    memory_dir = resolve_memory_dir(root).path
    index_path = memory_dir / "index.json"
    manifest_path = memory_dir / "manifest.json"

    if not manifest_path.exists():
        return {
            "entries": [],
            "reason": "manifest.json missing; run sdlc-repository-memory-init first",
        }

    if not index_path.exists():
        return {
            "entries": [],
            "reason": "index.json missing; run sdlc-repository-memory-sync first",
        }

    try:
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"entries": [], "reason": "index.json is invalid"}

    all_entries = index_data.get("entries", [])
    eligible = [e for e in all_entries if not _is_excluded(e.get("path", ""))]

    query_tokens = _tokenize(query) if query else set()

    if query_tokens:
        scored = [(e, _score_entry(e, query_tokens)) for e in eligible]
        scored.sort(key=lambda x: x[1], reverse=True)
        filtered = [e for e, s in scored if s > 0]
    else:
        filtered = eligible

    selected = filtered[:max_results]

    return {
        "entries": selected,
        "total_eligible": len(eligible),
        "total_indexed": len(all_entries),
        "loaded": len(selected),
        "skipped_paths": [
            e.get("path", "")
            for e in all_entries
            if _is_excluded(e.get("path", ""))
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Select relevant memory entries from .ai/memory/index.json")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory)")
    parser.add_argument("--query", default="", help="Comma-separated search keywords")
    parser.add_argument("--max", type=int, default=5, help="Maximum results (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    query = args.query.replace(",", " ") if args.query else ""
    result = select_memory(root, query=query, max_results=args.max)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("reason"):
            print(result["reason"])
            return 0
        entries = result.get("entries", [])
        if not entries:
            print("No matching memory entries found.")
        else:
            print(f"Loaded {result['loaded']} of {result['total_eligible']} eligible entries:")
            for e in entries:
                print(f"  - {e.get('path', 'unknown')}: {e.get('title', 'untitled')}")
        skipped = result.get("skipped_paths", [])
        if skipped:
            print(f"Skipped {len(skipped)} excluded entries: {', '.join(skipped)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
