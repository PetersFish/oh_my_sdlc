# Rewrite and Write-Back Policy

Use this policy before writing refreshed article content or overwriting a source document.

## Mode Confirmation Policy

Before writing refreshed article content in ANY mode, you MUST present the user with mode choices and get explicit confirmation:

1. **Classify** the required refresh depth based on source document analysis.
2. **Present** all three modes with the recommended one clearly marked:

   ```md
   ## Refresh Depth Mode Selection

   | Mode | Recommendation | What it allows |
   |---|---|---|
   | Conservative Refresh | ✅ Recommended | Patch outdated facts/APIs only; keep structure and tone |
   | Structural Refresh | — | Add missing modern sections; keep original progression |
   | Strategic Refresh | — | Restructure outline; upgrade target-reader level |

   **Recommendation rationale**: <brief evidence-backed reason>

   Please confirm which mode to use.
   ```

3. **Wait** for user confirmation before writing refreshed content. Research may proceed in parallel while awaiting confirmation, but the refreshed copy must NOT be generated until the mode is confirmed.
4. **Do not** treat "直接刷新" / "directly refresh" as consent to skip mode selection. These keywords select the workflow mode but do NOT replace refresh depth confirmation.
5. If the user explicitly names a mode (e.g., "Conservative Refresh"), honor it directly without re-presenting the table.

## Image Refresh Policy

When the source document contains images, diagrams, SVG embeds, Mermaid blocks, Obsidian image links, or Markdown `![...](...)` references:

1. **Audit** every image reference during source reading. List them in the report under 图片与图示刷新建议.
2. **Evaluate** each image against the refreshed content:
   - Is the image still accurate and relevant after content changes?
   - Is the image file accessible and readable?
   - Is the image link still valid?
3. **Classify** each image into one of these statuses:

   | Status | Action |
   |---|---|
   | Image is readable and content still matches | Keep with updated caption/context if needed |
   | Image is readable but content is now inaccurate | Regenerate with updated content |
   | Image link is broken, file is missing, or content is unreadable | Generate a replacement based on refreshed content and model understanding |
   | Image is entirely obsolete (removed topic) | Remove and note in report |

4. **For images that need regeneration or replacement:**
   - If the image is a diagram, architecture, or flowchart, invoke `transform-markdown-svg` for generation after user confirmation.
   - If the image is a screenshot or raster illustration, describe the replacement in the report and ask the user whether to proceed.
   - Always ask for user confirmation before generating or inserting images, per existing skill constraints.
5. **Do not** silently keep broken or unreadable image links in the refreshed copy. Replace or remove them with explicit notes in the report.
6. When the original image content cannot be identified (e.g., external link is dead), describe what the replacement image should convey based on the refreshed article content and model understanding of the topic.

## Refresh Depth Modes

The skill supports three refresh depths. Apply the correct policy per mode:

### Conservative Refresh (default for most articles)

- Scope: patch outdated API calls, version numbers, package names, deprecation warnings, and factual errors.
- Preserve the source document language, tone, target reader, and existing structure.
- Preserve the original citation style when it exists.
- If the source has no citations, keep the refreshed article clean and put sources in the report.
- Improve terminology, technical accuracy, outdated wording, and paragraph flow when needed.
- Keep mature recommendations separate from frontier exploration.
- Avoid marketing language and unsupported certainty.

### Structural Refresh

- All Conservative Refresh rules apply, plus:
- Keep the original progression and tone; add new sections where gaps exist.
- Reorder minor parts if the original flow would confuse a modern reader.
- Run Architecture Gap Analysis (see SKILL.md) before writing.
- Propose new section insertions in the report; wait for confirmation before writing.
- The result should still feel like the original article with additions, not a completely different document.

### Strategic Refresh

- All Structural Refresh rules apply, plus:
- May restructure the outline to match current mature practice (e.g., demo tutorial → production architecture guide).
- May upgrade the target reader level.
- May change the thesis statement and learning path.
- Preserve the source article's strongest traits: runnable code, progressive learning curve, original tone, hands-on project continuity.
- When absorbing external strengths, add named sections rather than dispersing them through existing prose; the reader should still recognize the original article's DNA.
- If the integration would make the article too long, propose splitting into a multi-part series in the report.
- The report MUST include Integration Strategy before the refreshed copy is written.

## Conservative Refresh Default (legacy — maintained for backward compatibility)

- Preserve the source document language.
- Preserve the target reader and overall tone.
- Preserve the existing structure unless it blocks accurate technical refresh.
- Preserve the original citation style when it exists.
- If the source has no citations, keep the refreshed article clean and put sources in the report.
- Improve terminology, technical accuracy, outdated wording, and paragraph flow when needed.
- Keep mature recommendations separate from frontier exploration.
- Avoid marketing language and unsupported certainty.

## Integration Strategy Policy

When the refresh must absorb strengths from an external reference:

| Rule | Description |
|---|---|
| Named sections | Import heavyweight architecture/methodology content as named sections, not inline prose rewrites. |
| Preserve DNA | The reader should still recognize the original article's tutorial voice, runnable code, and learning progression. |
| Practical-first | Put runnable code before abstract architecture; demo before theory. |
| Split if needed | If the integrated result exceeds the original by >2x, propose a multi-part series. |
| Evidence-required | Every imported strength must be backed by Tavily research, not just the external reference's claims. |

## Structure Changes

- **Conservative mode**: Do not perform restructuring. Propose it in the report if the structure blocks accuracy, and wait for confirmation.
- **Structural mode**: Add missing sections while keeping the original progression. Propose the new section plan in the report; do not rewrite the entire outline.
- **Strategic mode**: Restructure the outline only after the report shows the gap analysis, integration strategy, and proposed new TOC. Wait for explicit user confirmation before applying the new outline.

## Source Strength Preservation

Regardless of refresh depth, these traits must survive:

- Runnable code examples that the reader can copy and execute.
- Progressive learning curve (simple → complex).
- The article's original tone and language.
- Hands-on project continuity (the demo project should still work end-to-end after refresh).
- Beginner-friendly explanations for core concepts, even when adding advanced sections.

When adding advanced content (architecture, evaluation, governance), layer it as new sections after the core tutorial, not as replacements for the core tutorial.

## Citation Handling

- If the source uses footnotes, continue footnotes.
- If the source uses inline links, continue inline links.
- If the source has a references section, update that section consistently.
- If the source has no citation pattern, keep citations in the report only.

## Post-Generation Obligations

- After saving the refreshed copy, immediately run Report-to-Copy Sync Check (see SKILL.md).
- Do NOT declare work complete until the sync check is shown to the user.
- If `Missing` or `Partially synced` items exist, ask the user whether to patch them.
- Update the report's `Refreshed copy` status in the header if it says "待生成" but the copy now exists.
- Do not silently skip items without user confirmation — unconfirmed items are `Missing`, not `Deferred`.

## Refreshed Copy Requirements

- Save refreshed content to `versions/<stem>.YYYYMMDD-HHmm.md`.
- Keep the source file unchanged until explicit source write-back confirmation.
- Include only article content in the refreshed copy, not the refresh report.
- Preserve Markdown formatting style where practical.

## Source Write-Back Confirmation

Before overwriting the source document, show this confirmation shape:

```md
I am ready to write the refreshed copy back to the source document.

- Source document: `<source-path>`
- Refreshed copy to write back: `<versions-copy-path>`
- Report: `<report-path-or-none>`
- Preserved versions: timestamped files under `versions/` will remain.

Please confirm: overwrite `<source-path>` with `<versions-copy-path>`?
```

Only overwrite after the user explicitly confirms this source write-back.
