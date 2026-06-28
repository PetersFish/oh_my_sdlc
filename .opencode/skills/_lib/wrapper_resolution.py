from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .provider_registry_loader import load_provider_configs, load_registry, resolve_provider
from .wrapper_contracts import resolve_wrapper_provider_blockers, validate_contract_inputs


class WrapperResolutionBlocked(ValueError):
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
        raise WrapperResolutionBlocked([
            {
                "reason": "provider_resolution_failed",
                "message": f"Provider resolution failed for module {module!r}, capability {capability!r}",
                "recommended_action": "verify provider registry and provider config are aligned",
            }
        ])

    return WrapperDispatchResolution(
        module=module,
        capability=capability,
        provider=resolved.provider,
        dispatch=resolved.dispatch or {"kind": resolved.dispatch_kind, "target": resolved.dispatch_target},
        verifier=resolved.verifier or {"target": f"{resolved.provider}.{capability}"},
        result_contract=resolved.result_contract or f"{module}_result",
    )
