# 背景

> 本次迭代只落地目标 1-3：减少无意义授权打断、保持最小必要权限、把 MUST-first 工具策略写成可执行契约。
> gate 强化与历史兼容清理仅保留为后续提案，不属于本轮实施范围。

当前 SDLC 子代理体系已经拆分为 `dev-orchestrator`、`plan-agent`、`implement-agent`、`test-agent`、`review-agent`、`finish-agent` 等角色，并且每个角色在 prompt 中都定义了明确职责、输入输出契约和 handoff 产物要求。这套拆分方向是对的，但实际运行中出现了两个明显问题：

1. 多个 subagent 的职责与权限不一致。
2. 模型，尤其是 `deepseek-v4-pro`，对 skill、MCP、原生高阶工具的主动使用不足。

第一个问题最直接的表现是：很多 agent 需要写 handoff、plan、raw logs 或 workflow 运行产物，但 frontmatter 里的 `permission` 又把 `edit` 禁掉或设为 `ask`，导致流程频繁被权限拦截。用户本来处于连续思考和协作状态，却被系统反复要求授权，这会显著打断工作流。

第二个问题是：即使仓库已经提供了 `codegraph`、`tavily-search`、`context7`、`headroom`、`sdlc-repository-memory-load` 等高价值能力，模型也不一定会主动调用。结果是 agent 常常退回到低效的 bash 探索路径，例如依赖 `grep/find/ls/cat/head` 组合做代码理解，或者在需要最新文档和外部实践时不去主动联网调研。这样不仅效果差，也更容易误判问题。

此外，用户补充指出一个更核心的痛点；该项在本轮只作为后续方向记录，不进入当前实施：

- 当前系统最需要优化的不是历史 run 的修复，而是“实现偏离 spec / 预期时，test / review / finish gate 没有及时拦住”。

这说明当前问题不能只从“权限是否够用”来处理，还要从“各 gate 是否真的承担了应有的质量约束职责”来设计。否则即使权限放通了，也只是让 agent 更顺畅地继续偏离。

# 设计目标

本设计本轮只解决以下问题：

1. 降低 subagent 因权限不足而触发的无意义授权打断。
2. 保持最小必要权限原则，避免把危险能力一次性全部放开。
3. 明确各 subagent 在何种场景下必须优先调用 skill、MCP 和高阶工具。
4. （后续提案）提高 `test-agent`、`review-agent`、`finish-agent` 对 spec 偏离、预期偏离、验证缺口的拦截能力。
5. （后续提案）清理已经不再重要的历史兼容包袱，避免旧逻辑长期拖累新工作流。

# 非目标

本设计不打算在这一轮解决以下问题：

1. 不重写整个 workflow 运行时架构。
2. 不在本轮引入新的状态机框架或替换 `workflow.py`。
3. 不做跨所有 agent 的插件式集中权限系统重构。
4. 不优先处理历史 run 的数据回填和订正；用户已明确表示历史修复不是当前重点。

# 当前问题分析

## 1. 职责与权限不一致

从现有 agent 定义来看，多个角色的 prompt 正文已经要求它们写出明确产物，例如：

- `plan-agent` 需要写 `plan.md` 和 handoff。
- `implement-agent` 需要写 handoff 和 raw logs，并修改实现代码。
- `test-agent` 需要写 handoff、raw logs，必要时还要产出 EvalOps 回归资产。
- `review-agent` 需要写 handoff、验证日志。
- `finish-agent` 需要执行 archive、memory sync、roadmap done、workflow hook completion 等收尾动作。

但 frontmatter 中的权限并不总是支持这些职责：

- `plan-agent` 当前 `edit: deny`，与“生成计划产物”直接冲突。
- `test-agent` 当前 `edit: deny`，与“写 handoff/raw logs/EvalOps 产物”直接冲突。
- `review-agent` 当前 `edit: deny`，与“写 handoff/raw logs”不一致。
- `finish-agent` 当前 `edit: ask`，会让本应连续执行的 archive 和 cleanup 过程被频繁中断。

这类冲突不是“模型不会用权限”，而是契约本身前后矛盾。只要契约矛盾存在，agent 行为就不可预测：要么频繁阻塞，要么为了规避权限不足而走低质量旁路。

## 2. bash 权限过窄，但高阶工具使用策略又不够硬

