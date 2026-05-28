from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "skills" / "research-general" / "SKILL.md"
TEMPLATES_PATH = ROOT / "skills" / "research-general" / "references" / "templates.md"
QUALITY_PATH = ROOT / "skills" / "research-general" / "references" / "research-quality.md"


class ResearchSkillTest(unittest.TestCase):
    def test_run_guidance_requires_high_quality_research_framing(self) -> None:
        text = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("High-Quality Research Runs", text)
        self.assertIn("one-sentence real question", text)
        self.assertIn("concept definition", text)
        self.assertIn("causal mechanism", text)
        self.assertIn("real-world application", text)
        self.assertIn("consensus, controversies, and common misconceptions", text)
        self.assertIn("references/research-quality.md", text)

    def test_solution_template_matches_insight_research_structure(self) -> None:
        text = TEMPLATES_PATH.read_text(encoding="utf-8")

        expected_sections = [
            "Elevator Explanation",
            "Provocative Thesis",
            "Current Scientific Understanding",
            "Consensus, Controversies, and Misconceptions",
            "Cross-Disciplinary Map",
            "Cases and Applications",
            "Deeper Insight",
            "Practical Applications",
            "Reference Sources",
        ]

        for section in expected_sections:
            with self.subTest(section=section):
                self.assertIn(section, text)

    def test_quality_reference_sets_source_and_style_standards(self) -> None:
        text = QUALITY_PATH.read_text(encoding="utf-8")

        required_terms = [
            "peer-reviewed papers",
            "mainstream media",
            "authoritative institution reports",
            "classic theories",
            "English-language sources",
            "ordinary undergraduate",
            "original terms",
            "Complex Systems",
            "Information Theory",
            "Evolutionary Theory",
            "Behavioral Economics",
            "Cognitive Science",
            "Do not fabricate citations",
        ]

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
