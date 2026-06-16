# evalops-skill Design

## Context

在 AI Native 开发中，Skill、Agent Workflow、Prompt、模型版本都会持续变化。传统 TDD 验证代码行为，但无法回答：

- Skill 输出质量是否变好？
- 改 Prompt 后是否退化？
- 换模型后是否遵守输出规范？
- 之前翻车的问题是否再次出现？

需要引入 Eval 体系作为横切能力。本设计定义 `evalops-skill` 的资产模型、命令契约、工作流集成和 MVP 边界。核心结论：Eval 的核心资产不是工具，而是 Coverage Matrix + Case Collection + Golden Dataset + Failure Root Cause Analysis；工具可替换，高质量 Eval 数据是长期资产。

## Goals / Non-Goals

**Goals (MVP):**

- 初始化 `evals/` 目录结构和元数据
- 为任意 target（skill/agent/workflow/rag/project）定义 coverage matrix
- 捕获真实失败/边界案例到 inbox
- 基于 coverage 生成候选 case（严格门禁：coverage 必须用户先确认）
- 整理 inbox case（accept/reject/revise/merge）
- 将 accepted case 提升为 golden regression case（需人工确认）
- 导出 Promptfoo 配置并运行 golden eval
- 保存 run report

**Non-Goals (MVP):**

- DeepEval / OpenAI Evals / LangSmith 原生运行
- 完整 diagnose-failure / suggest-fix / apply-fix 闭环
- CI 集成
- 自动修复 skill / prompt
- 全量 dashboard
- 自动生成 golden case（golden 必须人工确认）

## Decisions

### D1: 命名 evalops-skill，前缀 sdlc-evalops

定位为 meta-skill 体系一员，和 meta-skill-lifecycle-governance 平行。`evalops-` 前缀表明它是 Eval 操作横切能力，不绑定单一评测工具。

### D2: 内部 Case Schema 是 source of truth，Promptfoo 是派生产物

不直接维护 `promptfooconfig.yaml` 作为唯一数据源。内部使用中立 YAML schema，通过 `/evalops:run` 自动导出 Promptfoo 配置。后续接入 DeepEval / OpenAI Evals 时只需增加导出映射。

### D3: Coverage Matrix 是 case 生成的前置门禁

`/evalops:generate-cases` 必须在 coverage 已存在且用户已确认后才执行。如果没有 coverage 或 coverage 未 review，必须先进入 `/evalops:define-coverage` 流程。

### D4: Golden Dataset 必须人工确认

AI 生成的 case 只能进入 inbox。从 inbox 到 accepted 需要 triage。从 accepted 到 golden 需要 promote 及用户显式确认。Golden Dataset 不会被 AI 自动污染。

### D5: target-id 泛化支持多种 target type

格式 `<target-type>.<name>`，例如 `skill.research-general`、`agent.contract-review`、`project.checkout-api`。避免把体系锁死在 skill 上。

### D6: Eval 失败不自动触发修复

第一版 run 失败后不自动修改 skill/case/coverage。失败原因可能是 target、case、expected、evaluator、上下文、工具调用或模型波动，必须先诊断再修复。

## Risks / Trade-offs

**Risk 1: 初期 case 积累慢**
- 缓解: coverage matrix 驱动 AI 生成候选 + 真实失败回流 inbox，两条路径并行
**Risk 2: 用户跳过 triage 直接把 AI case 当 golden 用**
- 缓解: skill 内硬编码 promoter 检查链，技术手段阻止 inbox → golden 直接跳转
**Risk 3: Promptfoo assert 映射不完整**
- 缓解: 第一版只映射 contains/not-contains/llm-rubric/regex，复杂 assertion 标记为 unsupported 而非静默跳过
**Risk 4: 目录扩散后 case 难以全局管理**
- 缓解: `metadata/target-index.yaml` 作为全局导航；后续可加 CLI 子命令做全局统计

## Architecture

### 目录结构

```
evals/
  coverage/
    <target-id>.yaml

  cases/
    inbox/
      <target-id>/
    accepted/
      <target-id>/
    rejected/
      <target-id>/
    golden/
      <target-id>/

  exports/
    promptfoo/
      <target-id>/
        promptfooconfig.yaml
        cases.yaml

  reports/
    runs/
      <run-id>/
        summary.md
        promptfoo-output.json
        failures.yaml
    diagnosis/

  metadata/
    target-index.yaml
    eval-policy.yaml
```

### 数据模型

### Coverage Matrix (`evals/coverage/<target-id>.yaml`)