当前 `implement-agent` 已经允许 `pytest`、`workflow.py`、`git status`、`git diff` 等命令，但在实际工程中还会自然需要以下只读动作：

- `git log`
- `git branch`
- `git worktree`
- `git check-ignore`

类似地，`finish-agent` 在收尾时也会需要只读 git 观察能力。问题不在于这些命令本身危险，而在于目前白名单不完整，导致本应安全的查看操作也会触发权限询问。

与此同时，用户记录的 `grep`、`head`、`find`、`ls`、`cat` 等需求，本质上反映的是“agent 需要探索能力”。但在 opencode 体系下，很多探索性需求其实已经有更好的抽象工具：

- 查文件：`Glob`
- 查文本：`Grep`
- 读文件：`Read`
- 理解代码结构：`codegraph_*`

因此本设计不建议简单地把传统 bash 探索命令大量加白，而是要明确：

- 优先使用平台已有的高阶工具。
- 当高阶工具不够时，停止并返回 blocker / remediation，而不是退回受限 bash。

本轮进一步收紧为：不保留任何通用 bash 探索降级路径。高阶工具不可用、未索引或能力不足时，agent 必须返回 blocker / remediation，而不是退回 shell 探索。

## 3. 模型没有被强约束去主动使用关键能力

用户明确指出 `deepseek-v4-pro` 在 MCP/skill 层面主动性较弱，这不是单个 prompt 语气问题，而是系统设计问题：

- 有工具，但触发条件写得不够硬。
- 有 skill，但角色 prompt 没有把“什么时候必须调用”表达成强约束。
- 有 memory / codegraph / context7 / tavily / headroom，但没有形成统一 Tool Usage Policy。

如果只是“推荐使用”，模型很容易在时间压力下退回最熟悉的通用路径。对这类问题，必须在 prompt 中使用更强的契约语言，例如 `MUST`、`ONLY WHEN`、`prefer before bash` 等。

## 4. gate 的质量边界不够锋利

用户最关心的是：实现如果偏离 spec / 预期，为什么没有被 `test-agent`、`review-agent`、`finish-agent` 拦住？

从现有 prompt 看，三个 gate 角色虽然都定义了任务，但仍然存在几个风险：

1. `test-agent` 更偏执行验证，但对“实现是否满足 spec/计划意图”的回查约束还不够强。
2. `review-agent` 虽然强调 review，但可能仍然更偏代码质量和测试结果，而不是“是否实现了约定行为”。
3. `finish-agent` 主要关注 archive / hook / cleanup，如果没有显式前置检查，很容易把“流程收尾”误当成“变更已被正确验证”。

这意味着 gate 目前更像流程节点，而不是足够强的质量闸门。

## 5. 历史兼容逻辑需要重新审视

用户已明确：

- 历史 run 的订正不是本轮重点。
- `_migrate_legacy_artifacts` 如果删除安全，可以删除。

这说明本轮应优先追求“当前主路径更干净、更可控”，而不是继续为了少量历史兼容逻辑保留复杂度。兼容逻辑如果长期存在，容易污染 agent prompt、workflow 脚本和验证逻辑，让新路径始终背着旧路径包袱。

# 设计原则

## 原则 1：权限按职责分层，不按方便放大

每个 agent 只获得其角色完成工作所需的最小权限：

- 只真正修改实现代码的 agent 才应拥有“通用 edit 能力”。
- 只需要写运行产物的 agent，可以允许写，但应通过 prompt 和测试将写入范围限制在 workflow artifacts。
- 只读探索命令可以相对放宽，但危险 git 和破坏性 shell 操作必须持续收紧。

## 原则 2：优先放开 workflow 产物写入，而不是全局写入意图

`plan-agent`、`test-agent`、`review-agent`、`finish-agent` 的主要写入不是产品代码，而是：

- `plan.md`
- handoff 文档
- raw logs
- workflow 运行产物
- memory / roadmap / archive 相关收尾资产

本设计承认：如果平台权限模型不能做到 path-scoped `edit`，那就需要以“edit 允许 + prompt 严格约束 + 契约测试”这一组合来替代真正的路径级访问控制。

## 原则 3：探索优先使用高阶工具，不优先放开传统 bash

对代码理解与检索类任务，应优先使用：

- `sdlc-repository-memory-load`
- `codegraph`
- `Glob`
- `Grep`
- `Read`

