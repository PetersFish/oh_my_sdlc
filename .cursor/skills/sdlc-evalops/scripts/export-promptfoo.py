#!/usr/bin/env python3
"""Generate Promptfoo export files from canonical golden cases for a target.

Usage:
  python skills/sdlc-evalops/scripts/export-promptfoo.py <target-id>
  python skills/sdlc-evalops/scripts/export-promptfoo.py <target-id> --check
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

from promptfoo_shared import generate_cases_yaml

# Supported assertion types: contains, not-contains, llm-rubric.

def find_repo_root() -> Path:
    p = Path.cwd().resolve()
    while True:
        if (p / ".ai" / "evals" / "manifest.yaml").is_file():
            return p
        if p.parent == p:
            break
        p = p.parent
    return Path.cwd().resolve()

REPO_ROOT = find_repo_root()
EVALS_ROOT = REPO_ROOT / ".ai" / "evals"
EVALS_MANIFEST = EVALS_ROOT / "manifest.yaml"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_global_manifest() -> dict:
    if not EVALS_MANIFEST.is_file():
        error(f"Global manifest not found: {EVALS_MANIFEST}")
        sys.exit(2)
    return load_yaml(EVALS_MANIFEST)


def resolve_target(global_manifest: dict, target_id: str) -> dict:
    targets = global_manifest.get("targets", [])
    for t in targets:
        if t.get("id") == target_id:
            return t
    error(f"Target '{target_id}' not found in global manifest")
    sys.exit(2)


def load_target_manifest(workspace_path: Path) -> dict:
    manifest_path = workspace_path / "manifest.yaml"
    if not manifest_path.is_file():
        error(f"Target manifest not found: {manifest_path}")
        sys.exit(2)
    return load_yaml(manifest_path)


def load_model_matrix() -> dict:
    global_manifest = load_global_manifest()
    mm_path = EVALS_ROOT / global_manifest.get("model_matrix_path", "model-matrix.yaml")
    if not mm_path.is_file():
        error(f"Model matrix not found: {mm_path}")
        sys.exit(2)
    return load_yaml(mm_path)


def resolve_default_provider(model_matrix: dict) -> dict:
    models = model_matrix.get("models", [])
    if not models:
        error("No models defined in model-matrix.yaml")
        sys.exit(2)
    default_model = models[0]
    promptfoo_block = default_model.get("promptfoo")
    if not promptfoo_block:
        error(f"Model '{default_model.get('name', '?')}' has no promptfoo config in model-matrix.yaml")
        sys.exit(2)
    return promptfoo_block


def resolve_grader(model_matrix: dict) -> dict | None:
    models = model_matrix.get("models", [])
    if not models:
        return None
    return models[0].get("grader")


def load_golden_cases(golden_dir: Path) -> list[dict]:
    cases = []
    if golden_dir.is_dir():
        for case_file in sorted(golden_dir.glob("*.yaml")):
            case = load_yaml(case_file)
            case["_file"] = str(case_file.name)
            cases.append(case)
    return cases


def generate_prompt(target_manifest: dict) -> str:
    source_paths = target_manifest.get("source_paths", [])
    target_id = target_manifest.get("target_id", "")
    target_type = target_manifest.get("target_type", "")

    source_lines = []
    for sp in source_paths:
        src_path = REPO_ROOT / sp
        if src_path.is_file():
            source_lines.append(f"# Source: {sp}\n")
            source_lines.append(src_path.read_text(encoding="utf-8"))
            source_lines.append("\n")
        else:
            log(f"Warning: source file not found: {sp}")

    source_block = "".join(source_lines) if source_lines else ""

    prompt = f"""You are evaluating the `{target_id}` {target_type}. Apply these {target_type} instructions as the source of truth before responding.

# {target_id} evaluation context

The assistant is acting as the `{target_id}`.

{source_block}

User input:

{{{{input}}}}

