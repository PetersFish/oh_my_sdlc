---
id: RM-SDLC-004
title: Backlog / GitHub Issues Integration
status: planned
stage: v4
priority: p3
order: 40
depends_on:
  - RM-SDLC-003
openspec_change: null
created_at: 2026-06-09
started_at: null
completed_at: null
patches: []
---

# Goal

适配团队协作和可视化管理。

# Scope

## In

- Backlog.md task 映射。
- GitHub issue 映射。
- roadmap item → issue 双向同步。
- patch → issue comment。
- OpenSpec change → PR / issue link。

## Out

- Web UI（kanban board 等，建议依赖 Backlog.md 已有能力）。
- 多用户协作 lock 机制。
- 自动生成 release notes。
