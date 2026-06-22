# Fix Roadmap Item Status Loader Filename Bug

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `loader_roadmap_item_status` to find roadmap item files by frontmatter `id` field instead of hardcoding `{item_id}.md`, which fails when real-world filenames include a slug suffix (e.g., `RM-ORCH-006-multi-run-concurrent-support.md`).

**Architecture:** Replace the two-line filename construction + existence check with a filename-agnostic scan that iterates all `.md` files in the items directory, parses frontmatter, and matches on the `id` field — the same pattern already used by `_find_roadmap_items`.

**Tech Stack:** Python 3, YAML frontmatter parsing

---

### Task 1: Write failing test with slug filenames

**Files:**
- Modify: `tests/test_workflow.py` (add test method)

- [ ] **Step 1: Add a `_make_roadmap_item_with_slug` helper and a failing test to `TestPostArchiveHooks`**

Current helper `_make_roadmap_item` writes `{item_id}.md` — the bug is invisible. Add a helper that writes `{item_id}-{slug}.md` to reproduce the real-world filename pattern.

```python
def _make_roadmap_item_with_slug(self, item_id, slug, status, openspec_change=None, area="area1", completed_at=None):
    items_dir = os.path.join(
        self.tmp, ".ai", "roadmap", "areas", area, "items"
    )
    os.makedirs(items_dir, exist_ok=True)
    fm = f"id: {item_id}\nstatus: {status}\n"
    if openspec_change:
        fm += f"openspec_change: {openspec_change}\n"
    if completed_at:
        fm += f"completed_at: {completed_at}\n"
    content = f"---\n{fm}---\n# {item_id}\n"
    fpath = os.path.join(items_dir, f"{item_id}-{slug}.md")
    with open(fpath, "w") as f:
        f.write(content)

def test_roadmap_done_hook_with_slug_filename(self):
    """roadmap_done_if_relevant hook resolves 'done' when item file has slug suffix."""
    self._start_archived_workflow("slug-test", [
        {"item_id": "RM-SLUG-001", "status": "active", "openspec_change": "slug-test"},
    ])
    # Overwrite with slug-named file to mimic real project layout
    # The loader must find it by frontmatter id, not filename
    items_dir = os.path.join(
        self.tmp, ".ai", "roadmap", "areas", "area1", "items"
    )
    # Remove the flat-named file created by _start_archived_workflow
    os.remove(os.path.join(items_dir, "RM-SLUG-001.md"))
    # Create slug-named file with done status
    self._make_roadmap_item_with_slug(
        "RM-SLUG-001", "my-feature-slug", "done",
        openspec_change="slug-test", completed_at="2026-06-22",
    )
    self._add_hook("roadmap_done_if_relevant")

    rc, out, _ = run_workflow(
        self.tmp, "complete-hook",
        hook="roadmap_done_if_relevant",
    )
    self.assertEqual(rc, 0)
    data = json.loads(out)
    self.assertEqual(data["evidence"]["roadmap_hook_resolution"], "idempotent_done")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_workflow.py::TestPostArchiveHooks::test_roadmap_done_hook_with_slug_filename -v
```
Expected: FAIL — `loader_roadmap_item_status` returns `None` for slug filenames, hook blocks.

---

### Task 2: Fix `loader_roadmap_item_status`

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py:389-404` (replace the loader body)

- [ ] **Step 1: Replace filename construction with frontmatter-id scan**

```python
def loader_roadmap_item_status(root, item_id):
    """Read the status of a specific roadmap item."""
    if not item_id:
        return None
    areas_dir = _resolve_path(root, ".ai/roadmap/areas")
    for area in _list_dirs(areas_dir):
        items_dir = os.path.join(areas_dir, area, "items")
        if not os.path.isdir(items_dir):
            continue
        for fname in _list_dirs(items_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(items_dir, fname)
            fm_id = _read_frontmatter_field(fpath, "id")
            if fm_id == item_id:
                return {
                    "item_id": item_id,
                    "status": _read_frontmatter_field(fpath, "status"),
                    "completed_at": _read_frontmatter_field(fpath, "completed_at"),
                }
    return None
```

- [ ] **Step 2: Run the previously-failing test to verify it passes**

```bash
python3 -m pytest tests/test_workflow.py::TestPostArchiveHooks::test_roadmap_done_hook_with_slug_filename -v
```
Expected: PASS

---

### Task 3: Run full test suite and sync templates

**Files:**
- No new modifications (canonical sync only)

- [ ] **Step 1: Run full test suite**

```bash
python3 -m pytest tests/test_workflow.py -v
```
Expected: all tests pass

- [ ] **Step 2: Sync canonical template**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
```

- [ ] **Step 3: Verify no template drift**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check
```
Expected: OK

- [ ] **Step 4: Distribute to skill copies**

```bash
python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py --source-repo . --skill-name sdlc-project-bootstrap --source-ref HEAD --target .opencode/skills/sdlc-project-bootstrap --status stable
python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py --source-repo . --skill-name sdlc-project-bootstrap --source-ref HEAD --target .claude/skills/sdlc-project-bootstrap --status stable
python3 skills/meta-skill-lifecycle-governance/scripts/install_skill.py --source-repo . --skill-name sdlc-project-bootstrap --source-ref HEAD --target .cursor/skills/sdlc-project-bootstrap --status stable
```
