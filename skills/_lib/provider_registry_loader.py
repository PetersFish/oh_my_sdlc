from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .wrapper_contracts import make_blocker

REGISTRY_PATH = Path(__file__).resolve().parent / "provider_registry.yaml"

CLIENT_CONFIG_DIRS = [
    ".opencode",
    ".cursor",
    ".claude",
]

CONFIG_FILENAME = "sdlc-providers.yaml"


@dataclass
class ProviderCapability:
    name: str
    supported: bool


@dataclass
class ProviderDef:
    name: str
    capabilities: Dict[str, bool] = field(default_factory=dict)
    backends: Dict[str, str] = field(default_factory=dict)
    dispatch_specs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    verifier_specs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    result_contracts: Dict[str, str] = field(default_factory=dict)


@dataclass
class ModuleProviderConfig:
    module: str
    default_provider: str
    providers: Dict[str, ProviderDef] = field(default_factory=dict)


@dataclass
class ResolvedProvider:
    module: str
    provider: str
    capability: str
    dispatch_kind: str
    dispatch_target: str
    dispatch: Dict[str, Any] = field(default_factory=dict)
    verifier: Dict[str, Any] = field(default_factory=dict)
    result_contract: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


def _load_registry_raw(registry_path: Optional[Path] = None) -> Dict[str, Any]:
    path = registry_path or REGISTRY_PATH
    if not path.exists():
        raise FileNotFoundError(f"provider registry not found at {path}")
    with open(path, "r") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"invalid registry YAML at {path}: expected a mapping, got {type(data).__name__}")
    return data


def _parse_registry(raw: Dict[str, Any]) -> Dict[str, ModuleProviderConfig]:
    modules_raw = raw.get("modules")
    if not isinstance(modules_raw, dict):
        raise ValueError("registry missing 'modules' mapping")
    parsed: Dict[str, ModuleProviderConfig] = {}
    for module_name, module_data in modules_raw.items():
        if not isinstance(module_data, dict):
            raise ValueError(f"registry module {module_name!r}: expected a mapping")
        providers: Dict[str, ProviderDef] = {}
        for provider_name, provider_data in module_data.get("providers", {}).items():
            if not isinstance(provider_data, dict):
                raise ValueError(
                    f"registry provider {provider_name!r} in module {module_name!r}: expected a mapping"
                )
            backends = provider_data.get("backend")
            if isinstance(backends, dict):
                backends = {str(k): str(v) for k, v in backends.items()}
            else:
                backends = {}
            dispatch_specs = provider_data.get("dispatch")
            if isinstance(dispatch_specs, dict):
                dispatch_specs = {
                    str(k): dict(v) for k, v in dispatch_specs.items() if isinstance(v, dict)
                }
            else:
                dispatch_specs = {
                    capability_name: {"kind": "skill", "target": target}
                    for capability_name, target in backends.items()
                }

            verifier_specs = provider_data.get("verifier")
            if isinstance(verifier_specs, dict):
                verifier_specs = {
                    str(k): dict(v) for k, v in verifier_specs.items() if isinstance(v, dict)
                }
            else:
                verifier_specs = {
                    capability_name: {"target": f"{provider_name}.{capability_name}"}
                    for capability_name in dispatch_specs.keys()
                }

            result_contracts = provider_data.get("result_contract")
            if isinstance(result_contracts, dict):
                result_contracts = {str(k): str(v) for k, v in result_contracts.items()}
            else:
                result_contracts = {}
            providers[provider_name] = ProviderDef(
                name=provider_name,
                capabilities=provider_data.get("capabilities", {}),
                backends=backends,
                dispatch_specs=dispatch_specs,
                verifier_specs=verifier_specs,
                result_contracts=result_contracts,
            )
        parsed[module_name] = ModuleProviderConfig(
            module=module_name,
            default_provider=module_data.get("default_provider", ""),
            providers=providers,
        )
    return parsed


def load_registry(registry_path: Optional[Path] = None) -> Dict[str, ModuleProviderConfig]:
    raw = _load_registry_raw(registry_path)
    return _parse_registry(raw)


# ---------------------------------------------------------------------------
# Provider config loading from project-level client directories
# ---------------------------------------------------------------------------


def _load_provider_config(repo_root: Path, client_dir: str) -> Optional[Dict[str, Any]]:
    config_path = repo_root / client_dir / CONFIG_FILENAME
    if not config_path.exists():
        return None
    with open(config_path, "r") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        return None
    return data