```yaml
target:
  id: skill.research-general
  type: skill
  path: skills/research-general/SKILL.md

coverage:
  functional:
    - problem_understanding
    - architecture_research
    - tradeoff_analysis
    - risk_analysis
    - implementation_plan
  quality:
    - completeness
    - specificity
    - actionability
    - evidence_grounding
  edge_cases:
    - ambiguous_request
    - conflicting_requirements
    - insufficient_context
    - overbroad_request
  output_constraints:
    - markdown_structure
    - no_unverified_claims
    - explicit_assumptions

risk_focus:
  critical_failures:
    - misses_cost_analysis
    - recommends_single_tool_without_tradeoff
    - skips_implementation_path

review:
  status: draft
  reviewed_by_user: false
  last_reviewed_at: null
```

### Eval Case (`evals/cases/{inbox,accepted,rejected,golden}/<target-id>/<case-id>.yaml`)

```yaml
id: skill.research-general.failure.cost-analysis-001

target:
  id: skill.research-general
  type: skill
  path: skills/research-general/SKILL.md

status: inbox          # inbox | accepted | rejected | golden
case_type: failure     # failure | regression | golden_candidate | edge | positive | negative
source: observed       # manual | observed | eval_failure | ai_suggested
severity: high         # critical | high | medium | low
created_at: 2026-06-07

coverage:
  functional:
    - tradeoff_analysis
    - cost_analysis
  quality:
    - completeness
    - actionability

input: |
  请调研 Agent Workflow 架构选型，并给出落地建议。

actual: |
  只推荐了 LangChain，没有比较其他方案，也没有成本分析。

expected:
  must_include:
    - 至少比较两种 workflow/orchestration 方案
    - 明确说明成本影响
    - 说明风险和落地步骤
  must_not_include:
    - 只推荐单一框架而不做取舍
  rubric: |
    回答应覆盖技术方案、取舍、风险、成本和实施路径。

evaluators:
  rule_based:
    contains:
      - 成本
      - 风险
      - 取舍
  llm_judge:
    enabled: true
    rubric: |
      判断回答是否完成架构选型所需的成本、风险和实施分析。
```

### Eval Policy (`evals/metadata/eval-policy.yaml`)

```yaml
default_runner: promptfoo
golden_requires_human_approval: true
ai_generated_cases_default_status: inbox
coverage_review_required_before_generation: true
```

### Target Index (`evals/metadata/target-index.yaml`)

```yaml
targets:
  - id: skill.research-general
    type: skill
    path: skills/research-general/SKILL.md
    coverage: evals/coverage/skill.research-general.yaml
    golden_count: 0
    inbox_count: 0
    last_run_at: null
    last_run_passed: null
```

## Interaction Model

### Invocation Modes

The slash-style command names (`/evalops:init`, `/evalops:capture`, etc.) are **capability names**, not the required user interface. The LLM SHOULD orchestrate them from natural-language intent. Manual invocation remains available for precise control.

**Mode 1: Natural-language orchestration (primary)**

The user expresses intent in natural language. The LLM selects and chains commands:

```
user: "帮 research-general 建一套 eval"
LLM: 编排 init → define-coverage → generate-cases → 用户审查 → triage → promote → run

user: "这次输出不符合预期，帮我沉淀成回归 case"
LLM: 编排 抽取上下文 → 用户确认 → capture → triage accept

user: "我改完了，跑一下相关 eval"
LLM: 编排 定位 target → 确保 golden 存在 → export promptfoo → run → summarize
```

**Mode 2: Explicit command invocation (fallback)**

用户可以直接调用命令做精确控制：

```
/evalops:capture skill.research-general
/evalops:triage skill.research-general
/evalops:run skill.research-general
```

**Mode 3: Proactive capture suggestion**

LLM 主动识别可捕获的失败并建议落盘：

- 当用户指出 skill 表现不好
- 当用户说“这次翻车了”
- 当用户纠正了 AI 输出
- 当 eval run 出现失败
- 当 code review 发现 AI 工作流遗漏要求
- 当 OpenSpec verify 发现行为偏差

LLM SHOULD proactively suggest capture, but MUST ask before writing the case to disk.

### High-Level Workflows (LLM-Orchestrated)

The skill exposes three high-level workflow patterns. Each is a natural-language entry point that the LLM maps to the underlying 7 commands.

#### 1. create-eval-suite

Goal: establish a complete eval suite for a target.

```
check evals/ initialized (init if needed)
→ check target-index entry
→ check coverage exists and reviewed
→ if not: define-coverage with user brainstorming
→ user confirms coverage
→ generate-cases to inbox
→ present candidate summary
→ ask user: iterate, accept selected, or stop?
→ triage accepted
→ promote to golden
→ run golden eval
→ summarize
```

