from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIR = REPO_ROOT / "skills"
CLIENT_DIRS = [
    REPO_ROOT / ".opencode" / "skills",
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / ".cursor" / "skills",
]
CANONICAL_SKILLS = sorted(
    path.name for path in CANONICAL_DIR.iterdir() if path.is_dir() and path.name.startswith("sdlc-")
)
INSTALL_METADATA_REQUIRED_FIELDS = [
    "skill",
    "source_repo",
    "source_path",
    "target",
    "installed_at",
    "status",
    "payload_hash",
    "files",
]
SUBDIRS_WITH_CONTENT = ["scripts", "schemas", "templates"]


class TestRepositoryMemorySkillCopies:
    def test_canonical_skill_dirs_exist(self):
        for skill in CANONICAL_SKILLS:
            canonical = CANONICAL_DIR / skill
            assert canonical.is_dir(), f"Canonical skill dir missing: {canonical}"
            assert (canonical / "SKILL.md").is_file(), f"Canonical SKILL.md missing: {skill}"

    def test_installed_copies_exist_in_all_client_dirs(self):
        for skill in CANONICAL_SKILLS:
            for client_dir in CLIENT_DIRS:
                skill_dir = client_dir / skill
                assert skill_dir.is_dir(), f"Installed copy missing: {skill_dir}"
                skill_md = skill_dir / "SKILL.md"
                assert skill_md.is_file(), f"SKILL.md missing: {skill_dir}"

    def test_skill_md_content_matches_canonical(self):
        for skill in CANONICAL_SKILLS:
            canonical_content = (CANONICAL_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
            for client_dir in CLIENT_DIRS:
                copy_content = (client_dir / skill / "SKILL.md").read_text(encoding="utf-8")
                assert canonical_content == copy_content, (
                    f"SKILL.md mismatch for {skill} in {client_dir.name}"
                )

    def test_skill_install_json_exists_in_all_copies(self):
        for skill in CANONICAL_SKILLS:
            for client_dir in CLIENT_DIRS:
                install_json = client_dir / skill / ".skill-install.json"
                assert install_json.is_file(), f".skill-install.json missing: {skill} in {client_dir.name}"

    def test_skill_install_json_has_required_fields(self):
        for skill in CANONICAL_SKILLS:
            for client_dir in CLIENT_DIRS:
                install_json = client_dir / skill / ".skill-install.json"
                data = json.loads(install_json.read_text(encoding="utf-8"))
                for field in INSTALL_METADATA_REQUIRED_FIELDS:
                    assert field in data, f"Missing field '{field}' in {install_json}"

    def test_skill_install_json_skill_name_matches(self):
        for skill in CANONICAL_SKILLS:
            for client_dir in CLIENT_DIRS:
                install_json = client_dir / skill / ".skill-install.json"
                data = json.loads(install_json.read_text(encoding="utf-8"))
                assert data["skill"] == skill, f"Expected skill={skill}, got {data['skill']} in {install_json}"

    def test_canonical_scripts_exist_in_all_copies(self):
        for skill in CANONICAL_SKILLS:
            canonical_scripts = CANONICAL_DIR / skill / "scripts"
            if not canonical_scripts.is_dir():
                continue
            for script_file in canonical_scripts.iterdir():
                if script_file.name.startswith("_") or not script_file.is_file():
                    continue
                for client_dir in CLIENT_DIRS:
                    copy_script = client_dir / skill / "scripts" / script_file.name
                    assert copy_script.is_file(), f"Script {script_file.name} missing in {client_dir.name}/{skill}"
                    canonical_content = script_file.read_text(encoding="utf-8")
                    copy_content = copy_script.read_text(encoding="utf-8")
                    assert canonical_content == copy_content, (
                        f"Script {script_file.name} content mismatch in {client_dir.name}/{skill}"
                    )

    def test_canonical_schemas_exist_in_all_copies(self):
        for skill in CANONICAL_SKILLS:
            canonical_schemas = CANONICAL_DIR / skill / "schemas"
            if not canonical_schemas.is_dir():
                continue
            for schema_file in canonical_schemas.iterdir():
                if not schema_file.is_file():
                    continue
                for client_dir in CLIENT_DIRS:
                    copy_schema = client_dir / skill / "schemas" / schema_file.name
                    assert copy_schema.is_file(), f"Schema {schema_file.name} missing in {client_dir.name}/{skill}"
                    canonical_content = schema_file.read_text(encoding="utf-8")
                    copy_content = copy_schema.read_text(encoding="utf-8")
                    assert canonical_content == copy_content, (
                        f"Schema {schema_file.name} content mismatch in {client_dir.name}/{skill}"
                    )

    def test_canonical_templates_exist_in_all_copies(self):
        for skill in CANONICAL_SKILLS:
            canonical_templates = CANONICAL_DIR / skill / "templates"
            if not canonical_templates.is_dir():
                continue
            for template_file in canonical_templates.iterdir():
                if not template_file.is_file():
                    continue
                for client_dir in CLIENT_DIRS:
                    copy_template = client_dir / skill / "templates" / template_file.name
                    assert copy_template.is_file(), f"Template {template_file.name} missing in {client_dir.name}/{skill}"
                    canonical_content = template_file.read_text(encoding="utf-8")
                    copy_content = copy_template.read_text(encoding="utf-8")
                    assert canonical_content == copy_content, (
                        f"Template {template_file.name} content mismatch in {client_dir.name}/{skill}"
                    )

    def test_openspec_memory_sync_exists_in_all_client_dirs(self):
        for client_dir in CLIENT_DIRS:
            skill_dir = client_dir / "sdlc-openspec-memory-sync"
            assert skill_dir.is_dir(), f"sdlc-openspec-memory-sync missing in {client_dir.name}"
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.is_file(), f"sdlc-openspec-memory-sync SKILL.md missing in {client_dir.name}"

    def test_runtime_path_helper_copied_to_cli_skill_trees(self):
        canonical = CANONICAL_DIR / "_lib" / "sdlc_runtime_paths.py"
        for target in [".opencode", ".claude", ".cursor"]:
            helper = REPO_ROOT / target / "skills" / "_lib" / "sdlc_runtime_paths.py"
            assert helper.exists(), f"missing runtime helper in {target}"
            assert helper.read_text(encoding="utf-8") == canonical.read_text(encoding="utf-8")
