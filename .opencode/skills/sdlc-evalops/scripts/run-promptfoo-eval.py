#!/usr/bin/env python3
"""Run Promptfoo eval for a target, writing reports to the repo.

Usage:
  export OPENCODE_GO_API_KEY=<key>
  python skills/sdlc-evalops/scripts/run-promptfoo-eval.py <target-id>

  Or run directly from auth.json:
  python skills/sdlc-evalops/scripts/run-promptfoo-eval.py <target-id> --from-auth

Chains:
  1. skills/sdlc-evalops/scripts/export-promptfoo.py <target-id>  (ensures exports fresh)
  2. promptfoo eval -c <config> -o <report-path> --max-concurrency 1 --no-cache
  3. Writes summary.md and failures.yaml

Reports land under .ai/evals/targets/<target-id>/reports/<run-id>/
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
from run_index import (
    load_run_index, save_run_index, get_git_baseline,
    get_changed_golden_files, find_last_full_run, find_latest_run,
    build_run_entry,
)
from case_selection import (
    collect_case_files, select_only_new, select_only_failed, build_case_status,
)
from promptfoo_shared import generate_cases_yaml

def generate_prompt_for_target(t_manifest: dict) -> str:
    source_paths = t_manifest.get("source_paths", [])
    target_id = t_manifest.get("target_id", "")
    target_type = t_manifest.get("target_type", "")
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

Provide only the assistant's final user-facing reply — one natural message as the user would see it. Do NOT output chain of thought, hidden reasoning, "Thinking:" text, or any other internal deliberation. Output the direct reply only.
"""


def generate_promptfoo_config(target_id: str, provider: dict,
                               grader: dict | None) -> str:
    import yaml as _yaml
    config = {
        "description": f"EvalOps target run for {target_id}",
        "prompts": ["file://prompt.md"],
        "providers": [provider],
        "tests": "cases.yaml",
    }
    if grader:
        config["defaultTest"] = {"options": {"provider": grader}}
    return _yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)


