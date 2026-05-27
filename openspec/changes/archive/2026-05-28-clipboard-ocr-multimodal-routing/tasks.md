## 1. Setup

- [x] 1.1 Copy the current routing skill into the canonical skill repo and align its scope with multimodal-first routing.
- [x] 1.2 Review the existing `ocr_mcp` tool descriptions and any related tests so the updated skill matches the available tool surface.

## 2. Implementation

- [x] 2.1 Update the skill body and frontmatter to prefer `load_image` when multimodal support is available, while preserving clipboard-first and non-`load*` fallback behavior.
- [x] 2.2 Add or update repository checks that confirm the skill mentions the routing decision and the fallback paths, then run the relevant validation commands.
