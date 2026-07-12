"""policies.py — policy registry, decorators, evaluation, and preflight.

Contains POLICY_REGISTRY, POLICY_META, policy decorators, policy functions,
subject/run-context evaluation, cmd_preflight, and cmd_ensure_run.
"""

import json
import os
import sys

from workflow_runtime.core import (
    _make_run_id,
    _resolve_path,
)
from workflow_runtime.state import (
    load_run_state,
    _set_pointer,
    _list_active_runs,
    _find_active_run_by_subject,
    _list_dirs,
    save_run_state,
)
from workflow_runtime.definitions import (
    load_workflow,
    _run_loaders,
)
from workflow_runtime.domains import (
    loader_openspec_change_status,
    loader_spec_change_status,
    loader_spec_archive_path,
    loader_roadmap_linked_item,
    loader_roadmap_item_status,
    _read_roadmap_item_spec_change,
    _read_frontmatter_field,
    _infer_phase,
)


# ---------------------------------------------------------------------------
# Done history helpers
# ---------------------------------------------------------------------------

def _load_done_history_run_ids(root):
    """Return set of (subject_type, subject_id) from done history runs."""
    governed = set()
    history_dir = _resolve_path(root, ".ai/workflows/runs/history")
    if not os.path.isdir(history_dir):
        return governed
    for entry in _list_dirs(history_dir):
        entry_path = os.path.join(history_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        run_json_path = os.path.join(entry_path, "run.json")
        if not os.path.isfile(run_json_path):
            continue
        try:
            with open(run_json_path, "r") as f:
                hist = json.load(f)
        except Exception:
            continue
        if hist.get("status") in ("done",):
            ps = hist.get("primary_subject", {})
            if ps.get("type") and ps.get("id"):
                governed.add((ps["type"], ps["id"]))
    return governed


def _make_preflight_decision(allowed, status, reason="", next_action=None):
    return {
        "allowed": allowed,
        "status": status,
        "reason": reason,
        "next_action": next_action,
    }


def _evaluate_subject_run_context(root, subject_type, subject_id):
    """Return (active_state_matching_subject, done_subjects_set). Sets pointer to matching run if found."""
    active = load_run_state(root)
    if active:
        ps = active.get("primary_subject", {})
        if ps.get("type") == subject_type and ps.get("id") == subject_id:
            done_subjects = _load_done_history_run_ids(root)
            return active, done_subjects

    matching = _find_active_run_by_subject(root, subject_type, subject_id)
    if matching:
        _set_pointer(root, matching["run_id"])

    done_subjects = _load_done_history_run_ids(root)
    return matching, done_subjects


# ---------------------------------------------------------------------------
# Policy registry
# ---------------------------------------------------------------------------

POLICY_REGISTRY = {}
POLICY_META = {}  # action -> {allowed_phases, repair_hooks, creates_run}

# Backward-compat: ACTION_PHASE_MAP for quick lookups
ACTION_PHASE_MAP = {}


def register_policy(action, *, allowed_phases=None, repair_hooks=None, creates_run=False):
    """Decorator to register a policy function for a governed action.

    Args:
        action: Governed action name.
        allowed_phases: Set of phase names this action is valid for (None = no restriction).
        repair_hooks: List of hook names to set pending when ensure-run creates a run.
        creates_run: Whether ensure-run is allowed to create a run for this action.
    """
    def decorator(fn):
        POLICY_REGISTRY[action] = fn
        POLICY_META[action] = {
            "allowed_phases": allowed_phases,
            "repair_hooks": repair_hooks or [],
            "creates_run": creates_run,
        }
        if allowed_phases is not None:
            ACTION_PHASE_MAP[action] = allowed_phases
        return fn
    return decorator


def _validate_action_phase(action, active_state):
    """Check that the active run's current_phase is valid for the action.
    Returns (is_valid, allowed_phases_set_or_None)."""
    allowed = ACTION_PHASE_MAP.get(action)
    if allowed is None:
        return True, None
    if not active_state:
        return True, None  # no-phase restriction only applies when a run exists
    current = active_state.get("current_phase", "")
    return current in allowed, allowed


def _start_command(subject_type, subject_id):
    """Return a next_action dict for workflow start."""
    return {
        "command": (
            f"python3 .ai/workflows/scripts/workflow.py --root . start"
            f" --subject-type {subject_type} --subject-id {subject_id}"
        ),
        "description": (
            f"Create a new workflow run for '{subject_id}'"
            f" then re-run preflight"
        ),
    }


def _find_linked_roadmap_run(root, change_id):
    """Scan active roadmap_item runs for a context.change_id or
    frontmatter spec_change/openspec_change matching a given change_id."""
    for _run_id, state in _list_active_runs(root):
        ps = state.get("primary_subject", {})
        if ps.get("type") != "roadmap_item":
            continue
        ctx = state.get("context", {})
        if ctx.get("change_id") == change_id:
            return state
        roadmap_item_id = ctx.get("roadmap_item_id") or ps.get("id")
        if roadmap_item_id:
            linked_change = _read_roadmap_item_spec_change(root, roadmap_item_id)
            if linked_change == change_id:
                return state
    return None


def _read_roadmap_item_openspec_change(root, item_id):
    """Read openspec_change frontmatter field from a roadmap item file."""
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    for area in _list_dirs(areas_dir):
        items_dir = os.path.join(areas_dir, area, "items")
        if not os.path.isdir(items_dir):
            continue
        for fname in _list_dirs(items_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(items_dir, fname)
            fm_id = _read_frontmatter_field(fpath, "id")
            if fm_id == item_id:
                return _read_frontmatter_field(fpath, "openspec_change")
    return None


def _ensure_command(subject_type, subject_id):
    """Return a next_action dict for workflow ensure-run."""
    return {
        "command": (
            f"python3 .ai/workflows/scripts/workflow.py --root . ensure-run"
            f" --action dangling_archive_repair"
            f" --subject-type {subject_type} --subject-id {subject_id}"
        ),
        "description": (
            f"Restore SDLC governance for archived change '{subject_id}'."
            f" Creates a post_archive_actions run with post-archive hooks."
            f" After hooks are resolved, complete-phase and advance to done."
        ),
    }


# --- Policies ---

@register_policy(
    "spec_create", allowed_phases={"create_change", "input"},
)
@register_policy(
    "spec_continue", allowed_phases={"create_change", "apply_change"},
)
@register_policy(
    "spec_apply", allowed_phases={"apply_change"},
)
@register_policy(
    "spec_archive", allowed_phases={"archive_change"},
)
@register_policy(
    "openspec_create", allowed_phases={"create_change", "input"},
)
@register_policy(
    "openspec_continue", allowed_phases={"create_change", "apply_change"},
)
@register_policy(
    "openspec_apply", allowed_phases={"apply_change"},
)
@register_policy(
    "openspec_archive", allowed_phases={"archive_change"},
)
def _policy_openspec_change(root, action, subject_type, subject_id):
    """Require matching active run or done history for openspec lifecycle actions.
    Also validates the run's current phase against the action via ACTION_PHASE_MAP."""
    if not subject_type or not subject_id:
        return _make_preflight_decision(False, "error", "missing_subject")
    active, done_subjects = _evaluate_subject_run_context(root, subject_type, subject_id)

    # Done history exists => lifecycle already completed
    if (subject_type, subject_id) in done_subjects:
        return _make_preflight_decision(True, "ok", "done_history_exists")

    # No active run => check for canonical linked roadmap_item run (promotion)
    if not active and action in ("openspec_create", "spec_create"):
        linked = _find_linked_roadmap_run(root, subject_id)
        if linked:
            _set_pointer(root, linked["run_id"])
            phase_ok, allowed_phases = _validate_action_phase(action, linked)
            if not phase_ok:
                current = linked["current_phase"]
                return _make_preflight_decision(
                    False, "blocked", "wrong_phase",
                    next_action={
                        "command": "python3 .ai/workflows/scripts/workflow.py --root . advance",
                        "description": (
                            f"Linked roadmap item run is in phase '{current}',"
                            f" but action '{action}' requires one of:"
                            f" {sorted(allowed_phases)}."
                            f" Advance the run to the correct phase first."
                        ),
                    },
                )
            return _make_preflight_decision(
                True, "ok", "linked_roadmap_run_exists",
            )

    # No active run => block, require start
    if not active:
        return _make_preflight_decision(
            False, "blocked", "missing_active_run",
            next_action=_start_command(subject_type, subject_id),
        )

    # Active run exists - check subject match
    active_ps = active.get("primary_subject", {})
    active_status = active.get("status", "")
    if (
        active_ps.get("type") == subject_type
        and active_ps.get("id") == subject_id
        and active_status in ("running", "blocked")
    ):
        # Phase validation
        phase_ok, allowed_phases = _validate_action_phase(action, active)
        if not phase_ok:
            current = active["current_phase"]
            return _make_preflight_decision(
                False, "blocked", "wrong_phase",
                next_action={
                    "command": "python3 .ai/workflows/scripts/workflow.py --root . advance",
                    "description": (
                        f"Run is in phase '{current}', but action '{action}'"
                        f" requires one of: {sorted(allowed_phases)}."
                        f" Advance the run to the correct phase first."
                    ),
                },
            )
        return _make_preflight_decision(True, "ok", "active_run_exists")

    # Different active run => conflict
    return _make_preflight_decision(
        False, "blocked", "conflict_active_run",
        next_action={
            "command": "python3 .ai/workflows/scripts/workflow.py --root . status",
            "description": (
                f"Active run for '{active_ps.get('id')}' exists."
                f" Complete or cancel it before starting '{subject_id}'."
            ),
        },
    )


@register_policy(
    "post_archive_actions", allowed_phases={"post_archive_actions"},
)
@register_policy(
    "dangling_archive_repair",
    allowed_phases={"post_archive_actions"},
    repair_hooks=["memory_sync", "roadmap_done_if_relevant"],
    creates_run=True,
)
def _policy_archived_change(root, action, subject_type, subject_id):
    """Archived changes must have an active run or done history."""
    if not subject_type or not subject_id:
        return _make_preflight_decision(False, "error", "missing_subject")
    active, done_subjects = _evaluate_subject_run_context(root, subject_type, subject_id)

    if (subject_type, subject_id) in done_subjects:
        return _make_preflight_decision(True, "ok", "done_history_exists")

    if not active:
        return _make_preflight_decision(
            False, "blocked", "missing_active_run",
            next_action=_ensure_command(subject_type, subject_id),
        )

    active_ps = active.get("primary_subject", {})
    active_status = active.get("status", "")
    if (
        active_ps.get("type") == subject_type
        and active_ps.get("id") == subject_id
        and active_status in ("running", "blocked")
    ):
        phase_ok, allowed_phases = _validate_action_phase(action, active)
        if not phase_ok:
            current = active["current_phase"]
            return _make_preflight_decision(
                False, "blocked", "wrong_phase",
                next_action={
                    "command": "python3 .ai/workflows/scripts/workflow.py --root . advance",
                    "description": (
                        f"Run is in phase '{current}', but action '{action}'"
                        f" requires one of: {sorted(allowed_phases)}."
                        f" Advance the run to the correct phase first."
                    ),
                },
            )
        return _make_preflight_decision(True, "ok", "active_run_exists")

    return _make_preflight_decision(
        False, "blocked", "conflict_active_run",
        next_action={
            "command": "python3 .ai/workflows/scripts/workflow.py --root . status",
            "description": (
                f"Active run for '{active_ps.get('id')}' exists."
                f" Complete or cancel it before repairing '{subject_id}'."
            ),
        },
    )


# --- Roadmap Actions ---

@register_policy("roadmap_capture", allowed_phases={"create_roadmap"})
@register_policy("roadmap_insert", allowed_phases={"create_roadmap"})
@register_policy("roadmap_review", allowed_phases={"review_roadmap"})
@register_policy("roadmap_revise")
@register_policy("roadmap_cancel")
@register_policy("roadmap_reorder")
@register_policy("roadmap_replan")
@register_policy("roadmap_done")
def _policy_roadmap(root, action, subject_type, subject_id):
    """Require matching active run or done history for stateful roadmap mutations."""
    if not subject_type or not subject_id:
        return _make_preflight_decision(False, "error", "missing_subject")
    active, done_subjects = _evaluate_subject_run_context(root, subject_type, subject_id)

    if (subject_type, subject_id) in done_subjects:
        return _make_preflight_decision(True, "ok", "done_history_exists")

    if not active:
        return _make_preflight_decision(
            False, "blocked", "missing_active_run",
            next_action=_start_command(subject_type, subject_id),
        )

    active_ps = active.get("primary_subject", {})
    active_status = active.get("status", "")
    if (
        active_ps.get("type") == subject_type
        and active_ps.get("id") == subject_id
        and active_status in ("running", "blocked")
    ):
        phase_ok, allowed_phases = _validate_action_phase(action, active)
        if not phase_ok:
            current = active["current_phase"]
            return _make_preflight_decision(
                False, "blocked", "wrong_phase",
                next_action={
                    "command": "python3 .ai/workflows/scripts/workflow.py --root . advance",
                    "description": (
                        f"Run is in phase '{current}', but action '{action}'"
                        f" requires one of: {sorted(allowed_phases)}."
                        f" Advance the run to the correct phase first."
                    ),
                },
            )
        return _make_preflight_decision(True, "ok", "active_run_exists")

    return _make_preflight_decision(
        False, "blocked", "conflict_active_run",
        next_action={
            "command": "python3 .ai/workflows/scripts/workflow.py --root . status",
            "description": (
                f"Active run for '{active_ps.get('id')}' exists."
                f" Complete or cancel it before starting '{subject_id}'."
            ),
        },
    )


# --- Preflight Commands ---

def cmd_preflight(root, args):
    """Read-only blocking gate: check if a governed action can proceed.
    Dispatches to the policy registry -- NEVER contains action-specific if/else."""
    action = getattr(args, "action", "")
    subject_type = args.subject_type
    subject_id = args.subject_id

    policy = POLICY_REGISTRY.get(action)
    if not policy:
        decision = _make_preflight_decision(False, "error", "unknown_action")
        print(json.dumps(decision, indent=2))
        sys.exit(1)

    decision = policy(root, action, subject_type, subject_id)
    print(json.dumps(decision, indent=2))
    if not decision["allowed"]:
        sys.exit(1)


def _create_workflow_run(root, subject_type, subject_id, pending_hooks):
    """Create a workflow run and return a preflight decision.
    Uses existing _infer_phase and _run_loaders for consistent behavior."""
    workflow_id = "sdlc-main"
    run_id = _make_run_id(subject_type, subject_id)
    phase = _infer_phase(root, subject_type, subject_id)

    state = {
        "version": 1,
        "run_id": run_id,
        "workflow": workflow_id,
        "flow_type": "spec-flow",
        "status": "running",
        "current_phase": phase,
        "primary_subject": {"type": subject_type, "id": subject_id},
        "context": {"change_id": subject_id} if subject_type == "spec_change" else {},
        "phase_readiness": {"phase": phase, "ready": False, "missing_required_inputs": []},
        "pending_hooks": list(pending_hooks),
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

    save_run_state(root, state)
    decision = _make_preflight_decision(
        True, "run_created", "active_run_created_for_governed_action",
        next_action={
            "command": (
                f"python3 .ai/workflows/scripts/workflow.py --root . resolve"
            ),
            "description": (
                f"Run created at phase '{phase}' for '{subject_id}'."
                f" Resolve to load context, complete hooks,"
                f" complete-phase --exit-criteria-satisfied pending_hooks_empty,"
                f" then advance to done."
            ),
        },
    )
    decision["run_id"] = run_id
    decision["current_phase"] = state["current_phase"]
    decision["pending_hooks"] = list(pending_hooks)
    return decision


def cmd_ensure_run(root, args):
    """Writable blocking gate: ensure a governed action has a run.
    Delegates to policy metadata via POLICY_META -- NEVER
    contains action-specific if/else."""
    action = getattr(args, "action", "")
    subject_type = args.subject_type
    subject_id = args.subject_id

    policy = POLICY_REGISTRY.get(action)
    if not policy:
        decision = _make_preflight_decision(False, "error", "unknown_action")
        print(json.dumps(decision, indent=2))
        sys.exit(1)

    meta = POLICY_META.get(action, {})

    # Non-governed actions (creates_run=False) pass through
    if not meta.get("creates_run"):
        decision = policy(root, action, subject_type, subject_id)
        print(json.dumps(decision, indent=2))
        if not decision["allowed"]:
            sys.exit(1)
        return

    # Governed actions with creates_run=True
    active, done_subjects = _evaluate_subject_run_context(
        root, subject_type, subject_id
    )

    if (subject_type, subject_id) in done_subjects:
        decision = _make_preflight_decision(True, "ok", "done_history_exists")
        print(json.dumps(decision, indent=2))
        return

    if not active:
        # Policy must have creates_run=True to reach here
        if not subject_type or not subject_id:
            decision = _make_preflight_decision(
                False, "blocked", "missing_active_run",
                next_action=_start_command(subject_type, subject_id),
            )
            print(json.dumps(decision, indent=2))
            sys.exit(1)

        if subject_type == "spec_change":
            linked = _find_linked_roadmap_run(root, subject_id)
            if linked:
                linked_ps = linked.get("primary_subject", {})
                decision = _make_preflight_decision(
                    False, "blocked", "linked_roadmap_run_exists",
                    next_action={
                        "command": (
                            f"python3 .ai/workflows/scripts/workflow.py --root . resume"
                            f" --subject-type {linked_ps.get('type', 'roadmap_item')}"
                            f" --subject-id {linked_ps.get('id', subject_id)}"
                        ),
                        "description": (
                            f"A linked roadmap_item run already exists for '{subject_id}'."
                            f" Resume or complete the canonical roadmap run before creating"
                            f" a repair run."
                        ),
                    },
                )
                print(json.dumps(decision, indent=2))
                sys.exit(1)

        # For spec_change subjects, verify subject is archived before creating a repair run
        if subject_type == "spec_change":
            status = loader_openspec_change_status(root, subject_id)
            if status.get("classification") != "archived":
                decision = _make_preflight_decision(
                    False, "error", "subject_not_archived",
                    next_action=_start_command(subject_type, subject_id),
                )
                print(json.dumps(decision, indent=2))
                sys.exit(1)

        hooks = meta.get("repair_hooks", [])
        decision = _create_workflow_run(root, subject_type, subject_id, hooks)
        print(json.dumps(decision, indent=2))
        return

    # Active run exists - check for match
    active_ps = active.get("primary_subject", {})
    active_status = active.get("status", "")
    if (
        active_ps.get("type") == subject_type
        and active_ps.get("id") == subject_id
        and active_status in ("running", "blocked")
    ):
        phase_ok, allowed_phases = _validate_action_phase(action, active)
        if not phase_ok:
            current = active["current_phase"]
            decision = _make_preflight_decision(
                False, "blocked", "wrong_phase",
                next_action={
                    "command": "python3 .ai/workflows/scripts/workflow.py --root . advance",
                    "description": (
                        f"Run is in phase '{current}', but action '{action}'"
                        f" requires one of: {sorted(allowed_phases or [])}."
                        f" Advance the run to the correct phase first."
                    ),
                },
            )
            print(json.dumps(decision, indent=2))
            sys.exit(1)
        decision = _make_preflight_decision(True, "ok", "active_run_exists")
        print(json.dumps(decision, indent=2))
        return

    # Conflict
    decision = _make_preflight_decision(
        False, "blocked", "conflict_active_run",
        next_action={
            "command": "python3 .ai/workflows/scripts/workflow.py --root . status",
            "description": (
                f"Active run for '{active_ps.get('id')}' exists."
                f" Complete or cancel it first."
            ),
        },
    )
    print(json.dumps(decision, indent=2))
    sys.exit(1)