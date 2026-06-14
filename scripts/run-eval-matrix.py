#!/usr/bin/env python3
"""Run EvalOps targets across the configured model matrix.

Usage:
  export OPENCODE_GO_API_KEY=<key>
  python scripts/run-eval-matrix.py <target-id>
  python scripts/run-eval-matrix.py <target-id> --from-auth
  python scripts/run-eval-matrix.py <target-id> --dry-run
  python scripts/run-eval-matrix.py --all
  python scripts/run-eval-matrix.py --all --dry-run

Chains:
  1. Read .ai/evals/manifest.yaml and .ai/evals/model-matrix.yaml.
  2. For each target and for each model entry:
     a. Generate run-scoped Promptfoo config under reports/<matrix-run-id>/<model-name>/promptfoo/
     b. Execute promptfoo eval -c <config> -o <report-path> --max-concurrency 1 --no-cache
     c. Parse output and write per-model summary.md + failures.yaml
  3. Write aggregate matrix summary.md per target.

Canonical exports/ under each target workspace are NOT mutated.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALS_ROOT = REPO_ROOT / ".ai" / "evals"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_global_manifest() -> dict:
    manifest_path = EVALS_ROOT / "manifest.yaml"
    if not manifest_path.is_file():
        error(f"Global manifest not found: {manifest_path}")
        sys.exit(2)
    return load_yaml(manifest_path)


def load_model_matrix() -> dict:
    global_manifest = load_global_manifest()
    mm_path = EVALS_ROOT / global_manifest.get("model_matrix_path", "model-matrix.yaml")
    if not mm_path.is_file():
        error(f"Model matrix not found: {mm_path}")
        sys.exit(2)
    return load_yaml(mm_path)


def load_target_manifest(workspace_path: Path) -> dict:
    manifest_path = workspace_path / "manifest.yaml"
    if not manifest_path.is_file():
        error(f"Target manifest not found: {manifest_path}")
        sys.exit(2)
    return load_yaml(manifest_path)


def resolve_targets(global_manifest: dict, cli_target_id: str | None,
                    model_matrix: dict) -> list[dict]:
    all_targets = global_manifest.get("targets", [])
    if cli_target_id:
        for t in all_targets:
            if t.get("id") == cli_target_id:
                return [t]
        error(f"Target '{cli_target_id}' not found in global manifest")
        sys.exit(2)

    target_selection = model_matrix.get("target_selection", {})
    default_mode = target_selection.get("default", "all")
    filter_by_type = target_selection.get("filter_by_type", [])

    if default_mode == "all":
        selected = all_targets
    else:
        selected = [t for t in all_targets if t.get("id") in default_mode]

    if filter_by_type:
        selected = [t for t in selected if t.get("id", "").split(".", 1)[0] in filter_by_type]

    if not selected:
        error("No targets selected. Check target_selection in model-matrix.yaml")
        sys.exit(2)

    return selected


def resolve_model_entries(model_matrix: dict) -> list[dict]:
    models = model_matrix.get("models", [])
    if not models:
        error("No model entries in model-matrix.yaml")
        sys.exit(2)
    return models


def generate_matrix_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"matrix-{ts}"


def model_safe_name(model_entry: dict) -> str:
    cfg_name = model_entry.get("name", "")
    if cfg_name:
        safe = cfg_name.replace("/", "-").replace(" ", "-")
        return safe
    promptfoo_block = model_entry.get("promptfoo", {})
    return promptfoo_block.get("label", model_entry.get("model", "unknown")).replace("/", "-")


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

    return f"""You are evaluating the `{target_id}` {target_type}. Apply these {target_type} instructions as the source of truth before responding.

# {target_id} evaluation context

The assistant is acting as the `{target_id}`.

{source_block}

User input:

{{{{input}}}}