def write_run_scoped_promptfoo_files(run_dir: Path, selected_cases: list[dict],
                                     t_manifest: dict, provider: dict,
                                     grader: dict | None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_content = generate_prompt_for_target(t_manifest)
    cases_content = generate_cases_yaml(selected_cases, t_manifest)
    config_content = generate_promptfoo_config(
        t_manifest.get("target_id", ""), provider, grader
    )
    (run_dir / "prompt.md").write_text(prompt_content, encoding="utf-8")
    (run_dir / "cases.yaml").write_text(cases_content, encoding="utf-8")
    (run_dir / "promptfooconfig.yaml").write_text(config_content, encoding="utf-8")


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


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def run_export(target_id: str) -> int:
    export_script = Path(__file__).resolve().parent / "export-promptfoo.py"
    log(f"Running export: {export_script} {target_id}")
    result = subprocess.run(
        [sys.executable, str(export_script), target_id],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if result.stdout.strip():
        print(result.stdout.strip(), file=sys.stderr)
    if result.returncode != 0:
        error(f"Export failed (exit {result.returncode})")
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return result.returncode
    return 0


def generate_run_id(target_id: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{target_id}-{ts}"


def resolve_api_key(from_auth: bool = False) -> str:
    api_key = os.environ.get("OPENCODE_GO_API_KEY", "")
    if api_key:
        return api_key

    if from_auth:
        import json as _json
        auth_path = Path.home() / ".local" / "share" / "opencode" / "auth.json"
        if auth_path.is_file():
            auth_data = _json.loads(auth_path.read_text("utf-8"))
            key = auth_data.get("opencode-go", {}).get("key", "")
            if key:
                return key

    return ""


def resolve_target_workspace(target_id: str) -> Path:
    if not (EVALS_ROOT / "manifest.yaml").is_file():
        error(f"EvalOps manifest not found: {EVALS_ROOT / 'manifest.yaml'}")
        sys.exit(2)

    import yaml
    manifest = yaml.safe_load((EVALS_ROOT / "manifest.yaml").read_text("utf-8")) or {}
    for t in manifest.get("targets", []):
        if t.get("id") == target_id:
            return EVALS_ROOT / t["workspace"]
    error(f"Target '{target_id}' not found in global manifest")
    sys.exit(2)


def load_model_matrix() -> dict:
    mm_path = EVALS_ROOT / "model-matrix.yaml"
    if mm_path.is_file():
        return yaml.safe_load(mm_path.read_text("utf-8")) or {}
    return {}


def load_golden_cases(golden_dir: Path) -> list[dict]:
    cases = []
    if golden_dir.is_dir():
        for case_file in sorted(golden_dir.glob("*.yaml")):
            case = yaml.safe_load(case_file.read_text("utf-8")) or {}
            case["_file"] = str(case_file.name)
            cases.append(case)
    return cases


def run_promptfoo_eval(config_path: Path, output_path: Path,
                       max_concurrency: int = 1) -> int:
    log(f"Running: promptfoo eval -c {config_path} -o {output_path}")
    env = os.environ.copy()
    result = subprocess.run(
        [
            "promptfoo", "eval",
            "-c", str(config_path),
            "-o", str(output_path),
            "--max-concurrency", str(max_concurrency),
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=600,
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

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": err_count,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "failure_count": len(failures),
        "failures": failures,
        "cases": case_details,
    }


def write_summary_md(reports_dir: Path, target_id: str, run_id: str,
                     export_fresh: bool, parsed: dict, config_path: Path,
                     run_mode: str = "full", failure_source: str | None = None,
                     max_concurrency: int = 1) -> None:
    total = parsed.get("total", 0)
    passed = parsed.get("passed", 0)
    failed = parsed.get("failed", 0)
    errors = parsed.get("errors", 0)
    failures = parsed.get("failures", [])

    lines = [
        f"# Eval Run: {run_id}",
        "",
        f"**Target:** {target_id}",
        f"**Run ID:** {run_id}",
        f"**Run Mode:** {run_mode}",
    ]
    if failure_source:
        lines.append(f"**Failure Source:** {failure_source}")
    lines.extend([
        "",
        f"**Export Freshness:** {'pass' if export_fresh else 'stale'}",
        f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
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
        f"**Eval Command:** `OPENCODE_GO_API_KEY=<key> promptfoo eval -c "
        f"{config_path.as_posix()} "
        f"-o .ai/evals/targets/{target_id}/reports/{run_id}/promptfoo-output.json "
        f"--max-concurrency {max_concurrency} --no-cache`",
        "",
        f"**Report Path:** `.ai/evals/targets/{target_id}/reports/{run_id}/`",
        "",
    ])

    if failures:
        lines.append("## Failures")
        lines.append("")
        for f in failures:
            lines.append(f"- {f}")
        lines.append("")
    else:
        lines.append("All golden cases passed.")
        lines.append("")

    summary_path = reports_dir / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Wrote: {summary_path}")


def write_failures_yaml(reports_dir: Path, parsed: dict) -> None:
    import yaml
    failures = parsed.get("failures", [])
    cases = parsed.get("cases", [])

    failure_data = {
        "run_id": str(reports_dir.name),
        "failed_count": parsed.get("failed", 0),
        "error_count": parsed.get("errors", 0),
        "failures": [],
    }

    failed_cases = [c for c in cases if not c.get("passed")]
    for fc in failed_cases:
        failure_data["failures"].append({
            "input_preview": fc.get("input_preview", ""),
        })

    failures_path = reports_dir / "failures.yaml"
    failures_path.write_text(yaml.dump(failure_data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    log(f"Wrote: {failures_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Promptfoo eval and write reports to repo"
    )
    parser.add_argument("target_id", help="Target ID (e.g., skill.sdlc-orchestrator)")
    parser.add_argument("--from-auth", action="store_true",
                        help="Read OPENCODE_GO_API_KEY from ~/.local/share/opencode/auth.json")
    parser.add_argument("--only-new", action="store_true",
                        help="Run only golden cases changed since last full run")
    parser.add_argument("--only-failed", action="store_true",
                        help="Run only previously failed cases")
    parser.add_argument("--failed-from", choices=["latest", "full"],
                        help="Failure source for --only-failed: latest run or last full run")
    args = parser.parse_args()

    if args.only_failed and not args.failed_from:
        error("--only-failed requires --failed-from latest|full")
        sys.exit(2)

    api_key = resolve_api_key(from_auth=args.from_auth)
    if not api_key:
        error(
            "OPENCODE_GO_API_KEY is not set. "
            "Run: export OPENCODE_GO_API_KEY=<key> "
            "or use --from-auth to read from ~/.local/share/opencode/auth.json"
        )
        sys.exit(2)

    os.environ["OPENCODE_GO_API_KEY"] = api_key

    target_id = args.target_id
    workspace = resolve_target_workspace(target_id)

    model_matrix = load_model_matrix()
    run_policy = model_matrix.get("run_policy", {})
    max_concurrency = run_policy.get("max_concurrency", 1)

    reports_base = workspace / "reports"
    run_index_data = load_run_index(reports_base)
    if run_index_data.get("target_id") != target_id:
        run_index_data["target_id"] = target_id

    t_manifest = yaml.safe_load((workspace / "manifest.yaml").read_text("utf-8")) or {}
    golden_rel = t_manifest.get("canonical_case_directories", {}).get("golden", "cases/golden")
    golden_dir = workspace / golden_rel
    golden_cases = load_golden_cases(golden_dir)

    failure_source: str | None = None

    if args.only_failed:
        run_mode = "only-failed"
        failure_source = args.failed_from
        if not run_index_data.get("runs"):
            error("No run index found. Run a full eval first.")
            sys.exit(2)
        if args.failed_from == "latest":
            ref_run = find_latest_run(run_index_data["runs"])
        else:
            ref_run = find_last_full_run(run_index_data["runs"])
        if not ref_run:
            error("No qualifying run found in run index. Run a full eval first.")
            sys.exit(2)
        failed_ids = ref_run.get("failed_cases", [])
        if not failed_ids:
            log("No failed cases to retry. Exiting.")
            sys.exit(0)
        selected_cases = select_only_failed(golden_cases, failed_ids)
        if not selected_cases:
            log("Failed case ids no longer present in golden dir. Exiting.")
            sys.exit(0)
        log(f"Only-failed ({failure_source}): {len(selected_cases)} case(s) to retry")

    elif args.only_new:
        run_mode = "only-new"
        run_index_data = load_run_index(reports_base)
        if run_index_data.get("target_id") != target_id:
            run_index_data["target_id"] = target_id
        last_full = find_last_full_run(run_index_data.get("runs", []))
        if not last_full:
            error("No prior full run found in run index. Run a full eval first.")
            sys.exit(2)
        baseline = last_full.get("git_baseline")
        if not baseline:
            error("Last full run has no Git baseline. Run a full eval to record one.")
            sys.exit(2)
        changed_files = get_changed_golden_files(REPO_ROOT, baseline, golden_dir)
        if not changed_files:
            log("No changed golden case files since last full run. Exiting.")
            sys.exit(0)
        selected_cases = select_only_new(golden_cases, changed_files)
        if not selected_cases:
            log("Changed files have no matching golden cases. Exiting.")
            sys.exit(0)
        log(f"Only-new: {len(selected_cases)} case(s) changed since baseline {baseline[:8]}")
    else:
        run_mode = "full"
        selected_cases = golden_cases

    run_id = generate_run_id(target_id)
    reports_dir = reports_base / run_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    log(f"Reports dir: {reports_dir}")

    if run_mode == "full":
        export_exit = run_export(target_id)
        export_fresh = export_exit == 0
        if export_exit != 0 and export_exit != 5:
            error("Export failed; aborting eval")
            sys.exit(export_exit)
        config_path = workspace / "exports" / "promptfoo" / "promptfooconfig.yaml"
    else:
        export_fresh = True
        model_matrix = load_model_matrix()
        first_model = model_matrix.get("models", [{}])[0]
        provider = first_model.get("promptfoo")
        grader = first_model.get("grader")
        run_promptfoo_dir = reports_dir / "promptfoo"
        write_run_scoped_promptfoo_files(
            run_promptfoo_dir, selected_cases, t_manifest, provider, grader
        )
        config_path = run_promptfoo_dir / "promptfooconfig.yaml"

    output_path = reports_dir / "promptfoo-output.json"

    eval_exit = run_promptfoo_eval(config_path, output_path, max_concurrency=max_concurrency)
    if eval_exit != 0:
        log(f"promptfoo eval exited with code {eval_exit}")

    parsed = parse_promptfoo_output(output_path)
    if "error" in parsed:
        error(f"Cannot parse results: {parsed['error']}")
        sys.exit(1)

    write_summary_md(reports_dir, target_id, run_id, export_fresh, parsed,
                     config_path=config_path, run_mode=run_mode,
                     failure_source=failure_source, max_concurrency=max_concurrency)
    write_failures_yaml(reports_dir, parsed)

    passed = parsed.get("passed", 0)
    failed = parsed.get("failed", 0)
    errors = parsed.get("errors", 0)
    total = parsed.get("total", 0)

    # Build run index entry
    git_baseline = get_git_baseline(REPO_ROOT)
    case_details = parsed.get("cases", [])
    case_status, failed_case_ids = build_case_status(case_details, selected_cases)
    case_files = collect_case_files(selected_cases, golden_dir)

    entry = build_run_entry(
        run_id=run_id, mode=run_mode, git_baseline=git_baseline,
        case_files=case_files, case_status=case_status,
        failed_cases=failed_case_ids,
        report_path=str(reports_dir.relative_to(REPO_ROOT)),
        failure_source=failure_source,
    )
    run_index_data.setdefault("runs", []).append(entry)
    save_run_index(reports_base, run_index_data)

    log(f"\nResults: {passed}/{total} passed, {failed} failed, {errors} errors")
    print(f"Report: {reports_dir}")

    if failed > 0 or errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
