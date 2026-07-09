#!/usr/bin/env python3
"""SDLC workflow runtime -- deterministic, non-interactive state machine.

Commands: status, start, resume, readiness, resolve, record-evidence,
complete-phase, complete-hook, advance, block, done, validate,
governance-check, preflight, ensure-run, before-dispatch, after-dispatch.
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
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
    "version", "run_id", "workflow", "flow_type", "status", "current_phase",
    "primary_subject", "context", "phase_readiness", "pending_hooks",
    "completed_hooks", "completed_phases", "gates", "evidence", "block",
    "updated_at",
}

VALID_FLOW_TYPES = {"spec-flow", "lightweight-flow"}
VALID_SUBJECT_TYPES = {"spec_change", "roadmap_item"}

VALID_EXECUTION_MODES = {"main_checkout", "worktree"}

WORKTREE_REQUIRED_FIELDS = ("control_root", "worktree_path", "feature_branch")


def _resolve_execution_mode(context):
    """Return the effective execution_mode for a run context.

    Missing execution_mode is interpreted as ``main_checkout`` for legacy
    compatibility (Spec Decision 1 / Decision 10).
    """
    mode = (context or {}).get("execution_mode")
    if not mode:
        return "main_checkout"
    return mode


def _build_runtime_context(context):
    """Build the canonical runtime_context dict derived from state.context.

    Includes execution_mode for both main_checkout and worktree runs, worktree
    fields only when available/relevant, and change_id.  Agents should not
    infer source-of-truth paths from prose when runtime_context is available
    (Spec Decision 4).
    """
    context = context or {}
    rt = {
        "execution_mode": _resolve_execution_mode(context),
        "change_id": context.get("change_id", ""),
    }
    for field in (
        "control_root", "worktree_path", "base_branch",
        "feature_branch", "parent_ref",
    ):
        value = context.get(field)
        if value:
            rt[field] = value
    return rt


def _read_pointer(root):
    pointer_path = _resolve_path(root, ".ai/workflows/runs/current.json")
    if not os.path.exists(pointer_path):
        return None
    with open(pointer_path, "r") as f:
        return json.load(f)


def _set_pointer(root, run_id):
    pointer_path = _resolve_path(root, ".ai/workflows/runs/current.json")
    _ensure_dir(os.path.dirname(pointer_path))
    with open(pointer_path, "w") as f:
        json.dump({"run_id": run_id}, f)


def _clear_pointer(root):
    pointer_path = _resolve_path(root, ".ai/workflows/runs/current.json")
    _ensure_dir(os.path.dirname(pointer_path))
    with open(pointer_path, "w") as f:
        json.dump({}, f)


def _active_path(root, run_id):
    return _resolve_path(root, f".ai/workflows/runs/active/{run_id}/run.json")


def load_run_state(root, run_id=None):
    if run_id is not None:
        path = _active_path(root, run_id)
        if not os.path.exists(path):
            return None
        _migrate_legacy_artifacts(root, run_id)
        with open(path, "r") as f:
            return json.load(f)
    pointer = _read_pointer(root)
    if not pointer or not pointer.get("run_id"):
        return None
    path = _active_path(root, pointer["run_id"])
    if not os.path.exists(path):
        return None
    _migrate_legacy_artifacts(root, pointer["run_id"])
    with open(path, "r") as f:
        return json.load(f)


def _list_active_runs(root):
    active_dir = _resolve_path(root, ".ai/workflows/runs/active")
    if not os.path.isdir(active_dir):
        return []
    results = []
    for entry in _list_dirs(active_dir):
        entry_path = os.path.join(active_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        run_json_path = os.path.join(entry_path, "run.json")
        if not os.path.isfile(run_json_path):
            continue
        try:
            with open(run_json_path, "r") as f:
                state = json.load(f)
            results.append((state.get("run_id", entry), state))
        except Exception:
            continue
    return results


def _find_active_run_by_subject(root, subject_type, subject_id):
    for run_id, state in _list_active_runs(root):
        ps = state.get("primary_subject", {})
        if ps.get("type") == subject_type and ps.get("id") == subject_id:
            if state.get("status") in ("running", "blocked"):
                return state
    return None


def _migrate_legacy_artifacts(root, run_id):
    """Migrate legacy run artifacts into the active run directory."""
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    runs_dir = _resolve_path(root, ".ai/workflows/runs")

    sentinel = os.path.join(active_dir, ".migrated")

    def move_children(src_dir, dst_dir):
        if not os.path.isdir(src_dir):
            return
        _ensure_dir(dst_dir)
        for item in os.listdir(src_dir):
            src = os.path.join(src_dir, item)
            dst = os.path.join(dst_dir, item)
            if not os.path.exists(dst):
                shutil.move(src, dst)
        try:
            os.rmdir(src_dir)
        except OSError:
            pass

    legacy_handoffs = os.path.join(runs_dir, "handoffs", run_id)
    legacy_logs = os.path.join(runs_dir, "logs", run_id)
    move_children(legacy_handoffs, os.path.join(active_dir, "handoffs"))
    move_children(legacy_logs, os.path.join(active_dir, "logs"))

    split_dir = os.path.join(runs_dir, run_id)
    for artifact_dir in ("plans", "handoffs", "logs"):
        move_children(
            os.path.join(split_dir, artifact_dir),
            os.path.join(active_dir, artifact_dir),
        )
    try:
        os.rmdir(split_dir)
    except OSError:
        pass

    with open(sentinel, "w") as f:
        f.write(_ts())


def _json_default(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def save_run_state(root, state):
    run_id = state["run_id"]
    path = _active_path(root, run_id)
    _ensure_dir(os.path.dirname(path))
    _migrate_legacy_artifacts(root, run_id)
    state["updated_at"] = _ts()
    with open(path, "w") as f:
        json.dump(state, f, indent=2, default=_json_default)
    _set_pointer(root, run_id)


def _finalize_run_to_history(root, state):
    """Mark an active run done, move it to history, and remove the active directory."""
    state = dict(state)
    state["status"] = "done"
    state["current_phase"] = "done"
    state["phase_readiness"] = {
        "phase": "done",
        "ready": True,
        "missing_required_inputs": [],
    }
    state["pending_hooks"] = []
    state["block"] = None
    state["updated_at"] = _ts()

    run_id = state["run_id"]
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    history_dir = _resolve_path(root, f".ai/workflows/runs/history/{run_id}")

    # Write updated state to run.json inside active directory
    _ensure_dir(active_dir)
    with open(os.path.join(active_dir, "run.json"), "w") as f:
        json.dump(state, f, indent=2)

    # Ensure history parent exists
    _ensure_dir(os.path.dirname(history_dir))

    # Move entire directory
    if os.path.exists(history_dir):
        shutil.rmtree(history_dir)
    shutil.move(active_dir, history_dir)

    pointer = _read_pointer(root)
    if pointer and pointer.get("run_id") == state["run_id"]:
        _clear_pointer(root)

    return state

    return state


def _missing_terminal_finish_agent_evidence(state):
    """Return a structured blocker dict if the required final lifecycle
    finish-agent evidence is missing before terminal movement (Spec Decision 9).

    For archive_change / post_archive_actions completion, the relevant
    finish-agent result must be recorded in ``evidence.agent_results`` before
    an active run can be moved to history.  Returns ``None`` when evidence is
    sufficient.

    The relevant slice is resolved using the same fallback order as
    after-dispatch minus the CLI/agent-result sources (which are not available
    at terminal time): dispatch intent slice_id
    (``evidence.agent_phase.slice_id``), then ``context.change_id``, then
    ``default``.  A successful finish-agent result recorded only under an
    unrelated slice does NOT satisfy validation (Spec Decision 9 requires the
    relevant slice's evidence).

    This validation is scoped to active terminal movement only; historical
    runs already in history are not re-validated.
    """
    completed = state.get("completed_phases", []) or []
    requires_finish = (
        "archive_change" in completed or "post_archive_actions" in completed
    )
    if not requires_finish:
        return None

    dispatch_intent_slice_id = (
        state.get("evidence", {}).get("agent_phase", {}).get("slice_id", "")
    ) or ""
    change_id = state.get("context", {}).get("change_id", "") or ""
    relevant_slice_id = (
        dispatch_intent_slice_id
        or change_id
        or "default"
    )

    agent_results = state.get("evidence", {}).get("agent_results", {}) or {}
    by_agent = agent_results.get(relevant_slice_id, {}) or {}
    finish_result = by_agent.get("finish-agent") or by_agent.get("finish_agent")
    if finish_result and finish_result.get("status") == "success":
        return None

    return {
        "error": (
            "terminal movement refused: required finish-agent evidence is missing "
            f"for slice '{relevant_slice_id}'. Record the finish-agent result via "
            "after-dispatch under the relevant slice before moving the active run "
            "to history."
        ),
        "reason": "missing_finish_agent_evidence",
        "agent": "finish-agent",
        "slice_id": relevant_slice_id,
    }


def validate_run_state(state):
    errors = []
    for key in RUN_STATE_KEYS:
        if key not in state:
            errors.append(f"missing required field: {key}")
    if state.get("status") not in VALID_STATUSES:
        errors.append(f"invalid status: {state.get('status')}")
    if state.get("flow_type") not in VALID_FLOW_TYPES:
        errors.append(f"invalid flow_type: {state.get('flow_type')}")
    ps = state.get("primary_subject", {})
    if ps.get("type") not in VALID_SUBJECT_TYPES:
        errors.append(f"invalid subject_type: {ps.get('type')}")
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
# Deterministic loaders
# ---------------------------------------------------------------------------

def _list_dirs(path):
    try:
        return sorted(os.listdir(path))
    except FileNotFoundError:
        return []


def _find_roadmap_items(root, change_id):
    """Scan .ai/roadmap/areas/*/items/*.md for spec_change or openspec_change match."""
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
            if fm and (fm.get("spec_change") == change_id or fm.get("openspec_change") == change_id):
                item_id = (
                    fm.get("id")
                    or fm.get("item_id")
                    or fname.replace(".md", "")
                )
                status = fm.get("status", "")
                completed_at = fm.get("completed_at")
                started_at = fm.get("started_at")
                items.append({
                    "item_id": item_id,
                    "status": status,
                    "completed_at": completed_at,
                    "started_at": started_at,
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
        # directory exists but no tasks.md: not yet ready for implementation
        return {"classification": "scaffold", "source": "active"}

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


def loader_spec_change_status(root, change_id):
    return loader_openspec_change_status(root, change_id)


def loader_spec_archive_path(root, change_id):
    return loader_openspec_archive_path(root, change_id)


def _read_roadmap_item_spec_change(root, item_id):
    """Read provider-agnostic spec_change from a roadmap item file.
    Tries spec_change first, then falls back to openspec_change for legacy compatibility."""
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
                spec = _read_frontmatter_field(fpath, "spec_change")
                if spec:
                    return spec
                return _read_frontmatter_field(fpath, "openspec_change")
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
        if not os.path.isdir(items_dir):
            continue
        for fname in _list_dirs(items_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(items_dir, fname)
            fm_id = _read_frontmatter_field(fpath, "id")
            if fm_id == item_id:
                return {
                    "item_id": item_id,
                    "status": _read_frontmatter_field(fpath, "status"),
                    "completed_at": _read_frontmatter_field(fpath, "completed_at"),
                    "started_at": _read_frontmatter_field(fpath, "started_at"),
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

@register_policy("superpowers_direct")
def _policy_no_workflow(root, action, subject_type, subject_id):
    return _make_preflight_decision(True, "not_required")


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


# ---------------------------------------------------------------------------
# Commands
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

    # Confirmation-gated lightweight-flow: LLM decides externally, runtime blocks until user confirms
    if args.flow_type == "lightweight-flow":
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": workflow_id,
            "flow_type": "lightweight-flow",
            "status": "blocked",
            "current_phase": phase,
            "primary_subject": {"type": subject_type, "id": subject_id},
            "context": {"change_id": subject_id} if subject_type == "spec_change" else {},
            "phase_readiness": {"phase": phase, "ready": False, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": {
                "type": "user_decision_required",
                "message": "Flow type: lightweight-flow. Confirm to continue.",
                "next_allowed": ["confirm_lightweight_flow"],
            },
            "updated_at": "",
        }
        wf = load_workflow(root, workflow_id)
        if wf:
            _run_loaders(root, state, wf)
        save_run_state(root, state)
        state["updated_at"] = _ts()
        print(json.dumps(state, indent=2))
        return

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
            "recommended_next_action": "resolve_blockers",
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

    # Evidence key validation
    evidence_keys = phase_def.get("evidence_keys", [])
    if evidence_keys:
        run_evidence = state.get("evidence", {})
        missing = []
        empty_vals = []
        invalid_positive = []
        for ek in evidence_keys:
            if ek not in run_evidence:
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

    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    if os.path.exists(active_dir):
        shutil.rmtree(active_dir)

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

        # Option B: refuse terminal movement when required final lifecycle
        # finish-agent evidence is missing (Spec Decision 9).
        finish_blocker = _missing_terminal_finish_agent_evidence(state)
        if finish_blocker:
            print(json.dumps(finish_blocker, indent=2))
            sys.exit(1)

        state["status"] = "done"
        run_id = state["run_id"]
        active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
        history_dir = _resolve_path(root, f".ai/workflows/runs/history/{run_id}")

        # Write final state to run.json
        _ensure_dir(active_dir)
        with open(os.path.join(active_dir, "run.json"), "w") as f:
            json.dump(state, f, indent=2)

        _ensure_dir(os.path.dirname(history_dir))
        if os.path.exists(history_dir):
            shutil.rmtree(history_dir)
        shutil.move(active_dir, history_dir)
        _clear_pointer(root)

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

    state["status"] = "done"
    state["updated_at"] = _ts()

    run_id = state["run_id"]
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    history_dir = _resolve_path(root, f".ai/workflows/runs/history/{run_id}")

    # Write final state to run.json
    _ensure_dir(active_dir)
    with open(os.path.join(active_dir, "run.json"), "w") as f:
        json.dump(state, f, indent=2)

    _ensure_dir(os.path.dirname(history_dir))
    if os.path.exists(history_dir):
        shutil.rmtree(history_dir)
    shutil.move(active_dir, history_dir)
    _clear_pointer(root)

    print(json.dumps(state, indent=2))


def cmd_governance_check(root, args):
    """Read-only governance diagnostics: dangling archives, pending hooks,
    duplicate promotion runs, and ungoverned roadmap items."""
    findings = []
    archive_dir = _resolve_path(root, "openspec/changes/archive")
    history_dir = _resolve_path(root, ".ai/workflows/runs/history")

    governed_change_ids = set()
    governed_roadmap_ids = set()

    active_runs = _list_active_runs(root)
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        if ps.get("type") == "spec_change" and ps.get("id"):
            governed_change_ids.add(ps["id"])
        if ps.get("type") == "roadmap_item" and ps.get("id"):
            governed_roadmap_ids.add(ps["id"])

    if os.path.isdir(history_dir):
        for entry in _list_dirs(history_dir):
            entry_path = os.path.join(history_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            # New-style: history/<run_id>/run.json
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
                if ps.get("type") == "spec_change" and ps.get("id"):
                    governed_change_ids.add(ps["id"])
                if ps.get("type") == "roadmap_item" and ps.get("id"):
                    governed_roadmap_ids.add(ps["id"])
                    change_id = (
                        hist.get("context", {}).get("change_id")
                        or hist.get("evidence", {}).get("change_id")
                        or _read_roadmap_item_spec_change(root, ps["id"])
                    )
                    if change_id:
                        governed_change_ids.add(change_id)

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
                f" --subject-type spec_change"
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

    # Detect duplicate promotion runs: roadmap_item + spec_change for same change
    roadmap_change_ids = {}
    openspec_run_ids = set()
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        ctx = active_state.get("context", {})
        ev = active_state.get("evidence", {})
        if ps.get("type") == "roadmap_item":
            cid = ctx.get("change_id") or ev.get("change_id")
            if not cid:
                item_id = ps.get("id")
                if item_id:
                    cid = _read_roadmap_item_spec_change(root, item_id)
            if cid:
                roadmap_change_ids[cid] = run_id
        elif ps.get("type") == "spec_change":
            openspec_run_ids.add(run_id)
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        if ps.get("type") != "spec_change":
            continue
        oc_change_id = ps.get("id")
        if oc_change_id and oc_change_id in roadmap_change_ids:
            canonical_run_id = roadmap_change_ids[oc_change_id]
            message = (
                f"Duplicate runs for change \"{oc_change_id}\":"
                f" spec_change run \"{run_id}\" and"
                f" roadmap_item run \"{canonical_run_id}\"."
                f" The roadmap_item run is canonical."
            )
            remediation = (
                f"Cancel the spec_change run \"{run_id}\" with:"
                f" python3 .ai/workflows/scripts/workflow.py --root . cancel-run"
                f" --subject-type spec_change --subject-id {oc_change_id}"
                f" --reason \"duplicate of canonical roadmap_item run {canonical_run_id}\"."
                f" Re-run \"workflow.py governance-check\" until block=false."
            )
            fh = _finding_hash(
                "duplicate_promotion_runs",
                change_id=oc_change_id,
                canonical_run_id=canonical_run_id,
                duplicate_run_id=run_id,
            )
            findings.append({
                "type": "duplicate_promotion_runs",
                "change_id": oc_change_id,
                "canonical_run_id": canonical_run_id,
                "duplicate_run_id": run_id,
                "message": message,
                "remediation": remediation,
                "hash": fh,
            })

    # Detect stale active roadmap_item runs whose item is already done/cancelled.
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        if ps.get("type") != "roadmap_item":
            continue
        if active_state.get("status") not in ("running", "blocked"):
            continue
        item_id = ps.get("id")
        if not item_id:
            continue
        item_status = loader_roadmap_item_status(root, item_id)
        if not item_status or item_status.get("status") not in ("done", "cancelled"):
            continue
        rel_path = active_state.get("evidence", {}).get("roadmap_item_path", item_id)
        message = (
            f'Active roadmap_item run "{run_id}" remains running after '
            f'roadmap item "{item_id}" became {item_status.get("status")}. '
            f"The active run is stale."
        )
        remediation = (
            f'Run: python3 .ai/workflows/scripts/workflow.py --root . cancel-run'
            f' --subject-type roadmap_item --subject-id {item_id}'
            f' --reason "stale active run for completed roadmap item".'
            f' Re-run "workflow.py governance-check" until block=false.'
        )
        fh = _finding_hash(
            "stale_active_roadmap_run",
            run_id=run_id,
            item_id=item_id,
            status=item_status.get("status"),
            file_path=rel_path,
        )
        findings.append({
            "type": "stale_active_roadmap_run",
            "run_id": run_id,
            "item_id": item_id,
            "status": item_status.get("status"),
            "file_path": rel_path,
            "message": message,
            "remediation": remediation,
            "hash": fh,
        })

    # Detect ungoverned active roadmap items without matching active run or done history
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    if os.path.isdir(areas_dir):
        for area in _list_dirs(areas_dir):
            items_dir = os.path.join(areas_dir, area, "items")
            if not os.path.isdir(items_dir):
                continue
            for fname in _list_dirs(items_dir):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(items_dir, fname)
                fm_id = _read_frontmatter_field(fpath, "id")
                fm_status = _read_frontmatter_field(fpath, "status")
                if not fm_id or not fm_status:
                    continue
                if fm_status in ("done", "cancelled", "idea"):
                    continue
                if fm_id in governed_roadmap_ids:
                    continue
                has_active = bool(_find_active_run_by_subject(root, "roadmap_item", fm_id))
                if has_active:
                    governed_roadmap_ids.add(fm_id)
                    continue
                rel_path = os.path.relpath(fpath, root)
                message = (
                    f"Roadmap item \"{fm_id}\" (status: {fm_status}) has no"
                    f" matching active run or done history."
                )
                start_cmd = (
                    f"python3 .ai/workflows/scripts/workflow.py --root . start"
                    f" --subject-type roadmap_item"
                    f" --subject-id {fm_id}"
                )
                remediation = (
                    f"Roadmap item \"{fm_id}\" ({rel_path}, status: {fm_status})"
                    f" is ungoverned. Run: {start_cmd}"
                    f" to create a run. Then complete-phase, advance, and re-run"
                    f" \"workflow.py governance-check\" until block=false."
                )
                fh = _finding_hash(
                    "ungoverned_roadmap_item",
                    item_id=fm_id,
                    status=fm_status,
                    file_path=rel_path,
                )
                findings.append({
                    "type": "ungoverned_roadmap_item",
                    "item_id": fm_id,
                    "status": fm_status,
                    "file_path": rel_path,
                    "message": message,
                    "remediation": remediation,
                    "hash": fh,
                })

    # Detect OpenSpec changes linked from roadmap items without
    # matching workflow evidence
    governed_roadmap_change_ids = set()
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        ctx = active_state.get("context", {})
        ev = active_state.get("evidence", {})
        if ps.get("type") == "roadmap_item":
            cid = ctx.get("change_id") or ev.get("change_id")
            if not cid:
                item_id = ps.get("id")
                if item_id:
                    cid = _read_roadmap_item_spec_change(root, item_id)
            if cid:
                governed_roadmap_change_ids.add(cid)
    if os.path.isdir(history_dir):
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
                ctx = hist.get("context", {})
                ev = hist.get("evidence", {})
                if ps.get("type") == "roadmap_item":
                    cid = ctx.get("change_id") or ev.get("change_id")
                    if not cid:
                        item_id = ps.get("id")
                        if item_id:
                            cid = _read_roadmap_item_spec_change(root, item_id)
                    if cid:
                        governed_roadmap_change_ids.add(cid)
    if os.path.isdir(areas_dir):
        for area in _list_dirs(areas_dir):
            items_dir = os.path.join(areas_dir, area, "items")
            if not os.path.isdir(items_dir):
                continue
            for fname in _list_dirs(items_dir):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(items_dir, fname)
                linked_change = _read_frontmatter_field(fpath, "spec_change") or _read_frontmatter_field(fpath, "openspec_change")
                if not linked_change or linked_change == "None":
                    continue
                fm_id = _read_frontmatter_field(fpath, "id")
                fm_status = _read_frontmatter_field(fpath, "status")
                if linked_change in governed_change_ids:
                    continue
                if linked_change in governed_roadmap_change_ids:
                    continue
                rel_path = os.path.relpath(fpath, root)
                message = (
                    f"Roadmap item \"{fm_id}\" (status: {fm_status}) links to"
                    f" OpenSpec change \"{linked_change}\" without matching"
                    f" workflow evidence."
                )
                # If there is an active roadmap_item run for this item, guide user to
                # write context.change_id and advance to create_change.
                linked_item_run = _find_active_run_by_subject(root, "roadmap_item", fm_id)
                if linked_item_run:
                    remediation = (
                        f"Roadmap item \"{fm_id}\" ({rel_path}) links to"
                        f" \"{linked_change}\" but its workflow run"
                        f" \"{linked_item_run.get('run_id', '?')}\" (phase: {linked_item_run.get('current_phase', '?')})"
                        f" has no context.change_id."
                        f" Run: python3 .ai/workflows/scripts/workflow.py --root . record-context"
                        f" --key change_id --value \"{linked_change}\""
                        f" --subject-type roadmap_item --subject-id {fm_id}"
                        f", then advance through create_change."
                        f" Re-run \"workflow.py governance-check\" until block=false."
                    )
                else:
                    remediation = (
                        f"Roadmap item \"{fm_id}\" ({rel_path}) links to"
                        f" \"{linked_change}\" without workflow evidence."
                        f" Start a run: python3 .ai/workflows/scripts/workflow.py --root . start"
                        f" --subject-type roadmap_item --subject-id {fm_id}"
                        f" and advance to create_change."
                        f" Re-run \"workflow.py governance-check\" until block=false."
                    )
                fh = _finding_hash(
                    "linked_item_no_workflow_evidence",
                    item_id=fm_id or "",
                    change_id=linked_change,
                )
                findings.append({
                    "type": "linked_item_no_workflow_evidence",
                    "item_id": fm_id,
                    "change_id": linked_change,
                    "file_path": rel_path,
                    "message": message,
                    "remediation": remediation,
                    "hash": fh,
                })

    for run_id, active_state in active_runs:
        pending = active_state.get("pending_hooks", [])
        if not pending:
            continue
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


def _strip_leading_date_slug(stem):
    parts = stem.split("-", 3)
    if len(parts) == 4 and all(part.isdigit() for part in parts[:3]):
        return parts[3]
    return stem


def _matching_superpowers_plans(root, subject_id):
    plans_dir = os.path.join(root, "docs", "superpowers", "plans")
    if not os.path.isdir(plans_dir):
        return []

    matches = []
    for filename in sorted(os.listdir(plans_dir)):
        if not filename.endswith(".md"):
            continue
        stem = os.path.splitext(filename)[0]
        normalized = _strip_leading_date_slug(stem)
        if normalized == subject_id or subject_id in normalized:
            matches.append(os.path.join(plans_dir, filename))
    return matches


def _infer_phase(root, subject_type, subject_id, flow_type="spec-flow"):
    if subject_type == "roadmap_item":
        item_status = loader_roadmap_item_status(root, subject_id)
        if item_status:
            status = item_status.get("status", "")
            if status == "idea":
                return "review_roadmap"
            if status == "ready":
                linked_change = _read_roadmap_item_spec_change(root, subject_id)
                if linked_change and linked_change != "None":
                    return "create_change"
                return "review_roadmap"
            if status == "active":
                return "apply_change"
            # done, cancelled, or unknown: start new lifecycle
        return "create_roadmap"
    if subject_type != "spec_change":
        return "input"
    if flow_type == "lightweight-flow":
        matches = _matching_superpowers_plans(root, subject_id)
        if len(matches) == 1:
            return "apply_change"
        return "create_change"
    status = loader_openspec_change_status(root, subject_id)
    classification = status.get("classification", "missing")
    if classification == "archived":
        return "post_archive_actions"
    if classification == "complete":
        return "archive_change"
    if classification in ("active", "in-progress"):
        return "apply_change"
    # scaffold, missing, unknown: artifact creation still pending
    return "create_change"


def _run_loaders(root, state, wf):
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
    return required.issubset(satisfied)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

FOUNDATIONS = {
    "workflow_py": ".ai/workflows/scripts/workflow.py",
    "workflow_yaml": ".ai/workflows/definitions/sdlc-main.yaml",
    "workflow_runs": ".ai/workflows/runs",
    "agents_md": "AGENTS.md",
    "openspec_config": "openspec/config.yaml",
    "memory_manifest": ".ai/memory/manifest.json",
}


def cmd_verify_foundations(root, args):
    report = {}
    for key, relpath in FOUNDATIONS.items():
        report[key] = os.path.exists(os.path.join(root, relpath))

    all_present = all(report.values())
    if args.json:
        print(json.dumps({"foundations": report, "all_present": all_present}, indent=2))
    else:
        for key, present in report.items():
            status = "PRESENT" if present else "MISSING"
            print(f"{status}: {key} ({FOUNDATIONS[key]})")
    if not all_present:
        sys.exit(1)


COMMANDS = {
    "status",
    "start",
    "resume",
    "readiness",
    "resolve",
    "record-evidence",
    "record-context",
    "complete-phase",
    "complete-hook",
    "advance",
    "block",
    "done",
    "cancel-run",
    "validate",
    "governance-check",
    "preflight",
    "ensure-run",
    "verify-foundations",
    "before-dispatch",
    "after-dispatch",
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
    parser.add_argument("--subject-type", default=None, choices=sorted(VALID_SUBJECT_TYPES), help="subject type")
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
    parser.add_argument("--flow-type", default=None, choices=sorted(VALID_FLOW_TYPES), help="flow type")
    parser.add_argument("--agent", default=None, help="agent name for dispatch hooks")
    parser.add_argument("--phase", default=None, help="phase for dispatch validation")
    parser.add_argument("--slice-id", default=None, help="implementation slice identifier")
    parser.add_argument("--block-type", default=None, help="block type")
    parser.add_argument("--message", default=None, help="block/status message")
    parser.add_argument("--next-allowed", default=None, help="comma-separated next allowed actions")
    parser.add_argument("--action", default=None, help="governed action for preflight/ensure-run")
    parser.add_argument("--json", action="store_true", help="output as JSON")

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
    elif args.command == "record-context":
        cmd_record_context(root, args)
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
    elif args.command == "cancel-run":
        cmd_cancel_run(root, args)
    elif args.command == "governance-check":
        cmd_governance_check(root, args)
    elif args.command == "preflight":
        cmd_preflight(root, args)
    elif args.command == "ensure-run":
        cmd_ensure_run(root, args)
    elif args.command == "verify-foundations":
        cmd_verify_foundations(root, args)
    elif args.command == "before-dispatch":
        cmd_before_dispatch(root, args)
    elif args.command == "after-dispatch":
        cmd_after_dispatch(root, args)


if __name__ == "__main__":
    main()
