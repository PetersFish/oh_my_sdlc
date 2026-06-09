# Roadmap Skill 调研报告与详细设计方案

## 1. 背景

### 1.1 当前开发工作流

当前项目主要使用以下 AI-native 开发组合：

* `opencode`：作为本地 AI CLI / Agent 执行环境；
* `Superpowers`：用于 TDD、debug、review、implementation 等执行类能力；
* `OpenSpec`：用于正式变更的 spec-driven development 工作流；
* 项目级自定义 skills：用于约束本地开发规范、流程、记忆同步和任务编排。

当前 OpenSpec 的典型职责是管理一次明确的变更：

```text
openspec/changes/<change-id>/
  proposal.md
  design.md
  tasks.md
  specs/...
```

它适合处理：

* 新功能；
* 重要重构；
* 架构调整；
* 公共 API / 数据模型变化；
* 需要明确验收标准的正式变更。

但它并不天然承担“全局产品路线图”的职责。

---

### 1.2 核心痛点

在实际使用 LLM 协助开发时，LLM 经常会在 brainstorm 或 propose 阶段给出类似规划：

```text
MVP：实现最小可用能力
V2：增强抽取 / 审查 / 交互能力
V3：增加 eval / dashboard / 多模型对比
Later：企业级能力、权限、知识库、审计等
```

但实际问题是：

1. MVP 实现完成后，V2 / V3 的规划常常遗失在聊天记录中；
2. OpenSpec 只聚焦当前 change，不负责维护全局演进路线；
3. 当前项目缺少一个机制，把“长期路线图”逐步转化为“可执行 OpenSpec change”；
4. 当执行到中途发现路线要调整时，缺少可追踪的 replan 机制；
5. 当某个 item 完成后发现需要一些小优化时，这些优化用 OpenSpec 又显得过重，但如果只靠聊天记录，又会在项目生命周期中丢失；
6. AI-native 开发的一个核心风险是：LLM 生成了大量阶段性建议，但这些建议没有稳定进入项目事实源，导致长期迭代过程中反复遗漏、重复讨论、上下文漂移。

因此，需要补充一个新的项目级 skill：

```text
roadmap-manager
```

它不是替代 OpenSpec，而是在 OpenSpec 之上提供一层“产品演进管理层”。

---

## 2. 问题本质

这个问题本质上不是简单的 TODO 管理问题，而是：

```text
长期产品路线图
  ↔
单次正式变更规格
  ↔
轻量优化 / 修补记录
  ↔
长期项目记忆
```

之间缺少一套稳定的桥接机制。

更准确地说，目前缺的是 AI-native SDLC 中的 **Product Roadmap Layer**。

现有分层可以理解为：

```text
Roadmap Layer        ：缺失，负责长期产品演进规划
Change Layer         ：OpenSpec，负责正式变更治理
Execution Layer      ：Superpowers / opencode，负责实现、测试、修复
Memory Layer         ：项目长期记忆，负责沉淀事实、架构、踩坑、约定
Patch / Worklog Layer：缺失，负责轻量修补和验收反馈追踪
```

Roadmap Skill 要解决的不是“如何写代码”，而是：

```text
下一步该做什么？
为什么现在做这个？
这个 item 从哪里来？
它是否已经转成 OpenSpec change？
它完成后产生了哪些补丁？
后续计划是否因为它的结果发生了调整？
```

---

## 3. 开源生态调研结论

### 3.1 OpenSpec

OpenSpec 的核心价值是让正式变更拥有结构化文档：

```text
proposal.md
design.md
tasks.md
spec deltas
```

它适合管理一个具体 change 的生命周期：

```text
propose → refine → implement → verify → archive
```

但 OpenSpec 不适合作为全局 Roadmap 系统。原因是：

1. 它以 change 为中心，而不是以 product roadmap 为中心；
2. 它管理的是“当前要做的变更”，不是 MVP / V2 / V3 / Later 的长期演进序列；
3. 它没有天然提供 roadmap item 的状态流转、依赖关系、重排、插队、取消、替代等机制；
4. 它不适合承载大量小修小补，否则会导致 spec 噪声过高。

结论：

```text
OpenSpec 应继续作为正式变更层，而不是 Roadmap 层。
```

---

### 3.2 GitHub Spec Kit

GitHub Spec Kit 提供 spec-driven development 的一套命令式流程：

```text
specify → plan → tasks → implement
```

它对本项目有参考价值，尤其是：

