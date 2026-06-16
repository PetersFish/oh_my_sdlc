# OpenCode SDLC 落地指南

核心判断：

> 你现在要做的不是“再加 skills”，而是把已有 skills 组织成一套 **Workflow Engine（工作流引擎）**。

---

## 1. 你的目标架构

```text
OpenCode
↓
Workflow Engine / Orchestrator
↓
Task Classification
↓
Phase-based SDLC
↓
Specialized Agents / Skills
```

对应你的组件：

```text
OpenSpec      → Specification
Roadmap       → Planning
Superpowers   → Implementation + TDD
Eval          → Semantic Evaluation
Memory        → Long-term Knowledge
Orchestrator  → Workflow Engine
```

---

## 2. 核心原则

第一条：

> **Agent 不管理 Workflow，Workflow 管理 Agent。**

第二条：

> **Orchestrator 不应该越来越聪明，而应该越来越固执。**

第三条：

> **每个阶段必须有输入、输出、退出条件。**

---

## 3. 推荐 SDLC 阶段

```text
0. Intake              需求接收
1. Classification      任务分类
2. Specification       规格定义
3. Planning            任务规划
4. Implementation      编码实现
5. Deterministic Gate  确定性验证
6. Semantic Eval       语义验证
7. Memory Update       记忆更新
8. Done                完成
```

---

## 4. 阶段与技能映射

| 阶段                 | 负责人                 | 产物                                            |
| ------------------ | ------------------- | --------------------------------------------- |
| Intake             | Orchestrator        | 用户意图摘要                                        |
| Classification     | Orchestrator        | tiny / bugfix / feature / refactor / research |
| Specification      | OpenSpec            | spec.md                                       |
| Planning           | Roadmap             | tasks.md / roadmap patch                      |
| Implementation     | Superpowers TDD     | code changes                                  |
| Deterministic Gate | Superpowers / shell | pytest、lint、typecheck 结果                      |
| Semantic Eval      | Eval                | APPROVE / REVISE                              |
| Memory Update      | Memory              | lessons、decisions、project facts               |

---

## 5. 不同任务走不同流程

### Tiny Task

```text
Intake
↓
Implementation
↓
Done
```

例如改错字、改注释、小配置。

### Bugfix

```text
Intake
↓
Reproduce
↓
Implementation
↓
Deterministic Gate
↓
Semantic Eval
↓
Memory Update
```

### Feature

```text
Intake
↓
Specification
↓
Planning
↓
Implementation
↓
Deterministic Gate
↓
Semantic Eval
↓
Memory Update
```

### Refactor

```text
Intake
↓
Scope Definition
↓
Planning
↓
Implementation
↓
Deterministic Gate
↓
Semantic Eval
↓
Memory Update
```

### Research / Design

```text
Intake
↓
Context Routing
↓
Research
↓
Decision Record
↓
Memory Update
```

---

## 6. 验证层要拆成两层

你现在的设计是对的：

```text
Superpowers TDD
=
Deterministic Verification
```

负责：

```text
pytest
lint
typecheck
build
```

而你的 Eval 应该是：

```text
Semantic Judge
```

负责：

```text
是否符合 spec
是否符合 roadmap
是否符合 memory
是否过度设计
是否有隐藏风险
```

完整验证链：

```text
Implementation
↓
Deterministic Gate
↓
Semantic Eval
↓
Done
```

金句：

> pytest 检查代码能不能跑；Eval 检查代码是不是实现了承诺。

---

## 7. Memory 的位置

Memory 不是普通阶段。

它是基础设施。

```text
Spec
Plan
Implement
Eval
  ↑
  │
Memory
```

但任务结束时必须有：

```text
Memory Update
```

写入：

```text
- 新决策
- 新约定
- 踩坑记录
- 测试命令
- 架构事实
- 未来 TODO
```

---

## 8. Context Routing 要做什么

不要把所有 memory、spec、roadmap 都塞给模型。

要做：

```text
User Request
↓
Context Router
↓
Relevant Memory
Relevant Spec
Relevant Code
Relevant Roadmap
↓
Agent
```

原则：

> 不是上下文越多越好，而是越相关越好。

第一版可以手工规则化：

```text
auth task       → 加载 auth memory + auth spec
database task   → 加载 db memory + migration notes
frontend task   → 加载 UI rules + component notes
bugfix          → 加载 recent failures + related tests
```

---

## 9. Orchestrator 第一版怎么写

不要先写复杂代码。

先写一个 `.opencode/agents/team.md` 或 `orchestrator.md`。

它只做四件事：

```text
1. 分类任务
2. 选择 workflow
3. 调用对应 agent / skill
4. 检查 phase output 和 exit criteria
```

明确禁止：

```text
Orchestrator 不直接改代码
Orchestrator 不跳过验证
Orchestrator 不把所有上下文一次性加载
```

---

## 10. 建议目录结构

```text
.agent/
  workflows/
    tiny.yaml
    bugfix.yaml
    feature.yaml
    refactor.yaml
    research.yaml

  runs/
    current.json

  plans/
    <task-name>.md

  notepads/
    <task-name>/
      learnings.md
      decisions.md
      deterministic.md
      semantic_eval.md
      problems.md
```

最小状态文件：

```json
{
  "active_workflow": "feature",
  "current_phase": "implementation",
  "completed_phases": ["intake", "specification", "planning"],
  "active_plan": ".agent/plans/auth-login.md",
  "status": "running"
}
```

---

## 11. 参考 OMO 的地方

OMO 最值得借鉴的不是 agent 名字，而是：

```text
Plan file
State file
Notepads
Worker delegation
Resume mode
Verification loop
```

你可以对应实现为：

```text
.omo/plans        → .agent/plans
.omo/boulder.json → .agent/runs/current.json
.omo/notepads     → .agent/notepads
Atlas             → 你的 Workflow Executor
Prometheus        → OpenSpec + Roadmap
Worker agents     → Superpowers / subagents
```

---

## 12. 最小可落地版本

先只实现一个 Feature Workflow：

```text
Intake
↓
OpenSpec
↓
Roadmap
↓
Superpowers TDD
↓
Deterministic Gate
↓
Eval
↓
Memory Update
```

成功标准：

```text
每次任务都有 spec
每次实现都有测试结果
每次完成都有 semantic eval
每次结束都有 memory update
失败后能回到上一阶段继续
```

---

## 13. 最终设计哲学

你的 OpenCode SDLC 不应该是：

```text
很多 skills 平铺
```

而应该是：

```text
Workflow Engine
调度
Skills
```

最重要的升级路径：

```text
Skill Collection
↓
Agent System
↓
Phase-based Workflow
↓
Stateful Workflow Engine
↓
Parallel Team Mode
```

你现在最该做的第一步：

> **定义你的任务阶段、阶段产物、退出条件。**

这一步完成，你的系统就从“AI 能力合集”进入了“AI 软件工程流程”。
