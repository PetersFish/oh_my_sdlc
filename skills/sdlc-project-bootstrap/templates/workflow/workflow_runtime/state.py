"""state.py — run-state I/O.

Run pointer discovery, active/history run loading, validation, persistence,
and context/state derivation. This is the only module that directly writes
workflow run-state files under ``.ai/workflows/runs/``.
"""

import datetime
import json
import os
import shutil

from workflow_runtime.core import (
    VALID_STATUSES,
    VALID_BLOCK_TYPES,
    VALID_GATE_STATUSES,
    VALID_FLOW_TYPES,
    VALID_SUBJECT_TYPES,
    VALID_EXECUTION_MODES,
    WORKTREE_REQUIRED_FIELDS,
    _ts,
    _ensure_dir,
    _resolve_path,
    _resolve_execution_mode,
    _build_runtime_context,
    _branch_finish_decision_required,
    _resolve_branch_finish_decision,
    _is_branch_decision_block,
    _should_reconcile_branch_decision_block,
)

# ---------------------------------------------------------------------------
# Run state schema
# ---------------------------------------------------------------------------

RUN_STATE_KEYS = {
    "version", "run_id", "workflow", "flow_type", "status", "current_phase",
    "primary_subject", "context", "phase_readiness", "pending_hooks",
    "completed_hooks", "completed_phases", "gates", "evidence", "block",
    "updated_at",
}


# ---------------------------------------------------------------------------
# Pointer I/O
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Run state loading
# ---------------------------------------------------------------------------

def _list_dirs(path):
    try:
        return sorted(os.listdir(path))
    except FileNotFoundError:
        return []


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


# ---------------------------------------------------------------------------
# Run state persistence
# ---------------------------------------------------------------------------

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
    return _move_run_to_history(root, state)


def _move_run_to_history(root, state):
    """Write the final state to the active run.json, then move the entire
    active run directory to history and clear the pointer if it points at
    this run.

    This is the single low-level state I/O for active-to-history transitions.
    Higher-level lifecycle handlers (cmd_done, cmd_advance terminal path)
    MUST call this instead of directly writing/moving run paths.
    """
    state = dict(state)
    run_id = state["run_id"]
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    history_dir = _resolve_path(root, f".ai/workflows/runs/history/{run_id}")

    # Write final state to run.json inside active directory
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
    if pointer and pointer.get("run_id") == run_id:
        _clear_pointer(root)

    return state


def _cancel_active_run(root, run_id):
    """Remove an active run directory without writing history.

    Used by cmd_cancel_run for replanned roadmap items. This is the single
    low-level state I/O for active-run cancellation. Higher-level lifecycle
    handlers MUST call this instead of directly calling shutil.rmtree.
    """
    active_dir = _resolve_path(root, f".ai/workflows/runs/active/{run_id}")
    if os.path.exists(active_dir):
        shutil.rmtree(active_dir)


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
# Lightweight-flow archive helpers
# ---------------------------------------------------------------------------

