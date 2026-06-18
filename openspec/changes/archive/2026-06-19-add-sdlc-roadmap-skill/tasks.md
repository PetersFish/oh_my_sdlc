## 1. Setup

- [x] 1.1 创建 `skills/sdlc-roadmap/` 目录结构（templates/, scripts/）
- [x] 1.2 确认 `.roadmap/` 空目录不存在冲突

## 2. sdlc-roadmap Skill

- [x] 2.1 创建 `skills/sdlc-roadmap/SKILL.md`（frontmatter + 完整工作流描述）
- [x] 2.2 定义 skill description（触发边界、与 OpenSpec skills 的排除规则）
- [x] 2.3 定义 roadmap init / capture / list / promote / done 命令语义
- [x] 2.4 定义 Roadmap Item 状态机（idea/planned/ready/active/done/deferred/cancelled/superseded）
- [x] 2.5 定义与 OpenSpec、Memory Sync 的边界规则
- [x] 2.6 定义 `.roadmap/` 文件模型

## 3. Templates

- [x] 3.1 创建 `skills/sdlc-roadmap/templates/roadmap.md`
- [x] 3.2 创建 `skills/sdlc-roadmap/templates/item.md`（含 frontmatter + body 节）
- [x] 3.3 创建 `skills/sdlc-roadmap/templates/decisions.md`

## 4. Scripts

- [x] 4.1 创建 `skills/sdlc-roadmap/scripts/validate.py`：校验 item 状态、depends_on、index 一致性
- [x] 4.2 创建 `skills/sdlc-roadmap/scripts/rebuild_index.py`：从 items/*.md 重建 index.json
- [x] 4.3 创建 `skills/sdlc-roadmap/scripts/list.py`：从 items 生成路线图摘要

## 5. Distribution

- [x] 5.1 复制 `skills/sdlc-roadmap/` 到 `.opencode/skills/sdlc-roadmap/`

## 6. Tests

- [x] 6.1 创建 `tests/test_sdlc_roadmap.py`
- [x] 6.2 测试 skill frontmatter 合法性（name, description 非空）
- [x] 6.3 测试模板文件存在（roadmap.md, item.md, decisions.md）
- [x] 6.4 测试 validate.py：非法状态检测
- [x] 6.5 测试 validate.py：depends_on 悬空引用检测
- [x] 6.6 测试 validate.py：index 与 item 不一致检测
- [x] 6.7 测试 validate.py：正常通过场景
- [x] 6.8 测试 rebuild_index.py：正常从 items 生成 index
- [x] 6.9 测试 rebuild_index.py：空 items 目录
- [x] 6.10 测试 rebuild_index.py：已存在 index 时的备份行为
- [x] 6.11 测试 list.py：正常输出
- [x] 6.12 测试 list.py：空 items 目录友好提示
- [x] 6.13 测试 `.opencode/skills/sdlc-roadmap/SKILL.md` 内容与源一致

## 7. Execution Notes / TDD Notes

- Test-first work: 先写测试，验证脚本行为后再确认通过
- Verification commands:
  - `python skills/sdlc-roadmap/scripts/validate.py` 应校验当前 `.roadmap/`
  - `python skills/sdlc-roadmap/scripts/list.py` 应输出当前路线图
  - `python skills/sdlc-roadmap/scripts/rebuild_index.py` 应从当前 items 重建 index
  - `pytest tests/test_sdlc_roadmap.py -v`
- Sequencing constraints:
  - 任务 1-3（setup、skill、templates）并行或任意顺序
  - 任务 4（scripts）可与 2-3 并行
  - 任务 5（distribution）依赖任务 2
  - 任务 6（tests）依赖任务 2-4
- Risky tasks: 2.1（SKILL.md 内容直接影响触发准确性）
