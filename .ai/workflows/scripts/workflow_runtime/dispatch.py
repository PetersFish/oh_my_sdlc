"""dispatch.py — runtime-context assembly and dispatch hooks.

Runtime-context assembly, before-dispatch, after-dispatch, handoff history,
evidence/result-contract validation, and lightweight artifact archive helpers.
"""

import datetime
import json
import os
import shutil
import sys
from typing import Any, Dict, List

from workflow_runtime.core import (
    VALID_FLOW_TYPES,
    VALID_EXECUTION_MODES,
    WORKTREE_REQUIRED_FIELDS,
    VALID_BRANCH_FINISH_DECISIONS,
    _ts,
    _resolve_path,
    _resolve_execution_mode,
    _build_runtime_context,
    _resolve_branch_finish_decision,
)
from workflow_runtime.state import (
    load_run_state,
    save_run_state,
    _archive_lightweight_superpowers_artifacts,
)
from workflow_runtime.definitions import (
    load_workflow,
    get_phase,
)

# ---------------------------------------------------------------------------
# Agent identity and routing maps
# ---------------------------------------------------------------------------

VALID_AGENT_NAMES = {
    "plan-agent", "plan_agent",
    "implement-agent", "implement_agent",
    "review-agent", "review_agent",
    "finish-agent", "finish_agent",
    "roadmap-agent", "roadmap_agent",
}

CANONICAL_AGENT_NAMES = {
    "plan-agent": "plan-agent",
    "plan_agent": "plan-agent",
    "implement-agent": "implement-agent",
    "implement_agent": "implement-agent",
    "review-agent": "review-agent",
    "review_agent": "review-agent",
    "finish-agent": "finish-agent",
    "finish_agent": "finish-agent",
    "roadmap-agent": "roadmap-agent",
    "roadmap_agent": "roadmap-agent",
}

BLOCK_AGENT_ACTION_MAP = {
    "dispatch_implement_agent": "implement-agent",
    "back_to_implement": "implement-agent",
    "dispatch_plan_agent": "plan-agent",
    "back_to_plan": "plan-agent",
    "dispatch_review_agent": "review-agent",
    "dispatch_roadmap_agent": "roadmap-agent",
}

PHASE_AGENT_MAP = {
    "review_roadmap": {"roadmap-agent"},
    "create_change": {"plan-agent", "roadmap-agent"},
    "apply_change": {"implement-agent", "review-agent", "roadmap-agent"},
    "archive_change": {"finish-agent", "roadmap-agent"},
    "post_archive_actions": {"finish-agent", "roadmap-agent"},
}


# ---------------------------------------------------------------------------
# Agent routing helpers
# ---------------------------------------------------------------------------

def _roadmap_agent_enabled(state):
    return state.get("primary_subject", {}).get("type") == "roadmap_item"


def _is_roadmap_hook(hook):
    return str(hook).startswith("roadmap_")


def _canonical_agent_name(agent):
    return CANONICAL_AGENT_NAMES.get(agent, agent)


ARCHIVE_PHASE_CLEANUP_ONLY_EVIDENCE = {
    "pending_hooks_empty",
    "cleanup_complete",
    "memory_sync_done",
    "roadmap_done_checked",
    "derived_artifacts_synced",
    "post_hook_dirty_tree",
}

# post_archive_actions evidence keys that represent positive cleanup success.
# These must be True when present; only post_hook_dirty_tree may be False
# (it means the tree is clean).
POSITIVE_CLEANUP_EVIDENCE_KEYS = {
    "memory_sync_done",
    "roadmap_done_checked",
    "derived_artifacts_synced",
    "cleanup_complete",
}


def _invalid_positive_cleanup_evidence(phase, evidence):
    """Return positive cleanup evidence keys that are present but not True.

    Only applies to post_archive_actions.  post_hook_dirty_tree may be False
    (clean tree); the other cleanup evidence keys must be True to represent
    successful cleanup.
    """
    if phase != "post_archive_actions":
        return []
    if not isinstance(evidence, dict):
        return []
    return sorted(
        key for key in POSITIVE_CLEANUP_EVIDENCE_KEYS
        if key in evidence and evidence[key] is not True
    )


