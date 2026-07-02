## MODIFIED Requirements

### Requirement: Roadmap promote 行为

promote 是将 roadmap item 转为 OpenSpec change 编排入口，不复制 OpenSpec 逻辑。For governed SDLC workflow runs, promotion and subsequent OpenSpec artifact creation SHALL leave the linked item in `ready`; the item SHALL become `active` only when implementation starts through the apply-start transition.

#### Scenario: promote 生成 promotion context
- **WHEN** 用户执行 `roadmap promote RM-001`
- **THEN** 读取 item 文件内容（Goal/Scope/Acceptance Criteria/Promotion Notes）
- **THEN** 生成 promotion context（摘要 item 的目标和范围）
- **THEN** 引导用户创建 OpenSpec change（调用 openspec-propose 或 openspec-new-change）
- **THEN** 将 item status 更新为 ready when OpenSpec artifacts are created for the governed run
- **THEN** 不设置 `started_at` until implementation starts
- **THEN** 不直接创建 proposal.md / design.md / tasks.md / spec.md

#### Scenario: promote 检查依赖
- **WHEN** 用户执行 `roadmap promote RM-002` 且 depends_on 指向未完成的 RM-001
- **THEN** 输出警告"依赖项 RM-001 尚未完成"
- **THEN** 仍允许 promotion 但提示风险

## ADDED Requirements

### Requirement: Governed Roadmap Lifecycle Transitions
The `sdlc-roadmap` worker SHALL support the roadmap item state mutations required by governed SDLC hooks for linked OpenSpec changes.

#### Scenario: Mark linked item ready after spec artifacts
- **WHEN** a governed OpenSpec change has completed provider-owned spec artifacts for one linked roadmap item
- **THEN** `sdlc-roadmap` SHALL be able to update the item status to `ready` without setting `started_at`

#### Scenario: Mark ready item active at apply start
- **WHEN** implementation starts for a linked roadmap item whose status is `ready`
- **THEN** `sdlc-roadmap` SHALL be able to update the item status to `active` and set `started_at`

#### Scenario: Mark active item done after archive
- **WHEN** an archived linked OpenSpec change corresponds to a roadmap item whose status is `active`
- **THEN** `sdlc-roadmap` SHALL be able to update the item status to `done` and set `completed_at`

#### Scenario: Preserve domain ownership
- **WHEN** workflow runtime or orchestrator code requires a roadmap item transition
- **THEN** the roadmap mutation SHALL be performed by `sdlc-roadmap`, not by direct edits from workflow runtime or orchestrator code
