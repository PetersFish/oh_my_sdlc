# Derived Artifact Sync Phase Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Execute one bounded slice at a time and keep checkboxes synchronized.

**Goal:** Move write-producing derived-artifact sync out of `implement-agent` and into `finish-agent`, and make `install_skill.py` a no-op when the target payload is unchanged, eliminating review-scope churn.

**Architecture:** `implement-agent` runs only read-only derived-sync checks during `apply_change` and returns blocked if drift is detected. `finish-agent` owns write-producing sync as post-review cleanup. `install_skill.py` compares payload hash before reinstall and skips all writes when unchanged.

**Tech Stack:** Python standard library, pytest/unittest, Markdown agent contracts, Git CLI.

**Primary Spec:** `docs/superpowers/specs/2026-07-13-derived-sync-phase-boundary-design.md`

---

## File Structure

- Modify: `skills/meta-skill-lifecycle-governance/scripts/install_skill.py` — no-op on unchanged payload
- Modify: `agents/implement-agent.md` — Derived Sync Restriction section + permission deny rules
- Modify: `agents/finish-agent.md` — strengthen Derived Artifact Sync ownership wording
- Create: `tests/test_install_skill.py` — no-op and changed-payload behavior tests
- Modify: `tests/test_wrapper_contracts.py` — implement/finish agent contract assertion additions
- Modify: distributed copies under `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`
- Modify: distributed copies under `.opencode/skills/meta-skill-lifecycle-governance/scripts/`

---

## Slice 1: install_skill.py No-Op on Unchanged Payload

### Task 1: Write Failing Tests for install_skill.py No-Op Behavior

**Files:**
- Create: `tests/test_install_skill.py`

- [x] **Step  Write failing tests for no-op and changed-payload behavior**

