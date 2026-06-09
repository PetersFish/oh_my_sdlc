---
id: RM-002
title: Replan & Patch
status: planned
stage: v2
priority: p1
order: 20
depends_on:
  - RM-001
openspec_change: null
created_at: 2026-06-09
started_at: null
completed_at: null
patches: []
---

# Goal

解决中途路线调整和小优化追踪问题。

# Scope

## In

- `roadmap replan`：路线图重规划，生成 revision 文件。
- `roadmap defer`：item 延后。
- `roadmap cancel`：item 取消。
- `roadmap supersede`：item 替代。
- `patch capture`：记录轻量优化。
- `patch done`：标记 patch 完成。
- `patch escalate`：将 patch 升级为 OpenSpec change。
- scripts: `validate.py` 扩展覆盖 patch 和 revision 结构。
- scripts: `sync.py` 对比 OpenSpec 状态与 roadmap 状态。

## Out

- `/patch.apply` 执行器。Patch 仍不自动执行代码，执行走普通开发/TDD/debug。
- Revision 的 revert/draft 状态（最小版本不复杂化）。

# Acceptance Criteria

- replan 能正确保留 done item 历史，生成 revision 文件。
- cancel/supersede/defer 正确更新状态和原因字段。
- patch 关联 parent_roadmap_item 和 related_openspec_change。
- escalate 能创建 OpenSpec change 并回写 patch 状态。
- `validate.py` 覆盖 patch/revision 校验。
- `sync.py` 能对比 OpenSpec changes/ + archive/ 与 roadmap 状态差异。
