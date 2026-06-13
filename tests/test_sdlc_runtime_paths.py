from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATHS = REPO_ROOT / "skills" / "_lib" / "sdlc_runtime_paths.py"


def _load_runtime_paths():
    spec = importlib.util.spec_from_file_location("sdlc_runtime_paths", RUNTIME_PATHS)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sdlc_runtime_paths"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_memory_path_defaults_to_ai_memory_namespace(tmp_path):
    runtime_paths = _load_runtime_paths()

    result = runtime_paths.resolve_memory_dir(tmp_path)

    assert result.path == tmp_path / ".ai" / "memory"
    assert result.kind == "canonical"
    assert result.legacy is False


def test_memory_path_prefers_existing_canonical_over_legacy(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai" / "memory").mkdir(parents=True)
    (tmp_path / ".ai-memory").mkdir()

    result = runtime_paths.resolve_memory_dir(tmp_path)

    assert result.path == tmp_path / ".ai" / "memory"
    assert result.kind == "canonical"
    assert result.legacy is False


def test_memory_path_falls_back_to_existing_legacy(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai-memory").mkdir()

    result = runtime_paths.resolve_memory_dir(tmp_path)

    assert result.path == tmp_path / ".ai-memory"
    assert result.kind == "legacy"
    assert result.legacy is True


def test_roadmap_path_defaults_to_ai_roadmap_namespace(tmp_path):
    runtime_paths = _load_runtime_paths()

    result = runtime_paths.resolve_roadmap_dir(tmp_path)

    assert result.path == tmp_path / ".ai" / "roadmap"
    assert result.kind == "canonical"
    assert result.legacy is False


def test_roadmap_path_falls_back_to_existing_legacy(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".roadmap").mkdir()

    result = runtime_paths.resolve_roadmap_dir(tmp_path)

    assert result.path == tmp_path / ".roadmap"
    assert result.kind == "legacy"
    assert result.legacy is True


def test_roadmap_manifest_path(tmp_path):
    runtime_paths = _load_runtime_paths()
    assert runtime_paths.roadmap_manifest_path(tmp_path) == tmp_path / ".ai" / "roadmap" / "manifest.json"


def test_roadmap_areas_dir(tmp_path):
    runtime_paths = _load_runtime_paths()
    assert runtime_paths.roadmap_areas_dir(tmp_path) == tmp_path / ".ai" / "roadmap" / "areas"


def test_roadmap_area_dir(tmp_path):
    runtime_paths = _load_runtime_paths()
    assert runtime_paths.roadmap_area_dir(tmp_path, "skill.test") == tmp_path / ".ai" / "roadmap" / "areas" / "skill.test"


def test_roadmap_area_items_dir(tmp_path):
    runtime_paths = _load_runtime_paths()
    assert runtime_paths.roadmap_area_items_dir(tmp_path, "skill.test") == tmp_path / ".ai" / "roadmap" / "areas" / "skill.test" / "items"


def test_has_area_layout_false_when_no_manifest(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai" / "roadmap").mkdir(parents=True)
    assert runtime_paths.has_area_layout(tmp_path) is False


def test_has_area_layout_true(tmp_path):
    runtime_paths = _load_runtime_paths()
    areas_dir = tmp_path / ".ai" / "roadmap" / "areas"
    areas_dir.mkdir(parents=True)
    (tmp_path / ".ai" / "roadmap" / "manifest.json").write_text('{"version":1}')
    assert runtime_paths.has_area_layout(tmp_path) is True


def test_has_flat_layout_true(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai" / "roadmap" / "items").mkdir(parents=True)
    assert runtime_paths.has_flat_layout(tmp_path) is True


def test_has_flat_layout_false(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai" / "roadmap").mkdir(parents=True)
    assert runtime_paths.has_flat_layout(tmp_path) is False


def test_discover_areas_empty(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai" / "roadmap" / "areas").mkdir(parents=True)
    assert runtime_paths.discover_areas(tmp_path) == []


def test_discover_areas_returns_ids(tmp_path):
    runtime_paths = _load_runtime_paths()
    for area_id in ["skill.foo", "skill.bar"]:
        area_dir = tmp_path / ".ai" / "roadmap" / "areas" / area_id
        area_dir.mkdir(parents=True)
        (area_dir / "manifest.json").write_text("{}")
    # Directory without manifest should be skipped
    (tmp_path / ".ai" / "roadmap" / "areas" / "no-manifest").mkdir(parents=True)
    result = runtime_paths.discover_areas(tmp_path)
    assert result == ["skill.bar", "skill.foo"]  # sorted


def test_load_roadmap_manifest(tmp_path):
    runtime_paths = _load_runtime_paths()
    (tmp_path / ".ai" / "roadmap").mkdir(parents=True)
    data = {"version": 1, "areas": [{"id": "skill.test"}]}
    (tmp_path / ".ai" / "roadmap" / "manifest.json").write_text(json.dumps(data))
    result = runtime_paths.load_roadmap_manifest(tmp_path)
    assert result == data


def test_load_roadmap_manifest_none(tmp_path):
    runtime_paths = _load_runtime_paths()
    assert runtime_paths.load_roadmap_manifest(tmp_path) is None


def test_load_area_manifest(tmp_path):
    runtime_paths = _load_runtime_paths()
    area_dir = tmp_path / ".ai" / "roadmap" / "areas" / "skill.test"
    area_dir.mkdir(parents=True)
    data = {"id": "skill.test", "kind": "skill"}
    (area_dir / "manifest.json").write_text(json.dumps(data))
    result = runtime_paths.load_area_manifest(tmp_path, "skill.test")
    assert result == data


def test_load_area_manifest_none(tmp_path):
    runtime_paths = _load_runtime_paths()
    assert runtime_paths.load_area_manifest(tmp_path, "skill.test") is None


def test_find_project_root_detects_canonical_ai_dir(tmp_path, monkeypatch):
    runtime_paths = _load_runtime_paths()
    project = tmp_path / "project"
    nested = project / "src" / "pkg"
    (project / ".ai" / "memory").mkdir(parents=True)
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    assert runtime_paths.find_project_root() == project
