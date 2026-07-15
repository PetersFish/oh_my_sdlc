"""lifecycle.py — lifecycle transition helpers and command handlers.

Status, start, resume, readiness, resolve, record-evidence, record-context,
complete-phase, complete-hook, advance, block, cancel-run, and done handlers.
"""

import json
import sys

from workflow_runtime.core import (
    VALID_BLOCK_TYPES,
    VALID_MEMORY_SYNC_RESOLUTIONS,
    VALID_EXECUTION_MODES,
    WORKTREE_REQUIRED_FIELDS,
    _make_run_id,
    _ts,
    _resolve_execution_mode,
    _should_reconcile_branch_decision_block,
)
from workflow_runtime.state import (
    _read_pointer,
    _set_pointer,
    _clear_pointer,
    load_run_state,
    save_run_state,
    _list_active_runs,
    _find_active_run_by_subject,
    validate_run_state,
    _finalize_run_to_history,
    _move_run_to_history,
    _cancel_active_run,
    _missing_terminal_finish_agent_evidence,
    _terminal_derived_artifact_drift,
    normalize_implementation_state,
    make_pending_implementation_state,
    make_slicing_assessment_block,
    active_apply_slicing_errors,
)
from workflow_runtime.definitions import (
    load_workflow,
    validate_workflow,
    get_phase,
    is_phase_complete,
    _run_loaders,
    _calc_readiness,
    _check_exit_criteria,
)
from workflow_runtime.domains import (
    loader_roadmap_item_status,
    _read_roadmap_item_spec_change,
    _infer_phase,
)
from workflow_runtime.policies import (
    _find_linked_roadmap_run,
)
from workflow_runtime.dispatch import (
    _roadmap_agent_enabled,
    _is_roadmap_hook,
    _invalid_positive_cleanup_evidence,
)


# ---------------------------------------------------------------------------
# Status and validation
# ---------------------------------------------------------------------------

def _status_summaries(active_runs):
    summaries = []
    for run_id, state in active_runs:
        summaries.append({
            "run_id": run_id,
            "current_phase": state.get("current_phase"),
            "status": state.get("status"),
            "primary_subject": state.get("primary_subject"),
            "updated_at": state.get("updated_at"),
        })
    return summaries


def cmd_status(root, args):
    subject_type = args.subject_type
    subject_id = args.subject_id

    if subject_type and subject_id:
        state = _find_active_run_by_subject(root, subject_type, subject_id)
        if not state:
            print(json.dumps({"status": "no_active_run"}, indent=2))
            return
        print(json.dumps(state, indent=2))
        return

    pointer = _read_pointer(root)
    if pointer and pointer.get("run_id"):
        state = load_run_state(root)
        if state:
            print(json.dumps(state, indent=2))
            return
        active_runs = _list_active_runs(root)
        summaries = _status_summaries(active_runs)
        print(
            json.dumps(
                {
                    "status": "stale_pointer",
                    "pointer_run_id": pointer["run_id"],
                    "message": "pointed run file not found in active/",
                    "runs": summaries,
                },
                indent=2,
            )
        )
        return

    active_runs = _list_active_runs(root)
    if not active_runs:
        print(json.dumps({"status": "no_active_run"}))
        return

    summaries = _status_summaries(active_runs)
    print(json.dumps({"status": "active_runs", "runs": summaries}, indent=2))


def cmd_validate(root, args):
    errors = []
    state = load_run_state(root)
    if state:
        errors.extend(validate_run_state(state))
    wf = load_workflow(root, args.workflow or "sdlc-main")
    if wf:
        errors.extend(validate_workflow(wf))
    elif root and args.workflow:
        errors.append(f"workflow {args.workflow} not found")
    elif root:
        errors.append("workflow sdlc-main not found")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"valid": True}))


# ---------------------------------------------------------------------------
# Start, resume, readiness, resolve
# ---------------------------------------------------------------------------

