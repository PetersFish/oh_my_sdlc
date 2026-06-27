from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVIDENCE_ENVELOPE_KEYS: List[str] = [
    "agent", "status", "phase", "slice_id", "flow_type",
    "evidence", "artifacts", "blockers", "recommended_next_action",
]

REQUIRED_ENVELOPE_KEYS: Set[str] = {"agent", "status", "phase", "evidence"}

VALID_AGENT_STATUSES: Set[str] = {"success", "failed", "blocked"}

VALID_FLOW_TYPES: Set[str] = {"spec-flow", "lightweight-flow"}

REQUIRED_CONTRACT_INPUTS: List[str] = [
    "workflow_run_id", "phase", "action", "flow_type",
]

HANDOFF_SECTIONS: List[str] = [
    "Metadata",
    "Objective",
    "Work Completed",
    "Files / Artifacts Changed",
    "Commands Run",
    "Evidence Summary",
    "Blockers",
    "Assumptions",
    "Risks / Follow-Ups",
    "Raw Logs",
]

HANDOFF_METADATA_KEYS: List[str] = [
    "Run ID", "Slice ID", "Agent", "Phase",
    "Flow Type", "Status", "Recommended Next Agent",
]

RAW_LOG_META_KEYS: List[str] = ["path", "kind", "command", "result"]

# Phase-to-agent mapping (canonical dash-form agent names)
PHASE_AGENT_MAP: Dict[str, Set[str]] = {
    "create_change": {"plan-agent"},
    "apply_change": {"implement-agent", "test-agent", "review-agent"},
    "archive_change": {"finish-agent"},
    "post_archive_actions": {"finish-agent"},
}

CHANGE_PHASES: Set[str] = set(PHASE_AGENT_MAP.keys())

# Agent names accepted in both dash and underscore forms
CANONICAL_AGENT_NAMES: Dict[str, str] = {
    "plan-agent": "plan-agent",
    "plan_agent": "plan-agent",
    "implement-agent": "implement-agent",
    "implement_agent": "implement-agent",
    "test-agent": "test-agent",
    "test_agent": "test-agent",
    "review-agent": "review-agent",
    "review_agent": "review-agent",
    "finish-agent": "finish-agent",
    "finish_agent": "finish-agent",
}

VALID_AGENT_NAMES: Set[str] = set(CANONICAL_AGENT_NAMES.keys())

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RawLogEntry:
    path: str
    kind: str = ""
    command: str = ""
    result: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "path": self.path,
            "kind": self.kind,
            "command": self.command,
            "result": self.result,
        }


@dataclass
class HandoffMetadata:
    run_id: str = ""
    slice_id: str = ""
    agent: str = ""
    phase: str = ""
    flow_type: str = ""
    status: str = ""
    recommended_next_agent: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "Run ID": self.run_id,
            "Slice ID": self.slice_id,
            "Agent": self.agent,
            "Phase": self.phase,
            "Flow Type": self.flow_type,
            "Status": self.status,
            "Recommended Next Agent": self.recommended_next_agent,
        }


@dataclass
class EvidenceEnvelope:
    agent: str
    status: str
    phase: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    slice_id: Optional[str] = None
    flow_type: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    blockers: List[Dict[str, str]] = field(default_factory=list)
    recommended_next_action: str = ""

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.agent:
            errors.append("missing 'agent'")
        if self.status not in VALID_AGENT_STATUSES:
            errors.append(
                f"invalid 'status': {self.status!r}, expected one of {VALID_AGENT_STATUSES}"
            )
        if not self.phase:
            errors.append("missing 'phase'")
        if self.flow_type is not None and self.flow_type not in VALID_FLOW_TYPES:
            errors.append(
                f"invalid 'flow_type': {self.flow_type!r}, expected one of {VALID_FLOW_TYPES}"
            )
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "status": self.status,
            "phase": self.phase,
            "slice_id": self.slice_id,
            "flow_type": self.flow_type,
            "evidence": self.evidence,
            "artifacts": self.artifacts,
            "blockers": self.blockers,
            "recommended_next_action": self.recommended_next_action,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# ---------------------------------------------------------------------------
# Contract validation and construction
# ---------------------------------------------------------------------------


