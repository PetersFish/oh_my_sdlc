---
name: integration-notion-sync
description: Syncs learning notes and conversation summaries from Cursor into a structured Notion Knowledge Base hierarchy. Use when the user wants to archive text to Notion under Knowledge Base with automatic categorization and appending to existing topic pages.
---

# Integration Notion Sync

## Instructions

Use this skill to implement a global `integration-notion-sync` style command that sends the current text (for example, study notes summarized from a chat) into Notion under a `Knowledge Base` root page.

The goal is:
- Default root: a Notion page titled `Knowledge Base`.
- First-level under `Knowledge Base`: category pages (for example `Unix`, `Python`, `Frontend`).
- Second-level inside each category: topic pages (for example `shell`), where multiple related notes are appended into the same page instead of creating many small pages.

### 1. Inputs you should collect

From the user:
- `content` (required): The full text to sync, preferably in Markdown.
- `category_hint` (optional): The expected high-level category, such as `Unix`, `Python`, `Frontend`. If omitted, infer it from the content.
- `topic_hint` (optional): The expected topic name inside the category, such as `shell`, `shell 条件表达式`, `shell 循环语法`. If omitted, infer it from the content.
  - **When `topic_hint` is missing, you MUST prefer a short, reusable topic name (for example `shell`) instead of putting a long “note title” into the page title. Use sub-headings inside the page for finer-grained note titles.**

If `category_hint` is not provided:
1. Analyze `content` to infer a domain category, for example:
   - Shell / Linux / bash / zsh → suggest `Unix`
   - Python code / pip / virtualenv → suggest `Python`
   - HTML / CSS / React / Vue → suggest `Frontend`
   - SQL / transactions / indexes → suggest `Databases`
2. Propose the inferred category name to the user and ask for confirmation before creating a new category page. Example:
   - “检测到内容主要是 shell 编程，建议放在 `Unix` 目录下，可以吗？”

If `topic_hint` is not provided:
1. Generate a concise **topic name that represents the broader knowledge area**, not a single fine-grained note, for example:
   - Prefer `shell` (shell 相关所有基础语法) over `shell 条件表达式与备份脚本`.
   - Prefer `git` over `git reset/checkout 区别`.
2. Inside that topic page, use dated sub-headings to记录具体细分知识点（如 `## [2026-03-05] shell 条件表达式与备份脚本`）。
3. Reuse the same topic name when later content is clearly an extension of the same theme, so that all related notes stay in one Notion page.

Always echo back the final `category` and `topic` you decided to use when you report the result to the user.

### 2. Locating the Knowledge Base root in Notion

Use the `user-notion` MCP server to talk to Notion.

Preferred behavior:
1. If a fixed root page id for `Knowledge Base` has been configured (see `reference.md` for details), use that id directly.
2. Otherwise, search Notion pages by title for a page named `Knowledge Base` and choose the most appropriate match as the root.
3. If no such page exists:
   - Tell the user that a `Knowledge Base` root page is required.
   - Ask the user either to:
     - Create a page named `Knowledge Base` manually in Notion, or
     - Provide an explicit page id to use as the root.
   - Once the user provides a stable page id, it can be recorded in `reference.md` for future runs.

You SHOULD NOT hard‑code any concrete MCP tool names here, because the available tools may vary. Instead, follow this pattern:
- Use a search‑like tool from `user-notion` to find pages by title.
- Use a page‑creation tool to create new pages under a parent page id.
- Use a page‑update or block‑append tool to modify or extend an existing page.

### 3. Finding or creating the category page

With the root page id for `Knowledge Base`:
1. List or search its child pages for a page whose title matches the resolved `category` (for example `Unix`).
2. If a matching category page exists:
   - Use that page id as the category page.
3. If no matching category page exists:
   - Show the user the candidate category name and ask for confirmation:
     - Example: “未在 Knowledge Base 下找到 `Unix` 目录，是否创建一个新的 `Unix` 子页面？”
   - After the user confirms, create a new page under `Knowledge Base` with that title.

Keep the category list flexible. Do not assume a fixed set of categories; reuse existing ones whenever possible.

### 4. Finding or creating the topic page inside the category