def cmd_start(root, args):
    workflow_id = args.workflow or "sdlc-main"
    subject_type = args.subject_type
    subject_id = args.subject_id
    if not subject_type:
        print(json.dumps({"error": "subject-type is required"}, indent=2), file=sys.stderr)
        sys.exit(1)
    run_id = _make_run_id(subject_type, subject_id)

    # Check ALL active runs for same-subject duplicate
    duplicate = _find_active_run_by_subject(root, subject_type, subject_id)
    if duplicate:
        print(
            json.dumps(
                {
                    "action": "conflict",
                    "message": "active run already exists for this subject",
                    "existing_run_id": duplicate["run_id"],
                    "existing_subject": duplicate.get("primary_subject", {}),
                },
                indent=2,
            )
        )
        sys.exit(1)

    # Prevent duplicate spec_change run when a linked roadmap_item run exists
    if subject_type == "spec_change":
        linked = _find_linked_roadmap_run(root, subject_id)
        if linked:
            print(
                json.dumps(
                    {
                        "action": "conflict",
                        "message": (
                            "A linked roadmap_item run already exists for this change."
                            " The roadmap_item run is the canonical run."
                        ),
                        "existing_run_id": linked["run_id"],
                        "existing_subject": linked.get("primary_subject", {}),
                    },
                    indent=2,
                )
            )
            sys.exit(1)

    flow_type = args.flow_type or "spec-flow"
    phase = _infer_phase(root, subject_type, subject_id, flow_type)

    # Explicit flow_type is treated as user-confirmed; no confirmation gate.
    state = {
        "version": 1,
        "run_id": run_id,
        "workflow": workflow_id,
        "flow_type": flow_type,
        "status": "running",
        "current_phase": phase,
        "primary_subject": {"type": subject_type, "id": subject_id},
        "context": {"change_id": subject_id} if subject_type == "spec_change" else {},
        "phase_readiness": {"phase": phase, "ready": False, "missing_required_inputs": []},
        "pending_hooks": [],
        "completed_hooks": [],
        "completed_phases": [],
        "gates": {},
        "evidence": {},
        "block": None,
        "updated_at": "",
    }
    wf = load_workflow(root, workflow_id)
    if wf:
        _run_loaders(root, state, wf)

    # Slicing assessment gate: an apply-ready run must be blocked until
    # plan-agent produces a validated slicing assessment.  The run is in
    # the apply phase for workflow identity, but apply execution is blocked.
    if phase == "apply_change":
        state["implementation"] = make_pending_implementation_state()
        state["status"] = "blocked"
        state["block"] = make_slicing_assessment_block()
        state["phase_readiness"] = {
            "phase": "apply_change",
            "ready": False,
            "missing_required_inputs": ["validated_implementation_slices"],
        }

    save_run_state(root, state)
    state["updated_at"] = _ts()
    print(json.dumps(state, indent=2))


def cmd_resume(root, args):
    subject_type = args.subject_type
    subject_id = args.subject_id

    if not subject_type or not subject_id:
        active_runs = _list_active_runs(root)
        summaries = []
        for run_id, state in active_runs:
            summaries.append({
                "run_id": run_id,
                "current_phase": state.get("current_phase"),
                "status": state.get("status"),
                "primary_subject": state.get("primary_subject"),
                "updated_at": state.get("updated_at"),
            })
        print(
            json.dumps(
                {
                    "error": "subject-type and subject-id required for resume with concurrent runs",
                    "active_runs": summaries,
                },
                indent=2,
            )
        )
        sys.exit(1)

    state = _find_active_run_by_subject(root, subject_type, subject_id)
    if not state:
        print(
            json.dumps(
                {
                    "error": f"no active run found for {subject_type}/{subject_id}",
                },
                indent=2,
            )
        )
        sys.exit(1)

    _set_pointer(root, state["run_id"])

    status = state.get("status")
    if status == "done":
        print(json.dumps({"action": "none", "message": "run is already done"}, indent=2))
        return
    if status == "cancelled":
        print(json.dumps({"action": "cancelled", "message": "run is cancelled, start new"}, indent=2))
        return

    wf = load_workflow(root, state.get("workflow", "sdlc-main"))
    if wf:
        effective_subject_id = subject_id
        if subject_type == "spec_change":
            effective_subject_id = state.get("context", {}).get("change_id") or subject_id
        phase = _infer_phase(root, subject_type, effective_subject_id, state.get("flow_type", "spec-flow"))
        state["current_phase"] = phase
        _run_loaders(root, state, wf)
        _calc_readiness(state, wf)

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


def cmd_readiness(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)
    wf = load_workflow(root, state.get("workflow", "sdlc-main"))
    if not wf:
        print(json.dumps({"error": "workflow not found"}, indent=2))
        sys.exit(1)
    _calc_readiness(state, wf)
    save_run_state(root, state)
    print(json.dumps(state, indent=2))


