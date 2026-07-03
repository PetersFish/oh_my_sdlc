# Dev-Orchestrator / Roadmap-Agent 协作设计

## Context

`roadmap-agent` 已加入 dev-orchestrator 工作流体系，但目前仅覆盖生命周期 hook（ready/apply-start/done），不覆盖 roadmap item review。用户期望 dev-orchestrator 在收到 "review roadmap item" 请求时，将任务派发给 roadmap-agent 完成评审，形成完整的主子 agent 协作闭环。

同时，`openspec_*` 命名在 workflow runtime 中暴露了实现细节，需要统一收敛到 `spec_*` 领域名。

## Goals / Non-Goals

**Goals:**

- roadmap-agent 成为 roadmap review 的执行者，dev-orchestrator 作为路由器
- review 通过后 item 标记为 `ready`，但不创建 spec artifacts
- 用户明确选择后才进入 `create_change` 阶段 dispatch plan-agent 创建 spec
- 统一将 `openspec_*` 领域名收敛为 `spec_*`，隐藏 OpenSpec 实现
- Run 创建时机按需：首次治理动作时创建，不批量创建

**Non-Goals:**

- 不重写 workflow.py 为 class-based state machine
- 不改变 roadmap 状态机的核心状态集合（idea/ready/active/done/cancelled）
- 不引入新的 provider/backend

## Decisions

### Decision 1: `ready` 语义调整

**原定义:** review 通过 + OpenSpec artifacts 已创建 → `ready`

**新定义:** review 通过 → `ready`

是否已创建 spec 由 `spec_change` 字段判断：

- `ready + spec_change: null` — 已评审通过，待创建 spec
- `ready + spec_change: <id>` — spec 已创建，待实现
- `active + spec_change: <id>` — 实现中

**Rationale:** 当时没有 agent 体系，状态不好控制。现在有了 roadmap-agent 作为 review 执行者，可以把 review 和 spec creation 解耦。

### Decision 2: `openspec_*` → `spec_*` 命名收敛

所有对外暴露的领域名统一为 `spec_*`：

- roadmap item frontmatter: `openspec_change` → `spec_change`
- workflow.py context/loader/evidence: `openspec_*` → `spec_*`
- hook 名称: `roadmap_status_ready_if_linked` → `roadmap_spec_link_if_ready`
- OpenSpec 只作为当前 provider/backend 名称，不暴露到领域模型

**Rationale:** 领域名不应绑定具体实现。未来 spec provider 可能不是 OpenSpec。

### Decision 3: Hook 语义变更

`roadmap_status_ready_if_linked` → `roadmap_spec_link_if_ready`

新语义：

- 只在 item 已 `ready` 时允许绑定 `spec_change`
- 如果 item 不是 `ready`，阻塞并要求先 review
- 如果 `spec_change` 已存在且匹配，幂等成功
- 不负责把 item 改成 `ready`（由 roadmap-agent review 负责）

### Decision 4: `review_roadmap` phase 由 roadmap-agent 执行

- `sdlc-main.yaml`: `review_roadmap` phase 的 allowed_workers 改为 `dev-orchestrator`（dispatch roadmap-agent）
- `dev-orchestrator.md`: 新增 `review_roadmap → roadmap-agent` 映射
- `roadmap-agent.md`: 新增 `roadmap_review` 输入输出契约

### Decision 5: Review 通过后不自动创建 spec

- `roadmap-agent` review 通过后只标记 `ready` + 写 changelog
- `dev-orchestrator` 问用户："创建 spec 还是 review 下一个 item？"
- 用户明确选择创建 spec 后，才进入 `create_change` dispatch plan-agent
- plan-agent 创建 spec artifacts 后绑定 `spec_change`

### Decision 6: Run 创建时机


| 场景                  | 是否创建 run                  |
| ------------------- | ------------------------- |
| 创建 roadmap item（草稿） | 否                         |
| 首次 `roadmap_review` | 是（`roadmap_item` subject） |
| 用户选择创建 spec         | 是（创建 `spec_change` run）   |
| `apply_change`      | 复用已有 run                  |
| 一个需求拆成多个 item       | 按需，不批量创建                  |


## State Model

```
idea ──(review passed)──→ ready ──(spec created)──→ ready ──(apply start)──→ active ──→ done
  │                        │                          │
  └────────────────────────┴──────────────────────────┴──→ cancelled
```


| 状态          | 含义               | spec_change   |
| ----------- | ---------------- | ------------- |
| `idea`      | 未评审、评审未通过、或有开放问题 | null          |
| `ready`     | review 已通过       | null 或 `<id>` |
| `active`    | 实现已开始            | `<id>`        |
| `done`      | 完成               | `<id>`        |
| `cancelled` | 取消保留历史           | null 或 `<id>` |


