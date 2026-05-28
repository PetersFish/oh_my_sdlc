---
id: modules/tests
type: module
title: Test Suite
summary: Python test suite covering skill lifecycle, module discovery, OCR router, and repository memory (init/load/sync). Uses pytest-style tests with supporting test images and markdown fixtures.
sync_status: synced
evidence_mode: discovery
linked_commits: ["72272fb8c448292dd985d7ee35f160de9e5c94bc"]
linked_specs: []
linked_sessions: ["20260529-01"]
updated_at: 2026-05-29T00:00:00Z
confidence: high
tags: [tests, pytest, skills, memory]
---

# Test Suite

## Current Understanding

The test suite covers the core skill infrastructure:
- **test_lifecycle_utils.py**: Skill lifecycle governance utilities
- **test_module_discovery.py**: Module discovery functionality
- **test_ocr_router_skill.py**: OCR/media routing skill
- **test_repository_memory_init.py**: Memory initialization
- **test_repository_memory_load.py**: Memory loading
- **test_repository_memory_skill_copies.py**: Skill copy/installation verification
- **test_repository_memory_sync.py**: Memory sync workflow

Supporting assets include test images (PNGs) and a Markdown-with-images fixture.

## Evidence

- 8 .py test files detected in discovery scan
- 2 .png test images in tests/images/
- 1 .md fixture file

## Operational Guidance

- Run tests with `pytest tests/` before making changes to skill or memory infrastructure
- Add test fixtures to tests/images/ for media-related tests
- Follow existing pattern: one test file per skill/module

## Update Notes

Initial discovery during first repository memory sync (2026-05-29).
