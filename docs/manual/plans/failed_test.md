# Failed Tests Report

Generated after recovery of `sdlc-repository-memory-*` skills from commit `d481513`.

**Test file**: `tests/test_repository_memory_skill_copies.py`
**157 passed, 2 failed**

---

## Failure 1: `test_skill_install_json_has_required_fields`

**Assertion**:
```python
Missing field 'source_path' in .opencode/skills/sdlc-evalops/.skill-install.json
```

**Root cause**: Many `.skill-install.json` files (added in commit `d481513`) are missing 3 fields:
`source_path`, `payload_hash`, `files`.

The test requires these fields from `INSTALL_METADATA_REQUIRED_FIELDS`:
```python
INSTALL_METADATA_REQUIRED_FIELDS = [
    "skill",
    "source_repo",
    "source_path",
    "target",
    "installed_at",
    "status",
    "payload_hash",
    "files",
]
```

**Affected skills** (39 `.skill-install.json` files across 3 client dirs, 13 unique skills):
- `integration-notion-sync`
- `media-ocr-router`
- `meta-skill-lifecycle-governance`
- `ops-mackup-backup`
- `qa-ai-architecture`
- `refresh-tech-article`
- `research-general`
- `sdlc-evalops`
- `study-zybook-notes`
- `transform-algo-render`
- `transform-markdown-svg`
- `transform-math-formula`
- `transform-xmind`

Each affected file has only 7 fields and is missing `source_path`, `payload_hash`, `files`.

**Good reference** — `.opencode/skills/sdlc-repository-memory-init/.skill-install.json`:
```json
{
  "skill": "sdlc-repository-memory-init",
  "source_repo": "/Users/yuping/Documents/workspace/oh_my_skills",
  "source_ref": "HEAD",
  "source_path": "skills/sdlc-repository-memory-init",
  "target": ".opencode/skills/sdlc-repository-memory-init",
  "installed_at": "2026-05-30T14:26:15.086576Z",
  "status": "stable",
  "backport_policy": "review-required",
  "payload_hash": "27cdbe1425d33f89d427d8079d5c2366cb0ec2fc152f1c9c1003c294457f9876",
  "files": [
    "SKILL.md",
    "schemas/index.schema.json",
    ...
  ]
}
```

**Fix approach**: Add `source_path`, `payload_hash`, `files` to every affected `.skill-install.json`. Simplest approach is to re-install these skills using `meta-skill-lifecycle-governance/scripts/install_skill.py` to regenerate correct metadata.

---

## Failure 2: `test_canonical_scripts_exist_in_all_copies`

**Assertion**:
```python
Script validate.py content mismatch in skills/sdlc-roadmap
```

**Root cause**: The canonical `skills/sdlc-roadmap/scripts/validate.py` was updated in a recent commit but the client copies (`.opencode/.claude/.cursor`) were not synced.

The canonical file has 7 extra lines that the copies are missing (2 additions at top, 6 additions later):

**Missing in all 3 copies** (lines 29-30 in canonical, after line 28 in copies):
```python
    roadmap_areas_dir,
    roadmap_manifest_path,
```

**Missing in all 3 copies** (lines 323-329 in canonical, after line 320 in copies):
```python
    elif (roadmap_dir / "areas").is_dir() and any(
        (roadmap_dir / "areas").iterdir()
    ):
        errors.append(
            "root manifest.json missing but areas/ directory exists with content. "
            "Create " + str(roadmap_manifest_path(root)) + " or remove orphan areas/"
        )
```

This content appears to add area-based layout support to the roadmap validate script.

**Fix approach**: Copy `skills/sdlc-roadmap/scripts/validate.py` to all 3 client dirs:
- `.opencode/skills/sdlc-roadmap/scripts/validate.py`
- `.claude/skills/sdlc-roadmap/scripts/validate.py`
- `.cursor/skills/sdlc-roadmap/scripts/validate.py`
