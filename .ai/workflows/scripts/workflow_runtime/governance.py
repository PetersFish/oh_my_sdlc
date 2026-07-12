"""governance.py — governance diagnostics, foundation verification, and final-commit.

Governance findings, foundation verification, archive diagnostics, and
final-commit support behavior.
"""

import json
import os
import subprocess
import sys

from workflow_runtime.core import (
    _resolve_path,
    _finding_hash,
)
from workflow_runtime.state import (
    _list_active_runs,
    _find_active_run_by_subject,
    _list_dirs,
)
from workflow_runtime.domains import (
    loader_roadmap_item_status,
    _read_roadmap_item_spec_change,
    _read_frontmatter_field,
)


# ---------------------------------------------------------------------------
# final-commit helpers
# ---------------------------------------------------------------------------

def _run_git(root, args, *, check=False):
    """Run a git command in root, capturing output.

    Returns (returncode, stdout, stderr).
    """
    result = subprocess.run(
        ["git"] + list(args),
        cwd=root,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    # Do NOT strip stdout here — callers that need line-by-line parsing
    # (e.g. git status --porcelain) depend on per-line formatting that
    # leading/trailing whitespace conveys.
    return result.returncode, result.stdout, result.stderr.strip()


def _git_status_porcelain(root):
    """Return list of (status_code, path) tuples from git status --porcelain.

    Uses -uall so untracked files are listed individually rather than as
    collapsed directories.
    """
    rc, out, _ = _run_git(root, ["status", "--porcelain", "-uall"])
    if rc != 0:
        return []
    entries = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status_code = line[:2]
        # Porcelain format: XY <path> or XY <path> -> <dest> for renames
        path_part = line[3:]
        if " -> " in path_part:
            # Rename: use destination path
            path = path_part.split(" -> ", 1)[1]
        else:
            path = path_part
        # Normalize to POSIX-style relative paths
        path = path.replace("\\", "/").strip('"')
        entries.append((status_code.strip(), path))
    return entries


def _git_dirty_paths(root):
    """Return list of dirty paths (relative, POSIX-style) from git status."""
    entries = _git_status_porcelain(root)
    return [path for _, path in entries]


def _final_commit_allowed_prefixes(run_id):
    """Return allowlist path prefixes for final-commit staging."""
    return [
        f".ai/workflows/runs/history/{run_id}/",
        ".ai/workflows/runs/current.json",
        ".ai/roadmap/",
        ".ai/memory/",
        "openspec/changes/archive/",
        "docs/superpowers/archive/",
    ]


def _is_delete_status(status_code):
    return "D" in (status_code or "")


def _classify_final_commit_entries(entries, run_id):
    """Split dirty status entries into allowed and residual path lists."""
    prefixes = _final_commit_allowed_prefixes(run_id)
    active_run_prefix = f".ai/workflows/runs/active/{run_id}/"
    allowed = []
    residual = []
    for status_code, path in entries:
        if any(path.startswith(prefix) or path == prefix.rstrip("/") for prefix in prefixes):
            allowed.append(path)
        elif path.startswith(active_run_prefix) and _is_delete_status(status_code):
            allowed.append(path)
        else:
            residual.append(path)
    return allowed, residual


def _classify_final_commit_paths(dirty_paths, run_id):
    """Split dirty paths into (allowed, residual) based on the allowlist.

    Path-only classification is retained for existing tests and callers. It
    does not allow active-run cleanup because active paths require Git status
    information to prove they are deletions.
    """
    prefixes = _final_commit_allowed_prefixes(run_id)
    allowed = []
    residual = []
    for path in dirty_paths:
        if any(path.startswith(prefix) or path == prefix.rstrip("/") for prefix in prefixes):
            allowed.append(path)
        else:
            residual.append(path)
    return allowed, residual


def _load_done_history_run_for_final_commit(root, run_id):
    """Validate that a done history run exists. Returns (state, error_code).

    On success, error_code is None.
    On failure, state is None and error_code is a stable string.
    """
    if not run_id:
        return None, "missing_run_id"
    history_run_path = _resolve_path(
        root, f".ai/workflows/runs/history/{run_id}/run.json"
    )
    if not os.path.exists(history_run_path):
        return None, "history_run_not_found"
    try:
        with open(history_run_path, "r") as f:
            state = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None, "invalid_run_json"
    state_run_id = state.get("run_id")
    if state_run_id and state_run_id != run_id:
        return None, "run_id_mismatch"
    status = state.get("status")
    current_phase = state.get("current_phase")
    if status != "done" and current_phase != "done":
        return None, "run_not_done"
    return state, None


def cmd_final_commit(root, args):
    """Final tail commit for governance artifacts after a workflow run is done.

    Stages only allowlisted paths, commits, optionally pushes, and reports
    residual dirty paths. Never uses git add -A.
    """
    run_id = args.run_id

    # 1. Validate done history run
    state, error_code = _load_done_history_run_for_final_commit(root, run_id)
    if error_code:
        print(json.dumps({
            "status": "failed",
            "run_id": run_id,
            "committed": False,
            "commit_id": None,
            "pushed": False,
            "staged_paths": [],
            "residual_dirty_paths": [],
            "error": error_code,
        }, indent=2))
        sys.exit(1)

    # 2. Read dirty paths
    dirty_entries = _git_status_porcelain(root)
    dirty_paths = [path for _, path in dirty_entries]

    # 3. Classify allowed vs residual
    allowed_dirty, residual_dirty = _classify_final_commit_entries(dirty_entries, run_id)

    # 4. If no allowed dirty paths, return noop
    if not allowed_dirty:
        print(json.dumps({
            "status": "noop",
            "reason": "nothing_to_commit",
            "run_id": run_id,
            "committed": False,
            "commit_id": None,
            "pushed": False,
            "staged_paths": [],
            "residual_dirty_paths": residual_dirty,
        }, indent=2))
        return

    # 5. Stage allowed paths individually (never git add -A)
    for path in allowed_dirty:
        _run_git(root, ["add", "--", path], check=True)

    # 6. Check staged diff for allowlisted paths only.
    #    Use the allowlist to filter, because git diff --cached --name-only
    #    may include pre-existing staged files outside the allowlist that
    #    must NOT be committed by final-commit.  allowed_dirty already
    #    encodes the status-aware allowlist (prefixes plus target active-run
    #    deletions), so membership filtering excludes pre-existing staged
    #    files outside the intended commit scope.
    rc, staged_out, _ = _run_git(root, ["diff", "--cached", "--name-only"])
    all_staged = [p.strip() for p in staged_out.splitlines() if p.strip()]
    allowed_set = set(allowed_dirty)
    staged_paths = [p for p in all_staged if p in allowed_set]

    # 7. If no allowlisted staged diff, return noop
    if not staged_paths:
        print(json.dumps({
            "status": "noop",
            "reason": "nothing_to_commit",
            "run_id": run_id,
            "committed": False,
            "commit_id": None,
            "pushed": False,
            "staged_paths": [],
            "residual_dirty_paths": residual_dirty,
        }, indent=2))
        return

    # 8. Commit ONLY allowlisted paths. Passing explicit pathspecs to
    #    git commit scopes the commit to those paths, preventing any
    #    pre-existing staged files outside the allowlist from being
    #    included while preserving their index state.
    message = args.message or f"chore(workflow): finalize {run_id}"
    rc, _, commit_err = _run_git(
        root, ["commit", "-m", message, "--"] + staged_paths
    )
    if rc != 0:
        print(json.dumps({
            "status": "failed",
            "run_id": run_id,
            "committed": False,
            "commit_id": None,
            "pushed": False,
            "staged_paths": staged_paths,
            "residual_dirty_paths": residual_dirty,
            "error": "commit_failed",
        }, indent=2))
        sys.exit(1)

    # 9. Read commit id
    rc, commit_id, _ = _run_git(root, ["rev-parse", "HEAD"])
    commit_id = commit_id.strip()

    # 10. Push if requested
    pushed = False
    if args.push:
        rc, _, push_err = _run_git(root, ["push", "origin", "HEAD"])
        if rc != 0:
            print(json.dumps({
                "status": "failed",
                "run_id": run_id,
                "committed": True,
                "commit_id": commit_id,
                "pushed": False,
                "staged_paths": staged_paths,
                "residual_dirty_paths": residual_dirty,
                "error": "push_failed",
            }, indent=2))
            sys.exit(1)
        pushed = True

    # 11. Read residual dirty paths again
    residual_after = _git_dirty_paths(root)

    # 12. Return structured JSON
    print(json.dumps({
        "status": "success",
        "run_id": run_id,
        "committed": True,
        "commit_id": commit_id,
        "pushed": pushed,
        "staged_paths": staged_paths,
        "residual_dirty_paths": residual_after,
    }, indent=2))


# ---------------------------------------------------------------------------
# Governance check
# ---------------------------------------------------------------------------

def cmd_governance_check(root, args):
    """Read-only governance diagnostics: dangling archives, pending hooks,
    duplicate promotion runs, and ungoverned roadmap items."""
    findings = []
    archive_dir = _resolve_path(root, "openspec/changes/archive")
    history_dir = _resolve_path(root, ".ai/workflows/runs/history")

    governed_change_ids = set()
    governed_roadmap_ids = set()

    active_runs = _list_active_runs(root)
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        if ps.get("type") == "spec_change" and ps.get("id"):
            governed_change_ids.add(ps["id"])
        if ps.get("type") == "roadmap_item" and ps.get("id"):
            governed_roadmap_ids.add(ps["id"])

    if os.path.isdir(history_dir):
        for entry in _list_dirs(history_dir):
            entry_path = os.path.join(history_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            # New-style: history/<run_id>/run.json
            run_json_path = os.path.join(entry_path, "run.json")
            if not os.path.isfile(run_json_path):
                continue
            try:
                with open(run_json_path, "r") as f:
                    hist = json.load(f)
            except Exception:
                continue
            if hist.get("status") in ("done",):
                ps = hist.get("primary_subject", {})
                if ps.get("type") == "spec_change" and ps.get("id"):
                    governed_change_ids.add(ps["id"])
                if ps.get("type") == "roadmap_item" and ps.get("id"):
                    governed_roadmap_ids.add(ps["id"])
                    change_id = (
                        hist.get("context", {}).get("change_id")
                        or hist.get("evidence", {}).get("change_id")
                        or _read_roadmap_item_spec_change(root, ps["id"])
                    )
                    if change_id:
                        governed_change_ids.add(change_id)

    if os.path.isdir(archive_dir):
        for entry in _list_dirs(archive_dir):
            e_path = os.path.join(archive_dir, entry)
            if not os.path.isdir(e_path):
                continue
            parts = entry.split("-")
            if len(parts) < 4:
                continue
            change_id = "-".join(parts[3:])
            if change_id in governed_change_ids:
                continue
            rel_path = os.path.relpath(e_path, root)
            message = (
                f"Archived OpenSpec change \"{change_id}\" has no "
                f"matching workflow run."
            )
            ensure_cmd = (
                f"python3 .ai/workflows/scripts/workflow.py --root . ensure-run"
                f" --action dangling_archive_repair"
                f" --subject-type spec_change"
                f" --subject-id {change_id}"
            )
            remediation = (
                f"Archived OpenSpec change \"{change_id}\" (archive path: {rel_path})"
                f" has no matching workflow run. Run: {ensure_cmd}"
                f" to create a post_archive_actions run. Then resolve,"
                f" complete hooks, complete-phase --exit-criteria-satisfied"
                f" pending_hooks_empty, advance to done, and re-run"
                f" \"workflow.py governance-check\" until block=false."
            )
            fh = _finding_hash(
                "dangling_archive", change_id=change_id, archive_path=rel_path
            )
            findings.append({
                "type": "dangling_archive",
                "change_id": change_id,
                "archive_path": rel_path,
                "message": message,
                "remediation": remediation,
                "hash": fh,
            })

    # Detect duplicate promotion runs: roadmap_item + spec_change for same change
    roadmap_change_ids = {}
    openspec_run_ids = set()
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        ctx = active_state.get("context", {})
        ev = active_state.get("evidence", {})
        if ps.get("type") == "roadmap_item":
            cid = ctx.get("change_id") or ev.get("change_id")
            if not cid:
                item_id = ps.get("id")
                if item_id:
                    cid = _read_roadmap_item_spec_change(root, item_id)
            if cid:
                roadmap_change_ids[cid] = run_id
        elif ps.get("type") == "spec_change":
            openspec_run_ids.add(run_id)
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        if ps.get("type") != "spec_change":
            continue
        oc_change_id = ps.get("id")
        if oc_change_id and oc_change_id in roadmap_change_ids:
            canonical_run_id = roadmap_change_ids[oc_change_id]
            message = (
                f"Duplicate runs for change \"{oc_change_id}\":"
                f" spec_change run \"{run_id}\" and"
                f" roadmap_item run \"{canonical_run_id}\"."
                f" The roadmap_item run is canonical."
            )
            remediation = (
                f"Cancel the spec_change run \"{run_id}\" with:"
                f" python3 .ai/workflows/scripts/workflow.py --root . cancel-run"
                f" --subject-type spec_change --subject-id {oc_change_id}"
                f" --reason \"duplicate of canonical roadmap_item run {canonical_run_id}\"."
                f" Re-run \"workflow.py governance-check\" until block=false."
            )
            fh = _finding_hash(
                "duplicate_promotion_runs",
                change_id=oc_change_id,
                canonical_run_id=canonical_run_id,
                duplicate_run_id=run_id,
            )
            findings.append({
                "type": "duplicate_promotion_runs",
                "change_id": oc_change_id,
                "canonical_run_id": canonical_run_id,
                "duplicate_run_id": run_id,
                "message": message,
                "remediation": remediation,
                "hash": fh,
            })

    # Detect stale active roadmap_item runs whose item is already done/cancelled.
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        if ps.get("type") != "roadmap_item":
            continue
        if active_state.get("status") not in ("running", "blocked"):
            continue
        item_id = ps.get("id")
        if not item_id:
            continue
        item_status = loader_roadmap_item_status(root, item_id)
        if not item_status or item_status.get("status") not in ("done", "cancelled"):
            continue
        rel_path = active_state.get("evidence", {}).get("roadmap_item_path", item_id)
        message = (
            f'Active roadmap_item run "{run_id}" remains running after '
            f'roadmap item "{item_id}" became {item_status.get("status")}. '
            f"The active run is stale."
        )
        remediation = (
            f'Run: python3 .ai/workflows/scripts/workflow.py --root . cancel-run'
            f' --subject-type roadmap_item --subject-id {item_id}'
            f' --reason "stale active run for completed roadmap item".'
            f' Re-run "workflow.py governance-check" until block=false.'
        )
        fh = _finding_hash(
            "stale_active_roadmap_run",
            run_id=run_id,
            item_id=item_id,
            status=item_status.get("status"),
            file_path=rel_path,
        )
        findings.append({
            "type": "stale_active_roadmap_run",
            "run_id": run_id,
            "item_id": item_id,
            "status": item_status.get("status"),
            "file_path": rel_path,
            "message": message,
            "remediation": remediation,
            "hash": fh,
        })

    # Detect ungoverned active roadmap items without matching active run or done history
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    if os.path.isdir(areas_dir):
        for area in _list_dirs(areas_dir):
            items_dir = os.path.join(areas_dir, area, "items")
            if not os.path.isdir(items_dir):
                continue
            for fname in _list_dirs(items_dir):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(items_dir, fname)
                fm_id = _read_frontmatter_field(fpath, "id")
                fm_status = _read_frontmatter_field(fpath, "status")
                if not fm_id or not fm_status:
                    continue
                if fm_status in ("done", "cancelled", "idea"):
                    continue
                if fm_id in governed_roadmap_ids:
                    continue
                has_active = bool(_find_active_run_by_subject(root, "roadmap_item", fm_id))
                if has_active:
                    governed_roadmap_ids.add(fm_id)
                    continue
                rel_path = os.path.relpath(fpath, root)
                message = (
                    f"Roadmap item \"{fm_id}\" (status: {fm_status}) has no"
                    f" matching active run or done history."
                )
                start_cmd = (
                    f"python3 .ai/workflows/scripts/workflow.py --root . start"
                    f" --subject-type roadmap_item"
                    f" --subject-id {fm_id}"
                )
                remediation = (
                    f"Roadmap item \"{fm_id}\" ({rel_path}, status: {fm_status})"
                    f" is ungoverned. Run: {start_cmd}"
                    f" to create a run. Then complete-phase, advance, and re-run"
                    f" \"workflow.py governance-check\" until block=false."
                )
                fh = _finding_hash(
                    "ungoverned_roadmap_item",
                    item_id=fm_id,
                    status=fm_status,
                    file_path=rel_path,
                )
                findings.append({
                    "type": "ungoverned_roadmap_item",
                    "item_id": fm_id,
                    "status": fm_status,
                    "file_path": rel_path,
                    "message": message,
                    "remediation": remediation,
                    "hash": fh,
                })

    # Detect OpenSpec changes linked from roadmap items without
    # matching workflow evidence
    governed_roadmap_change_ids = set()
    for run_id, active_state in active_runs:
        ps = active_state.get("primary_subject", {})
        ctx = active_state.get("context", {})
        ev = active_state.get("evidence", {})
        if ps.get("type") == "roadmap_item":
            cid = ctx.get("change_id") or ev.get("change_id")
            if not cid:
                item_id = ps.get("id")
                if item_id:
                    cid = _read_roadmap_item_spec_change(root, item_id)
            if cid:
                governed_roadmap_change_ids.add(cid)
    if os.path.isdir(history_dir):
        for entry in _list_dirs(history_dir):
            entry_path = os.path.join(history_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            run_json_path = os.path.join(entry_path, "run.json")
            if not os.path.isfile(run_json_path):
                continue
            try:
                with open(run_json_path, "r") as f:
                    hist = json.load(f)
            except Exception:
                continue
            if hist.get("status") in ("done",):
                ps = hist.get("primary_subject", {})
                ctx = hist.get("context", {})
                ev = hist.get("evidence", {})
                if ps.get("type") == "roadmap_item":
                    cid = ctx.get("change_id") or ev.get("change_id")
                    if not cid:
                        item_id = ps.get("id")
                        if item_id:
                            cid = _read_roadmap_item_spec_change(root, item_id)
                    if cid:
                        governed_roadmap_change_ids.add(cid)
    if os.path.isdir(areas_dir):
        for area in _list_dirs(areas_dir):
            items_dir = os.path.join(areas_dir, area, "items")
            if not os.path.isdir(items_dir):
                continue
            for fname in _list_dirs(items_dir):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(items_dir, fname)
                linked_change = _read_frontmatter_field(fpath, "spec_change") or _read_frontmatter_field(fpath, "openspec_change")
                if not linked_change or linked_change == "None":
                    continue
                fm_id = _read_frontmatter_field(fpath, "id")
                fm_status = _read_frontmatter_field(fpath, "status")
                if linked_change in governed_change_ids:
                    continue
                if linked_change in governed_roadmap_change_ids:
                    continue
                rel_path = os.path.relpath(fpath, root)
                message = (
                    f"Roadmap item \"{fm_id}\" (status: {fm_status}) links to"
                    f" OpenSpec change \"{linked_change}\" without matching"
                    f" workflow evidence."
                )
                # If there is an active roadmap_item run for this item, guide user to
                # write context.change_id and advance to create_change.
                linked_item_run = _find_active_run_by_subject(root, "roadmap_item", fm_id)
                if linked_item_run:
                    remediation = (
                        f"Roadmap item \"{fm_id}\" ({rel_path}) links to"
                        f" \"{linked_change}\" but its workflow run"
                        f" \"{linked_item_run.get('run_id', '?')}\" (phase: {linked_item_run.get('current_phase', '?')})"
                        f" has no context.change_id."
                        f" Run: python3 .ai/workflows/scripts/workflow.py --root . record-context"
                        f" --key change_id --value \"{linked_change}\""
                        f" --subject-type roadmap_item --subject-id {fm_id}"
                        f", then advance through create_change."
                        f" Re-run \"workflow.py governance-check\" until block=false."
                    )
                else:
                    remediation = (
                        f"Roadmap item \"{fm_id}\" ({rel_path}) links to"
                        f" \"{linked_change}\" without workflow evidence."
                        f" Start a run: python3 .ai/workflows/scripts/workflow.py --root . start"
                        f" --subject-type roadmap_item --subject-id {fm_id}"
                        f" and advance to create_change."
                        f" Re-run \"workflow.py governance-check\" until block=false."
                    )
                fh = _finding_hash(
                    "linked_item_no_workflow_evidence",
                    item_id=fm_id or "",
                    change_id=linked_change,
                )
                findings.append({
                    "type": "linked_item_no_workflow_evidence",
                    "item_id": fm_id,
                    "change_id": linked_change,
                    "file_path": rel_path,
                    "message": message,
                    "remediation": remediation,
                    "hash": fh,
                })

    for run_id, active_state in active_runs:
        pending = active_state.get("pending_hooks", [])
        if not pending:
            continue
        ctx = active_state.get("context", {})
        change_id = ctx.get("change_id", "")
        hook_list = ", ".join(pending)
        message = (
            f"Active run \"{run_id}\" has {len(pending)} unresolved "
            f"hook(s): {pending}."
        )
        remediation = (
            f"Active run \"{run_id}\" has unresolved hooks: [{hook_list}]. "
            f"Invoke the responsible workers for each hook, then run "
            f"\"workflow.py complete-hook --hook <hook-name>\" for each. "
            f"Re-run \"workflow.py governance-check\" until block=false."
        )
        fh = _finding_hash(
            "pending_hooks",
            run_id=run_id,
            change_id=change_id or None,
            pending_hook_names=",".join(sorted(pending)),
        )
        findings.append({
            "type": "pending_hooks",
            "run_id": run_id,
            "change_id": change_id or None,
            "pending_hook_names": pending,
            "message": message,
            "remediation": remediation,
            "hash": fh,
        })

    block = len(findings) > 0
    output = {"block": block, "findings": findings}
    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# Foundation verification
# ---------------------------------------------------------------------------

FOUNDATIONS = {
    "workflow_py": ".ai/workflows/scripts/workflow.py",
    "workflow_yaml": ".ai/workflows/definitions/sdlc-main.yaml",
    "workflow_runs": ".ai/workflows/runs",
    "agents_md": "AGENTS.md",
    "openspec_config": "openspec/config.yaml",
    "memory_manifest": ".ai/memory/manifest.json",
}


def cmd_verify_foundations(root, args):
    report = {}
    for key, relpath in FOUNDATIONS.items():
        report[key] = os.path.exists(os.path.join(root, relpath))

    all_present = all(report.values())
    if args.json:
        print(json.dumps({"foundations": report, "all_present": all_present}, indent=2))
    else:
        for key, present in report.items():
            status = "PRESENT" if present else "MISSING"
            print(f"{status}: {key} ({FOUNDATIONS[key]})")
    if not all_present:
        sys.exit(1)