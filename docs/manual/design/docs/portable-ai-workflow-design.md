# 可迁移 AI CLI 工作流设计方案

## 1. 背景

当前我在使用 AI CLI 工具进行本地开发，主要涉及：

* Claude Code
* Codex CLI
* OpenCode

这些工具都具备一定的 agentic coding 能力，但它们的工作流机制、扩展机制、配置方式并不统一。

例如：

| CLI         | 主要扩展方式                                          |
| ----------- | ----------------------------------------------- |
| Claude Code | hooks、skills、subagents、permissions、`CLAUDE.md`  |
| Codex CLI   | hooks、`AGENTS.md`、sandbox、approval              |
| OpenCode    | agents、commands、plugins、instructions、MCP config |

其中，Claude Code 和 Codex CLI 都有类似 hooks 的生命周期扩展能力；OpenCode 则主要通过 plugins、commands、agents、instructions 来实现类似能力。

我当前已经围绕 OpenCode + Superpowers + OpenSpec 形成了一套 AI-native 开发流程，但随着实践深入，发现几个核心问题：

### 1.1 工作流容易绑定单一 CLI

如果直接基于某个工具的原生机制开发，例如：

* Claude Code hooks
* Codex hooks
* OpenCode plugins
* OpenCode commands
* Claude skills
* `AGENTS.md`
* `CLAUDE.md`

那么这套工作流会很难迁移到其他 CLI。

例如，如果把 memory sync 完整写成 Claude Code `Stop hook`，迁移到 OpenCode 时就要重新实现。如果把 roadmap 管理完整写成 OpenCode plugin，迁移到 Codex 时也会有较大成本。

因此，不能围绕某个 CLI 的具体能力设计核心工作流。

---

### 1.2 三款 CLI 能力相似，但语义和接口不同

三款 CLI 都能支持类似的开发流程：

* plan
* apply
* review
* test
* memory sync
* roadmap update
* eval collect
* permission control
* tool call guard
* session lifecycle hook

但它们对这些能力的表达方式不同。

例如：

| 抽象能力    | Claude Code          | Codex CLI                   | OpenCode                    |
| ------- | -------------------- | --------------------------- | --------------------------- |
| 会话开始    | `SessionStart hook`  | `SessionStart hook`         | plugin event / command init |
| 工具调用前拦截 | `PreToolUse hook`    | `PreToolUse hook`           | plugin event                |
| 工具调用后处理 | `PostToolUse hook`   | `PostToolUse hook`          | plugin event                |
| 结束时同步记忆 | `Stop hook`          | `Stop hook`                 | plugin / command            |
| 项目指令    | `CLAUDE.md`          | `AGENTS.md`                 | instructions config         |
| 计划模式    | prompt + permissions | sandbox + approval + prompt | Plan agent                  |
| 执行模式    | permissions          | workspace-write / approval  | Build agent                 |

因此，如果希望一套工作流可以跨 CLI 迁移，就需要先抽象出稳定的工作流语义，再分别映射到各个 CLI 的具体机制。

---

### 1.3 当前工作流存在长期治理需求

我希望开发的不只是一个单点 skill，而是一套长期可演进的 AI 开发工作流体系，覆盖：

* 需求澄清
* brainstorm
* proposal
* design
* task 拆解
* TDD / eval
* apply
* verify
* archive
* roadmap 维护
* 小优化追踪
* memory sync
* session handoff
* 模型切换后的稳定性治理
* MCP / tools / skills 路由治理

这些能力如果都散落在不同 CLI 的配置文件中，会导致：

* 迁移困难
* 规则重复
* 维护成本高
* 工作流语义不稳定
* CLI 切换后行为不一致
* 后续扩展新工具时需要大规模重写

因此，需要把它抽象成一套 CLI 无关的基础工作流内核。

---

## 2. 目标

本项目目标是开发一套 **可迁移的 AI CLI 工作流框架**。