而不是默认给 `find`、`ls`、`cat`、`head` 大量白名单。这样既减少低质量 bash 依赖，也降低 prompt 和权限面的不必要扩张。

## 原则 4：工具触发条件必须可执行，不是建议性口号

对于 `deepseek-v4-pro` 这类主动性偏弱的模型，不能只写“可以使用某工具”，必须写成：

- 何时必须用
- 何时优先用
- 何时禁止退化为 bash

否则工具可用性并不会自动变成工具使用率。

## 原则 5：gate 要对“偏离预期”负责，而不是只对“流程走完”负责

`test-agent`、`review-agent`、`finish-agent` 不能只完成各自流程动作，还必须承担以下职责：

- 检查实现是否覆盖了 plan/spec 中承诺的行为
- 检查测试是否真的验证了预期行为，而不是仅验证实现细节
- 检查收尾前是否已有足够证据说明变更达到要求

# 解决方案

## 一、调整 subagent 权限模型

### 1. `dev-orchestrator`

定位保持不变：它仍然只是纯路由和 workflow 控制协调器。

建议权限：

- `edit: deny`
- `task: allow`
- `question: allow`
- `skill`: 白名单控制，但扩大到它在路由期真正需要的前置能力
- bash 仍仅允许 workflow 控制和只读 git 观察：
  - `python3 .ai/workflows/scripts/workflow.py *`
  - `python3 skills/_lib/resolve_dispatch_cli.py *`
  - `git status*`
  - `git diff*`
  - `git log*`

不建议让 `dev-orchestrator` 获取实现级探索和写入权限，因为这会模糊它与 specialized subagent 的边界。

### 2. `plan-agent`

当前问题是职责要求它生成计划文档和 handoff，但权限却禁止写入。

建议权限：

- `edit: allow`
- `skill: allow`
- `task: deny`
- `question: allow`
- bash 允许有限只读：
  - `python3 .ai/workflows/scripts/workflow.py *`
  - `git status*`
  - `git diff*`
  - `git log*`

补充约束：

- prompt 中明确说明它只允许写 workflow 计划和 handoff 产物，不允许修改源码、测试、配置和用户文档。

### 3. `implement-agent`

它是唯一应继续拥有通用代码修改职责的 agent。

建议权限：

- 保持 `edit: allow`
- bash 在现有基础上增加安全只读 git 命令：
  - `git log*`
  - `git branch*`
  - `git worktree*`
  - `git check-ignore*`
- 保留：
  - `python3 -m pytest *`
  - `pytest *`
  - `python3 .ai/workflows/scripts/workflow.py *`
  - `git status*`
  - `git diff*`

继续禁止：

- `git commit*`
- `git push*`
- `git reset*`
- `git checkout *`
- `rm *`

### 4. `test-agent`

当前 `edit: deny` 与 handoff / raw logs / EvalOps 产物写入冲突最明显。

建议权限：

- `edit: allow`
- `skill: allow`
- `task: deny`
- `question: ask`
- bash 允许：
  - `python3 -m pytest *`
  - `pytest *`
  - `python3 .ai/workflows/scripts/workflow.py *`
  - `git status*`
  - `git diff*`
  - `git log*`

补充约束：

- prompt 中明确禁止修改实现代码。
- 允许写入 workflow 产物、日志以及必要的 EvalOps 回归资产。

### 5. `review-agent`

`review-agent` 不应修改业务代码，但确实需要写 handoff 和验证日志。

建议权限：

- `edit: allow`
- `skill: allow`
- `task: deny`
- `question: ask`
- bash 允许：
  - `python3 -m pytest *`
  - `pytest *`
  - `python3 .ai/workflows/scripts/workflow.py *`
  - `git status*`
  - `git diff*`
  - `git log*`

补充约束：

- prompt 中明确只允许写 handoff 和验证相关日志，不允许直接修复代码。

### 6. `finish-agent`

它承担 archive、memory sync、roadmap、workflow hook completion 等收尾职责，持续 `ask` 会严重破坏流畅性。

建议权限：

- `edit: allow`
- `skill: allow`
- `task: deny`
- `question: ask`
- bash 允许：
  - `python3 .ai/workflows/scripts/workflow.py *`
  - `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py *`
  - `git status*`
  - `git diff*`
  - `git log*`
  - `git branch*`
  - `git worktree*`

