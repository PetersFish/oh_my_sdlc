#!/usr/bin/env python3
"""Behavioral tests for scripts/safe_delete.py — repository-scoped safe deletion."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "safe_delete.py",
)


def run_safe_delete(root: str, *paths: str, recursive: bool = False) -> tuple[int, str, str]:
    args = [sys.executable, SCRIPT, "--root", root]
    if recursive:
        args.append("--recursive")
    args.extend(paths)
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def write_file(root: str, relpath: str, content: str = "x\n") -> str:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestSafeDelete(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_safe_delete_removes_repo_relative_file(self):
        target = write_file(self.tmp, "victim.txt")
        rc, out, _ = run_safe_delete(self.tmp, "victim.txt")
        self.assertEqual(rc, 0, f"expected rc=0, got stdout={out!r}")
        self.assertFalse(os.path.exists(target), "file should be deleted")
        report = json.loads(out)
        self.assertIn("deleted", report)
        self.assertEqual(report["deleted"][0]["path"], "victim.txt")
        self.assertEqual(report["deleted"][0]["kind"], "file")

    def test_safe_delete_rejects_absolute_path(self):
        target = write_file(self.tmp, "victim.txt")
        rc, out, _ = run_safe_delete(self.tmp, str(os.path.realpath(target)))
        self.assertEqual(rc, 1, f"absolute path must be refused, got stdout={out!r}")
        self.assertTrue(os.path.exists(target), "file must NOT be deleted when path is absolute")
        report = json.loads(out)
        self.assertEqual(report["refused"][0]["reason"], "absolute_path_forbidden")

    def test_safe_delete_rejects_protected_memory_path(self):
        protected = write_file(self.tmp, ".ai/memory/keep.md", "keep")
        rc, out, _ = run_safe_delete(self.tmp, ".ai/memory/keep.md")
        self.assertEqual(rc, 1, f"protected path must be refused, got stdout={out!r}")
        self.assertTrue(os.path.exists(protected), "protected memory file must NOT be deleted")
        report = json.loads(out)
        self.assertEqual(report["refused"][0]["reason"], "protected_path")

    def test_safe_delete_rejects_protected_git_path(self):
        protected = write_file(self.tmp, ".git/config", "git-config")
        rc, out, _ = run_safe_delete(self.tmp, ".git/config")
        self.assertEqual(rc, 1, f"protected .git path must be refused, got stdout={out!r}")
        self.assertTrue(os.path.exists(protected), "protected .git file must NOT be deleted")
        report = json.loads(out)
        self.assertEqual(report["refused"][0]["reason"], "protected_path")

    def test_safe_delete_rejects_path_escape(self):
        # Create a file outside root via a symlink-style escape attempt
        outside = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        with open(os.path.join(outside, "secret.txt"), "w") as f:
            f.write("secret")
        rc, out, _ = run_safe_delete(self.tmp, "../secret.txt")
        self.assertEqual(rc, 1, f"escape path must be refused, got stdout={out!r}")
        report = json.loads(out)
        self.assertEqual(report["refused"][0]["reason"], "path_escape_forbidden")

    def test_safe_delete_skips_missing_file(self):
        rc, out, _ = run_safe_delete(self.tmp, "does-not-exist.txt")
        self.assertEqual(rc, 0, f"missing file should be skipped, got stdout={out!r}")
        report = json.loads(out)
        self.assertEqual(report["skipped"][0]["reason"], "missing")

    def test_safe_delete_requires_recursive_for_directory(self):
        write_file(self.tmp, "dir/inner.txt", "x")
        rc, out, _ = run_safe_delete(self.tmp, "dir")
        self.assertEqual(rc, 1, f"directory without --recursive must be refused, got stdout={out!r}")
        report = json.loads(out)
        self.assertEqual(report["refused"][0]["reason"], "recursive_required")

    def test_safe_delete_recursive_removes_directory(self):
        write_file(self.tmp, "dir/inner.txt", "x")
        rc, out, _ = run_safe_delete(self.tmp, "dir", "--recursive") if False else run_safe_delete(self.tmp, "dir", recursive=True)
        self.assertEqual(rc, 0, f"recursive directory delete should succeed, got stdout={out!r}")
        report = json.loads(out)
        self.assertEqual(report["deleted"][0]["kind"], "directory")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "dir")))

    def test_safe_delete_mixed_batch_reports_deleted_and_refused(self):
        write_file(self.tmp, "ok.txt")
        write_file(self.tmp, ".ai/memory/keep.md", "keep")
        rc, out, _ = run_safe_delete(self.tmp, "ok.txt", ".ai/memory/keep.md")
        self.assertEqual(rc, 1, "refused entries must cause non-zero exit")
        report = json.loads(out)
        deleted_paths = [e["path"] for e in report["deleted"]]
        refused_paths = [e["path"] for e in report["refused"]]
        self.assertIn("ok.txt", deleted_paths)
        self.assertIn(".ai/memory/keep.md", refused_paths)


if __name__ == "__main__":
    unittest.main(verbosity=2)