"""slices.py — implementation slice lifecycle commands.

P0 sliced apply-change: read-only slice-status, deterministic slice-next,
and exceptional-control slice-block / slice-resume / slice-cancel commands.

These commands operate on the ``implementation`` block of run state and
delegate validation to ``state.validate_implementation_state``.
"""

import json
import sys

from workflow_runtime.state import (
    load_run_state,
    save_run_state,
    normalize_implementation_state,
    validate_implementation_state,
    active_apply_slicing_errors,
    make_pending_implementation_state,
    make_slicing_assessment_block,
    make_no_decomposition_implementation_state,
    slice_is_ready,
    all_required_slices_completed,
    ACTIVE_SLICE_STATUSES,
)
from workflow_runtime.core import _ts


def _emit(data, exit_code=0):
    """Print JSON and exit with the given code."""
    print(json.dumps(data, indent=2))
    if exit_code != 0:
        sys.exit(exit_code)


def _no_active_run_blocker():
    return {
        "status": "blocked",
        "errors": [{
            "reason": "no_active_run",
            "message": "No active workflow run exists",
            "slice_ids": [],
        }],
    }


def _slice_view(sl):
    """Return a public-safe view of a slice dict."""
    return dict(sl)


def cmd_slice_status(root, args):
    """Read-only slice status report for all slices or one selected slice."""
    state = load_run_state(root)
    if not state:
        _emit(_no_active_run_blocker(), exit_code=1)
        return

    # Slicing assessment gate: an active apply run without persisted
    # implementation state cannot report a synthetic default slice.
    # Use active_apply_slicing_errors rather than normalize_implementation_state
    # so missing state is reported instead of silently synthesized.
    if state.get("current_phase") == "apply_change" and state.get("status") in ("running", "blocked"):
        impl = state.get("implementation")
        if impl is None:
            _emit({
                "status": "assessment_required",
                "reason": "missing_slicing_assessment",
                "recommended_next_action": "run_slice_init",
            }, exit_code=0)
            return
        assessment_status = impl.get("slicing_assessment", {}).get("status", "")
        if assessment_status in ("pending", "blocked"):
            _emit({
                "status": "assessment_required",
                "reason": f"slicing_assessment_{assessment_status}",
                "recommended_next_action": "dispatch_plan_agent_for_slicing_assessment",
            }, exit_code=0)
            return
        errors = validate_implementation_state(impl)
        if errors:
            _emit({"status": "error", "errors": errors}, exit_code=2)
            return
    else:
        impl = normalize_implementation_state(state)
        errors = validate_implementation_state(impl)
        if errors:
            _emit({"status": "error", "errors": errors}, exit_code=2)
            return

    target = getattr(args, "slice_id", None)
    if target:
        slices = [s for s in impl.get("slices", []) if s.get("slice_id") == target]
        if not slices:
            _emit({
                "status": "error",
                "errors": [{
                    "reason": "unknown_slice",
                    "message": f"slice {target!r} not found",
                    "slice_ids": [target],
                }],
            }, exit_code=2)
            return
    else:
        slices = impl.get("slices", [])

    _emit({
        "status": "ok",
        "strategy": impl.get("strategy", "sequential"),
        "slicing_assessment": impl.get("slicing_assessment", {}),
        "aggregate_review_status": impl.get("aggregate_review_status", "pending"),
        "active_slice_id": impl.get("active_slice_id"),
        "slices": [_slice_view(s) for s in slices],
    })


