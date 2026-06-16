一个好的 skill，本质上不是“把提示词写得很长”，而是把某一类任务的**触发条件、输入边界、执行流程、质量标准、失败处理**封装成可复用的操作规范。

结合你现在的 OpenCode / Superpowers / OpenSpec / 自定义 memory、eval、roadmap、orchestrator 体系，我建议你用下面这套标准来判断一个 skill 是否合格。

---

# 一、好的 skill 应该具备的特征

## 1. 职责单一，边界清晰

好的 skill 应该只解决一类明确问题。

例如：

| Skill                    | 合理职责                                      |
| ------------------------ | ----------------------------------------- |
| `openspec-propose-skill` | 只负责生成 / 修订 OpenSpec proposal、design、tasks |
| `tdd-skill`              | 只负责红绿重构、测试驱动循环                            |
| `eval-skill`             | 只负责语义评估、golden case、rubric 评分             |
| `roadmap-skill`          | 只负责长期规划、版本项追踪、小优化沉淀                       |
| `memory-sync-skill`      | 只负责提交前后记忆更新                               |

不好的 skill 通常会这样写：

> 当用户要开发功能、修 bug、写文档、做测试、更新 roadmap、同步 memory、跑 eval 时，都使用本 skill。

这类 skill 其实已经不是 skill，而是一个混乱的超级 prompt。

---

## 2. 有明确的触发条件

好的 skill 要告诉模型：**什么时候该用，什么时候不该用**。

例如：

```md
Use this skill when:
- 用户正在设计一个中大型功能
- 需要生成或更新 OpenSpec change
- 需求尚未进入编码阶段

Do not use this skill when:
- 用户只是要求修一个小 bug
- 用户明确要求直接修改代码
- 当前任务已经有明确 tasks.md，且只需要执行其中一个 task
```

这可以避免模型乱用 skill。

尤其是你的体系里有多个 skill：Superpowers、OpenSpec、memory、eval、roadmap、orchestrator。如果触发条件不清楚，模型会出现两个问题：

1. 该用的时候不用；
2. 不该用的时候乱用。

---

## 3. 输入要求明确

一个好的 skill 要说明执行前需要哪些上下文。

例如一个 `eval-skill` 应该要求：

```md
Required inputs:
- 被评估对象：prompt / skill / agent workflow / review output
- 评估维度：准确性、一致性、稳定性、可解释性等
- case 来源：已有 case / 新增 case / 用户提供案例
- 是否允许自动修改被评估对象
```

一个差的 skill 会直接说：

> 对任务进行评估，并给出改进建议。

这太模糊。模型不知道评估什么、按什么标准评估、是否能改、是否要保存 case。

---

## 4. 输出物稳定、结构化

好的 skill 应该有稳定的输出格式。

例如 roadmap skill 的输出可以固定为：

```md
# Roadmap Item

## Status
planned / active / done / deferred / dropped

## Problem
...

## Scope
...

## Acceptance Criteria
...

## Dependencies
...

## Next Action
...
```

稳定输出的好处是：

1. 后续 skill 可以读取；
2. 便于 diff；
3. 便于自动化；
4. 避免每次输出风格漂移；
5. 适合作为长期项目资产。

如果 skill 每次输出格式都不一样，后续自动化基本会很痛苦。

---

## 5. 有清晰的执行流程

好的 skill 不只是描述目标，还要描述步骤。

例如：

```md
Workflow:
1. Understand the user's intent.
2. Classify task size: tiny / small / medium / large.
3. Decide whether OpenSpec is needed.
4. If needed, create or update proposal/design/tasks.
5. If not needed, route to lightweight implementation workflow.
6. Before coding, confirm acceptance criteria exist.
7. After coding, run deterministic tests.
8. If semantic behavior matters, invoke eval workflow.
```

这比“请按照最佳实践完成任务”强很多。

对你的场景尤其重要，因为你想做的是 agent 工作流，而不是单次问答。流程越明确，模型越不容易擅自跳步骤。

---

## 6. 有质量门禁

好的 skill 应该定义“什么叫完成”。

例如 `tdd-skill`：

```md
Completion criteria:
- 至少有一个失败测试先出现
- 实现代码只覆盖当前测试目标
- 所有相关测试通过
- 没有明显过度设计
- tasks.md 中对应项已更新
```

例如 `eval-skill`：

```md
Completion criteria:
- 每个 case 都有 pass/fail/uncertain 标记
- fail case 必须给出失败原因
- uncertain case 不能强行算作通过
- 修改 prompt 后必须重新跑关键 case
```

没有 completion criteria 的 skill，很容易变成“输出一段看起来不错的话”。