它应该能够在 Claude Code、Codex CLI、OpenCode 之间迁移，并且未来可以扩展到其他 agentic coding 工具，例如 Cursor CLI、Gemini CLI、Aider 等。

---

### 2.1 核心目标

#### 目标一：构建稳定的 Workflow Core

将真正的工作流语义沉淀到 CLI 无关的基础层中。

基础层负责定义：

* 生命周期
* 状态机
* 文档结构
* 任务状态
* roadmap 状态
* eval 数据结构
* memory 结构
* 执行边界
* 权限策略
* 工作流规范

核心原则：

```text
Core 不依赖 Claude Code、Codex、OpenCode 中任何一个具体 CLI。
```

---

#### 目标二：构建 Capability Contract

在 Core 和各个 CLI 之间增加一层能力契约。

能力契约负责定义抽象能力，例如：

* `on_session_start`
* `on_user_prompt`
* `before_tool_use`
* `after_tool_use`
* `on_stop`
* `before_apply`
* `after_apply`
* `plan_only`
* `apply_changes`
* `run_tests`
* `update_task_status`
* `update_roadmap_status`
* `sync_memory`
* `collect_eval_case`
* `record_decision`

这些能力不是某个 CLI 的原生接口，而是我自己的标准能力接口。

---

#### 目标三：构建 CLI Adapter

为不同 CLI 提供转义层 / 适配层。

Adapter 负责将 Capability Contract 映射到具体 CLI 能力。

例如：

```text
on_stop
  → Claude Code Stop hook
  → Codex Stop hook
  → OpenCode plugin event / command
```

Adapter 不应该承载核心业务逻辑，只负责：

* 触发
* 注入
* 映射
* 调用统一脚本
* 生成 CLI 配置

---

#### 目标四：支持长期项目治理

这套工作流不仅要解决一次性代码生成问题，还要支持项目生命周期中的长期治理，包括：

* roadmap 不丢失
* MVP / V2 / V3 可追踪
* 小优化可以被记录
* task 状态可以被持续更新
* session 切换后可以续接
* eval case 可以沉淀
* model upgrade 后可以回归验证
* memory 可以基于 commit / diff 增量同步
* AI 在 propose 阶段不能越权写代码
* AI 在 apply 阶段需要按任务闭环执行

---

## 3. 方案

## 3.1 总体架构

推荐采用三层架构：

```text
Workflow Core / 基础内核层
        ↓
Capability Contract / 能力契约层
        ↓
CLI Adapter / 转义适配层
        ↓
Claude Code / Codex CLI / OpenCode
```

核心原则：

```text
不要迁移 CLI 实现，要迁移工作流语义。
```

也就是说，不要把工作流定义成：

```text
Claude Code Stop hook 里执行 memory sync
```

而应该定义成：

```text
当开发会话结束、重要文件变化、或者用户准备提交代码时，触发 memory sync。
```

然后分别在不同 CLI 中映射：

| CLI         | 实现                                |
| ----------- | --------------------------------- |
| Claude Code | `Stop hook`                       |
| Codex CLI   | `Stop hook`                       |
| OpenCode    | plugin event / command / git hook |

---

## 3.2 基础内核层：Workflow Core

Workflow Core 是整个系统中最重要的一层。

它负责定义稳定、不依赖具体 CLI 的工作流语义。

### 3.2.1 Core 应包含的模块

| 模块                   | 作用                                                                        |
| -------------------- | ------------------------------------------------------------------------- |
| `workflow-lifecycle` | 定义 brainstorm / propose / apply / verify / archive / surgery / bugfix 等阶段 |
| `roadmap-core`       | 管理全局路线图、版本演进、item 状态                                                      |
| `task-core`          | 管理任务拆解、任务状态、小优化追踪                                                         |
| `spec-core`          | 管理 proposal、design、decision、OpenSpec-lite 文档                              |
| `eval-core`          | 管理 case collection、golden dataset、eval loop                               |
| `memory-core`        | 管理项目记忆、pitfalls、commit baseline、diff sync                                 |
| `permission-core`    | 定义 plan-only、apply、review-only 等权限边界                                      |
| `handoff-core`       | 支持长任务跨 session 续接                                                         |