1. 将自然语言需求转成结构化 spec；
2. 将 spec 转成 plan；
3. 将 plan 转成 tasks；
4. 进一步接入 agent 执行。

但它仍然主要聚焦某个 feature 的 spec lifecycle，而不是完整的长期 roadmap lifecycle。

结论：

```text
Spec Kit 可作为流程设计参考，但不建议直接替换当前 OpenSpec + Superpowers 工作流。
```

---

### 3.3 Backlog.md

Backlog.md 是一个接近本需求的开源方向。它提供：

1. Markdown-native task 管理；
2. Git repo 内部存储；
3. CLI / Kanban / Web UI；
4. AI-ready task board；
5. 适合让 AI agent 围绕任务工作。

它很适合做：

```text
repo-local backlog / task board
```

但它并不原生解决：

```text
Roadmap item → OpenSpec change
OpenSpec archive → Roadmap item done
Roadmap replan → 后续 item 重排
轻量 patch → 关联 roadmap item / openspec change
```

结论：

```text
Backlog.md 可以作为未来可选底座或灵感来源，但当前阶段更建议自研轻量 Roadmap Skill。
```

---

### 3.4 总体判断

目前没有发现一个成熟开源项目可以完整覆盖以下链路：

```text
全局 Roadmap
  → 自动 promotion 为 OpenSpec change
  → OpenSpec 完成后回写 Roadmap
  → 小优化进入 Patch Log
  → 中途调整进入 Roadmap Revision
  → 后续 item 自动推进
```

因此建议：

```text
自研一套轻量 roadmap-manager skill。
```

但不要设计成大型项目管理系统，而应定位为：

```text
面向 opencode + OpenSpec + Superpowers 的本地 AI-native Roadmap 编排层。
```

---

## 4. 解决思路

### 4.1 总体设计原则

Roadmap Skill 应遵循以下原则：

#### 原则 1：Roadmap 不等于任务列表

Roadmap 记录的是产品演进阶段，不是所有细碎工作。

适合进入 Roadmap 的内容：

```text
MVP 风险审查
V2 条款抽取
V3 Eval Dashboard
V4 多租户权限
V5 企业知识库增强
```

不适合进入 Roadmap 的内容：

```text
修复一个空输入 bug
调整 prompt 一句话
修改 JSON 字段名
补充 3 个 eval case
优化错误提示文案
```

这些应该进入 Patch Log。

---

#### 原则 2：OpenSpec 只处理正式变更

OpenSpec 适合：

```text
新增核心模块
修改架构
新增数据模型
新增 API
复杂重构
引入 eval gate
```

不适合：

```text
小修小补
prompt 微调
局部 bugfix
轻量验收反馈
```

---

#### 原则 3：Patch Log 负责轻量但可追踪的改动

Patch Log 解决的问题是：

```text
这件事不值得开 OpenSpec，但又不应该消失在聊天记录里。
```

例如：

```text
PATCH-001 improve-json-output-stability
PATCH-002 fix-empty-contract-input
PATCH-003 add-five-eval-cases
PATCH-004 clarify-risk-level-description
```

---

#### 原则 4：Roadmap 必须支持 replan

真实开发中，roadmap 一定会变化。

因此不能只保留当前 roadmap，还必须记录：

```text
为什么调整？
调整前是什么？
调整后是什么？
哪些 item 被新增、延后、取消、替代？
对当前执行有什么影响？
```

这部分由 Roadmap Revision 负责。

---

#### 原则 5：已完成的历史不随意改写

当 roadmap 调整时：

```text
done item      ：原则上不改历史，只补充后续 patch / note
active item    ：修改必须显式记录 revision
ready/planned  ：允许重排、拆分、合并、延后、取消
idea item      ：可自由调整
```

---

#### 原则 6：所有状态都要落盘

不要让 roadmap 状态只存在于聊天上下文中。

至少需要落盘到：

```text
.roadmap/roadmap.md
.roadmap/items/*.md
.roadmap/index.json
.roadmap/revisions/*.md
.roadmap/patches/*.md
```

---

## 5. 目标架构

推荐的本地架构如下：

```text
.roadmap/
  roadmap.md
  index.json

  items/
    RM-001-mvp-risk-review.md
    RM-002-clause-extraction.md
    RM-003-eval-dashboard.md

  revisions/
    2026-06-08-replan-after-mvp.md

  patches/
    PATCH-20260608-001-improve-json-output.md
    PATCH-20260608-002-fix-empty-input.md

  decisions.md

openspec/
  changes/
    add-contract-risk-review-mvp/
      proposal.md
      design.md
      tasks.md
      specs/...

ai-memory/
  project.md
  architecture.md
  pitfalls.md
  decisions.md

skills/
  roadmap-manager/
    SKILL.md
```

