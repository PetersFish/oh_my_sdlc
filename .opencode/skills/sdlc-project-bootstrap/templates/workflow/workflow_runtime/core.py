"""core.py — constants and pure generic helpers.

Contains timestamps, hashes, path resolution, decision factories, and
shared validation sets that have no dependency on other runtime modules.
"""

import datetime
import hashlib
import os

# ---------------------------------------------------------------------------
# Validation sets
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

VALID_BRANCH_FINISH_DECISIONS = {"merge_local", "create_pr", "keep_branch", "discard"}

VALID_FLOW_TYPES = {"spec-flow", "lightweight-flow"}
VALID_SUBJECT_TYPES = {"spec_change", "roadmap_item"}

VALID_EXECUTION_MODES = {"main_checkout", "worktree"}

WORKTREE_REQUIRED_FIELDS = ("control_root", "worktree_path", "feature_branch")


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

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


def _branch_finish_decision_required(context):
    """Return True when a branch_finish_decision gate is required (Spec Dec 1,3).

    The gate is required when a feature branch/worktree is present, regardless
    of execution_mode.  Main-checkout mode without a feature branch does not
    require the gate by default.
    """
    context = context or {}
    execution_mode = _resolve_execution_mode(context)
    if execution_mode == "worktree":
        return True
    # Main-checkout still requires the gate when context.feature_branch is set.
    if context.get("feature_branch"):
        return True
    return False


def _resolve_branch_finish_decision(context):
    """Return the recorded branch_finish_decision or empty string.

    Validates the value against the allowed set when present.  Returns
    ``("", "missing")`` when required and absent, ``(value, "invalid")`` when
    present but not in the allowed set, or ``(value, "ok")`` when valid.
    """
    context = context or {}
    decision = context.get("branch_finish_decision", "") or ""
    if not _branch_finish_decision_required(context):
        return decision, "not_required"
    if not decision:
        return "", "missing"
    if decision not in VALID_BRANCH_FINISH_DECISIONS:
        return decision, "invalid"
    return decision, "ok"


def _is_branch_decision_block(block):
    """Return True when *block* is the runtime-owned branch-decision gate block.

    Recognition is based on the structured block shape emitted by
    ``cmd_before_dispatch``: type ``user_decision_required`` with
    ``ask_user_branch_finish_decision`` in ``next_allowed``.  This avoids
    broad message matching and ensures only runtime-owned decision blocks
    are eligible for reconciliation.
    """
    if not isinstance(block, dict):
        return False
    if block.get("type") != "user_decision_required":
        return False
    return "ask_user_branch_finish_decision" in block.get("next_allowed", [])


def _should_reconcile_branch_decision_block(state, tentative_context, recorded_key):
    """Return True when recording *tentative_context* under *recorded_key* validly
    resolves the persisted branch-decision block (Spec: repair-workflow-decision-block-unlock).

    All of the following must hold:
    1. The run is currently ``blocked``.
    2. The recorded key is exactly ``branch_finish_decision``.
    3. The tentative context resolves to decision status ``ok``.
    4. The persisted block represents the branch-decision gate.
    """
    if recorded_key != "branch_finish_decision":
        return False
    if state.get("status") != "blocked":
        return False
    block = state.get("block")
    if not _is_branch_decision_block(block):
        return False
    _, decision_status = _resolve_branch_finish_decision(tentative_context)
    return decision_status == "ok"