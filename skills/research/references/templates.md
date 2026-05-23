# Templates

Use these templates when creating or refreshing research artifacts. Keep existing user content when possible and make the smallest correct edit.

## `request.md`

```markdown
# 背景

# 原始需求

# 调研目标

# 范围

## In Scope

## Out of Scope

# 约束条件

# 期望产物

# 成功标准

# 待澄清问题
```

## `solution.md`

```markdown
# <Topic> 调研报告

> 调研时间：YYYY-MM-DD  
> derived_from_run: YYYY-MM-DD-HHmm

## 1. 结论先行

## 2. 背景与问题定义

## 3. 方案总览

| 方案 | 类型 | 优势 | 劣势 | 适配性 | 风险 | 推荐度 |
|---|---|---|---|---|---|---|

## 4. 现成方案对比

## 5. 自实现方案对比

## 6. 推荐路线

## 7. 风险与治理

## 8. 后续行动

## 9. 参考来源

## 10. Knowledge Extraction Candidates

| Candidate | Target Wiki Page | Reason |
|---|---|---|
```

## `meta.yaml`

```yaml
title: <Topic title>
slug: <topic-slug>
status: wishlist
topic_type: evolving
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
last_run: null
derived_from_run: null
tags: []
tools: []
rerun_policy: on_demand
next_review_hint: null
```

Allowed values:

| Field | Values |
|---|---|
| `status` | `wishlist`, `running`, `done` |
| `topic_type` | `one_shot`, `evolving`, `watch` |
| `rerun_policy` | `none`, `on_demand`, `monthly`, `quarterly` |

## Run Snapshot

```text
runs/YYYY-MM-DD-HHmm/
  request.md
  solution.md
  sources.md
  notes.md
  review.md
```

### `runs/<timestamp>/sources.md`

```markdown
# Sources

| Source | URL | Type | Used In Run | Reliability | Notes |
|---|---|---|---|---|---|
```

### `runs/<timestamp>/notes.md`

```markdown
# Notes

## Findings

## Rejected Options

## Open Questions
```

### `runs/<timestamp>/review.md`

```markdown
# Review

## Quality Checks

## User Feedback

## Follow-up Items
```

## `dialogue.md`

```markdown
# Dialogue Log

## YYYY-MM-DD

### User Intent

### Clarifications

### Decisions

### Open Questions
```

## Wiki Candidates

Candidate extraction output should use this table by default and leave `research/wiki/` unchanged:

```markdown
## Knowledge Extraction Candidates

| Candidate | Target Wiki Page | Reason | Source Topic | Confidence |
|---|---|---|---|---|
```