def cmd_resolve(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)
    wf = load_workflow(root, state.get("workflow", "sdlc-main"))
    if not wf:
        print(json.dumps({"error": "workflow not found"}, indent=2))
        sys.exit(1)
    _run_loaders(root, state, wf)
    _calc_readiness(state, wf)

    # Attempt to clear resolvable blocks
    block = state.get("block")
    if block:
        block_type = block.get("type", "")
        if block_type == "missing_required_inputs":
            if state["phase_readiness"].get("ready"):
                state["block"] = None
                state["status"] = "running"
            else:
                still_missing = state["phase_readiness"].get("missing_required_inputs", [])
                print(
                    json.dumps(
                        {
                            "error": "block not resolved",
                            "block_type": block_type,
                            "reason": f"still missing inputs: {still_missing}",
                            "next_allowed": block.get("next_allowed", []),
                        },
                        indent=2,
                    )
                )
                sys.exit(1)
        elif block_type == "domain_state_mismatch":
            if is_phase_complete(state, state["current_phase"]):
                state["block"] = None
                state["status"] = "running"
            else:
                print(
                    json.dumps(
                        {
                            "error": "block not resolved",
                            "block_type": block_type,
                            "reason": "phase is not yet complete",
                            "next_allowed": block.get("next_allowed", []),
                        },
                        indent=2,
                    )
                )
                sys.exit(1)
        elif block_type == "user_decision_required" and "confirm_lightweight_flow" in block.get("next_allowed", []):
            # Lightweight-flow confirmation: LLM chose externally, user confirms
            confirmed = state.get("evidence", {}).get("lightweight_flow_confirmed")
            if confirmed:
                state["block"] = None
                state["status"] = "running"
                state["flow_type"] = "lightweight-flow"
            else:
                print(
                    json.dumps(
                        {
                            "error": "block not resolved",
                            "block_type": block_type,
                            "reason": "lightweight-flow not yet confirmed",
                            "next_allowed": block.get("next_allowed", []),
                            "recommendation": "record evidence: lightweight_flow_confirmed",
                        },
                        indent=2,
                    )
                )
                sys.exit(1)
        else:
            print(
                json.dumps(
                    {
                        "error": "block cannot be automatically resolved",
                        "block_type": block_type,
                        "block_message": block.get("message"),
                        "current_phase": state["current_phase"],
                        "next_allowed": block.get("next_allowed", []),
                        "recommendation": "review the block cause and take explicit action",
                    },
                    indent=2,
                )
            )
            sys.exit(1)
    else:
        state["status"] = "running"

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Record evidence and context
# ---------------------------------------------------------------------------

def cmd_record_evidence(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)
    if args.key and args.value is not None:
        try:
            val = json.loads(args.value)
        except (json.JSONDecodeError, TypeError):
            val = args.value
        state.setdefault("evidence", {})[args.key] = val
    save_run_state(root, state)
    print(json.dumps(state, indent=2))


def cmd_record_context(root, args):
    """Write a key into the run's context dict (e.g., change_id for roadmap promotion).

    Validates execution_mode-specific requirements before committing context
    changes (Spec Decision 5):
    - execution_mode must be one of VALID_EXECUTION_MODES when set.
    - When execution_mode is set to ``worktree``, required worktree fields
      (control_root, worktree_path, feature_branch) must already be present
      in the context after the write.
    """
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)
    if not args.key:
        print(json.dumps({"error": "key required for record-context"}, indent=2))
        sys.exit(1)
    if args.value is None:
        print(json.dumps({"error": "value required for record-context"}, indent=2))
        sys.exit(1)

    context = state.setdefault("context", {})

    # Validate execution_mode value when the key being set is execution_mode.
    if args.key == "execution_mode":
        if args.value not in VALID_EXECUTION_MODES:
            print(
                json.dumps(
                    {
                        "error": (
                            f"invalid execution_mode: {args.value!r}; "
                            f"must be one of {sorted(VALID_EXECUTION_MODES)}"
                        )
                    },
                    indent=2,
                )
            )
            sys.exit(1)

    # Apply the write to a tentative context for validation.
    tentative_context = dict(context)
    tentative_context[args.key] = args.value

    # When execution_mode is worktree, require worktree fields to be present.
    effective_mode = _resolve_execution_mode(tentative_context)
    if effective_mode == "worktree":
        missing = [f for f in WORKTREE_REQUIRED_FIELDS if not tentative_context.get(f)]
        if missing:
            print(
                json.dumps(
                    {
                        "error": (
                            "execution_mode=worktree requires context fields: "
                            + ", ".join(missing)
                            + ". Record them before or together with execution_mode."
                        )
                    },
                    indent=2,
                )
            )
            sys.exit(1)

    context[args.key] = args.value

    # Reconcile stale branch-decision blocks when a corrected valid
    # branch_finish_decision is recorded (Spec: repair-workflow-decision-block-unlock).
    if _should_reconcile_branch_decision_block(state, context, args.key):
        state["status"] = "running"
        state["block"] = None

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Complete phase and hooks
# ---------------------------------------------------------------------------