def _archive_lightweight_superpowers_artifacts(root, state, agent_evidence):
    """Move Superpowers plan/spec design artifacts into typed archive dirs.

    Called during after-dispatch for finish-agent archive_change success on
    lightweight-flow runs.  Uses the source/destination paths reported by
    finish-agent in ``archived_design_artifact_paths`` and
    ``source_design_artifact_paths``.  Falls back to deriving destinations
    from ``context.primary_design_path`` and ``context.design_artifact_paths``
    when finish-agent did not report explicit paths.

    Collision handling: if a destination file already exists, it is preserved
    (not overwritten) and a deterministic suffix is used for the new file.

    Returns a dict with keys ``moved`` (list of (src, dst) tuples),
    ``skipped`` (list of src paths that were missing on disk and whose
    archive destination was also absent), and ``already_archived`` (list of
    (src, dst) tuples where the source was absent but the destination
    already existed, indicating a prior archive move succeeded).
    """
    moved = []
    skipped = []
    already_archived = []
    if not isinstance(agent_evidence, dict):
        return {"moved": moved, "skipped": skipped, "already_archived": already_archived}

    context = state.get("context", {}) or {}
    archived_paths = list(agent_evidence.get("archived_design_artifact_paths") or [])
    source_paths = list(agent_evidence.get("source_design_artifact_paths") or [])

    # When finish-agent did not report explicit paths, derive them from the
    # runtime design artifact contract (primary_design_path + design_artifact_paths).
    if not archived_paths and not source_paths:
        primary = context.get("primary_design_path") or ""
        design_artifacts = context.get("design_artifact_paths") or []
        if primary:
            source_paths.append(primary)
        for entry in design_artifacts:
            if isinstance(entry, dict):
                kind = entry.get("kind", "")
                p = entry.get("path", "")
                if p and kind in ("plan", "spec"):
                    source_paths.append(p)

    # Normalize every source path to a repo-relative POSIX string so the
    # governed runtime contract (which may supply ABSOLUTE design artifact
    # paths) is classified correctly.  Absolute paths under the repo root are
    # converted to repo-relative; paths already repo-relative pass through.
    # Non-superpowers and outside-repo paths are dropped later by
    # _archive_dst_for() returning None.
    def _to_repo_rel(p):
        if not p:
            return ""
        p_norm = os.path.normpath(p)
        if os.path.isabs(p_norm) and root:
            root_abs = os.path.normpath(root)
            try:
                rel = os.path.relpath(p_norm, root_abs)
            except ValueError:
                return p_norm
            # If the path is outside the repo root, relpath yields a "../..."
            # string; leave it so _archive_dst_for() drops it as non-superpowers.
            return rel
        return p_norm

    source_paths = [_to_repo_rel(s) for s in source_paths if _to_repo_rel(s)]

    # Derive archive destinations for any source lacking one:
    # plans/<file> -> archive/plans/<file>, specs/<file> -> archive/specs/<file>.
    def _archive_dst_for(src):
        src_norm = os.path.normpath(src)
        if src_norm.startswith("docs/superpowers/plans/"):
            fname = os.path.basename(src_norm)
            return f"docs/superpowers/archive/plans/{fname}"
        if src_norm.startswith("docs/superpowers/specs/"):
            fname = os.path.basename(src_norm)
            return f"docs/superpowers/archive/specs/{fname}"
        return None

    if not archived_paths:
        archived_paths = []
    for src in source_paths:
        archived_paths.append(_archive_dst_for(src))
    # Drop None destinations (non-superpowers paths) by aligning the two lists.
    paired = [(s, d) for s, d in zip(source_paths, archived_paths) if d]
    source_paths = [s for s, _ in paired]
    archived_paths = [d for _, d in paired]

    # Deterministic slug/date fallback (Spec Decision 11 / Task 8): if only a
    # plan or only a spec is known, look for a matching counterpart file with
    # the same slug/date filename in the sibling active superpowers directory.
    # This catches runs where the runtime contract only carried the plan
    # primary path but a matching spec exists on disk.
    def _has_kind(kind):
        prefix = f"docs/superpowers/{'plans' if kind == 'plan' else 'specs'}/"
        return any(os.path.normpath(s).startswith(prefix) for s in source_paths)

    def _add_counterpart(kind):
        other_kind = "spec" if kind == "plan" else "plan"
        other_dir = f"docs/superpowers/{other_kind}s"
        # Derive the slug/date filename from the known plan/spec source.
        known_prefix = f"docs/superpowers/{kind}s/"
        fname = None
        for s in source_paths:
            s_norm = os.path.normpath(s)
            if s_norm.startswith(known_prefix):
                fname = os.path.basename(s_norm)
                break
        if not fname:
            return
        candidate_src = f"{other_dir}/{fname}"
        candidate_abs = _resolve_path(root, candidate_src)
        if os.path.exists(candidate_abs):
            source_paths.append(candidate_src)
            archived_paths.append(_archive_dst_for(candidate_src))

    if _has_kind("plan") and not _has_kind("spec"):
        _add_counterpart("plan")
    elif _has_kind("spec") and not _has_kind("plan"):
        _add_counterpart("spec")

    for src_rel, dst_rel in zip(source_paths, archived_paths):
        src_abs = _resolve_path(root, src_rel)
        dst_abs = _resolve_path(root, dst_rel)
        if not os.path.exists(src_abs):
            if os.path.exists(dst_abs):
                already_archived.append((src_rel, dst_rel))
            else:
                skipped.append(src_rel)
            continue
        _ensure_dir(os.path.dirname(dst_abs))
        # Collision handling: do not overwrite existing destination.
        if os.path.exists(dst_abs):
            stem, ext = os.path.splitext(dst_abs)
            counter = 1
            candidate = f"{stem}-{counter}{ext}"
            while os.path.exists(candidate):
                counter += 1
                candidate = f"{stem}-{counter}{ext}"
            dst_abs = candidate
            dst_rel = os.path.relpath(dst_abs, root) if root else dst_abs
        shutil.move(src_abs, dst_abs)
        moved.append((src_rel, dst_rel))

    return {"moved": moved, "skipped": skipped, "already_archived": already_archived}