逻辑分层：

```text
Roadmap Skill
  负责：长期规划、item 状态、replan、promotion、patch 追踪

OpenSpec
  负责：正式变更 proposal/spec/design/tasks/verify/archive

Superpowers
  负责：TDD、debug、implementation、review

Memory Sync Skill
  负责：把重要结论沉淀到长期项目记忆
```

---

## 6. 核心对象模型

### 6.1 Roadmap Item

Roadmap Item 表示一个产品演进阶段。

示例：

```md
---
id: RM-001
title: MVP 合同风险审查
status: done
stage: mvp
priority: p0
depends_on: []
openspec_change: add-contract-risk-review-mvp
created_at: 2026-06-08
started_at: 2026-06-08
completed_at: 2026-06-15
patches:
  - PATCH-20260608-001
  - PATCH-20260608-002
---

# Goal

实现最小可用的合同风险审查能力。

# Scope

## In

- 上传合同文本
- 调用 LLM 识别风险条款
- 输出风险等级、风险原因、修改建议
- 支持基础人工确认

## Out

- 多模型对比
- Eval Dashboard
- 条款级版本管理
- 企业知识库检索

# Acceptance Criteria

- 用户可以提交一份合同文本
- 系统可以返回结构化风险审查结果
- 每条风险包含风险类型、严重程度、解释、建议修改文本
- 至少覆盖 10 个 golden cases

# Promotion Notes

生成 OpenSpec change 时，优先创建：

- proposal.md
- design.md
- tasks.md
- specs/contract-risk-review/spec.md

# Completion Notes

RM-001 已完成，但验收后发现输出格式稳定性需要继续优化。
相关优化记录在 PATCH-20260608-001 和 PATCH-20260608-002。
```

---

### 6.2 Roadmap Revision

Roadmap Revision 表示一次路线图调整。

示例：

```md
# Roadmap Revision: Replan after MVP

Date: 2026-06-08

## Trigger

RM-001 MVP 风险审查完成后，发现当前系统缺少稳定的 eval baseline。
如果直接推进 RM-002 条款抽取，后续很难判断功能增强是否导致审查质量退化。

## Previous Roadmap

1. RM-001 MVP 风险审查
2. RM-002 V2 条款抽取
3. RM-003 V3 Eval Dashboard

## New Roadmap

1. RM-001 MVP 风险审查
2. RM-004 Eval Dataset & Regression Gate
3. RM-002 V2 条款抽取
4. RM-003 Eval Dashboard

## Changes

- 新增 RM-004：Eval Dataset & Regression Gate
- RM-002 从第二阶段后移到第三阶段
- RM-003 从第三阶段后移到第四阶段

## Rationale

当前最主要风险不是功能不足，而是模型输出质量不可控。
先建立 eval baseline，可以降低后续开发中的回归风险。

## Impact

- RM-002 暂不 promotion 为 OpenSpec change
- RM-004 标记为 ready
- RM-002 状态从 ready 改为 planned
```

---

### 6.3 Patch

Patch 表示轻量优化、bugfix、prompt 微调、验收反馈等。

示例：

```md
---
id: PATCH-20260608-001
title: 改进风险审查输出格式稳定性
status: done
type: optimization
parent_roadmap_item: RM-001
related_openspec_change: add-contract-risk-review-mvp
created_at: 2026-06-08
completed_at: 2026-06-08
---

# Problem

RM-001 完成后，人工验收发现风险审查结果虽然可用，但输出格式不稳定。
部分结果缺少 `risk_level` 或 `suggested_revision` 字段。

# Scope

## In

- 调整 prompt，强化 JSON schema 输出约束
- 增加输出字段校验
- 对缺失字段返回明确错误

## Out

- 不重构审查流程
- 不引入多模型对比
- 不新增 eval dashboard

# Verification

- 使用 5 个现有合同样例重新测试
- 确认每条风险均包含：
  - risk_type
  - risk_level
  - reason
  - suggested_revision

# Result

已完成。输出结构稳定性提升。
```

---

### 6.4 Decision

Decision 用于记录跨 roadmap / patch / OpenSpec 的重要决策。

示例：