def cmd_complete_phase(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)
    wf = load_workflow(root, state.get("workflow", "sdlc-main"))
    if not wf:
        print(json.dumps({"error": "workflow not found"}, indent=2))
        sys.exit(1)

    current = state["current_phase"]
    phase_def = get_phase(wf, current)
    if not phase_def:
        print(json.dumps({"error": f"unknown phase: {current}"}, indent=2))
        sys.exit(1)

    exit_ok = _check_exit_criteria(state, phase_def, args.exit_criteria_satisfied)
    if not exit_ok:
        state["status"] = "blocked"
        state["block"] = {
            "type": "exit_criteria_failed",
            "message": "exit criteria not satisfied",
            "next_allowed": ["resolve", "block"],
        }
        save_run_state(root, state)
        print(json.dumps(state, indent=2))
        sys.exit(1)

    # P0 Sliced apply-change: aggregate review completion gate
    # and slicing assessment prerequisites.
    # Spec Invariants 1, 2: an active apply run must have persisted
    # implementation state.  Spec Decision 9: historical compatibility
    # cannot authorize active apply phase-completion gates.
    if current == "apply_change":
        if state.get("implementation") is None:
            print(json.dumps({
                "error": "Active apply run has no persisted implementation slicing state",
            }, indent=2))
            sys.exit(1)
        impl = normalize_implementation_state(state)
        # Spec Decision 9: slicing_assessment must be completed (not pending/blocked)
        # before phase completion is allowed.
        assessment = impl.get("slicing_assessment", {})
        assessment_status = assessment.get("status", "pending")
        if assessment_status in ("pending", "blocked"):
            print(json.dumps({
                "error": (
                    f"apply_change completion requires a completed "
                    f"slicing_assessment; status is {assessment_status!r}. "
                    "Run slice-init or resolve the assessment block first."
                ),
            }, indent=2))
            sys.exit(1)
        agg_status = impl.get("aggregate_review_status", "pending")
        if agg_status != "passed":
            print(json.dumps({
                "error": (
                    f"apply_change completion requires aggregate_review_status "
                    f"'passed', got {agg_status!r}. Dispatch aggregate review "
                    f"via slice-next and after-dispatch(review-agent, slice_id=aggregate)."
                ),
            }, indent=2))
            sys.exit(1)

    # Evidence key validation
    evidence_keys = phase_def.get("evidence_keys", [])
    if evidence_keys:
        run_evidence = state.get("evidence", {})
        missing = []
        empty_vals = []
        invalid_positive = []
        for ek in evidence_keys:
            if ek not in run_evidence:
                # Backward-compat alias: legacy archive_path_exists satisfies
                # archive_action_completed evidence key (Spec Decision 10).
                if ek == "archive_action_completed" and run_evidence.get("archive_path_exists"):
                    continue
                missing.append(ek)
            elif run_evidence[ek] is None or (isinstance(run_evidence[ek], str) and not run_evidence[ek].strip()):
                empty_vals.append(ek)
        invalid_positive = _invalid_positive_cleanup_evidence(current, run_evidence)
        if missing or empty_vals or invalid_positive:
            parts = []
            if missing:
                parts.append(f"missing evidence keys: {missing}")
            if empty_vals:
                parts.append(f"empty evidence keys: {empty_vals}")
            if invalid_positive:
                parts.append(
                    f"invalid positive cleanup evidence (must be True): {invalid_positive}"
                )
            print(
                json.dumps(
                    {"error": "; ".join(parts)},
                    indent=2,
                )
            )
            sys.exit(1)

    # Clear any stale block and restore running status
    if state.get("block"):
        state["block"] = None
    state["status"] = "running"

    completed = state.setdefault("completed_phases", [])
    if current not in completed:
        completed.append(current)

    for hook in phase_def.get("post_hooks", []):
        if _is_roadmap_hook(hook) and not _roadmap_agent_enabled(state):
            continue
        pending = state.setdefault("pending_hooks", [])
        if hook not in pending:
            pending.append(hook)

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


def _resolve_roadmap_hook_linked_items(state):
    """Resolve linked roadmap items from evidence for hook validation.

    Returns (items, link_count) where items is the list of linked items
    and link_count is the number of items (0, 1, or 2+).
    """
    raw = state.get("evidence", {}).get("roadmap_link")
    if not raw:
        return [], 0
    if isinstance(raw, dict):
        items = raw.get("items", [])
        count = raw.get("count", 0)
        if count == 0 or not items:
            return [], 0
        return items, count
    return [], 0


def _apply_roadmap_hook_block(state, hook_name, block_type, message, next_allowed=None):
    """Apply a block for a roadmap lifecycle hook and save state."""
    if next_allowed is None:
        next_allowed = ["resolve", "record-evidence", "block"]
    state["status"] = "blocked"
    state["block"] = {
        "type": block_type,
        "message": message,
        "next_allowed": next_allowed,
        "route_to_agent": "roadmap-agent",
        "remediation": "Use 'roadmap-agent' (sdlc-roadmap skill) to update the roadmap item state, then re-run complete-hook.",
    }
    return state


