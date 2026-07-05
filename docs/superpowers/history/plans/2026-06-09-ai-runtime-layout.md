# AI Runtime Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move SDLC skill runtime state from scattered root directories into `.ai/`, using `.ai/memory` for repository memory and `.ai/roadmap` for roadmap state, while preserving read compatibility with existing `.ai-memory` and `.roadmap` projects.

**Architecture:** Add one shared path resolver under `skills/_lib/` and update SDLC scripts to use it instead of hard-coded `.ai-memory` or `.roadmap` paths. New initialization writes only to `.ai/...`; existing legacy directories remain readable as fallback until a later explicit migration/removal change.

**Tech Stack:** Python standard library, Markdown skill docs, pytest/unittest tests, repository-local skill copies under `skills/`, `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/`.

---

## Scope

In scope:
- Runtime layout: `.ai/memory` replaces new `.ai-memory` writes.
- Runtime layout: `.ai/roadmap` replaces new `.roadmap` writes.
- Legacy read fallback for `.ai-memory` and `.roadmap`.
- Skill docs, templates, tests, AGENTS memory block, and distributed copies.

Out of scope:
- Moving canonical skill source from `skills/`.
- Removing legacy fallback.
- Automatically migrating real user projects without explicit confirmation.
- Changing OpenSpec runtime layout under `openspec/`.

## File Structure

Create:
- `skills/_lib/sdlc_runtime_paths.py` — shared runtime path resolver for `.ai/memory`, `.ai/roadmap`, and legacy fallback detection.
- `tests/test_sdlc_runtime_paths.py` — unit tests for the resolver.

Modify:
- `skills/sdlc-repository-memory-init/scripts/init_memory.py` — create `.ai/memory` for new projects.
- `skills/sdlc-repository-memory-load/scripts/select_memory.py` — load `.ai/memory` first, then `.ai-memory` fallback.
- `skills/sdlc-repository-memory-load/scripts/validate_memory.py` — validate resolved memory directory.
- `skills/sdlc-repository-memory-sync/scripts/rebuild_index.py` — rebuild resolved memory index.
- `skills/sdlc-repository-memory-sync/scripts/reconcile_pending.py` — reconcile resolved memory files and queue.
- `skills/sdlc-repository-memory-sync/scripts/validate_memory.py` — validate resolved memory directory.
- `skills/sdlc-repository-memory-sync/scripts/update_manifest.py` — update resolved manifest.
- `skills/sdlc-repository-memory-sync/scripts/discover_modules.py` — exclude `.ai/` and read resolved discovery prefs.
- `skills/sdlc-repository-memory-sync/scripts/child_modules.py` — read/write resolved memory module and review queue paths.
- `skills/sdlc-repository-memory-sync/scripts/detect_state.py` — detect resolved manifest.
- `skills/sdlc-roadmap/scripts/validate.py` — validate `.ai/roadmap` first, legacy `.roadmap` fallback.
- `skills/sdlc-roadmap/scripts/rebuild_index.py` — rebuild `.ai/roadmap` first, legacy `.roadmap` fallback.
- `skills/sdlc-roadmap/scripts/list.py` — list `.ai/roadmap` first, legacy `.roadmap` fallback.
- `skills/sdlc-repository-memory-init/SKILL.md` — document `.ai/memory` as canonical runtime path.
- `skills/sdlc-repository-memory-load/SKILL.md` — document canonical path and legacy fallback.
- `skills/sdlc-repository-memory-load/templates/context-pack.md` — show `.ai/memory/...` paths.
- `skills/sdlc-repository-memory-sync/SKILL.md` — document canonical path and legacy fallback.
- `skills/sdlc-repository-memory-reset/SKILL.md` — reset `.ai/memory`, with legacy handling.
- `skills/sdlc-openspec-memory-sync/SKILL.md` — check `.ai/memory/manifest.json`, fallback `.ai-memory/manifest.json`.
- `skills/sdlc-project-bootstrap/SKILL.md` — initialize `.ai/memory` for new projects.
- `skills/sdlc-repository-memory-init/templates/AGENTS-memory-block.md` — update default memory-load reminder.
- `skills/sdlc-roadmap/SKILL.md` — document `.ai/roadmap` as canonical runtime path.
- `tests/test_repository_memory_init.py` — assert new init writes `.ai/memory`; add legacy fallback integration where relevant.
- `tests/test_repository_memory_load.py` — assert selection and validation use `.ai/memory`; add legacy fallback tests.
- `tests/test_repository_memory_sync.py` — update fixtures to `.ai/memory`; add fallback test for legacy `.ai-memory`.
- `tests/test_module_discovery.py` — update fixtures and excluded path expectations to `.ai/memory`/`.ai`.
- `tests/test_project_bootstrap_skills.py` — update bootstrap assertions to `.ai/memory`.
- `tests/test_sdlc_roadmap.py` — update default fixtures to `.ai/roadmap`; add legacy `.roadmap` fallback tests.
- `.opencode/skills/**` matching SDLC skills — refresh from canonical skills.
- `.claude/skills/**` matching SDLC skills — refresh from canonical skills.
- `.cursor/skills/**` matching SDLC skills — refresh from canonical skills.

