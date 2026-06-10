---
name: media-ocr-router
description: Route clipboard images, local image paths, and Markdown-embedded media through the best available image workflow. Use when the user asks to inspect a screenshot, copied image, local image path, or Markdown file with images/videos, especially when the model may support multimodal input and you should prefer `load_image` / `load_markdown_images` / `load_markdown_media` before falling back to any non-`load*` tool. Keep this quiet for non-image tasks.
---

# Media OCR Router

## Purpose

Use this skill to turn clipboard images, local image paths, or Markdown-embedded media into the right image-processing path.

The preferred order is:

1. Capture the clipboard image when the user copied a screenshot
2. Prefer `ocr-vlm_load_image` for a single local image when the current model and client can keep image content in the model context
3. Prefer `ocr-vlm_load_markdown_images` or `ocr-vlm_load_markdown_media` when the user gives a Markdown file with embedded images or media and the client can keep MCP image/resource content in context
4. If the media is loaded successfully, directly inspect them yourself and write the descriptions back under the corresponding image entries
5. Fall back to `ocr-vlm_describe_image` when direct image routing is unavailable or uncertain
6. Use `ocr-vlm_extract_image_text` or `ocr-vlm_extract_markdown_image_text` only when the user wants exact transcription and the model cannot directly inspect the loaded media

## When To Use

- The user asks to inspect, describe, or analyze a clipboard screenshot
- The user provides a local image path and wants the model to look at the image
- The user provides a Markdown file with embedded images or videos and wants the content inspected
- The user asks whether to use direct image loading or a non-`load*` fallback
- The current model appears to support multimodal input and direct image loading should be tried first

## Do NOT Use When

- The task is unrelated to images
- The user only wants text OCR and not image interpretation
- The model/client cannot handle image content and the user explicitly wants a text-only fallback path

If the current model is clearly non-vision, skip the direct-image branch and go straight to a non-`load*` fallback such as `ocr-vlm_describe_image` or `ocr-vlm_extract_image_text`.

## Routing Rules

### Step 1: Decide the entry point

- If the user says they copied an image or screenshot, call `clipboard_image` first.
- If the user already gave a local file path, use that path directly.

### Step 2: Prefer direct image loading when possible

- If the current model supports image input and the client is expected to preserve MCP image content, call `ocr-vlm_load_image`.
- Use this path for visual understanding, UI review, architecture diagrams, and other tasks where the model should inspect the image itself.

### Step 2b: Prefer Markdown media loading for embedded assets

- If the user points at a Markdown file that embeds local images or videos, call `ocr-vlm_load_markdown_images` or `ocr-vlm_load_markdown_media` first.
- Use `ocr-vlm_load_markdown_images` when the file only needs image loading.
- Use `ocr-vlm_load_markdown_media` when the file mixes images and videos or the user asked for all embedded media.
- After loading succeeds, directly inspect the loaded media yourself and append the interpretation beneath each matching image or media reference.
- Only use `ocr-vlm_extract_markdown_image_text` if the model cannot directly inspect the loaded media or the user explicitly asked for OCR transcription.

### Step 3: Fall back when direct routing is uncertain

- If the current model is non-vision, or the client may not pass image content back into context, call a non-`load*` fallback such as `ocr-vlm_describe_image`.
- If the user wants exact text, call `ocr-vlm_extract_image_text` instead of description.

## Required Steps

1. Get the image path, either from `clipboard_image` or from the user's local path.
2. Choose `ocr-vlm_load_image` first when multimodal routing is supported for a single image.
3. Choose `ocr-vlm_load_markdown_images` or `ocr-vlm_load_markdown_media` first when the input is a Markdown file with embedded media.
4. If loading succeeds, directly inspect the loaded media yourself and write the result below each corresponding reference.
5. Otherwise choose a non-`load*` fallback such as `ocr-vlm_describe_image`.
6. If the user explicitly wants exact characters or OCR output, choose `ocr-vlm_extract_image_text` or `ocr-vlm_extract_markdown_image_text`.

## Error Handling

- If `clipboard_image` returns an error, tell the user no image was found in the clipboard and ask them to copy one first.
- If `ocr-vlm_load_image` is unavailable in the current client path, fall back to a non-`load*` tool such as `ocr-vlm_describe_image`.
- If Markdown media loading is unavailable or returns partial results, fall back to direct per-image processing or another non-`load*` tool.
- If the model cannot directly inspect loaded Markdown media, use `ocr-vlm_extract_markdown_image_text` as the non-`load*` fallback.
- If the VLM fallback fails, surface the failure and suggest retrying or switching to OCR-only transcription.

## Multiple Images

Process multiple images one at a time:

1. Copy or point to image 1 → get the path → choose direct load or fallback → return the result
2. Copy or point to image 2 → repeat
3. Continue as needed

Each call to `clipboard_image` overwrites the previous file, so process images sequentially.
