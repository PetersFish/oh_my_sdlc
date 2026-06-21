#!/usr/bin/env python3
"""SDLC workflow runtime -- deterministic, non-interactive state machine.

Commands: status, start, resume, readiness, resolve, record-evidence,
complete-phase, complete-hook, advance, block, done, validate,
governance-check, preflight, ensure-run.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_STATUSES = {"running", "blocked", "done", "cancelled"}

VALID_BLOCK_TYPES = {
    "missing_required_inputs",
    "user_decision_required",
    "worker_failed",
    "exit_criteria_failed",
    "eval_failed",
    "hook_blocked",
    "domain_state_mismatch",
}

VALID_GATE_STATUSES = {"required", "passed", "not_required", "user_exception", "failed"}

VALID_MEMORY_SYNC_RESOLUTIONS = {"synced", "not_needed", "user_deferred"}


def _make_run_id(subject_type, subject_id):
    today = datetime.date.today().isoformat()
    return f"{today}-{subject_id}"


def _ts():
    return datetime.datetime.now().isoformat()


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def _resolve_path(root, rel):
    return os.path.normpath(os.path.join(root, rel)) if root else rel


def _finding_hash(finding_type, **fields):
    canonical = finding_type + "|" + "|".join(
        f"{k}={v}" for k, v in sorted(fields.items()) if v is not None
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Run state I/O
# ---------------------------------------------------------------------------

RUN_STATE_KEYS = {
    "version", "run_id", "workflow", "status", "current_phase",
    "primary_subject", "context", "phase_readiness", "pending_hooks",
    "completed_hooks", "completed_phases", "gates", "evidence", "block",
    "updated_at",
}


def load_run_state(root):
    path = _resolve_path(root, ".ai/workflows/runs/current.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def _json_default(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def save_run_state(root, state):
    path = _resolve_path(root, ".ai/workflows/runs/current.json")
    _ensure_dir(os.path.dirname(path))
    state["updated_at"] = _ts()
    with open(path, "w") as f:
        json.dump(state, f, indent=2, default=_json_default)


def validate_run_state(state):
    errors = []
    for key in RUN_STATE_KEYS:
        if key not in state:
            errors.append(f"missing required field: {key}")
    if state.get("status") not in VALID_STATUSES:
        errors.append(f"invalid status: {state.get('status')}")
    if state.get("block") and isinstance(state["block"], dict):
        bt = state["block"].get("type", "")
        if bt not in VALID_BLOCK_TYPES:
            errors.append(f"invalid block type: {bt}")
    for rid, gate in state.get("gates", {}).items():
        if gate.get("status", "") not in VALID_GATE_STATUSES:
            errors.append(f"gate {rid}: invalid status: {gate.get('status')}")
    return errors


# ---------------------------------------------------------------------------
# Workflow definition
# ---------------------------------------------------------------------------

SUPPORTED_PHASE_FIELDS = {
    "required_inputs", "context_loaders", "allowed_workers",
    "exit_criteria", "post_hooks", "branches", "next", "terminal",
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
# Deterministic loaders
# ---------------------------------------------------------------------------

def _list_dirs(path):
    try:
        return sorted(os.listdir(path))
    except FileNotFoundError:
        return []


def _find_roadmap_items(root, openspec_change_id):
    """Scan .ai/roadmap/areas/*/items/*.md for openspec_change match."""
    items = []
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    if not os.path.isdir(areas_dir):
        return items
    for area in _list_dirs(areas_dir):
        items_dir = os.path.join(areas_dir, area, "items")
        if not os.path.isdir(items_dir):
            continue
        for fname in _list_dirs(items_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(items_dir, fname)
            try:
                with open(fpath, "r") as f:
                    content = f.read()
            except Exception:
                continue
            fm = _parse_yaml_frontmatter(content)
            if fm and fm.get("openspec_change") == openspec_change_id:
                item_id = (
                    fm.get("id")
                    or fm.get("item_id")
                    or fname.replace(".md", "")
                )
                status = fm.get("status", "")
                completed_at = fm.get("completed_at")
                items.append({
                    "item_id": item_id,
                    "status": status,
                    "completed_at": completed_at,
                    "file": fpath,
                    "area": area,
                })
    return items


def _parse_yaml_frontmatter(content):
    """Parse YAML frontmatter between --- markers."""
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    try:
        raw = yaml.safe_load(content[3:end])
        if isinstance(raw, dict):
            return _sanitize_for_json(raw)
        return raw
    except Exception:
        return None


def _sanitize_for_json(obj):
    """Recursively convert YAML-parsed objects to JSON-serializable types."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if hasattr(obj, "__str__"):
        return str(obj)
    return obj


def _read_frontmatter_field(path, field):
    try:
        with open(path, "r") as f:
            content = f.read()
        fm = _parse_yaml_frontmatter(content)
        return fm.get(field) if fm else None
    except Exception:
        return None


def loader_openspec_change_status(root, change_id):
    """Classify an OpenSpec change as active, archived, missing, in-progress, complete, or unknown."""
    active_dir = _resolve_path(root, f"openspec/changes/{change_id}")
    archives = _resolve_path(root, "openspec/changes/archive")
    if os.path.isdir(active_dir):
        tasks_path = os.path.join(active_dir, "tasks.md")
        if os.path.exists(tasks_path):
            with open(tasks_path, "r") as f:
                content = f.read()
            incomplete = any(
                line.strip().startswith("- [ ]") for line in content.split("\n")
            )
            all_tasks = any(
                line.strip().startswith("- [") for line in content.split("\n")
            )
            if all_tasks and not incomplete:
                return {"classification": "complete", "source": "active"}
            return {"classification": "in-progress", "source": "active"}
        return {"classification": "active", "source": "active"}

    if os.path.isdir(archives):
        for entry in _list_dirs(archives):
            e_path = os.path.join(archives, entry)
            if not os.path.isdir(e_path):
                continue
            parts = entry.split("-")
            if len(parts) >= 4 and "-".join(parts[3:]) == change_id:
                return {
                    "classification": "archived",
                    "source": e_path,
                }
    return {"classification": "missing", "source": None}


def loader_openspec_archive_path(root, change_id):
    """Find archive path for a change id."""
    archives = _resolve_path(root, "openspec/changes/archive")
    matches = []
    if os.path.isdir(archives):
        for entry in _list_dirs(archives):
            parts = entry.split("-")
            if len(parts) >= 4 and "-".join(parts[3:]) == change_id:
                matches.append(os.path.join(archives, entry))
    if len(matches) == 1:
        rel = os.path.relpath(matches[0], root) if root else matches[0]
        return rel
    return None


def loader_roadmap_linked_item(root, change_id):
    """Scan roadmap items for openspec_change match."""
    items = _find_roadmap_items(root, change_id)
    if len(items) == 0:
        return {"count": 0, "items": []}
    return {"count": len(items), "items": items}


def loader_roadmap_item_status(root, item_id):
    """Read the status of a specific roadmap item."""
    if not item_id:
        return None
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    for area in _list_dirs(areas_dir):
        items_dir = os.path.join(areas_dir, area, "items")
        fname_md = f"{item_id}.md"
        fpath = os.path.join(items_dir, fname_md)
        if os.path.exists(fpath):
            return {
                "item_id": item_id,
                "status": _read_frontmatter_field(fpath, "status"),
                "completed_at": _read_frontmatter_field(fpath, "completed_at"),
            }
    return None


# ---------------------------------------------------------------------------
# Preflight: blocking gate policy registry (open for extension, closed for modification)
# ---------------------------------------------------------------------------

def _load_done_history_run_ids(root):
    """Return set of (subject_type, subject_id) from done history runs."""
    governed = set()
    history_dir = _resolve_path(root, ".ai/workflows/runs/history")
    if not os.path.isdir(history_dir):
        return governed
    for fname in _list_dirs(history_dir):
        if not fname.endswith(".json"):
            continue
        hpath = os.path.join(history_dir, fname)
        try:
            with open(hpath, "r") as f:
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
    """Return (active_state, done_subjects_set) for subject validation."""
    active = load_run_state(root)
    done_subjects = _load_done_history_run_ids(root)
    return active, done_subjects


# Policy registry: add new governed actions by registering a policy function.
# A policy receives (root, action, subject_type, subject_id) and returns a dict
# with keys: allowed, status, reason, next_action.
# Policy metadata is stored per-action in POLICY_META (not on the function)
# to avoid stacked-decorator overwrite bugs.
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

@register_policy("superpowers_direct")
def _policy_no_workflow(root, action, subject_type, subject_id):
    return _make_preflight_decision(True, "not_required")


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
        "status": "running",
        "current_phase": phase,
        "primary_subject": {"type": subject_type, "id": subject_id},
        "context": {"change_id": subject_id} if subject_type == "openspec_change" else {},
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

    # Non-governed actions (e.g., superpowers_direct) pass through
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

        # Verify subject is archived before creating a repair run
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


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_status(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"status": "no_active_run"}, indent=2))
        return
    print(json.dumps(state, indent=2))


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


def cmd_start(root, args):
    existing = load_run_state(root)
    workflow_id = args.workflow or "sdlc-main"
    subject_type = args.subject_type or "openspec_change"
    subject_id = args.subject_id
    run_id = _make_run_id(subject_type, subject_id)

    if existing and existing.get("status") in ("running", "blocked"):
        existing_subject = existing.get("primary_subject", {})
        if (
            existing_subject.get("type") == subject_type
            and existing_subject.get("id") == subject_id
        ):
            print(
                json.dumps(
                    {
                        "action": "resume",
                        "run_id": existing["run_id"],
                        "current_phase": existing["current_phase"],
                        "message": "matching active run exists, use resume",
                    },
                    indent=2,
                )
            )
            return
        else:
            print(
                json.dumps(
                    {
                        "action": "conflict",
                        "message": "different active run exists",
                        "existing_run_id": existing["run_id"],
                        "existing_subject": existing_subject,
                    },
                    indent=2,
                )
            )
            sys.exit(1)

    phase = _infer_phase(root, subject_type, subject_id)

    state = {
        "version": 1,
        "run_id": run_id,
        "workflow": workflow_id,
        "status": "running",
        "current_phase": phase,
        "primary_subject": {"type": subject_type, "id": subject_id},
        "context": {"change_id": subject_id} if subject_type == "openspec_change" else {},
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

    save_run_state(root, state)
    state["updated_at"] = _ts()
    print(json.dumps(state, indent=2))


def cmd_resume(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run to resume"}, indent=2))
        sys.exit(1)

    subject_type = args.subject_type
    subject_id = args.subject_id

    existing_subject = state.get("primary_subject", {})
    if subject_type and subject_id:
        if (
            existing_subject.get("type") != subject_type
            or existing_subject.get("id") != subject_id
        ):
            print(
                json.dumps(
                    {
                        "action": "conflict",
                        "message": "active run has different subject",
                        "run_id": state["run_id"],
                        "existing_subject": existing_subject,
                        "requested_subject": {"type": subject_type, "id": subject_id},
                    },
                    indent=2,
                )
            )
            sys.exit(1)

    status = state.get("status")
    if status == "done":
        print(json.dumps({"action": "none", "message": "run is already done"}, indent=2))
        return
    if status == "cancelled":
        print(json.dumps({"action": "cancelled", "message": "run is cancelled, start new"}, indent=2))
        return

    wf = load_workflow(root, state.get("workflow", "sdlc-main"))
    if wf:
        phase = _infer_phase(root, existing_subject.get("type"), existing_subject.get("id"))
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
    save_run_state(root, state)
    print(json.dumps(state, indent=2))


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

    completed = state.setdefault("completed_phases", [])
    if current not in completed:
        completed.append(current)

    for hook in phase_def.get("post_hooks", []):
        pending = state.setdefault("pending_hooks", [])
        if hook not in pending:
            pending.append(hook)

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


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

    elif hook_name == "roadmap_done_if_relevant":
        raw = state.get("evidence", {}).get("roadmap_link")
        if not raw:
            state.setdefault("evidence", {})["roadmap_hook_resolution"] = "no_linked_item"
        elif isinstance(raw, dict):
            items = raw.get("items", [])
            if raw.get("count", 0) == 0 or not items:
                state.setdefault("evidence", {})["roadmap_hook_resolution"] = "no_linked_item"
            elif len(items) == 1:
                item = items[0]
                status = item.get("status", "")
                if status == "done" and item.get("completed_at"):
                    state.setdefault("evidence", {})["roadmap_hook_resolution"] = "idempotent_done"
                elif status == "active":
                    latest_status = loader_roadmap_item_status(root, item.get("item_id"))
                    if latest_status and latest_status.get("status") == "done" and latest_status.get("completed_at"):
                        state.setdefault("evidence", {})["roadmap_hook_resolution"] = "done"
                    else:
                        state["status"] = "blocked"
                        state["block"] = {
                            "type": "hook_blocked",
                            "message": f"roadmap item {item.get('item_id')} still active",
                            "next_allowed": ["resolve", "record-evidence", "block"],
                        }
                        save_run_state(root, state)
                        print(json.dumps(state, indent=2))
                        sys.exit(1)
                elif status in ("idea", "ready", "cancelled"):
                    state["status"] = "blocked"
                    state["block"] = {
                        "type": "domain_state_mismatch",
                        "message": f"roadmap item {item.get('item_id')} has status {status}",
                        "next_allowed": ["resolve", "block"],
                    }
                    save_run_state(root, state)
                    print(json.dumps(state, indent=2))
                    sys.exit(1)
            else:
                state["status"] = "blocked"
                state["block"] = {
                    "type": "user_decision_required",
                    "message": "multiple roadmap items linked to this change",
                    "candidates": items,
                    "next_allowed": [
                        "choose one item to mark done",
                        "repair roadmap links manually",
                        "mark all active matches done with reason",
                        "skip roadmap done with reason",
                    ],
                }
                save_run_state(root, state)
                print(json.dumps(state, indent=2))
                sys.exit(1)

    pending.remove(hook_name)
    completed = state.setdefault("completed_hooks", [])
    if hook_name not in completed:
        completed.append(hook_name)

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


def cmd_advance(root, args):
    state = load_run_state(root)
    if not state:
        print(json.dumps({"error": "no active run"}, indent=2))
        sys.exit(1)

    if state.get("status") == "blocked":
        print(json.dumps({"error": "run is blocked, cannot advance"}, indent=2))
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

        state["status"] = "done"
        history_dir = _resolve_path(root, ".ai/workflows/runs/history/")
        _ensure_dir(history_dir)
        history_path = os.path.join(history_dir, f"{state['run_id']}.json")
        with open(history_path, "w") as f:
            json.dump(state, f, indent=2)

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
        state["status"] = "blocked"
        state["block"] = {
            "type": "exit_criteria_failed",
            "message": "current phase is not done",
            "next_allowed": ["advance", "resolve", "block"],
        }
        save_run_state(root, state)
        print(json.dumps(state, indent=2))
        sys.exit(1)

    if state.get("status") == "blocked":
        print(json.dumps({"error": "run is blocked, cannot complete"}, indent=2))
        sys.exit(1)

    state["status"] = "done"
    state["updated_at"] = _ts()

    history_dir = _resolve_path(root, ".ai/workflows/runs/history/")
    _ensure_dir(history_dir)
    history_path = os.path.join(history_dir, f"{state['run_id']}.json")
    with open(history_path, "w") as f:
        json.dump(state, f, indent=2)

    save_run_state(root, state)
    print(json.dumps(state, indent=2))


def cmd_governance_check(root, args):
    """Read-only governance diagnostics: dangling archives and pending hooks."""
    findings = []
    archive_dir = _resolve_path(root, "openspec/changes/archive")
    active_state = load_run_state(root)
    history_dir = _resolve_path(root, ".ai/workflows/runs/history")

    governed_change_ids = set()

    if active_state:
        ps = active_state.get("primary_subject", {})
        if ps.get("type") == "openspec_change" and ps.get("id"):
            governed_change_ids.add(ps["id"])

    if os.path.isdir(history_dir):
        for fname in _list_dirs(history_dir):
            if not fname.endswith(".json"):
                continue
            hpath = os.path.join(history_dir, fname)
            try:
                with open(hpath, "r") as f:
                    hist = json.load(f)
            except Exception:
                continue
            if hist.get("status") in ("done",):
                ps = hist.get("primary_subject", {})
                if ps.get("type") == "openspec_change" and ps.get("id"):
                    governed_change_ids.add(ps["id"])

    if os.path.isdir(archive_dir):
        for entry in _list_dirs(archive_dir):
            e_path = os.path.join(archive_dir, entry)
            if not os.path.isdir(e_path):
                continue
            parts = entry.split("-")
            if len(parts) < 4:
                continue
            change_id = "-".join(parts[3:])
            if change_id in governed_change_ids:
                continue
            rel_path = os.path.relpath(e_path, root)
            message = (
                f"Archived OpenSpec change \"{change_id}\" has no "
                f"matching workflow run."
            )
            ensure_cmd = (
                f"python3 .ai/workflows/scripts/workflow.py --root . ensure-run"
                f" --action dangling_archive_repair"
                f" --subject-type openspec_change"
                f" --subject-id {change_id}"
            )
            remediation = (
                f"Archived OpenSpec change \"{change_id}\" (archive path: {rel_path})"
                f" has no matching workflow run. Run: {ensure_cmd}"
                f" to create a post_archive_actions run. Then resolve,"
                f" complete hooks, complete-phase --exit-criteria-satisfied"
                f" pending_hooks_empty, advance to done, and re-run"
                f" \"workflow.py governance-check\" until block=false."
            )
            fh = _finding_hash(
                "dangling_archive", change_id=change_id, archive_path=rel_path
            )
            findings.append({
                "type": "dangling_archive",
                "change_id": change_id,
                "archive_path": rel_path,
                "message": message,
                "remediation": remediation,
                "hash": fh,
            })

    if active_state:
        pending = active_state.get("pending_hooks", [])
        if pending:
            run_id = active_state.get("run_id", "")
            ctx = active_state.get("context", {})
            change_id = ctx.get("change_id", "")
            hook_list = ", ".join(pending)
            message = (
                f"Active run \"{run_id}\" has {len(pending)} unresolved "
                f"hook(s): {pending}."
            )
            remediation = (
                f"Active run \"{run_id}\" has unresolved hooks: [{hook_list}]. "
                f"Invoke the responsible workers for each hook, then run "
                f"\"workflow.py complete-hook --hook <hook-name>\" for each. "
                f"Re-run \"workflow.py governance-check\" until block=false."
            )
            fh = _finding_hash(
                "pending_hooks",
                run_id=run_id,
                change_id=change_id or None,
                pending_hook_names=",".join(sorted(pending)),
            )
            findings.append({
                "type": "pending_hooks",
                "run_id": run_id,
                "change_id": change_id or None,
                "pending_hook_names": pending,
                "message": message,
                "remediation": remediation,
                "hash": fh,
            })

    block = len(findings) > 0
    output = {"block": block, "findings": findings}
    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _infer_phase(root, subject_type, subject_id):
    if subject_type != "openspec_change":
        return "input"
    status = loader_openspec_change_status(root, subject_id)
    classification = status.get("classification", "missing")
    if classification == "archived":
        return "post_archive_actions"
    if classification == "complete":
        return "archive_change"
    if classification in ("active", "in-progress"):
        return "apply_change"
    return "create_change"


def _run_loaders(root, state, wf):
    current = state["current_phase"]
    phase_def = get_phase(wf, current)
    if not phase_def:
        return
    for loader_name in phase_def.get("context_loaders", []):
        if loader_name == "openspec_change_status":
            change_id = state.get("context", {}).get("change_id", "")
            if change_id:
                result = loader_openspec_change_status(root, change_id)
                state.setdefault("evidence", {})["openspec_status"] = result
        elif loader_name == "openspec_archive_path":
            change_id = state.get("context", {}).get("change_id", "")
            if change_id:
                ap = loader_openspec_archive_path(root, change_id)
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
    return required.issubset(satisfied)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

COMMANDS = {
    "status",
    "start",
    "resume",
    "readiness",
    "resolve",
    "record-evidence",
    "complete-phase",
    "complete-hook",
    "advance",
    "block",
    "done",
    "validate",
    "governance-check",
    "preflight",
    "ensure-run",
}


def main():
    parser = argparse.ArgumentParser(description="SDLC workflow runtime")
    parser.add_argument("--root", default=None, help="workspace root path")
    parser.add_argument(
        "command",
        choices=sorted(COMMANDS),
        help="command to execute",
    )
    parser.add_argument("--workflow", default=None, help="workflow id")
    parser.add_argument("--subject-type", default=None, help="subject type")
    parser.add_argument("--subject-id", default=None, help="subject id")
    parser.add_argument("--key", default=None, help="evidence key")
    parser.add_argument("--value", default=None, help="evidence value (JSON)")
    parser.add_argument(
        "--exit-criteria-satisfied", default=None, help="comma-separated criteria"
    )
    parser.add_argument("--hook", default=None, help="hook name to complete")
    parser.add_argument("--resolution", default=None, help="resolution value for hook")
    parser.add_argument("--reason", default=None, help="reason for resolution")
    parser.add_argument("--residual-risk", default=None, help="residual risk for deferred")
    parser.add_argument("--branch", default=None, help="branch decision label")
    parser.add_argument("--block-type", default=None, help="block type")
    parser.add_argument("--message", default=None, help="block/status message")
    parser.add_argument("--next-allowed", default=None, help="comma-separated next allowed actions")
    parser.add_argument("--action", default=None, help="governed action for preflight/ensure-run")

    args = parser.parse_args()
    root = args.root or os.getcwd()

    if args.command == "status":
        cmd_status(root, args)
    elif args.command == "validate":
        cmd_validate(root, args)
    elif args.command == "start":
        cmd_start(root, args)
    elif args.command == "resume":
        cmd_resume(root, args)
    elif args.command == "readiness":
        cmd_readiness(root, args)
    elif args.command == "resolve":
        cmd_resolve(root, args)
    elif args.command == "record-evidence":
        cmd_record_evidence(root, args)
    elif args.command == "complete-phase":
        cmd_complete_phase(root, args)
    elif args.command == "complete-hook":
        cmd_complete_hook(root, args)
    elif args.command == "advance":
        cmd_advance(root, args)
    elif args.command == "block":
        cmd_block(root, args)
    elif args.command == "done":
        cmd_done(root, args)
    elif args.command == "governance-check":
        cmd_governance_check(root, args)
    elif args.command == "preflight":
        cmd_preflight(root, args)
    elif args.command == "ensure-run":
        cmd_ensure_run(root, args)


if __name__ == "__main__":
    main()
