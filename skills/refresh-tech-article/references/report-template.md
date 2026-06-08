# Refresh Report Template

Use this template when creating a technical article refresh report.

```md
# 技术文章刷新报告

## 源文档

- Path: `<source-path>`
- Refreshed copy: `<versions-path-or-pending>`
- Report: `<report-path>`

## 执行时间

`YYYY-MM-DD HH:mm local time`

## 主题判断

- Main topic:
- Technology stack:
- Target reader:
- Original language and tone:
- Citation style:

## 刷新深度分级

- Mode: `Conservative Refresh` | `Structural Refresh` | `Strategic Refresh`
- Rationale for the chosen mode:
- If escalation from conservative is needed, why:

## 结论摘要

- Overall status: `current`, `partially outdated`, or `substantially outdated`
- Most important refresh decision:
- Highest-risk outdated claim:

## 过时点

| Original claim or section | Current status | Why it changed | Evidence |
|---|---|---|---|

## 当前成熟方案

| Mature approach | Why it is mature | Production considerations | Evidence |
|---|---|---|---|

## 架构与工程化缺口（Structural / Strategic Refresh 时必填）

Evaluate whether the source article is missing production-critical dimensions. Only fill rows where the gap is real and evidence-backed.

| Missing dimension | Why it matters in current practice | Should be added as | Priority |
|---|---|---|---|
| (e.g., Workflow/orchestration) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., Evaluation) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., Guardrails) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., MCP/tool ecosystem) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., RAG architecture) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., Memory/State layering) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., Observability) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., Framework selection) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., Multi-agent patterns) | (evidence) | New section / inline note | High/Med/Low |
| (e.g., Production risks) | (evidence) | New section / inline note | High/Med/Low |

## 前沿探索方向

| Frontier direction | Why it matters | Maturity and risk | Evidence |
|---|---|---|---|

## 争议与不确定性

| Controversy | Competing positions | Practical decision guidance | Evidence |
|---|---|---|---|

## 建议修改

| Source location | Proposed change | Reason | Requires user decision |
|---|---|---|---|

## 吸收外部/新版优势的整合策略（当有参考文章需吸收时填写）

| Source strength to preserve | New strength to import | Integration method |
|---|---|---|
| (e.g., runnable Agent demo code) | (e.g., Workflow-first production guidance) | (e.g., Add after Agent section) |
| (e.g., beginner-friendly tone) | (e.g., Architecture layering) | (e.g., Insert as new Section 2) |

## 结构优化建议

- Keep current structure:
- Recommended restructuring, if any:
- Reason to wait for confirmation before major rewrite:

## 图片与图示刷新建议

If the source document contains any images, diagrams, SVGs, Mermaid blocks, or Markdown image references, audit every reference:

| # | Original reference (line/link) | Status | Recommended action | Needs user confirmation |
|---|---|---|---|---|
| 1 | `!(path/to/image.png)` | Readable / Broken / Obsolete | Keep / Update caption / Regenerate / Replace / Remove | Yes/No |
| 2 | Mermaid block line N | Content now inaccurate | Regenerate with updated data | Yes |

### Image generation approach

- Diagram recommended: `yes` or `no`
- If yes, whether `transform-markdown-svg` should be used after confirmation:

### Rules

- Unreadable images or broken links must be flagged for replacement; do not silently carry them into the refreshed copy.
- When the original image content cannot be identified, describe what the replacement image should convey based on the refreshed article content and model understanding.
- Image generation or insertion still requires user confirmation before any tools are invoked.

## 来源与证据

| Source | Type | Date or version signal | Supports | URL |
|---|---|---|---|---|

## 待用户确认事项

- Confirm whether to generate the refreshed copy.
- Confirm any major structure optimization.
- Confirm any diagram or image generation/replacement.
- Confirm source write-back only after reviewing the refreshed copy.

## 同步落地点（供 Post-Generation Sync Check 使用）

每条 `建议修改` 建议附带预期落地点，使后续的 Report-to-Copy Sync Check 可以精确定位：

| Source location | Proposed change | Expected landing in refreshed copy | Requires user decision |
|---|---|---|---|
| (e.g., Section 2) | (change) | (e.g., "Section 2, `Python 3.10` mention") | 否/是 |

Expected landing 填写为文章中的位置描述，如：
- `Section 2, after install commands`
- `New section 8.6, first code block`
- `Section 6.3, `InMemorySaver` import line`
- `Footer, migration table row`
```

Keep the report evidence-oriented. Do not turn it into the refreshed article itself.