def cmd_slice_next(root, args):
    """Deterministic, non-mutating selection of the next slice to dispatch.

    Returns one of:
    - ``dispatch_slice`` with one declaration-ordered ready slice;
    - ``dispatch_aggregate_review``;
    - ``all_slices_and_aggregate_complete``;
    - ``assessment_required`` when slicing assessment is missing or pending;
    - ``no_ready_slice`` diagnostics.
    """
    state = load_run_state(root)
    if not state:
        _emit(_no_active_run_blocker(), exit_code=1)
        return

    # Slicing assessment gate: an active apply run without persisted
    # implementation state or with pending/blocked assessment cannot
    # synthesize a default slice.
    if state.get("current_phase") == "apply_change" and state.get("status") in ("running", "blocked"):
        impl = state.get("implementation")
        if impl is None:
            _emit({
                "status": "assessment_required",
                "reason": "missing_slicing_assessment",
                "recommended_next_action": "run_slice_init",
            }, exit_code=0)
            return
        assessment_status = impl.get("slicing_assessment", {}).get("status", "")
        if assessment_status == "pending":
            _emit({
                "status": "assessment_required",
                "reason": "slicing_assessment_pending",
                "recommended_next_action": "dispatch_plan_agent_for_slicing_assessment",
            }, exit_code=0)
            return
        if assessment_status == "blocked":
            _emit({
                "status": "assessment_required",
                "reason": "slicing_assessment_blocked",
                "recommended_next_action": "resolve_assessment_block",
            }, exit_code=0)
            return
        errors = validate_implementation_state(impl)
        if errors:
            _emit({"status": "error", "errors": errors}, exit_code=2)
            return
    else:
        impl = normalize_implementation_state(state)
        errors = validate_implementation_state(impl)
        if errors:
            _emit({"status": "error", "errors": errors}, exit_code=2)
            return

    slices = impl.get("slices", []) or []
    active = [s for s in slices if s.get("status") in ACTIVE_SLICE_STATUSES]
    active_ids = set(s.get("slice_id", "") for s in active)

    # If any slice is active, we can't dispatch a new one.
    if active:
        _emit({
            "status": "no_ready_slice",
            "reason": "slice_in_progress",
            "active_slice_id": active[0].get("slice_id", ""),
            "active_status": active[0].get("status", ""),
        })
        return

    # Check if all required slices are completed.
    if all_required_slices_completed(impl):
        agg = impl.get("aggregate_review_status", "pending")
        if agg == "passed":
            _emit({"status": "all_slices_and_aggregate_complete"})
            return
        # Dispatch aggregate review.
        _emit({"status": "dispatch_aggregate_review"})
        return

    # Find the first ready slice in declaration order.
    by_id = {s.get("slice_id", ""): s for s in slices}
    for sl in slices:
        if sl.get("status") == "cancelled":
            continue
        if slice_is_ready(sl, by_id, active_ids):
            _emit({
                "status": "dispatch_slice",
                "slice_id": sl.get("slice_id", ""),
                "slice": _slice_view(sl),
            })
            return

    # No ready slice — check if any are blocked.
    blocked = [s.get("slice_id", "") for s in slices if s.get("status") == "blocked"]
    _emit({
        "status": "no_ready_slice",
        "reason": "no_ready_slice_available",
        "blocked_slice_ids": blocked,
    })


def cmd_slice_block(root, args):
    """Block a slice with explicit exceptional-control evidence."""
    state = load_run_state(root)
    if not state:
        _emit(_no_active_run_blocker(), exit_code=1)
        return

    slice_id = getattr(args, "slice_id", None) or ""
    if not slice_id:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "missing_slice_id",
                "message": "--slice-id is required for slice-block",
                "slice_ids": [],
            }],
        }, exit_code=2)
        return

    block_value = getattr(args, "value", None) or "{}"
    try:
        block_data = json.loads(block_value)
    except (json.JSONDecodeError, TypeError):
        block_data = {"raw": block_value}

    impl = state.get("implementation")
    if impl is None:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "no_implementation_state",
                "message": "run has no implementation slice state",
                "slice_ids": [],
            }],
        }, exit_code=2)
        return

    slices = impl.get("slices", []) or []
    found = False
    for sl in slices:
        if sl.get("slice_id") == slice_id:
            sl["status"] = "blocked"
            sl["block"] = block_data
            found = True
            break

    if not found:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "unknown_slice",
                "message": f"slice {slice_id!r} not found",
                "slice_ids": [slice_id],
            }],
        }, exit_code=2)
        return

    impl["active_slice_id"] = None
    state["updated_at"] = _ts()
    save_run_state(root, state)

    _emit({"status": "ok", "slice_id": slice_id, "block": block_data})


