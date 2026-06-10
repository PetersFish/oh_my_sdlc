---
name: transform-algo-render
description: Provides a reusable algorithm section template with core process summary, pseudocode rendering using Obsidian callouts, and complexity analysis. Use when output needs algorithm summaries, pseudocode blocks, or running time statements in markdown.
---

# transform-algo-render

## When to use

Use this skill whenever the output needs a reusable algorithm section template, including:

- Core process summary (2-5 bullets)
- Pseudocode rendering with stable markdown/html layout
- Running time statement and reasoning bullets

Typical use cases:

- Chapter summaries with an algorithm section
- Assignment solutions that include pseudocode
- Any markdown that must render algorithm steps without list-marker glitches

## Output contract (single source of truth)

Every algorithm section should follow this structure:

1. **Core process**: 2-5 concise bullets for main flow and edge conditions.
2. **Pseudocode block**: exactly one Obsidian callout block per algorithm using `> [!pseudo]`.
3. **Complexity fields**:
   - **Running Time / 时间复杂度:** $O(...)$
   - **Reasoning / 复杂度说明:** 1-3 bullets explaining the dominant operations.

## Language policy

- Pseudocode keywords, function names, and variables must be in English.
- Comment language follows body language:
  - Chinese body -> Chinese comments
  - English body -> English comments

## Formula rendering policy

- Use `$...$` for inline algorithm and math expressions (for example, `$dist[*] \leftarrow -1$`, `$Adj[v]$`, `$areAdjacent(v,u)$`).
- Do not use backticks for mathematical variables, assignments, tuples, comparisons, or pseudocode state updates.
- Keep backticks only for literal markdown syntax examples (for example, ``> [!pseudo]`` or `> - step`).
- Before/after example: use `$dist[start] \leftarrow 0$` (correct), not plain-text "dist[start] <- 0" (incorrect).

## Pseudocode rendering template (must use)

> [!pseudo]
> **Algorithm** name(params)
> - **Input:** ...
> - **Output:** ...
> 
> - step 1
> - step 2
> - **if** condition **then** ...
>   - do something
> - **else** ...
>   - do something

Use Obsidian callout + blockquote list syntax for steps inside the callout.

## Complexity template

**Running Time / 时间复杂度:** $O(...)$

**Reasoning / 复杂度说明:**

- [dominant operation and count]
- [why data structure / loop yields this bound]
- [optional: why this bound is tight or acceptable]

