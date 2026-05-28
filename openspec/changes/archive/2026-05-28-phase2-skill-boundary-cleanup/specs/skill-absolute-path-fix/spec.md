# skill-absolute-path-fix

Removal of machine-specific absolute paths from skill bodies and installed copies. Skill bodies SHALL reference other skills by name or use paths relative to the skill base directory.

## ADDED Requirements

### Requirement: transform-markdown-svg has no absolute script path

The body of `skills/transform-markdown-svg/SKILL.md` SHALL NOT contain any absolute path beginning with `/Users/`. The script invocation instruction SHALL use a path relative to the skill base directory or reference the skill name.

#### Scenario: No /Users/ path in transform-markdown-svg
- **WHEN** reading the body of `skills/transform-markdown-svg/SKILL.md`
- **THEN** no line matches the pattern `/Users/yuping/.cursor/skills/`

#### Scenario: Script invocation is usable without absolute path
- **WHEN** reading the script invocation instruction in `skills/transform-markdown-svg/SKILL.md`
- **THEN** the path references `scripts/embed_drawio_svg.py` relative to the skill directory or uses a skill-name-based resolution path that does not depend on a specific home directory

### Requirement: study-zybook-notes references skills by name, not path

The body of `skills/study-zybook-notes/SKILL.md` SHALL reference atomic skills (`transform-algo-render`, `transform-markdown-svg`) by their skill name, not by absolute filesystem paths.

#### Scenario: No /Users/ path in study-zybook-notes
- **WHEN** reading the body of `skills/study-zybook-notes/SKILL.md`
- **THEN** no line matches the pattern `/Users/yuping/.cursor/skills/`

#### Scenario: Skill references use name not path
- **WHEN** reading references to `transform-algo-render` in the body
- **THEN** the reference uses the skill name or a relative path, not an absolute machine-specific path

### Requirement: All skill bodies are free of absolute paths

No `skills/*/SKILL.md` file SHALL contain an absolute path beginning with `/Users/`, `/tmp/`, `/var/`, or `file:///` in its body content. Relative paths (e.g., `references/`, `scripts/`, `templates/`) and relative-to-home examples (e.g., `.cursor/skills`) are permitted.

#### Scenario: grep returns no absolute path matches
- **WHEN** searching all `skills/*/SKILL.md` files for the pattern `/Users/`
- **THEN** no matches are found

### Requirement: Installed copies also have no absolute paths

After sync, installed copies in `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/` SHALL also contain no absolute paths matching `/Users/`.

#### Scenario: Installed copies clean
- **WHEN** searching installed copy SKILL.md files for `/Users/`
- **THEN** no matches are found