```md
# Decision: Patch Log 不升级为 OpenSpec 的条件

Date: 2026-06-08

## Decision

小范围、低风险、当天可完成的优化默认进入 Patch Log，不创建 OpenSpec change。

## Rationale

OpenSpec 适合正式变更。如果所有小修小补都走 OpenSpec，会增加认知负担，并降低开发流速。

## Rule

以下情况必须升级为 OpenSpec：

- 影响公共 API
- 修改核心数据模型
- 影响多个模块
- 涉及架构取舍
- 预计超过半天到一天
- 有较高回归风险
- 改变产品能力边界
```

---

## 7. 状态机设计

### 7.1 Roadmap Item 状态

建议支持以下状态：

```text
idea
planned
ready
active
done
deferred
cancelled
superseded
```

含义：

| 状态         | 含义                       |
| ---------- | ------------------------ |
| idea       | 只是想法，尚未进入正式路线图           |
| planned    | 已规划，但暂不执行                |
| ready      | 已准备好转成 OpenSpec change   |
| active     | 已生成 OpenSpec change，正在执行 |
| done       | 已完成并验收                   |
| deferred   | 延后，不删除                   |
| cancelled  | 明确取消                     |
| superseded | 被其他 item 替代              |

核心流转：

```text
idea → planned → ready → active → done
```

调整流转：

```text
planned → deferred
ready → deferred
planned → cancelled
ready → cancelled
planned → superseded
ready → superseded
```

---

### 7.2 Patch 状态

建议支持：

```text
open
active
done
cancelled
escalated
```

含义：

| 状态        | 含义                  |
| --------- | ------------------- |
| open      | 已记录，尚未处理            |
| active    | 正在处理                |
| done      | 已完成                 |
| cancelled | 放弃处理                |
| escalated | 升级为 OpenSpec change |

核心流转：

```text
open → active → done
open → escalated
open → cancelled
```

---

### 7.3 Roadmap Revision 状态

Revision 通常是不可变历史记录，不需要复杂状态。

可选字段：

```yaml
status: applied
```

如果后续需要 review 机制，可扩展为：

```text
draft
applied
reverted
```

最小版本不建议复杂化。

---

## 8. 命令设计

### 8.1 Roadmap 主线命令

#### `/roadmap.init`

初始化目录结构。

输入：

```text
/roadmap.init
```

输出：

```text
.roadmap/
  roadmap.md
  index.json
  items/
  revisions/
  patches/
  decisions.md
```

---

#### `/roadmap.capture`

从当前对话、需求讨论或技术方案中提取 MVP / V2 / V3 / Later，并生成 roadmap items。

输入示例：

```text
/roadmap.capture
请把上面讨论里的 MVP、V2、V3 规划整理进 roadmap。
```

行为：

1. 读取当前上下文；
2. 识别阶段性规划；
3. 为每个阶段生成 Roadmap Item；
4. 更新 `roadmap.md`；
5. 更新 `index.json`。

输出示例：

```text
Created:
- RM-001 MVP 合同风险审查
- RM-002 V2 条款抽取
- RM-003 V3 Eval Dashboard
```

---

#### `/roadmap.list`

展示当前路线图。

输出示例：

```text
RM-001  done     MVP 合同风险审查
RM-004  ready    Eval Dataset & Regression Gate
RM-002  planned  V2 条款抽取
RM-003  planned  V3 Eval Dashboard
```

---

#### `/roadmap.promote RM-002`

将某个 roadmap item 转成 OpenSpec change。

行为：

1. 读取 `RM-002`；
2. 检查依赖项是否已完成；
3. 生成 OpenSpec change id；
4. 创建 `openspec/changes/<change-id>/`；
5. 生成 proposal / design / tasks / spec delta 草稿；
6. 更新 roadmap item：

   * `status: active`
   * `openspec_change: <change-id>`
   * `started_at: <date>`
7. 更新 `index.json` 和 `roadmap.md`。

---

#### `/roadmap.next`

自动推进下一个可执行 item。

行为：

1. 找到第一个 `status = ready` 的 item；
2. 检查 `depends_on`；
3. 如无阻塞，执行 promote；
4. 如果没有 ready item，则提示需要 replan 或手动标记 ready。

---

#### `/roadmap.done RM-002`

标记 roadmap item 完成。

行为：

1. 检查关联 OpenSpec change 是否已完成或已 archive；
2. 读取完成摘要；
3. 更新 item：

   * `status: done`
   * `completed_at: <date>`
   * `completion_notes`
