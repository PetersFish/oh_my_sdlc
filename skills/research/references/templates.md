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

## 1. One-Sentence Real Question

用一句话压缩本次研究真正要回答的问题，并标注问题类型：concept definition、causal mechanism、real-world application、controversy judgment、actionable recommendation。

## 2. Elevator Explanation

用一到两分钟能讲清楚的话解释结论。默认读者是普通大学生：通俗但不浅薄。

## 3. Provocative Thesis

写一句有冲击力但不夸大的判断。它应该帮助读者重新看待问题，而不是制造标题党。

## 4. Current Scientific Understanding

概括当前科学理解、经典理论、代表人物和关键英文术语。区分强证据、弱证据和合理推测。

## 5. Consensus, Controversies, and Misconceptions

| Type | Claim | Evidence | Notes |
|---|---|---|---|
| Consensus |  |  |  |
| Controversy |  |  |  |
| Misconception |  |  |  |

## 6. Cross-Disciplinary Map

从多个学科连接概念，不做百科式罗列。可选视角：Complex Systems、Information Theory、Evolutionary Theory、Behavioral Economics、Cognitive Science。

| Lens | What It Explains | Key Terms |
|---|---|---|

## 7. Cases and Applications

用案例说明理论如何进入现实生活、组织、产品、公司、政策或个人决策。

## 8. Deeper Insight

提炼更深层的洞见、类比、格言式表达或可传播金句。保持可辩护，不牺牲准确性。

## 9. Practical Applications

列出可以落地到生活、学习、工作或决策中的应用。说明适用边界。

## 10. Reference Sources

| Source | URL | Type | Reliability | Used For |
|---|---|---|---|---|

## 11. Knowledge Extraction Candidates

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
