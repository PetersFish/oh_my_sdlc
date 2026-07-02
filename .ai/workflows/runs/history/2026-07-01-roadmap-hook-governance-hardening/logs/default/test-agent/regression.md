# Regression Log

- `python3 -m pytest tests/test_sdlc_roadmap.py -v` → 54 passed
- `python3 -m pytest tests/ -v` → 939 passed, 37 subtests passed

## Additional observations
- `git diff --no-index -- agents/dev-orchestrator.md .opencode/agents/dev-orchestrator.md` shows activation-managed `model`/`variant` frontmatter in distributed copies; broader wrapper-contract tests passed, supporting consistent distributed prompt content.
- `openspec/changes/roadmap-hook-governance-hardening/tasks.md` keeps 5.3/5.4/5.5 unchecked, so the checklist does not claim unrun work as complete.