4. 更新 `roadmap.md` 和 `index.json`；
5. 提示是否需要：

   * 创建 patch；
   * 触发 roadmap replan；
   * 执行 memory sync。

---

#### `/roadmap.sync`

同步 OpenSpec 状态与 roadmap 状态。

行为：

1. 扫描 `.roadmap/items/*.md`；
2. 检查其中的 `openspec_change`；
3. 对比 `openspec/changes/` 或 `openspec/archive/`；
4. 自动更新状态建议；
5. 输出差异报告。

---

### 8.2 Roadmap 调整命令

#### `/roadmap.replan`

用于路线图重规划。

输入示例：

```text
/roadmap.replan
RM-001 完成后发现 eval baseline 更重要，请重新调整后续 roadmap。
```

行为：

1. 读取当前 roadmap；
2. 保留 done item 历史；
3. 分析 active / ready / planned item；
4. 生成调整方案；
5. 创建 `.roadmap/revisions/<date>-<slug>.md`；
6. 更新受影响 item 的状态、顺序、依赖关系；
7. 更新 `roadmap.md` 和 `index.json`。

约束：

```text
- 不应静默删除 item；
- 取消必须标记 cancelled；
- 替代必须标记 superseded；
- 延后必须标记 deferred 或 planned；
- active item 的调整必须显式记录影响。
```

---

#### `/roadmap.defer RM-002`

将 item 延后。

行为：

```text
status: deferred
```

并在 item 中追加：

```md
# Deferred Reason

...
```

---

#### `/roadmap.cancel RM-003`

取消 item。

行为：

```text
status: cancelled
```

并记录取消原因。

---

#### `/roadmap.supersede RM-002 RM-004`

表示 RM-002 被 RM-004 替代。

行为：

```yaml
status: superseded
superseded_by: RM-004
```

---

### 8.3 Patch 命令

#### `/patch.capture`

记录一个轻量 patch。

输入示例：

```text
/patch.capture
RM-001 完成后发现输出 JSON 不稳定，请记录为轻量优化。
```

行为：

1. 判断是否适合 patch；
2. 如果适合，创建 `.roadmap/patches/PATCH-<date>-<seq>-<slug>.md`；
3. 关联 parent roadmap item；
4. 关联 related OpenSpec change；
5. 更新 roadmap item 的 `patches` 列表；
6. 更新 `index.json`。

---

#### `/patch.apply PATCH-20260608-001`

执行 patch。

行为：

1. 读取 patch scope；
2. 确认不需要升级为 OpenSpec；
3. 执行局部修改；
4. 运行最小验证；
5. 更新 patch 状态为 `active` 或 `done`。

---

#### `/patch.done PATCH-20260608-001`

标记 patch 完成。

行为：

1. 更新 patch：

   * `status: done`
   * `completed_at`
   * `result`
2. 更新 parent roadmap item；
3. 如果 patch 产生重要经验，提示执行 memory sync。

---

#### `/patch.escalate PATCH-20260608-001`

将 patch 升级为 OpenSpec change。

触发条件：

```text
- 影响公共 API
- 修改核心数据模型
- 影响多个模块
- 需要复杂测试矩阵
- 涉及架构取舍
- 预计超过半天到一天
- 有较高回归风险
- 改变产品能力边界
```

行为：

1. 读取 patch；
2. 创建 OpenSpec change；
3. patch 状态改为 `escalated`；
4. 写入 `related_openspec_change`；
5. 更新 parent roadmap item。

---

## 9. 文件结构详细设计

### 9.1 推荐目录

```text
.roadmap/
  roadmap.md
  index.json

  items/
    RM-001-mvp-risk-review.md
    RM-002-clause-extraction.md
    RM-003-eval-dashboard.md

  revisions/
    2026-06-08-replan-after-mvp.md

  patches/
    PATCH-20260608-001-improve-json-output.md
    PATCH-20260608-002-fix-empty-input.md

  decisions.md
```

---

### 9.2 `roadmap.md`

用途：

```text
人类可读总览。
```

示例：

````md
# Product Roadmap

## Current Sequence

| ID | Status | Title | OpenSpec | Notes |
|---|---|---|---|---|
| RM-001 | done | MVP 风险审查 | add-contract-risk-review-mvp | 已完成，后续有 2 个 patch |
| RM-004 | ready | Eval Baseline | - | 插队，优先于 V2 |
| RM-002 | planned | V2 条款抽取 | - | 延后 |
| RM-003 | planned | V3 Eval Dashboard | - | 后续再做 |

