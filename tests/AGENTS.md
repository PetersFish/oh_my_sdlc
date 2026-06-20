# Tests Guidelines

## Shared Helpers

Shared test helpers live under `tests/support/`. Do not duplicate helper logic inside individual test files when a support helper exists.

## Frontmatter Parsing

For Markdown/YAML frontmatter, use `tests/support/frontmatter.py::read_frontmatter`.

Do NOT implement ad hoc frontmatter parsers with string splitting, `partition(":")`, or manual folded-scalar handling. The YAML `>-` and `|` block scalar syntax cannot be parsed by line-by-line `split(":")` alone.

If a new parser or helper is needed, add it once under `tests/support/` and cover it with focused tests.

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## Adding New Test Files

- New test files follow the naming convention `tests/test_<subject>.py`.
- Import shared helpers from `support.<module>`.
- Do not duplicate `_read_frontmatter`, `_read_yaml`, or similar parser functions.
