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

Incremental mode:

  --changed-files-from-git   classify the current Git worktree change set and
                             run only the affected sync/check suites.
  --changed-file <path>      repeatable manual changed-file input.
  --full                     explicit full mode alias (default when no
                             changed-file options are given).

When incremental mode classifies changes as docs/tests/memory-only, no
subprocess suites run and the report scope is `skipped`. When sync-rule
files change, incremental mode falls back to full behavior.
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

# Governed live workflow files that trigger workflow template sync/distribution.
GOVERNED_WORKFLOW_FILES = {
    ".ai/workflows/scripts/workflow.py",
    ".ai/workflows/definitions/sdlc-main.yaml",
}

# Sync-rule files that force full mode in incremental execution.
SYNC_RULE_FILES = {
    "scripts/sync_derived_artifacts.py",
    "scripts/setup_agents.py",
    "scripts/install_agents.py",
    "scripts/activate_agents_config.py",
    "skills/meta-skill-lifecycle-governance/scripts/install_skill.py",
    "skills/meta-skill-lifecycle-governance/scripts/check_skill_distribution.py",
    "skills/sdlc-project-bootstrap/scripts/sync_templates.py",
}


class Affected:
    """Affected-domain classification result for a change set."""

    def __init__(
        self,
        workflows: bool = False,
        agents: bool = False,
        skills: set[str] | None = None,
        full: bool = False,
        skipped_paths: list[str] | None = None,
        reason: str | None = None,
    ) -> None:
        self.workflows = workflows
        self.agents = agents
        self.skills = skills if skills is not None else set()
        self.full = full
        self.skipped_paths = skipped_paths if skipped_paths is not None else []
        self.reason = reason

    def to_report(self) -> dict:
        return {
            "workflows": self.workflows,
            "agents": self.agents,
            "skills": sorted(self.skills),
            "full": self.full,
            "skipped_paths": sorted(self.skipped_paths),
            "reason": self.reason,
        }


def _normalize_path(path: str) -> str:
    """Normalize a changed path to repository-relative POSIX form.

    - replaces backslashes with slashes;
    - strips whitespace;
    - removes leading `./`;
    - ignores empty paths.
    """
    p = path.replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return p


def classify_changes(changed_files: list[str]) -> Affected:
    """Classify changed paths into affected sync domains.

    Does not touch the filesystem so deleted files classify correctly.
    """
    affected = Affected()
    for raw in changed_files:
        p = _normalize_path(raw)
        if not p:
            continue

        # Sync-rule files force full mode.
        if p in SYNC_RULE_FILES:
            affected.full = True
            if affected.reason is None:
                affected.reason = f"sync-rule change: {p}"
            continue

        # Governed live workflow files.
        if p in GOVERNED_WORKFLOW_FILES:
            affected.workflows = True
            continue

        # Canonical agent paths (not generated distribution copies).
        if p.startswith("agents/"):
            affected.agents = True
            continue

        # Canonical skill paths: skills/<skill-name>/...
        if p.startswith("skills/"):
            parts = p.split("/", 2)
            if len(parts) >= 2 and parts[1]:
                affected.skills.add(parts[1])
                continue
            # bare "skills/" without a name — ignored
            affected.skipped_paths.append(p)
            continue

        # Everything else is ignored for derived-artifact sync purposes.
        affected.skipped_paths.append(p)

    return affected


