from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .wrapper_contracts import make_blocker

REGISTRY_PATH = Path(__file__).resolve().parent / "provider_registry.yaml"
REGISTRY_VERSION = 2
SUPPORTED_DISPATCH_KINDS = {"skill"}

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


def _load_registry_raw(registry_path: Optional[Path] = None) -> Dict[str, Any]:
    path = registry_path or REGISTRY_PATH
    if not path.exists():
        raise FileNotFoundError(f"provider registry not found at {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"invalid registry YAML at {path}: expected a mapping, got {type(data).__name__}")
    version = data.get("version")
    if version != REGISTRY_VERSION:
        raise ValueError(
            f"provider registry at {path} must declare version {REGISTRY_VERSION}, got {version!r}"
        )
    return data


def _require_mapping(container: Dict[str, Any], key: str, context: str) -> Dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{context}: expected '{key}' to be a mapping")
    return value


def _parse_registry(raw: Dict[str, Any]) -> Dict[str, ModuleProviderConfig]:
    modules_raw = raw.get("modules")
    if not isinstance(modules_raw, dict):
        raise ValueError("registry missing 'modules' mapping")
    parsed: Dict[str, ModuleProviderConfig] = {}
    for module_name, module_data in modules_raw.items():
        if not isinstance(module_data, dict):
            raise ValueError(f"registry module {module_name!r}: expected a mapping")
        providers: Dict[str, ProviderDef] = {}
        providers_raw = _require_mapping(module_data, "providers", f"registry module {module_name!r}")
        for provider_name, provider_data in providers_raw.items():
            if not isinstance(provider_data, dict):
                raise ValueError(
                    f"registry provider {provider_name!r} in module {module_name!r}: expected a mapping"
                )
            capabilities = _require_mapping(
                provider_data,
                "capabilities",
                f"registry provider {provider_name!r} in module {module_name!r}",
            )
            dispatch_specs_raw = _require_mapping(
                provider_data,
                "dispatch",
                f"registry provider {provider_name!r} in module {module_name!r}",
            )
            verifier_specs_raw = _require_mapping(
                provider_data,
                "verifier",
                f"registry provider {provider_name!r} in module {module_name!r}",
            )
            result_contracts_raw = _require_mapping(
                provider_data,
                "result_contract",
                f"registry provider {provider_name!r} in module {module_name!r}",
            )

            dispatch_specs = {
                str(capability_name): dict(spec)
                for capability_name, spec in dispatch_specs_raw.items()
                if isinstance(spec, dict)
            }
            verifier_specs = {
                str(capability_name): dict(spec)
                for capability_name, spec in verifier_specs_raw.items()
                if isinstance(spec, dict)
            }
            result_contracts = {
                str(capability_name): str(contract_name)
                for capability_name, contract_name in result_contracts_raw.items()
                if isinstance(contract_name, str) and contract_name
            }
            providers[provider_name] = ProviderDef(
                name=provider_name,
                capabilities={str(name): bool(supported) for name, supported in capabilities.items()},
                dispatch_specs=dispatch_specs,
                verifier_specs=verifier_specs,
                result_contracts=result_contracts,
            )
        parsed[module_name] = ModuleProviderConfig(
            module=module_name,
            default_provider=str(module_data.get("default_provider", "")),
            providers=providers,
        )
    return parsed


def load_registry(registry_path: Optional[Path] = None) -> Dict[str, ModuleProviderConfig]:
    raw = _load_registry_raw(registry_path)
    return _parse_registry(raw)


def _load_provider_config(repo_root: Path, client_dir: str) -> Optional[Dict[str, Any]]:
    config_path = repo_root / client_dir / CONFIG_FILENAME
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as fh:
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


def load_consistent_provider_config(
    repo_root: Path,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, str]]]:
    configs = load_provider_configs(repo_root)
    if not configs:
        return None, []

    mismatches: List[Dict[str, str]] = []
    explicit_by_module: Dict[str, Dict[str, str]] = {}
    for client_dir, cfg in configs.items():
        for module_name, module_cfg in cfg.items():
            if not isinstance(module_cfg, dict):
                continue
            provider_name = module_cfg.get("provider")
            if isinstance(provider_name, str) and provider_name:
                explicit_by_module.setdefault(module_name, {})[client_dir] = provider_name

    for module_name, by_client in explicit_by_module.items():
        unique_providers = sorted(set(by_client.values()))
        if len(unique_providers) > 1:
            details = ", ".join(f"{client_dir}={provider_name}" for client_dir, provider_name in sorted(by_client.items()))
            mismatches.append(make_blocker(
                reason="distributed_provider_config_mismatch",
                message=(
                    f"Provider configs disagree for module {module_name!r}: {details}. "
                    f"Expected all client configs to resolve to the same provider."
                ),
                recommended_action=(
                    f"Align {CONFIG_FILENAME} across {', '.join(CLIENT_CONFIG_DIRS)} for module {module_name!r}"
                ),
            ))
    if mismatches:
        return None, mismatches
    return next(iter(configs.values())), []