def cmd_complete_hook(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)

    hook_name = args.hook
    if not hook_name:
        print(json.dumps({"error": "hook name required"}, indent=2))
        sys.exit(1)

    pending = state.get("pending_hooks", [])
    if hook_name not in pending:
        print(json.dumps({"error": f"hook {hook_name} is not pending"}, indent=2))
        sys.exit(1)

    if hook_name == "memory_sync":
        resolution = args.resolution or "synced"
        if resolution not in VALID_MEMORY_SYNC_RESOLUTIONS:
            print(
                json.dumps(
                    {"error": f"invalid memory_sync resolution: {resolution}"}, indent=2
                )
            )
            sys.exit(1)
        if resolution == "not_needed" and not args.reason:
            print(
                json.dumps(
                    {"error": "not_needed requires explicit reason"}, indent=2
                )
            )
            sys.exit(1)
        if resolution == "user_deferred":
            if not args.reason:
                print(
                    json.dumps(
                        {"error": "user_deferred requires explicit reason"}, indent=2
                    )
                )
                sys.exit(1)
            state.setdefault("evidence", {})["memory_sync_residual_risk"] = (
                args.residual_risk or ""
            )
        state.setdefault("evidence", {})["memory_sync_resolution"] = resolution
        state.setdefault("evidence", {})["memory_sync_reason"] = args.reason or ""

    elif hook_name == "roadmap_spec_link_if_ready":
        items, count = _resolve_roadmap_hook_linked_items(state)
        if count == 0:
            state.setdefault("evidence", {})["roadmap_hook_resolution"] = "no_linked_item"
        elif count == 1:
            item = items[0]
            item_id = item.get("item_id")
            current = loader_roadmap_item_status(root, item_id)
            if current and current.get("status") == "ready":
                state.setdefault("evidence", {})["roadmap_hook_resolution"] = "spec_linked"
            else:
                observed_status = current.get("status") if current else item.get("status", "unknown")
                _apply_roadmap_hook_block(
                    state, hook_name, "domain_state_mismatch",
                    f"roadmap item {item_id} has status {observed_status}, expected ready before spec link",
                    ["resolve", "record-evidence", "block"],
                )
                save_run_state(root, state)
                print(json.dumps(state, indent=2))
                sys.exit(1)
        else:
            _apply_roadmap_hook_block(
                state, hook_name, "user_decision_required",
                "multiple roadmap items linked to this change",
                ["choose one item to link to spec", "repair roadmap links manually"],
            )
            state["block"]["candidates"] = items
            save_run_state(root, state)
            print(json.dumps(state, indent=2))
            sys.exit(1)

    elif hook_name == "roadmap_status_ready_if_linked":
        items, count = _resolve_roadmap_hook_linked_items(state)
        if count == 0:
            state.setdefault("evidence", {})["roadmap_hook_resolution"] = "no_linked_item"
        elif count == 1:
            item = items[0]
            item_id = item.get("item_id")
            current = loader_roadmap_item_status(root, item_id)
            if current and current.get("status") == "ready":
                state.setdefault("evidence", {})["roadmap_hook_resolution"] = "ready"
            else:
                observed_status = current.get("status") if current else item.get("status", "unknown")
                _apply_roadmap_hook_block(
                    state, hook_name, "domain_state_mismatch",
                    f"roadmap item {item_id} has status {observed_status}, expected ready",
                    ["resolve", "record-evidence", "block"],
                )
                save_run_state(root, state)
                print(json.dumps(state, indent=2))
                sys.exit(1)
        else:
            _apply_roadmap_hook_block(
                state, hook_name, "user_decision_required",
                "multiple roadmap items linked to this change",
                ["choose one item to mark ready", "repair roadmap links manually"],
            )
            state["block"]["candidates"] = items
            save_run_state(root, state)
            print(json.dumps(state, indent=2))
            sys.exit(1)

    elif hook_name == "roadmap_apply_start_if_ready":
        items, count = _resolve_roadmap_hook_linked_items(state)
        if count == 0:
            state.setdefault("evidence", {})["roadmap_hook_resolution"] = "no_linked_item"
        elif count == 1:
            item = items[0]
            item_id = item.get("item_id")
            current = loader_roadmap_item_status(root, item_id)
            if current and current.get("status") == "active" and current.get("started_at"):
                state.setdefault("evidence", {})["roadmap_hook_resolution"] = "active"
            else:
                observed_status = current.get("status") if current else item.get("status", "unknown")
                _apply_roadmap_hook_block(
                    state, hook_name, "domain_state_mismatch",
                    f"roadmap item {item_id} has status {observed_status}, expected active with started_at",
                    ["resolve", "record-evidence", "block"],
                )
                save_run_state(root, state)
                print(json.dumps(state, indent=2))
                sys.exit(1)
        else:
            _apply_roadmap_hook_block(
                state, hook_name, "user_decision_required",
                "multiple roadmap items linked to this change",
                ["choose one item to mark active", "repair roadmap links manually"],
            )
            state["block"]["candidates"] = items
            save_run_state(root, state)
            print(json.dumps(state, indent=2))
            sys.exit(1)

    elif hook_name == "roadmap_done_if_relevant":
        items, count = _resolve_roadmap_hook_linked_items(state)
        if count == 0:
            state.setdefault("evidence", {})["roadmap_hook_resolution"] = "no_linked_item"
        elif count == 1:
            item = items[0]
            status = item.get("status", "")
            if status == "done" and item.get("completed_at"):
                linked_item_run = _find_active_run_by_subject(
                    root, "roadmap_item", item.get("item_id")
                )
                if linked_item_run:
                    linked_change = linked_item_run.get("context", {}).get("change_id") or _read_roadmap_item_spec_change(root, item.get("item_id"))
                    if linked_change == state.get("context", {}).get("change_id"):
                        state.setdefault("evidence", {})["roadmap_hook_resolution"] = "done"
                        state.setdefault("evidence", {})["roadmap_item_run_finalized"] = linked_item_run.get("run_id")
                        if linked_item_run.get("run_id") == state.get("run_id"):
                            pending.remove(hook_name)
                            completed = state.setdefault("completed_hooks", [])
                            if hook_name not in completed:
                                completed.append(hook_name)
                            finalized = _finalize_run_to_history(root, state)
                            print(json.dumps(finalized, indent=2))
                            return
                        _finalize_run_to_history(root, linked_item_run)
                    else:
                        state.setdefault("evidence", {})["roadmap_hook_resolution"] = "idempotent_done"
                else:
                    state.setdefault("evidence", {})["roadmap_hook_resolution"] = "idempotent_done"
            elif status == "active":
                latest_status = loader_roadmap_item_status(root, item.get("item_id"))
                if latest_status and latest_status.get("status") == "done" and latest_status.get("completed_at"):
                    linked_item_run = _find_active_run_by_subject(
                        root, "roadmap_item", item.get("item_id")
                    )
                    if linked_item_run:
                        state.setdefault("evidence", {})["roadmap_hook_resolution"] = "done"
                        state.setdefault("evidence", {})["roadmap_item_run_finalized"] = linked_item_run.get("run_id")
                        if linked_item_run.get("run_id") == state.get("run_id"):
                            pending.remove(hook_name)
                            completed = state.setdefault("completed_hooks", [])
                            if hook_name not in completed:
                                completed.append(hook_name)
                            finalized = _finalize_run_to_history(root, state)
                            print(json.dumps(finalized, indent=2))
                            return
                        _finalize_run_to_history(root, linked_item_run)
                    else:
                        state.setdefault("evidence", {})["roadmap_hook_resolution"] = "done"
                else:
                    _apply_roadmap_hook_block(
                        state, hook_name, "hook_blocked",
                        f"roadmap item {item.get('item_id')} still active",
                        ["resolve", "record-evidence", "block"],
                    )
                    save_run_state(root, state)
                    print(json.dumps(state, indent=2))
                    sys.exit(1)
            elif status in ("idea", "ready", "cancelled"):
                _apply_roadmap_hook_block(
                    state, hook_name, "domain_state_mismatch",
                    f"roadmap item {item.get('item_id')} has status {status}",
                    ["resolve", "block"],
                )
                save_run_state(root, state)
                print(json.dumps(state, indent=2))
                sys.exit(1)
        else:
            _apply_roadmap_hook_block(
                state, hook_name, "user_decision_required",
                "multiple roadmap items linked to this change",
                [
                    "choose one item to mark done",
                    "repair roadmap links manually",
                    "mark all active matches done with reason",
                    "skip roadmap done with reason",
                ],
            )
            state["block"]["candidates"] = items
            save_run_state(root, state)
            print(json.dumps(state, indent=2))
            sys.exit(1)

    pending.remove(hook_name)
    completed = state.setdefault("completed_hooks", [])
    if hook_name not in completed:
        completed.append(hook_name)

    # Clear hook_blocked block when all pending hooks are resolved.
    if not pending and state.get("block") and state.get("block", {}).get("type") == "hook_blocked":
        state["block"] = None
        if state.get("status") == "blocked":
            state["status"] = "running"

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Cancel, advance, block, done
# ---------------------------------------------------------------------------

