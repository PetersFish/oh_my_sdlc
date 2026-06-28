"""Behavior tests for scripts/install_agents.py."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts", "install_agents.py",
)


def write_file(root: str, relpath: str, content: str) -> None:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_install(source: str, target: str, *extra_args: str):
    args = [
        sys.executable,
        SCRIPT,
        "--source", source,
        "--target", target,
        *extra_args,
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestInstallAgents(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source_root = os.path.join(self.tmp, "repo")
        self.source_agents = os.path.join(self.source_root, "agents")
        self.target = os.path.join(self.tmp, "target")
        os.makedirs(self.source_agents, exist_ok=True)

        write_file(self.source_root, "agents/dev-orchestrator.md", "# dev\n")
        write_file(self.source_root, "agents/review-agent.md", "# review\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_fresh_install_writes_files_and_repo_root_metadata(self):
        rc, stdout, stderr = run_install(
            self.source_agents,
            self.target,
            "--source-ref", "TESTREF",
        )
        self.assertEqual(rc, 0, f"fresh install should succeed, stdout={stdout!r} stderr={stderr!r}")
        self.assertTrue(os.path.exists(os.path.join(self.target, "dev-orchestrator.md")))
        self.assertTrue(os.path.exists(os.path.join(self.target, "review-agent.md")))

        metadata = read_json(os.path.join(self.target, ".agent-install.json"))
        self.assertEqual(metadata["source_ref"], "TESTREF")
        self.assertEqual(
            os.path.realpath(metadata["source_repo"]),
            os.path.realpath(self.source_root),
            "source_repo should default to the repo root, not agents/ itself",
        )
        self.assertEqual(sorted(metadata["files"].keys()), ["dev-orchestrator.md", "review-agent.md"])

    def test_second_install_without_force_fails_and_does_not_refresh_metadata(self):
        rc1, stdout1, stderr1 = run_install(
            self.source_agents,
            self.target,
            "--source-ref", "FIRSTREF",
        )
        self.assertEqual(rc1, 0, f"first install should succeed, stdout={stdout1!r} stderr={stderr1!r}")
        original_metadata = read_json(os.path.join(self.target, ".agent-install.json"))

        write_file(self.source_root, "agents/review-agent.md", "# review updated\n")

        rc2, stdout2, stderr2 = run_install(
            self.source_agents,
            self.target,
            "--source-ref", "SECONDREF",
        )
        self.assertNotEqual(rc2, 0, "install without --force must fail when target files already exist")
        combined = f"{stdout2}\n{stderr2}"
        self.assertIn("--force", combined)

        current_review = open(os.path.join(self.target, "review-agent.md"), encoding="utf-8").read()
        self.assertEqual(current_review, "# review\n", "target content must remain unchanged on failed install")

        metadata = read_json(os.path.join(self.target, ".agent-install.json"))
        self.assertEqual(metadata["source_ref"], original_metadata["source_ref"])
        self.assertEqual(metadata["installed_at"], original_metadata["installed_at"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