```python
#!/usr/bin/env python3
"""Behavioral tests for install_skill.py no-op-on-unchanged-payload behavior."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL_SKILL = REPO_ROOT / "skills" / "meta-skill-lifecycle-governance" / "scripts" / "install_skill.py"


def _run_install(source_repo, skill_name, target, source_ref="HEAD", status="stable"):
    result = subprocess.run(
        [
            sys.executable, str(INSTALL_SKILL),
            "--source-repo", str(source_repo),
            "--skill-name", skill_name,
            "--source-ref", source_ref,
            "--target", str(target),
            "--status", status,
        ],
        capture_output=True, text=True,
    )
    return result


class TestInstallSkillNoOp(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="install-skill-test-")
        self.source_repo = tempfile.mkdtemp(prefix="source-repo-")
        skill_dir = pathlib.Path(self.source_repo) / "skills" / "demo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Demo Skill\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        shutil.rmtree(self.source_repo, ignore_errors=True)

    def test_second_install_with_unchanged_payload_is_noop(self):
        target = pathlib.Path(self.tmpdir) / "demo-skill"
        r1 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r1.returncode, 0)
        metadata_path = target / ".skill-install.json"
        original_metadata = metadata_path.read_text()
        original_mtime = metadata_path.stat().st_mtime_ns

        r2 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r2.returncode, 0)
        new_metadata = metadata_path.read_text()
        new_mtime = metadata_path.stat().st_mtime_ns

        self.assertEqual(original_metadata, new_metadata,
                         "metadata file must be byte-identical on no-op install")
        self.assertEqual(original_mtime, new_mtime,
                         "metadata file mtime must not change on no-op install")

    def test_install_with_changed_payload_updates_metadata(self):
        target = pathlib.Path(self.tmpdir) / "demo-skill"
        r1 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r1.returncode, 0)
        original_metadata = (target / ".skill-install.json").read_text()

        skill_md = pathlib.Path(self.source_repo) / "skills" / "demo-skill" / "SKILL.md"
        skill_md.write_text("# Demo Skill v2\nMore content.\n")

        r2 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r2.returncode, 0)
        new_metadata = (target / ".skill-install.json").read_text()

        self.assertNotEqual(original_metadata, new_metadata,
                            "metadata must change when payload changes")

    def test_noop_preserves_target_file_mtime(self):
        target = pathlib.Path(self.tmpdir) / "demo-skill"
        r1 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r1.returncode, 0)
        skill_md = target / "SKILL.md"
        original_mtime = skill_md.stat().st_mtime_ns

        r2 = _run_install(self.source_repo, "demo-skill", target)
        self.assertEqual(r2.returncode, 0)
        new_mtime = skill_md.stat().st_mtime_ns

        self.assertEqual(original_mtime, new_mtime,
                         "target file mtime must not change on no-op install")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step  Run tests to verify they fail**

Run: `python3 -m pytest tests/test_install_skill.py -v`
Expected: FAIL — second install overwrites metadata with fresh timestamp, mtime changes.

### Task 2: Implement No-Op Logic in install_skill.py

**Files:**
- Modify: `skills/meta-skill-lifecycle-governance/scripts/install_skill.py`

- [x] **Step  Add payload comparison before reinstall**

Replace the body of `main()` with logic that:

```python
def _existing_target_metadata(target_dir: Path) -> dict | None:
    metadata_path = target_dir / ".skill-install.json"
    if not metadata_path.exists():
        return None
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a skill into a target directory.")
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--status", default="stable")
    args = parser.parse_args()

    source_skill = Path(args.source_repo) / "skills" / args.skill_name
    target_dir = Path(args.target)
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    # Compute source payload hash without writing to target.
    source_payload_hash, source_files = _compute_source_payload(source_skill)

    # Check if target already has identical payload.
    existing = _existing_target_metadata(target_dir)
    if existing is not None:
        existing_hash = existing.get("payload_hash", "")
        existing_files = existing.get("files", [])
        if existing_hash == source_payload_hash and existing_files == source_files:
            # No-op: payload unchanged, skip all writes.
            print(json.dumps(existing, indent=2))
            return 0

    # Payload differs or target missing — install normally.
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_skill, target_dir)

    payload_hash, files = _compute_payload(target_dir)
    metadata = build_install_metadata(
        skill_name=args.skill_name,
        source_repo=args.source_repo,
        source_ref=args.source_ref,
        status=args.status,
        target=str(target_dir),
        payload_hash=payload_hash,
        files=files,
    )
    (target_dir / ".skill-install.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0
```

Also add `_compute_source_payload` and `_existing_target_metadata` helper functions:

```python
def _compute_source_payload(source_dir: Path) -> tuple[str, list[str]]:
    files = sorted(
        str(p.relative_to(source_dir))
        for p in source_dir.rglob("*")
        if p.is_file()
        and p.name not in (".skill-install.json", ".DS_Store")
        and "__pycache__" not in p.parts
    )
    hasher = hashlib.sha256()
    for f in files:
        hasher.update((source_dir / f).read_bytes())
        hasher.update(b"\x00")
    return hasher.hexdigest(), files
```

- [x] **Step  Run tests to verify they pass**

Run: `python3 -m pytest tests/test_install_skill.py -v`
Expected: PASS

- [x] **Step  Run existing lifecycle and sync tests to verify no regressions**

Run: `python3 -m pytest tests/test_lifecycle_utils.py tests/test_sync_derived_artifacts.py -v`
Expected: PASS

- [x] **Step  Commit**

```bash
git add tests/test_install_skill.py skills/meta-skill-lifecycle-governance/scripts/install_skill.py
git commit -m "feat(install_skill): no-op on unchanged payload to prevent timestamp churn"
```

---

## Slice 2: implement-agent Derived Sync Restriction

### Task 3: Write Failing Contract Tests for implement-agent Derived Sync Restriction

**Files:**
- Modify: `tests/test_wrapper_contracts.py`

- [x] **Step  Add failing tests asserting implement-agent forbids --fix and install_skill**

Add to `tests/test_wrapper_contracts.py` in the implement-agent contract test class:

```python
def test_implement_agent_forbids_derived_sync_fix(self):
    body = self._read_agent_body("implement-agent")
    self.assertIn("MUST NOT run `sync_derived_artifacts.py --fix`", body,
                  "implement-agent must explicitly forbid --fix during apply_change")

def test_implement_agent_forbids_setup_agents_force(self):
    body = self._read_agent_body("implement-agent")
    self.assertIn("MUST NOT run `setup_agents.py --force`", body,
                  "implement-agent must explicitly forbid setup_agents --force")

def test_implement_agent_forbids_install_skill(self):
    body = self._read_agent_body("implement-agent")
    self.assertIn("MUST NOT run `install_skill.py`", body,
                  "implement-agent must explicitly forbid install_skill.py")

def test_implement_agent_may_run_read_only_check(self):
    body = self._read_agent_body("implement-agent")
    self.assertIn("sync_derived_artifacts.py --check", body,
                  "implement-agent may run read-only --check")
```

- [x] **Step  Run tests to verify they fail**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -k "test_implement_agent_forbids" -v`
Expected: FAIL — strings not yet present in implement-agent.md.

### Task 4: Add Derived Sync Restriction Section to implement-agent.md

**Files:**
- Modify: `agents/implement-agent.md`

- [x] **Step  Add restriction section after "Producer-Owned Cleanup"**

Insert after the "Producer-Owned Cleanup" section:

```markdown
## Derived Sync Restriction

During `apply_change`, you MUST NOT run any write-producing derived-artifact
sync command. Specifically:

- MUST NOT run `sync_derived_artifacts.py --fix`.
- MUST NOT run `setup_agents.py --force`.
- MUST NOT run `install_skill.py`.

You MAY run read-only checks to detect drift:

- `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git`
- `python3 scripts/sync_templates.py --check`

If the read-only check reports drift, return `status: blocked` with:

```json
{
  "blockers": [
    {
      "reason": "derived_artifact_drift_detected",
      "message": "Derived artifact drift detected. Deferred to finish-agent.",
      "recommended_action": "defer_to_finish_agent"
    }
  ],
  "recommended_next_action": "dispatch_review_agent"
}
```

Derived-artifact sync is owned by `finish-agent` during post-review cleanup.
This boundary prevents review-scope churn from generated/distributed files.
```

- [x] **Step  Run contract tests to verify they pass**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -k "test_implement_agent_forbids" -v`
Expected: PASS

- [x] **Step  Commit**

```bash
git add agents/implement-agent.md tests/test_wrapper_contracts.py
git commit -m "feat(implement-agent): forbid write-producing derived sync during apply_change"
```

---

## Slice 3: finish-agent Derived Sync Ownership Strengthening

### Task 5: Write Failing Contract Test for finish-agent Strengthened Ownership

**Files:**
- Modify: `tests/test_wrapper_contracts.py`

- [x] **Step  Add failing test asserting finish-agent owns write-producing sync**

```python
def test_finish_agent_owns_write_producing_derived_sync(self):
    body = self._read_agent_body("finish-agent")
    self.assertIn("owns write-producing derived-artifact sync", body,
                  "finish-agent must explicitly own write-producing derived sync")
```

### Task 6: Strengthen finish-agent Derived Artifact Sync Section

**Files:**
- Modify: `agents/finish-agent.md`

- [x] **Step  Add ownership statement to existing Derived Artifact Sync section**

Prepend to the existing "Derived Artifact Sync" section:

```markdown
## Derived Artifact Sync

`finish-agent` owns write-producing derived-artifact sync. During
`post_archive_actions`, after source changes are reviewed and accepted,
run the full sync cycle:

1. `python3 scripts/sync_derived_artifacts.py --check`
2. If drift is reported: `python3 scripts/sync_derived_artifacts.py --fix`
3. Re-run `python3 scripts/sync_derived_artifacts.py --check` and block until clean.

Generated derived-artifact changes are finish cleanup evidence, not
implementation change-set evidence. `implement-agent` is forbidden from
running write-producing sync during `apply_change`.
```

- [x] **Step  Run contract tests to verify they pass**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -k "test_finish_agent_owns_write_producing" -v`
Expected: PASS

- [x] **Step  Commit**

```bash
git add agents/finish-agent.md tests/test_wrapper_contracts.py
git commit -m "feat(finish-agent): strengthen write-producing derived sync ownership"
```

---

## Slice 4: Template and Distributed-Copy Sync

### Task 7: Sync Canonical Changes to Distributed Copies

**Files:**
- Modify: `.opencode/agents/implement-agent.md`, `.opencode/agents/finish-agent.md`
- Modify: `.claude/agents/implement-agent.md`, `.claude/agents/finish-agent.md`
- Modify: `.cursor/agents/implement-agent.md`, `.cursor/agents/finish-agent.md`
- Modify: `.opencode/skills/meta-skill-lifecycle-governance/scripts/install_skill.py`
- Modify: `.claude/skills/meta-skill-lifecycle-governance/scripts/install_skill.py`
- Modify: `.cursor/skills/meta-skill-lifecycle-governance/scripts/install_skill.py`

- [x] **Step  Run derived artifact sync in check mode**

Run: `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git`
Expected: Reports drift.

- [x] **Step  Run derived artifact sync in fix mode**

Run: `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git`
Expected: Syncs canonical to distributed copies.

- [x] **Step  Re-run check to verify clean**

Run: `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git`
Expected: OK, all suites in sync.

- [x] **Step  Commit**

```bash
git add .opencode/ .claude/ .cursor/
git commit -m "sync: distribute derived-sync phase boundary changes to all CLI targets"
```

---

## Slice 5: Integration Verification

### Task 8: Run Full Regression and Contract Validation

- [x] **Step  Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass, 0 failures.

- [x] **Step  Run derived artifact sync check**

Run: `python3 scripts/sync_derived_artifacts.py --check`
Expected: OK, all suites in sync.

- [x] **Step  Verify plan checkboxes**

Run: `python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-13-derived-sync-phase-boundary.md`
Expected: All checkboxes complete.

- [x] **Step  Commit any remaining changes**

```bash
git add -A
git commit -m "test: full regression pass for derived-sync phase boundary"
```

---

## Verification Summary

After all slices complete:

```bash
python3 -m pytest tests/ -v
python3 scripts/sync_derived_artifacts.py --check
```