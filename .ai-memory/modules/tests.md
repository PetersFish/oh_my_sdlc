---
id: tests
type: module
title: Tests
summary: Test suite for repository skills: memory init/load/sync, module discovery, OCR routing, skill copies, lifecycle utilities, and research. Python-based with image fixtures. Run with pytest from the repository root.
parent_id: null
sync_status: synced
evidence_mode: discovery
linked_commits: []
linked_specs: []
linked_sessions: ["20260529-000001"]
updated_at: 2026-05-29T00:00:00Z
confidence: high
tags: [tests, pytest, python, verification]
owned_paths: ["tests/"]
path_hints: ["tests/"]
keywords: [test, pytest, verify, assertion, test file]
test_paths: ["tests/"]
spec_paths: []
---

# Tests

## Current Understanding

The `tests/` directory contains Python unit tests for the repository's skill system. Tests cover memory init/load/sync, module discovery, OCR routing, skill copy consistency, lifecycle utilities, and the research skill. Test data includes image fixtures under `tests/images/` and a Markdown file with embedded images for OCR testing.

## Evidence

Initial discovery scan: 25 files (8 .py, 14 .pyc, 2 .png, 1 .md). 8 test modules total.

## Operational Guidance

- Run tests with `pytest tests/` from repository root.
- Test files follow `test_<module>.py` naming convention.
- Image fixtures in `tests/images/` are used by OCR router tests.
- `tests/md_with_images.md` is test data for Markdown image handling.

## Child Modules

None — flat test file structure.

## Key Files

- `tests/test_repository_memory_init.py` — memory initialization tests
- `tests/test_repository_memory_load.py` — memory loading tests
- `tests/test_repository_memory_sync.py` — memory sync tests
- `tests/test_module_discovery.py` — module discovery tests
- `tests/test_ocr_router_skill.py` — OCR router tests
- `tests/test_lifecycle_utils.py` — lifecycle utility tests
- `tests/test_repository_memory_skill_copies.py` — skill copy consistency
- `tests/test_research_skill.py` — research skill tests

## Entry Points

Run all tests: `pytest tests/`

## Tests

N/A — this is the test module itself.

## Related Specs

Individual test modules correspond to OpenSpec specs under `openspec/specs/`.

## Update Notes

First sync after repository memory initialization.