---

## 7. 明确副作用边界

这点对 OpenCode / Claude Code / Codex 这类 AI-CLI 特别重要。

一个好的 skill 要写清楚：

| 操作                     | 是否允许   |
| ---------------------- | ------ |
| 读取文件                   | 允许     |
| 修改文件                   | 何时允许   |
| 创建新文件                  | 何时允许   |
| 删除文件                   | 默认禁止   |
| 执行测试                   | 允许     |
| 执行 destructive command | 禁止或需确认 |
| 修改配置                   | 需确认    |
| commit / push          | 默认禁止   |

例如：

```md
Side-effect policy:
- In plan mode, do not modify files.
- In build mode, only modify files directly related to the selected task.
- Never delete files unless explicitly requested.
- Never run migration, deploy, or publish commands without explicit permission.
```

你的很多问题都和这个有关：你只想 propose，模型却开始写代码；你只想设计，它却 apply 了。这通常就是 skill 的副作用边界没写死。

---

## 8. 能处理失败和不确定性

好的 skill 要告诉模型失败时怎么办。

例如：

```md
If required context is missing:
- Do not guess aggressively.
- Inspect nearby files first.
- If still unclear, produce assumptions explicitly.

If tests fail:
- Identify whether failure is caused by implementation, test, environment, or requirement ambiguity.
- Do not keep patching blindly more than two iterations.
- Summarize failure and propose next step.
```

差的 skill 只写“确保测试通过”，结果模型会无限修补、扩大改动范围，甚至改测试来让测试通过。

---

## 9. 与其他 skill 有协作边界

你的体系里会有很多 skill。好的 skill 要知道自己和其他 skill 的关系。

例如：

```md
This skill may delegate to:
- superpowers/tdd when implementation requires test-first development
- roadmap when the task affects long-term planning
- eval when semantic correctness cannot be validated by pytest
- memory-sync after meaningful architecture or workflow changes

This skill must not duplicate:
- deterministic testing logic handled by superpowers/tdd
- semantic evaluation handled by eval-skill
```

这个非常适合你现在的 orchestrator 设计。

尤其是你已经明确说过：

> 我的 eval 只负责无法通过 pytest case 验证的语义部分，deterministic 部分交给 superpowers 的 tdd。

那么 skill 就必须把这个边界写进去，否则 evaluator 会和 tdd 抢职责。

---

## 10. 尽量可组合，而不是全能

好的 skill 应该像 Unix 工具一样，可以组合。

例如：

```text
roadmap-skill
  -> openspec-skill
      -> tdd-skill
          -> eval-skill
              -> memory-sync-skill
```

而不是一个 skill 同时做 roadmap、openspec、tdd、eval、memory。

你可以有 orchestrator skill，但 orchestrator 的职责应该是：

1. 判断阶段；
2. 选择 skill；
3. 安排顺序；
4. 维护上下文交接；
5. 做结果检查。

它不应该亲自实现所有细节。

---

## 11. 能控制上下文预算

好的 skill 应该说明：

1. 需要加载哪些文件；
2. 不需要加载哪些文件；
3. 什么情况下加载完整上下文；
4. 什么情况下只读摘要。

例如：

```md
Context loading policy:
- First read README, package config, current spec, and related tests.
- Do not scan the entire repository unless dependency impact is unclear.
- Prefer summaries for archived specs.
- Load full historical roadmap only when planning future milestones.
```

这对你尤其关键，因为你一直在关注：

* skill frontmatter 太多；
* context routing；
* memory 分层；
* LLM 注意力稀释；
* router 是否需要按需加载 skill。

好的 skill 不是“多给上下文”，而是“给刚好足够的上下文”。

---

## 12. 有可测试性

一个优秀 skill 应该能被 eval。

也就是说，你可以设计 case 来判断它是否生效。

例如测试一个 `openspec-lightweight-decision-skill`：

| Case         | 期望行为                              |
| ------------ | --------------------------------- |
| 修一个 typo     | 不创建 OpenSpec change               |
| 新增登录锁定功能     | 创建 OpenSpec change                |
| 修改一个函数的小 bug | 直接走 tdd，不走 proposal               |
| 需求模糊的大功能     | 先 clarify / assumptions，再 propose |
| 用户说“不要改代码”   | 只输出方案，不修改文件                       |

如果一个 skill 无法被测试，说明它大概率太模糊。

---

# 二、急需避免的坏特征

## 1. 职责过大

典型坏味道：

```md
这个 skill 用于帮助用户完成软件开发全流程。
```

这类 skill 看起来强，实际最容易失控。

问题是：

