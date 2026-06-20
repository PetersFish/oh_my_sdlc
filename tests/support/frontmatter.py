from pathlib import Path

import yaml


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    frontmatter = text[3:end].strip()
    data = yaml.safe_load(frontmatter)
    return data if isinstance(data, dict) else {}