Provide only the assistant's final user-facing reply — one natural message as the user would see it. Do NOT output chain of thought, hidden reasoning, "Thinking:" text, or any other internal deliberation. Output the direct reply only.
"""
    return prompt


def generate_promptfoo_config(target_manifest: dict, provider: dict, grader: dict | None) -> str:
    target_id = target_manifest.get("target_id", "")
    config = {
        "description": f"EvalOps export for {target_id}",
        "prompts": ["file://prompt.md"],
        "providers": [provider],
        "tests": "cases.yaml",
    }
    if grader:
        config["defaultTest"] = {
            "options": {
                "provider": grader,
            }
        }
    return yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)


def validate_no_global_assertions(config: dict) -> list[str]:
    errors = []
    default_asserts = config.get("defaultTest", {}).get("assert", [])
    if default_asserts:
        errors.append(
            "Promptfoo config contains global defaultTest.assert. "
            "Assertions must be per-case, not global."
        )
    return errors


def validate_no_unconfigured_llm_rubric(cases_content: str, target_manifest: dict) -> list[str]:
    errors = []
    cases = yaml.safe_load(cases_content)
    if not isinstance(cases, list):
        return errors
    for case in cases:
        for assertion in case.get("assert", []):
            if assertion.get("type") == "llm-rubric":
                if not assertion.get("value", "").strip():
                    errors.append(
                        "Unconfigured llm-rubric assertion: missing rubric text."
                    )
    return errors


def write_if_changed(path: Path, content: str) -> bool:
    """Write content to path. Returns True if written, False if unchanged."""
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def compute_freshness_key(target_manifest: dict, workspace_path: Path) -> str:
    parts = []

    golden_dir = workspace_path / target_manifest.get(
        "canonical_case_directories", {}
    ).get("golden", "cases/golden")
    if golden_dir.is_dir():
        for cf in sorted(golden_dir.glob("*.yaml")):
            parts.append(digest_file(cf))

    for sp in target_manifest.get("source_paths", []):
        src_path = REPO_ROOT / sp
        if src_path.is_file():
            parts.append(digest_file(src_path))

    parts.append(digest_file(workspace_path / "manifest.yaml"))

    parts.append(digest_file(workspace_path / "coverage.yaml"))

    mm_path = EVALS_ROOT / "model-matrix.yaml"
    if mm_path.is_file():
        parts.append(digest_file(mm_path))

    return hashlib.sha256("".join(parts).encode()).hexdigest()


def run_export(target_id: str, check_mode: bool = False) -> int:
    global_manifest = load_global_manifest()
    target_entry = resolve_target(global_manifest, target_id)
    workspace_path = EVALS_ROOT / target_entry["workspace"]
    target_manifest = load_target_manifest(workspace_path)
    model_matrix = load_model_matrix()
    provider = resolve_default_provider(model_matrix)
    grader = resolve_grader(model_matrix)

    golden_cases_dir = workspace_path / target_manifest.get(
        "canonical_case_directories", {}
    ).get("golden", "cases/golden")

    export_dir = workspace_path / target_manifest.get(
        "promptfoo_export_outputs", {}
    ).get("directory", "exports/promptfoo")

    if not golden_cases_dir.is_dir() or not list(golden_cases_dir.glob("*.yaml")):
        error(f"No golden cases found in: {golden_cases_dir}")
        return 1

    log(f"Target: {target_id}")
    log(f"Golden cases: {golden_cases_dir}")
    log(f"Export dir: {export_dir}")

    golden_cases = load_golden_cases(golden_cases_dir)
    log(f"Loaded {len(golden_cases)} golden cases")

    prompt_content = generate_prompt(target_manifest)
    cases_content = generate_cases_yaml(golden_cases, target_manifest)
    config_content = generate_promptfoo_config(target_manifest, provider, grader)

    config_dict = yaml.safe_load(config_content)
    validation_errors = validate_no_global_assertions(config_dict)
    validation_errors.extend(validate_no_unconfigured_llm_rubric(cases_content, target_manifest))

    if validation_errors:
        for e in validation_errors:
            error(e)
        return 1

    if check_mode:
        freshness_key = compute_freshness_key(target_manifest, workspace_path)

        if not export_dir.is_dir():
            error(f"Export directory '{export_dir}' is missing")
            return 3

        prompt_path = export_dir / "prompt.md"
        cases_path = export_dir / "cases.yaml"
        config_path = export_dir / "promptfooconfig.yaml"

        missing = []
        for p in [prompt_path, cases_path, config_path]:
            if not p.is_file():
                missing.append(str(p.relative_to(workspace_path)))

        if missing:
            error(f"Missing export files: {', '.join(missing)}")
            return 4

        prompt_differs = prompt_path.read_text(encoding="utf-8") != prompt_content
        cases_differs = cases_path.read_text(encoding="utf-8") != cases_content
        config_differs = config_path.read_text(encoding="utf-8") != config_content

        stale = []
        if prompt_differs:
            stale.append("prompt.md")
        if cases_differs:
            stale.append("cases.yaml")
        if config_differs:
            stale.append("promptfooconfig.yaml")

        if stale:
            error(f"Stale export files: {', '.join(stale)}")
            return 5

        log("Freshness check passed")
        return 0

    prompt_path = export_dir / "prompt.md"
    cases_path = export_dir / "cases.yaml"
    config_path = export_dir / "promptfooconfig.yaml"

    changed = []
    if write_if_changed(prompt_path, prompt_content):
        changed.append("prompt.md")
    if write_if_changed(cases_path, cases_content):
        changed.append("cases.yaml")
    if write_if_changed(config_path, config_content):
        changed.append("promptfooconfig.yaml")

    if changed:
        log(f"Updated: {', '.join(changed)}")
    else:
        log("Exports already up to date")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Promptfoo export from golden cases")
    parser.add_argument("target_id", help="Target ID (e.g., skill.sdlc-orchestrator)")
    parser.add_argument("--check", action="store_true",
                        help="Check freshness without rewriting files")
    args = parser.parse_args()

    sys.exit(run_export(args.target_id, check_mode=args.check))


if __name__ == "__main__":
    main()