## Collaboration Flow

```
用户: review roadmap item RM-xxx
  │
  ▼
dev-orchestrator
  ├── 确认/resume roadmap_item run (phase=review_roadmap)
  ├── before-dispatch → roadmap-agent
  └── dispatch roadmap-agent
        │
        ▼
      roadmap-agent
        ├── 加载 sdlc-roadmap skill
        ├── 读取 RM-xxx
        ├── LLM review checklist
        │
        ├── 有开放问题?
        │     └── YES → item 保持 idea, 返回 questions → 用户补充 → redispatch
        │
        └── review 通过?
              └── YES → 标记 ready, 写 changelog, 返回 success
                        │
                        ▼
                      dev-orchestrator
                        ├── after-dispatch
                        └── 问用户: 创建 spec / review 下一个 item
                              │
                              ├── 创建 spec → create_change → dispatch plan-agent
                              │     └── plan-agent 创建 spec artifacts → 绑定 spec_change
                              │
                              └── review 下一个 → roadmap-agent 找下一个 idea item → 继续 review
```

## Roadmap-Agent Contract (review_roadmap)

### Input

```json
{
  "workflow_run_id": "<run_id>",
  "phase": "review_roadmap",
  "action": "roadmap_review",
  "context": {
    "roadmap_item_id": "RM-xxx"
  }
}
```

### Output — Review Passed

```json
{
  "agent": "roadmap-agent",
  "status": "success",
  "phase": "review_roadmap",
  "slice_id": "default",
  "flow_type": "spec-flow",
  "evidence": {
    "roadmap_review_decision": "passed",
    "roadmap_item_id": "RM-xxx",
    "item_status": "ready",
    "transition_applied": true,
    "open_questions": [],
    "recommended_dispatch_target": "ask_user"
  },
  "artifacts": {
    "handoff_path": ".ai/workflows/runs/active/<run_id>/handoffs/default/roadmap-agent.md"
  },
  "blockers": [],
  "recommended_next_action": "ask_user_next_step"
}
```

### Output — Open Questions

```json
{
  "agent": "roadmap-agent",
  "status": "blocked",
  "phase": "review_roadmap",
  "slice_id": "default",
  "flow_type": "spec-flow",
  "evidence": {
    "roadmap_review_decision": "needs_discussion",
    "roadmap_item_id": "RM-xxx",
    "item_status": "idea",
    "transition_applied": false,
    "open_questions": [
      {"id": "q1", "question": "Acceptance criterion X is ambiguous. What does Y mean?", "reason": "..."}
    ]
  },
  "artifacts": {},
  "blockers": [
    {"reason": "open_review_questions", "message": "Review found open questions requiring user input."}
  ],
  "recommended_next_action": "ask_user_for_clarification"
}
```

## Affected Files


| 文件                                          | 变更类型 | 说明                                                   |
| ------------------------------------------- | ---- | ---------------------------------------------------- |
| `agents/roadmap-agent.md`                   | 修改   | 新增 `roadmap_review` 输入输出契约                           |
| `agents/dev-orchestrator.md`                | 修改   | 新增 `review_roadmap → roadmap-agent` 映射               |
| `.ai/workflows/definitions/sdlc-main.yaml`  | 修改   | `review_roadmap` allowed_workers 改为 dev-orchestrator |
| `.ai/workflows/scripts/workflow.py`         | 修改   | `openspec_*` → `spec_*`；hook 语义调整                    |
| `skills/sdlc-roadmap/SKILL.md`              | 修改   | review 语义调整：通过后只标记 ready，不创建 spec                    |
| `tests/test_workflow.py`                    | 修改   | 更新 `openspec_*` → `spec_*` 引用                        |
| `tests/test_wrapper_contracts.py`           | 修改   | 新增 roadmap-agent review 契约测试                         |
| 分发副本 (`.opencode/`, `.claude/`, `.cursor/`) | 同步   | 随 canonical 变更同步                                     |


## Risks / Trade-offs

**[Breaking change: `openspec_*` → `spec_*`]** → 一次性迁移，需要更新所有测试、模板、分发副本。产品未发布，可接受。

**[`ready` 语义变更]** → 现有 `ready` item 如果没有 `spec_change`，语义从"spec 已创建"变为"review 已通过"。需要检查现有数据并迁移。

**[Review 不自动创建 spec]** → 增加一步用户交互，但降低误操作风险，符合当前 agent 架构设计。