Respond as the assistant would after applying `{target_id}`.
"""


def map_case_to_promptfoo(case: dict, target_manifest: dict) -> dict | None:
    entry: dict = {"vars": {"input": case.get("input", "")}}
    assertions = []

    expected = case.get("expected", {})
    must_include = expected.get("must_include") or []
    must_not_include = expected.get("must_not_include") or []
    rubric = expected.get("rubric") or ""

    evaluators = case.get("evaluators", {})
    rule_based = evaluators.get("rule_based", {})
    llm_judge = evaluators.get("llm_judge", {})

    assertion_policy = target_manifest.get("assertion_policy", {})
    allow_llm_rubric = assertion_policy.get("allow_llm_rubric", False)

    for item in must_include:
        assertions.append({"type": "contains", "value": item.strip() if isinstance(item, str) else item})

    for item in must_not_include:
        assertions.append({"type": "not-contains", "value": item.strip() if isinstance(item, str) else item})

    rule_contains = rule_based.get("contains") or []
    for item in rule_contains:
        if item and item not in must_include:
            assertions.append({"type": "contains", "value": item.strip() if isinstance(item, str) else item})

    rule_not_contains = rule_based.get("not-contains") or []
    for item in rule_not_contains:
        if item and item not in must_not_include:
            assertions.append({"type": "not-contains", "value": item.strip() if isinstance(item, str) else item})

    if rubric and llm_judge.get("enabled", False):
        if not rubric.strip():
            error(f"Case '{case.get('id', '?')}' has llm-rubric enabled but no rubric text configured.")
            return None
        if not allow_llm_rubric:
            error(f"Case '{case.get('id', '?')}' has llm-rubric but target policy prohibits unconfigured llm-rubric assertions.")
            return None
        assertions.append({"type": "llm-rubric", "value": rubric})

    if not assertions:
        log(f"Warning: no assertions generated for case '{case.get('id', '?')}'")
        return None

    entry["assert"] = assertions
    return entry


def load_golden_cases(golden_dir: Path) -> list[dict]:
    cases = []
    if golden_dir.is_dir():
        for case_file in sorted(golden_dir.glob("*.yaml")):
            case = load_yaml(case_file)
            case["_file"] = str(case_file.name)
            cases.append(case)
    return cases


def generate_promptfoo_config(target_id: str, provider: dict,
                               grader: dict | None) -> str:
    config = {
        "description": f"EvalOps matrix export for {target_id}",
        "prompts": ["file://prompt.md"],
        "providers": [provider],
        "tests": "cases.yaml",
    }
    if grader:
        config["defaultTest"] = {"options": {"provider": grader}}
    return yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)


def generate_cases_yaml(golden_cases: list[dict], target_manifest: dict) -> str:
    entries = []
    comment = f"# Golden cases exported for {target_manifest.get('target_id', '')}\n"
    comment += f"# Source: {target_manifest.get('canonical_case_directories', {}).get('golden', 'cases/golden')}\n"
    comment += "# Generated by scripts/run-eval-matrix.py - DO NOT EDIT\n\n"
    lines = [comment]

    for case in golden_cases:
        entry = map_case_to_promptfoo(case, target_manifest)
        if entry is None:
            log(f"Skipped case: {case.get('id', case.get('_file', '?'))} (missing valid assertions)")
            continue
        lines.append(yaml.dump([entry], default_flow_style=False, allow_unicode=True, sort_keys=False))

    return "".join(lines)


def write_matrix_promptfoo_files(export_dir: Path, golden_cases: list[dict],
                                  target_manifest: dict, provider: dict,
                                  grader: dict | None) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    prompt_content = generate_prompt(target_manifest)
    cases_content = generate_cases_yaml(golden_cases, target_manifest)
    config_content = generate_promptfoo_config(
        target_manifest.get("target_id", ""), provider, grader
    )

    (export_dir / "prompt.md").write_text(prompt_content, encoding="utf-8")
    (export_dir / "cases.yaml").write_text(cases_content, encoding="utf-8")
    (export_dir / "promptfooconfig.yaml").write_text(config_content, encoding="utf-8")


def run_promptfoo_eval(config_path: Path, output_path: Path,
                       timeout_seconds: int = 600) -> int:
    log(f"Running: promptfoo eval -c {config_path} -o {output_path}")
    env = os.environ.copy()
    result = subprocess.run(
        [
            "promptfoo", "eval",
            "-c", str(config_path),
            "-o", str(output_path),
            "--max-concurrency", "1",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=timeout_seconds,
    )
    if result.stdout.strip():
        log(result.stdout.strip())
    if result.returncode != 0:
        error(f"promptfoo eval failed (exit {result.returncode})")
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def parse_promptfoo_output(output_path: Path) -> dict:
    if not output_path.is_file():
        error(f"Eval output not found: {output_path}")
        return {"error": "output file missing"}
    try:
        data = json.loads(output_path.read_text("utf-8"))
    except json.JSONDecodeError as e:
        error(f"Failed to parse eval output: {e}")
        return {"error": str(e)}

    results = data.get("results", {})
    stats = results.get("stats", {})
    failures = results.get("failures", [])
    eval_results = results.get("results", [])

    case_details = []
    for r in eval_results:
        outcome = r.get("success", r.get("pass", False))
        grading_result = r.get("gradingResult", {})
        assertion_results = grading_result.get("componentResults", [])
        detail = {
            "input_preview": r.get("prompt", {}).get("raw", "")[:200],
            "passed": outcome,
            "assertions": [
                {"pass": a.get("pass"), "reason": a.get("reason", "")[:200]}
                for a in assertion_results
            ],
        }
        case_details.append(detail)

    total = len(eval_results)
    passed = stats.get("successes", 0)
    failed = stats.get("failures", 0)
    err_count = stats.get("errors", 0)

    observed_provider = None
    observed_model = None
    if eval_results:
        first = eval_results[0]
        provider_info = first.get("provider", {})
        if isinstance(provider_info, dict):
            observed_provider = provider_info.get("id") or provider_info.get("label")
        p_label = first.get("prompt", {}).get("provider")
        if p_label:
            observed_model = p_label

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": err_count,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "failure_count": len(failures),
        "failures": failures,
        "cases": case_details,
        "observed_provider": observed_provider,
        "observed_model": observed_model,
    }


def write_model_summary(reports_dir: Path, target_id: str, model_entry: dict,
                         model_name: str, parsed: dict) -> None:
    total = parsed.get("total", 0)
    passed = parsed.get("passed", 0)
    failed = parsed.get("failed", 0)
    errors = parsed.get("errors", 0)
    failures = parsed.get("failures", [])

    cfg_name = model_entry.get("name", "?")
    cfg_provider = model_entry.get("provider", "?")
    cfg_model = model_entry.get("model", "?")
    cfg_pf_id = model_entry.get("promptfoo", {}).get("id", "?")
    observed_provider = parsed.get("observed_provider", "?")
    observed_model = parsed.get("observed_model", "?")

    lines = [
        f"# Matrix Model Run: {model_name}",
        "",
        f"**Target:** {target_id}",
        f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Configured Model",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Name | {cfg_name} |",
        f"| Provider | {cfg_provider} |",
        f"| Model | {cfg_model} |",
        f"| Promptfoo ID | {cfg_pf_id} |",
        "",
        "## Observed (from Promptfoo output)",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Provider | {observed_provider} |",
        f"| Model | {observed_model} |",
        "",
        "## Results",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Cases | {total} |",
        f"| Passed | {passed} |",
        f"| Failed | {failed} |",
        f"| Errors | {errors} |",
        f"| Pass Rate | {parsed.get('pass_rate', '?')}% |",
        "",
    ]

    if failures:
        lines.append("## Failures")
        lines.append("")
        for f in failures:
            lines.append(f"- {f}")
        lines.append("")
    else:
        lines.append("All golden cases passed.")
        lines.append("")

    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Wrote: {reports_dir / 'summary.md'}")


def write_model_failures(reports_dir: Path, parsed: dict) -> None:
    cases = parsed.get("cases", [])
    failure_data = {
        "failed_count": parsed.get("failed", 0),
        "error_count": parsed.get("errors", 0),
        "failures": [],
    }
    failed_cases = [c for c in cases if not c.get("passed")]
    for fc in failed_cases:
        failure_data["failures"].append({
            "input_preview": fc.get("input_preview", ""),
        })

    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "failures.yaml"
    path.write_text(
        yaml.dump(failure_data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    log(f"Wrote: {path}")


def write_aggregate_summary(target_reports_dir: Path, target_id: str,
                              run_id: str,
                              model_results: list[dict]) -> None:
    target_reports_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Matrix Eval Run: {run_id}",
        "",
        f"**Target:** {target_id}",
        f"**Run ID:** {run_id}",
        f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Results by Model",
        "",
        "| Model | Total | Passed | Failed | Errors | Pass Rate |",
        "|-------|-------|--------|--------|--------|-----------|",
    ]

    overall_total = 0
    overall_passed = 0
    overall_failed = 0
    overall_errors = 0

    for mr in model_results:
        parsed = mr.get("parsed", {})
        model_name = mr.get("model_name", "?")
        total = parsed.get("total", 0)
        passed = parsed.get("passed", 0)
        failed = parsed.get("failed", 0)
        errors = parsed.get("errors", 0)
        pass_rate = parsed.get("pass_rate", 0)

        overall_total += total
        overall_passed += passed
        overall_failed += failed
        overall_errors += errors

        lines.append(
            f"| {model_name} | {total} | {passed} | {failed} | {errors} | {pass_rate}% |"
        )

    overall_pass_rate = round(overall_passed / overall_total * 100, 1) if overall_total > 0 else 0
    lines.extend([
        "",
        f"**Overall:** {overall_total} total, {overall_passed} passed, {overall_failed} failed, {overall_errors} errors ({overall_pass_rate}%)",
        "",
        "## Per-Model Reports",
        "",
    ])
    for mr in model_results:
        model_name = mr.get("model_name", "?")
        lines.append(
            f"- `{mr.get('report_dir', '?')}/` — config: {mr.get('cfg_name', '?')}, observed: {mr.get('observed_provider', '?')}"
        )

    (target_reports_dir / "summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    log(f"Wrote aggregate summary: {target_reports_dir / 'summary.md'}")


def resolve_api_key(from_auth: bool = False) -> str:
    api_key = os.environ.get("OPENCODE_GO_API_KEY", "")
    if api_key:
        return api_key
    if from_auth:
        auth_path = Path.home() / ".local" / "share" / "opencode" / "auth.json"
        if auth_path.is_file():
            auth_data = json.loads(auth_path.read_text("utf-8"))
            key = auth_data.get("opencode-go", {}).get("key", "")
            if key:
                return key
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run EvalOps targets across the configured model matrix"
    )
    parser.add_argument(
        "target_id", nargs="?", default=None,
        help="Target ID (e.g., skill.sdlc-orchestrator). Omit with --all to run all targets."
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all registered targets (from target_selection in model-matrix.yaml)"
    )
    parser.add_argument(
        "--from-auth", action="store_true",
        help="Read OPENCODE_GO_API_KEY from ~/.local/share/opencode/auth.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate configs and print plan without executing promptfoo eval"
    )
    args = parser.parse_args()

    if not args.target_id and not args.all:
        error("Specify a <target-id> or use --all to run all registered targets.")
        sys.exit(2)

    api_key = resolve_api_key(from_auth=args.from_auth)
    if not api_key and not args.dry_run:
        error(
            "OPENCODE_GO_API_KEY is not set. "
            "Run: export OPENCODE_GO_API_KEY=<key> "
            "or use --from-auth to read from ~/.local/share/opencode/auth.json\n"
            "Or use --dry-run to inspect the matrix plan without running eval."
        )
        sys.exit(2)
    if api_key:
        os.environ["OPENCODE_GO_API_KEY"] = api_key

    global_manifest = load_global_manifest()
    model_matrix = load_model_matrix()
    targets = resolve_targets(global_manifest, args.target_id, model_matrix)
    model_entries = resolve_model_entries(model_matrix)
    run_policy = model_matrix.get("run_policy", {})
    fail_fast = run_policy.get("fail_fast", False)
    retry_count = run_policy.get("retry_count", 0)
    timeout_seconds = run_policy.get("timeout_seconds", 300)

    matrix_run_id = generate_matrix_run_id()

    log(f"Matrix Run ID: {matrix_run_id}")
    log(f"Targets: {len(targets)}")
    log(f"Models: {len(model_entries)}")
    log(f"Fail Fast: {fail_fast}")

    if args.dry_run:
        log("Dry-run mode: configs will be generated but no eval executed.")
        for target in targets:
            target_id = target["id"]
            workspace = EVALS_ROOT / target["workspace"]
            t_manifest = load_target_manifest(workspace)
            golden_dir = workspace / t_manifest.get(
                "canonical_case_directories", {}
            ).get("golden", "cases/golden")
            golden_cases = load_golden_cases(golden_dir)
            log(f"  Target: {target_id} ({len(golden_cases)} golden cases)")
            for model_entry in model_entries:
                model_name = model_safe_name(model_entry)
                promptfoo_block = model_entry.get("promptfoo", {})
                grader_block = model_entry.get("grader")
                log(f"    Model: {model_name} (provider: {promptfoo_block.get('id', '?')})")
        log("Dry-run complete. No evals executed.")
        return

    any_failure = False

    for target in targets:
        target_id = target["id"]
        workspace = EVALS_ROOT / target["workspace"]
        t_manifest = load_target_manifest(workspace)
        golden_dir = workspace / t_manifest.get(
            "canonical_case_directories", {}
        ).get("golden", "cases/golden")
        golden_cases = load_golden_cases(golden_dir)

        if not golden_cases:
            error(f"No golden cases found for target '{target_id}' at {golden_dir}")
            any_failure = True
            continue

        target_reports_dir = workspace / "reports" / matrix_run_id
        log(f"\nTarget: {target_id} ({len(golden_cases)} golden cases)")
        log(f"Reports: {target_reports_dir}")

        model_results = []

        for model_entry in model_entries:
            model_name = model_safe_name(model_entry)
            promptfoo_block = model_entry.get("promptfoo")
            grader_block = model_entry.get("grader")

            if not promptfoo_block:
                error(f"Model entry '{model_entry.get('name', '?')}' has no promptfoo config")
                any_failure = True
                if fail_fast:
                    sys.exit(2)
                model_results.append({
                    "model_name": model_name,
                    "cfg_name": model_entry.get("name", "?"),
                    "observed_provider": "?",
                    "report_dir": str(target_reports_dir / model_name),
                    "parsed": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "error": "no promptfoo config"},
                })
                continue

            model_export_dir = target_reports_dir / model_name / "promptfoo"
            log(f"\n  Model: {model_name} ({promptfoo_block.get('id', '?')})")

            write_matrix_promptfoo_files(
                model_export_dir, golden_cases, t_manifest,
                promptfoo_block, grader_block,
            )

            model_output_path = model_export_dir.parent / "promptfoo-output.json"

            exit_code = 1
            for attempt in range(retry_count + 1):
                if attempt > 0:
                    log(f"  Retry {attempt}/{retry_count}...")
                exit_code = run_promptfoo_eval(
                    model_export_dir / "promptfooconfig.yaml",
                    model_output_path,
                    timeout_seconds=timeout_seconds,
                )
                if exit_code == 0:
                    break

            model_report_dir = model_export_dir.parent
            parsed = parse_promptfoo_output(model_output_path)
            write_model_summary(model_report_dir, target_id, model_entry, model_name, parsed)
            write_model_failures(model_report_dir, parsed)

            failed_count = parsed.get("failed", 0)
            error_count = parsed.get("errors", 0)
            status = "FAIL" if (exit_code != 0 or failed_count > 0 or error_count > 0) else "PASS"
            log(
                f"  {status}: {parsed.get('passed', 0)}/{parsed.get('total', 0)} passed, "
                f"{failed_count} failed, {error_count} errors"
            )

            model_results.append({
                "model_name": model_name,
                "cfg_name": model_entry.get("name", "?"),
                "observed_provider": parsed.get("observed_provider", "?"),
                "report_dir": str(model_report_dir),
                "parsed": parsed,
            })

            if exit_code != 0 or failed_count > 0 or error_count > 0:
                any_failure = True
                if fail_fast:
                    log("fail_fast enabled, stopping remaining model runs.")
                    break

        write_aggregate_summary(target_reports_dir, target_id, matrix_run_id, model_results)

    if any_failure:
        log("\nMatrix run completed with failures.")
        sys.exit(1)

    log("\nMatrix run completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