def _premature_archive_cleanup_evidence(agent, phase, agent_evidence):
    if _canonical_agent_name(agent) != "finish-agent":
        return []
    if phase != "archive_change":
        return []
    if not isinstance(agent_evidence, dict):
        return []
    return sorted(
        key for key in ARCHIVE_PHASE_CLEANUP_ONLY_EVIDENCE
        if key in agent_evidence
    )


def _phase_allows_agent(phase, agent):
    canonical = _canonical_agent_name(agent)
    allowed = PHASE_AGENT_MAP.get(phase)
    if allowed is None:
        return False
    return canonical in allowed


def _allows_replan_from_apply_change(state, agent):
    canonical = _canonical_agent_name(agent)
    if canonical != "plan-agent":
        return False
    if state.get("current_phase") != "apply_change":
        return False
    block = state.get("block") or {}
    next_allowed = block.get("next_allowed", [])
    if isinstance(next_allowed, str):
        next_allowed = [next_allowed]
    latest = state.get("evidence", {}).get("agent_result", {})
    blockers = latest.get("blockers", []) if isinstance(latest, dict) else []
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        if blocker.get("reason") in {"requirement_ambiguity", "design_ambiguity"}:
            return True
        if blocker.get("recommended_action") == "dispatch_plan_agent":
            return True
    return "dispatch_plan_agent" in next_allowed


def _normalized_block_actions(raw_actions):
    if raw_actions is None:
        return []
    if isinstance(raw_actions, str):
        raw_actions = raw_actions.split(",")
    if not isinstance(raw_actions, list):
        return []
    return [str(action).strip() for action in raw_actions if str(action).strip()]


def _action_routes_to_agent(action, canonical_agent):
    if not action:
        return False
    normalized = str(action).strip()
    if normalized in VALID_AGENT_NAMES:
        return _canonical_agent_name(normalized) == canonical_agent
    return BLOCK_AGENT_ACTION_MAP.get(normalized) == canonical_agent


def _latest_blocker_routes_to_agent(state, canonical_agent):
    latest = state.get("evidence", {}).get("agent_result", {})
    if not isinstance(latest, dict):
        return False
    if _action_routes_to_agent(latest.get("recommended_next_action"), canonical_agent):
        return True
    blockers = latest.get("blockers", [])
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        if canonical_agent == "plan-agent" and blocker.get("reason") in {"requirement_ambiguity", "design_ambiguity"}:
            return True
        if _action_routes_to_agent(blocker.get("recommended_action"), canonical_agent):
            return True
        if _action_routes_to_agent(blocker.get("recommended_next_action"), canonical_agent):
            return True
    return False


def _roadmap_block_routes_to_agent(block, canonical_agent):
    if canonical_agent != "roadmap-agent":
        return False
    if not isinstance(block, dict):
        return False
    if block.get("type") not in {"hook_blocked", "domain_state_mismatch", "user_decision_required"}:
        return False
    return _canonical_agent_name(block.get("route_to_agent", "")) == canonical_agent


def _allows_blocked_dispatch(state, agent):
    canonical_agent = _canonical_agent_name(agent)
    if state.get("status") != "blocked":
        return False
    block = state.get("block") or {}
    if _roadmap_block_routes_to_agent(block, canonical_agent):
        return True
    if block.get("type") != "worker_failed":
        return False
    actions = _normalized_block_actions(block.get("next_allowed"))
    if any(_action_routes_to_agent(action, canonical_agent) for action in actions):
        return True
    if _latest_blocker_routes_to_agent(state, canonical_agent):
        return True
    return False


# ---------------------------------------------------------------------------
# Before-dispatch command
# ---------------------------------------------------------------------------

