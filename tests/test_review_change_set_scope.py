"""Executable Git fixtures for review-agent live change-set scope.

These tests prove the review scope contract used by agents/review-agent.md:
live Git commands report only actually authored changes. Stale generated copies
that are not written by implementation do not become part of the review change
set, while manually edited generated copies are visible to review.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


CANONICAL_AGENT = """---
name: review-agent
---
# Review Agent

Original body.
"""

DERIVED_AGENT = """---
name: review-agent
model: test-model
variant: medium
---
# Review Agent

Original body.
"""


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )


def write_file(repo: Path, relpath: str, content: str) -> None:
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def setup_review_scope_repo(repo: Path) -> str:
    """Create a temporary repo with canonical and derived review-agent files."""
    run_git(repo, "init", "--initial-branch=main")
    run_git(repo, "config", "user.email", "test@example.com")
    run_git(repo, "config", "user.name", "Test User")

    write_file(repo, "agents/review-agent.md", CANONICAL_AGENT)
    write_file(repo, ".opencode/agents/review-agent.md", DERIVED_AGENT)
    write_file(repo, ".claude/agents/review-agent.md", DERIVED_AGENT)
    write_file(repo, ".cursor/agents/review-agent.md", DERIVED_AGENT)
    run_git(repo, "add", ".")
    run_git(repo, "commit", "--no-verify", "-m", "initial")
    return run_git(repo, "rev-parse", "HEAD").stdout.strip()


def changed_paths_from_git_scope(repo: Path) -> set[str]:
    """Mirror review-agent live change discovery commands as a path set."""
    unstaged = set(run_git(repo, "diff", "--name-only").stdout.splitlines())
    staged = set(run_git(repo, "diff", "--cached", "--name-only").stdout.splitlines())
    untracked = set(
        run_git(repo, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    )
    return unstaged | staged | untracked


@pytest.mark.parametrize("stage_canonical", [False, True])
def test_stale_unwritten_derived_paths_are_absent_from_live_git_scope(
    tmp_path: Path, stage_canonical: bool
) -> None:
    """Canonical edit alone must not synthesize stale derived paths into review.

    The derived files are now stale relative to the authored canonical content,
    but because implementation did not write them, Git's live review commands
    report only the canonical file.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    setup_review_scope_repo(repo)

    write_file(
        repo,
        "agents/review-agent.md",
        CANONICAL_AGENT.replace("Original body.", "Updated canonical body."),
    )
    if stage_canonical:
        run_git(repo, "add", "agents/review-agent.md")

    assert changed_paths_from_git_scope(repo) == {"agents/review-agent.md"}

    stale_but_unwritten = {
        ".opencode/agents/review-agent.md",
        ".claude/agents/review-agent.md",
        ".cursor/agents/review-agent.md",
    }
    assert not stale_but_unwritten & set(
        run_git(repo, "diff", "--name-only").stdout.splitlines()
    )
    assert not stale_but_unwritten & set(
        run_git(repo, "diff", "--cached", "--name-only").stdout.splitlines()
    )
    assert not stale_but_unwritten & set(
        run_git(repo, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    )


def test_manually_modified_derived_path_is_visible_to_live_git_scope(
    tmp_path: Path,
) -> None:
    """A generated file actually edited in the worktree remains review-visible."""
    repo = tmp_path / "repo"
    repo.mkdir()
    setup_review_scope_repo(repo)

    write_file(
        repo,
        ".opencode/agents/review-agent.md",
        DERIVED_AGENT.replace("Original body.", "Manual generated edit."),
    )

    assert ".opencode/agents/review-agent.md" in changed_paths_from_git_scope(repo)
    assert ".opencode/agents/review-agent.md" in run_git(
        repo, "diff", "--name-only"
    ).stdout.splitlines()
    assert " .opencode/agents/review-agent.md" in run_git(
        repo, "status", "--short"
    ).stdout


def test_staged_and_committed_derived_paths_are_visible_to_git_review_ranges(
    tmp_path: Path,
) -> None:
    """Generated files staged or committed inside a range remain review-visible."""
    repo = tmp_path / "repo"
    repo.mkdir()
    base_ref = setup_review_scope_repo(repo)

    write_file(
        repo,
        ".claude/agents/review-agent.md",
        DERIVED_AGENT.replace("Original body.", "Staged generated edit."),
    )
    run_git(repo, "add", ".claude/agents/review-agent.md")

    assert ".claude/agents/review-agent.md" in run_git(
        repo, "diff", "--cached", "--name-only"
    ).stdout.splitlines()

    run_git(repo, "commit", "--no-verify", "-m", "commit generated edit")
    assert ".claude/agents/review-agent.md" in run_git(
        repo, "diff", "--name-only", f"{base_ref}..HEAD"
    ).stdout.splitlines()
