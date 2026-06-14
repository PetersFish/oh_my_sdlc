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


def run_promptfoo_eval(config_path: Path, output_path: Path) -> int:
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
                     export_fresh: bool, parsed: dict) -> None:
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
        f".ai/evals/targets/{target_id}/exports/promptfoo/promptfooconfig.yaml "
        f"-o .ai/evals/targets/{target_id}/reports/{run_id}/promptfoo-output.json "
        f"--max-concurrency 1 --no-cache`",
        "",
        f"**Report Path:** `.ai/evals/targets/{target_id}/reports/{run_id}/`",
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
    args = parser.parse_args()

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

    export_exit = run_export(target_id)
    export_fresh = export_exit == 0
    if export_exit != 0 and export_exit != 5:  # 5 = stale exports
        error("Export failed; aborting eval")
        sys.exit(export_exit)

    run_id = generate_run_id(target_id)
    reports_dir = workspace / "reports" / run_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    log(f"Reports dir: {reports_dir}")

    config_path = workspace / "exports" / "promptfoo" / "promptfooconfig.yaml"
    output_path = reports_dir / "promptfoo-output.json"

    eval_exit = run_promptfoo_eval(config_path, output_path)
    if eval_exit != 0:
        error(f"promptfoo eval failed (exit {eval_exit})")
        sys.exit(eval_exit)

    parsed = parse_promptfoo_output(output_path)
    if "error" in parsed:
        error(f"Cannot parse results: {parsed['error']}")
        sys.exit(1)

    write_summary_md(reports_dir, target_id, run_id, export_fresh, parsed)
    write_failures_yaml(reports_dir, parsed)

    passed = parsed.get("passed", 0)
    failed = parsed.get("failed", 0)
    errors = parsed.get("errors", 0)
    total = parsed.get("total", 0)

    log(f"\nResults: {passed}/{total} passed, {failed} failed, {errors} errors")
    print(f"Report: {reports_dir}")

    if failed > 0 or errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