补充约束：

- prompt 中明确其写入职责仅限 archive、workflow 产物、memory sync、roadmap 收尾等，不进入新的实现修改。

## 二、为所有 subagent 增加统一 Tool Usage Policy

建议在 `plan-agent`、`implement-agent`、`test-agent`、`review-agent`、`finish-agent` 中统一加入一段强约束策略，用于提升 `deepseek-v4-pro` 的工具使用稳定性。

### 统一策略内容

#### 1. 代码库理解

当需要理解当前代码库结构、模块关系、调用链、符号定义时：

- 当任务依赖历史决策、模块关系或代码结构时，必须先调用 `sdlc-repository-memory-load` 获取仓库记忆上下文。
- 如果只是 doc-only 或 single-known-file workflow artifact 工作，可跳过 memory/codegraph 前置要求。
- 必须优先使用 `codegraph_*` 进行结构化理解。
- 观察性 git 不是代码探索主路径。

#### 2. 文件与文本搜索

- 查文件优先 `Glob`
- 查文本优先 `Grep`
- 读文件优先 `Read`
- 禁止退化为 bash 探索；工具不可用时必须返回 blocker / remediation

#### 3. 最新技术调研

当任务涉及最新外部实践、近期技术变化、当前行业方案时：

- 必须使用 `tavily-search`

#### 4. 最新库/API/CLI 文档和代码范例

当任务涉及库、框架、SDK、CLI、云服务的当前文档、参数语义、迁移信息或代码示例时：

- 必须使用 `context7`

#### 5. 大输出压缩

当命令输出、日志、长文档内容过大时：

- 应优先使用 `headroom` 压缩上下文
- 不应把大量原始输出直接带入后续多步推理

#### 6. skill 纪律

- 只要任务命中已有 skill 的触发条件，就必须先调用 skill 再行动。
- 不得以“事情很小”为理由跳过 skill。

#### 7. 失败处理

- 若首选工具 unavailable、unindexed 或 demonstrably insufficient，必须 stop 并返回 blocker / remediation。
- 不允许把 `git` 或其他 shell 命令重新当成通用探索兜底。

## 三、对不同 agent 增加角色特定工具约束

### `plan-agent`

- 代码理解优先 `sdlc-repository-memory-load` + `codegraph_context`
- 只对影响设计和计划闭环的问题进行探索
- 如果需要用户进一步输入，返回结构化 `questions_for_user`，而不是自己持续展开实现讨论

### `implement-agent`

- 修改代码前优先定位最小改动点
- 结构问题优先使用 `codegraph_context`、`codegraph_trace`
- 需要当前库/API示例时再调用 `context7`
- 不得为了方便扩大为 bash-heavy 工作流

### `test-agent`

- 重点验证行为，而不是围绕实现细节堆测试
- 需要最新测试实践或 AI 回归方案时才调用 `tavily-search` / `context7`
- 大日志必须考虑 `headroom`
- 不得借修测试之名修改实现代码

### `review-agent`

- findings 优先
- review 必须关注“是否符合 spec / plan / 预期行为”，而不是只看代码风格
- 如需判断库行为或外部约束，可调用 `context7`
- 不得直接修复代码

### `finish-agent`

- 优先处理 archive、workflow hook、memory、roadmap
- 不应重新发散到实现细节探索
- 只在收尾必要场景使用联网或上下文压缩能力

## 四、后续提案：强化 gate，明确谁负责拦截偏离预期的实现

以下内容保留为后续提案，不纳入本轮 goals 1-3 实施。

### 1. `test-agent` 的职责补强

`test-agent` 不应只机械执行测试命令，还应承担“验证实现是否覆盖计划和预期行为”的职责。

建议在 prompt 中明确要求：

1. 复核 `implement-agent` 提交的 focused tests 是否覆盖计划中的关键行为点。
2. 检查新测试是否只验证实现细节、字符串或内部调用，而没有覆盖真实行为。
3. 当 plan/spec 中存在明确验收点时，应回查这些验收点是否有对应验证证据。
4. 如果发现“测试是绿的，但关键承诺行为未被验证”，应返回 blocker，而不是简单通过。

这能把 `test-agent` 从“测试执行者”提升为“行为验证 gate”。

### 2. `review-agent` 的职责补强

`review-agent` 应成为“实现与预期一致性”的最后质量审查层，而不仅是一般代码 review。

