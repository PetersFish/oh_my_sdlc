你这个 skill 库已经出现一个典型信号：

> skill 已经从“几个临时 prompt”演进成“平台级能力层”。

这时候继续纯平铺，会出现两个问题：

1. 人类认知负担上升
2. AI 触发边界开始模糊

但你现在还没到“必须 DSL 化 / skill registry 化”的阶段。

你目前最适合的是：

> “逻辑分层 + 命名前缀 + 生命周期治理”

而不是物理嵌套目录。

---

# 我对你当前 skill 的语义分组建议

我会把它拆成 6 个能力域：

---

# 1. SDLC / OpenSpec Workflow

核心目标：

> 管理需求 → 设计 → 实现 → 记忆同步 → 验证 的开发生命周期

建议：

```text
sdlc-openspec-memory-sync
sdlc-repository-memory-init
sdlc-repository-memory-load
sdlc-repository-memory-sync
sdlc-skill-lifecycle-governance
```

你现在：

```text
openspec-memory-sync
repository-memory-init
repository-memory-load
repository-memory-sync
skill-lifecycle-governance
```

问题：

* repository-memory-* 实际属于 SDLC infra
* openspec-memory-sync 本质是 workflow hook
* governance 也是 infra

AI 不容易感知它们属于同一个体系。

---

# 2. Research / Architecture

核心目标：

> 调研、架构设计、方案推导

建议：

```text
research-general
research-ai-architecture
```

对应：

```text
research
ai-architecture-coach
```

这里我会进一步建议：

---

## ai-architecture-coach 不建议叫 coach

因为：

```text
coach
assistant
helper
expert
advisor
```

这些名字都太人格化。

AI 更容易误判 skill 边界。

更推荐：

```text
research-ai-architecture
architecture-review
architecture-tradeoff-analysis
```

skill 名字最好体现：

* 输入
* 输出
* 边界

而不是人格。

---

# 3. Rendering / Transformation Pipeline

这是你当前最值得抽象的一层。

你已经出现：

```text
algo-render-core
markdown-svg-generator
math-formula-rendering
convert-xmind
ocr-router
```

它们本质都是：

> 输入结构 → 转换 → 渲染

我会统一为：

```text
transform-algo-render-core
transform-markdown-svg
transform-math-formula
transform-xmind
transform-ocr-router
```

这样 AI 会天然理解：

```text
这是一组 transformation pipeline
```

而不是几个 unrelated tools。

---

# 4. External Integration

```text
sync-notion
zybook-assist
```

建议：

```text
integration-notion-sync
integration-zybook
```

原因：

integration 是非常强的语义边界。

AI 会知道：

* 会访问外部系统
* 可能涉及 API
* 可能有同步副作用

这很重要。

---

# 5. System / Ops

```text
mackup-backup
```

建议：

```text
ops-mackup-backup
```

以后：

```text
ops-dotfiles
ops-homebrew
ops-env-bootstrap
```

会非常清晰。

---

# 6. Meta Skills（未来会越来越重要）

你现在其实已经隐约有了：

```text
skill-lifecycle-governance
```

未来建议单独形成：

```text
meta-skill-governance
meta-skill-audit
meta-skill-refactor
meta-skill-docgen
```

这是：

> “管理 skill 系统本身的 skill”

后面你 skill 多了以后，这层会非常关键。

---

# 推荐的最终结构（逻辑语义）

虽然物理目录还是平铺：

```text
skills/
  sdlc-openspec-memory-sync
  sdlc-repository-memory-init
  sdlc-repository-memory-load
  sdlc-repository-memory-sync

  research-general
  research-ai-architecture

  transform-algo-render-core
  transform-markdown-svg
  transform-math-formula
  transform-xmind
  transform-ocr-router

  integration-notion-sync
  integration-zybook

  ops-mackup-backup

  meta-skill-governance
```

---

# 为什么这个结构对 AI 更友好

因为 LLM 对：

```text
prefix clustering
```

极其敏感。

例如：

```text
transform-*
```

模型会自然推断：

* 这些 skill 是一类
* 输入输出可能类似
* 适合一起组合

这比：

```text
markdown-svg-generator
math-formula-rendering
convert-xmind
```

强很多。

---

# 你现在最大的潜在风险

不是 skill 太多。

而是：

> “skill 边界开始变得不清晰”

例如：

```text
research
ai-architecture-coach
```

已经有 overlap。

以后会出现：

* AI 同时触发多个 skill
* skill instruction 冲突
* skill chaining 混乱
* token 浪费

所以你下一阶段最应该做的是：

# skill taxonomy（技能分类体系）

而不是：

# skill nesting（目录嵌套）

这是两个完全不同的问题。

---

# 我建议你下一步增加两个治理机制

---

# 1. capability tags

每个 skill：

```yaml
---
name: transform-markdown-svg
category: transform
capabilities:
  - markdown
  - svg
  - rendering
inputs:
  - markdown
outputs:
  - svg
---
```

这会显著提升 AI routing。

---

# 2. anti-trigger rules

这是很多 skill 系统没有做的。

例如：

```yaml
do_not_use_when:
  - user asks for system architecture
  - task requires repository-wide refactor
```

否则：

skill 越多，
误触发越严重。