def cmd_slice_resume(root, args):
    """Resume a blocked slice -> ready only when dependencies remain accepted."""
    state = load_run_state(root)
    if not state:
        _emit(_no_active_run_blocker(), exit_code=1)
        return

    slice_id = getattr(args, "slice_id", None) or ""
    if not slice_id:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "missing_slice_id",
                "message": "--slice-id is required for slice-resume",
                "slice_ids": [],
            }],
        }, exit_code=2)
        return

    impl = state.get("implementation")
    if impl is None:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "no_implementation_state",
                "message": "run has no implementation slice state",
                "slice_ids": [],
            }],
        }, exit_code=2)
        return

    slices = impl.get("slices", []) or []
    found = False
    for sl in slices:
        if sl.get("slice_id") == slice_id:
            if sl.get("status") != "blocked":
                _emit({
                    "status": "error",
                    "errors": [{
                        "reason": "slice_not_blocked",
                        "message": f"slice {slice_id!r} status is {sl.get('status')!r}, not 'blocked'",
                        "slice_ids": [slice_id],
                    }],
                }, exit_code=2)
                return
            # Check dependencies remain accepted.
            by_id = {s.get("slice_id", ""): s for s in slices}
            for dep in sl.get("depends_on", []) or []:
                dep_sl = by_id.get(dep)
                if not dep_sl or dep_sl.get("status") != "completed":
                    _emit({
                        "status": "error",
                        "errors": [{
                            "reason": "dependency_not_accepted",
                            "message": f"dependency {dep!r} is not completed",
                            "slice_ids": [slice_id],
                        }],
                    }, exit_code=2)
                    return
            sl["status"] = "ready"
            sl["block"] = None
            found = True
            break

    if not found:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "unknown_slice",
                "message": f"slice {slice_id!r} not found",
                "slice_ids": [slice_id],
            }],
        }, exit_code=2)
        return

    state["updated_at"] = _ts()
    save_run_state(root, state)

    _emit({"status": "ok", "slice_id": slice_id})


def cmd_slice_cancel(root, args):
    """Cancel a required slice with explicit decision/exception evidence."""
    state = load_run_state(root)
    if not state:
        _emit(_no_active_run_blocker(), exit_code=1)
        return

    slice_id = getattr(args, "slice_id", None) or ""
    if not slice_id:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "missing_slice_id",
                "message": "--slice-id is required for slice-cancel",
                "slice_ids": [],
            }],
        }, exit_code=2)
        return

    reason = getattr(args, "reason", None) or ""
    if not reason:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "missing_cancel_reason",
                "message": "--reason is required to cancel a required slice",
                "slice_ids": [slice_id],
            }],
        }, exit_code=2)
        return

    impl = state.get("implementation")
    if impl is None:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "no_implementation_state",
                "message": "run has no implementation slice state",
                "slice_ids": [],
            }],
        }, exit_code=2)
        return

    slices = impl.get("slices", []) or []
    found = False
    for sl in slices:
        if sl.get("slice_id") == slice_id:
            sl["status"] = "cancelled"
            sl["block"] = {"reason": "cancelled", "message": reason}
            found = True
            break

    if not found:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "unknown_slice",
                "message": f"slice {slice_id!r} not found",
                "slice_ids": [slice_id],
            }],
        }, exit_code=2)
        return

    impl["active_slice_id"] = None
    state["updated_at"] = _ts()
    save_run_state(root, state)

    _emit({"status": "ok", "slice_id": slice_id, "reason": reason})


