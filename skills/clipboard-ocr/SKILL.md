---
name: clipboard-ocr
description: Pipeline for extracting macOS clipboard images and describing them via OCR. ONLY for non-vision (LLM-only) models that CANNOT natively see images (e.g., DeepSeek, MiMo-V2.5-Pro). Do NOT trigger when using multimodal/vision models (GPT-4o, Claude, Gemini, MiMo-V2.5).
---

# Clipboard Image OCR Pipeline

## Purpose

When using a non-vision model (e.g., DeepSeek v4 pro) that cannot natively "see" images, this skill provides a two-step pipeline to describe clipboard images:

1. Extract the image from macOS clipboard and save to a file
2. Describe the image content via OCR

## When To Use

- The CURRENT MODEL is a non-vision / LLM-only model (e.g., DeepSeek, MiMo-V2.5-Pro) that cannot natively see images
- User says "识别剪贴板图片" / "describe clipboard image" / "识别图片"
- User asks to analyze or describe an image they just copied or screenshotted
- User pastes an image reference without a visible path

## Do NOT Use When

The current model supports native image input (multimodal/vision models), including:
- GPT-4o, GPT-4 Vision, GPT-4.1-mini, o3, o4-mini
- Claude 3+, Claude 4+ (Opus/Sonnet/Haiku)
- Gemini 2.0+, Gemini Flash/Pro
- MiMo-V2.5 (base, NOT Pro)
- Qwen-VL series
- Any model that lists "image" as a supported input modality

If unsure whether the current model supports vision, check its input modalities before proceeding. When a vision model is detected, skip this skill and let the model handle images natively.

## Required Steps

### Step 1: Extract image from clipboard

Call the `clipboard_image` tool to save the clipboard image to a file and get the path.

```
clipboard_image → returns /Users/yuping/Pictures/opencode/clip-YYYYMMDD-HHMMSS.png
```

### Step 2: Describe the image via OCR

Use the returned path from Step 1 to call the `ocr-vlm_describe_image` tool.

```
ocr-vlm_describe_image(image_path="/Users/yuping/Pictures/opencode/clip-YYYYMMDD-HHMMSS.png")
```

### Step 3: Return the result

Return the OCR description to the user.

## Error Handling

- If `clipboard_image` returns an ERROR message, inform the user that no image was found in the clipboard and ask them to copy an image first.
- If `ocr-vlm_describe_image` fails, inform the user of the OCR failure and suggest they try again.

## Multiple Images

For multiple images, process them one at a time:
1. Screenshot / copy image 1 → call clipboard_image → ocr-vlm_describe_image → return result
2. Screenshot / copy image 2 → call clipboard_image → ocr-vlm_describe_image → return result
3. Repeat as needed

Each call to `clipboard_image` overwrites the previous file (timestamped filename ensures no collision).	
