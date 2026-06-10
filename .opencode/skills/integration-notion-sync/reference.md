# integration-notion-sync Reference

This file documents configuration details and assumptions for the `integration-notion-sync` skill.

## Knowledge Base root page

- The default root of the knowledge hierarchy is a Notion page titled `Knowledge Base`.
- If your workspace already has such a page, the skill should prefer using that page as the root.
- If you want to ensure a stable and unambiguous root, you can record the page id here for reference.

Example (do not hard‑code real secrets into this file if it is shared):

```text
KB_ROOT_PAGE_ID = "<your-knowledge-base-root-page-id>"
```

When this id is known:
- The agent should use this id as the parent when searching for or creating category pages.
- Title‑based search for `Knowledge Base` can be used as a fallback if the id is not configured.

## Common categories

You can optionally keep notes here about common or pre‑existing category pages to guide the agent’s choices.

Examples:

- `Unix` — for shell, bash, zsh, Linux 命令行、终端使用等内容。
- `Python` — for Python 语法、标准库、虚拟环境与依赖管理等内容。
- `Frontend` — for HTML/CSS/JavaScript/React/Vue 等前端相关内容。
- `Databases` — for SQL、索引、事务、数据库调优等内容。

These names are suggestions only. The agent should always:
- Prefer reusing existing child pages under `Knowledge Base` whose titles match the category.
- Ask the user before creating a brand‑new category page when in doubt.

