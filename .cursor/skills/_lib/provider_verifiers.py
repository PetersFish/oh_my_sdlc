from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .sdlc_runtime_paths import resolve_memory_dir
from .wrapper_contracts import make_blocker


Verifier = Callable[..., List[Dict[str, str]]]


def _openspec_change_dir(repo_root: Path, change_id: Optional[str]) -> Optional[Path]:
    if not change_id:
        return None
    return repo_root / "openspec" / "changes" / change_id


def verify_openspec_create(repo_root: Path | str, change_id: Optional[str] = None, **_: object) -> List[Dict[str, str]]:
    root = Path(repo_root)
    change_dir = _openspec_change_dir(root, change_id)
    if change_dir is None:
        return [make_blocker(
            reason="missing_change_id",
            message="openspec.create verification requires change_id",
            recommended_action="Pass change_id so the verifier can inspect the generated change artifacts",
        )]

    required_paths = [
        change_dir / "proposal.md",
        change_dir / "design.md",
        change_dir / "tasks.md",
    ]
    missing = [path.name for path in required_paths if not path.exists()]

    has_spec_artifact = (change_dir / "spec.md").exists() or any((change_dir / "specs").glob("**/*.md"))
    if not has_spec_artifact:
        missing.append("specs/**/*.md")

    if missing:
        return [make_blocker(
            reason="missing_required_artifact",
            message=f"openspec.create missing required artifacts: {', '.join(missing)}",
            recommended_action="Re-run openspec artifact creation or restore the missing change artifacts",
        )]

    return []


def verify_local_repository_sync(repo_root: Path | str, **_: object) -> List[Dict[str, str]]:
    root = Path(repo_root)
    memory_dir = resolve_memory_dir(root).path
    manifest_path = memory_dir / "manifest.json"
    index_path = memory_dir / "index.json"

    missing = [path.name for path in (manifest_path, index_path) if not path.exists()]
    if missing:
        return [make_blocker(
            reason="memory_sync_artifacts_missing",
            message=f"local.repository_sync missing required memory artifacts: {', '.join(missing)}",
            recommended_action="Run repository memory sync before marking the provider verification complete",
        )]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [make_blocker(
            reason="memory_sync_artifacts_invalid",
            message=f"local.repository_sync could not parse memory artifacts: {exc}",
            recommended_action="Repair the generated memory manifest/index and re-run memory sync",
        )]

    last_sync = manifest.get("last_sync")
    last_synced_commit = manifest.get("git", {}).get("last_synced_commit")
    entries = index_data.get("entries")
    if not isinstance(entries, list) or (not last_sync and not last_synced_commit):
        return [make_blocker(
            reason="memory_sync_state_not_observed",
            message="local.repository_sync could not observe synced memory state from manifest/index",
            recommended_action="Re-run repository memory sync until manifest last_sync or git.last_synced_commit is recorded",
        )]

    return []


PROVIDER_VERIFIERS: Dict[str, Verifier] = {
    "openspec.create": verify_openspec_create,
    "local.repository_sync": verify_local_repository_sync,
}


def get_provider_verifier(target: str) -> Optional[Verifier]:
    return PROVIDER_VERIFIERS.get(target)


def verify_provider_artifacts(target: str, repo_root: Path | str, **kwargs: object) -> List[Dict[str, str]]:
    verifier = get_provider_verifier(target)
    if verifier is None:
        return [make_blocker(
            reason="unknown_provider_verifier",
            message=f"No provider verifier registered for target {target!r}",
            recommended_action="Add a provider-specific verifier before relying on this verification target",
        )]
    return verifier(repo_root=repo_root, **kwargs)