## Active Item

当前没有 active item。

## Next Recommended Action

执行：

```bash
/roadmap.promote RM-004
````

````

---

### 9.3 `index.json`

用途：

```text
机器可读索引，方便 skill 快速扫描。
````

示例：

```json
{
  "version": 1,
  "current": "RM-004",
  "items": [
    {
      "id": "RM-001",
      "status": "done",
      "title": "MVP 风险审查",
      "openspec_change": "add-contract-risk-review-mvp",
      "patches": [
        "PATCH-20260608-001",
        "PATCH-20260608-002"
      ]
    },
    {
      "id": "RM-004",
      "status": "ready",
      "title": "Eval Baseline",
      "openspec_change": null,
      "patches": []
    },
    {
      "id": "RM-002",
      "status": "planned",
      "title": "V2 条款抽取",
      "openspec_change": null,
      "patches": []
    }
  ]
}
```

设计原则：

1. `index.json` 是派生索引，不是唯一事实源；
2. Markdown item 是主记录；
3. 如果不一致，以 item 文件为准，并允许 `/roadmap.sync` 修复索引；
4. 不建议让人工频繁编辑 `index.json`。

---

### 9.4 `items/*.md`

用途：

```text
记录单个 roadmap item 的完整上下文。
```

必须包含：

```text
frontmatter
Goal
Scope
Acceptance Criteria
Promotion Notes
Completion Notes
```

---

### 9.5 `patches/*.md`

用途：

```text
记录轻量优化、bugfix、prompt tuning、验收反馈。
```

必须包含：

```text
frontmatter
Problem
Scope
Verification
Result
```

---

### 9.6 `revisions/*.md`

用途：

```text
记录 roadmap 调整历史。
```

必须包含：

```text
Trigger
Previous Roadmap
New Roadmap
Changes
Rationale
Impact
```

---

### 9.7 `decisions.md`

用途：

```text
记录跨 item、patch、OpenSpec 的长期决策。
```

适合记录：

```text
什么时候用 OpenSpec
什么时候用 Patch
什么时候需要 eval gate
什么时候需要 memory sync
什么时候可以跳过 design.md
```

---

## 10. Roadmap / OpenSpec / Patch 的边界规则

### 10.1 进入 Roadmap 的条件

满足以下条件之一，建议进入 Roadmap：

```text
- 改变产品能力边界
- 是一个明确版本阶段
- 需要多天开发
- 需要正式验收
- 影响后续技术路线
- 有依赖关系和优先级
- 可能需要 OpenSpec change
```

示例：

```text
MVP 风险审查
V2 条款抽取
V3 Eval Dashboard
V4 多租户权限
```

---

### 10.2 进入 OpenSpec 的条件

满足以下条件之一，建议创建 OpenSpec change：

```text
- 新增核心功能
- 修改核心架构
- 修改公共 API
- 修改核心数据模型
- 影响多个模块
- 需要复杂测试矩阵
- 有明显架构取舍
- 回归风险较高
- 需要正式 proposal / design / tasks
```

---

### 10.3 进入 Patch 的条件

满足以下条件，建议使用 Patch：

```text
- 小范围
- 低风险
- 局部修改
- 当天可完成
- 不改变产品能力边界
- 不影响核心架构
- 不需要完整 proposal / design
```

示例：

```text
prompt 微调
输出格式修正
小 bugfix
补充少量 eval case
错误文案优化
小范围 UI 调整
```

---

### 10.4 Patch 升级 OpenSpec 的条件

如果 patch 满足以下任一条件，必须升级为 OpenSpec：

```text
- 影响公共 API
- 修改核心数据模型
- 影响多个模块
- 需要新增复杂测试矩阵
- 涉及架构取舍
- 预计超过半天到一天
- 有较高回归风险
- 改变产品能力边界
```

---

## 11. 典型生命周期

### 11.1 初始规划

用户与 LLM 讨论后得到：

```text
MVP：合同风险审查
V2：条款抽取
V3：Eval Dashboard
```

执行：

```bash
/roadmap.capture
```

生成：

```text
RM-001 MVP 合同风险审查
RM-002 V2 条款抽取
RM-003 V3 Eval Dashboard
```

---

### 11.2 推进 MVP

执行：

```bash
/roadmap.promote RM-001
```

生成：

```text
openspec/changes/add-contract-risk-review-mvp/
```

