## Why

当前项目的 AI-native 开发栈（opencode + OpenSpec + Superpowers + Memory Sync）缺少一层"长期产品路线图编排层"。OpenSpec 管理当前 change 的规格/设计/任务，Memory Sync 负责长期知识沉淀，但 MVP/V2/V3 的全局路线图、item 如何逐步转为 OpenSpec change、路线调整如何记录，这几个环节之间没有桥接机制。

具体痛点（详见 `design/roadmap.md`）：
1. LLM 在 brainstorm/propose 阶段给出的 MVP/V2/V3/Later 规划常在聊天中遗失
2. OpenSpec 只聚焦单个 change，不维护全局演进路线
3. 缺少"长期路线图 -> 可执行 OpenSpec change"的转化机制
4. 中途路线调整无追踪
5. 轻量优化（不值得开 OpenSpec）无记录，随聊天消失

需要新增 `sdlc-roadmap` skill，在 OpenSpec 之上提供薄编排层。

## What Changes

- **New skill `skills/sdlc-roadmap/`**: SDK 编排层 skill，提供 roadmap init/capture/list/promote/done 能力
- **New templates**: `templates/roadmap.md`、`templates/item.md`、`templates/decisions.md`
- **New scripts**:
  - `scripts/validate.py`：校验 item frontmatter、index.json 一致性、状态合法性
  - `scripts/list.py`：从 `items/*.md` 生成路线图摘要
  - `scripts/rebuild_index.py`：从 `items/*.md` 重建 `index.json`
- **`.roadmap/` 目录模型**: roadmap.md、index.json、items/、revisions/、patches/、decisions.md
- **Skill 复制**: 同步到 `.opencode/skills/sdlc-roadmap/SKILL.md` 确保当前 opencode 可触发

## Capabilities

### New Capabilities
- `sdlc-roadmap`: SDLC 路线图编排——长期路线图捕获、OpenSpec promotion 入口、完成回写、状态流转

## Impact

- New skill directory: `skills/sdlc-roadmap/`
- No changes to existing skills
- No changes to OpenSpec schema
- No changes to `.ai-memory/` memory system
- No breaking changes
- V1 不含 replan、patch log、复杂 CLI