---

### 3.2.2 Core 的职责

Core 层负责：

| 职责      | 示例                                              |
| ------- | ----------------------------------------------- |
| 生命周期定义  | brainstorm → propose → apply → verify → archive |
| 状态机定义   | todo、doing、blocked、done、deferred                |
| 文档结构定义  | roadmap.md、tasks.md、decision-log.md、pitfalls.md |
| 输入输出契约  | 输入需求，输出 proposal / tasks / eval result          |
| 执行边界    | propose 阶段只能读，apply 阶段才能写                       |
| 任务闭环    | 代码修改后必须更新 task 状态                               |
| 记忆同步    | 重要变更后更新 project memory                          |
| eval 沉淀 | 缺陷和人工反馈进入 eval case collection                  |

---

### 3.2.3 Core 不应该做的事情

Core 不应该直接依赖：

* Claude Code hooks
* Codex hooks
* OpenCode plugins
* Claude skills
* OpenCode commands
* `CLAUDE.md`
* `AGENTS.md`
* 某个 CLI 的权限配置
* 某个 CLI 的 agent 配置

这些都应该放到 Adapter 层。

---

## 3.3 能力契约层：Capability Contract

Capability Contract 是 Core 和 CLI Adapter 之间的标准接口。

它负责回答一个问题：

> 我的工作流需要哪些抽象能力？

---

### 3.3.1 抽象事件

```yaml
events:
  - on_session_start
  - on_user_prompt
  - before_tool_use
  - after_tool_use
  - before_apply
  - after_apply
  - on_permission_request
  - before_compact
  - on_stop
```

---

### 3.3.2 抽象执行能力

```yaml
execution:
  - read_files
  - edit_files
  - run_shell
  - run_tests
  - create_branch
  - commit
  - inspect_diff
```

---

### 3.3.3 抽象治理能力

```yaml
governance:
  - require_plan_before_apply
  - block_write_in_plan_mode
  - require_task_mark_done
  - require_roadmap_update
  - require_memory_sync_before_commit
  - require_eval_case_for_regression
  - require_decision_log_for_scope_change
```

---

### 3.3.4 抽象 artifact 能力

```yaml
artifacts:
  - update_roadmap
  - update_tasks
  - update_decision_log
  - update_eval_cases
  - update_memory_index
  - update_handoff
```

---

### 3.3.5 能力支持等级

由于不同 CLI 对同一能力的支持程度不同，需要定义 support level：

```yaml
support_level:
  native: CLI 原生支持
  emulated: 通过 prompt / command / plugin / script 模拟
  partial: 部分支持，需要人工约束
  unsupported: 不支持
```

示例：

```yaml
opencode:
  plan_only:
    support: native
    implementation: "Plan agent"

  memory_sync_on_stop:
    support: emulated
    implementation: "plugin event or manual command"

  project_instruction:
    support: native
    implementation: "instructions config"

codex:
  plan_only:
    support: partial
    implementation: "sandbox + approval + prompt"

  memory_sync_on_stop:
    support: native
    implementation: "Stop hook"

  project_instruction:
    support: native
    implementation: "AGENTS.md"

claude_code:
  plan_only:
    support: partial
    implementation: "permissions + prompt"

  memory_sync_on_stop:
    support: native
    implementation: "Stop hook"

  project_instruction:
    support: native
    implementation: "CLAUDE.md"
```

---

## 3.4 CLI Adapter 层

Adapter 层负责把 Capability Contract 映射到具体 CLI。

### 3.4.1 Adapter 的职责

Adapter 只做三件事：

