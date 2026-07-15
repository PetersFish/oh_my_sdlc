#!/usr/bin/env python3
"""Aggregate agent setup: install (template sync) then activate (render model/variant).

Provides a single user-facing entrypoint that composes install_agents.py and
activate_agents_config.py in order.  Supports unified --check, --dry-run, and
--force modes.

Modes:
  (default)   Install canonical prompts (template sync), then activate config.
  --check     Report both template drift and activation drift.
  --dry-run   Preview install and activation actions without writing files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from agent_config_lib import (
    CONFIG_SUBDIR,
    MODEL_PROFILES_FILENAME,
    SKIP_NAMES,
    SKIP_SUFFIXES,
    get_target_config_path,
    load_model_profiles_config,
    resolve_effective_model,
    resolve_effective_variant,
    update_frontmatter,
)


INSTALL_SCRIPT = Path(__file__).resolve().parent / "install_agents.py"
ACTIVATE_SCRIPT = Path(__file__).resolve().parent / "activate_agents_config.py"

if not INSTALL_SCRIPT.is_file():
    print(f"ERROR: install script not found: {INSTALL_SCRIPT}", file=sys.stderr)
    sys.exit(1)
if not ACTIVATE_SCRIPT.is_file():
    print(f"ERROR: activate script not found: {ACTIVATE_SCRIPT}", file=sys.stderr)
    sys.exit(1)


def _global_target() -> Path:
    return Path.home() / ".config" / "opencode" / "agents"


def _canonical_source() -> Path:
    return (Path(__file__).resolve().parent / ".." / "agents").resolve()


def _canonical_config_template() -> Path:
    return _canonical_source() / CONFIG_SUBDIR / MODEL_PROFILES_FILENAME


def _canonical_agent_files() -> dict[str, Path]:
    source = _canonical_source()
    files: dict[str, Path] = {}
    if not source.is_dir():
        return files
    for entry in sorted(source.iterdir()):
        if entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith(SKIP_SUFFIXES):
            continue
        if entry.is_file() and entry.suffix == ".md":
            files[entry.name] = entry
    return files


def _run_script(script: Path, target: Path, extra_args: list[str]) -> tuple[int, str, str]:
    """Run a script with --target and capture output."""
    args = [
        sys.executable,
        str(script),
        "--target", str(target),
        *extra_args,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _preview_dry_run(target: Path, force: bool = False) -> int:
    """Preview install and activation effects without writing files."""
    canonical_files = _canonical_agent_files()
    if not canonical_files:
        print("[DRY-RUN] no canonical agent markdown files found")
        return 0

    existing_conflicts = [name for name in canonical_files if (target / name).exists()]
    if existing_conflicts and not force:
        print("[DRY-RUN] install would fail: target already contains agent files; re-run with --force to overwrite")
        for name in existing_conflicts:
            print(f"[DRY-RUN] existing conflict: {name}")
    else:
        for name in canonical_files:
            tgt_path = target / name
            action = "overwrite" if tgt_path.exists() else "install"
            print(f"[DRY-RUN] would install: {name} ({action})")

    target_config = get_target_config_path(target)
    config_path = target_config if target_config.is_file() else _canonical_config_template()
    if target_config.is_file():
        print(f"[DRY-RUN] target config already exists, preserved: {target_config}")
    else:
        print(f"[DRY-RUN] would initialize config template: {target_config}")

    if not config_path.is_file():
        print("[DRY-RUN] activation preview unavailable: no config template found")
        return 0

    config = load_model_profiles_config(config_path)
    agent_names = set(config.get("agents", {}).keys())

    for name, canonical_path in canonical_files.items():
        agent_name = canonical_path.stem
        if agent_name not in agent_names:
            continue

        source_path = target / name if (target / name).exists() else canonical_path
        original = source_path.read_text(encoding="utf-8")
        model = resolve_effective_model(agent_name, config)
        variant = resolve_effective_variant(agent_name, config)
        updated = update_frontmatter(original, model, variant)
        if updated != original:
            print(f"[DRY-RUN] would activate: {name} -> model={model} variant={variant}")

    return 0


def do_setup(target: Path, force: bool = False, dry_run: bool = False) -> int:
    """Run install then activate for a target.

    Returns 0 on success, non-zero on failure."""
    if dry_run:
        return _preview_dry_run(target, force=force)

    # Step 1: Template sync (install)
    # Always pass --install-only: setup_agents handles activation in step 2,
    # so the install_agents guardrail against bare CLI-target installs is
    # intentionally bypassed here.
    install_args = ["--install-only"]
    if force:
        install_args.append("--force")
    rc_install, stdout_install, stderr_install = _run_script(
        INSTALL_SCRIPT, target, install_args
    )
    if stdout_install:
        print(stdout_install)
    if stderr_install:
        print(stderr_install, file=sys.stderr)
    if rc_install != 0:
        print("ERROR: install step failed", file=sys.stderr)
        return rc_install

    # Step 2: Activation
    activate_args = []
    if dry_run:
        activate_args.append("--dry-run")
    rc_activate, stdout_activate, stderr_activate = _run_script(
        ACTIVATE_SCRIPT, target, activate_args
    )
    if stdout_activate:
        print(stdout_activate)
    if stderr_activate:
        print(stderr_activate, file=sys.stderr)

    if rc_activate != 0:
        print("ERROR: activation step failed", file=sys.stderr)

    return rc_activate


def do_check(target: Path, json_output: bool = False) -> int:
    """Run install --check and activate --check. Exit 1 if either reports drift.

    When ``json_output`` is True, emit a structured JSON report on stdout with
    concrete repository-relative stale agent target paths for each failing
    check, instead of only plain-text DRIFT lines.
    """
    if json_output:
        return _do_check_json(target)

    overall = 0

    # Template drift check
    rc_install, stdout_install, stderr_install = _run_script(
        INSTALL_SCRIPT, target, ["--check"]
    )
    if stdout_install:
        print(stdout_install)
    if stderr_install:
        print(stderr_install, file=sys.stderr)

    if rc_install != 0:
        print("--- template drift detected (install --check) ---")
        overall = 1

    # Activation drift check
    rc_activate, stdout_activate, stderr_activate = _run_script(
        ACTIVATE_SCRIPT, target, ["--check"]
    )
    if stdout_activate:
        print(stdout_activate)
    if stderr_activate:
        print(stderr_activate, file=sys.stderr)

    if rc_activate != 0:
        print("--- activation drift detected (activate --check) ---")
        overall = 1

    if overall == 0:
        print("OK: agents fully in sync")
    return overall


def _stale_template_paths(target: Path) -> list[str]:
    """Return repository-relative stale agent paths for template drift.

    Compares canonical agents/ against ``target`` using normalized prompt
    content (ignoring activation-managed fields).  Reports each stale target
    path as ``<target_rel>/<filename>``.
    """
    from agent_config_lib import (
        SKIP_NAMES,
        SKIP_SUFFIXES,
        normalized_prompt_compare,
    )

    source = _canonical_source()
    if not source.is_dir():
        return []

    stale: list[str] = []
    src_files: dict[str, str] = {}
    for entry in sorted(source.iterdir()):
        if entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith(SKIP_SUFFIXES):
            continue
        if entry.is_file() and entry.suffix == ".md":
            src_files[entry.name] = entry.read_text(encoding="utf-8")

    if not src_files:
        return []

    tgt_files: dict[str, str] = {}
    if target.is_dir():
        for entry in sorted(target.iterdir()):
            if entry.name in SKIP_NAMES:
                continue
            if entry.name.endswith(SKIP_SUFFIXES):
                continue
            if entry.is_file() and entry.suffix == ".md":
                tgt_files[entry.name] = entry.read_text(encoding="utf-8")

    for name, src_content in src_files.items():
        tgt_content = tgt_files.get(name)
        rel = f"{target.name}/{name}" if target.name else name
        if tgt_content is None:
            stale.append(rel)
        elif not normalized_prompt_compare(src_content, tgt_content):
            stale.append(rel)

    for name in tgt_files:
        if name not in src_files:
            rel = f"{target.name}/{name}" if target.name else name
            stale.append(rel)

    # Target config check
    config_path = get_target_config_path(target)
    if not config_path.is_file():
        stale.append(f"{target.name}/config/{MODEL_PROFILES_FILENAME}")

    return sorted(stale)


def _stale_activation_paths(target: Path) -> list[str]:
    """Return repository-relative stale agent paths for activation drift.

    Compares effective model/variant from target config against rendered
    frontmatter in each target agent markdown file.
    """
    config_path = get_target_config_path(target)
    if not config_path.is_file():
        return []

    try:
        config = load_model_profiles_config(config_path)
    except ValueError:
        return []

    agent_names = set(config.get("agents", {}).keys())
    if not agent_names:
        return []

    # Reuse the extraction helper from activate_agents_config.
    import importlib.util
    activate_path = Path(__file__).resolve().parent / "activate_agents_config.py"
    spec = importlib.util.spec_from_file_location(
        "_activate_for_check", str(activate_path)
    )
    activate_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(activate_mod)
    _extract = activate_mod._extract_model_variant_from_markdown

    stale: list[str] = []
    if not target.is_dir():
        return stale
    for entry in sorted(target.iterdir()):
        if entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith(SKIP_SUFFIXES):
            continue
        if not entry.is_file() or entry.suffix != ".md":
            continue
        stem = entry.stem
        if stem not in agent_names:
            continue
        try:
            expected_model = resolve_effective_model(stem, config)
            expected_variant = resolve_effective_variant(stem, config)
        except ValueError:
            rel = f"{target.name}/{entry.name}" if target.name else entry.name
            stale.append(rel)
            continue
        content = entry.read_text(encoding="utf-8")
        actual_model, actual_variant = _extract(content)
        if actual_model != expected_model or actual_variant != expected_variant:
            rel = f"{target.name}/{entry.name}" if target.name else entry.name
            stale.append(rel)

    return sorted(stale)


def _do_check_json(target: Path) -> int:
    """Structured JSON check report with concrete stale agent paths."""
    stale_template = _stale_template_paths(target)
    stale_activation = _stale_activation_paths(target)
    overall = 1 if (stale_template or stale_activation) else 0
    report = {
        "target": str(target),
        "stale_paths": sorted(set(stale_template) | set(stale_activation)),
        "template_drift_paths": stale_template,
        "activation_drift_paths": stale_activation,
        "status": "drift" if overall else "ok",
        "returncode": overall,
    }
    print(json.dumps(report, indent=2))
    return overall


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate agent setup: install (template sync) then activate (render model/variant)."
    )
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--target", default=None,
                              help="target agents directory")
    target_group.add_argument("--global", dest="global_install", action="store_true",
                              help="use ~/.config/opencode/agents/ (default)")
    parser.add_argument("--force", action="store_true",
                        help="force overwrite existing agent files during install")
    parser.add_argument("--check", action="store_true",
                        help="report template drift and activation drift, exit 1 on either")
    parser.add_argument("--json", action="store_true",
                        help="emit structured JSON report (use with --check)")
    parser.add_argument("--dry-run", action="store_true",
                        help="preview planned install and activation actions without writing files")
    args = parser.parse_args()

    if args.target:
        target = Path(args.target).resolve()
    else:
        target = _global_target()

    if args.check:
        return do_check(target, json_output=args.json)

    return do_setup(target, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