def _cmd(args: list[str]) -> dict:
    proc = subprocess.run(args, capture_output=True, text=True)
    return {
        "args": args,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _workflow_check_suites(root: Path) -> list[dict]:
    return [
        {
            "name": "workflow_templates",
            "command": [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--check"],
        },
        {
            "name": "workflow_distributed",
            "command": [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--check-distributed"],
        },
    ]


def _agent_check_suites(root: Path) -> list[dict]:
    suites: list[dict] = []
    for target in AGENT_TARGETS:
        suites.append({
            "name": f"agents_{target.split('/')[0]}",
            "command": [sys.executable, str(SETUP_AGENTS), "--target", str(root / target), "--check"],
        })
    return suites


def _skill_check_suite(root: Path, skills: set[str] | None) -> dict:
    cmd = [sys.executable, str(CHECK_SKILLS), "--root", str(root)]
    if skills is not None and skills:
        cmd += ["--skills", ",".join(sorted(skills))]
    return {
        "name": "skills",
        "command": cmd,
    }


def _check_suites(root: Path, affected: Affected | None = None) -> list[dict]:
    """Build check suites.

    When `affected` is None, run the full suite (current behavior).
    When `affected` is provided, run only selected domain suites unless
    `affected.full` is true (fall back to full).
    """
    if affected is None or affected.full:
        suites: list[dict] = []
        suites += _workflow_check_suites(root)
        suites += _agent_check_suites(root)
        suites.append(_skill_check_suite(root, None))
        return suites

    suites = []
    if affected.workflows:
        suites += _workflow_check_suites(root)
    if affected.agents:
        suites += _agent_check_suites(root)
    if affected.skills:
        suites.append(_skill_check_suite(root, affected.skills))
    return suites


def _workflow_fix_steps(root: Path) -> list[dict]:
    return [
        {
            "name": "workflow_templates_sync",
            "command": [sys.executable, str(SYNC_TEMPLATES), "--root", str(root)],
        },
        {
            "name": "workflow_templates_distribute",
            "command": [sys.executable, str(SYNC_TEMPLATES), "--root", str(root), "--distribute"],
        },
    ]


def _agent_fix_steps(root: Path) -> list[dict]:
    steps: list[dict] = []
    for target in AGENT_TARGETS:
        steps.append({
            "name": f"agents_{target.split('/')[0]}_force",
            "command": [sys.executable, str(SETUP_AGENTS), "--target", str(root / target), "--force"],
        })
    return steps


def _skill_fix_steps(root: Path, skills: set[str] | None) -> list[dict]:
    """Build skill install steps.

    `skills is None` means full all-skill install.
    `skills == set()` means install no skills (returns []).
    `skills == {"demo-skill"}` means install only that skill.

    Does NOT validate that the canonical skill directory exists — callers are
    responsible for preflighting affected skills (see
    `_missing_affected_skills`) so that missing skills are reported and
    excluded before reaching this builder.
    """
    if skills is not None and not skills:
        return []

    steps: list[dict] = []
    if skills is None:
        skills_dir = root / "skills"
        if skills_dir.is_dir():
            skill_names = sorted(p.name for p in skills_dir.iterdir() if p.is_dir())
        else:
            skill_names = []
    else:
        skill_names = sorted(skills)

    for skill_name in skill_names:
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


def _missing_affected_skills(root: Path, skills: set[str]) -> list[str]:
    """Preflight: return affected skill names whose canonical directory is absent.

    A skill is considered missing when `root/skills/<skill-name>/` does not
    exist as a directory. This covers deleted and renamed canonical skills.
    Returns a sorted list of missing skill names.
    """
    missing: list[str] = []
    skills_dir = root / "skills"
    for name in skills:
        if not (skills_dir / name).is_dir():
            missing.append(name)
    return sorted(missing)


def _fix_steps(root: Path, affected: Affected | None = None) -> list[dict]:
    """Build fix steps.

    When `affected` is None, run the full step set (current behavior).
    When `affected` is provided, run only selected domain steps unless
    `affected.full` is true (fall back to full).
    """
    if affected is None or affected.full:
        steps: list[dict] = []
        steps += _workflow_fix_steps(root)
        steps += _agent_fix_steps(root)
        steps += _skill_fix_steps(root, None)
        return steps

    steps = []
    if affected.workflows:
        steps += _workflow_fix_steps(root)
    if affected.agents:
        steps += _agent_fix_steps(root)
    if affected.skills:
        steps += _skill_fix_steps(root, affected.skills)
    return steps


def discover_changed_files_from_git(root: str | os.PathLike) -> list[str]:
    """Collect changed files from the current Git worktree.

    Includes tracked modified/staged changes (git diff --name-only HEAD) and
    untracked files (git ls-files --others --exclude-standard). De-duplicates
    and returns a sorted list of repository-relative paths.

    Raises RuntimeError if a Git command fails.
    """
    root_path = Path(root).resolve()
    changed: set[str] = set()

    diff_cmd = ["git", "-C", str(root_path), "diff", "--name-only", "HEAD"]
    diff_proc = subprocess.run(diff_cmd, capture_output=True, text=True)
    if diff_proc.returncode != 0:
        raise RuntimeError(
            f"git diff --name-only HEAD failed (rc={diff_proc.returncode}): {diff_proc.stderr.strip()}"
        )
    for line in diff_proc.stdout.splitlines():
        p = _normalize_path(line)
        if p:
            changed.add(p)

    ls_cmd = ["git", "-C", str(root_path), "ls-files", "--others", "--exclude-standard"]
    ls_proc = subprocess.run(ls_cmd, capture_output=True, text=True)
    if ls_proc.returncode != 0:
        raise RuntimeError(
            f"git ls-files --others --exclude-standard failed (rc={ls_proc.returncode}): {ls_proc.stderr.strip()}"
        )
    for line in ls_proc.stdout.splitlines():
        p = _normalize_path(line)
        if p:
            changed.add(p)

    return sorted(changed)


def run_aggregate(
    root: str | os.PathLike,
    mode: str,
    json_output: bool = False,
    changed_files: list[str] | None = None,
    incremental: bool = False,
) -> tuple[int, dict | None]:
    """Run the aggregate sync in check or fix mode.

    Returns (returncode, report_or_none). When json_output is True, returns a
    structured report dict. Otherwise prints plain text to stdout.

    When `incremental` is True, `changed_files` is classified into affected
    domains and only the selected suites/steps are run. When `incremental` is
    False (default), the full current behavior runs.

    Incremental fix mode preflights affected skill directories: a missing
    canonical skill directory (deleted/renamed) is reported in
    `missing_skills`, excluded from the install set, and the run returns a
    non-zero exit code. Present skills in the same change set still install
    normally. Full mode does not preflight because it enumerates the live
    `skills/` directory directly.
    """
    root_path = Path(root).resolve()
    if mode not in ("check", "fix"):
        raise ValueError(f"unknown mode: {mode!r}")

    affected: Affected | None = None
    missing_skills: list[str] = []
    if incremental:
        affected = classify_changes(changed_files or [])
        if mode == "fix" and affected.skills and not affected.full:
            # Preflight: validate affected canonical skill directories exist.
            missing_skills = _missing_affected_skills(root_path, affected.skills)
            if missing_skills:
                # Exclude missing skills from the install set so present
                # skills still install while missing ones are reported.
                affected.skills = {s for s in affected.skills
                                   if s not in set(missing_skills)}
        suites = _check_suites(root_path, affected) if mode == "check" else _fix_steps(root_path, affected)
        if affected.full:
            scope = "full"
        elif not suites and not missing_skills:
            scope = "skipped"
        elif not suites and missing_skills:
            scope = "error"
        else:
            scope = "incremental" if not missing_skills else "incremental_with_errors"
    else:
        suites = _check_suites(root_path) if mode == "check" else _fix_steps(root_path)
        scope = "full"

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

    # Missing affected skills force a non-zero exit.
    if missing_skills:
        overall_rc = 1

    if scope == "skipped":
        status = "skipped"
    elif missing_skills:
        status = "error"
    elif overall_rc == 0:
        status = "ok"
    else:
        status = "drift"

    report = {
        "mode": mode,
        "scope": scope,
        "status": status,
        "returncode": overall_rc,
        "affected": affected.to_report() if affected is not None else None,
        "missing_skills": missing_skills,
        "suites": results,
    }

    if json_output:
        return overall_rc, report

    _print_plain_text(mode, scope, status, affected, results, overall_rc, missing_skills)
    return overall_rc, None


def _print_plain_text(
    mode: str,
    scope: str,
    status: str,
    affected: Affected | None,
    results: list[dict],
    overall_rc: int,
    missing_skills: list[str] | None = None,
) -> None:
    missing_skills = missing_skills or []
    if missing_skills:
        print(f"ERROR: missing canonical skill directories: {', '.join(missing_skills)}", file=sys.stderr)
        print("  these skills were reported as changed but their canonical "
              "skills/<name>/ directory is absent (deleted/renamed).", file=sys.stderr)
        print("  install_skill.py was NOT called for the missing skills.", file=sys.stderr)
        if affected is not None and affected.skills:
            print(f"  installed present skills: {', '.join(sorted(affected.skills))}", file=sys.stderr)
        return

    if scope == "skipped":
        print("SKIPPED: no derived-artifact domains affected by the current change set")
        if affected is not None and affected.skipped_paths:
            print(f"  skipped paths: {', '.join(sorted(affected.skipped_paths))}")
        return

    if scope == "full" and affected is not None:
        print(f"FULL: sync-rule change selected full mode ({affected.reason})")

    if scope == "incremental" and affected is not None:
        selected = []
        if affected.workflows:
            selected.append("workflows")
        if affected.agents:
            selected.append("agents")
        if affected.skills:
            selected.append(f"skills: {', '.join(sorted(affected.skills))}")
        print(f"INCREMENTAL: selected domains: {', '.join(selected)} ({len(results)} {mode} suites)")

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate derived-artifact sync entrypoint."
    )
    parser.add_argument("--root", default=".", help="repository root path")
    parser.add_argument("--check", action="store_true", help="read-only verification")
    parser.add_argument("--fix", action="store_true", help="apply synchronization")
    parser.add_argument("--json", action="store_true", help="emit structured JSON report")
    parser.add_argument(
        "--changed-files-from-git",
        action="store_true",
        help="collect changed files from the current Git worktree and run only affected suites",
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        default=None,
        help="manual changed-file input (repeatable)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="explicit full mode alias (default when no changed-file options are given)",
    )
    args = parser.parse_args()

    if args.check and args.fix:
        print("ERROR: --check and --fix are mutually exclusive", file=sys.stderr)
        return 2
    if not args.check and not args.fix:
        print("ERROR: must specify --check or --fix", file=sys.stderr)
        return 2

    mode = "check" if args.check else "fix"

    incremental = bool(args.changed_files_from_git or args.changed_file)
    if args.full and incremental:
        print("WARNING: --full overrides changed-file options; running full mode", file=sys.stderr)
        incremental = False

    changed_files: list[str] | None = None
    if incremental:
        changed_files = []
        if args.changed_file:
            changed_files.extend(args.changed_file)
        if args.changed_files_from_git:
            try:
                changed_files.extend(discover_changed_files_from_git(args.root))
            except RuntimeError as e:
                print(f"ERROR: Git changed-file discovery failed: {e}", file=sys.stderr)
                return 2

    rc, report = run_aggregate(
        args.root,
        mode=mode,
        json_output=args.json,
        changed_files=changed_files,
        incremental=incremental,
    )
    if args.json and report is not None:
        print(json.dumps(report, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())