然后通过 OpenSpec / Superpowers 执行：

```text
proposal → design → tasks → implementation → verify → archive
```

完成后：

```bash
/roadmap.done RM-001
```

---

### 11.3 MVP 后发现小问题

验收发现：

```text
JSON 输出不稳定
空合同异常处理不好
风险等级解释不清楚
```

这些不适合直接开三个 OpenSpec。

执行：

```bash
/patch.capture
```

生成：

```text
PATCH-20260608-001 improve-json-output
PATCH-20260608-002 fix-empty-contract
PATCH-20260608-003 clarify-risk-level-description
```

然后分别执行：

```bash
/patch.apply PATCH-20260608-001
/patch.done PATCH-20260608-001
```

---

### 11.4 准备做 V2 前发现路线要调整

原计划：

```text
RM-001 MVP 风险审查
RM-002 V2 条款抽取
RM-003 V3 Eval Dashboard
```

但完成 MVP 后发现：

```text
如果没有 eval baseline，后续 V2 很难判断是否造成审查质量退化。
```

执行：

```bash
/roadmap.replan
```

调整为：

```text
RM-001 done     MVP 风险审查
RM-004 ready    Eval Dataset & Regression Gate
RM-002 planned  V2 条款抽取
RM-003 planned  Eval Dashboard
```

同时生成：

```text
.roadmap/revisions/2026-06-08-insert-eval-baseline.md
```

---

### 11.5 自动推进下一个 item

执行：

```bash
/roadmap.next
```

系统找到：

```text
RM-004 Eval Dataset & Regression Gate
```

并生成对应 OpenSpec change。

---

## 12. 与 Memory Sync 的关系

Roadmap Skill 不应承担长期记忆同步职责，但应在关键节点提示或触发 Memory Sync。

建议在以下节点触发：

```text
- roadmap.done
- patch.done
- roadmap.replan
- patch.escalate
- openspec archive 后
```

Memory Sync 应沉淀：

```text
- 已完成能力
- 当前架构
- 重要设计决策
- 踩坑记录
- eval 基线
- 模型 / prompt 调整经验
```

但 Roadmap Skill 自身只负责记录：

```text
这个 item / patch / revision 发生了什么。
```

---

## 13. Skill 实现建议

### 13.1 第一阶段：纯文本 Skill

第一版不建议写复杂 CLI 或脚本。建议先做纯文本 skill：

```text
skills/roadmap-manager/SKILL.md
```

核心内容：

```text
- 何时使用 roadmap
- 何时使用 OpenSpec
- 何时使用 patch
- 文件结构
- 命令语义
- 输出模板
- 状态机
- promotion 规则
- replan 规则
```

第一阶段目标：

```text
让 opencode 在执行 /roadmap.* 和 /patch.* 风格指令时，稳定生成和维护文件。
```

---

### 13.2 第二阶段：增加脚本辅助

当纯文本 skill 稳定后，再增加脚本：

```text
scripts/roadmap/
  init.ts
  list.ts
  sync.ts
  validate.ts
```

优先实现：

```text
roadmap.validate
roadmap.list
roadmap.sync
```

原因：

```text
读和校验比写更容易稳定。
```

不建议一开始就让脚本负责复杂生成。复杂生成仍交给 LLM，脚本负责检查结构和一致性。

---

### 13.3 第三阶段：与 OpenSpec 深度集成

后续可以增加：

```text
roadmap.promote.ts
```

自动生成：

```text
openspec/changes/<change-id>/
```

但是否自动生成 design / tasks / specs，可以分阶段：

```text
v1：只生成 change 目录和 proposal 草稿
v2：生成 proposal + tasks
v3：生成 proposal + design + tasks + spec delta
v4：支持校验 OpenSpec schema
```

---

## 14. MVP 范围建议

Roadmap Skill 的 MVP 不要做太大。

### 14.1 MVP 必须支持

```text
/roadmap.init
/roadmap.capture
/roadmap.list
/roadmap.promote
/roadmap.done
/roadmap.replan
/patch.capture
/patch.done
```

### 14.2 MVP 文件

```text
.roadmap/
  roadmap.md
  index.json
  items/
  revisions/
  patches/
  decisions.md
```

### 14.3 MVP 不必支持

```text
Web UI
Kanban
GitHub Issues 同步
复杂 CLI
多用户协作
自动依赖图
自动生成 release notes
```

这些可以放到 V2 / V3。

---

## 15. 后续版本规划

