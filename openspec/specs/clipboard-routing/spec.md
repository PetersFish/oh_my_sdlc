# clipboard-routing

TBD

## Requirements

### Requirement: Prefer direct image loading when multimodal support is available
The `ocr-router` skill SHALL instruct the model to prefer `ocr-vlm_load_image` for local image paths or clipboard-extracted images when the current model is known to support image input and the client path is expected to preserve MCP image content.

#### Scenario: Vision-capable path
- **WHEN** the user asks to analyze a screenshot or local image and the current model can handle image input
- **THEN** the skill routes to `ocr-vlm_load_image` before any non-`load*` fallback

### Requirement: Fall back to non-`load*` tools when image routing is uncertain
The `ocr-router` skill SHALL instruct the model to use `ocr-vlm_describe_image` or `ocr-vlm_extract_image_text` when direct multimodal image routing is unavailable, unsupported, or uncertain.

#### Scenario: Non-vision or uncertain client path
- **WHEN** the current model cannot consume image input directly or the client cannot be trusted to pass image content through
- **THEN** the skill falls back to `ocr-vlm_describe_image` for semantic analysis or `ocr-vlm_extract_image_text` for exact transcription

### Requirement: Preserve clipboard-first workflow
The `ocr-router` skill SHALL keep the macOS clipboard extraction step as the entry point when the user is working from a copied screenshot or clipboard image.

#### Scenario: Clipboard screenshot
- **WHEN** the user says they copied an image or asks to inspect the clipboard image
- **THEN** the skill first uses `clipboard_image` and then applies the routing rule for `load_image` versus non-`load*` fallback
