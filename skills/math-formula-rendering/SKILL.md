---
name: math-formula-rendering
description: Enforces Markdown math delimiter rules. Use whenever writing or editing mathematical formulas, LaTeX, algorithm analysis, course notes, Markdown, or any chat output containing math expressions.
---

# Math Formula Rendering

## Rule

When writing or editing any Markdown, notes, or chat output containing mathematical formulas:

- Use `$...$` for inline formulas.
- Use `$$...$$` for block formulas.
- Do not use backslash-delimited LaTeX wrappers such as `\(...\)` or `\[...\]`.
- Preserve normal LaTeX commands inside formulas, such as `\sum`, `\frac`, `\Theta`, subscripts, and superscripts.

## Examples

Correct inline:

```markdown
$X_{ij}=1$
```

Correct block:

```markdown
$$
E[X]=\sum_i E[X_i]
$$
```

Incorrect:

```markdown
\(X_{ij}=1\)
\[
E[X]=\sum_i E[X_i]
\]
```
