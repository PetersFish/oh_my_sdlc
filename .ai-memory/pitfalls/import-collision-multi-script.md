---
id: pitfall-import-collision-multi-script
type: pitfalls
title: Import name collision when multiple test files load validate_memory.py from different skills
summary: When test_repository_memory_load.py and test_repository_memory_sync.py both use sys.path.insert to load validate_memory from their respective script directories, Python caches the first import. Running the full test suite causes the wrong validate_memory module to be used by the second test file, resulting in 3 false failures.
sync_status: synced
evidence_mode: session_observation
linked_commits: []
linked_specs: ['repository-memory-system-v2']
linked_sessions: ['2026-05-27-002']
updated_at: 2026-05-27T14:00:00Z
confidence: high
tags: [tests, python, imports, collision, debugging]
---

# Import Name Collision in Multi-Script Test Suites

## Current Understanding

When two separate Python test files both need to import a module with the same name (e.g., `validate_memory.py` exists in both `skills/repository-memory-load/scripts/` and `skills/repository-memory-sync/scripts/`), using `sys.path.insert` causes the first loaded copy to be cached in `sys.modules`. The second test file's `from validate_memory import validate_memory` silently uses the cached version from the wrong directory.

## Evidence

- Tests passed individually (`pytest tests/test_repository_memory_sync.py::TestValidateMemory -v`) but failed when run with other test files
- 3 false failures: test_valid_manifest_passes, test_missing_manifest_field_reported, test_valid_frontmatter_passes
- Root cause: `test_repository_memory_load.py` inserted its scripts dir first, loading load's validate_memory.py. When `test_repository_memory_sync.py` later tried to import validate_memory, Python returned the cached load version

## Operational Guidance

**Solution: Use `importlib.util.spec_from_file_location`**

```python
import importlib.util

SYNC_SCRIPTS_DIR = REPO_ROOT / "skills" / "repository-memory-sync" / "scripts"

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_validate_mod = _load_module("validate_memory_sync", SYNC_SCRIPTS_DIR / "validate_memory.py")
validate_memory = _validate_mod.validate_memory
```

Key: give each module a unique internal name (e.g., `validate_memory_sync` vs `validate_memory_load`) to avoid `sys.modules` collision.

**When to apply**: Any time multiple test files need to import scripts with the same filename from different directories. This is common in skill repositories where skills share script names (e.g., validate_memory.py appears in both load and sync).

## Update Notes

Encountered and fixed on 2026-05-27 during repository-memory-system-v2 implementation testing.
