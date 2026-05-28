from __future__ import annotations

import unittest
from pathlib import Path


SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "media-ocr-router" / "SKILL.md"


class ClipboardOcrSkillTest(unittest.TestCase):
    def test_skill_mentions_multimodal_routing_and_fallbacks(self) -> None:
        text = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("name: media-ocr-router", text)
        self.assertIn("load_image", text)
        self.assertIn("load_markdown_images", text)
        self.assertIn("load_markdown_media", text)
        self.assertIn("describe_image", text)
        self.assertIn("extract_image_text", text)
        self.assertIn("clipboard_image", text)
        self.assertRegex(text, r"prefer.*load_image|load_image.*prefer")
        self.assertIn("non-`load*`", text)
        self.assertRegex(text, r"fallback|Fallback")

    def test_skill_prefers_markdown_media_loading_before_ocr_fallback(self) -> None:
        text = SKILL_PATH.read_text(encoding="utf-8")

        load_idx = text.index("load_markdown_images")
        media_idx = text.index("load_markdown_media")
        extract_idx = text.index("extract_markdown_image_text")

        self.assertLess(load_idx, extract_idx)
        self.assertLess(media_idx, extract_idx)
        self.assertIn("directly inspect them yourself", text)
        self.assertIn("another non-`load*` tool", text)


if __name__ == "__main__":
    unittest.main()
