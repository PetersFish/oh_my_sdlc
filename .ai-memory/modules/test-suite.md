---
id: test-suite
type: module
title: Test Suite
summary: Python test suite covering skill lifecycle utilities, OCR router, research, OpenSpec memory sync, and the repository memory system (init, load, sync, skill copies). Located in tests/. Load when adding new skills, modifying lifecycle scripts, or debugging memory system behavior.
sync_status: synced
evidence_mode: commit
linked_commits: ['62085d3', 'f409d1f', '2f90be4', 'e1bd6da']
linked_specs: ['repository-memory-system-v2']
linked_sessions: ['2026-05-27-001']
updated_at: 2026-05-27T13:43:32Z
confidence: high
tags: [tests, python, validation]
---

# Test Suite

## Current Understanding

The test suite (`tests/`) validates the core skill infrastructure:

| Test File | Covers |
|---|---|
| `test_lifecycle_utils.py` | Skill lifecycle governance utilities |
| `test_ocr_router_skill.py` | OCR router multimodal image routing |
| `test_research_skill.py` | Research skill behavior |
| `test_openspec_memory_sync_skill.py` | OpenSpec memory sync adapter |
| `test_repository_memory_init.py` | Repository memory init (32 symbols) |
| `test_repository_memory_load.py` | Repository memory load (46 symbols) |
| `test_repository_memory_sync.py` | Repository memory sync (58 symbols) |
| `test_repository_memory_skill_copies.py` | Skill copy consistency (20 symbols) |
| `testrepository_memory_init.py` | Duplicate/redundant init test (22 symbols) |

## Evidence

- Tests were introduced alongside their corresponding skills/modules
- Largest test files are for the memory system, reflecting its complexity
- `testrepository_memory_init.py` appears to be a duplicate — may need cleanup

## Operational Guidance

- Run tests before installing or distributing skills
- Memory system tests are the most complex; sync tests cover the full workflow
- Test file `testrepository_memory_init.py` (no underscore) may be a duplicate of `test_repository_memory_init.py`

## Update Notes

- 2026-05-27: First memory sync — documented test suite structure
