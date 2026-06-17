---
id: RM-SDLC-003
title: Validation & Sync
status: idea
stage: v3
priority: p2
order: 30
depends_on:
  - RM-SDLC-002
openspec_change: null
created_at: 2026-06-09
started_at: null
completed_at: null
---

# Goal

提升稳定性，减少手工检查负担。

# Scope

## In

- `index.json` 校验规则完善。
- `roadmap.md` 自动重建（从 items 生成）。
- item 状态一致性检查（依赖项完成状态 vs 当前状态）。
- OpenSpec change 状态同步（active → done 自动检测）。
- patch 关联完整性检查。
- 增强 `scripts/validate.py` 覆盖以上所有检查。
- 增强 `scripts/rebuild_index.py` 支持增量更新。

## Out

- CI 集成。
- 自动修复（只报告差异，不自动修改）。
