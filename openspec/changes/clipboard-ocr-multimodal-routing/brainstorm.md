# Brainstorm

## Problem

`ocr-router` is currently framed as a non-vision fallback pipeline. In practice, the workspace now has a local MCP server that can either return `image` content directly (`load_image`) or fall back to server-side VLM/OCR (`describe_image`, `extract_image_text`). The skill should help the model choose the right path instead of always assuming a non-`load*` fallback.

The main gap is routing, not image extraction. The skill needs to answer:

- When should the model prefer `ocr-vlm_load_image`?
- When is `ocr-vlm_describe_image` the right fallback?
- How should clipboard images and local image paths be handled with the same policy?

## Constraints

- Preserve the existing routing intent so the current trigger surface stays stable.
- Avoid creating a redundant new skill that competes with `ocr-router`.
- Do not over-claim runtime capabilities: the skill can guide tool choice, but it cannot guarantee that every client will re-inject MCP image content into model context.
- Keep non-`load*` tools as fallback paths for non-vision models or unknown client behavior.
- Keep the workflow compatible with the existing `ocr_mcp` tool set and the clipboard extraction tool.

## Options

1. Keep the skill as OCR-only.
- Lowest risk, but it leaves `load_image` underused and does not express the preferred multimodal path.

2. Create a new `direct-image-bridge` skill.
- Clean separation, but it duplicates overlapping behavior and fragments triggers between two similar skills.

3. Update `ocr-router` into a routing skill.
- Teach it to prefer `load_image` when the model/client can use image content, then fall back to OCR/VLM helpers when necessary.
- This keeps a single entry point for clipboard images and local image paths.

## Recommendation

Update `ocr-router` in place and broaden its scope from “clipboard OCR pipeline” to “clipboard and local image routing for multimodal-first workflows.”

Recommended behavior:

- Use `clipboard_image` when the user is working from the macOS clipboard.
- Prefer `ocr-vlm_load_image` when the current model and client can handle MCP image content.
- Fall back to `ocr-vlm_describe_image` when the model is non-vision or client behavior is uncertain.
- Use `ocr-vlm_extract_image_text` only when the user wants exact text transcription.