def cmd_before_dispatch(root, args):
    state = load_run_state(root)
    if not state:
        blocker = {
            "agent": getattr(args, "agent", "unknown"),
            "status": "blocked",
            "phase": getattr(args, "phase", state.get("current_phase", "")) if state else "",
            "slice_id": getattr(args, "slice_id", ""),
            "flow_type": "",
            "evidence": {},
            "artifacts": {},
            "blockers": [{
                "reason": "no_active_run",
                "message": "No active workflow run exists",
                "recommended_action": "call workflow.py start or ensure-run first",
            }],
            "recommended_next_action": "start_run",
        }
        print(json.dumps(blocker, indent=2))
        sys.exit(1)

    agent = getattr(args, "agent", "") or ""
    canonical_agent = _canonical_agent_name(agent)
    current_phase = state.get("current_phase", "")
    phase = args.phase or current_phase
    flow_type = state.get("flow_type", "")
    context = state.get("context", {}) or {}
    execution_mode = _resolve_execution_mode(context)

    blocker_reasons = []
    if agent not in VALID_AGENT_NAMES:
        blocker_reasons.append({
            "reason": "invalid_agent",
            "message": f"Unknown agent: {agent}. Must be one of: {sorted(VALID_AGENT_NAMES)}",
            "recommended_action": "correct the --agent argument",
        })
    if args.phase and args.phase != current_phase:
        blocker_reasons.append({
            "reason": "phase_mismatch",
            "message": f"Requested phase '{args.phase}' does not match active phase '{current_phase}'",
            "recommended_action": "dispatch using the active workflow phase",
        })
    if not flow_type:
        blocker_reasons.append({
            "reason": "missing_flow_type",
            "message": "flow_type is not set in the workflow run state",
            "recommended_action": "set --flow-type on workflow.py start",
        })
    if flow_type and flow_type not in VALID_FLOW_TYPES:
        blocker_reasons.append({
            "reason": "invalid_flow_type",
            "message": f"flow_type '{flow_type}' is not a valid value",
            "recommended_action": f"flow_type must be one of: {sorted(VALID_FLOW_TYPES)}",
        })
    if execution_mode not in VALID_EXECUTION_MODES:
        blocker_reasons.append({
            "reason": "invalid_execution_mode",
            "message": f"execution_mode '{execution_mode}' is not a valid value",
            "recommended_action": f"execution_mode must be one of: {sorted(VALID_EXECUTION_MODES)}",
        })
    elif execution_mode == "worktree":
        missing_worktree_fields = [
            f for f in WORKTREE_REQUIRED_FIELDS if not context.get(f)
        ]
        if missing_worktree_fields:
            blocker_reasons.append({
                "reason": "missing_worktree_context",
                "message": (
                    "execution_mode=worktree requires: "
                    + ", ".join(missing_worktree_fields)
                ),
                "recommended_action": (
                    "record required worktree context fields via "
                    "workflow.py record-context before dispatching agents"
                ),
            })
    allow_replan = _allows_replan_from_apply_change(state, canonical_agent)
    allow_blocked_dispatch = _allows_blocked_dispatch(state, canonical_agent)
    if state.get("status") == "blocked" and agent not in {"finish-agent", "finish_agent"} and not (allow_replan or allow_blocked_dispatch):
        block = state.get("block", {})
        blocker_reasons.append({
            "reason": "run_is_blocked",
            "message": f"Workflow run is blocked: {block.get('type', 'unknown')} — {block.get('message', 'no message')}",
            "recommended_action": "resolve the block before dispatching agents",
        })
    if agent in VALID_AGENT_NAMES and not (_phase_allows_agent(current_phase, canonical_agent) or allow_replan or allow_blocked_dispatch):
        blocker_reasons.append({
            "reason": "agent_not_allowed_for_phase",
            "message": f"Agent '{canonical_agent}' is not allowed in phase '{current_phase}'",
            "recommended_action": "select an agent mapped to the current phase",
        })
    if canonical_agent == "roadmap-agent" and not _roadmap_agent_enabled(state):
        blocker_reasons.append({
            "reason": "roadmap_not_enabled",
            "message": "roadmap-agent is disabled because primary_subject.type is not roadmap_item",
            "recommended_action": "continue the non-roadmap workflow path without dispatching roadmap-agent",
        })

    # Branch finish decision gate (Spec Decision 1-3): finish-agent must have
    # an explicit branch_finish_decision before branch-affecting actions when
    # a feature branch/worktree is present.
    if canonical_agent == "finish-agent" and phase in ("archive_change", "post_archive_actions"):
        decision, status = _resolve_branch_finish_decision(context)
        if status == "missing":
            blocker_reasons.append({
                "reason": "missing_branch_finish_decision",
                "message": (
                    "finish requires explicit branch_finish_decision before "
                    "branch-affecting actions"
                ),
                "recommended_action": "ask_user_branch_finish_decision",
            })
        elif status == "invalid":
            blocker_reasons.append({
                "reason": "invalid_branch_finish_decision",
                "message": (
                    f"branch_finish_decision {decision!r} is not one of: "
                    f"{sorted(VALID_BRANCH_FINISH_DECISIONS)}"
                ),
                "recommended_action": "ask_user_branch_finish_decision",
            })

    if blocker_reasons:
        blocker = {
            "agent": agent,
            "status": "blocked",
            "phase": phase,
            "slice_id": getattr(args, "slice_id", ""),
            "flow_type": flow_type,
            "evidence": {},
            "artifacts": {},
            "blockers": blocker_reasons,
            "recommended_next_action": (
                "ask_user_branch_finish_decision"
                if any(b.get("reason") in (
                    "missing_branch_finish_decision",
                    "invalid_branch_finish_decision",
                ) for b in blocker_reasons)
                else "resolve_blockers"
            ),
        }
        print(json.dumps(blocker, indent=2))
        sys.exit(1)

    dispatch_intent = {
        "agent_phase": phase,
        "agent": canonical_agent,
        "flow_type": flow_type,
        "dispatched_at": _ts(),
    }
    if args.slice_id:
        dispatch_intent["slice_id"] = args.slice_id

    state.setdefault("evidence", {})["agent_phase"] = dispatch_intent
    state["updated_at"] = _ts()
    save_run_state(root, state)

    result = {
        "agent": canonical_agent,
        "status": "dispatched",
        "phase": phase,
        "slice_id": getattr(args, "slice_id", ""),
        "flow_type": flow_type,
        "evidence": {"dispatched_at": _ts()},
        "artifacts": {},
        "blockers": [],
        "recommended_next_action": "execute_agent",
        "runtime_context": _build_runtime_context(context),
    }
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Evidence envelope and phase evidence validation
# ---------------------------------------------------------------------------

