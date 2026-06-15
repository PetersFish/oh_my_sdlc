这是我基于我们整段讨论整理的一份设计报告。我会尽量站在**Agent System Architect（智能体系统架构师）**的角度来写，而不是 OpenCode 用户的角度。

---

# 从 Skills 到 Workflow Engine

## —— 基于 OpenCode + OpenSpec + Memory + Eval 的 Agent 系统设计调研

---

# 电梯演讲

你现在已经不在解决：

> 「如何让 AI 更聪明」

而是在解决：

> 「如何组织多个 AI 能力协同工作」

这是两个完全不同的问题。

很多 Agent 项目是在堆能力（Capability）。

而你已经进入：

```text
Capability
    ↓
Workflow
        ↓
Orchestration
            ↓
System
```

阶段。

未来你的 Agent 系统竞争力，不会来自：

```text
新增多少 Skill
```

而来自：

```text
如何组织已有 Skill
```

---

# 一句话暴论

> Agent 系统最大的瓶颈从来不是模型能力，而是工作流熵增。

当系统只有一个 Agent：

```text
用户
 ↓
Agent
```

几乎没有管理成本。

---

当系统变成：

```text
Memory
Roadmap
OpenSpec
Eval
Superpowers
Custom Skills
```

问题就变成：

```text
谁先执行？

谁负责决策？

谁负责验收？

谁拥有最终解释权？
```

---

如果没有 Orchestration：

```text
能力越多
混乱越大
```

---

# 当前系统分析

你目前拥有：

```text
OpenCode

    ↓

Orchestrator

    ├─ OpenSpec
    ├─ Memory
    ├─ Eval
    ├─ Roadmap
    └─ Superpowers
```

这已经不是：

```text
Skill Collection
```

而是：

```text
Agent Workflow System
```

---

# 为什么 OMO 对你不是增量

对于普通用户：

OMO 提供：

```text
Planner
Reviewer
Researcher
Executor
```

属于能力补充。

---

对于你：

这些能力已经存在：

| OMO          | 你的系统         |
| ------------ | ------------ |
| Planner      | Roadmap      |
| Spec         | OpenSpec     |
| Reviewer     | Eval         |
| Memory       | Memory       |
| Team Manager | Orchestrator |

因此：

```text
安装OMO
≠
获得新能力
```

而是：

```text
研究OMO
=
获得新架构
```

---

# OMO 最值得学习的三个思想

## 1 Context Routing

### 核心观点

Agent 不应该看到全部信息。

Agent 应该只看到当前任务需要的信息。

---

错误模式：

```text
Memory
Roadmap
Spec
Docs
Codebase

全部塞给模型
```

---

正确模式：

```text
Task

↓

Router

↓

Relevant Context

↓

Agent
```

---

本质：

```text
选择信息
比增加信息更重要
```

---

## 2 Orchestration

### 核心观点

Agent 不应该决定下一步做什么。

Workflow 应该决定。

---

错误模式：

```text
Agent
  ↓
Think
  ↓
Act
  ↓
Think
  ↓
Act
```

---

正确模式：

```text
Phase

↓

Task

↓

Agent
```

---

即：

```text
当前阶段
决定
允许做什么
```

---

## 3 Verification Loop

### 核心观点

执行不等于完成。

---

传统模式：

```text
Plan
↓
Implement
↓
Done
```

---

高级模式：

```text
Plan
↓
Implement
↓
Evaluate

PASS ?
```

---

```text
PASS
 ↓
Done
```

---

```text
FAIL
 ↓
Repair
 ↓
Evaluate
```

---

你的 Eval Skill 应当长期保留。

---

# 一个关键发现

## Orchestrator 不应该是 Agent

这是我认为你未来最值得思考的。

目前你可能把 Orchestrator 理解成：

```text
一个超级Agent
```

---

但从 OMO 学到的东西是：

```text
Orchestrator
=
Workflow Engine
```

