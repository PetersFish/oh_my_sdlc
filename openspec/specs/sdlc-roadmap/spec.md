# sdlc-roadmap

## Purpose

SDLC roadmap orchestration layer that bridges long-term product roadmap planning with OpenSpec changes. Provides a `.roadmap/` file model with structured item lifecycle management (capture, promote, list, done) and supporting tool scripts for validation, index rebuilding, and human-readable summaries.

## Requirements

### Requirement: Skill 目录结构与 frontmatter

sdlc-roadmap skill 必须位于 `skills/sdlc-roadmap/`，包含合法的 SKILL.md。

#### Scenario: skill frontmatter 存在且合法
- **WHEN** 读取 `skills/sdlc-roadmap/SKILL.md`
- **THEN** frontmatter 中 name 为 `sdlc-roadmap`，description 非空且包含触发关键词（roadmap、路线图、MVP/V2/V3/Later 规划）
- **THEN** description 明确声明"Use ONLY when..."以避免与 OpenSpec skills 误触发

#### Scenario: SKILL.md 包含完整工作流描述
- **WHEN** 读取 `skills/sdlc-roadmap/SKILL.md`
- **THEN** 文档包含 roadmap init / capture / list / promote / done 的命令描述
- **THEN** 文档包含 `.roadmap/` 文件模型说明
- **THEN** 文档包含 Roadmap Item 状态机定义（idea/planned/ready/active/done/deferred/cancelled/superseded）
- **THEN** 文档包含与 OpenSpec、Memory Sync 的边界规则

### Requirement: 模板文件

sdlc-roadmap skill 必须提供模板文件供项目初始化使用。

#### Scenario: 模板文件存在
- **WHEN** 检查 `skills/sdlc-roadmap/templates/`
- **THEN** 存在 `roadmap.md` 模板
- **THEN** 存在 `item.md` 模板（含 frontmatter: id, title, status, stage, priority, order, depends_on, openspec_change, patches）
- **THEN** 存在 `decisions.md` 模板

#### Scenario: item 模板 frontmatter 字段完整
- **WHEN** 读取 `skills/sdlc-roadmap/templates/item.md`
- **THEN** frontmatter 包含：id, title, status, stage, priority, order, depends_on, openspec_change, created_at, started_at, completed_at, patches
- **THEN** 模板包含 body 节：Goal, Scope, Acceptance Criteria, Promotion Notes, Completion Notes

### Requirement: 校验脚本 validate.py

`validate.py` 必须校验 `.roadmap/` 目录的结构一致性。

#### Scenario: 检测非法 item 状态
- **WHEN** 运行 `validate.py` 且存在 status 不在允许枚举中的 item
- **THEN** 输出错误信息，指明非法 status 值和所在文件
- **THEN** 退出码非零

#### Scenario: 检测 depends_on 悬空引用
- **WHEN** 运行 `validate.py` 且某 item 的 depends_on 指向不存在的 item id
- **THEN** 输出悬空引用错误
- **THEN** 退出码非零

#### Scenario: 检测 index 与 item 不一致
- **WHEN** 运行 `validate.py` 且 index.json 中某字段与 item 文件 frontmatter 不一致
- **THEN** 输出差异报告（具体字段名、index 值、item 值）
- **THEN** 退出码非零

#### Scenario: 校验通过时静默退出
- **WHEN** 运行 `validate.py` 且所有 item 合法、index 一致
- **THEN** 退出码为 0，无错误输出

### Requirement: 重建索引脚本 rebuild_index.py

`rebuild_index.py` 必须从 `items/*.md` 重建 `index.json`。

#### Scenario: 从 item 文件生成 index
- **WHEN** 运行 `rebuild_index.py`
- **THEN** 扫描 `.roadmap/items/*.md`
- **THEN** 输出 `index.json` 包含所有 item 的 id/status/title/stage/priority/order/depends_on/openspec_change/patches
- **THEN** items 按 order 升序排列

#### Scenario: 处理空 items 目录
- **WHEN** 运行 `rebuild_index.py` 且 `items/` 目录为空
- **THEN** 生成 version 为 1、items 为空数组的 index.json

