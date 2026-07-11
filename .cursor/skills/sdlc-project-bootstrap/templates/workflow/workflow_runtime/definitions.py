"""definitions.py — workflow definition loading and validation.

YAML definition loading, phase/transition interpretation, exit criteria,
and definition validation.
"""

import os

import yaml

from workflow_runtime.core import _resolve_path

# ---------------------------------------------------------------------------
# Workflow definition
# ---------------------------------------------------------------------------

SUPPORTED_PHASE_FIELDS = {
    "required_inputs", "context_loaders", "allowed_workers",
    "evidence_keys", "exit_criteria", "post_hooks", "branches", "next", "terminal",
}


def load_workflow(root, workflow_id):
    path = _resolve_path(root, f".ai/workflows/definitions/{workflow_id}.yaml")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return yaml.safe_load(f)


def validate_workflow(wf):
    errors = []
    if not isinstance(wf, dict):
        return ["workflow definition must be a YAML mapping"]
    if wf.get("version") != 1:
        errors.append("version must be 1")
    if not wf.get("id"):
        errors.append("missing workflow id")
    phases = wf.get("phases", {})
    if not phases:
        errors.append("no phases defined")
    for name, phase in phases.items():
        if not isinstance(phase, dict):
            errors.append(f"phase {name}: must be a mapping")
            continue
        for key in phase:
            if key not in SUPPORTED_PHASE_FIELDS:
                errors.append(f"phase {name}: unsupported field: {key}")
        evidence_keys = phase.get("evidence_keys")
        if evidence_keys is not None:
            if not isinstance(evidence_keys, list):
                errors.append(f"phase {name}: evidence_keys must be a list")
            else:
                for ek in evidence_keys:
                    if not isinstance(ek, str) or not ek.strip():
                        errors.append(f"phase {name}: evidence_keys must be non-empty strings")
        if not phase.get("terminal") and not phase.get("next") and not phase.get("branches"):
            errors.append(f"phase {name}: must have next, branches, or terminal")
        if phase.get("branches"):
            branches = phase["branches"]
            if not isinstance(branches, dict):
                errors.append(f"phase {name}: branches must be a mapping")
            else:
                for label, target in branches.items():
                    if target not in phases:
                        errors.append(
                            f"phase {name}: branch {label} targets unknown phase {target}"
                        )
        if phase.get("next"):
            if phase["next"] not in phases:
                errors.append(f"phase {name}: next targets unknown phase {phase['next']}")
    return errors


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------

def get_phase(wf, name):
    return wf.get("phases", {}).get(name)


def is_phase_complete(state, phase_name):
    return phase_name in state.get("completed_phases", [])


# ---------------------------------------------------------------------------
# Loader and readiness helpers
# ---------------------------------------------------------------------------

def _run_loaders(root, state, wf):
    from workflow_runtime.domains import (
        loader_spec_change_status,
        loader_spec_archive_path,
        loader_roadmap_linked_item,
        loader_roadmap_item_status,
    )
    current = state["current_phase"]
    phase_def = get_phase(wf, current)
    if not phase_def:
        return
    for loader_name in phase_def.get("context_loaders", []):
        if loader_name in ("spec_change_status", "openspec_change_status"):
            change_id = state.get("context", {}).get("change_id", "")
            if change_id:
                result = loader_spec_change_status(root, change_id)
                state.setdefault("evidence", {})["spec_status"] = result
        elif loader_name in ("spec_archive_path", "openspec_archive_path"):
            change_id = state.get("context", {}).get("change_id", "")
            if change_id:
                ap = loader_spec_archive_path(root, change_id)
                if ap:
                    state.setdefault("evidence", {})["archive_path"] = ap
        elif loader_name == "roadmap_linked_item":
            change_id = state.get("context", {}).get("change_id", "")
            if change_id:
                result = loader_roadmap_linked_item(root, change_id)
                state.setdefault("evidence", {})["roadmap_link"] = result
                if result["count"] == 1:
                    state.setdefault("context", {})["roadmap_item_id"] = result["items"][0]["item_id"]
                if result["count"] > 1:
                    state["status"] = "blocked"
                    state["block"] = {
                        "type": "user_decision_required",
                        "message": "multiple roadmap items linked to this change",
                        "candidates": result["items"],
                        "next_allowed": [
                            "choose one item",
                            "repair roadmap links manually",
                        ],
                    }
        elif loader_name == "roadmap_item_status":
            item_id = state.get("context", {}).get("roadmap_item_id", "")
            if item_id:
                result = loader_roadmap_item_status(root, item_id)
                if result:
                    state.setdefault("evidence", {})["roadmap_item_status"] = result


def _calc_readiness(state, wf):
    current = state["current_phase"]
    phase_def = get_phase(wf, current)
    if not phase_def:
        state["phase_readiness"] = {
            "phase": current,
            "ready": True,
            "missing_required_inputs": [],
        }
        return

    missing = []
    for inp in phase_def.get("required_inputs", []):
        parts = inp.split(".")
        value = state
        for p in parts:
            if isinstance(value, dict):
                value = value.get(p)
            else:
                value = None
                break
        if value is None or value == "":
            missing.append(inp)

    ready = len(missing) == 0
    state["phase_readiness"] = {
        "phase": current,
        "ready": ready,
        "missing_required_inputs": missing,
    }

    if not ready:
        state["status"] = "blocked"
        state["block"] = {
            "type": "missing_required_inputs",
            "message": f"missing: {missing}",
            "next_allowed": ["resolve", "block"],
        }


def _check_exit_criteria(state, phase_def, supplied):
    satisfied = set(supplied.split(",") if supplied else [])
    required = set(phase_def.get("exit_criteria", []))
    # Backward-compat alias: legacy archive_path_exists satisfies
    # archive_action_completed (Spec Decision 10 migration).
    if "archive_action_completed" in required and "archive_path_exists" in satisfied:
        satisfied.add("archive_action_completed")
    return required.issubset(satisfied)