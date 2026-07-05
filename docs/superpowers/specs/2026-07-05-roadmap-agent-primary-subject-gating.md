# Roadmap-Agent Primary Subject Gating

## Context

当前 `dev-orchestrator` workflow 在 `primary_subject.type == "spec_change"` 时，也会无差别执行 roadmap lifecycle hooks，从而 dispatch `roadmap-agent`。

这导致没有 roadmap 关联的普通 spec/lightweight workflow 也会进入 roadmap-agent，最终只返回 `no_linked_item`，浪费 token 和时间。

run.json 已经包含稳定字段：

```json
{
  "primary_subject": {
    "type": "spec_change",
    "id": "..."
  }
}
```

因此不需要引入新的复杂 roadmap activation model。可以直接使用 `primary_subject.type` 作为 roadmap-agent 是否启用的判定源。

## Goal

只有当当前 workflow run 的 `primary_subject.type == "roadmap_item"` 时，才允许激活 `roadmap-agent`。

当 `primary_subject.type != "roadmap_item"` 时：

- 不把 roadmap hooks 加入 `pending_hooks`
- 不 dispatch `roadmap-agent`
- 不让 roadmap-agent 执行 `no_linked_item` 空转逻辑

## Non-Goals

- 不新增 run.json 顶层 `roadmap` 字段
- 不引入 roadmap activation model
- 不改变 roadmap item 状态机
- 不改变 `spec_change` / `roadmap_item` subject 类型
- 不修改 OpenSpec / Superpowers flow 选择逻辑
- 不重写 workflow.py
- 不移除 roadmap-agent

## Rule

```text
roadmap-agent is enabled if and only if:

primary_subject.type == "roadmap_item"
```

## Runtime Behavior

### Case 1: primary_subject.type == spec_change

Input run:

```json
{
  "primary_subject": {
    "type": "spec_change",
    "id": "some-change"
  }
}
```

Expected behavior:

- `roadmap_spec_link_if_ready` is not enqueued
- `roadmap_apply_start_if_ready` is not enqueued
- `roadmap_done_if_relevant` is not enqueued
- `roadmap-agent` cannot be dispatched
- normal lifecycle continues through plan-agent / implement-agent / review-agent / finish-agent
- `memory_sync` remains unaffected

### Case 2: primary_subject.type == roadmap_item

Input run:

```json
{
  "primary_subject": {
    "type": "roadmap_item",
    "id": "RM-001"
  }
}
```

Expected behavior:

- roadmap lifecycle hooks may be enqueued
- `review_roadmap` can dispatch roadmap-agent
- roadmap-agent can update roadmap item state
- roadmap-governed workflow remains supported

## Design

Add helper in `.ai/workflows/scripts/workflow.py`:

```python
def _roadmap_agent_enabled(state):
    return state.get("primary_subject", {}).get("type") == "roadmap_item"
```

Add helper:

```python
def _is_roadmap_hook(hook):
    return str(hook).startswith("roadmap_")
```

When adding phase post-hooks to `pending_hooks`, filter roadmap hooks:

```python
for hook in phase_def.get("post_hooks", []):
    if _is_roadmap_hook(hook) and not _roadmap_agent_enabled(state):
        continue
    ...
```

In `cmd_before_dispatch`, block roadmap-agent when disabled:

```python
if canonical_agent == "roadmap-agent" and not _roadmap_agent_enabled(state):
    blocker_reasons.append({
        "reason": "roadmap_not_enabled",
        "message": "roadmap-agent is disabled because primary_subject.type is not roadmap_item",
        "recommended_action": "continue the non-roadmap workflow path without dispatching roadmap-agent",
    })
```

## Acceptance Criteria

1. For `primary_subject.type == "spec_change"`, roadmap hooks are not added to `pending_hooks`.
2. For `primary_subject.type == "spec_change"`, `before-dispatch --agent roadmap-agent` returns blocked.
3. For `primary_subject.type == "roadmap_item"`, `before-dispatch --agent roadmap-agent` remains allowed when the phase mapping allows it.
4. `review_roadmap` still works for roadmap item runs.
5. `memory_sync` is not affected.
6. Existing non-roadmap workflow tests still pass.
7. Existing roadmap workflow tests still pass.
8. No new run.json top-level schema field is introduced.

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/scripts/workflow.py` | Add primary-subject based roadmap-agent gate and roadmap hook filtering |
| `tests/test_workflow.py` | Add behavior tests for disabled/enabled roadmap-agent routing |
| `agents/dev-orchestrator.md` | Document that roadmap-agent is dispatched only for `primary_subject.type == "roadmap_item"` |
| distributed agent copies | Sync dev-orchestrator prompt if needed |
| workflow.py template copies | Sync runtime template copies if project requires template distribution |
