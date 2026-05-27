## Context

The current `ocr-router` skill is optimized for a non-vision fallback workflow: it extracts a clipboard image, saves it locally, and then sends the image to `ocr-vlm_describe_image`. That is still useful, but it is no longer the best default when the current model and client can move `image` content through MCP and let the model inspect it directly.

This change updates the skill to act as a routing layer for image input, not just an OCR pipeline.

## Goals / Non-Goals

### Goals

- Keep the skill scope but rename it to `ocr-router`.
- Prefer direct multimodal image loading (`ocr-vlm_load_image`) when the model/client path can support it.
- Preserve clipboard extraction for clipboard-based workflows.
- Preserve non-`load*` fallback paths for non-vision or uncertain environments.
- Make the decision rule explicit so the model knows when to route vs. when to fall back.

### Non-Goals

- Do not change the `ocr_mcp` server implementation.
- Do not add a second, overlapping skill for the same image-routing job.
- Do not promise that every client can re-inject MCP image content into model context.
- Do not remove the existing non-`load*` fallback behavior.

## Decisions

1. Rename the skill to `ocr-router`.
2. Expand the skill body to cover both clipboard images and local image paths.
3. Add a routing rule that prefers `ocr-vlm_load_image` only when the model is vision-capable and the client path is expected to preserve MCP image content.
4. Use `ocr-vlm_describe_image` when direct image routing is unavailable or uncertain.
5. Use `ocr-vlm_extract_image_text` only for exact-text transcription requests.
6. Keep the clipboard extraction step as the entry path whenever the user is working from the macOS clipboard.

## Risks / Trade-offs

- The skill may still overestimate client capability if the client advertises image support but does not pass image content back into model context.
- A more explicit routing policy makes the skill longer, but it reduces accidental fallback to OCR when direct multimodal input is available.
- Keeping a single skill avoids trigger fragmentation, but it means the skill now covers both routing and fallback guidance.
