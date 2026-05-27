## ADDED Requirements

### Requirement: Create discovery-prefs.json during initialization
`init_memory.py` SHALL create `.ai-memory/discovery-prefs.json` with
`schema_version: "1.0"`, `exclude_patterns` (default deny-list including `.git`,
`.ai-memory`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.pytest_cache`,
`.mypy_cache`, `.ruff_cache`, `.tox`, `dist`, `build`, `target`, `.idea`,
`.vscode`), `max_depth: 5`, `scan_paths: null`, and `module_map: {}`.

#### Scenario: First-time init creates discovery prefs with defaults
- **WHEN** `init_memory.py` creates `.ai-memory/` for the first time
- **THEN** `discovery-prefs.json` SHALL exist with default values for all
  required fields

#### Scenario: Re-init preserves existing discovery prefs
- **WHEN** `init_memory.py` runs and `discovery-prefs.json` already exists
- **THEN** it SHALL NOT overwrite the file
