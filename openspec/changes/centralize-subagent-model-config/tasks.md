## 1. Shared Config And Helper Layer

- [ ] 1.1 Add `agents/config/model-profiles.yaml` with fixed profiles, default variant, and initial per-agent assignments.
- [ ] 1.2 Add shared helper logic for target resolution, config loading/validation, effective model resolution, frontmatter update/insert, and normalized prompt comparison.
- [ ] 1.3 Add focused tests for schema validation, model/variant precedence, frontmatter preservation, and normalized compare behavior.

## 2. Template Sync Refactor

- [ ] 2.1 Refactor `scripts/install_agents.py` to copy canonical prompts plus the config template into target agent directories.
- [ ] 2.2 Preserve existing target `config/model-profiles.yaml` files on reinstall while still initializing missing target config.
- [ ] 2.3 Update template-sync check behavior so activation-managed `model` and `variant` differences do not count as canonical prompt drift.
- [ ] 2.4 Add or update focused tests covering fresh install, config preservation, and normalized template drift detection.

## 3. Effective Config Activation

- [ ] 3.1 Add `scripts/activate_agents_config.py` as a thin CLI over the shared helper layer.
- [ ] 3.2 Implement effective `model` and `variant` rendering from target config, including frontmatter insertion for body-only markdown.
- [ ] 3.3 Add activation `--check` and `--dry-run` behavior for rendered frontmatter drift without unnecessary writes.
- [ ] 3.4 Add focused tests covering profile defaults, agent overrides, frontmatter insertion, and activation drift detection.

## 4. Aggregate Setup Flow

- [ ] 4.1 Add `scripts/setup_agents.py` to run template sync before activation for a target or global install.
- [ ] 4.2 Implement aggregate `--check` so template drift and activation drift are both surfaced through one entrypoint.
- [ ] 4.3 Implement aggregate `--dry-run` and a non-destructive config-refresh-friendly path.
- [ ] 4.4 Add focused tests covering install-then-activate sequencing, check failures, dry-run, and refresh behavior.

## 5. Canonical Cleanup And Bootstrap Guidance

- [ ] 5.1 Remove activation-managed `model` and `variant` fields from canonical `agents/*.md`.
- [ ] 5.2 Update `skills/sdlc-project-bootstrap/SKILL.md` so initialization-time agent setup routes through script entrypoints only.
- [ ] 5.3 Keep bootstrap initialization-only and do not add a new `sdlc-agent-config` skill in this change.
- [ ] 5.4 Regenerate derived agent copies and any affected distributed documentation through the existing distribution workflow.
- [ ] 5.5 Add or update focused tests covering canonical cleanup and bootstrap guidance boundaries.

## 6. Verification

- [ ] 6.1 Run `python3 -m pytest tests/test_install_agents.py -v`.
- [ ] 6.2 Run `python3 -m pytest tests/test_activate_agents_config.py -v`.
- [ ] 6.3 Run `python3 -m pytest tests/test_setup_agents.py -v`.
- [ ] 6.4 Run `python3 -m pytest tests/test_project_bootstrap_skills.py -v`.
- [ ] 6.5 Run `python3 -m pytest tests/test_wrapper_contracts.py -v` if agent frontmatter drift expectations or distributed artifacts require it.
- [ ] 6.6 Run a final focused regression covering install, activation, setup, bootstrap guidance, and any affected wrapper-contract checks.