建议它增加以下显式检查：

1. 读取 plan/handoff/spec 摘要，确认实现覆盖了约定的目标范围。
2. 检查是否存在“实现看起来合理，但偏离了原始需求”的情况。
3. 检查测试是否遗漏关键负例、边界条件或集成层验证。
4. 如果发现变更虽通过测试，但未完成计划承诺，应返回 blocker，并路由回 `implement-agent` 或 `plan-agent`。

这能避免“测试通过但功能方向错了”仍然进入 finish。

### 3. `finish-agent` 的职责补强

`finish-agent` 不应把 archive / sync 的完成当成变更正确性的证明。

建议其在执行收尾前明确检查：

1. `test-agent` 的 `verification_passed` 是否存在且为真。
2. `review-agent` 的 `review_complete` 是否存在且为真。
3. 是否仍有未解决 blocker、未处理 hook 或未闭环的 spec/plan 偏差。
4. 如发现前序 gate 证据不足，应停止 finalize，而不是继续归档。

换句话说，`finish-agent` 要对“只有验证充分的变更才能收尾”负责。

## 五、后续提案：清理历史兼容逻辑

以下内容保留为后续提案，不纳入本轮 goals 1-3 实施：

1. 若 `_migrate_legacy_artifacts` 已不再是当前主路径所需，且删除不会破坏现有核心流程，应考虑移除。
2. 即使暂时保留，也应把它视为待删除兼容层，而不是继续扩展其职责。
3. 新的权限和 prompt 设计不应为了兼容旧产物路径而变复杂。

这样可以避免当前主路径被旧逻辑拖住，持续增加调试和提示词复杂度。

# 推荐权限矩阵摘要

| Agent | edit | bash 核心策略 | 核心限制 |
| --- | --- | --- | --- |
| `dev-orchestrator` | deny | 仅 workflow 控制 + 只读 git | 不做技术实现、不写文件 |
| `plan-agent` | allow | workflow.py + 观察性只读 git | 仅写 workflow artifacts，不改源码 |
| `implement-agent` | allow | pytest + workflow.py + 扩展观察性只读 git | 禁止 destructive git / shell；无 bash 降级 |
| `test-agent` | allow | pytest + workflow.py + 观察性只读 git | 不改实现，仅写 workflow artifacts / 验证产物 |
| `review-agent` | allow | pytest + workflow.py + 观察性只读 git | 不改实现，仅写 workflow artifacts / review 产物 |
| `finish-agent` | allow | workflow.py + sync + 扩展观察性只读 git | 仅做收尾与 workflow artifacts，不重新实现 |

# 关键 Trade-offs

## Trade-off 1：给非实现型 agent `edit: allow` 会扩大理论写面

这是本设计最明显的代价。

问题在于：

- 从角色职责看，`plan-agent`、`test-agent`、`review-agent`、`finish-agent` 都确实需要写某些文件。
- 但如果平台权限模型不能做路径级 `edit` 控制，那么只要它们要写产物，就必须得到较宽的 `edit` 能力。

风险：

- 理论上这些 agent 就具备修改源码的能力。

缓解手段：

1. 在 prompt 中写出强限制，只允许对应角色产物写入。
2. 用测试锁定这些限制文案，防止 prompt 漂移。
3. 保持这些角色不加载实现型技能组合。
4. 保持 `dev-orchestrator` 的路由边界清晰，不让它们承担实现任务。

## Trade-off 2：不大量放开 `find/ls/cat/head`，会保留一部分模型不适应成本

从用户体验看，直接开放传统 bash 探索命令似乎更省事；但从长期质量看，这会鼓励 agent 继续使用低效路径。

本设计刻意偏向：

- 优先使用 `Glob/Grep/Read/codegraph`
- 少量补足只读 git
- 不把探索主路径重新做成 bash-heavy 模式

代价是：

- 某些模型短期内可能仍然不习惯高阶工具抽象。

收益是：

- 长期工具使用质量更高，提示词更统一，也更符合当前平台能力边界。

## Trade-off 3：prompt 更强约束，会让 agent 提示更长

加入统一 Tool Usage Policy 和 gate 补强内容后，agent prompt 会变长。

代价：

- 上下文长度更大。
- 维护时需要更关注文案一致性。

收益：