def cmd_cancel_run(root, args):
    """Remove an active run without writing history. Used for replanned roadmap items."""
    subject_type = args.subject_type or "roadmap_item"
    subject_id = args.subject_id
    reason = args.reason or "cancelled"

    if not subject_id:
        print(json.dumps({"error": "subject-id required for cancel-run"}))
        sys.exit(1)

    active = _find_active_run_by_subject(root, subject_type, subject_id)
    if not active:
        print(json.dumps({"status": "not_found", "message": f"no active run for {subject_type}/{subject_id}"}))
        return

    run_id = active["run_id"]
    pointer = _read_pointer(root)
    if pointer and pointer.get("run_id") == run_id:
        _clear_pointer(root)

    _cancel_active_run(root, run_id)

    print(json.dumps({"status": "cancelled", "run_id": run_id, "reason": reason}))


def cmd_advance(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)

    if state.get("status") == "blocked":
        block = state.get("block", {})
        phase_complete = is_phase_complete(state, state["current_phase"])
        print(
            json.dumps(
                {
                    "error": "run is blocked, cannot advance",
                    "current_phase": state["current_phase"],
                    "phase_complete": phase_complete,
                    "block": {
                        "type": block.get("type"),
                        "message": block.get("message"),
                        "next_allowed": block.get("next_allowed", []),
                    },
                    "recommendation": (
                        "resolve the block before advancing"
                        if not phase_complete
                        else "phase is complete — resolve block then advance"
                    ),
                },
                indent=2,
            )
        )
        sys.exit(1)

    wf = load_workflow(root, state.get("workflow", "sdlc-main"))
    if not wf:
        print(json.dumps({"error": "workflow not found"}, indent=2))
        sys.exit(1)

    current = state["current_phase"]
    phase_def = get_phase(wf, current)
    if not phase_def:
        print(json.dumps({"error": f"unknown phase: {current}"}, indent=2))
        sys.exit(1)

    if not is_phase_complete(state, current):
        print(json.dumps({"error": f"phase {current} is not complete"}, indent=2))
        sys.exit(1)

    if phase_def.get("post_hooks"):
        for hook in phase_def.get("post_hooks", []):
            if hook in state.get("pending_hooks", []):
                print(
                    json.dumps(
                        {
                            "error": f"post hook {hook} is pending, complete hooks first",
                        },
                        indent=2,
                    )
                )
                sys.exit(1)

    if phase_def.get("terminal"):
        finish_blocker = _missing_terminal_finish_agent_evidence(state)
        if finish_blocker:
            print(json.dumps(finish_blocker, indent=2))
            sys.exit(1)

        drift_blocker = _terminal_derived_artifact_drift(root, state)
        if drift_blocker:
            print(json.dumps(drift_blocker, indent=2))
            sys.exit(1)

        state["current_phase"] = "done"
        save_run_state(root, state)
        print(json.dumps(state, indent=2))
        return

    branches = phase_def.get("branches")
    if branches:
        decision_key = args.branch or state.get("context", {}).get("review_decision")
        if not decision_key:
            state["status"] = "blocked"
            state["block"] = {
                "type": "user_decision_required",
                "message": "branch decision required",
                "next_allowed": ["resolve", "block"],
                "allowed_branches": list(branches.keys()),
            }
            save_run_state(root, state)
            print(json.dumps(state, indent=2))
            sys.exit(1)
        if decision_key not in branches:
            state["status"] = "blocked"
            state["block"] = {
                "type": "user_decision_required",
                "message": f"unknown branch: {decision_key}",
                "next_allowed": ["resolve", "block"],
                "allowed_branches": list(branches.keys()),
            }
            save_run_state(root, state)
            print(json.dumps(state, indent=2))
            sys.exit(1)
        next_phase = branches[decision_key]
    elif phase_def.get("next"):
        next_phase = phase_def["next"]
    else:
        print(json.dumps({"error": "no next phase or terminal defined"}, indent=2))
        sys.exit(1)

    state["current_phase"] = next_phase
    state["phase_readiness"] = {"phase": next_phase, "ready": False, "missing_required_inputs": []}
    _run_loaders(root, state, wf)
    _calc_readiness(state, wf)

    # Slicing assessment gate: when advancing into apply_change, require
    # a valid materialized assessment.  If planning completed without
    # assessment, install the slicing blocker instead of advancing into
    # running apply.  Do not reset user approval or regenerate design artifacts.
    if next_phase == "apply_change":
        if state.get("implementation") is None:
            state["implementation"] = make_pending_implementation_state()
            state["status"] = "blocked"
            state["block"] = make_slicing_assessment_block()
            state["phase_readiness"] = {
                "phase": "apply_change",
                "ready": False,
                "missing_required_inputs": ["validated_implementation_slices"],
            }
        else:
            # Validate existing implementation state; block if invalid.
            impl_errors = active_apply_slicing_errors(state)
            if impl_errors:
                state["status"] = "blocked"
                state["block"] = make_slicing_assessment_block()
                state["phase_readiness"] = {
                    "phase": "apply_change",
                    "ready": False,
                    "missing_required_inputs": ["validated_implementation_slices"],
                }

    if next_phase == "done":
        pending = state.get("pending_hooks", [])
        if pending:
            state["status"] = "blocked"
            state["block"] = {
                "type": "hook_blocked",
                "message": f"pending hooks remain: {pending}",
                "next_allowed": ["resolve", "record-evidence", "block"],
            }
            save_run_state(root, state)
            print(json.dumps(state, indent=2))
            sys.exit(1)

        required_gates = state.get("gates", {})
        for gid, gate in required_gates.items():
            if gate.get("status") == "required":
                state["status"] = "blocked"
                state["block"] = {
                    "type": "exit_criteria_failed",
                    "message": f"required gate {gid} not resolved",
                    "next_allowed": ["resolve", "record-evidence", "block"],
                }
                save_run_state(root, state)
                print(json.dumps(state, indent=2))
                sys.exit(1)

        # Option B: refuse terminal movement when required final lifecycle
        # finish-agent evidence is missing (Spec Decision 9).
        finish_blocker = _missing_terminal_finish_agent_evidence(state)
        if finish_blocker:
            print(json.dumps(finish_blocker, indent=2))
            sys.exit(1)

        drift_blocker = _terminal_derived_artifact_drift(root, state)
        if drift_blocker:
            print(json.dumps(drift_blocker, indent=2))
            sys.exit(1)

        state["status"] = "done"
        state = _move_run_to_history(root, state)

        print(json.dumps(state, indent=2))
        return

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