| 职责 | 示例                                                               |
| -- | ---------------------------------------------------------------- |
| 触发 | 将 `on_stop` 映射为 Stop hook / plugin event                         |
| 注入 | 将 core runbook 注入到 `CLAUDE.md`、`AGENTS.md`、OpenCode instructions |
| 执行 | 调用统一脚本，例如 `sync-memory.ts`、`validate-roadmap.ts`                 |

---

### 3.4.2 Adapter 不应该做的事

Adapter 不应该承载核心业务规则。

错误做法：

```text
在 adapters/opencode/plugins/roadmap.ts 中实现完整 roadmap 状态机。
```

正确做法：

```text
adapters/opencode/plugins/roadmap.ts 只负责在合适时机调用 core/scripts/update-roadmap.ts。
```

也就是说：

```text
业务逻辑放 Core。
CLI 差异放 Adapter。
```

---

## 3.5 推荐目录结构

```text
.ai-workflow/
  README.md

  core/
    lifecycle.md
    principles.md
    roles.md
    safety.md

  contracts/
    capabilities.yaml
    events.yaml
    artifacts.yaml
    permissions.yaml

  schemas/
    roadmap.schema.json
    task.schema.json
    decision.schema.json
    eval-case.schema.json
    memory.schema.json

  runbooks/
    brainstorm.md
    propose.md
    apply.md
    verify.md
    archive.md
    surgery.md
    bugfix.md
    eval-loop.md
    memory-sync.md

  artifacts/
    roadmap.md
    backlog.md
    decision-log.md
    pitfalls.md
    eval-cases.jsonl
    memory-index.md
    handoff.md

  scripts/
    validate-roadmap.ts
    validate-tasks.ts
    sync-memory.ts
    collect-eval-case.ts
    check-plan-only.ts
    update-roadmap.ts
    update-task-status.ts

  adapters/
    claude-code/
      CLAUDE.md
      settings.json
      hooks/
        memory-sync.sh
        guard-plan-mode.sh
      skills/

    codex/
      AGENTS.md
      hooks.json
      config.toml
      prompts/

    opencode/
      opencode.jsonc
      commands/
      plugins/
        memory-sync.ts
        roadmap-guard.ts
```

---

## 3.6 推荐核心 artifact

### 3.6.1 roadmap.md

用于维护全局路线图，解决 MVP / V2 / V3 被遗忘的问题。

建议结构：

```markdown
# Roadmap

## Active

### item-001: MVP 合同风险审查基础能力

Status: doing
Priority: high
Linked Spec: specs/add-contract-review-mvp
Started At: 2026-xx-xx

#### Goal

实现合同条款风险识别、风险等级判断、理由解释、修改建议生成。

#### Acceptance Criteria

- [ ] 支持上传合同文本
- [ ] 支持按条款识别风险
- [ ] 支持输出风险等级
- [ ] 支持生成审查理由
- [ ] 支持生成修改建议

#### Follow-ups

- [ ] 增加风险类型 taxonomy
- [ ] 增加模型回归 eval
```

---

### 3.6.2 backlog.md

用于记录不适合进入正式 spec 的小优化、小问题、小反馈。

```markdown
# Backlog

## Small Fixes

### fix-001: 优化风险解释文案

Status: todo
Source: manual acceptance
Related Roadmap Item: item-001
Impact: low
Suggested Handling: surgery
```

---

### 3.6.3 decision-log.md

用于记录重要设计决策，避免 session 切换后丢失上下文。

```markdown
# Decision Log

## DEC-001: 使用 workflow core + adapter 架构

Date: 2026-xx-xx

### Context

需要让工作流在 Claude Code、Codex CLI、OpenCode 之间迁移。

### Decision

采用三层架构：

- Workflow Core
- Capability Contract
- CLI Adapter

### Consequences

核心逻辑不绑定单一 CLI，但初期实现成本会略高。
```

---

### 3.6.4 pitfalls.md

用于记录 AI 开发中反复出现的问题。