- `deepseek-v4-pro` 这类主动性偏弱的模型更容易稳定命中正确工具。
- “推荐使用”升级为“必须使用”的契约之后，行为更可控。

## Trade-off 4：（后续提案）加强 gate 会增加通过门槛，也可能增加回退次数

一旦 `test-agent`、`review-agent` 更积极地拦截“测试虽绿但行为未闭环”的情况，短期内 workflow 可能会出现更多 blocker 和回退。

这不是坏事，而是把原本被漏掉的问题显式暴露出来。代价是流程看起来会更严格，收益是更接近用户真正关心的质量保障。

# 落地步骤

## 第一阶段：更新 canonical agent prompt 和 frontmatter

修改 `agents/` 下 canonical 文件：

- `agents/dev-orchestrator.md`
- `agents/plan-agent.md`
- `agents/implement-agent.md`
- `agents/test-agent.md`
- `agents/review-agent.md`
- `agents/finish-agent.md`

更新内容包括：

1. frontmatter `permission`
2. 统一 Tool Usage Policy
3. 各角色专项约束
4. goals 1-3 范围内的边界与工具策略文案

## 第二阶段：补契约测试

至少应增加以下测试：

1. frontmatter 权限测试
2. prompt 工具使用策略测试
3. 非实现型 agent 是否包含 workflow artifact-only 写入边界文案测试
4. 危险 git 命令未被误放开的测试

## 第三阶段：分发到多 CLI 目标

由于 `agents/` 是 canonical，修改后需要同步到：

- `.opencode/agents/`
- `.claude/agents/`
- `.cursor/agents/`

避免 canonical 与 distributed copies 漂移。

## 第四阶段：验证典型路径

应至少人工或脚本化验证以下典型场景：

1. `plan-agent` 能生成 plan/handoff，不再因写入被拦。
2. `implement-agent` 能进行只读 git 探索，不再因 `branch/worktree/check-ignore/log` 被拦。
3. `test-agent` 能写验证日志和 handoff，但不会被设计成修改实现代码。
4. 工具不可用时 agent 会返回 blocker / remediation，而不是降级为 bash 探索。

# 风险与缓解

## 风险 1：平台权限能力不足以表达“只允许写 workflow 产物”

缓解：

- 通过 prompt 强约束角色边界
- 通过测试防止边界文案回退
- 如后续 opencode 支持 path-scoped edit，可再进一步收紧

## 风险 2：agent 仍可能忽略工具策略

缓解：

- 使用 `MUST` 级语义
- 在关键角色中重复出现相同策略
- 对工具调用约束增加静态 prompt 契约测试

## 风险 3：（后续提案）兼容逻辑移除判断不充分

缓解：

- 在实际删除 `_migrate_legacy_artifacts` 前，先确认当前 workflow 主路径和测试不再依赖它
- 若存在少量残余依赖，可先标记废弃，再下一轮彻底删除

# 备选方案与为何不选

## 方案 A：只调权限，不调 prompt

优点：

- 改动小
- 可以快速减少授权打断

缺点：

- 无法解决模型不会主动使用 `codegraph`、`context7`、`tavily`、`headroom` 的问题
- 无法强化 gate 对偏离预期实现的识别能力

因此不选。

## 方案 C：一步上集中式权限治理或插件改写系统提示

优点：

- 中长期可维护性可能更好
- 可降低每个 agent 独立维护的成本

缺点：

- 改动范围大
- 验证成本高
- 本轮目标是优先解决真实运行痛点，不适合扩大为平台级重构

因此本轮不选。

# 最终建议

本轮应采用“权限收敛 + prompt/tool policy 收敛”的组合方案。

具体来说：

1. 为 `plan-agent`、`test-agent`、`review-agent`、`finish-agent` 开启完成职责所需的写入能力。
2. 为 `implement-agent` 和 `finish-agent` 补足安全只读 git 能力。
3. 不把传统 bash 探索命令作为主要增量，而是统一要求优先使用 `sdlc-repository-memory-load`、`codegraph`、`Glob/Grep/Read`、`context7`、`tavily-search`、`headroom`。
4. 将 gate 补强与 `_migrate_legacy_artifacts` 清理明确标记为后续提案，避免本轮范围漂移。

这样做的结果不是“让所有权限都更大”，而是让每个角色获得足够但可控的能力，并且把真正重要的质量约束重新压实到对应 gate 上。