def _validate_evidence_envelope_contract(result: Dict[str, Any]) -> List[str]:
    """Validate that agent result conforms to shared evidence envelope contract.
    Returns a list of error messages (empty = valid).
    The 'agent' field is optional here because after_dispatch receives it via CLI arg."""
    errors: List[str] = []
    if not isinstance(result, dict):
        return ["agent result must be a dict"]
    if "status" not in result:
        errors.append("missing 'status' in evidence envelope")
    if result.get("status") not in ("success", "failed", "blocked"):
        errors.append(f"invalid status: {result.get('status')!r}")
    evidence = result.get("evidence")
    if evidence is not None and not isinstance(evidence, dict):
        errors.append("'evidence' must be a dict")
    elif evidence is not None:
        focused = evidence.get("focused_tests")
        if focused is not None and not isinstance(focused, list):
            errors.append("evidence.focused_tests must be an array when present")
    blockers = result.get("blockers")
    if blockers is not None and not isinstance(blockers, list):
        errors.append("'blockers' must be a list")
    artifacts = result.get("artifacts")
    if artifacts is not None and not isinstance(artifacts, dict):
        errors.append("'artifacts' must be a dict")
    return errors


def _missing_phase_evidence_keys(agent_evidence: Dict[str, Any], phase_def: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for key in phase_def.get("evidence_keys", []):
        value = agent_evidence.get(key)
        if value is None or value == "":
            # Backward-compat alias: legacy archive_path_exists satisfies
            # archive_action_completed evidence key (Spec Decision 10).
            if key == "archive_action_completed" and agent_evidence.get("archive_path_exists"):
                continue
            missing.append(key)
    return missing


def _missing_exit_criteria(phase_evidence_view: Dict[str, Any], phase_def: Dict[str, Any]) -> List[str]:
    raw = phase_evidence_view.get("criteria_satisfied", "")
    satisfied = {item for item in str(raw).split(",") if item}
    required = set(phase_def.get("exit_criteria", []))
    for key in list(required - satisfied):
        value = phase_evidence_view.get(key)
        if value is not None and value != "" and value is not False:
            satisfied.add(key)
    # Backward-compat alias: legacy archive_path_exists satisfies
    # archive_action_completed (Spec Decision 10 migration).  Both the
    # criteria_satisfied string declaration and a truthy evidence value
    # for archive_path_exists count.
    if "archive_action_completed" in required:
        if "archive_path_exists" in satisfied:
            satisfied.add("archive_action_completed")
        else:
            legacy_val = phase_evidence_view.get("archive_path_exists")
            if legacy_val is not None and legacy_val != "" and legacy_val is not False:
                satisfied.add("archive_action_completed")
    return sorted(required - satisfied)


def _build_phase_evidence_view(state, phase, slice_id, agent_evidence):
    merged = {}
    if phase == "apply_change":
        prior = state.get("evidence", {}).get("agent_results", {}).get(slice_id, {})
        for result in prior.values():
            if result.get("status") == "success":
                merged.update(result.get("evidence", {}))
        merged.update(state.get("evidence", {}))
        merged.update(agent_evidence)
        return merged
    merged.update(agent_evidence)
    return merged


# ---------------------------------------------------------------------------
# Handoff history helpers
# ---------------------------------------------------------------------------

def _write_handoff_history_copy(root, handoff_path):
    abs_latest = _resolve_path(root, handoff_path)
    if not os.path.exists(abs_latest):
        return None
    history_dir = os.path.join(os.path.dirname(abs_latest), "history")
    os.makedirs(history_dir, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(abs_latest))
    history_name = f"{stem}-{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S%fZ')}{ext}"
    history_path = os.path.join(history_dir, history_name)
    shutil.copyfile(abs_latest, history_path)
    return history_path


def _read_handoff_metadata(path):
    """Parse the ``## Metadata`` block of a handoff markdown file.

    Returns a dict of canonical metadata keys (e.g. ``"Run ID"``,
    ``"Slice ID"``, ``"Agent"``, ``"Phase"``, ``"Flow Type"``, ``"Status"``)
    mapped to their stripped string values.  Returns an empty dict if the
    file is missing or has no ``## Metadata`` section.
    """
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return {}

    metadata: Dict[str, str] = {}
    in_metadata = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "## Metadata":
            in_metadata = True
            continue
        if in_metadata and stripped.startswith("## "):
            break
        if in_metadata and stripped.startswith("- **") and "**:" in stripped:
            key, value = stripped[4:].split("**:", 1)
            metadata[key.strip()] = value.strip()
    return metadata


def _handoff_metadata_mismatch_blocker(metadata, expected):
    """Return a structured blocker dict if handoff metadata mismatches context.

    ``expected`` is a dict of canonical keys to expected values.  Returns the
    first mismatch as a blocker dict, or None when all present metadata fields
    match (missing metadata fields are tolerated — only present-but-mismatched
    fields block).
    """
    field_map = {
        "Agent": expected.get("agent", ""),
        "Phase": expected.get("phase", ""),
        "Slice ID": expected.get("slice_id", ""),
        "Flow Type": expected.get("flow_type", ""),
    }
    for field, expected_value in field_map.items():
        actual = metadata.get(field)
        if actual is not None and str(actual) != str(expected_value):
            return {
                "reason": "handoff_metadata_mismatch",
                "message": (
                    f"handoff metadata field '{field}' value '{actual}' does not "
                    f"match active run context '{expected_value}'"
                ),
                "recommended_action": "regenerate_handoff_artifact",
            }
    return None


# ---------------------------------------------------------------------------
# After-dispatch command
# ---------------------------------------------------------------------------

def cmd_after_dispatch(root, args):
    state = load_run_state(root)
    if not state:
        blocker = {
            "agent": getattr(args, "agent", "unknown"),
            "status": "blocked",
            "phase": getattr(args, "phase", ""),
            "slice_id": getattr(args, "slice_id", ""),
            "flow_type": "",
            "evidence": {},
            "artifacts": {},
            "blockers": [{
                "reason": "no_active_run",
                "message": "No active workflow run exists",
                "recommended_action": "call workflow.py start or ensure-run first",
            }],
            "recommended_next_action": "start_run",
        }
        print(json.dumps(blocker, indent=2))
        sys.exit(1)

    agent = getattr(args, "agent", "") or ""
    canonical_agent = _canonical_agent_name(agent)
    phase = args.phase or state.get("current_phase", "")
    flow_type = state.get("flow_type", "")
    agent_result_value = getattr(args, "value", None)

    agent_result = {}
    if agent_result_value:
        try:
            agent_result = json.loads(agent_result_value)
        except (json.JSONDecodeError, TypeError):
            agent_result = {"raw_result": agent_result_value}

    # 3.8b: Validate agent result against evidence envelope contract
    envelope_errors = _validate_evidence_envelope_contract(agent_result)
    if envelope_errors:
        agent_result.setdefault("blockers", []).extend(
            {"reason": "envelope_contract_violation",
             "message": err,
             "recommended_action": "correct evidence envelope format"}
            for err in envelope_errors
        )

    agent_status = agent_result.get("status", "unknown")
    agent_evidence = agent_result.get("evidence", {})
    agent_blockers = agent_result.get("blockers", [])
    agent_recommended = agent_result.get("recommended_next_action", "")
    agent_artifacts = agent_result.get("artifacts") or {}

    # Slice id fallback order (Spec Decision 6):
    # 1. CLI --slice-id
    # 2. agent_result.slice_id
    # 3. state.evidence.agent_phase.slice_id (dispatch intent)
    # 4. state.context.change_id
    # 5. "default"
    cli_slice_id = getattr(args, "slice_id", "") or ""
    agent_slice_id = agent_result.get("slice_id", "") or ""
    dispatch_intent_slice_id = (
        state.get("evidence", {}).get("agent_phase", {}).get("slice_id", "")
    ) or ""
    change_id = state.get("context", {}).get("change_id", "") or ""
    slice_id = (
        cli_slice_id
        or agent_slice_id
        or dispatch_intent_slice_id
        or change_id
        or "default"
    )

    premature_cleanup_keys = _premature_archive_cleanup_evidence(
        canonical_agent,
        phase,
        agent_evidence,
    )
    if agent_status == "success" and premature_cleanup_keys:
        agent_blockers.append({
            "reason": "premature_cleanup_evidence",
            "message": (
                "finish-agent archive_change success claimed cleanup-only evidence "
                f"before post_archive_actions: {', '.join(premature_cleanup_keys)}"
            ),
            "recommended_action": "dispatch_finish_agent_for_post_archive_actions",
        })

    latest_result = {
        "agent": canonical_agent,
        "status": agent_status,
        "phase": phase,
        "slice_id": slice_id,
        "flow_type": flow_type,
        "evidence": agent_evidence,
        "artifacts": agent_artifacts,
        "blockers": agent_blockers,
        "recommended_next_action": agent_recommended,
        "recorded_at": _ts(),
    }
    evidence = state.setdefault("evidence", {})
    evidence["agent_result"] = latest_result
    evidence.setdefault("agent_results", {}).setdefault(slice_id, {})[canonical_agent] = latest_result

    wf = load_workflow(root, state.get("workflow", "sdlc-main"))
    phase_def = None
    phase_evidence_view = dict(agent_evidence)
    if wf:
        phase_def = get_phase(wf, phase)
        if phase_def:
            phase_evidence_view = _build_phase_evidence_view(state, phase, slice_id, agent_evidence)
            phase_evidence_keys = phase_def.get("evidence_keys", [])
            if agent_status == "success" and not agent_blockers:
                for ek in phase_evidence_keys:
                    source = phase_evidence_view if phase == "apply_change" else agent_evidence
                    if ek in source:
                        evidence[ek] = source[ek]

    if phase == "apply_change":
        artifacts = agent_result.get("artifacts") or {}
        handoff_path = artifacts.get("handoff_path")
        if handoff_path:
            abs_handoff = _resolve_path(root, handoff_path)
            metadata = _read_handoff_metadata(abs_handoff) if os.path.exists(abs_handoff) else {}
            mismatch_blocker = _handoff_metadata_mismatch_blocker(
                metadata,
                {
                    "agent": canonical_agent,
                    "phase": phase,
                    "slice_id": slice_id,
                    "flow_type": flow_type,
                },
            )
            if mismatch_blocker:
                agent_blockers.append(mismatch_blocker)
            else:
                history_path = _write_handoff_history_copy(root, handoff_path)
                if history_path:
                    artifacts.setdefault("history_handoff_paths", []).append(
                        os.path.relpath(history_path, root) if root else history_path
                    )

    # Synchronize canonical change_id from provider-created spec artifacts.
    # When a provider (e.g., OpenSpec) normalizes the change_id during artifact
    # creation, the agent result carries the canonical value.  Update context so
    # that later phases (apply_change, archive_change) look up the correct id.
    if agent_status == "success":
        agent_change_id = (
            agent_evidence.get("change_id")
            or (agent_result.get("artifacts") or {}).get("change_id")
        )
        if agent_change_id:
            current_change_id = state.get("context", {}).get("change_id", "")
            if agent_change_id != current_change_id:
                state.setdefault("context", {})["change_id"] = agent_change_id

    # Lightweight-flow Superpowers archive moves (Spec Decision 11): when
    # finish-agent succeeds at archive_change for a lightweight-flow run,
    # move matching Superpowers plan/spec files into typed archive dirs.
    if (
        agent_status == "success"
        and canonical_agent == "finish-agent"
        and phase == "archive_change"
        and flow_type == "lightweight-flow"
    ):
        archive_result = _archive_lightweight_superpowers_artifacts(
            root, state, agent_evidence
        )
        if archive_result["moved"]:
            # Update the agent evidence with actual moved paths so downstream
            # consumers see the real source/destination pairs.
            agent_evidence["archived_design_artifact_paths"] = [
                dst for _, dst in archive_result["moved"]
            ]
            agent_evidence["source_design_artifact_paths"] = [
                src for src, _ in archive_result["moved"]
            ]
        elif archive_result.get("already_archived"):
            # finish-agent already moved the files; record the confirmed
            # archive destinations so downstream evidence stays consistent.
            agent_evidence["archived_design_artifact_paths"] = [
                dst for _, dst in archive_result["already_archived"]
            ]
            agent_evidence["source_design_artifact_paths"] = [
                src for src, _ in archive_result["already_archived"]
            ]
        # Spec Decision 11: if expected Superpowers artifacts were missing on
        # disk (the helper recorded them as skipped), the runtime must not
        # allow archive_action_completed=true to stand.  Flip the semantic
        # evidence to false and add a blocker so phase completion cannot pass
        # while the expected files never moved.
        if archive_result["skipped"]:
            agent_evidence["archive_action_completed"] = False
            agent_evidence["archive_not_required_reason"] = (
                "missing_lightweight_archive_artifacts"
            )
            agent_blockers.append({
                "reason": "missing_lightweight_archive_artifacts",
                "message": (
                    "finish-agent reported archive success but expected "
                    "Superpowers design artifacts were not found on disk: "
                    + ", ".join(archive_result["skipped"])
                ),
                "recommended_action": "surface_error",
            })

    next_cmd = "complete-phase"
    recommended_next_action = agent_recommended or "complete_phase"
    if agent_status != "success":
        next_cmd = "block"
        if not agent_recommended or agent_recommended in {"dispatch_review_agent", "complete_phase"}:
            recommended_next_action = "resolve_failure"
    elif agent_blockers:
        next_cmd = "block"
    elif canonical_agent == "implement-agent":
        # implement-agent owns normal verification; route to review-agent next.
        next_cmd = ""
        recommended_next_action = "dispatch_review_agent"
    elif canonical_agent == "roadmap-agent":
        # roadmap-agent is a lifecycle hook worker, not a phase worker.
        # Its after-dispatch should lead to hook completion flow, not
        # phase completion.  Do NOT validate against phase evidence_keys
        # or exit_criteria — those are for phase-completing workers.
        next_cmd = ""
        recommended_next_action = agent_recommended or "complete_hooks"

    if wf and phase_def and agent_status == "success" and not agent_blockers and next_cmd == "complete-phase":
        missing_evidence_keys = _missing_phase_evidence_keys(phase_evidence_view, phase_def)
        if missing_evidence_keys:
            agent_blockers.append({
                "reason": "missing_phase_evidence_keys",
                "message": f"agent success is missing required phase evidence keys: {', '.join(missing_evidence_keys)}",
                "recommended_action": "resolve_failure",
            })
        else:
            missing_exit_criteria = _missing_exit_criteria(phase_evidence_view, phase_def)
            if missing_exit_criteria:
                agent_blockers.append({
                    "reason": "missing_exit_criteria_satisfied",
                    "message": f"agent success is missing criteria_satisfied entries for: {', '.join(missing_exit_criteria)}",
                    "recommended_action": "resolve_failure",
                })

        invalid_positive = _invalid_positive_cleanup_evidence(phase, phase_evidence_view)
        if invalid_positive:
            agent_blockers.append({
                "reason": "invalid_phase_evidence_values",
                "message": (
                    "post_archive_actions positive cleanup evidence must be True; "
                    f"false/empty values for: {', '.join(invalid_positive)}"
                ),
                "recommended_action": "resolve_failure",
            })

        if phase == "apply_change" and phase_evidence_view.get("eval_passed_or_human_decision_recorded"):
            # Require prior successful implement-agent verification evidence as
            # the verification basis.  Review-agent must not self-claim
            # verification_passed without implement-agent proof.
            prior_implement = state.get("evidence", {}).get("agent_results", {}).get(slice_id, {}).get("implement-agent", {})
            implement_verified = (
                prior_implement.get("status") == "success"
                and (
                    prior_implement.get("evidence", {}).get("verification_passed")
                    or prior_implement.get("evidence", {}).get("regression_passed")
                    or prior_implement.get("evidence", {}).get("tdd_passed")
                    or prior_implement.get("evidence", {}).get("focused_tests")
                )
            )
            if not implement_verified:
                agent_blockers.append({
                    "reason": "missing_verification_basis",
                    "message": "apply_change acceptance cannot record eval_passed_or_human_decision_recorded without successful implement-agent verification evidence",
                    "recommended_action": "resolve_failure",
                })

        if phase == "apply_change" and agent_status == "success" and not agent_blockers:
            for ek in phase_def.get("evidence_keys", []):
                if ek in phase_evidence_view:
                    evidence[ek] = phase_evidence_view[ek]

    should_block = next_cmd == "block"
    if agent_blockers and next_cmd == "complete-phase":
        next_cmd = "block"
        recommended_next_action = "resolve_failure"
        should_block = True

    if agent_blockers:
        block_message = "; ".join(b.get("reason", b.get("message", "")) for b in agent_blockers)
        next_allowed = ",".join(b.get("recommended_action", recommended_next_action or "resolve") for b in agent_blockers)
    else:
        block_message = f"agent_status={agent_status}" if should_block else ""
        next_allowed = recommended_next_action if should_block else ""

    if should_block:
        state["status"] = "blocked"
        state["block"] = {
            "type": "worker_failed",
            "message": block_message,
            "next_allowed": [item for item in next_allowed.split(",") if item],
        }
    else:
        if state.get("block") and state.get("block", {}).get("type") == "worker_failed":
            state["block"] = None
        if state.get("status") == "blocked":
            state["status"] = "running"

    state["updated_at"] = _ts()
    save_run_state(root, state)

    transition = {
        "agent": canonical_agent,
        "status": agent_status,
        "phase": phase,
        "slice_id": slice_id,
        "flow_type": flow_type,
        "evidence": agent_evidence,
        "artifacts": agent_result.get("artifacts", {}),
        "blockers": agent_blockers,
        "recommended_next_action": recommended_next_action,
        "workflow_command": f"workflow.py {next_cmd}" if next_cmd else "",
        "workflow_args": {
            "exit_criteria_satisfied": phase_evidence_view.get("criteria_satisfied", agent_evidence.get("criteria_satisfied", "")),
            "block_type": "worker_failed" if should_block else "",
            "message": block_message,
            "next_allowed": next_allowed,
        },
    }
    print(json.dumps(transition, indent=2))