#!/usr/bin/env python3
"""Aggregate derived-artifact synchronization entrypoint.

Composes existing repository scripts behind a single check/fix contract:

  --check   read-only verification of workflow templates, distributed workflow
            templates, project-level agent copies, and canonical skill
            distribution.
  --fix     apply synchronization: sync live -> canonical workflow templates,
            distribute to project-level workflow template copies, force-install
            + activate agents in all project-level targets, and re-install
            every canonical skill to .opencode/, .claude/, and .cursor/.
  --json    emit a structured report instead of plain text.

The first version intentionally excludes .ai/memory/, EvalOps exports,
research artifacts, and other ephemeral runtime outputs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SYNC_TEMPLATES = REPO_ROOT / "skills" / "sdlc-project-bootstrap" / "scripts" / "sync_templates.py"
SETUP_AGENTS = REPO_ROOT / "scripts" / "setup_agents.py"
CHECK_SKILLS = REPO_ROOT / "skills" / "meta-skill-lifecycle-governance" / "scripts" / "check_skill_distribution.py"
INSTALL_SKILL = REPO_ROOT / "skills" / "meta-skill-lifecycle-governance" / "scripts" / "install_skill.py"

AGENT_TARGETS = (
    ".opencode/agents",
    ".claude/agents",
    ".cursor/agents",
)

SKILL_TARGETS = (
    ".opencode/skills",
    ".claude/skills",
    ".cursor/skills",
)


def _cmd(args: list[str]) -> dict:
    proc = subprocess.run(args, capture_output=True, text=True)
    return {
        "args": args,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _check_suites(root: Path) -> list[dict]:
    suites: list[dict] = []
    suites.append({
        "name": "workflow_templates",
        "command": [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--check"],
    })
    suites.append({
        "name": "workflow_distributed",
        "command": [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--check-distributed"],
    })
    for target in AGENT_TARGETS:
        suites.append({
            "name": f"agents_{target.split('/')[0]}",
            "command": [sys.executable, str(SETUP_AGENTS), "--target", str(root / target), "--check"],
        })
    suites.append({
        "name": "skills",
        "command": [sys.executable, str(CHECK_SKILLS), "--root", str(root)],
    })
    return suites


def _fix_steps(root: Path) -> list[dict]:
    steps: list[dict] = []
    # 1. Sync live workflow -> canonical template
    steps.append({
        "name": "workflow_templates_sync",
        "command": [sys.executable, str(SYNC_TEMPLATES), "--root", str(root)],
    })
    # 2. Distribute canonical template to all project-level copies
    steps.append({
        "name": "workflow_templates_distribute",
        "command": [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--distribute"],
    })
    # 3. Force-install + activate agents in every project-level target
    for target in AGENT_TARGETS:
        steps.append({
            "name": f"agents_{target.split('/')[0]}_force",
            "command": [sys.executable, str(SETUP_AGENTS), "--target", str(root / target), "--force"],
        })
    # 4. Re-install each canonical skill to every project-level target
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            skill_name = skill_dir.name
            for target in SKILL_TARGETS:
                steps.append({
                    "name": f"skill_{skill_name}_{target.split('/')[0]}",
                    "command": [
                        sys.executable, str(INSTALL_SKILL),
                        "--source-repo", str(root),
                        "--skill-name", skill_name,
                        "--source-ref", "HEAD",
                        "--target", str(root / target / skill_name),
                        "--status", "stable",
                    ],
                })
    return steps


def run_aggregate(root: str | os.PathLike, mode: str, json_output: bool = False) -> tuple[int, dict | None]:
    """Run the aggregate sync in check or fix mode.

    Returns (returncode, report_or_none). When json_output is True, returns a
    structured report dict. Otherwise prints plain text to stdout.
    """
    root_path = Path(root).resolve()
    if mode == "check":
        suites = _check_suites(root_path)
    elif mode == "fix":
        suites = _fix_steps(root_path)
    else:
        raise ValueError(f"unknown mode: {mode!r}")

    results = []
    overall_rc = 0
    for suite in suites:
        result = _cmd(suite["command"])
        results.append({
            "name": suite["name"],
            "command": suite["command"],
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        })
        if result["returncode"] != 0:
            overall_rc = 1

    report = {
        "mode": mode,
        "status": "ok" if overall_rc == 0 else "drift",
        "returncode": overall_rc,
        "suites": results,
    }

    if json_output:
        return overall_rc, report

    if overall_rc == 0:
        print(f"OK: all {len(results)} {mode} suites in sync")
    else:
        print(f"DRIFT: {mode} reported failures in {sum(1 for r in results if r['returncode'] != 0)} of {len(results)} suites")
        for r in results:
            if r["returncode"] != 0:
                print(f"  FAIL {r['name']}: rc={r['returncode']}")
                if r["stdout"].strip():
                    print(r["stdout"].strip())
                if r["stderr"].strip():
                    print(r["stderr"].strip(), file=sys.stderr)
    return overall_rc, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate derived-artifact sync entrypoint."
    )
    parser.add_argument("--root", default=".", help="repository root path")
    parser.add_argument("--check", action="store_true", help="read-only verification")
    parser.add_argument("--fix", action="store_true", help="apply synchronization")
    parser.add_argument("--json", action="store_true", help="emit structured JSON report")
    args = parser.parse_args()

    if args.check and args.fix:
        print("ERROR: --check and --fix are mutually exclusive", file=sys.stderr)
        return 2
    if not args.check and not args.fix:
        print("ERROR: must specify --check or --fix", file=sys.stderr)
        return 2

    mode = "check" if args.check else "fix"
    rc, report = run_aggregate(args.root, mode=mode, json_output=args.json)
    if args.json and report is not None:
        print(json.dumps(report, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())