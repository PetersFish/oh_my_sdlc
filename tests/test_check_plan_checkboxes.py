import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = os.path.join("scripts", "check_plan_checkboxes.py")


def run_script(plan_path: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, SCRIPT, plan_path],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestCheckPlanCheckboxes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.plan = Path(self.tmp) / "plan.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def test_all_checked_exit_0(self):
        self.plan.write_text(
            "# Plan\n\n"
            "- [x] **Step 1: do thing**\n\n"
            "- [x] **Step 2: do other thing**\n"
        )
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 0)
        self.assertIn("all checkboxes complete", out)

    def test_unchecked_exit_1(self):
        self.plan.write_text(
            "# Plan\n\n"
            "- [ ] **Step 1: do thing**\n\n"
            "- [x] **Step 2: do other thing**\n"
        )
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 1)
        self.assertIn("unchecked checkbox", out)
        self.assertIn("Step 1", out)

    def test_no_checkboxes_exit_0(self):
        self.plan.write_text("# Plan\n\nNo steps here.\n")
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 0)
        self.assertIn("all checkboxes complete", out)

    def test_missing_file_exit_2(self):
        rc, _, err = run_script(str(Path(self.tmp) / "nope.md"))
        self.assertEqual(rc, 2)
        self.assertIn("file not found", err)

    def test_mixed_checked_unchecked_exit_1(self):
        self.plan.write_text(
            "### Task 1\n\n"
            "- [x] **Step 1: write test**\n\n"
            "- [ ] **Step 2: run test**\n\n"
            "- [ ] **Step 3: implement**\n\n"
            "### Task 2\n\n"
            "- [x] **Step 1: commit**\n"
        )
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 1)
        self.assertIn("2 unchecked", out)
        self.assertIn("Step 2", out)
        self.assertIn("Step 3", out)
        self.assertNotIn("Step 1", out)

    def test_indented_checkbox_detected(self):
        self.plan.write_text(
            "# Plan\n\n"
            "  - [ ] **Step 1: indented**\n"
        )
        rc, out, _ = run_script(str(self.plan))
        self.assertEqual(rc, 1)
        self.assertIn("Step 1", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