Inside the chosen category page:
1. Search its children for a page whose title best matches the resolved `topic`.
   - Example: if the category is `Unix` and the topic is `shell`:
     - Search for `shell`, `Shell`, or other close variants within that category.
2. If a matching topic page exists:
   - Use its page id as the target document and append new content to it.
3. If no matching topic page exists:
   - Create a new page with the `topic` as its title under the category page.
   - When creating a new topic page:
     - Start the body with a top‑level heading like `# Shell` or `# Shell 条件表达式` that mirrors the title.
     - Then write the main `content` below that heading.

When you are unsure whether new content belongs to an existing topic or should use a new topic name:
1. Compare the semantic meaning of the new `content` with the existing topic pages in the same category.
2. If it is clearly a continuation (for example another shell 基础语法点), prefer appending to the existing `shell` page.
3. If it is a distinct topic (for example “Unix 进程管理”), consider creating a new topic page like `进程管理` under `Unix`.
4. In ambiguous cases, ask the user whether to:
   - Append to an existing topic page, or
   - Create a new topic page with a suggested name.

### 5. Appending or writing content into the topic page

If the topic page already exists:
1. Append a new section at the end of the page.
2. This section should typically contain:
   - A dated sub‑heading, for example:
     - `## [2026-03-05] Shell 条件表达式补充`
   - The full `content` text provided by the user, preserving Markdown structure as much as possible.
3. If the content is very small (for example one short note), you may still add a small heading or bullet label to keep the page organized.

If the topic page is newly created:
1. Use the main heading (for example `# Shell`) and write the entire `content` below it.
2. Optionally add a short introductory paragraph that briefly describes the scope of this topic page, inferred from the content.

Avoid rewriting or deleting existing content on the page unless the user explicitly asks for edits. This skill is primarily for appending notes and building a continuous knowledge log.

### 6. Reporting results back to the user

After syncing:
1. Report the full Notion path in a human‑readable way, for example:
   - `Knowledge Base / Unix / shell`
2. Indicate whether:
   - A new category page was created.
   - A new topic page was created.
   - Or existing pages were reused and the content was appended.
3. When possible, also provide the Notion URL of the final topic page so that the user can open it directly.

Keep the final explanation short and focused on:
- Where the note was stored.
- Whether it was appended to an existing page or created as a new page.

## Examples

### Example 1: First shell conditional expressions note

User description:
- “这是我整理的一份关于 shell 编程中条件表达式的学习笔记，帮我同步到 Notion。”

Behavior:
1. Infer category: `Unix`.
2. Ask the user to confirm using `Unix` as the category if it does not already exist.
3. Under `Knowledge Base / Unix`, search for a topic page named `shell`.
4. If no such page exists:
   - Create a new topic page titled `shell`.
   - Use `# Shell` as the first heading in the body and write the full conditional‑expression notes below.
5. Return a message like:
   - “已将笔记同步到 Notion：`Knowledge Base / Unix / shell`，并创建了新的 shell 主题页面。”

### Example 2: Another shell loop syntax note

User description:
- “这是关于 shell 循环语法的笔记，也同步到 Notion，同一个 shell 笔记就行，不要新建文件。”

Behavior:
1. Infer or receive category: `Unix`.
2. Reuse the existing category page `Unix`.
3. Inside `Unix`, find the existing topic page `shell`.
4. Append a new section at the end of the `shell` page:
   - For example:
     - `## [2026-03-05] Shell 循环语法`
   - Then append the new loop‑syntax notes as Markdown.
5. Return a message like:
   - “已将新的 shell 循环语法笔记追加到 Notion：`Knowledge Base / Unix / shell` 页面中。”

### Example 3: Explicit category and topic hints

User provides:
- `category_hint`: `Python`
- `topic_hint`: `虚拟环境与依赖管理`
- `content`: Detailed notes about venv, pip, requirements.txt.

Behavior:
1. Use `Python` as category without needing to infer.
2. Under `Knowledge Base / Python`, find or create a topic page titled `虚拟环境与依赖管理`.
3. If the page exists, append a dated section with the new notes.
4. If it does not exist, create it and write the notes under a main heading such as `# 虚拟环境与依赖管理`.
5. Report the final path and whether the content was appended or newly created.