def validate_evidence_envelope(data: Dict[str, Any]) -> List[str]:
    """Validate that a dict conforms to the shared evidence envelope shape."""
    errors: List[str] = []
    missing = REQUIRED_ENVELOPE_KEYS - set(data.keys())
    if missing:
        errors.append(f"missing required envelope keys: {sorted(missing)}")
    if "status" in data and data["status"] not in VALID_AGENT_STATUSES:
        errors.append(
            f"invalid status: {data['status']!r}, expected one of {VALID_AGENT_STATUSES}"
        )
    if "flow_type" in data and data["flow_type"] is not None:
        if data["flow_type"] not in VALID_FLOW_TYPES:
            errors.append(
                f"invalid flow_type: {data['flow_type']!r}, expected one of {VALID_FLOW_TYPES}"
            )
    if "evidence" in data and isinstance(data["evidence"], dict):
        focused = data["evidence"].get("focused_tests")
        if focused is not None and not isinstance(focused, list):
            errors.append("evidence.focused_tests must be an array when present")
    return errors


def validate_handoff_structure(content: str) -> List[str]:
    """Check that a handoff Markdown string has the required top-level sections."""
    missing: List[str] = []
    for section in HANDOFF_SECTIONS:
        header = f"## {section}"
        if header not in content:
            missing.append(section)
    return missing


def validate_raw_log_entry(entry: Dict[str, Any]) -> List[str]:
    """Check that a raw log entry has required metadata fields."""
    missing = [k for k in RAW_LOG_META_KEYS if k not in entry]
    if missing:
        return [f"raw log entry missing metadata keys: {missing}"]
    return []


def validate_contract_inputs(inputs: Dict[str, Any]) -> List[str]:
    """Check that wrapper contract inputs include required fields."""
    missing = [k for k in REQUIRED_CONTRACT_INPUTS if k not in inputs]
    return missing


def canonical_agent_name(name: str) -> Optional[str]:
    """Return the canonical dash-form agent name, or None if invalid."""
    return CANONICAL_AGENT_NAMES.get(name)


def is_agent_allowed_in_phase(agent: str, phase: str) -> bool:
    """Check if an agent is allowed to run in the given workflow phase."""
    allowed = PHASE_AGENT_MAP.get(phase)
    if allowed is None:
        return False
    canonical = canonical_agent_name(agent)
    if canonical is None:
        return False
    return canonical in allowed