def cmd_slice_init(root, args):
    """Explicitly initialize implementation state for a legacy active run.

    Limited to active ``apply_change`` runs.  Creates pending implementation
    state, sets the ``slicing_assessment_required`` blocker, records
    timestamped migration evidence, and clears an unconsumed implement-agent
    dispatch intent only when no matching agent result exists.

    With ``--skip-assessment``, materializes a governed ``default`` slice
    directly under a ``not_required`` assessment (requires a non-empty
    reason).

    Does not touch repository source, tests, plans, or other worktree files.
    """
    run_id = getattr(args, "run_id", None) or None
    state = load_run_state(root, run_id=run_id)
    if not state:
        _emit(_no_active_run_blocker(), exit_code=1)
        return

    reason = (getattr(args, "reason", None) or "").strip()
    if not reason:
        _emit({
            "status": "error",
            "errors": [{
                "reason": "missing_repair_reason",
                "message": "--reason is required for slice-init",
                "slice_ids": [],
            }],
        }, exit_code=2)
        return

    if state.get("current_phase") != "apply_change":
        _emit({
            "status": "error",
            "errors": [{
                "reason": "slice_init_wrong_phase",
                "message": f"slice-init is limited to apply_change runs, got phase {state.get('current_phase')!r}",
                "slice_ids": [],
            }],
        }, exit_code=2)
        return

    skip_assessment = getattr(args, "skip_assessment", False) or False
    existing_impl = state.get("implementation")

    if existing_impl is not None:
        # Validate existing implementation; if valid, this is a no-op.
        errors = validate_implementation_state(existing_impl)
        if not errors and existing_impl.get("slicing_assessment", {}).get("status") in ("completed", "not_required"):
            _emit({
                "status": "ok",
                "message": "implementation already valid",
            })
            return
        if errors:
            _emit({
                "status": "error",
                "errors": [{
                    "reason": "existing_implementation_invalid",
                    "message": "refusing to overwrite a malformed partial implementation block",
                    "slice_ids": [],
                }],
            }, exit_code=2)
            return

    # Check for unconsumed implement-agent dispatch intent.
    evidence = state.get("evidence", {}) or {}
    agent_phase = evidence.get("agent_phase", {}) or {}
    intent_agent = agent_phase.get("agent", "") if isinstance(agent_phase, dict) else ""
    cleared_intent = False

    if intent_agent == "implement-agent":
        # Check if a matching agent result exists.
        agent_results = evidence.get("agent_results", {}) or {}
        intent_slice_id = agent_phase.get("slice_id", "") or "default"
        matching_results = agent_results.get(intent_slice_id, {}) or {}
        if matching_results.get("implement-agent"):
            _emit({
                "status": "error",
                "errors": [{
                    "reason": "matching_agent_result_exists",
                    "message": "refusing destructive repair: matching implement-agent result exists",
                    "slice_ids": [intent_slice_id],
                }],
            }, exit_code=2)
            return
        # Clear the unconsumed intent.
        evidence.pop("agent_phase", None)
        cleared_intent = True

    # Materialize the appropriate implementation state.
    if skip_assessment:
        new_impl = make_no_decomposition_implementation_state(reason, assessed_by="user")
        state["implementation"] = new_impl
        state["status"] = "running"
        state["block"] = None
        state["phase_readiness"] = {
            "phase": "apply_change",
            "ready": True,
            "missing_required_inputs": [],
        }
    else:
        new_impl = make_pending_implementation_state()
        state["implementation"] = new_impl
        state["status"] = "blocked"
        state["block"] = make_slicing_assessment_block()
        state["phase_readiness"] = {
            "phase": "apply_change",
            "ready": False,
            "missing_required_inputs": ["validated_implementation_slices"],
        }

    # Record migration evidence.
    migration = {
        "action": "slice_init",
        "reason": reason,
        "migrated_at": _ts(),
        "previous_implementation_present": existing_impl is not None,
        "cleared_dispatch_intent": cleared_intent,
    }
    if skip_assessment:
        migration["skip_assessment"] = True
    state.setdefault("slicing_migrations", []).append(migration)

    state["updated_at"] = _ts()
    save_run_state(root, state)

    _emit({"status": "ok", "migration": migration})