#!/usr/bin/env python3
"""SDLC workflow runtime -- deterministic, non-interactive state machine.

This module is a thin facade that delegates to the modular
``workflow_runtime`` package. All implementation logic lives in the
package's responsibility-based modules:

- ``workflow_runtime.core`` — constants, pure helpers, runtime context
- ``workflow_runtime.state`` — run-state I/O, pointer handling, persistence
- ``workflow_runtime.definitions`` — workflow YAML loading and validation
- ``workflow_runtime.domains`` — read-only domain loaders
- ``workflow_runtime.policies`` — policy registry, preflight, ensure-run
- ``workflow_runtime.dispatch`` — before/after dispatch hooks
- ``workflow_runtime.lifecycle`` — status, start, advance, done, etc.
- ``workflow_runtime.governance`` — governance-check, final-commit, foundations
- ``workflow_runtime.cli`` — parser construction and command dispatch

Commands: status, start, resume, readiness, resolve, record-evidence,
complete-phase, complete-hook, advance, block, done, validate,
governance-check, preflight, ensure-run, before-dispatch, after-dispatch,
final-commit.
"""

import os
import sys

# Make the sibling workflow_runtime package importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Re-export public symbols for backward compatibility with tests and
# callers that import the workflow module directly.
from workflow_runtime.core import (
    VALID_STATUSES,
    VALID_BLOCK_TYPES,
    VALID_GATE_STATUSES,
    VALID_MEMORY_SYNC_RESOLUTIONS,
    VALID_BRANCH_FINISH_DECISIONS,
    VALID_FLOW_TYPES,
    VALID_SUBJECT_TYPES,
    VALID_EXECUTION_MODES,
    WORKTREE_REQUIRED_FIELDS,
    _make_run_id,
    _ts,
    _ensure_dir,
    _resolve_path,
    _finding_hash,
    _resolve_execution_mode,
    _build_runtime_context,
    _branch_finish_decision_required,
    _resolve_branch_finish_decision,
    _is_branch_decision_block,
    _should_reconcile_branch_decision_block,
)

from workflow_runtime.state import (
    RUN_STATE_KEYS,
    _read_pointer,
    _set_pointer,
    _clear_pointer,
    _active_path,
    load_run_state,
    _list_active_runs,
    _find_active_run_by_subject,
    _migrate_legacy_artifacts,
    _json_default,
    save_run_state,
    _finalize_run_to_history,
    _missing_terminal_finish_agent_evidence,
    validate_run_state,
    _archive_lightweight_superpowers_artifacts,
    _list_dirs,
)

from workflow_runtime.definitions import (
    SUPPORTED_PHASE_FIELDS,
    load_workflow,
    validate_workflow,
    get_phase,
    is_phase_complete,
    _run_loaders,
    _calc_readiness,
    _check_exit_criteria,
)

from workflow_runtime.domains import (
    _parse_yaml_frontmatter,
    _sanitize_for_json,
    _read_frontmatter_field,
    _find_roadmap_items,
    _read_roadmap_item_spec_change,
    loader_openspec_change_status,
    loader_openspec_archive_path,
    loader_spec_change_status,
    loader_spec_archive_path,
    loader_roadmap_linked_item,
    loader_roadmap_item_status,
    _strip_leading_date_slug,
    _matching_superpowers_plans,
    _infer_phase,
)

from workflow_runtime.policies import (
    POLICY_REGISTRY,
    POLICY_META,
    ACTION_PHASE_MAP,
    register_policy,
    _make_preflight_decision,
    _evaluate_subject_run_context,
    _validate_action_phase,
    _start_command,
    _find_linked_roadmap_run,
    _read_roadmap_item_openspec_change,
    _ensure_command,
    _load_done_history_run_ids,
    _policy_openspec_change,
    _policy_archived_change,
    _policy_roadmap,
    cmd_preflight,
    _create_workflow_run,
    cmd_ensure_run,
)

from workflow_runtime.dispatch import (
    VALID_AGENT_NAMES,
    CANONICAL_AGENT_NAMES,
    BLOCK_AGENT_ACTION_MAP,
    PHASE_AGENT_MAP,
    _roadmap_agent_enabled,
    _is_roadmap_hook,
    _canonical_agent_name,
    ARCHIVE_PHASE_CLEANUP_ONLY_EVIDENCE,
    POSITIVE_CLEANUP_EVIDENCE_KEYS,
    _invalid_positive_cleanup_evidence,
    _premature_archive_cleanup_evidence,
    _phase_allows_agent,
    _allows_replan_from_apply_change,
    _normalized_block_actions,
    _action_routes_to_agent,
    _latest_blocker_routes_to_agent,
    _roadmap_block_routes_to_agent,
    _allows_blocked_dispatch,
    cmd_before_dispatch,
    _validate_evidence_envelope_contract,
    _missing_phase_evidence_keys,
    _missing_exit_criteria,
    _build_phase_evidence_view,
    _write_handoff_history_copy,
    _read_handoff_metadata,
    _handoff_metadata_mismatch_blocker,
    cmd_after_dispatch,
)

from workflow_runtime.lifecycle import (
    _status_summaries,
    cmd_status,
    cmd_validate,
    cmd_start,
    cmd_resume,
    cmd_readiness,
    cmd_resolve,
    cmd_record_evidence,
    cmd_record_context,
    cmd_complete_phase,
    _resolve_roadmap_hook_linked_items,
    _apply_roadmap_hook_block,
    cmd_complete_hook,
    cmd_cancel_run,
    cmd_advance,
    cmd_block,
    cmd_done,
)

from workflow_runtime.governance import (
    _run_git,
    _git_status_porcelain,
    _git_dirty_paths,
    _final_commit_allowed_prefixes,
    _classify_final_commit_paths,
    _load_done_history_run_for_final_commit,
    cmd_final_commit,
    cmd_governance_check,
    FOUNDATIONS,
    cmd_verify_foundations,
)

from workflow_runtime.slices import (
    cmd_slice_status,
    cmd_slice_next,
    cmd_slice_block,
    cmd_slice_resume,
    cmd_slice_cancel,
)

from workflow_runtime.state import (
    normalize_implementation_state,
    validate_implementation_state,
    slice_is_ready,
    all_required_slices_completed,
)

from workflow_runtime.cli import (
    COMMANDS,
    main,
)


if __name__ == "__main__":
    main()