### V1：Roadmap Core

目标：

```text
解决 MVP / V2 / V3 不丢失的问题。
```

能力：

```text
- init
- capture
- list
- promote
- done
```

---

### V2：Replan & Patch

目标：

```text
解决中途调整和小优化追踪问题。
```

能力：

```text
- replan
- defer
- cancel
- supersede
- patch.capture
- patch.done
- patch.escalate
```

---

### V3：Validation & Sync

目标：

```text
提升稳定性，减少手工检查负担。
```

能力：

```text
- index.json 校验
- roadmap.md 重建
- item 状态一致性检查
- OpenSpec change 状态同步
- patch 关联检查
```

---

### V4：Backlog / GitHub Issues 集成

目标：

```text
适配团队协作和可视化管理。
```

能力：

```text
- Backlog.md task 映射
- GitHub issue 映射
- roadmap item → issue
- patch → issue comment
- OpenSpec change → PR / issue link
```

---

## 16. 推荐给 opencode 的执行提示词

开发 Roadmap Skill 时，可以给 opencode 使用以下提示词：

```text
我要在当前项目中开发一个 roadmap-manager skill，用于补齐 OpenSpec 只关注单个 change、缺少全局 roadmap 管理的问题。

请基于以下目标进行设计和实现：

1. 新增 .roadmap/ 目录结构：
   - roadmap.md
   - index.json
   - items/
   - revisions/
   - patches/
   - decisions.md

2. 新增 skills/roadmap-manager/SKILL.md，描述以下能力：
   - /roadmap.init
   - /roadmap.capture
   - /roadmap.list
   - /roadmap.promote
   - /roadmap.done
   - /roadmap.replan
   - /patch.capture
   - /patch.done
   - /patch.escalate

3. Roadmap item 用于记录产品演进阶段，例如 MVP、V2、V3。
   OpenSpec change 用于正式结构化变更。
   Patch 用于轻量优化、bugfix、prompt tuning、验收反馈。

4. Roadmap item 状态包括：
   - idea
   - planned
   - ready
   - active
   - done
   - deferred
   - cancelled
   - superseded

5. Patch 状态包括：
   - open
   - active
   - done
   - cancelled
   - escalated

6. Roadmap 必须支持 replan。
   每次 replan 都要在 .roadmap/revisions/ 下生成 revision 文件，记录：
   - Trigger
   - Previous Roadmap
   - New Roadmap
   - Changes
   - Rationale
   - Impact

7. Patch 必须可关联：
   - parent_roadmap_item
   - related_openspec_change

8. /roadmap.promote 应将 roadmap item 转成 OpenSpec change，并回写 roadmap item 的 openspec_change 字段。

9. /roadmap.done 应标记 item 完成，并提示是否需要 patch.capture、roadmap.replan 或 memory sync。

10. 第一版优先做纯文本 skill 和模板，不要引入复杂 CLI。需要保证文件结构清晰、规则明确、适合 LLM 稳定执行。

请先生成详细设计方案和文件模板，然后再进入实现。
```

---

## 17. 最终结论

当前问题可以总结为：

```text
OpenSpec 解决的是“当前 change 怎么做”；
Superpowers 解决的是“具体执行怎么做”；
Memory Sync 解决的是“长期知识怎么沉淀”；
但缺少一个 Roadmap Skill 解决“长期路线怎么不丢、怎么推进、怎么调整”。
```

因此建议自研 `roadmap-manager` skill。

最终目标架构：

```text
Roadmap
  负责不迷路

OpenSpec
  负责不乱改

Patch Log
  负责不丢细节

Revision
  负责不丢决策历史

Memory Sync
  负责不丢长期知识
```

推荐最小闭环：

```text
/roadmap.capture
  ↓
/roadmap.promote RM-001
  ↓
OpenSpec apply / verify / archive
  ↓
/roadmap.done RM-001
  ↓
/patch.capture 记录轻量优化
  ↓
/patch.done
  ↓
/roadmap.replan 视情况调整后续路线
  ↓
/roadmap.next
```

这套设计可以解决以下核心问题：

1. MVP / V2 / V3 不再遗失；
2. 每个阶段都可以转成 OpenSpec change；
3. 完成后的轻量优化不会消失在聊天记录里；
4. 中途路线调整有 revision 记录；
5. Roadmap、OpenSpec、Patch、Memory 各司其职；
6. 适合本地 opencode + OpenSpec + Superpowers 的 AI-native 开发工作流。