1. 触发范围过宽；
2. 和其他 skill 冲突；
3. 不知道何时停止；
4. 难以 eval；
5. 修改成本高。

建议拆成多个小 skill，再由 orchestrator 组合。

---

## 2. 触发条件模糊

坏例子：

```md
当用户需要帮助时使用本 skill。
```

这等于没有触发条件。

更好的写法是：

```md
Use this skill only when the user asks to design, create, or update a formal OpenSpec change.
Do not use it for small implementation-only edits.
```

---

## 3. 只写原则，不写步骤

坏例子：

```md
遵循最佳实践，保证代码质量，考虑可维护性。
```

这些话没有错，但没有操作性。

更好的写法：

```md
Before implementation:
1. Identify the smallest testable behavior.
2. Add or update a failing test.
3. Run the targeted test.
4. Implement the minimal code.
5. Re-run the test.
6. Refactor only after green.
```

原则要落到流程，否则模型很难稳定执行。

---

## 4. 没有禁止项

很多 skill 只告诉模型“应该做什么”，但不告诉模型“不能做什么”。

这会导致模型越界。

例如你应该明确写：

```md
Do not:
- Start coding during proposal generation.
- Modify unrelated files.
- Rewrite existing architecture unless explicitly requested.
- Mark tasks complete without running the relevant validation.
- Treat semantic eval as a replacement for deterministic tests.
```

“禁止项”对 agent 比“建议项”更重要。

---

## 5. 允许模型过度自主

坏例子：

```md
如果你认为有必要，可以自行创建文件、修改架构、调整测试、更新文档。
```

这会导致模型自作主张。

更好的方式是分级授权：

```md
Allowed without confirmation:
- Read files
- Create draft documents
- Modify files directly related to current task in build mode
- Run local tests

Requires explicit confirmation:
- Delete files
- Change public API
- Modify database schema
- Introduce new framework
- Change CI/CD
- Commit, push, deploy, publish
```

---

## 6. 输出格式不稳定

坏例子：

```md
最后给出总结。
```

“总结”太自由。

更好的方式：

```md
Final response format:
- What changed
- Files touched
- Validation performed
- Remaining risks
- Next recommended action
```

稳定格式会显著提升可复用性。

---

## 7. 和其他 skill 抢职责

例如 eval skill 同时负责 pytest、promptfoo、语义评估、代码修复、roadmap 更新。

这会导致：

1. skill 之间互相覆盖；
2. orchestrator 难以路由；
3. 出错后不知道该修哪个 skill；
4. eval 结果不可信。

你的体系里可以这样分：

| 能力                                 | 应该归属               |
| ---------------------------------- | ------------------ |
| pytest / deterministic test        | Superpowers TDD    |
| 语义一致性 / rubric / golden case       | Eval skill         |
| OpenSpec proposal / design / tasks | OpenSpec skill     |
| 长期版本规划                             | Roadmap skill      |
| 阶段判断 / skill 编排                    | Orchestrator skill |
| 项目经验沉淀                             | Memory skill       |

---

## 8. 把 workflow 写死得过度僵硬

坏 skill 不一定都是太松，也可能太死。

例如：

```md
所有功能开发都必须先创建 OpenSpec change。
```

这会让小修小改变得很重。

更好的方式是做任务分级：

| 任务类型      | 推荐流程                                   |
| --------- | -------------------------------------- |
| tiny      | 直接修改，必要时补测试                            |
| small     | TDD + 简短说明                             |
| medium    | lightweight spec + TDD                 |
| large     | OpenSpec + design + tasks + TDD + eval |
| strategic | roadmap + OpenSpec + eval + memory     |

你的判断是对的：第一步应该定义好自定义任务阶段。没有任务阶段，orchestrator 就没法稳定决策。

---

## 9. 没有 checkpoint / handoff

长任务中，skill 必须要求模型留下交接信息。

例如：

```md
After each major step, update handoff with:
- Current objective
- Completed work
- Pending work
- Key decisions
- Relevant files
- Validation status
- Risks
```

否则 session 一切换，后续模型很难接上。

这也是你之前一直遇到的上下文连续性问题。

---

## 10. 不区分 plan mode 和 build mode

AI-CLI 里这是高危问题。

坏例子：

```md
根据用户需求完成任务。
```

它没有区分“只规划”和“可执行”。

更好的写法：

```md
In plan mode:
- Do not edit files.
- Produce proposal, design, task breakdown, or implementation plan only.

In build mode:
- Edit only files required by the selected task.
- Run relevant validation.
- Report changes and validation results.
```

这可以降低模型在 propose 阶段直接写代码的概率。

---

## 11. 不记录决策依据