```markdown
# Pitfalls

## PIT-001: Propose 阶段误写代码

### Symptom

只要求生成方案，但 AI 直接开始修改代码。

### Prevention

- plan-only 模式下禁止 edit/write/shell side effects
- propose runbook 中明确禁止改代码
- adapter 层增加 guard
```

---

### 3.6.5 eval-cases.jsonl

用于沉淀长期 eval 数据。

```jsonl
{"id":"case-001","source":"manual_acceptance","input":"某合同条款...","expected":"应识别为付款风险","tags":["contract-review","payment-risk"]}
```

---

### 3.6.6 memory-index.md

用于记录长期项目记忆。

```markdown
# Memory Index

## Project Summary

本项目是合同条款风险审查系统，核心目标是稳定识别合同风险并生成解释和修改建议。

## Current Architecture

- Workflow Core 管理稳定流程
- Adapter 适配不同 AI CLI
- Eval Core 管理回归验证

## Current Baseline

Last Sync Commit: abc1234
Last Sync Date: 2026-xx-xx
```

---

## 3.7 核心工作流设计

### 3.7.1 Propose 流程

目标：只做方案设计，不改代码。

```text
User Request
  ↓
Read project context
  ↓
Clarify scope
  ↓
Update proposal / design / tasks
  ↓
Validate no code changes
  ↓
Wait for apply
```

规则：

* 不允许修改业务代码
* 不允许执行 destructive shell command
* 必须输出 proposal / design / tasks
* 必须标记风险和 trade-off
* 如果发现小优化，进入 backlog
* 如果影响 roadmap，更新 roadmap

---

### 3.7.2 Apply 流程

目标：按已确认方案执行实现。

```text
Load approved proposal
  ↓
Load tasks
  ↓
Execute task one by one
  ↓
Run tests
  ↓
Update task status
  ↓
Update roadmap / backlog
  ↓
Generate handoff
```

规则：

* 必须基于已确认的 proposal / tasks
* 每完成一个 task，需要更新状态
* 如果发现 scope change，写入 decision-log
* 如果发现新问题，进入 backlog
* 如果出现回归风险，补充 eval case

---

### 3.7.3 Surgery 流程

目标：处理小范围修复，避免 OpenSpec 过重。

适用场景：

* 小 bugfix
* 文案调整
* 轻量重构
* 局部优化
* 不需要完整 proposal 的改动

规则：

* 必须限制 scope
* 必须记录到 backlog
* 必须说明影响范围
* 必须运行最小验证
* 不允许扩大为大范围重构

---

### 3.7.4 Eval Loop 流程

目标：沉淀模型稳定性资产。

```text
Collect case
  ↓
Confirm expected output
  ↓
Add to golden dataset
  ↓
Run eval
  ↓
Analyze failure
  ↓
Fix prompt / rule / code / data
  ↓
Run regression
```

规则：

* 失败 case 不能只修 prompt，要先判断问题来源
* 问题来源可能是：

  * prompt 不清楚
  * schema 不稳定
  * taxonomy 缺失
  * 模型能力不足
  * test case 不合理
  * expected output 错误
* 人工确认后的 case 才能进入 golden dataset
* 模型升级前后必须跑关键 eval

---

### 3.7.5 Memory Sync 流程

目标：解决长项目上下文丢失问题。

触发条件：

* session 结束
* 重要文件变更
* roadmap 状态变化
* task 完成
* commit 前
* 用户手动触发

同步内容：

* 当前项目状态
* 已完成任务
* 重要设计决策
* 新增 pitfalls
* 新增 eval cases
* 当前 roadmap 状态
* 当前 commit baseline

---

## 3.8 三款 CLI 的适配策略

### 3.8.1 Claude Code Adapter

重点利用：

* `CLAUDE.md`
* hooks
* permissions
* skills
* subagents

适合：

* lifecycle hook
* memory sync
* tool call guard
* permission control
* skill 化 runbook

