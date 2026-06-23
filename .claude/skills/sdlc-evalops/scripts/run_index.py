"""Shared run index helpers for EvalOps runner scripts."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def load_run_index(reports_dir: Path) -> dict:
    """Load run index from reports_dir/run-index.json, returning empty dict if absent."""
    index_path = reports_dir / "run-index.json"
    if not index_path.is_file():
        return {"target_id": "", "runs": []}
    return json.loads(index_path.read_text("utf-8"))


def save_run_index(reports_dir: Path, index_data: dict) -> None:
    """Save run index to reports_dir/run-index.json."""
    index_path = reports_dir / "run-index.json"
    reports_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index_data, indent=2, default=str) + "\n", encoding="utf-8")


def get_git_baseline(repo_root: Path) -> str | None:
    """Return HEAD commit hash as Git baseline."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def get_changed_golden_files(repo_root: Path, baseline: str, golden_dir: Path) -> list[str]:
    """Return list of golden case file *basenames* changed relative to baseline."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", baseline, "--", str(golden_dir) + "/"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=10,
        )
        if result.returncode == 0:
            basenames = set()
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    basenames.add(os.path.basename(line))
            return sorted(basenames)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return []


def find_last_full_run(runs: list[dict]) -> dict | None:
    """Return the most recent run entry with mode 'full', or None."""
    full_runs = [r for r in runs if r.get("mode") == "full"]
    if not full_runs:
        return None
    return sorted(full_runs, key=lambda r: r.get("timestamp", ""), reverse=True)[0]


def find_latest_run(runs: list[dict]) -> dict | None:
    """Return the most recent run entry regardless of mode, or None."""
    if not runs:
        return None
    return sorted(runs, key=lambda r: r.get("timestamp", ""), reverse=True)[0]


def build_run_entry(run_id: str, mode: str, git_baseline: str | None,
                    case_files: dict, case_status: dict, failed_cases: list[str],
                    report_path: str, failure_source: str | None = None) -> dict:
    """Build a run index entry dict."""
    entry = {
        "run_id": run_id,
        "mode": mode,
        "git_baseline": git_baseline,
        "case_files": case_files,
        "case_status": case_status,
        "failed_cases": failed_cases,
        "report_path": report_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if failure_source:
        entry["failure_source"] = failure_source
    return entry
