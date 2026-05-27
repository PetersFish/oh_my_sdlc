## Why

`ocr-router` currently assumes a non-vision fallback path, but the workspace now has a local MCP server that can return image content directly. That makes the old skill scope too narrow: it describes how to process clipboard images, but not how to route image input through the best available path.

## What Changes

- Keep the existing routing skill name, but rename it to `ocr-router`.
- Expand the skill from OCR-only guidance to image-input routing guidance.
- Prefer `ocr-vlm_load_image` when the current model and client can consume MCP image content.
- Fall back to `ocr-vlm_describe_image` when vision support is unavailable or uncertain.
- Keep all non-`load*` tools as fallback paths, including `ocr-vlm_describe_image` and `ocr-vlm_extract_image_text`.
- Preserve the clipboard-first flow by keeping `clipboard_image` in the path when the user is working from the macOS clipboard.

## Impact

- Users get a single skill that covers clipboard images and local image paths without needing a separate routing skill.
- The model is less likely to jump straight to OCR when it could instead use direct multimodal input.
- The existing non-`load*` fallback behavior remains available for non-vision models and uncertain client setups.
- The change is mostly instructional and low risk: it updates routing guidance, not core MCP tool behavior.