def load_provider_configs(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    """Return {client_dir: config_dict} for each client config file that exists."""
    configs: Dict[str, Dict[str, Any]] = {}
    for client_dir in CLIENT_CONFIG_DIRS:
        cfg = _load_provider_config(repo_root, client_dir)
        if cfg is not None:
            configs[client_dir] = cfg
    return configs


def load_primary_provider_config(repo_root: Path) -> Optional[Dict[str, Any]]:
    """Return the first available provider config from client directories."""
    for client_dir in CLIENT_CONFIG_DIRS:
        cfg = _load_provider_config(repo_root, client_dir)
        if cfg is not None:
            return cfg
    return None


# ---------------------------------------------------------------------------
# Provider resolution with fail-closed behavior
# ---------------------------------------------------------------------------


def resolve_provider(
    module: str,
    capability: str,
    registry: Optional[Dict[str, ModuleProviderConfig]] = None,
    config: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
) -> Optional[ResolvedProvider]:
    """Resolve which provider and backend handles a module capability.

    Returns a ResolvedProvider on success, or None if a blocker should be raised.
    Use `resolve_provider_or_blocker` for the structured blocker variant.
    """
    if registry is None:
        registry = load_registry()

    resolved = resolve_provider_dispatch_spec(
        module=module,
        capability=capability,
        registry=registry,
        config=config,
        repo_root=repo_root,
    )
    if resolved is None:
        return None
    return resolved


def resolve_provider_dispatch_spec(
    module: str,
    capability: str,
    registry: Optional[Dict[str, ModuleProviderConfig]] = None,
    config: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
) -> Optional[ResolvedProvider]:
    if registry is None:
        registry = load_registry()

    if config is None and repo_root is not None:
        config = load_primary_provider_config(Path(repo_root))

    module_config = registry.get(module)
    if module_config is None:
        return None

    # Determine provider name: config > default
    provider_name = module_config.default_provider
    if config is not None:
        module_cfg = config.get(module)
        if isinstance(module_cfg, dict):
            provider_name = module_cfg.get("provider", provider_name)

    provider_def = module_config.providers.get(provider_name)
    if provider_def is None:
        return None

    # Check capability
    supported = provider_def.capabilities.get(capability, False)
    if not supported:
        return None

    dispatch = provider_def.dispatch_specs.get(capability)
    if not isinstance(dispatch, dict) or not dispatch.get("target"):
        return None

    verifier = provider_def.verifier_specs.get(capability, {})
    if not isinstance(verifier, dict) or not verifier.get("target"):
        verifier = {"target": f"{provider_name}.{capability}"}

    result_contract = provider_def.result_contracts.get(capability, f"{module}_result")

    return ResolvedProvider(
        module=module,
        provider=provider_name,
        capability=capability,
        dispatch_kind=str(dispatch.get("kind", "skill")),
        dispatch_target=str(dispatch.get("target", "")),
        dispatch=dispatch,
        verifier=verifier,
        result_contract=result_contract,
    )


def resolve_provider_or_blocker(
    module: str,
    capability: str,
    registry: Optional[Dict[str, ModuleProviderConfig]] = None,
    config: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """Resolve a provider backend and return blockers if anything fails.

    Returns an empty list on success, or a list of structured blocker dicts.
    """
    if registry is None:
        try:
            registry = load_registry()
        except Exception as exc:
            return [make_blocker(
                reason="registry_load_failed",
                message=f"Failed to load provider registry: {exc}",
                recommended_action="Verify skills/_lib/provider_registry.yaml exists and is valid YAML",
            )]

    blockers: List[Dict[str, str]] = []

    module_config = registry.get(module)
    if module_config is None:
        known = sorted(registry.keys())
        blockers.append(make_blocker(
            reason="unknown_module",
            message=f"Module {module!r} not in provider registry. Known modules: {known}",
            recommended_action=f"Register module {module!r} in the provider registry or verify the module name",
        ))
        return blockers

    # Determine provider name: config > default
    provider_name = module_config.default_provider
    if config is not None:
        module_cfg = config.get(module)
        if isinstance(module_cfg, dict):
            provider_name = module_cfg.get("provider", provider_name)

    if not provider_name:
        blockers.append(make_blocker(
            reason="missing_provider",
            message=f"No provider configured for module {module!r} and no default registered",
            recommended_action=f"Set {module}.provider in sdlc-providers.yaml or add a default to the registry",
        ))
        return blockers

    provider_def = module_config.providers.get(provider_name)
    if provider_def is None:
        allowed = sorted(module_config.providers.keys())
        blockers.append(make_blocker(
            reason="unknown_provider",
            message=f"Provider {provider_name!r} not registered for module {module!r}. Allowed: {allowed}",
            recommended_action=f"Change {module}.provider in sdlc-providers.yaml to one of {allowed}",
        ))
        return blockers

    supported = provider_def.capabilities.get(capability, False)
    if not supported:
        supported_caps = [k for k, v in provider_def.capabilities.items() if v]
        blockers.append(make_blocker(
            reason="unsupported_capability",
            message=(
                f"Provider {provider_name!r} for module {module!r} does not support "
                f"capability {capability!r}. Supported: {supported_caps}"
            ),
            recommended_action=f"Choose a different provider or extend {provider_name!r} to support {capability!r}",
        ))
        return blockers

    dispatch = provider_def.dispatch_specs.get(capability)
    if not isinstance(dispatch, dict) or not dispatch.get("target"):
        blockers.append(make_blocker(
            reason="missing_backend",
            message=f"Provider {provider_name!r} for module {module!r} has no dispatch target mapped for capability {capability!r}",
            recommended_action=f"Add a dispatch mapping in the provider registry for {provider_name!r}.{capability}",
        ))
        return blockers

    return []


def get_provider_config_value(config: Optional[Dict[str, Any]], module: str, key: str) -> Optional[str]:
    """Read a string config value from the provider config dict.

    Returns None if the config, module section, or key is missing.
    """
    if config is None:
        return None
    section = config.get(module)
    if not isinstance(section, dict):
        return None
    val = section.get(key)
    if isinstance(val, str):
        return val
    return None
