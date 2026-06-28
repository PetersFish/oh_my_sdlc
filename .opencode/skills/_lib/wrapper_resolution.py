from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .provider_registry_loader import (
    SUPPORTED_DISPATCH_KINDS,
    load_consistent_provider_config,
    load_registry,
    resolve_provider,
)
from .wrapper_contracts import make_blocker, resolve_wrapper_provider_blockers, validate_contract_inputs


class WrapperResolutionBlocked(Exception):
    def __init__(self, blockers):
        self.blockers = blockers
        message = blockers[0]["message"] if blockers else "Wrapper resolution blocked"
        super().__init__(message)


@dataclass
class WrapperDispatchResolution:
    module: str
    capability: str
    provider: str
    dispatch: Dict[str, str]
    verifier: Dict[str, str]
    result_contract: str


def resolve_wrapper_dispatch(
    module: str,
    capability: str,
    workflow_run_id: str,
    phase: str,
    action: str,
    flow_type: str,
    repo_root: Optional[Path | str] = None,
) -> WrapperDispatchResolution:
    missing = validate_contract_inputs(
        {
            "workflow_run_id": workflow_run_id,
            "phase": phase,
            "action": action,
            "flow_type": flow_type,
        }
    )
    if missing:
        raise ValueError(f"missing required inputs: {missing}")

    root = Path(repo_root) if repo_root else Path.cwd()
    blockers = resolve_wrapper_provider_blockers(module, capability, repo_root=str(root))
    if blockers:
        raise WrapperResolutionBlocked(blockers)

    registry = load_registry()
    config, config_blockers = load_consistent_provider_config(root)
    if config_blockers:
        raise WrapperResolutionBlocked(config_blockers)

    resolved = resolve_provider(
        module=module,
        capability=capability,
        registry=registry,
        config=config,
        repo_root=root,
    )
    if resolved is None:
        raise WrapperResolutionBlocked([
            make_blocker(
                reason="provider_resolution_failed",
                message=f"Provider resolution failed for module {module!r}, capability {capability!r}",
                recommended_action="verify provider registry and provider config are aligned",
            )
        ])

    dispatch = resolved.dispatch or {"kind": resolved.dispatch_kind, "target": resolved.dispatch_target}
    dispatch_kind = dispatch.get("kind")
    if dispatch_kind not in SUPPORTED_DISPATCH_KINDS:
        raise WrapperResolutionBlocked([
            make_blocker(
                reason="unsupported_dispatch_kind",
                message=(
                    f"Resolved provider {resolved.provider!r} for module {module!r} returned unsupported "
                    f"dispatch kind {dispatch_kind!r}"
                ),
                recommended_action=f"Use one of the supported dispatch kinds: {sorted(SUPPORTED_DISPATCH_KINDS)}",
            )
        ])

    return WrapperDispatchResolution(
        module=module,
        capability=capability,
        provider=resolved.provider,
        dispatch=dispatch,
        verifier=resolved.verifier or {"target": f"{resolved.provider}.{capability}"},
        result_contract=resolved.result_contract or f"{module}_result",
    )
