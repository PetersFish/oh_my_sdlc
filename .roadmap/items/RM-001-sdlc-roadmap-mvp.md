---
id: RM-001
title: sdlc-roadmap Skill MVP
status: ready
stage: mvp
priority: p0
order: 10
depends_on: []
openspec_change: add-sdlc-roadmap-skill
created_at: 2026-06-09
started_at: null
completed_at: null
patches: []
---

# Goal

实现 sdlc-roadmap skill 的最小可用版本，补齐 OpenSpec 与长期路线图之间的编排层。

# Scope

## In

- `skills/sdlc-roadmap/SKILL.md`：skill 主文档，定义触发条件、命令语义、状态机、边界规则。
- `templates/roadmap.md`：`.roadmap/roadmap.md` 模板。
- `templates/item.md`：roadmap item 模板。
- `templates/decisions.md`：decisions 模板。
- `scripts/validate.py`：校验 item frontmatter、index.json 一致性、状态合法性。
- `scripts/list.py`：从 `items/*.md` 生成路线图摘要输出。
- `scripts/rebuild_index.py`：从 `items/*.md` 重建 `index.json`。
- 能力：`roadmap init` / `roadmap capture` / `roadmap list` / `roadmap promote` / `roadmap done`。
- 同步到 `.opencode/skills/sdlc-roadmap/SKILL.md`，确保当前 opencode 可触发。

## Out

- `/patch.apply` 执行器（Patch 只做记录和升级判断，不自动执行代码）。
- 自动生成完整 OpenSpec artifacts（promote 生成 context + 引导，不代劳 proposal/design/tasks/spec）。
- Web UI / Kanban / GitHub Issues 集成。
- 复杂 CLI。
- replan / defer / cancel / supersede（留到 V2）。

# Acceptance Criteria

- `skills/sdlc-roadmap/SKILL.md` 存在且 frontmatter 合法。
- 模板文件存在且格式正确。
- `validate.py` 能检测 item status 非法、depends_on 悬空引用、index 与 item 不一致。
- `rebuild_index.py` 从 item 文件生成 index.json，不丢字段。
- `list.py` 输出稳定的 roadmap 摘要表。
- 测试覆盖上述脚本的核心路径。
- opencode 在用户说"初始化 roadmap"或"roadmap capture"时能正确触发 skill。

# Promotion Notes

生成 OpenSpec change 时使用 change id: `add-sdlc-roadmap-skill`。

核心边界决策已在 `design/roadmap.md` 审核中确认：
- Roadmap 是薄编排层，不替代 OpenSpec/Superpowers/Memory Sync。
- promote 生成 context + 引导 OpenSpec skill，不复制 OpenSpec 逻辑。
- Patch 第一版只做记录和升级判断，不执行代码。

# Design Reference

详见 `design/roadmap.md` 审核结论。
