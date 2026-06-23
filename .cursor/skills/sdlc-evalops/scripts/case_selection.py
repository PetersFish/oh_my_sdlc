"""Shared case selection and identity helpers for EvalOps runner scripts."""

from __future__ import annotations

import hashlib
from pathlib import Path


def get_case_identity(case: dict, golden_dir: Path) -> tuple[str, str, str, str]:
    """Return (case_id, file_name, content_hash, canonical_path_abs).

    case_id is from case.get('id'). file_name is from case.get('_file').
    content_hash is sha256 of the golden YAML file content.
    canonical_path_abs is the absolute path to the golden YAML file.
    """
    case_id = case.get("id", case.get("_file", "?"))
    file_name = case.get("_file", "")
    file_path = golden_dir / file_name
    content_hash = ""
    if file_path.is_file():
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return case_id, file_name, content_hash, str(file_path)


def collect_case_files(selected_cases: list[dict], golden_dir: Path) -> dict:
    """Build case_files dict for run index entry."""
    case_files = {}
    for case in selected_cases:
        case_id, file_name, content_hash, _abs_path = get_case_identity(case, golden_dir)
        case_files[case_id] = {"file": file_name, "hash": content_hash}
    return case_files


def select_only_new(golden_cases: list[dict], changed_files: list[str]) -> list[dict]:
    """Return cases whose _file is in changed_files (basenames)."""
    selected = [c for c in golden_cases if c.get("_file") in changed_files]
    return selected


def select_only_failed(golden_cases: list[dict], failed_ids: list[str]) -> list[dict]:
    """Return cases whose id is in failed_ids. Silently skips unmatched ids."""
    by_id = {c.get("id"): c for c in golden_cases}
    selected = []
    for fid in failed_ids:
        case = by_id.get(fid)
        if case:
            selected.append(case)
    return selected


def build_case_status(eval_results: list[dict], selected_cases: list[dict]) -> tuple[dict, list[str]]:
    """Build case_status dict and failed_cases list from Promptfoo eval results.

    eval_results are the parsed 'cases' list from parse_promptfoo_output().
    selected_cases are the case dicts that were actually run.

    Returns (case_status, failed_cases).
    case_status: {case_id: "passed" | "failed"}
    failed_cases: [case_id]

    Assumes eval_results[i] corresponds to selected_cases[i] (Promptfoo preserves
    input case ordering in its output).
    """
    case_status = {}
    failed_cases = []
    for idx, case in enumerate(selected_cases):
        case_id = case.get("id", "?")
        if idx < len(eval_results):
            passed = eval_results[idx].get("passed", False)
        else:
            passed = True
        status = "passed" if passed else "failed"
        case_status[case_id] = status
        if not passed:
            failed_cases.append(case_id)
    return case_status, failed_cases