def load_primary_provider_config(repo_root: Path) -> Optional[Dict[str, Any]]:
    config, _ = load_consistent_provider_config(repo_root)
    return config


def resolve_provider(
    module: str,
    capability: str,
    registry: Optional[Dict[str, ModuleProviderConfig]] = None,
    config: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
) -> Optional[ResolvedProvider]:
    """Resolve which provider and dispatch spec handles a module capability."""
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
        config, blockers = load_consistent_provider_config(Path(repo_root))
        if blockers:
            return None

    module_config = registry.get(module)
    if module_config is None:
        return None

    provider_name = module_config.default_provider
    if config is not None:
        module_cfg = config.get(module)
        if isinstance(module_cfg, dict):
            provider_name = module_cfg.get("provider", provider_name)

    provider_def = module_config.providers.get(provider_name)
    if provider_def is None:
        return None

    supported = provider_def.capabilities.get(capability, False)
    if not supported:
        return None

    dispatch = provider_def.dispatch_specs.get(capability)
    if not isinstance(dispatch, dict) or not dispatch.get("target"):
        return None
    dispatch_kind = dispatch.get("kind")
    if not isinstance(dispatch_kind, str) or dispatch_kind not in SUPPORTED_DISPATCH_KINDS:
        return None

    verifier = provider_def.verifier_specs.get(capability)
    if not isinstance(verifier, dict) or not verifier.get("target"):
        return None

    result_contract = provider_def.result_contracts.get(capability)
    if not isinstance(result_contract, str) or not result_contract:
        return None

    return ResolvedProvider(
        module=module,
        provider=provider_name,
        capability=capability,
        dispatch_kind=dispatch_kind,
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
    """Resolve a provider dispatch and return blockers if anything fails."""
    if registry is None:
        try:
            registry = load_registry()
        except Exception as exc:
            return [make_blocker(
                reason="registry_load_failed",
                message=f"Failed to load provider registry: {exc}",
                recommended_action="Verify skills/_lib/provider_registry.yaml exists and is valid YAML",
            )]

    if config is None and repo_root is not None:
        config, config_blockers = load_consistent_provider_config(Path(repo_root))
        if config_blockers:
            return config_blockers

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

    provider_name = module_config.default_provider
    if config is not None:
        module_cfg = config.get(module)
        if isinstance(module_cfg, dict):
            provider_name = module_cfg.get("provider", provider_name)

    if not provider_name:
        blockers.append(make_blocker(
            reason="missing_provider",
            message=f"No provider configured for module {module!r} and no default registered",
            recommended_action=f"Set {module}.provider in {CONFIG_FILENAME} or add a default to the registry",
        ))
        return blockers

    provider_def = module_config.providers.get(provider_name)
    if provider_def is None:
        allowed = sorted(module_config.providers.keys())
        blockers.append(make_blocker(
            reason="unknown_provider",
            message=f"Provider {provider_name!r} not registered for module {module!r}. Allowed: {allowed}",
            recommended_action=f"Change {module}.provider in {CONFIG_FILENAME} to one of {allowed}",
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
            reason="missing_dispatch",
            message=f"Provider {provider_name!r} for module {module!r} has no dispatch mapping for capability {capability!r}",
            recommended_action=f"Add a dispatch mapping in the provider registry for {provider_name!r}.{capability}",
        ))
        return blockers

    dispatch_kind = dispatch.get("kind")
    if not isinstance(dispatch_kind, str) or dispatch_kind not in SUPPORTED_DISPATCH_KINDS:
        blockers.append(make_blocker(
            reason="unsupported_dispatch_kind",
            message=(
                f"Provider {provider_name!r} for module {module!r} uses unsupported dispatch kind "
                f"{dispatch_kind!r} for capability {capability!r}"
            ),
            recommended_action=f"Use one of the supported dispatch kinds: {sorted(SUPPORTED_DISPATCH_KINDS)}",
        ))
        return blockers

    verifier = provider_def.verifier_specs.get(capability)
    if not isinstance(verifier, dict) or not verifier.get("target"):
        blockers.append(make_blocker(
            reason="missing_verifier",
            message=f"Provider {provider_name!r} for module {module!r} has no verifier mapped for capability {capability!r}",
            recommended_action=f"Add a verifier mapping in the provider registry for {provider_name!r}.{capability}",
        ))
        return blockers

    result_contract = provider_def.result_contracts.get(capability)
    if not isinstance(result_contract, str) or not result_contract:
        blockers.append(make_blocker(
            reason="missing_result_contract",
            message=f"Provider {provider_name!r} for module {module!r} has no result_contract mapped for capability {capability!r}",
            recommended_action=f"Add a result_contract mapping in the provider registry for {provider_name!r}.{capability}",
        ))
        return blockers

    return []


def get_provider_config_value(config: Optional[Dict[str, Any]], module: str, key: str) -> Optional[str]:
    """Read a string config value from the provider config dict."""
    if config is None:
        return None
    section = config.get(module)
    if not isinstance(section, dict):
        return None
    val = section.get(key)
    if isinstance(val, str):
        return val
    return None