#### Scenario: 不损坏已有 index
- **WHEN** 运行 `rebuild_index.py` 且 `index.json` 已存在
- **THEN** 先备份为 `index.json.bak`，再写入新索引

### Requirement: 列表脚本 list.py

`list.py` 必须从 item 文件生成人类可读的路线图摘要。

#### Scenario: 输出路线图摘要表
- **WHEN** 运行 `list.py`
- **THEN** 输出包含 ID、状态、标题、Stage 列的表格
- **THEN** 按 order 排序输出
- **THEN** 高亮或标记当前 active item

#### Scenario: 空路线图时友好提示
- **WHEN** 运行 `list.py` 且 `items/` 为空
- **THEN** 输出"No roadmap items found"并退出码为 0

### Requirement: Roadmap capture 行为

open code 执行 `roadmap capture` 时应从对话上下文提取路线图规划并生成 item 文件。

#### Scenario: 从对话捕获 roadmap items
- **WHEN** 用户说"把上面讨论的 MVP、V2、V3 规划整理进 roadmap"且 `.roadmap/` 已初始化
- **THEN** 识别阶段性规划（MVP、V2、V3 等）
- **THEN** 为每个阶段创建 `.roadmap/items/RM-XXX-*.md`
- **THEN** 更新 `roadmap.md`
- **THEN** 输出创建摘要

### Requirement: Roadmap promote 行为

promote 是将 roadmap item 转为 OpenSpec change 编排入口，不复制 OpenSpec 逻辑。

#### Scenario: promote 生成 promotion context
- **WHEN** 用户执行 `roadmap promote RM-001`
- **THEN** 读取 item 文件内容（Goal/Scope/Acceptance Criteria/Promotion Notes）
- **THEN** 生成 promotion context（摘要 item 的目标和范围）
- **THEN** 引导用户创建 OpenSpec change（调用 openspec-propose 或 openspec-new-change）
- **THEN** 将 item status 更新为 active，记录 `started_at`
- **THEN** 不直接创建 proposal.md / design.md / tasks.md / spec.md

#### Scenario: promote 检查依赖
- **WHEN** 用户执行 `roadmap promote RM-002` 且 depends_on 指向未完成的 RM-001
- **THEN** 输出警告"依赖项 RM-001 尚未完成"
- **THEN** 仍允许 promotion 但提示风险

### Requirement: Roadmap done 行为

done 标记 item 完成并提示后续动作。

#### Scenario: done 标记完成
- **WHEN** 用户执行 `roadmap done RM-001`
- **THEN** 更新 item status 为 done，记录 `completed_at`
- **THEN** 更新 `roadmap.md` 和 `index.json`
- **THEN** 提示是否需要：创建 patch、触发 roadmap replan、执行 memory sync

### Requirement: Skill 分发

sdlc-roadmap 必须同时存在于 canonical 路径和运行时路径。

#### Scenario: 运行时 skill 副本存在
- **WHEN** 检查 `.opencode/skills/sdlc-roadmap/SKILL.md`
- **THEN** 文件存在且与 `skills/sdlc-roadmap/SKILL.md` 内容一致

### Requirement: 测试覆盖

必须为脚本和 skill 行为提供测试。

#### Scenario: validate.py 测试
- **WHEN** 运行 `tests/test_sdlc_roadmap.py`
- **THEN** 包含 validate.py 的测试用例：非法状态检测、悬空引用、index 不一致、正常通过

#### Scenario: rebuild_index.py 测试
- **WHEN** 运行测试
- **THEN** 包含 rebuild_index.py 的测试用例：正常生成、空 items 目录、备份已有 index

#### Scenario: list.py 测试
- **WHEN** 运行测试
- **THEN** 包含 list.py 的测试用例：正常输出表格、空目录友好提示

#### Scenario: skill frontmatter 测试
- **WHEN** 运行 `tests/test_sdlc_roadmap.py`
- **THEN** 包含对 `skills/sdlc-roadmap/SKILL.md` frontmatter 合法性的测试
- **THEN** 包含对模板文件存在性的测试