#### 2. capture-regression

Goal: capture a real failure or edge case for future regression protection.

```
extract input/actual/expected from conversation context
→ present draft to user for confirmation
→ capture to inbox
→ optionally triage accept (if user wants immediate acceptance)
→ remind: promote is a separate step for golden
```

#### 3. run-regression

Goal: run evaluation against one or more targets and summarize results.

```
locate target via target-index or user hint
→ ensure golden cases exist under evals/cases/golden/<target-id>/
→ export promptfoo config
→ call promptfoo eval
→ save run report
→ summarize: pass/fail counts, failed cases, severity breakdown
→ if failures: suggest capture for new failure patterns, do NOT auto-fix
```

## Commands

The 7 commands below are the internal capability API. The Interaction Model above defines how the LLM orchestrates them from user intent.

### 1. `/evalops:init`

**用途**: 初始化项目 `evals/` 资产目录

**输入**:
- target root path
- optional: target types to support (default all)
- optional: default runner (fixed to promptfoo in MVP)

**输出**:
```
evals/
  coverage/
  cases/inbox/ accepted/ rejected/ golden/
  exports/promptfoo/
  reports/runs/ diagnosis/
  metadata/target-index.yaml
  metadata/eval-policy.yaml
```

**行为边界**:
- 创建目录和基础 metadata
- 不创建具体 case
- 不自动扫描所有 skill/project target
- 不运行 Promptfoo

### 2. `/evalops:define-coverage`

**用途**: 为 target 定义或迭代 coverage matrix

**输入**:
- target-id (e.g. `skill.research-general`)
- target type
- target source path
- user intent / quality concerns
- optional: existing failures
- optional: existing docs/specs

**输出**: `evals/coverage/<target-id>.yaml`

**行为边界**:
- 必须和用户头脑风暴 coverage 范围
- 必须让用户确认方向，`review.reviewed_by_user` 置为 true
- coverage 未确认时，generate-cases 不可执行
- 允许覆盖已有 coverage 进行迭代更新

### 3. `/evalops:capture`

**用途**: 捕获真实失败、优秀输出、边界输入

**输入**:
- target-id
- case type (failure|regression|golden_candidate|edge|positive|negative)
- user input
- expected behavior
- actual output (optional)
- failure reason (optional)
- severity (critical|high|medium|low)
- source (manual|observed|eval_failure|ai_suggested)
- coverage mapping (optional)

**输出**: `evals/cases/inbox/<target-id>/<case-id>.yaml`

**行为边界**:
- 默认进入 inbox
- 不能直接进入 golden
- 即使描述为"高价值回归 case"，最多进入 accepted，promote 单独执行
- The assistant SHOULD proactively suggest capture when it detects a reusable failure, but MUST ask before writing the case to disk
- 允许从 OpenCode 对话上下文抽取 input/actual，但需用户确认

### 4. `/evalops:generate-cases`

**用途**: 基于 coverage matrix 和已有 case 生成候选 case

**输入**:
- target-id
- generation focus (optional)
- case count (optional)
- case types (optional)
- coverage dimensions to expand (optional)
- existing cases to avoid duplicates

**输出**: `evals/cases/inbox/<target-id>/candidate-*.yaml`

**强门禁**:
```
if evals/coverage/<target-id>.yaml 不存在:
  stop, 进入 define-coverage

if coverage.review.reviewed_by_user != true:
  stop, 要求用户 review/refine coverage 后再执行

if coverage reviewed:
  生成候选 case 到 inbox
```

**生成后必须询问用户**:
- 是否继续迭代某个 coverage 方向？
- 是否删除同质化 case？
- 是否补充真实失败类 case？
- 是否把部分 candidate 标记为 accepted？

**行为边界**:
- 只生成 candidate，不运行 eval
- 不修改 golden
- 不自动接受自己的输出
- 尽量基于 coverage gaps、真实 failure、已有 case 扩展，而非凭空生成大量通用 case
- AI 生成的 case 永远不能直接进入 golden

### 5. `/evalops:triage`

**用途**: 整理 inbox case

**输入**:
- target-id
- case-id or batch selector
- action (accept|reject|revise|merge|split|defer)
- reason
- optional edits to expected/rubric/coverage

**输出**:
- `evals/cases/accepted/<target-id>/<case-id>.yaml`
- `evals/cases/rejected/<target-id>/<case-id>.yaml`
- 或更新 inbox case