示例映射：

| Contract              | Claude Code          |
| --------------------- | -------------------- |
| `project_instruction` | `CLAUDE.md`          |
| `on_stop`             | `Stop hook`          |
| `before_tool_use`     | `PreToolUse hook`    |
| `after_tool_use`      | `PostToolUse hook`   |
| `runbook`             | skill                |
| `plan_only`           | prompt + permissions |

---

### 3.8.2 Codex CLI Adapter

重点利用：

* `AGENTS.md`
* hooks
* sandbox
* approval
* config

适合：

* 标准化项目指令
* memory sync
* approval guard
* sandbox profile
* command hook

示例映射：

| Contract              | Codex CLI                   |
| --------------------- | --------------------------- |
| `project_instruction` | `AGENTS.md`                 |
| `on_stop`             | `Stop hook`                 |
| `before_tool_use`     | `PreToolUse hook`           |
| `permission_request`  | approval                    |
| `plan_only`           | sandbox + approval + prompt |
| `runbook`             | prompt / AGENTS.md section  |

---

### 3.8.3 OpenCode Adapter

重点利用：

* `opencode.jsonc`
* Plan / Build agents
* commands
* plugins
* instructions
* MCP config

适合：

* 多模型工作流
* 自研 workflow plugin
* commands 化 runbook
* project-level instructions
* skill-router / tool-router 扩展

示例映射：

| Contract              | OpenCode                  |
| --------------------- | ------------------------- |
| `project_instruction` | instructions config       |
| `plan_only`           | Plan agent                |
| `apply_changes`       | Build agent               |
| `runbook`             | command                   |
| `on_stop`             | plugin event / command    |
| `tool_router`         | plugin / instructions     |
| `memory_sync`         | plugin / command / script |

---

## 3.9 第一阶段 MVP 建议

不要一开始就实现完整 Workflow SDK。建议先实现最小可用版本。

### MVP 范围

```text
MVP = Workflow Core + OpenCode Adapter + 可迁移 Contract 雏形
```

优先支持：

| 能力                    | 优先级 |
| --------------------- | --- |
| roadmap.md            | P0  |
| backlog.md            | P0  |
| decision-log.md       | P0  |
| propose runbook       | P0  |
| apply runbook         | P0  |
| surgery runbook       | P0  |
| memory-index.md       | P1  |
| eval-cases.jsonl      | P1  |
| OpenCode commands     | P0  |
| OpenCode instructions | P0  |
| OpenCode plugin       | P1  |
| Claude Adapter        | P2  |
| Codex Adapter         | P2  |

---

### MVP 目录

```text
.ai-workflow/
  core/
    lifecycle.md
    principles.md
    safety.md

  contracts/
    capabilities.yaml

  runbooks/
    propose.md
    apply.md
    surgery.md
    memory-sync.md

  artifacts/
    roadmap.md
    backlog.md
    decision-log.md
    pitfalls.md
    memory-index.md

  scripts/
    validate-roadmap.ts
    validate-tasks.ts
    sync-memory.ts

  adapters/
    opencode/
      opencode.jsonc
      commands/
        propose.md
        apply.md
        surgery.md
        memory-sync.md
```

---

## 3.10 后续演进路线

### Phase 1：OpenCode 可用

目标：先服务我当前主力开发环境。

完成：

* `.ai-workflow` 目录结构
* core runbooks
* roadmap / backlog / decision-log
* OpenCode commands
* OpenCode instructions
* 基础校验脚本

---

### Phase 2：强化治理能力

目标：解决 AI 开发过程中的常见失控点。

完成：

* plan-only guard
* task status checker
* roadmap drift checker
* decision-log checker
* memory sync
* handoff 生成
* surgery scope guard

---

### Phase 3：Eval 集成

目标：解决模型升级、模型切换后的表现漂移问题。

完成：

* eval case collection
* golden dataset
* promptfoo 或自定义 eval runner
* failure analysis runbook
* regression report

