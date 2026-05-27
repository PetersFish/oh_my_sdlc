# Plan

## 1. Task Map

- [ ] 1.1 Covers `tasks.md` 1.1 by creating the canonical `ocr-router` skill content in the repo.
- [ ] 1.2 Covers `tasks.md` 1.2 by checking the existing `ocr_mcp` tool surface and keeping the routing language consistent.
- [ ] 1.3 Covers `tasks.md` 2.1 by updating the skill frontmatter/body to prefer `load_image` with non-`load*` fallback.
- [ ] 1.4 Covers `tasks.md` 2.2 by adding or updating validation that checks for the routing decision and fallback wording.

## 2. Execution Steps

1. Write the smallest failing repository check first, if needed, for the skill metadata and routing language.
2. Implement the `ocr-router` skill update with the minimal wording needed to express multimodal-first routing.
3. Re-run the repository validation that covers the skill file and confirm the new routing guidance is present.