def check_parallel_disjoint(work_packages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Verify parallel work packages operate on disjoint files/modules.

    Returns a blocker dict if packages share files/modules, or None if safe.
    """
    seen_files: Dict[str, str] = {}
    for pkg in work_packages:
        files = pkg.get("files", [])
        if isinstance(files, list):
            for f in files:
                if f in seen_files:
                    return {
                        "reason": "shared_file_in_parallel_packages",
                        "message": (
                            f"File {f!r} appears in both package "
                            f"{seen_files[f]!r} and package {pkg.get('slice_id', 'unknown')!r}"
                        ),
                        "recommended_action": "serialize_or_split_differently",
                    }
                seen_files[f] = pkg.get("slice_id", "unknown")
        modules = pkg.get("modules", [])
        if isinstance(modules, list):
            for m in modules:
                key = f"module:{m}"
                if key in seen_files:
                    return {
                        "reason": "shared_module_in_parallel_packages",
                        "message": (
                            f"Module {m!r} appears in both package "
                            f"{seen_files[key]!r} and package {pkg.get('slice_id', 'unknown')!r}"
                        ),
                        "recommended_action": "serialize_or_split_differently",
                    }
                seen_files[key] = pkg.get("slice_id", "unknown")
    return None


def make_evidence_envelope(
    agent: str,
    status: str,
    phase: str,
    evidence: Optional[Dict[str, Any]] = None,
    slice_id: Optional[str] = None,
    flow_type: Optional[str] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    blockers: Optional[List[Dict[str, str]]] = None,
    recommended_next_action: str = "",
) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        agent=agent,
        status=status,
        phase=phase,
        evidence=evidence or {},
        slice_id=slice_id,
        flow_type=flow_type,
        artifacts=artifacts or {},
        blockers=blockers or [],
        recommended_next_action=recommended_next_action,
    )


def make_blocker(
    reason: str,
    message: str = "",
    recommended_action: str = "",
) -> Dict[str, str]:
    return {
        "reason": reason,
        "message": message,
        "recommended_action": recommended_action,
    }


def make_raw_log_entry(
    path: str,
    kind: str = "",
    command: str = "",
    result: str = "",
) -> Dict[str, str]:
    return {
        "path": path,
        "kind": kind,
        "command": command,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Module-specific wrapper contract definitions
# ---------------------------------------------------------------------------


@dataclass
class WrapperContract:
    """Stable wrapper contract definition for a lifecycle module."""

    module: str
    required_inputs: List[str] = field(default_factory=list)
    evidence_keys: List[str] = field(default_factory=list)
    exit_criteria: List[str] = field(default_factory=list)
    failure_modes: List[Dict[str, str]] = field(default_factory=list)
    remediation: List[Dict[str, str]] = field(default_factory=list)


SPEC_WRAPPER = WrapperContract(
    module="spec",
    required_inputs=["change_id", "action"],
    evidence_keys=[
        "openspec_artifacts_done",
        "tasks_complete",
        "tdd_passed",
        "archive_path_exists",
    ],
    exit_criteria=[
        "openspec_artifacts_done",
        "tasks_complete",
        "tdd_passed",
        "eval_passed_or_human_decision_recorded",
        "archive_path_exists",
    ],
    failure_modes=[
        {
            "mode": "missing_change_id",
            "description": "No change_id in run context or agent input",
            "blocks_phase": "true",
        },
        {
            "mode": "artifact_generation_failed",
            "description": "OpenSpec artifact creation/apply/archive failed",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "missing_change_id",
            "action": "Ensure context.change_id is set in workflow run state before dispatching plan-agent",
        },
        {
            "for": "artifact_generation_failed",
            "action": "Surface error to user; agent may retry or user may troubleshoot OpenSpec",
        },
    ],
)

MEMORY_WRAPPER = WrapperContract(
    module="memory",
    required_inputs=["session_notes"],
    evidence_keys=["memory_synced", "not_needed"],
    exit_criteria=["memory_context_loaded_or_not_initialized", "pending_hooks_empty"],
    failure_modes=[
        {
            "mode": "sync_failed",
            "description": "Memory sync worker returned an error",
            "blocks_phase": "false",
        },
    ],
    remediation=[
        {
            "for": "sync_failed",
            "action": "Retry memory sync; if persistent, user may defer via complete-hook",
        },
    ],
)

ROADMAP_WRAPPER = WrapperContract(
    module="roadmap",
    required_inputs=["item_id", "action"],
    evidence_keys=["roadmap_item_created", "review_decision_recorded"],
    exit_criteria=["roadmap_item_created", "review_decision_recorded", "review_passed_or_failed"],
    failure_modes=[
        {
            "mode": "item_not_found",
            "description": "Roadmap item id does not exist",
            "blocks_phase": "true",
        },
        {
            "mode": "state_mismatch",
            "description": "Roadmap item state does not allow requested action",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "item_not_found",
            "action": "Verify item id; may need to capture first",
        },
        {
            "for": "state_mismatch",
            "action": "Report current state and allowed transitions to user",
        },
    ],
)

EVAL_WRAPPER = WrapperContract(
    module="eval",
    required_inputs=["target_id"],
    evidence_keys=["eval_passed_or_human_decision_recorded", "golden_eval_run"],
    exit_criteria=["eval_passed_or_human_decision_recorded"],
    failure_modes=[
        {
            "mode": "no_golden_cases",
            "description": "No golden eval cases exist for target",
            "blocks_phase": "true",
        },
        {
            "mode": "golden_eval_failed",
            "description": "Promptfoo golden eval returned failures",
            "blocks_phase": "true",
        },
        {
            "mode": "runner_unavailable",
            "description": "Promptfoo not installed or not found",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "no_golden_cases",
            "action": "Route to sdlc-evalops for case creation, or user grants EvalOps exception",
        },
        {
            "for": "golden_eval_failed",
            "action": "Route to sdlc-evalops for failure classification and user-confirmed fix plan",
        },
        {
            "for": "runner_unavailable",
            "action": "User may install Promptfoo or grant EvalOps exception",
        },
    ],
)

PLANNING_WRAPPER = WrapperContract(
    module="planning",
    required_inputs=["requirements"],
    evidence_keys=["plan_produced", "intent_ready_for_classification"],
    exit_criteria=["intent_ready_for_classification", "workflow_branch_selected"],
    failure_modes=[
        {
            "mode": "ambiguous_requirements",
            "description": "Design ambiguity that brainstorming cannot resolve",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "ambiguous_requirements",
            "action": "Escalate to user for clarification",
        },
    ],
)

IMPLEMENTATION_WRAPPER = WrapperContract(
    module="implementation",
    required_inputs=["slice_id", "tasks"],
    evidence_keys=["tasks_complete", "tdd_passed", "focused_tests_passed"],
    exit_criteria=["tasks_complete", "tdd_passed"],
    failure_modes=[
        {
            "mode": "tdd_failure",
            "description": "TDD red/green loop did not reach green",
            "blocks_phase": "true",
        },
        {
            "mode": "focused_test_failure",
            "description": "Focused tests did not pass after implementation",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "tdd_failure",
            "action": "implement-agent retries with systematic debugging",
        },
        {
            "for": "focused_test_failure",
            "action": "implement-agent fixes implementation and retries",
        },
    ],
)

TESTING_WRAPPER = WrapperContract(
    module="testing",
    required_inputs=["slice_id", "focused_tests", "changed_test_files"],
    evidence_keys=["verification_passed", "overfit_check_passed", "regression_passed"],
    exit_criteria=["tdd_passed", "eval_passed_or_human_decision_recorded"],
    failure_modes=[
        {
            "mode": "verification_failure",
            "description": "Independent verification found failures",
            "blocks_phase": "true",
        },
        {
            "mode": "overfit_detected",
            "description": "New or changed tests are overfit to implementation details",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "verification_failure",
            "action": "Route blocker back to implement-agent with failure details",
        },
        {
            "for": "overfit_detected",
            "action": "Route blocker to implement-agent to rewrite tests for behavioral coverage",
        },
    ],
)

REVIEW_WRAPPER = WrapperContract(
    module="review",
    required_inputs=["verification_evidence"],
    evidence_keys=["review_complete"],
    exit_criteria=["run_status_done"],
    failure_modes=[
        {
            "mode": "review_blocked",
            "description": "Code review found issues that must be addressed",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "review_blocked",
            "action": "Implement review feedback and re-run test-agent verification",
        },
    ],
)

FINISH_WRAPPER = WrapperContract(
    module="finish",
    required_inputs=["change_id"],
    evidence_keys=["archive_path_exists", "pending_hooks_empty"],
    exit_criteria=["pending_hooks_empty", "run_status_done"],
    failure_modes=[
        {
            "mode": "archive_failed",
            "description": "OpenSpec archive or branch finish failed",
            "blocks_phase": "true",
        },
        {
            "mode": "hooks_pending",
            "description": "Post-archive hooks not resolved",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "archive_failed",
            "action": "Surface error; user may retry or manually resolve",
        },
        {
            "for": "hooks_pending",
            "action": "Complete memory_sync and roadmap_done_if_relevant hooks",
        },
    ],
)

VERIFICATION_WRAPPER = WrapperContract(
    module="verification",
    required_inputs=["verification_target"],
    evidence_keys=["verification_passed", "regression_passed"],
    exit_criteria=[],
    failure_modes=[
        {
            "mode": "verification_failed",
            "description": "Verification against change artifacts found deviations",
            "blocks_phase": "true",
        },
    ],
    remediation=[
        {
            "for": "verification_failed",
            "action": "Surface deviations to user; may require re-implementation",
        },
    ],
)

WRAPPER_REGISTRY: Dict[str, WrapperContract] = {
    "spec": SPEC_WRAPPER,
    "memory": MEMORY_WRAPPER,
    "roadmap": ROADMAP_WRAPPER,
    "eval": EVAL_WRAPPER,
    "planning": PLANNING_WRAPPER,
    "implementation": IMPLEMENTATION_WRAPPER,
    "testing": TESTING_WRAPPER,
    "review": REVIEW_WRAPPER,
    "finish": FINISH_WRAPPER,
    "verification": VERIFICATION_WRAPPER,
}


def get_wrapper(module: str) -> Optional[WrapperContract]:
    return WRAPPER_REGISTRY.get(module)


def logs_optional_policy(status: str) -> bool:
    """Raw logs are expected for failures/blockers, optional for success."""
    return status != "success"


# ---------------------------------------------------------------------------
# Provider resolution integration: wrapper contracts → provider backends
# ---------------------------------------------------------------------------


def resolve_wrapper_provider_blockers(
    module: str,
    capability: str,
    repo_root: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Resolve a wrapper module's provider backend for the given capability.

    Verifies the wrapper contract exists, then delegates to provider resolution.
    Returns empty list on success, or structured blocker dicts on failure.
    """
    if module not in WRAPPER_REGISTRY:
        return [make_blocker(
            reason="unknown_module",
            message=f"Module {module!r} not in wrapper contract registry",
            recommended_action=f"Module must be one of {sorted(WRAPPER_REGISTRY.keys())}",
        )]

    from .provider_registry_loader import resolve_provider_or_blocker, load_provider_configs, load_registry

    root = Path(repo_root) if repo_root else Path.cwd()

    try:
        registry = load_registry()
    except Exception as exc:
        return [make_blocker(
            reason="registry_load_failed",
            message=str(exc),
            recommended_action="Verify skills/_lib/provider_registry.yaml exists",
        )]

    if module not in registry:
        return [make_blocker(
            reason="not_provider_managed",
            message=f"Module {module!r} is a wrapper contract but not yet provider-managed",
            recommended_action=f"Add module {module!r} to provider_registry.yaml or use direct wrapper",
        )]

    configs = load_provider_configs(root)
    config = next(iter(configs.values()), None) if configs else None

    return resolve_provider_or_blocker(module, capability, registry=registry, config=config)