def cmd_block(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)

    block_type = args.block_type or "user_decision_required"
    if block_type not in VALID_BLOCK_TYPES:
        print(json.dumps({"error": f"invalid block type: {block_type}"}, indent=2))
        sys.exit(1)

    state["status"] = "blocked"
    state["block"] = {
        "type": block_type,
        "message": args.message or "blocked",
        "next_allowed": args.next_allowed.split(",") if args.next_allowed else [],
    }
    save_run_state(root, state)
    print(json.dumps(state, indent=2))


def cmd_done(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)

    pending = state.get("pending_hooks", [])
    if pending:
        state["status"] = "blocked"
        state["block"] = {
            "type": "hook_blocked",
            "message": f"pending hooks remain: {pending}",
            "next_allowed": ["resolve", "record-evidence", "block"],
        }
        save_run_state(root, state)
        print(json.dumps(state, indent=2))
        sys.exit(1)

    required_gates = {
        k: v
        for k, v in state.get("gates", {}).items()
        if v.get("status") not in ("passed", "not_required", "user_exception")
    }
    required_gates = {
        k: v for k, v in required_gates.items() if v.get("status") == "required"
    }
    if required_gates:
        state["status"] = "blocked"
        state["block"] = {
            "type": "exit_criteria_failed",
            "message": f"required gates not resolved: {list(required_gates.keys())}",
            "next_allowed": ["resolve", "record-evidence", "block"],
        }
        save_run_state(root, state)
        print(json.dumps(state, indent=2))
        sys.exit(1)

    if state.get("current_phase") != "done":
        print(
            json.dumps(
                {
                    "error": "run is not in terminal phase",
                    "current_phase": state["current_phase"],
                    "completed_phases": state.get("completed_phases", []),
                    "hint": "advance through phases until 'done' before calling done",
                },
                indent=2,
            )
        )
        sys.exit(1)

    if state.get("status") == "blocked":
        print(json.dumps({"error": "run is blocked, cannot complete"}, indent=2))
        sys.exit(1)

    # Option B: refuse terminal movement when required final lifecycle
    # finish-agent evidence is missing (Spec Decision 9).
    finish_blocker = _missing_terminal_finish_agent_evidence(state)
    if finish_blocker:
        print(json.dumps(finish_blocker, indent=2))
        sys.exit(1)

    drift_blocker = _terminal_derived_artifact_drift(root, state)
    if drift_blocker:
        print(json.dumps(drift_blocker, indent=2))
        sys.exit(1)

    state["status"] = "done"
    state["updated_at"] = _ts()

    state = _move_run_to_history(root, state)

    print(json.dumps(state, indent=2))
