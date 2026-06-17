---
id: RM-SDLC-002
title: Roadmap Revision Workflow
status: active
stage: v2
priority: p1
order: 20
depends_on:
  - RM-SDLC-001
openspec_change: sdlc-roadmap-revision-workflow
created_at: 2026-06-09
started_at: 2026-06-17
completed_at: null
patches: []
---

# Goal

解决 roadmap 生成后的评审、修正、顺序调整、插入、取消和整体重规划问题，并为这些变更保留可追溯日志。

# Scope

## In

- `roadmap review`：评审 `idea` 状态的 roadmap item；评审不通过则不创建 OpenSpec change，评审通过后创建完整 OpenSpec artifacts 并变为 `ready`。
- `roadmap revise`：修正 roadmap item 内容，修改前保存 snapshot，修改后追加 changelog。
- `roadmap insert`：新增 roadmap item；不指定位置时默认追加，指定 `--before/--after` 时插入指定位置。
- `roadmap reorder`：统一调整优先级和实现顺序，支持更新 `priority`、`order` 或二者同时更新。
- `roadmap cancel`：取消 roadmap item，保留 item 和取消前 snapshot。
- `roadmap replan`：归档未完成计划并重新生成 `idea` items，保留 `done`/`cancelled`，显式处理 `active` items。
- apply/implementation 开始后将匹配的 ready roadmap item 变为 `active`。
- `sdlc-orchestrator` 在 OpenSpec archive 成功后的 post-archive gate 中路由到 `sdlc-roadmap done`，由 roadmap 执行 `active -> done` 状态更新。
- scripts: `validate.py` 收敛到最小状态模型并覆盖 revision/changelog 结构。
- scripts: `sync.py` 对比 OpenSpec 状态与 roadmap 状态，作为生命周期不一致的诊断工具，不承担 archive 后状态转换触发职责。

## Out

- patch 概念、patch 记录文件、`patch capture/done/escalate`。
- `/patch.apply` 执行器或任何 roadmap 驱动的代码执行。
- `planned`、`deferred`、`superseded` 状态。
- Revision 的 revert/draft 状态（最小版本不复杂化）。

# Acceptance Criteria

- 新 roadmap item 默认进入 `idea` 状态。
- review 能引导用户评审 `idea` items；评审不通过时保持 `idea` 且不创建 OpenSpec change。
- review 通过后能创建完整 OpenSpec artifacts，回写 `openspec_change`，并在 artifacts complete 后变为 `ready`。
- review 完成后能检查剩余未评审 items，并询问继续 review 或开始 apply ready change。
- apply/implementation 开始后能将 `ready -> active`，并回写 `started_at`。
- revise 能在更新内容前保存 snapshot，并在 `revisions/changelog.md` 追加变更记录。
- insert 能默认 append，也能按 `--before/--after` 插入指定位置。
- reorder 能统一调整 `priority` 和 `order`，且不改变 item 状态。
- cancel 能保留 item、保存 snapshot、追加 changelog；active item 取消前必须处理关联 OpenSpec change。
- replan 能归档 `idea/ready` 旧计划、保留 `done/cancelled`、显式处理 `active`，并创建新的 `idea` items。
- `sdlc-orchestrator` 的 post-archive gate 能在 OpenSpec archive 成功后找到匹配的 `active` roadmap item，并路由到 `sdlc-roadmap done`。
- `sdlc-roadmap done` 能执行 `active -> done`，更新 `completed_at`、completion notes、index，并运行 validation。
- `validate.py` 覆盖最小状态模型和 revision/changelog 结构。
- `sync.py` 能对比 OpenSpec changes/ + archive/ 与 roadmap 状态差异。
