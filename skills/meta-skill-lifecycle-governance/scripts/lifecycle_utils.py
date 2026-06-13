from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path


def build_install_metadata(
    *,
    skill_name: str,
    source_repo: str,
    source_ref: str,
    status: str,
    target: str,
    backport_policy: str = "review-required",
    source_skill_dir: Path | None = None,
) -> dict[str, str | list[str]]:
    metadata: dict[str, str | list[str]] = {
        "skill": skill_name,
        "source_repo": source_repo,
        "source_ref": source_ref,
        "status": status,
        "target": target,
        "installed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "backport_policy": backport_policy,
    }

    if source_skill_dir is not None:
        try:
            source_repo_path = Path(source_repo).resolve()
            source_path = str(source_skill_dir.resolve().relative_to(source_repo_path))
        except ValueError:
            source_path = source_skill_dir.name
        metadata["source_path"] = source_path

        hasher = hashlib.sha256()
        file_list: list[str] = []
        for f in sorted(source_skill_dir.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(source_skill_dir))
                file_list.append(rel)
                hasher.update(f.read_bytes())
        metadata["payload_hash"] = hasher.hexdigest()
        metadata["files"] = file_list

    return metadata


def classify_backport_candidate(note: str) -> str:
    text = note.lower()

    if any(
        marker in text
        for marker in (
            "temporary",
            "workaround",
            "for now",
            "hotfix",
        )
    ):
        return "temporary-workaround"

    if any(
        marker in text
        for marker in (
            "project-specific",
            "current project",
            "project naming scheme",
            "private path",
            "vault path",
            "hardcodes",
            "local-only",
            "workspace-specific",
        )
    ):
        return "project-overlay"

    return "generic-improvement"