**行为边界**:
- triage accept 不等于 golden
- reject 保留原因
- merge/split 避免丢失来源信息
- accepted case 必须满足 expected、rubric、coverage 至少基本完整

### 6. `/evalops:promote`

**用途**: 将 accepted case 提升为 golden regression case

**输入**:
- target-id
- case-id or selected accepted cases
- final expected
- final rubric
- evaluator strategy
- coverage mapping
- human approval

**输出**: `evals/cases/golden/<target-id>/<case-id>.yaml`

**Promote 前检查**:
```
status == accepted
expected.must_include 或 expected.rubric 非空
coverage 非空
severity 非空
evaluators 至少包含 rule_based / schema / llm_judge / human_review 中一种
用户明确确认 promote
```

**行为边界**:
- 不能 promote inbox case，必须先 triage accept
- 不能 promote AI 未经确认生成的 candidate
- 不能因为 Promptfoo 能跑就视为 golden 合格

### 7. `/evalops:run`

**用途**: 运行某个 target 的 golden eval（第一版只支持 Promptfoo）

**输入**:
- target-id
- optional: provider/model
- optional: case selector
- optional: changed-only
- optional: dry-run

**内部步骤**:
```
1. 读取 evals/cases/golden/<target-id>/
2. 读取 evals/coverage/<target-id>.yaml
3. 生成 exports/promptfoo/<target-id>/promptfooconfig.yaml
4. 生成 exports/promptfoo/<target-id>/cases.yaml
5. 调用 promptfoo eval
6. 保存结果到 reports/runs/<run-id>/
7. 输出失败摘要和下一步建议
```

**输出**:
```
evals/exports/promptfoo/<target-id>/promptfooconfig.yaml
evals/exports/promptfoo/<target-id>/cases.yaml
evals/reports/runs/<run-id>/summary.md
evals/reports/runs/<run-id>/promptfoo-output.json
evals/reports/runs/<run-id>/failures.yaml
```

**行为边界**:
- 只运行 golden，默认不运行 inbox/accepted
- 运行失败不自动修改 skill/case
- 失败后建议用户进入 future `diagnose` 流程
- 第一版生成 failure summary，但不实现完整 root cause diagnosis

## Promptfoo Export Mapping

内部 case schema 到 Promptfoo 的映射规则:

| 内部字段 | Promptfoo 映射 |
|---------|---------------|
| `input` | test input / `vars.input` |
| `expected.must_include` | `assert: contains` |
| `expected.must_not_include` | `assert: not-contains` |
| `expected.rubric` | `assert: llm-rubric` |
| `evaluators.rule_based.contains` | `assert: contains` |
| `coverage / severity / case_type` | metadata |

第一版支持的 Promptfoo assertions:
- `contains`
- `not-contains`
- `regex` (optional)
- `llm-rubric`
- `javascript` (optional)

## Design Principles (Hard Rules)

```
Coverage Matrix is the planning layer for eval cases.
AI-generated cases MUST enter inbox first.
Golden Dataset MUST require human confirmation.
Coverage MUST be user-reviewed before candidate generation.
Promptfoo exports are derived artifacts, not source of truth.
Eval failure MUST NOT trigger automatic fixes in MVP.
Failure may indicate target, case, evaluator, context, tool, or model issues.
```

## Workflow Integration

### OpenCode + Superpowers

```
brainstorming → coverage/case 方向确认
test-driven-development → 代码行为验证
evalops-skill → AI 行为回归验证
meta-skill-lifecycle-governance → release 前 EVALUATE-IN-REPO
verification-before-completion → 完成前说明 eval 是否已跑
```

### OpenSpec

```
openspec propose → design → spec → tasks
→ apply + TDD
→ evalops:run affected targets
→ verify
→ memory sync
→ archive
```

### Skill Lifecycle

```
DEVELOP → EVALUATE-IN-REPO (run golden eval)
→ PILOT-IN-PROJECT (capture 真实失败到 inbox)
→ BACKPORT (通用失败 case 回流 canonical repo)
→ RELEASE (通过关键 golden eval)
→ DISTRIBUTE
```

## MVP Scope Summary

| 包含                    | 不包含                            |
| --------------------- | ------------------------------ |
| init                  | diagnose-failure 完整版           |
| define-coverage       | suggest-fix                    |
| capture               | apply-fix                      |
| generate-cases (门禁严格) | DeepEval runner                |
| triage                | OpenAI Evals runner            |
| promote (人工确认)        | LangSmith/Langfuse integration |
| run (Promptfoo)       | CI automation                  |
| promptfoo export (自动) | 自动修复 skill                     |
| run report 保存         | dashboard                      |
