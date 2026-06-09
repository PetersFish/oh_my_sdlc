## Context

oh_my_skills 项目已有完整的 SDLC 技能族（bootstrap/init/memory），以及 OpenSpec + Superpowers 执行栈。但产品级别缺少一层负责"长期路线图 -> 单次正式变更"的编排层。

已完成的上下文工作：
- `design/roadmap.md`：调研报告与详细设计（痛点分析、开源生态对比、对象模型、状态机、命令设计）
- `design/roadmap.md` 审核结论：MVP 收敛为 skill + 最小校验脚本，定位为薄 SDLC 编排层
- `.roadmap/` 已创建，包含 RM-001 到 RM-004 的 roadmap items、decisions.md
- 核心边界决策已记录于 `.roadmap/decisions.md`

## Goals / Non-Goals

**Goals:**
- 提供 `sdlc-roadmap` skill，补齐 OpenSpec 与长期路线图之间的编排层
- MVP 支持：roadmap init / capture / list / promote / done
- 提供三个最小脚本：validate.py / list.py / rebuild_index.py
- 定义 `.roadmap/` 文件模型（roadmap.md、index.json、items/、revisions/、patches/、decisions.md）
- promote 生成 promotion context + 引导 OpenSpec skill，不复制 OpenSpec 逻辑
- done 后提示是否需要 patch、replan、memory sync
- 同步到 `.opencode/skills/sdlc-roadmap/` 确保当前 opencode 可触发

**Non-Goals:**
- V1 不含 replan / defer / cancel / supersede（留到 V2）
- V1 不含 Patch Log（留到 V2）
- 不含 `/patch.apply` 执行器（即使 V2 也只做记录和升级判断）
- 不含 Web UI / Kanban / GitHub Issues 集成
- 不含复杂 CLI
- 不自动生成 OpenSpec change 的全部 artifacts（proposal/design/tasks/spec）
- 不重复 OpenSpec、Superpowers、Memory Sync 的逻辑

## Decisions

### Decision 1: 薄编排层，不是替代品

sdlc-roadmap 是 Roadmap Layer 的编排器。不替代 OpenSpec（Change Layer）、Superpowers（Execution Layer）、Memory Sync（Memory Layer）。

**职责边界:**
- Roadmap: 长期序列、阶段目标、优先级、promotion 入口、done 后后续提示
- OpenSpec: 正式 change 的 proposal/design/tasks/spec
- Superpowers: TDD、debug、review、implementation
- Memory Sync: 长期事实沉淀（能力、架构、踩坑、约定）

**Alternatives considered:**
- 直接扩展 OpenSpec 承担 roadmap 职责：rejected，OpenSpec 以 change 为中心，不是 product roadmap 为中心
- 引入第三方工具（Backlog.md 等）：rejected，需要更紧密地和现有 openspec/superpowers/memory 体系集成
- roadmap-manager 作为独立大型 skill：rejected，V1 范围过大不利于稳定

### Decision 2: MVP 不含 replan 和 patch

第一版只做核心编排闭环（capture -> promote -> done），replan 和 patch 推迟到 V2。

**Rationale:** 第一版如果同时覆盖 roadmap、OpenSpec promotion、patch log、revision log，容易导致行为分散、回归风险高。先验证核心闭环（路线图可见 + promotion 链路 + 完成回写），再用实际经验设计 replan/patch 的行为细节。

**Alternatives considered:**
- 全量第一版：rejected，行为面太大，调试困难
- 只有 capture/list：rejected，没有 promote/done 无法形成闭环

### Decision 3: promote 不复制 OpenSpec 逻辑

`roadmap promote` 读取 RM item 生成 promotion context，调用或引导 OpenSpec skill，然后回写 `openspec_change` 和状态。不直接生成 proposal/design/tasks/spec。

**Rationale:** 已有 `openspec-propose`、`openspec-new-change` 等 skills 负责规格生成。Roadmap 负责"为什么现在做这个"，OpenSpec 负责"怎么规格化"。

**Alternatives considered:**
- 在 promote 中生成完整 OpenSpec artifacts：rejected，重复造轮且容易和已有 OpenSpec skills 冲突
- 不生成任何东西只更新状态：rejected，太薄导致每次都要再手动执行 OpenSpec CLI

### Decision 4: 命名统一为 sdlc-roadmap

Skill 名称 `sdlc-roadmap`（非 `roadmap-manager`），目录 `skills/sdlc-roadmap/`。

**Rationale:** 与 `sdlc-project-bootstrap`、`sdlc-openspec-init`、`sdlc-repository-memory-*` 同族，触发边界更清晰。

### Decision 5: 脚本优先做读和校验

三脚本选型：validate.py（校验）、list.py（只读摘要）、rebuild_index.py（从 item 重建 index）。

**Rationale:** 读和校验比写更容易稳定。复杂生成仍交给 LLM，脚本只负责结构检查和一致性。

**Alternatives considered:**
- 直接用 LLM 维护所有文件：rejected，无校验层容易产生不一致
- 全部用脚本自动化：rejected，V1 过度工程化，LLM 生成 item 内容的质量高于脚本

### Decision 6: 文件模型

`.roadmap/` 目录位于项目根目录，与 `openspec/`、`.ai-memory/`、`skills/` 平级。

```
.roadmap/
  roadmap.md          # 人类可读总览
  index.json          # 机器索引（派生，非唯一事实源）
  items/              # RM-XXX-*.md，每文件一个 item
  revisions/          # 路线调整记录（V2 正式启用）
  patches/            # 轻量修补记录（V2 正式启用）
  decisions.md        # 跨 item 决策记录
```

Markdown item 文件是唯一事实源，index.json 是派生索引。不一致时以 item 为准，允许 `/roadmap sync` 修复索引。

### Decision 7: 分发策略

canonical path: `skills/sdlc-roadmap/SKILL.md`。
当前会话同步到 `.opencode/skills/sdlc-roadmap/SKILL.md`。
后续分发到 `~/.config/opencode/skills/`、`~/.claude/skills/` 等多 CLI 目标。

**Rationale:** 参考已知 pitfall（stale-global-skill-copies），必须同时更新 canonical 和运行时路径，否则 opencode 可能加载过期版本。

## Risks / Trade-offs

- **Risk: skill 未正确分发到运行时路径，导致 opencode 不触发。** -> Mitigation: V1 同时创建 `.opencode/skills/sdlc-roadmap/SKILL.md` 副本；后续分发遵循 lifecycle governance 流程。
- **Risk: promote 和已有 OpenSpec skills 竞争触发。** -> Mitigation: `sdlc-roadmap` 的 description 明确限定为"roadmap 编排"，不影响 openspec-propose/new-change 的独立触发。
- **Risk: 仅靠 LLM 维护文件可能产生不一致。** -> Mitigation: V1 就要三个校验脚本，后续增强覆盖。
- **Risk: index.json 与 item 文件不一致时用户困惑。** -> Mitigation: validate.py 首先检查此问题，输出差异报告；不静默修复。
- **Risk: `.roadmap/` 目录增长过快。** -> Mitigation: items/ 每文件一个 item，数量有限；patches/ 有明确数量上限建议（每 item 不超过 10 个 patches，超限建议 escalate）。
