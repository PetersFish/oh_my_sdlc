#!/usr/bin/env python3
"""Phase-aware pre-commit hook policy for derived-artifact drift.

Owns only orchestration and pure policy.  Invoked by the existing shell hook:

    python3 scripts/derived_sync_hook_policy.py --root <checkout-root>

Responsibilities (no file writes):
  - collect staged index entries (git diff --cached --name-status -z);
  - collect complete dirty state (git status --porcelain=v1 -z);
  - resolve the current lifecycle phase from workflow runtime state;
  - bind the current checkout to exactly one active workflow run;
  - classify staged canonical paths using the shared path-aware classifier
    exported by scripts/sync_derived_artifacts.py;
  - return a stable allow/reject HookPolicyResult with stable diagnostic
    reasons.

Does NOT duplicate canonical-to-derived mappings.  Reuses
sync_derived_artifacts.classify_changes and sync_templates.GOVERNED for
path-aware attribution.

Stable rejection reasons:
  manual_generated_artifact_change
  generated_artifact_mixed_with_authored_commit
  unattributed_generated_drift
  unrelated_generated_drift
  missing_workflow_phase_context
  ambiguous_workflow_run_context
  workflow_checkout_mismatch
  unsupported_canonical_skill_removal
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Generated distribution target prefixes (derived copies, not canonical).
GENERATED_PREFIXES = (
    ".opencode/",
    ".claude/",
    ".cursor/",
)

# Agent distribution target suffixes.
AGENT_TARGET_SUFFIXES = ("/agents",)

# Skill distribution target suffixes.
SKILL_TARGET_SUFFIXES = ("/skills",)


class HookPolicyResult:
    """Result of the phase-aware hook policy evaluation.

    Fields separate staged canonical scope, actual generated changes, and
    stale generated targets so the hook can decide whether expected
    apply-phase drift may bypass the distribution-drift check.
    """

    def __init__(
        self,
        allowed,
        reason,
        phase,
        run_id,
        staged_canonical_paths,
        actual_dirty_generated_paths,
        actual_staged_generated_paths,
        detected_stale_generated_paths,
        attributable_stale_generated_paths,
        unattributed_generated_paths,
        details,
    ):
        self.allowed = allowed
        self.reason = reason
        self.phase = phase
        self.run_id = run_id
        self.staged_canonical_paths = staged_canonical_paths
        self.actual_dirty_generated_paths = actual_dirty_generated_paths
        self.actual_staged_generated_paths = actual_staged_generated_paths
        self.detected_stale_generated_paths = detected_stale_generated_paths
        self.attributable_stale_generated_paths = attributable_stale_generated_paths
        self.unattributed_generated_paths = unattributed_generated_paths
        self.details = details

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "phase": self.phase,
            "run_id": self.run_id,
            "staged_canonical_paths": self.staged_canonical_paths,
            "actual_dirty_generated_paths": self.actual_dirty_generated_paths,
            "actual_staged_generated_paths": self.actual_staged_generated_paths,
            "detected_stale_generated_paths": self.detected_stale_generated_paths,
            "attributable_stale_generated_paths": self.attributable_stale_generated_paths,
            "unattributed_generated_paths": self.unattributed_generated_paths,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Git entry collection
# ---------------------------------------------------------------------------

def _normalize_path(p: str) -> str:
    p = p.replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return p


def _parse_porcelain_z(output: str) -> list[tuple[str, str]]:
    """Parse git status --porcelain=v1 -z output into (status, path) tuples.

    Handles renamed entries (status 'R' / 'C') with the form
    ``R  old\0new\0``.
    """
    entries: list[tuple[str, str]] = []
    parts = output.split("\0")
    i = 0
    while i < len(parts):
        part = parts[i]
        if not part:
            i += 1
            continue
        status = part[:2]
        path_field = part[2:]
        if status and status[0] in ("R", "C"):
            # Renamed/copied: next part is the new path
            if i + 1 < len(parts):
                new_path = parts[i + 1]
                i += 2
                path = _normalize_path(new_path)
            else:
                i += 1
                path = _normalize_path(path_field)
        else:
            i += 1
            path = _normalize_path(path_field)
        if path:
            status_clean = status.strip()
            entries.append((status_clean, path))
    return entries


def discover_staged_entries(root: str | os.PathLike) -> list[tuple[str, str]]:
    """Collect staged index entries from ``git diff --cached --name-status -z``.

    Returns a list of (status, path) tuples with repository-relative paths.
    Preserves rename and deletion status.
    """
    root_path = Path(root).resolve()
    proc = subprocess.run(
        ["git", "-C", str(root_path), "diff", "--cached", "--name-status", "-z"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git diff --cached --name-status -z failed (rc={proc.returncode}): "
            f"{proc.stderr.strip()}"
        )
    return _parse_name_status_z(proc.stdout)


def _parse_name_status_z(output: str) -> list[tuple[str, str]]:
    """Parse ``git diff --name-status -z`` output into (status, path) tuples."""
    entries: list[tuple[str, str]] = []
    parts = output.split("\0")
    i = 0
    while i < len(parts):
        part = parts[i]
        if not part:
            i += 1
            continue
        # name-status: <status>\t<path>  for normal, <status>\t<old>\t<new> for renames
        # With -z, fields are NUL-separated: status\0path\0  or status\0old\0new\0
        status = part
        i += 1
        if i >= len(parts):
            break
        path1 = parts[i]
        i += 1
        if status and status[0] in ("R", "C"):
            # rename/copy: path1 is old, path2 is new
            if i < len(parts):
                path2 = parts[i]
                i += 1
                path = _normalize_path(path2)
            else:
                path = _normalize_path(path1)
        else:
            path = _normalize_path(path1)
        if path:
            entries.append((status.strip(), path))
    return entries


def discover_worktree_entries(root: str | os.PathLike) -> list[tuple[str, str]]:
    """Collect complete worktree dirty state from ``git status --porcelain=v1 -z``.

    Returns a list of (status, path) tuples with repository-relative paths.
    Includes unstaged modifications, untracked files, renames, and deletions.

    Untracked directories are expanded to individual files using
    ``git ls-files --others --exclude-standard`` so callers see concrete file
    paths rather than directory entries.
    """
    root_path = Path(root).resolve()
    proc = subprocess.run(
        ["git", "-C", str(root_path), "status", "--porcelain=v1", "-z"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git status --porcelain=v1 -z failed (rc={proc.returncode}): "
            f"{proc.stderr.strip()}"
        )
    entries = _parse_porcelain_z(proc.stdout)
    # Expand untracked directory entries into concrete file paths.
    expanded: list[tuple[str, str]] = []
    for status, path in entries:
        if status == "??" and path.endswith("/"):
            # Untracked directory: list individual files under it.
            dir_path = path.rstrip("/")
            ls_proc = subprocess.run(
                ["git", "-C", str(root_path), "ls-files", "--others",
                 "--exclude-standard", dir_path],
                capture_output=True, text=True,
            )
            if ls_proc.returncode == 0:
                for line in ls_proc.stdout.splitlines():
                    p = _normalize_path(line)
                    if p:
                        expanded.append(("??", p))
            else:
                expanded.append((status, path))
        else:
            expanded.append((status, path))
    return expanded


# ---------------------------------------------------------------------------
# Phase resolution and checkout-to-run binding
# ---------------------------------------------------------------------------

def _list_active_runs(root: str) -> list[tuple[str, dict]]:
    """List all active runs under root/.ai/workflows/runs/active/.

    Returns a list of (run_id, state_dict) tuples.
    """
    active_dir = os.path.join(root, ".ai", "workflows", "runs", "active")
    if not os.path.isdir(active_dir):
        return []
    results: list[tuple[str, dict]] = []
    for entry in sorted(os.listdir(active_dir)):
        entry_path = os.path.join(active_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        run_json = os.path.join(entry_path, "run.json")
        if not os.path.isfile(run_json):
            continue
        try:
            with open(run_json, "r") as f:
                state = json.load(f)
            results.append((state.get("run_id", entry), state))
        except Exception:
            continue
    return results


def _normalize_path_str(p: str | None) -> str:
    if not p:
        return ""
    return os.path.normpath(p)


def _run_matches_checkout(
    state: dict,
    checkout_root: str,
    control_root: str | None = None,
) -> bool:
    """Determine whether a run state matches the current checkout.

    For worktree-mode runs: match by normalized ``context.worktree_path``.
    For main-checkout runs: match by normalized ``context.control_root`` (or
    the absence of worktree_path) against the checkout root.

    When ``control_root`` is provided, active runs under that control root are
    candidates; the worktree path is the binding key for worktree-mode runs.
    """
    context = state.get("context", {}) or {}
    execution_mode = context.get("execution_mode") or "main_checkout"
    worktree_path = _normalize_path_str(context.get("worktree_path"))
    run_control_root = _normalize_path_str(context.get("control_root"))

    checkout_norm = _normalize_path_str(checkout_root)

    if execution_mode == "worktree":
        if worktree_path and _normalize_path_str(worktree_path) == checkout_norm:
            return True
        return False

    # main_checkout
    if worktree_path:
        # If a main-checkout run explicitly records a worktree_path, it does not
        # match a different checkout.
        if _normalize_path_str(worktree_path) == checkout_norm:
            return True
        return False
    # No worktree_path: bind by control_root or by the checkout root itself
    if run_control_root and _normalize_path_str(run_control_root) == checkout_norm:
        return True
    # If control_root is provided (for worktree-mode lookup), a main-checkout
    # run stored under that control root matches the control root checkout.
    if control_root and run_control_root and _normalize_path_str(control_root) == run_control_root:
        if checkout_norm == _normalize_path_str(control_root):
            return True
    # Fallback: if no control_root recorded, match if this is the active root
    if not run_control_root and not control_root:
        return True
    return False


def resolve_phase(
    root: str | os.PathLike,
    control_root: str | os.PathLike | None = None,
) -> tuple[str | None, str | None]:
    """Resolve the current lifecycle phase from workflow runtime state.

    Returns (phase, run_id).  When no active run matches the current checkout,
    returns (None, None) to preserve existing non-workflow behavior.

    Raises RuntimeError when:
      - an active run matches but has an unreadable phase;
      - multiple active runs match the same checkout (ambiguous context).
    """
    root_path = os.path.normpath(str(root))
    control_root_norm = os.path.normpath(str(control_root)) if control_root else None

    # Candidate roots to inspect for active runs.  For worktree-mode binding,
    # the state lives under the control root, not the worktree.
    inspect_roots = []
    if control_root_norm:
        inspect_roots.append(control_root_norm)
    inspect_roots.append(root_path)

    matching: list[tuple[str, dict]] = []
    seen_run_ids: set[str] = set()
    for inspect_root in inspect_roots:
        for run_id, state in _list_active_runs(inspect_root):
            if run_id in seen_run_ids:
                continue
            if _run_matches_checkout(state, root_path, control_root_norm):
                matching.append((run_id, state))
                seen_run_ids.add(run_id)

    if not matching:
        return None, None

    if len(matching) > 1:
        raise RuntimeError(
            "ambiguous_workflow_run_context: multiple active runs match the "
            f"current checkout ({len(matching)} runs): "
            f"{[rid for rid, _ in matching]}"
        )

    run_id, state = matching[0]
    # Only consider running/blocked runs as active.
    status = state.get("status", "")
    if status not in ("running", "blocked"):
        return None, None

    phase = state.get("current_phase", "")
    if not phase:
        raise RuntimeError(
            f"missing_workflow_phase_context: active run {run_id!r} has an "
            f"unreadable or empty current_phase"
        )

    return phase, run_id


# ---------------------------------------------------------------------------
# Path-aware attribution
# ---------------------------------------------------------------------------

def _is_generated_path(path: str) -> bool:
    """Return True if a path is under a generated distribution target."""
    return any(path.startswith(prefix) for prefix in GENERATED_PREFIXES)


def _classify_canonical(staged_entries: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    """Classify staged entries into canonical and generated paths.

    Returns (canonical_paths, generated_paths).  Canonical paths are those
    that the shared classifier recognizes as authored sources.  Generated
    paths are those under distribution targets.
    """
    canonical: list[str] = []
    generated: list[str] = []
    for status, path in staged_entries:
        if _is_generated_path(path):
            generated.append(path)
        else:
            canonical.append(path)
    return canonical, generated


def _import_sync_module():
    """Import sync_derived_artifacts.py for path-aware classification."""
    import importlib.util
    sync_path = REPO_ROOT / "scripts" / "sync_derived_artifacts.py"
    spec = importlib.util.spec_from_file_location("sync_derived_artifacts", str(sync_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _attribute_stale_paths(
    stale_paths: list[str],
    staged_canonical_paths: list[str],
    sync_mod,
) -> tuple[list[str], list[str]]:
    """Partition stale generated paths into attributable and unattributed.

    A stale path is attributable when it maps to one of the staged canonical
    paths through the existing sync mapping.  Uses the shared classifier's
    domain knowledge rather than a duplicate mapping table.
    """
    if not stale_paths:
        return [], []

    # Build a map from canonical path to expected generated targets using the
    # shared classifier.  The classifier gives us the affected domains; we
    # derive the specific generated target paths from the domain.
    affected = sync_mod.classify_changes(staged_canonical_paths)
    attributable_domains = {
        "agents": affected.agents,
        "skills": set(affected.skills),
        "workflows": affected.workflows,
    }

    attributable: list[str] = []
    unattributed: list[str] = []
    for stale in stale_paths:
        if _is_stale_attributable(stale, staged_canonical_paths, attributable_domains):
            attributable.append(stale)
        else:
            unattributed.append(stale)
    return attributable, unattributed


def _stale_matches_canonical_agent(stale: str, staged_canonical_paths: list[str]) -> bool:
    """Check if a stale agent target maps to a staged canonical agent file.

    e.g. ``.opencode/agents/implement-agent.md`` -> ``agents/implement-agent.md``
    """
    for prefix in GENERATED_PREFIXES:
        if not stale.startswith(prefix):
            continue
        rest = stale[len(prefix):]
        if not rest.startswith("agents/"):
            continue
        agent_filename = rest[len("agents/"):]
        # Match against staged canonical agents/<filename>
        for canonical in staged_canonical_paths:
            if canonical.startswith("agents/"):
                canonical_filename = canonical[len("agents/"):]
                if canonical_filename == agent_filename:
                    return True
    return False


def _stale_matches_canonical_skill(stale: str, staged_canonical_paths: list[str]) -> bool:
    """Check if a stale skill target maps to a staged canonical skill file.

    e.g. ``.opencode/skills/demo-skill/SKILL.md`` -> ``skills/demo-skill/SKILL.md``
    """
    for prefix in GENERATED_PREFIXES:
        if not stale.startswith(prefix):
            continue
        rest = stale[len(prefix):]
        if not rest.startswith("skills/"):
            continue
        # rest is like skills/demo-skill/SKILL.md
        skill_relative = rest[len("skills/"):]
        for canonical in staged_canonical_paths:
            if canonical.startswith("skills/"):
                canonical_relative = canonical[len("skills/"):]
                if canonical_relative == skill_relative:
                    return True
                # Also match by skill name prefix (any file under the skill)
                # so the whole skill dir is attributable when the skill is staged.
                staged_skill_name = canonical_relative.split("/")[0] if canonical_relative else ""
                stale_skill_name = skill_relative.split("/")[0] if skill_relative else ""
                if staged_skill_name and staged_skill_name == stale_skill_name:
                    return True
    return False


def _stale_matches_canonical_workflow(stale: str, staged_canonical_paths: list[str]) -> bool:
    """Check if a stale workflow template/distributed target maps to a staged
    governed workflow source.

    e.g. ``.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py``
    -> ``.ai/workflows/scripts/workflow_runtime/state.py``
    """
    for prefix in GENERATED_PREFIXES:
        if not stale.startswith(prefix):
            continue
        rest = stale[len(prefix):]
        # Workflow templates are distributed under
        # <prefix>/skills/sdlc-project-bootstrap/templates/workflow/...
        workflow_tmpl_marker = "skills/sdlc-project-bootstrap/templates/workflow/"
        if workflow_tmpl_marker not in rest:
            continue
        tmpl_relative = rest[rest.index(workflow_tmpl_marker) + len(workflow_tmpl_marker):]
        # tmpl_relative is like workflow.py, sdlc-main.yaml, workflow_runtime/state.py
        # Map back to the live governed path.
        live_candidates = [
            f".ai/workflows/scripts/{tmpl_relative}" if tmpl_relative.startswith("workflow_runtime/") else "",
            f".ai/workflows/scripts/{tmpl_relative}" if tmpl_relative == "workflow.py" else "",
            f".ai/workflows/definitions/{tmpl_relative}" if tmpl_relative == "sdlc-main.yaml" else "",
        ]
        # Also handle direct mapping: tmpl_relative = workflow_runtime/state.py
        # -> .ai/workflows/scripts/workflow_runtime/state.py
        if tmpl_relative.startswith("workflow_runtime/"):
            live_candidates = [f".ai/workflows/scripts/{tmpl_relative}"]
        elif tmpl_relative == "workflow.py":
            live_candidates = [".ai/workflows/scripts/workflow.py"]
        elif tmpl_relative == "sdlc-main.yaml":
            live_candidates = [".ai/workflows/definitions/sdlc-main.yaml"]
        else:
            live_candidates = []

        for canonical in staged_canonical_paths:
            for candidate in live_candidates:
                if candidate and canonical == candidate:
                    return True
    return False


def _is_stale_attributable(
    stale: str,
    staged_canonical_paths: list[str],
    attributable_domains: dict,
) -> bool:
    """Determine whether a single stale generated path is attributable to a
    staged canonical source through existing sync mapping."""
    if not staged_canonical_paths:
        return False

    # Agent domain
    if attributable_domains.get("agents"):
        if _stale_matches_canonical_agent(stale, staged_canonical_paths):
            return True
    # Skill domain
    if attributable_domains.get("skills"):
        if _stale_matches_canonical_skill(stale, staged_canonical_paths):
            return True
    # Workflow domain
    if attributable_domains.get("workflows"):
        if _stale_matches_canonical_workflow(stale, staged_canonical_paths):
            return True
    return False


# ---------------------------------------------------------------------------
# Policy evaluation
# ---------------------------------------------------------------------------

def _is_canonical_skill_removal(staged_entries: list[tuple[str, str]]) -> bool:
    """Detect canonical Skill directory deletion/rename (unsupported)."""
    for status, path in staged_entries:
        if path.startswith("skills/") and status == "D":
            return True
    return False


def evaluate_policy(
    root: str | os.PathLike,
    staged_entries: list[tuple[str, str]],
    worktree_entries: list[tuple[str, str]],
    detected_stale_generated_paths: list[str],
    phase: str | None,
    run_id: str | None,
) -> HookPolicyResult:
    """Evaluate the phase-aware hook policy.

    Returns a HookPolicyResult with stable allow/reject decision and reason.

    Phase rules:
      - apply_change: allow attributable stale derived targets when generated
        files are not modified or staged;
      - non-apply phases: stale targets are NOT allowed (strict);
      - no phase: existing non-workflow behavior; any generated change or
        unattributed drift rejects.
    """
    sync_mod = _import_sync_module()

    canonical_paths, generated_paths = _classify_canonical(staged_entries)

    # Classify generated paths from worktree entries (dirty generated files)
    dirty_generated = [
        path for status, path in worktree_entries if _is_generated_path(path)
    ]
    # Staged generated (mixed into authored commit)
    staged_generated = generated_paths

    # Unsupported: canonical Skill directory deletion/rename
    if _is_canonical_skill_removal(staged_entries):
        return HookPolicyResult(
            allowed=False,
            reason="unsupported_canonical_skill_removal",
            phase=phase,
            run_id=run_id,
            staged_canonical_paths=canonical_paths,
            actual_dirty_generated_paths=dirty_generated,
            actual_staged_generated_paths=staged_generated,
            detected_stale_generated_paths=detected_stale_generated_paths,
            attributable_stale_generated_paths=[],
            unattributed_generated_paths=[],
            details={"staged": staged_entries},
        )

    # Missing phase context: phase-specific policy required but unavailable.
    if phase is None:
        if detected_stale_generated_paths or staged_generated or dirty_generated:
            return HookPolicyResult(
                allowed=False,
                reason="missing_workflow_phase_context",
                phase=phase,
                run_id=run_id,
                staged_canonical_paths=canonical_paths,
                actual_dirty_generated_paths=dirty_generated,
                actual_staged_generated_paths=staged_generated,
                detected_stale_generated_paths=detected_stale_generated_paths,
                attributable_stale_generated_paths=[],
                unattributed_generated_paths=detected_stale_generated_paths,
                details={},
            )
        # No generated issues and no phase: allow (ordinary non-workflow commit)
        return HookPolicyResult(
            allowed=True,
            reason=None,
            phase=phase,
            run_id=run_id,
            staged_canonical_paths=canonical_paths,
            actual_dirty_generated_paths=dirty_generated,
            actual_staged_generated_paths=staged_generated,
            detected_stale_generated_paths=detected_stale_generated_paths,
            attributable_stale_generated_paths=[],
            unattributed_generated_paths=[],
            details={},
        )

    # Reject manual generated artifact change (generated files dirty in worktree)
    if dirty_generated:
        # Distinguish between untracked new generated files (always manual) and
        # modified/deleted generated files that might be unrelated drift.
        untracked_generated = [
            path for status, path in worktree_entries
            if _is_generated_path(path) and status == "??"
        ]
        modified_generated = [
            path for status, path in worktree_entries
            if _is_generated_path(path) and status != "??"
        ]

        # Untracked generated files are always manual artifact changes.
        if untracked_generated:
            return HookPolicyResult(
                allowed=False,
                reason="manual_generated_artifact_change",
                phase=phase,
                run_id=run_id,
                staged_canonical_paths=canonical_paths,
                actual_dirty_generated_paths=dirty_generated,
                actual_staged_generated_paths=staged_generated,
                detected_stale_generated_paths=detected_stale_generated_paths,
                attributable_stale_generated_paths=[],
                unattributed_generated_paths=[],
                details={"offending": untracked_generated},
            )

        # Modified/deleted generated files: partition into attributable
        # (manual modification of a target the staged canonical owns) and
        # unrelated (dirty generated path not owned by the staged canonical set).
        dirty_attributable, dirty_unrelated = _attribute_stale_paths(
            modified_generated, canonical_paths, sync_mod,
        )
        if dirty_unrelated:
            return HookPolicyResult(
                allowed=False,
                reason="unrelated_generated_drift",
                phase=phase,
                run_id=run_id,
                staged_canonical_paths=canonical_paths,
                actual_dirty_generated_paths=dirty_generated,
                actual_staged_generated_paths=staged_generated,
                detected_stale_generated_paths=detected_stale_generated_paths,
                attributable_stale_generated_paths=[],
                unattributed_generated_paths=dirty_unrelated,
                details={"offending": dirty_unrelated},
            )
        return HookPolicyResult(
            allowed=False,
            reason="manual_generated_artifact_change",
            phase=phase,
            run_id=run_id,
            staged_canonical_paths=canonical_paths,
            actual_dirty_generated_paths=dirty_generated,
            actual_staged_generated_paths=staged_generated,
            detected_stale_generated_paths=detected_stale_generated_paths,
            attributable_stale_generated_paths=[],
            unattributed_generated_paths=[],
            details={"offending": dirty_generated},
        )

    # Reject mixed authored/generated commit (generated files staged)
    if staged_generated:
        return HookPolicyResult(
            allowed=False,
            reason="generated_artifact_mixed_with_authored_commit",
            phase=phase,
            run_id=run_id,
            staged_canonical_paths=canonical_paths,
            actual_dirty_generated_paths=dirty_generated,
            actual_staged_generated_paths=staged_generated,
            detected_stale_generated_paths=detected_stale_generated_paths,
            attributable_stale_generated_paths=[],
            unattributed_generated_paths=[],
            details={"offending": staged_generated},
        )

    # Partition stale paths into attributable and unattributed
    attributable, unattributed = _attribute_stale_paths(
        detected_stale_generated_paths, canonical_paths, sync_mod,
    )

    # Apply-phase allowance: allow attributable stale targets
    if phase == "apply_change":
        if unattributed:
            return HookPolicyResult(
                allowed=False,
                reason="unattributed_generated_drift",
                phase=phase,
                run_id=run_id,
                staged_canonical_paths=canonical_paths,
                actual_dirty_generated_paths=dirty_generated,
                actual_staged_generated_paths=staged_generated,
                detected_stale_generated_paths=detected_stale_generated_paths,
                attributable_stale_generated_paths=attributable,
                unattributed_generated_paths=unattributed,
                details={"offending": unattributed},
            )
        # All stale paths are attributable (or none exist) -> allow
        return HookPolicyResult(
            allowed=True,
            reason=None,
            phase=phase,
            run_id=run_id,
            staged_canonical_paths=canonical_paths,
            actual_dirty_generated_paths=dirty_generated,
            actual_staged_generated_paths=staged_generated,
            detected_stale_generated_paths=detected_stale_generated_paths,
            attributable_stale_generated_paths=attributable,
            unattributed_generated_paths=unattributed,
            details={},
        )

    # Non-apply phase: stale targets are NOT allowed (strict)
    if detected_stale_generated_paths:
        return HookPolicyResult(
            allowed=False,
            reason="unattributed_generated_drift",
            phase=phase,
            run_id=run_id,
            staged_canonical_paths=canonical_paths,
            actual_dirty_generated_paths=dirty_generated,
            actual_staged_generated_paths=staged_generated,
            detected_stale_generated_paths=detected_stale_generated_paths,
            attributable_stale_generated_paths=attributable,
            unattributed_generated_paths=detected_stale_generated_paths,
            details={},
        )

    # No stale paths, no generated issues -> allow
    return HookPolicyResult(
        allowed=True,
        reason=None,
        phase=phase,
        run_id=run_id,
        staged_canonical_paths=canonical_paths,
        actual_dirty_generated_paths=dirty_generated,
        actual_staged_generated_paths=staged_generated,
        detected_stale_generated_paths=detected_stale_generated_paths,
        attributable_stale_generated_paths=attributable,
        unattributed_generated_paths=unattributed,
        details={},
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase-aware pre-commit hook policy for derived-artifact drift."
    )
    parser.add_argument("--root", default=".", help="repository checkout root path")
    parser.add_argument("--json", action="store_true", help="emit structured JSON result")
    args = parser.parse_args()

    root = os.path.normpath(args.root)

    # Resolve phase from workflow runtime state
    try:
        phase, run_id = resolve_phase(root)
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "allowed": False}, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Collect Git entries
    try:
        staged_entries = discover_staged_entries(root)
        worktree_entries = discover_worktree_entries(root)
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "allowed": False}, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # For stale-path detection, we would run the full read-only sync check here.
    # For now, the hook policy is a pure function of the provided inputs; the
    # shell hook integration (Slice 3) will wire the sync check output.
    detected_stale: list[str] = []

    result = evaluate_policy(
        root=root,
        staged_entries=staged_entries,
        worktree_entries=worktree_entries,
        detected_stale_generated_paths=detected_stale,
        phase=phase,
        run_id=run_id,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.allowed:
            print(f"OK: policy allows commit (phase={result.phase})")
        else:
            print(f"BLOCKED: {result.reason}", file=sys.stderr)
            if result.unattributed_generated_paths:
                print(f"  unattributed: {', '.join(result.unattributed_generated_paths)}",
                      file=sys.stderr)
            if result.actual_dirty_generated_paths:
                print(f"  dirty generated: {', '.join(result.actual_dirty_generated_paths)}",
                      file=sys.stderr)
            if result.actual_staged_generated_paths:
                print(f"  staged generated: {', '.join(result.actual_staged_generated_paths)}",
                      file=sys.stderr)

    return 0 if result.allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())