# Rewrite and Write-Back Policy

Use this policy before writing refreshed article content or overwriting a source document.

## Conservative Refresh Default

- Preserve the source document language.
- Preserve the target reader and overall tone.
- Preserve the existing structure unless it blocks accurate technical refresh.
- Preserve the original citation style when it exists.
- If the source has no citations, keep the refreshed article clean and put sources in the report.
- Improve terminology, technical accuracy, outdated wording, and paragraph flow when needed.
- Keep mature recommendations separate from frontier exploration.
- Avoid marketing language and unsupported certainty.

## Structure Changes

Do not perform major restructuring by default. If the current structure prevents an accurate modern explanation, propose the new structure in the report and wait for confirmation before rewriting around it.

## Citation Handling

- If the source uses footnotes, continue footnotes.
- If the source uses inline links, continue inline links.
- If the source has a references section, update that section consistently.
- If the source has no citation pattern, keep citations in the report only.

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
