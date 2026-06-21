from __future__ import annotations

from datetime import datetime, timezone


def build_install_metadata(
    *,
    skill_name: str,
    source_repo: str,
    source_ref: str,
    status: str,
    target: str,
    backport_policy: str = "review-required",
) -> dict[str, str]:
    return {
        "skill": skill_name,
        "source_repo": source_repo,
        "source_ref": source_ref,
        "status": status,
        "target": target,
        "installed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "backport_policy": backport_policy,
    }


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