Do not modify:
- Existing repository `.ai-memory/` runtime content in this repo unless the user explicitly asks to migrate this repository’s own memory after the code change.
- `openspec/` directory layout.

---

### Task 1: Add Shared Runtime Path Resolver

**Files:**
- Create: `skills/_lib/sdlc_runtime_paths.py`
- Create: `tests/test_sdlc_runtime_paths.py`

- [ ] **Step 1: Write failing resolver tests**

Create `tests/test_sdlc_runtime_paths.py` with:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATHS = REPO_ROOT / "skills" / "_lib" / "sdlc_runtime_paths.py"


def _load_runtime_paths():
    spec = importlib.util.spec_from_file_location("sdlc_runtime_paths", RUNTIME_PATHS)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_memory_path_defaults_to_ai_memory_namespace(tmp_path):
    runtime_paths = _load_runtime_paths()

    result = runtime_paths.resolve_memory_dir(tmp_path)

    assert result.path == tmp_path / ".ai" / "memory"
    assert result.kind == "canonical"
    assert result.legacy is False


def test_memory_path_prefers_existing_canonical_over_legacy(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai" / "memory").mkdir(parents=True)
    (tmp_path / ".ai-memory").mkdir()

    result = runtime_paths.resolve_memory_dir(tmp_path)

    assert result.path == tmp_path / ".ai" / "memory"
    assert result.kind == "canonical"
    assert result.legacy is False


def test_memory_path_falls_back_to_existing_legacy(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai-memory").mkdir()

    result = runtime_paths.resolve_memory_dir(tmp_path)

    assert result.path == tmp_path / ".ai-memory"
    assert result.kind == "legacy"
    assert result.legacy is True


def test_roadmap_path_defaults_to_ai_roadmap_namespace(tmp_path):
    runtime_paths = _load_runtime_paths()

    result = runtime_paths.resolve_roadmap_dir(tmp_path)

    assert result.path == tmp_path / ".ai" / "roadmap"
    assert result.kind == "canonical"
    assert result.legacy is False


def test_roadmap_path_falls_back_to_existing_legacy(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".roadmap").mkdir()

    result = runtime_paths.resolve_roadmap_dir(tmp_path)

    assert result.path == tmp_path / ".roadmap"
    assert result.kind == "legacy"
    assert result.legacy is True


def test_find_project_root_detects_canonical_ai_dir(tmp_path, monkeypatch):
    runtime_paths = _load_runtime_paths()
    project = tmp_path / "project"
    nested = project / "src" / "pkg"
    (project / ".ai" / "memory").mkdir(parents=True)
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    assert runtime_paths.find_project_root() == project
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sdlc_runtime_paths.py -q`

Expected: FAIL because `skills/_lib/sdlc_runtime_paths.py` does not exist.

- [ ] **Step 3: Implement resolver**

Create `skills/_lib/sdlc_runtime_paths.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


AI_DIR = ".ai"
MEMORY_SUBDIR = "memory"
ROADMAP_SUBDIR = "roadmap"
LEGACY_MEMORY_DIR = ".ai-memory"
LEGACY_ROADMAP_DIR = ".roadmap"


@dataclass(frozen=True)
class RuntimePath:
    path: Path
    kind: str
    legacy: bool


def canonical_memory_dir(root: Path) -> Path:
    return root / AI_DIR / MEMORY_SUBDIR


def canonical_roadmap_dir(root: Path) -> Path:
    return root / AI_DIR / ROADMAP_SUBDIR


def resolve_memory_dir(root: Path) -> RuntimePath:
    canonical = canonical_memory_dir(root)
    if canonical.exists():
        return RuntimePath(canonical, "canonical", False)
    legacy = root / LEGACY_MEMORY_DIR
    if legacy.exists():
        return RuntimePath(legacy, "legacy", True)
    return RuntimePath(canonical, "canonical", False)


def resolve_roadmap_dir(root: Path) -> RuntimePath:
    canonical = canonical_roadmap_dir(root)
    if canonical.exists():
        return RuntimePath(canonical, "canonical", False)
    legacy = root / LEGACY_ROADMAP_DIR
    if legacy.exists():
        return RuntimePath(legacy, "legacy", True)
    return RuntimePath(canonical, "canonical", False)


def find_project_root(start: Path | None = None) -> Path:
    cwd = (start or Path.cwd()).resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / AI_DIR / MEMORY_SUBDIR).is_dir():
            return parent
        if (parent / AI_DIR / ROADMAP_SUBDIR).is_dir():
            return parent
        if (parent / LEGACY_MEMORY_DIR).is_dir():
            return parent
        if (parent / LEGACY_ROADMAP_DIR).is_dir():
            return parent
        if (parent / "openspec").is_dir():
            return parent
        if (parent / ".git").is_dir():
            return parent
    return cwd
```

- [ ] **Step 4: Run resolver tests**

Run: `pytest tests/test_sdlc_runtime_paths.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/sdlc_runtime_paths.py tests/test_sdlc_runtime_paths.py
git commit -m "feat: add shared SDLC runtime path resolver"
```

---

### Task 2: Migrate Memory Init To `.ai/memory`

**Files:**
- Modify: `skills/sdlc-repository-memory-init/scripts/init_memory.py`
- Modify: `tests/test_repository_memory_init.py`

- [ ] **Step 1: Write failing init tests for canonical path**

In `tests/test_repository_memory_init.py`, change `_memory_dir()` to:

```python
    def _memory_dir(self) -> Path:
        return self.tmp_dir / ".ai" / "memory"
```

In `TestEndToEndIntegration.test_init_creates_structure_idempotently`, change:

```python
            memory_dir = tmp_dir / ".ai-memory"
```

to:

```python
            memory_dir = tmp_dir / ".ai" / "memory"
```

In `TestEndToEndIntegration.test_later_commit_reconciles_pending_memory`, change:

```python
            modules_dir = tmp_dir / ".ai-memory" / "modules"
```

to:

```python
            modules_dir = tmp_dir / ".ai" / "memory" / "modules"
```

and change:

```python
            rq = json.loads((tmp_dir / ".ai-memory" / "review-queue.json").read_text(encoding="utf-8"))
```

to:

```python
            rq = json.loads((tmp_dir / ".ai" / "memory" / "review-queue.json").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repository_memory_init.py -q`

Expected: FAIL because `init_memory()` still writes `.ai-memory`.

- [ ] **Step 3: Update init script to use resolver**

In `skills/sdlc-repository-memory-init/scripts/init_memory.py`, add imports after line 8:

```python
LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import resolve_memory_dir  # noqa: E402
```

Change line 40 from:

```python
    memory_dir = root / ".ai-memory"
```

to:

```python
    memory_dir = resolve_memory_dir(root).path
```

Change line 55 exclude patterns from:

```python
            ".git", ".ai-memory", "node_modules", "__pycache__",
```

to:

```python
            ".git", ".ai", ".ai-memory", "node_modules", "__pycache__",
```

Change CLI description line 100 from:

```python
    parser = argparse.ArgumentParser(description="Initialize .ai-memory/ in a repository.")
```

to:

```python
    parser = argparse.ArgumentParser(description="Initialize .ai/memory/ in a repository.")
```

Change line 115 from:

```python
        print(f"Repository Memory initialized at {root}/.ai-memory/")
```

to:

```python
        print(f"Repository Memory initialized at {memory_dir}/")
```

Add `memory_dir = resolve_memory_dir(root).path` after `result = init_memory(root)` in `main()` so the print statement has the resolved path:

```python
    result = init_memory(root)
    memory_dir = resolve_memory_dir(root).path
```

- [ ] **Step 4: Run init tests**

Run: `pytest tests/test_repository_memory_init.py -q`

Expected: PASS for init tests that only depend on initialization; reconciliation-related failures are acceptable until Task 4 updates sync scripts.

- [ ] **Step 5: Commit**

```bash
git add skills/sdlc-repository-memory-init/scripts/init_memory.py tests/test_repository_memory_init.py
git commit -m "feat: initialize repository memory under .ai"
```

---

### Task 3: Migrate Memory Load And Validation

**Files:**
- Modify: `skills/sdlc-repository-memory-load/scripts/select_memory.py`
- Modify: `skills/sdlc-repository-memory-load/scripts/validate_memory.py`
- Modify: `tests/test_repository_memory_load.py`

- [ ] **Step 1: Update tests to canonical path and add legacy fallback**

In `tests/test_repository_memory_load.py`, change both `_memory_dir()` helpers from:

```python
        return TEST_ROOT / ".ai-memory"
```

to:

```python
        return TEST_ROOT / ".ai" / "memory"
```

Add this test to `TestSelectMemoryMissingIndex` after `test_empty_index_returns_no_entries`:

```python
    def test_legacy_ai_memory_is_read_as_fallback(self) -> None:
        legacy_dir = TEST_ROOT / ".ai-memory"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": "1.0", "memory_version": 1, "git": {"available": False}}
        (legacy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        index = {"schema_version": "1.0", "entries": [
            {"title": "Legacy Auth", "summary": "Legacy memory", "path": "modules/auth.md", "type": "module", "sync_status": "synced", "tags": ["auth"]},
        ]}
        (legacy_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

        result = select_memory(TEST_ROOT, query="auth")

        assert result["entries"][0]["title"] == "Legacy Auth"
```

- [ ] **Step 2: Run tests to verify failures**

Run: `pytest tests/test_repository_memory_load.py -q`

Expected: FAIL because load scripts still read `.ai-memory` directly and do not import the resolver.

- [ ] **Step 3: Update `select_memory.py`**

Add after imports:

```python
LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import resolve_memory_dir  # noqa: E402
```

Change lines 79-80 from:

```python
    index_path = root / ".ai-memory" / "index.json"
    manifest_path = root / ".ai-memory" / "manifest.json"
```

to:

```python
    memory_dir = resolve_memory_dir(root).path
    index_path = memory_dir / "index.json"
    manifest_path = memory_dir / "manifest.json"
```

Change CLI description line 127 from:

```python
    parser = argparse.ArgumentParser(description="Select relevant memory entries from .ai-memory/index.json")
```

to:

```python
    parser = argparse.ArgumentParser(description="Select relevant memory entries from .ai/memory/index.json")
```

- [ ] **Step 4: Update load `validate_memory.py`**

Add the same `LIB_DIR` import block after imports.

Change the hard-coded memory directory from:

```python
    memory_dir = root / ".ai-memory"
```

to:

```python
    memory_dir = resolve_memory_dir(root).path
```

Change CLI description from `.ai-memory/` to `.ai/memory/`.

- [ ] **Step 5: Run memory load tests**

Run: `pytest tests/test_repository_memory_load.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/sdlc-repository-memory-load/scripts/select_memory.py skills/sdlc-repository-memory-load/scripts/validate_memory.py tests/test_repository_memory_load.py
git commit -m "feat: load repository memory from .ai namespace"
```

---

### Task 4: Migrate Memory Sync Scripts

**Files:**
- Modify: `skills/sdlc-repository-memory-sync/scripts/rebuild_index.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/reconcile_pending.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/validate_memory.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/update_manifest.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/discover_modules.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/child_modules.py`
- Modify: `skills/sdlc-repository-memory-sync/scripts/detect_state.py`
- Modify: `tests/test_repository_memory_sync.py`
- Modify: `tests/test_module_discovery.py`

- [ ] **Step 1: Update sync tests to canonical path**

In `tests/test_repository_memory_sync.py`, replace fixture path construction:

```python
tmp_path / ".ai-memory"
root / ".ai-memory"
```

with:

```python
tmp_path / ".ai" / "memory"
root / ".ai" / "memory"
```

In `tests/test_module_discovery.py`, replace fixture path construction:

```python
tmp_path / ".ai-memory"
```

with:

```python
tmp_path / ".ai" / "memory"
```

Keep one new fallback test in `tests/test_repository_memory_sync.py`:

```python
def test_rebuild_index_reads_legacy_ai_memory_when_canonical_missing(tmp_path):
    memory_dir = tmp_path / ".ai-memory"
    (memory_dir / "modules").mkdir(parents=True)
    (memory_dir / "modules" / "legacy.md").write_text(
        "---\n"
        "id: legacy\n"
        "type: module\n"
        "title: Legacy\n"
        "summary: Legacy memory\n"
        "sync_status: synced\n"
        "updated_at: 2026-01-01T00:00:00Z\n"
        "confidence: high\n"
        "tags: []\n"
        "---\n\n"
        "Legacy body.\n",
        encoding="utf-8",
    )

    result = rebuild_index(tmp_path, write=False)

    assert result["status"] == "ok"
    assert result["entries"][0]["id"] == "legacy"
```

- [ ] **Step 2: Run tests to verify failures**

Run: `pytest tests/test_repository_memory_sync.py tests/test_module_discovery.py -q`

Expected: FAIL because sync scripts still read `.ai-memory` directly.

- [ ] **Step 3: Import resolver into each sync script**

In every sync script listed in this task, add after imports:

```python
LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import resolve_memory_dir  # noqa: E402
```

For scripts that do not currently import `sys`, add `import sys`.

- [ ] **Step 4: Replace hard-coded memory root reads/writes**

Use this exact replacement pattern:

```python
memory_dir = root / ".ai-memory"
```

becomes:

```python
memory_dir = resolve_memory_dir(root).path
```

Use this exact replacement pattern:

```python
root / ".ai-memory" / "discovery-prefs.json"
```

becomes:

```python
resolve_memory_dir(root).path / "discovery-prefs.json"
```

Use this exact replacement pattern:

```python
root / ".ai-memory" / "review-queue.json"
```

becomes:

```python
resolve_memory_dir(root).path / "review-queue.json"
```

Use this exact replacement pattern in `detect_state.py`:

```python
manifest_path = root / ".ai-memory" / "manifest.json"
```

becomes:

```python
manifest_path = resolve_memory_dir(root).path / "manifest.json"
```

- [ ] **Step 5: Update module discovery excludes**

In `skills/sdlc-repository-memory-sync/scripts/discover_modules.py`, update the excluded names list from:

```python
    ".ai-memory",
```

to include both:

```python
    ".ai",
    ".ai-memory",
```

Do not remove `.ai-memory` from excludes; legacy memory should not be indexed as an application module.

- [ ] **Step 6: Update script descriptions and errors**

Change user-facing descriptions/errors from `.ai-memory/` to `.ai/memory/`, and mention legacy fallback only where the message explains detection. Example for `rebuild_index.py`:

```python
"error": ".ai/memory/ directory not found",
```

and:

```python
parser = argparse.ArgumentParser(description="Rebuild .ai/memory/index.json from memory files")
```

- [ ] **Step 7: Run sync and discovery tests**

Run: `pytest tests/test_repository_memory_sync.py tests/test_module_discovery.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add skills/sdlc-repository-memory-sync/scripts tests/test_repository_memory_sync.py tests/test_module_discovery.py
git commit -m "feat: sync repository memory from .ai namespace"
```

---

### Task 5: Migrate Roadmap Scripts To `.ai/roadmap`

**Files:**
- Modify: `skills/sdlc-roadmap/scripts/validate.py`
- Modify: `skills/sdlc-roadmap/scripts/rebuild_index.py`
- Modify: `skills/sdlc-roadmap/scripts/list.py`
- Modify: `tests/test_sdlc_roadmap.py`

- [ ] **Step 1: Update roadmap tests to canonical path**

In `tests/test_sdlc_roadmap.py`, change every test setup from:

```python
self.roadmap_dir = Path(self.tmpdir) / ".roadmap"
```

to:

```python
self.roadmap_dir = Path(self.tmpdir) / ".ai" / "roadmap"
```

Add this fallback test to `TestListScript`:

```python
    def test_legacy_roadmap_is_read_as_fallback(self) -> None:
        shutil.rmtree(self.roadmap_dir.parent)
        legacy_roadmap = Path(self.tmpdir) / ".roadmap"
        (legacy_roadmap / "items").mkdir(parents=True)
        _make_item(legacy_roadmap, "RM-001", status="ready", order=10)

        result = _run_script("list.py", self.tmpdir)

        self.assertEqual(result.returncode, 0)
        self.assertIn("RM-001", result.stdout)
```

- [ ] **Step 2: Run roadmap tests to verify failures**

Run: `pytest tests/test_sdlc_roadmap.py -q`

Expected: FAIL because scripts still look for `.roadmap`.

- [ ] **Step 3: Import resolver into roadmap scripts**

In `validate.py`, `rebuild_index.py`, and `list.py`, add after imports:

```python
LIB_DIR = Path(__file__).resolve().parents[2] / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from sdlc_runtime_paths import find_project_root, resolve_roadmap_dir  # noqa: E402
```

For scripts missing `import sys`, add `import sys`.

- [ ] **Step 4: Replace local root finders**

In each roadmap script, remove the local `find_root()` function or stop using it.

Change:

```python
root = find_root()
roadmap_dir = root / ".roadmap"
```

to:

```python
root = find_project_root()
roadmap_dir = resolve_roadmap_dir(root).path
```

- [ ] **Step 5: Update user-facing messages**

Change errors from:

```python
print("ERROR: .roadmap/ directory not found")
print("ERROR: .roadmap/items/ directory not found")
print("WARNING: No item files found in .roadmap/items/")
```

to:

```python
print("ERROR: .ai/roadmap/ directory not found")
print("ERROR: .ai/roadmap/items/ directory not found")
print("WARNING: No item files found in .ai/roadmap/items/")
```

Keep fallback behavior internal; user-facing docs should steer new projects to `.ai/roadmap`.

- [ ] **Step 6: Run roadmap tests**

Run: `pytest tests/test_sdlc_roadmap.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/sdlc-roadmap/scripts tests/test_sdlc_roadmap.py
git commit -m "feat: use .ai namespace for roadmap runtime"
```

---

### Task 6: Update Skill Docs And Templates

**Files:**
- Modify: `skills/sdlc-repository-memory-init/SKILL.md`
- Modify: `skills/sdlc-repository-memory-load/SKILL.md`
- Modify: `skills/sdlc-repository-memory-load/templates/context-pack.md`
- Modify: `skills/sdlc-repository-memory-sync/SKILL.md`
- Modify: `skills/sdlc-repository-memory-reset/SKILL.md`
- Modify: `skills/sdlc-openspec-memory-sync/SKILL.md`
- Modify: `skills/sdlc-project-bootstrap/SKILL.md`
- Modify: `skills/sdlc-repository-memory-init/templates/AGENTS-memory-block.md`
- Modify: `skills/sdlc-roadmap/SKILL.md`

- [ ] **Step 1: Update canonical path wording**

Replace new-runtime wording consistently:

```text
.ai-memory/
```

with:

```text
.ai/memory/
```

Replace roadmap runtime wording consistently:

```text
.roadmap/
```

with:

```text
.ai/roadmap/
```

Do not mechanically replace legacy sections that explicitly explain fallback.

- [ ] **Step 2: Add compatibility note to memory skills**

Add this paragraph to `sdlc-repository-memory-init`, `sdlc-repository-memory-load`, and `sdlc-repository-memory-sync` after their file model or workflow introduction:

```markdown
## Runtime Path Compatibility

The canonical runtime path is `.ai/memory/`. For existing projects, scripts may read legacy `.ai-memory/` when `.ai/memory/` is absent. New initialization writes only to `.ai/memory/`; do not create new `.ai-memory/` directories.
```

- [ ] **Step 3: Add compatibility note to roadmap skill**

Add this paragraph to `skills/sdlc-roadmap/SKILL.md` after `## File Model`:

```markdown
The canonical runtime path is `.ai/roadmap/`. For existing projects, scripts may read legacy `.roadmap/` when `.ai/roadmap/` is absent. New initialization writes only to `.ai/roadmap/`; do not create new `.roadmap/` directories.
```

- [ ] **Step 4: Update AGENTS memory block**

In `skills/sdlc-repository-memory-init/templates/AGENTS-memory-block.md`, use this exact content:

```markdown
## Repository Memory

If `.ai/memory/index.json` exists and the task involves planning, editing, reviewing, or continuing work in this repository, load relevant repository memory first using `sdlc-repository-memory-load`.

For existing repositories, `.ai-memory/index.json` is a supported legacy fallback when `.ai/memory/index.json` does not exist.

Do not load `.ai/memory/sync-history/`, `.ai/memory/sessions/`, `.ai/memory/snapshots/`, `.ai/memory/tmp/`, `.ai/memory/cache/`, or `.ai/memory/review-queue.json` by default.
```

- [ ] **Step 5: Run documentation keyword check**

Run: `rg "\.ai-memory|\.roadmap" skills/sdlc-* skills/sdlc-roadmap`

Expected: remaining matches only appear in compatibility/fallback notes or legacy reset/migration warnings.

- [ ] **Step 6: Run doc-related tests**

Run: `pytest tests/test_project_bootstrap_skills.py tests/test_sdlc_roadmap.py tests/test_repository_memory_init.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/sdlc-repository-memory-init skills/sdlc-repository-memory-load skills/sdlc-repository-memory-sync skills/sdlc-repository-memory-reset skills/sdlc-openspec-memory-sync skills/sdlc-project-bootstrap skills/sdlc-roadmap tests/test_project_bootstrap_skills.py
git commit -m "docs: document .ai runtime layout for SDLC skills"
```

---

### Task 7: Refresh CLI Skill Copies

**Files:**
- Modify: `.opencode/skills/sdlc-repository-memory-init/**`
- Modify: `.opencode/skills/sdlc-repository-memory-load/**`
- Modify: `.opencode/skills/sdlc-repository-memory-sync/**`
- Modify: `.opencode/skills/sdlc-repository-memory-reset/**`
- Modify: `.opencode/skills/sdlc-openspec-memory-sync/**`
- Modify: `.opencode/skills/sdlc-project-bootstrap/**`
- Modify: `.opencode/skills/sdlc-roadmap/**`
- Modify: `.claude/skills/sdlc-repository-memory-init/**`
- Modify: `.claude/skills/sdlc-repository-memory-load/**`
- Modify: `.claude/skills/sdlc-repository-memory-sync/**`
- Modify: `.claude/skills/sdlc-repository-memory-reset/**`
- Modify: `.claude/skills/sdlc-openspec-memory-sync/**`
- Modify: `.claude/skills/sdlc-project-bootstrap/**`
- Modify: `.cursor/skills/sdlc-repository-memory-init/**`
- Modify: `.cursor/skills/sdlc-repository-memory-load/**`
- Modify: `.cursor/skills/sdlc-repository-memory-sync/**`
- Modify: `.cursor/skills/sdlc-repository-memory-reset/**`
- Modify: `.cursor/skills/sdlc-openspec-memory-sync/**`
- Modify: `.cursor/skills/sdlc-project-bootstrap/**`

- [ ] **Step 1: Copy canonical skill directories to CLI copies**

Run these commands from the repository root:

```bash
cp -R skills/sdlc-repository-memory-init/. .opencode/skills/sdlc-repository-memory-init/
cp -R skills/sdlc-repository-memory-load/. .opencode/skills/sdlc-repository-memory-load/
cp -R skills/sdlc-repository-memory-sync/. .opencode/skills/sdlc-repository-memory-sync/
cp -R skills/sdlc-repository-memory-reset/. .opencode/skills/sdlc-repository-memory-reset/
cp -R skills/sdlc-openspec-memory-sync/. .opencode/skills/sdlc-openspec-memory-sync/
cp -R skills/sdlc-project-bootstrap/. .opencode/skills/sdlc-project-bootstrap/
cp -R skills/sdlc-roadmap/. .opencode/skills/sdlc-roadmap/
cp -R skills/sdlc-repository-memory-init/. .claude/skills/sdlc-repository-memory-init/
cp -R skills/sdlc-repository-memory-load/. .claude/skills/sdlc-repository-memory-load/
cp -R skills/sdlc-repository-memory-sync/. .claude/skills/sdlc-repository-memory-sync/
cp -R skills/sdlc-repository-memory-reset/. .claude/skills/sdlc-repository-memory-reset/
cp -R skills/sdlc-openspec-memory-sync/. .claude/skills/sdlc-openspec-memory-sync/
cp -R skills/sdlc-project-bootstrap/. .claude/skills/sdlc-project-bootstrap/
cp -R skills/sdlc-repository-memory-init/. .cursor/skills/sdlc-repository-memory-init/
cp -R skills/sdlc-repository-memory-load/. .cursor/skills/sdlc-repository-memory-load/
cp -R skills/sdlc-repository-memory-sync/. .cursor/skills/sdlc-repository-memory-sync/
cp -R skills/sdlc-repository-memory-reset/. .cursor/skills/sdlc-repository-memory-reset/
cp -R skills/sdlc-openspec-memory-sync/. .cursor/skills/sdlc-openspec-memory-sync/
cp -R skills/sdlc-project-bootstrap/. .cursor/skills/sdlc-project-bootstrap/
```

If a destination directory does not exist, create it with `mkdir -p <destination>` before copying.

- [ ] **Step 2: Copy shared helper to CLI skill trees**

Run:

```bash
mkdir -p .opencode/skills/_lib .claude/skills/_lib .cursor/skills/_lib
cp skills/_lib/sdlc_runtime_paths.py .opencode/skills/_lib/sdlc_runtime_paths.py
cp skills/_lib/sdlc_runtime_paths.py .claude/skills/_lib/sdlc_runtime_paths.py
cp skills/_lib/sdlc_runtime_paths.py .cursor/skills/_lib/sdlc_runtime_paths.py
```

- [ ] **Step 3: Add distribution tests for helper presence**

In `tests/test_repository_memory_skill_copies.py`, add assertions equivalent to:

```python
def test_runtime_path_helper_copied_to_cli_skill_trees():
    for target in [".opencode", ".claude", ".cursor"]:
        helper = REPO_ROOT / target / "skills" / "_lib" / "sdlc_runtime_paths.py"
        assert helper.exists(), f"missing runtime helper in {target}"
        assert helper.read_text(encoding="utf-8") == (REPO_ROOT / "skills" / "_lib" / "sdlc_runtime_paths.py").read_text(encoding="utf-8")
```

Use the existing assertion style in that test file if it uses `unittest` instead of plain pytest.

- [ ] **Step 4: Run distribution tests**

Run: `pytest tests/test_repository_memory_skill_copies.py tests/test_sdlc_roadmap.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .opencode/skills .claude/skills .cursor/skills tests/test_repository_memory_skill_copies.py
git commit -m "chore: refresh CLI skill copies for .ai runtime layout"
```

---

### Task 8: Add Explicit Migration Guidance

**Files:**
- Create or modify: `docs/sdlc-runtime-layout.md`
- Modify: `skills/sdlc-repository-memory-reset/SKILL.md`
- Modify: `skills/sdlc-roadmap/SKILL.md`

- [ ] **Step 1: Write migration guide**

Create `docs/sdlc-runtime-layout.md` with:

```markdown
# SDLC Runtime Layout

SDLC skills store runtime state under `.ai/`.

## Canonical Paths

| Runtime area | Canonical path | Legacy fallback |
|---|---|---|
| Repository memory | `.ai/memory/` | `.ai-memory/` |
| Roadmap | `.ai/roadmap/` | `.roadmap/` |

New initialization writes only to canonical paths. Existing projects remain readable through legacy fallback when the canonical path does not exist.

## Manual Migration

Run these commands only after confirming the project does not already have canonical runtime state:

```bash
mkdir -p .ai
mv .ai-memory .ai/memory
mv .roadmap .ai/roadmap
```

If both canonical and legacy directories exist, do not merge automatically. Inspect both directories and decide which one is authoritative.

## Conflict Rule

When both canonical and legacy directories exist, SDLC scripts prefer canonical paths:

- `.ai/memory/` wins over `.ai-memory/`
- `.ai/roadmap/` wins over `.roadmap/`

Legacy directories should be removed only after the user confirms their contents have been migrated or are obsolete.
```

- [ ] **Step 2: Link migration guide from skills**

In `skills/sdlc-repository-memory-reset/SKILL.md`, add:

```markdown
For manual path migration from `.ai-memory/` to `.ai/memory/`, follow `docs/sdlc-runtime-layout.md`. Do not merge canonical and legacy directories automatically.
```

In `skills/sdlc-roadmap/SKILL.md`, add:

```markdown
For manual path migration from `.roadmap/` to `.ai/roadmap/`, follow `docs/sdlc-runtime-layout.md`. Do not merge canonical and legacy directories automatically.
```

- [ ] **Step 3: Run documentation grep**

Run: `rg "\.ai-memory|\.roadmap" docs skills/sdlc-* skills/sdlc-roadmap`

Expected: any remaining legacy path matches are in compatibility, fallback, migration, or reset safety sections.

- [ ] **Step 4: Commit**

```bash
git add docs/sdlc-runtime-layout.md skills/sdlc-repository-memory-reset/SKILL.md skills/sdlc-roadmap/SKILL.md
git commit -m "docs: add SDLC runtime layout migration guide"
```

---

### Task 9: Full Verification

**Files:**
- No planned source edits unless verification exposes failures.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
pytest \
  tests/test_sdlc_runtime_paths.py \
  tests/test_repository_memory_init.py \
  tests/test_repository_memory_load.py \
  tests/test_repository_memory_sync.py \
  tests/test_module_discovery.py \
  tests/test_project_bootstrap_skills.py \
  tests/test_sdlc_roadmap.py \
  tests/test_repository_memory_skill_copies.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run: `pytest -q`

Expected: PASS.

- [ ] **Step 3: Check remaining legacy references**

Run:

```bash
rg "\.ai-memory|\.roadmap" skills tests docs AGENTS.md
```

Expected: remaining matches are limited to legacy compatibility/fallback docs, migration guide, and tests that explicitly validate legacy fallback.

- [ ] **Step 4: Check working tree**

Run: `git status --short`

Expected: only intended files changed, or clean if all task commits were made.

- [ ] **Step 5: Final commit if needed**

If verification fixes required changes after Task 8, commit them:

```bash
git add <fixed-files>
git commit -m "test: verify .ai runtime layout migration"
```

---

## Self-Review

Spec coverage:
- `.ai/memory` as new repository memory runtime path: covered by Tasks 2, 3, 4, 6, 8.
- `.ai/roadmap` as new roadmap runtime path: covered by Tasks 5, 6, 8.
- Legacy fallback for `.ai-memory` and `.roadmap`: covered by Tasks 1, 3, 4, 5, 8.
- Avoid moving canonical skill source from `skills/`: documented in scope and not included in any task.
- Cross-CLI copies stay synchronized: covered by Task 7.
- Verification: covered by Task 9.

Placeholder scan:
- The plan does not contain unfinished-marker wording or unspecified implementation steps.
- Code steps include concrete snippets and exact file paths.

Type consistency:
- Shared resolver exposes `RuntimePath`, `resolve_memory_dir`, `resolve_roadmap_dir`, and `find_project_root`.
- Later tasks consistently use `.path` from resolver results.
- Tests and script updates consistently refer to `.ai/memory` and `.ai/roadmap` as canonical paths.