---

Agent：

```text
负责干活
```

---

Workflow：

```text
负责决定什么时候干活
```

---

这是本质区别。

---

# 推荐的新架构

## v1

当前：

```text
User

↓

Orchestrator

↓

Skills
```

---

## v2

建议：

```text
User

↓

Task Classifier

↓

Workflow Engine

↓

Skills
```

---

即：

```text
Request

↓

What task is this?

↓

What phase should run?

↓

What skill should execute?
```

---

# Phase First Architecture

这是最重要的升级。

---

# 推荐 Phase

```text
PHASE 0
Intake

PHASE 1
Specification

PHASE 2
Planning

PHASE 3
Execution

PHASE 4
Validation

PHASE 5
Memory Update

PHASE 6
Done
```

---

# 映射到现有系统

```text
Specification
    ↓
OpenSpec

Planning
    ↓
Roadmap

Execution
    ↓
Superpowers

Validation
    ↓
Eval

Memory Update
    ↓
Memory
```

---

# Memory 的正确位置

很多人会这样设计：

```text
Memory Agent
```

---

实际上：

```text
Memory
=
Infrastructure
```

更合理。

---

应该是：

```text
Spec
  ↑
  │

Plan
  ↑
  │

Execute
  ↑
  │

Eval
  ↑
  │

Memory
```

---

Memory 是跨阶段能力。

不是阶段本身。

---

# 推荐状态机

```text
Intake

↓

Spec

↓

Plan

↓

Execute

↓

Validate
```

---

验证结果：

```text
PASS
 ↓
Memory Update
 ↓
Done
```

---

或者：

```text
FAIL
 ↓
Execute
 ↓
Validate
```

形成闭环。

---

# 引入 Task Classification

所有任务不应该走同一个流程。

---

## Tiny Task

例如：

```text
改README

修复拼写

改注释
```

流程：

```text
Intake
↓
Execute
↓
Done
```

---

## Normal Task

例如：

```text
新增API
```

流程：

```text
Spec
↓
Plan
↓
Execute
↓
Validate
```

---

## Major Task

例如：

```text
重构认证系统
```

流程：

```text
Spec
↓
Plan
↓
Checkpoint
↓
Execute
↓
Validate
↓
Memory Update
```

---

# 下一阶段演化

当 Workflow 稳定后。

再考虑：

```text
Single Worker
```

升级：

```text
Multiple Workers
```

即：

```text
Orchestrator

↓

Planner

↓

┌─────────┐
│ WorkerA │
│ WorkerB │
│ WorkerC │
└─────────┘

↓

Eval
```

---

这才是真正意义上的 Team Mode。

---

# 长期路线图

## 第一阶段（现在）

明确：

```text
Phase
```

---

目标：

```text
Workflow可视化
```

---

## 第二阶段

明确：

```text
Phase Input
Phase Output
Phase Exit Criteria
```

---

目标：

```text
Workflow可验证
```

---

## 第三阶段

引入：

```text
Context Router
```

---

目标：

```text
Workflow可扩展
```

---

## 第四阶段

引入：

```text
Parallel Workers
```

---

目标：

```text
Workflow可并行
```

---

# 最终洞见

如果把 Agent 系统的发展分成四个时代：

```text
时代1
Prompt Engineering

时代2
Skills

时代3
Agent

时代4
Workflow Engine
```

大部分人还停留在：

```text
再加一个Skill
再加一个Agent
```

的阶段。

而从你的系统组成来看：

```text
OpenSpec
Roadmap
Memory
Eval
Orchestrator
```

你已经站在时代4的门口了。

未来最值得投入的方向，不是继续增加能力，而是建立一套明确的：

```text
Phase
State
Transition
Context Routing
Verification Loop
```

体系。

因为当能力越来越多时，系统的价值不再来自拥有多少能力，而来自能否让这些能力在正确的时间，以正确的顺序，被正确地调用。
