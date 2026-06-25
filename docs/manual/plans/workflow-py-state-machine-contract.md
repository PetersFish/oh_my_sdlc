# workflow.py 最小状态机契约优化方案

## 背景

当前 `workflow.py` 已具备基本的 guarded transitions：`advance` 阻止 blocked/phase 未完成/pending hook/required gate 等情况。但 `agent-backed-lifecycle-wrapper-architecture` 设计要求 state machine 还需要支撑：

- `flow_type` 显式写入 run state
- Agent 产出 normalized evidence 后，通过 `record-evidence` -> `complete-phase` -> `advance` 完成状态转移
- Agent 失败时通过 structured blocker 写入并阻塞
- Exit criteria validation 不仅检查字符串，还需关联 evidence 字段
- dev-orchestrator 可以分派并行 work packages，各包产出 per-package evidence

以下是不动现有架构的前提下，最小增量设计。

---

## 设计约束

- `workflow.py` 仍是唯一状态机 owner
- 不引入新的顶层命令（暂不新增 cmd_dev_orchestrator 之类）
- 所有 agent/wrapper 通过已有命令与 state machine 交互
- 改动限于 `RUN_STATE_KEYS`、`start`/`ensure-run` 输入、evidence 校验、block type 扩展

---

## 增量设计

### 1. 新增 `flow_type` 字段

**改动点**: `RUN_STATE_KEYS` 增加 `"flow_type"`。

```python
RUN_STATE_KEYS = {
    "version", "run_id", "workflow", "status", "current_phase",
    "primary_subject", "context", "phase_readiness", "pending_hooks",
    "completed_hooks", "completed_phases", "gates", "evidence", "block",
    "flow_type",  # NEW
    "updated_at",
}
```

**行为**:
- `start` 和 `_create_workflow_run` 接受可选 `--flow-type` CLI 参数。
- 如果用户不传，默认 `spec-flow` 保持向后兼容。
- `validate_run_state` 校验 `flow_type` 必须是 `"spec-flow"` 或 `"lightweight-flow"`。
- Agent 读取 `flow_type` 做路由决策，不自行推断。

### 2. `--flow-type` CLI 参数

`cmd_start` 和 `cmd_ensure_run` 接受 `--flow-type`:

```
python3 workflow.py start --subject-type openspec_change --subject-id my-change --flow-type spec-flow
```

缺省值策略：`openspec_change` 类型默认 `spec-flow`；
`roadmap_item` 类型默认 `spec-flow`；
未来新增 subject type 可显式指定。

### 3. Evidence contract validation

`cmd_complete_phase` 当前只检查 `--exit-criteria-satisfied` 传入的逗号分隔字符串是否覆盖 `phase_def.exit_criteria`。这不能确保 evidence 真的符合要求。

**改进**: 增加一个 `evidence_keys` 可选 param，允许 phase def 声明需要哪些 evidence keys 存在且不为空：

```yaml
phases:
  apply_change:
    exit_criteria:
      - tasks_complete
      - tdd_passed
    evidence_keys:             # NEW
      - implement_artifacts    # 必须有值
      - test_results           # 必须有值
```

`_check_exit_criteria` 接收 phase def，额外检查 `evidence_keys` 列表中的 key 是否都在 `state["evidence"]` 中存在且 value 不为 `None`/`""`。任一缺失则 fail。

### 4. Agent blocker 扩展

当前 `block` 类型只有 `user_decision_required`、`worker_failed` 等。为了 agent 驱动的 blocker：

- 不新增 block type；复用 `worker_failed` 并附带 `block.meta = {"agent": "plan-agent", "phase": "plan", "flow_type": "spec-flow"}`。
- `dev-orchestrator` 如果检测到 agent 失败，调用：
  ```
  workflow.py block --block-type worker_failed --message "plan-agent: missing flow_type" --next-allowed "resolve,record-evidence,block"
  ```

### 5. Agent dispatch handoff field

在 run state 的 `evidence` 中约定一个 agent dispatch 的标识 key：

```json
{
  "phase": "apply_change",
  "evidence": {
    "agent_phase": {
      "agent": "implement-agent",
      "flow_type": "spec-flow",
      "work_package": "implementation-phase-1",
      "started_at": "2026-06-25T00:00:00"
    }
  }
}
```

这不是 state machine 强制的，而是 convention（agent 写入 `record-evidence --key agent_phase --value '{...}'`），方便 workflow runner 知道当前由哪个 agent 在执行。

### 6. 并行 work packages 的 per-package evidence

`dev-orchestrator` 可以拆并行包，每个包完成时调用：
```
workflow.py record-evidence --key implement_package_1 --value '{"status":"done","files":["a.py","b.py"]}'
workflow.py record-evidence --key implement_package_2 --value '{"status":"done","files":["c.py"]}'
```

`phase_def.exit_criteria` 中的 `evidence_keys` 可以声明需要哪些 package evidence：
```yaml
evidence_keys:
  - implement_package_1
  - implement_package_2
```

集成验证（Step 4 of `dev-orchestrator`）完成后，才调用 `complete-phase`。

---

## 不改什么

- 不引入新顶层命令（如 `cmd_dev_orchestrator`）
- 不删除或重命名现有命令
- 不改变 `advance`/`resolve`/`block`/`done` 的核心 guard 逻辑
- 不要求 `sdlc-main.yaml` 现在就改掉 concrete workers（YAML 改动是后续独立的实现 task）

---

## 相关 spec 要求

| Spec Requirement | 本方案对应点 |
|---|---|
| `flow_type` is explicit state field | #1, #2 |
| Wrapper normalizes agent output into evidence | #3, #5 |
| Agent blocker returns structured blocker | #4 |
| Parallel packages have per-package evidence | #6 |
| Wrapper fail closed when evidence missing | #3 (evidence_keys validation) |

---

## 后续讨论点

1. `flow_type` 的默认推导规则：是否完全由 caller 指定，还是根据 subject type 自动推断？
2. `evidence_keys` 的粒度：是否需要 typed evidence（eg. `str` vs `dict` vs `list`）？
3. 是否需要在 phase YAML 中显式声明 agent name（直接替代 `allowed_workers`），还是让 `dev-orchestrator` 负责 agent selection？
4. 并行 packages 是否需要 `complete-phase` 支持 "partial completion"（部分包完成后先 record-evidence，等全部完成才 advance）还是保持当前“一 phase 一 complete”模型？
