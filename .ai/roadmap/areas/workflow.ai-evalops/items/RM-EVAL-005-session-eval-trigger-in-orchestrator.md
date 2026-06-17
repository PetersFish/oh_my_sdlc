---
id: RM-EVAL-005
title: "Session Eval 触发器接入 sdlc-orchestrator"
status: idea
stage: v2
priority: p1
order: 50
depends_on:
  - RM-EVAL-004
openspec_change: null
created_at: 2026-06-16
started_at: null
completed_at: null
---

# Goal

让 Session Eval 不再只是 `sdlc-evalops` 文档里的概念，而是在 SDLC 流程中由 `sdlc-orchestrator` 明确触发，尤其当 AI 行为变更和用户纠错发生时。

# Scope

## In

- 在 `sdlc-orchestrator` 中增加 Session Eval 触发逻辑。
- 当任务涉及 AI behavior target 且出现用户纠错、输出偏差、eval 失败、verify 偏差时，触发 `sdlc-evalops` 的 capture-regression / session eval 流程。
- 明确 Session Eval 作用：捕获 inbox case、映射 coverage、提示 triage，不替代 Promptfoo golden eval。
- 在 orchestrator 流程中增加检查点：implementation 后、verify 前、eval 失败后。
- 保持用户确认门槛：不能自动写 golden，只能建议 capture；写 inbox 也需确认。

## Out

- 不在此阶段做 Promptfoo 性能优化。
- 不做自动 case promotion 到 golden。
- 不做无用户确认的自动写入。
- 不让 Session Eval 变成最终门禁。

# Acceptance Criteria

- `sdlc-orchestrator` 在 AI behavior target 改动后提示是否需要 Session Eval capture。
- 用户指出 AI 输出不符合预期时，建议将该场景 capture 为 regression case。
- Eval 失败时，提示是否 capture 新失败模式，而不是直接修代码。
- Session Eval 产物进入 inbox，并触发 triage。
- 最终完成声明仍要求 Promptfoo golden eval 或明确说明 blocked runner dependency。
- 文档明确：Session Eval = 发现/积累案例；Promptfoo Eval = 回归验证/门禁。

# Promotion Notes

适合在 RM-EVAL-004（Promptfoo 加速）完成后再推进。加速能力先解决"跑 eval 太慢"的核心痛点，再补流程触发，避免触发更多慢 eval 造成体验变差。

# Completion Notes

