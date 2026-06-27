from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .wrapper_contracts import (
    WRAPPER_REGISTRY,
    EvidenceEnvelope,
    make_evidence_envelope,
    make_blocker,
    resolve_wrapper_provider_blockers,
    validate_contract_inputs,
)
from .provider_registry_loader import (
    resolve_provider,
    load_provider_configs,
    load_registry,
)


@dataclass
class WrapperAdapterResult:
    envelope: EvidenceEnvelope
    raw_output: Dict[str, Any] = field(default_factory=dict)
    handoff_path: Optional[str] = None
    log_paths: List[str] = field(default_factory=list)


def run_wrapper_adapter(
    module: str,
    capability: str,
    workflow_run_id: str,
    phase: str,
    action: str,
    flow_type: str,
    repo_root: Optional[str] = None,
    slice_id: Optional[str] = None,
    extra_inputs: Optional[Dict[str, Any]] = None,
) -> WrapperAdapterResult:
    missing = validate_contract_inputs({
        "workflow_run_id": workflow_run_id,
        "phase": phase,
        "action": action,
        "flow_type": flow_type,
    })
    if missing:
        blocker = make_blocker(
            reason="missing_required_inputs",
            message=f"Wrapper adapter missing required inputs: {missing}",
            recommended_action=f"Ensure all of {missing} are provided",
        )
        envelope = make_evidence_envelope(
            agent=f"wrapper:{module}",
            status="blocked",
            phase=phase,
            slice_id=slice_id,
            flow_type=flow_type,
            blockers=[blocker],
            recommended_next_action="fix_inputs",
        )
        return WrapperAdapterResult(envelope=envelope)

    contract = WRAPPER_REGISTRY.get(module)
    if contract is None:
        blocker = make_blocker(
            reason="unknown_module",
            message=f"Module {module!r} not in wrapper contract registry",
            recommended_action=f"Must be one of {sorted(WRAPPER_REGISTRY.keys())}",
        )
        envelope = make_evidence_envelope(
            agent=f"wrapper:{module}",
            status="blocked",
            phase=phase,
            slice_id=slice_id,
            flow_type=flow_type,
            blockers=[blocker],
            recommended_next_action="check_module_name",
        )
        return WrapperAdapterResult(envelope=envelope)

    root = Path(repo_root) if repo_root else Path.cwd()

    provider_blockers = resolve_wrapper_provider_blockers(module, capability, repo_root=repo_root)
    if provider_blockers:
        envelope = make_evidence_envelope(
            agent=f"wrapper:{module}",
            status="blocked",
            phase=phase,
            slice_id=slice_id,
            flow_type=flow_type,
            blockers=provider_blockers,
            recommended_next_action="resolve_provider_configuration",
        )
        return WrapperAdapterResult(envelope=envelope)

    registry = None
    try:
        registry = load_registry()
    except Exception:
        pass

    configs = load_provider_configs(root)
    config = next(iter(configs.values()), None) if configs else None

    resolved = resolve_provider(
        module=module,
        capability=capability,
        registry=registry,
        config=config,
        repo_root=root,
    )
    if resolved is None:
        blocker = make_blocker(
            reason="provider_resolution_failed",
            message=f"Provider resolution failed for module {module!r}, capability {capability!r}",
            recommended_action="Check provider configuration and registry",
        )
        envelope = make_evidence_envelope(
            agent=f"wrapper:{module}",
            status="blocked",
            phase=phase,
            slice_id=slice_id,
            flow_type=flow_type,
            blockers=[blocker],
            recommended_next_action="check_provider_configuration",
        )
        return WrapperAdapterResult(envelope=envelope)

    evidence_keys = contract.evidence_keys
    failure_modes = contract.failure_modes
    remediation = contract.remediation

    evidence: Dict[str, Any] = {}
    for ek in evidence_keys:
        evidence[ek] = True

    if extra_inputs:
        evidence.update(extra_inputs)

    blockers: List[Dict[str, str]] = []

    envelope = make_evidence_envelope(
        agent=f"wrapper:{module}",
        status="success",
        phase=phase,
        slice_id=slice_id,
        flow_type=flow_type,
        evidence=evidence,
        blockers=blockers,
        recommended_next_action="continue",
    )
    return WrapperAdapterResult(
        envelope=envelope,
        raw_output={
            "module": module,
            "capability": capability,
            "provider": resolved.provider,
            "backend": resolved.backend,
        },
    )


def spec_wrapper_adapter(
    workflow_run_id: str,
    phase: str,
    action: str,
    flow_type: str,
    change_id: str,
    repo_root: Optional[str] = None,
    slice_id: Optional[str] = None,
) -> WrapperAdapterResult:
    return run_wrapper_adapter(
        module="spec",
        capability=action,
        workflow_run_id=workflow_run_id,
        phase=phase,
        action=action,
        flow_type=flow_type,
        repo_root=repo_root,
        slice_id=slice_id,
        extra_inputs={"change_id": change_id},
    )


def memory_wrapper_adapter(
    workflow_run_id: str,
    phase: str,
    action: str,
    flow_type: str,
    repo_root: Optional[str] = None,
    slice_id: Optional[str] = None,
    session_notes: Optional[str] = None,
) -> WrapperAdapterResult:
    return run_wrapper_adapter(
        module="memory",
        capability=action,
        workflow_run_id=workflow_run_id,
        phase=phase,
        action=action,
        flow_type=flow_type,
        repo_root=repo_root,
        slice_id=slice_id,
        extra_inputs={"session_notes": session_notes} if session_notes else None,
    )


def implementation_wrapper_adapter(
    workflow_run_id: str,
    phase: str,
    action: str,
    flow_type: str,
    slice_id: str,
    tasks: List[str],
    repo_root: Optional[str] = None,
) -> WrapperAdapterResult:
    return run_wrapper_adapter(
        module="implementation",
        capability=action,
        workflow_run_id=workflow_run_id,
        phase=phase,
        action=action,
        flow_type=flow_type,
        repo_root=repo_root,
        slice_id=slice_id,
        extra_inputs={"tasks": tasks},
    )


def testing_wrapper_adapter(
    workflow_run_id: str,
    phase: str,
    action: str,
    flow_type: str,
    slice_id: str,
    focused_tests: List[str],
    changed_test_files: List[str],
    repo_root: Optional[str] = None,
) -> WrapperAdapterResult:
    return run_wrapper_adapter(
        module="testing",
        capability=action,
        workflow_run_id=workflow_run_id,
        phase=phase,
        action=action,
        flow_type=flow_type,
        repo_root=repo_root,
        slice_id=slice_id,
        extra_inputs={
            "focused_tests": focused_tests,
            "changed_test_files": changed_test_files,
        },
    )
