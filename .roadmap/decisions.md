# Decisions

## Decision: sdlc-roadmap 的定位

Date: 2026-06-09

### Decision

sdlc-roadmap 是薄 SDLC 编排层，不是重量级项目管理系统。

### Rationale

OpenSpec 解决"当前 change 怎么做"、Superpowers 解决"具体执行怎么做"、Memory Sync 解决"长期知识怎么沉淀"，三者之间缺少一层"长期路线怎么不丢、怎么推进、怎么调整"的编排层。自研轻量 skill 比引入完整项目管理工具更适配现有工作流。

### Rule

- Roadmap 负责：长期路线可见性、item 状态流转、promotion 到 OpenSpec 的入口、done 后后续提示。
- OpenSpec 负责：正式 change 的 proposal/design/tasks/spec。
- Superpowers 负责：TDD、debug、review、implementation。
- Memory Sync 负责：长期事实沉淀（能力、架构、踩坑、约定）。
- Roadmap 不直接执行代码修改；不复制 OpenSpec 逻辑。

---

## Decision: MVP 不包含 replan 和 patch.apply

Date: 2026-06-09

### Decision

sdlc-roadmap MVP 范围：init / capture / list / promote / done + 三个最小脚本（validate/list/rebuild_index）。replan 和 patch 功能推迟到 V2。

### Rationale

第一版如果同时覆盖 roadmap、OpenSpec promotion、patch log、revision log，行为面太大不利于稳定。先验证核心编排闭环，后续再加调整和修补能力。

---

## Decision: promote 不复制 OpenSpec 逻辑

Date: 2026-06-09

### Decision

`roadmap promote` 读取 RM item 生成 promotion context，调用或引导 OpenSpec skill（openspec-propose / openspec-new-change），然后回写 `openspec_change` 和状态。不直接生成 proposal/design/tasks/spec。

### Rationale

避免和已有 OpenSpec skills 重叠，保持各层职责清晰。Roadmap 负责"为什么做、做哪一个"，OpenSpec 负责"怎么规格化这个 change"。

---

## Decision: Patch Log 不进入 MVP，V2 只做记录不做执行器

Date: 2026-06-09

### Decision

MVP 不包含 Patch Log。V2 加入 patch capture/done/escalate，但不做 `/patch.apply`。Patch 执行仍走普通开发流程、TDD 或 debugging skill。

### Rationale

Patch Log 有价值，但和执行层重叠风险高。先保证核心路线图闭环，再扩展轻量追踪。`/patch.apply` 容易和 TDD/debug/review 技能冲突。

---

## Decision: 命名统一为 sdlc-roadmap

Date: 2026-06-09

### Decision

Skill 名称为 `sdlc-roadmap`（而非 `roadmap-manager`）。目录：`skills/sdlc-roadmap/`。

### Rationale

与现有 `sdlc-*` 技能族（sdlc-project-bootstrap, sdlc-openspec-init, sdlc-repository-memory-*）保持命名一致，触发边界更清晰，属于 SDLC 工作流编排层。
