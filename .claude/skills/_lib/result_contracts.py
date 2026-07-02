"""Contract normalizers for provider-verifier result contracts.

Each normalizer maps provider-verifier-specific results into a stable,
provider-verifier-agnostic evidence envelope.  A normalization failure or
missing contract returns a structured blocker dict.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from .wrapper_contracts import make_blocker, make_design_artifact_entry


Normalizer = Callable[[Dict[str, Any]], Dict[str, Any]]

# ---------------------------------------------------------------------------
# spec_change normalizer
# ---------------------------------------------------------------------------


def _spec_artifact_kind(path: str) -> str:
    """Infer the design artifact kind for a spec provider artifact path."""
    name = path.rsplit("/", 1)[-1]
    if name == "proposal.md":
        return "proposal"
    if name == "design.md":
        return "design"
    if name == "tasks.md":
        return "tasks"
    if name == "spec.md":
        return "spec"
    return "notes"


def _normalize_spec_artifact_paths(paths: Any) -> List[Dict[str, str]]:
    """Convert provider artifact path strings into design artifact entries."""
    if not isinstance(paths, list):
        return []
    entries: List[Dict[str, str]] = []
    for path in paths:
        if not isinstance(path, str) or not path.strip():
            continue
        entries.append(make_design_artifact_entry(
            kind=_spec_artifact_kind(path),
            path=path,
            source="openspec",
        ))
    return entries


def normalize_spec_change(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a provider-verifier spec_change result into a stable envelope.

    Required fields: change_id, status.
    Optional fields: artifact_paths, handoff_path.
    """
    change_id = raw.get("change_id")
    if not change_id:
        return make_blocker(
            reason="missing_change_id",
            message="spec_change normalization requires change_id",
            recommended_action="Ensure the provider emits a change_id in its result",
        )

    status = raw.get("status")
    if not status:
        return make_blocker(
            reason="missing_status",
            message="spec_change normalization requires status",
            recommended_action="Ensure the provider emits a status in its result",
        )

    artifact_paths = raw.get("artifact_paths", [])
    design_artifact_paths = _normalize_spec_artifact_paths(artifact_paths)
    primary_design_path = None
    for entry in design_artifact_paths:
        if entry["kind"] == "proposal":
            primary_design_path = entry["path"]
            break
    if primary_design_path is None and design_artifact_paths:
        primary_design_path = design_artifact_paths[0]["path"]

    return {
        "change_id": change_id,
        "status": status,
        "artifact_paths": artifact_paths,
        "design_artifact_paths": design_artifact_paths,
        "primary_design_path": primary_design_path,
        "handoff_path": raw.get("handoff_path"),
    }


# ---------------------------------------------------------------------------
# memory_sync normalizer
# ---------------------------------------------------------------------------


def normalize_memory_sync(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a provider-verifier memory_sync result into a stable envelope.

    Required field: status.
    Evidence fields: loaded, synced.
    Optional references: report_path, review_queue_path.
    """
    status = raw.get("status")
    if not status:
        return make_blocker(
            reason="missing_status",
            message="memory_sync normalization requires status",
            recommended_action="Ensure the provider emits a status in its result",
        )

    result: Dict[str, Any] = {
        "status": status,
        "loaded": raw.get("loaded", {}),
        "synced": raw.get("synced", {}),
    }
    if "report_path" in raw:
        result["report_path"] = raw["report_path"]
    if "review_queue_path" in raw:
        result["review_queue_path"] = raw["review_queue_path"]

    return result


# ---------------------------------------------------------------------------
# Normalizer registry
# ---------------------------------------------------------------------------


NORMALIZER_REGISTRY: Dict[str, Normalizer] = {
    "spec_change": normalize_spec_change,
    "memory_sync": normalize_memory_sync,
}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def normalize_result(contract_name: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch raw provider-verifier results to the correct contract normalizer.

    Returns a normalized evidence envelope dict on success, or a structured
    blocker dict if the contract name is unknown or normalization fails.
    """
    normalizer = NORMALIZER_REGISTRY.get(contract_name)
    if normalizer is None:
        return make_blocker(
            reason="unknown_contract",
            message=f"No normalizer registered for contract {contract_name!r}",
            recommended_action=f"Register a normalizer for {contract_name!r} in result_contracts.py",
        )
    return normalizer(raw)