坏 skill 只输出结论，不解释为什么。

好的 skill 应该保留关键判断依据，尤其是：

1. 为什么需要 OpenSpec；
2. 为什么不需要 OpenSpec；
3. 为什么要进入 eval；
4. 为什么该任务属于 small / medium / large；
5. 为什么修改某个文件；
6. 为什么某个风险暂不处理。

这对 roadmap、memory、后续复盘都很重要。

---

## 12. 对“不确定”处理不好

坏例子：

```md
如果信息不足，自己根据最佳实践补全。
```

这会制造幻觉。

更好的写法：

```md
When context is insufficient:
- First inspect local evidence.
- Then state assumptions explicitly.
- Prefer reversible changes.
- Do not make irreversible architectural decisions based on assumptions.
```

---

# 三、好的 skill 的检查清单

你可以用这张表审查每个 skill。

| 检查项  | 好 skill 应该满足            |
| ---- | ----------------------- |
| 职责   | 只解决一个明确问题               |
| 触发   | 有 use / do not use 条件   |
| 输入   | 说明需要哪些上下文               |
| 输出   | 格式稳定，可被后续流程消费           |
| 流程   | 有明确步骤，不只是原则             |
| 质量   | 有 completion criteria   |
| 副作用  | 明确哪些操作允许、哪些禁止           |
| 协作   | 知道和其他 skill 的边界         |
| 失败处理 | 知道测试失败、信息不足、冲突时怎么办      |
| 上下文  | 有加载策略，避免全量扫描            |
| 可测试  | 可以设计 case 验证 skill 是否生效 |
| 可维护  | 不把所有逻辑塞进一个超级 skill      |

---

# 四、我建议你的 skill 分层标准

结合你目前的体系，建议分成 4 层。

## 第 1 层：基础能力 skill

负责单一技术动作。

例如：

| Skill                | 职责                 |
| -------------------- | ------------------ |
| `tdd`                | deterministic 测试驱动 |
| `eval`               | 语义评估               |
| `memory-sync`        | 记忆同步               |
| `doc-refresh`        | 技术文章刷新             |
| `diagram-generation` | Markdown 生图        |

这类 skill 应该尽量小、稳定、可测试。

---

## 第 2 层：项目流程 skill

负责某个项目中的标准流程。

例如：

| Skill                      | 职责                                   |
| -------------------------- | ------------------------------------ |
| `openspec-workflow`        | OpenSpec 的 propose / apply / archive |
| `contract-review-workflow` | 合同审查项目的业务流程                          |
| `code-review-workflow`     | AI 代码审查流程                            |
| `roadmap-workflow`         | MVP / V2 / V3 演进流程                   |

这类 skill 可以组合基础能力 skill。

---

## 第 3 层：路由 / 编排 skill

也就是你的 orchestrator。

它的职责不是亲自做事，而是：

1. 判断任务阶段；
2. 判断任务大小；
3. 选择合适 skill；
4. 控制执行顺序；
5. 防止 skill 冲突；
6. 做 handoff；
7. 做结果验收。

---

## 第 4 层：项目记忆 / 规范层

例如：

| 文件                   | 作用            |
| -------------------- | ------------- |
| `AGENTS.md`          | 项目级总规范        |
| `ROADMAP.md`         | 长期规划          |
| `DECISIONS.md` / ADR | 架构决策          |
| `MEMORY.md`          | 项目经验沉淀        |
| `EVALS.md`           | 评估策略与 case 索引 |

skill 不应该把所有长期事实都写进自己内部。长期事实应该放到项目资产里，skill 只负责读取和维护。

---

# 五、最重要的结论

你可以用一句话判断 skill 好不好：

> 好的 skill 是一个有边界、有流程、有验收标准、可组合、可测试的任务执行协议；坏的 skill 是一段很长、很泛、看似聪明但无法稳定复现的提示词。

对你当前体系而言，最应该避免的是这三类：

1. **超级 skill**：什么都管，最后谁都管不好。
2. **无副作用边界的 skill**：plan 阶段乱改代码，proposal 阶段直接 apply。
3. **不可 eval 的 skill**：无法用 case 判断它是否真的提升了 agent 行为。

你现在最优先要做的，不是继续加 skill，而是先定义一套统一的 skill 规格模板。比如每个 skill 都必须包含：

```md
# Purpose
# Use When
# Do Not Use When
# Required Inputs
# Workflow
# Output Format
# Completion Criteria
# Side-effect Policy
# Failure Handling
# Delegation Rules
# Examples
# Eval Cases
```

有了这个模板，你的 skill 体系才会从“提示词集合”升级成“可维护的 agent 操作系统”。