---

### Phase 4：Claude Code Adapter

目标：将当前工作流迁移到 Claude Code。

完成：

* 生成 `CLAUDE.md`
* 生成 hooks 配置
* 生成 skills
* 映射 permissions
* 验证 propose / apply / memory sync

---

### Phase 5：Codex CLI Adapter

目标：将当前工作流迁移到 Codex CLI。

完成：

* 生成 `AGENTS.md`
* 生成 hooks 配置
* 生成 sandbox / approval 配置
* 验证 propose / apply / memory sync

---

### Phase 6：Workflow SDK 化

目标：从项目内 workflow 升级为可复用工具。

理想命令：

```bash
workflow init
workflow adapt opencode
workflow adapt claude-code
workflow adapt codex
workflow validate
workflow sync-memory
workflow roadmap next
workflow eval collect
workflow eval run
```

---

## 4. 关键设计原则

### 4.1 Core 不知道 CLI

Core 中不能出现：

* Claude Code hook
* Codex hook
* OpenCode plugin
* `CLAUDE.md`
* `AGENTS.md`
* `opencode.jsonc`

Core 只描述工作流语义。

---

### 4.2 Adapter 不承载业务逻辑

Adapter 只负责映射，不负责实现核心状态机。

错误：

```text
OpenCode plugin 内部实现完整 roadmap 管理逻辑。
```

正确：

```text
OpenCode plugin 调用 core/scripts/update-roadmap.ts。
```

---

### 4.3 Runbook 是跨 CLI 的最小可迁移单元

不要一开始就写成 Claude skill 或 OpenCode command。

应该先写成：

```text
runbooks/propose.md
runbooks/apply.md
runbooks/surgery.md
runbooks/eval-loop.md
runbooks/memory-sync.md
```

然后由 Adapter 转换成：

| Runbook          | Claude Code                 | Codex               | OpenCode         |
| ---------------- | --------------------------- | ------------------- | ---------------- |
| `propose.md`     | skill / `CLAUDE.md` section | `AGENTS.md` section | command          |
| `apply.md`       | skill                       | prompt / command    | command          |
| `memory-sync.md` | hook + script               | hook + script       | plugin / command |
| `surgery.md`     | skill                       | prompt              | command          |

---

### 4.4 所有关键状态必须落盘

不要依赖模型记忆。

必须落盘的内容：

* roadmap
* backlog
* tasks
* decision log
* pitfalls
* eval cases
* memory index
* handoff

---

### 4.5 权限边界必须显式

至少定义以下模式：

| 模式            | 是否可写代码       | 是否可执行命令 | 用途                   |
| ------------- | ------------ | ------- | -------------------- |
| `plan-only`   | 否            | 只读命令    | brainstorm / propose |
| `review-only` | 否            | 只读命令    | review / verify      |
| `apply`       | 是            | 是       | 实现                   |
| `surgery`     | 是，但 scope 受限 | 是       | 小修复                  |
| `danger`      | 是            | 是       | 高风险操作，需要确认           |

---

## 5. 最终结论

本项目不应该做成某个 CLI 的单一 skill、hook 或 plugin，而应该做成一套 **portable AI workflow framework**。

推荐架构是：

```text
Workflow Core
  负责稳定工作流语义、状态机、文档结构、规则

Capability Contract
  负责定义抽象事件、权限、artifact、执行能力

CLI Adapter
  负责映射到 Claude Code、Codex CLI、OpenCode
```

最终目标是：

```text
一套核心工作流，多套 CLI 适配。
```

这样可以避免被某个 CLI 锁定，同时保留在不同工具之间迁移和复用的能力。

第一阶段建议不要追求完整跨 CLI，而是先完成：

```text
Workflow Core + OpenCode Adapter + Contract 雏形
```

等 OpenCode 环境跑通后，再逐步增加 Claude Code Adapter 和 Codex CLI Adapter。
