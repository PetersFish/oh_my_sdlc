# Subagent Model Config Implementation Plan

## Objective

Implement centralized per-subagent model configuration so canonical `agents/*.md` stay model-agnostic, each CLI target gets its own effective `model-profiles.yaml`, and generated target agent frontmatter is rendered from that effective config through a dedicated activation step.

## Design Review Outcome

### Overall assessment

The design is directionally sound and appropriately scoped for a short-term frontmatter-render approach. The split between canonical template sync and effective-config activation is the right boundary, and the proposed YAML schema is simple enough to evolve into a later runtime resolver.

### Findings to carry into implementation

1. **Canonical agent cleanup is required but not called out explicitly.** Current canonical `agents/*.md` still include `model` / `variant` in at least some files. Implementation must remove those fields from canonical prompts and rely on activation for derived copies.
2. **`setup_agents.py --dry-run` is underspecified.** The design says the aggregate entry should support dry-run, but only activation defines dry-run behavior. Implementation should define dry-run as a non-writing preview of both template-sync and activation effects.
3. **Config-refresh UX should avoid unnecessary prompt overwrite.** The design sometimes recommends `setup_agents.py --force` after editing target config, but that is heavier than needed. Prefer an activation-only refresh path; keep aggregate `setup_agents.py` as the normal user entry.
4. **Metadata/hash semantics need clarification.** After activation mutates target markdown, `.agent-install.json` can no longer mean “final target file hash equals canonical hash”. Implementation should treat metadata as canonical install state, while activation drift is checked separately.
5. **Bootstrap-skill scope needs careful handling.** `sdlc-project-bootstrap` is currently framed as initialization-only. For “refresh agents” natural-language flows, implementation should route through the script entry without broadening bootstrap into a general maintenance skill unless explicitly desired.
6. **Frontmatter insertion behavior should be explicit.** Activation must define behavior for targets with no frontmatter: insert YAML frontmatter with `model` and `variant` while preserving body verbatim.

### Planning recommendation

Proceed with implementation, but treat items 2-5 above as first-class acceptance criteria during coding and review.

### User feedback incorporated and final approval

The user agreed with findings 1, 2, 3, 4, and 6.

For finding 5, the accepted implementation decision is:

- **Do not expand `sdlc-project-bootstrap` into a general refresh/maintenance skill in this change.**
- **Do not create a new `sdlc-agent-config` skill in this same change.**
- Instead, keep this change focused on the script/runtime layer (`install_agents.py`, `activate_agents_config.py`, `setup_agents.py`) plus minimal bootstrap-skill documentation for initialization-time agent setup only.
- Treat post-bootstrap “refresh agents after config edits” as an LLM-routed operation that can call `setup_agents.py` or activation directly without introducing a new durable skill yet.

Rationale:

1. The current design is about model-config plumbing, not long-term conversational routing taxonomy.
2. A new dedicated skill would add trigger semantics, documentation, distribution, and maintenance scope beyond what is needed to land the infrastructure safely.
3. Bootstrap already has a clear initialization contract; stretching it into lifecycle maintenance would blur that boundary.
4. Once real refresh usage patterns are observed, a later focused change can decide whether a dedicated `sdlc-agent-config` skill is justified.

The user has approved the implementation plan with this item 5 decision incorporated. The plan is ready for the next workflow step after the spec-flow provider-owned artifacts are generated and verified through the resolved provider wrapper.

## Recommended Approach

Build a shared helper library first, then move `install_agents.py` to pure template-sync semantics, then add activation and aggregate setup layers on top. Keep verification behavior split the same way as runtime behavior: template drift and activation drift are separate checks and only combine at the `setup_agents.py --check` layer.

## Files / Artifacts Expected

### Create

- `agents/config/model-profiles.yaml`
- `scripts/agent_config_lib.py`
- `scripts/activate_agents_config.py`
- `scripts/setup_agents.py`
- `tests/test_activate_agents_config.py`
- `tests/test_setup_agents.py`

### Modify

- `agents/*.md` (remove canonical `model` / `variant` fields where present)
- `scripts/install_agents.py`
- `skills/sdlc-project-bootstrap/SKILL.md`
- `tests/test_install_agents.py`
- `tests/test_project_bootstrap_skills.py`
- `tests/test_wrapper_contracts.py` (only if canonical/distributed frontmatter expectations need adjustment)

### Regenerated derived artifacts during implementation

- `.opencode/agents/*.md`
- `.claude/agents/*.md`
- `.cursor/agents/*.md`

## TDD-Aware Implementation Order

### Work package 1: shared config/helper layer

**Goal:** establish schema parsing, effective model resolution, frontmatter mutation, and normalized prompt comparison.

**Tests to add first**

1. `test_load_valid_model_profiles_config`
   - Verifies a valid config with defaults/profiles/agents loads successfully.
   - **Expected pre-implementation failure:** helper module/functions missing.
2. `test_rejects_invalid_schema_version`
   - Verifies `schema_version != 1` is rejected.
   - **Expected pre-implementation failure:** no validation path.
3. `test_resolves_agent_model_override_over_profile_model`
   - Verifies `agents.<name>.model` wins over profile model.
   - **Expected pre-implementation failure:** no resolver.
4. `test_resolves_variant_priority_agent_then_profile_then_defaults_then_medium`
   - Verifies the full variant fallback chain.
   - **Expected pre-implementation failure:** no resolver / wrong fallback.
5. `test_rejects_model_without_provider_prefix`
   - Verifies `provider/model` validation.
   - **Expected pre-implementation failure:** no validation.
6. `test_update_frontmatter_preserves_existing_fields_and_body`
   - Verifies `model` / `variant` insertion does not alter other frontmatter fields or markdown body.
   - **Expected pre-implementation failure:** no frontmatter update helper.
7. `test_normalized_prompt_compare_ignores_model_and_variant_only`
   - Verifies template drift comparison ignores only those two fields.
   - **Expected pre-implementation failure:** raw hash comparison still treats them as drift.

**Implementation step after failures are confirmed**

- Add `scripts/agent_config_lib.py` with target resolution, config load/validate, effective resolution, frontmatter update/insert, scan helpers, and normalized compare helpers.

### Work package 2: `install_agents.py` becomes template-sync only

**Goal:** sync canonical prompt + config template, but never render `model` / `variant`.

**Tests to write/update first**

1. `test_fresh_install_copies_agent_markdown_and_config_template`
   - Verifies first install creates markdown files plus `target/config/model-profiles.yaml`.
   - **Expected pre-implementation failure:** config template not copied.
2. `test_existing_target_config_is_preserved_on_reinstall`
   - Verifies target effective config is not overwritten.
   - **Expected pre-implementation failure:** no separate config-handling logic.
3. `test_install_does_not_inject_model_or_variant`
   - Verifies installed markdown contains no activation fields from install phase.
   - **Expected pre-implementation failure:** canonical files may still contain them or install copies activated content blindly.
4. `test_check_detects_prompt_drift_but_ignores_model_and_variant`
   - Verifies check mode ignores activation-managed fields while still failing for other frontmatter/body differences.
   - **Expected pre-implementation failure:** current check hashes full files.
5. `test_check_requires_target_config_to_exist`
   - Verifies template-sync check fails when effective config has never been initialized.
   - **Expected pre-implementation failure:** current check only looks at markdown.

**Implementation step after failures are confirmed**

- Refactor `scripts/install_agents.py` onto the shared helper, copy config template into `target/config/`, preserve existing target config, and change check mode to normalized content comparison.

### Work package 3: add `activate_agents_config.py`

**Goal:** render effective `model` / `variant` from target config into target markdown.

**Tests to add first**

1. `test_activation_injects_profile_model_and_default_variant`
   - Verifies profile model + default `variant: medium` are written.
   - **Expected pre-implementation failure:** script missing.
2. `test_activation_uses_profile_variant_override`
   - Verifies profile variant overrides defaults.
   - **Expected pre-implementation failure:** no profile-level override handling.
3. `test_activation_uses_agent_variant_override`
   - Verifies agent variant overrides profile/default.
   - **Expected pre-implementation failure:** no agent-level override handling.
4. `test_activation_uses_agent_model_override`
   - Verifies agent model override wins over profile.
   - **Expected pre-implementation failure:** no agent-level model override handling.
5. `test_activation_check_reports_drift_when_config_changes_without_rerender`
   - Verifies `--check` fails after editing target config but before rerender.
   - **Expected pre-implementation failure:** no activation drift checker.
6. `test_activation_can_insert_frontmatter_when_missing`
   - Verifies body-only markdown gets valid frontmatter inserted.
   - **Expected pre-implementation failure:** no insertion path.
7. `test_activation_rewrites_fields_after_template_sync_force`
   - Verifies activation restores `model` / `variant` after prompt overwrite.
   - **Expected pre-implementation failure:** no activation step.

**Implementation step after failures are confirmed**

- Implement `scripts/activate_agents_config.py` as a thin CLI over helper functions with `--target`, `--global`, `--check`, and `--dry-run`.

### Work package 4: add `setup_agents.py`

**Goal:** provide one user-facing script that composes install + activation and unified checks.

**Tests to add first**

1. `test_setup_runs_install_then_activation`
   - Verifies a single run produces both config file and activated frontmatter.
   - **Expected pre-implementation failure:** script missing.
2. `test_setup_check_fails_for_template_drift`
   - Verifies aggregated `--check` surfaces install drift.
   - **Expected pre-implementation failure:** no aggregate script.
3. `test_setup_check_fails_for_activation_drift`
   - Verifies aggregated `--check` surfaces activation drift separately.
   - **Expected pre-implementation failure:** no aggregate script.
4. `test_setup_dry_run_reports_actions_without_writing`
   - Verifies aggregate dry-run does not mutate files.
   - **Expected pre-implementation failure:** dry-run semantics missing.
5. `test_setup_force_reinstalls_prompt_then_reapplies_effective_model_fields`
   - Verifies final artifact keeps effective `model` / `variant` even after forced prompt sync.
   - **Expected pre-implementation failure:** no orchestration.

**Implementation step after failures are confirmed**

- Implement `scripts/setup_agents.py` as orchestration only. Prefer adding an activation-only refresh path or equivalent non-destructive behavior for config refreshes.

### Work package 5: natural-language/bootstrap integration and canonical cleanup

**Goal:** make user-facing guidance consistent with the new script model and remove canonical model coupling.

**Tests to add/update first**

1. `test_bootstrap_skill_mentions_agent_setup_step`
   - Verifies bootstrap documentation includes the agent setup step.
   - **Expected pre-implementation failure:** no such step yet.
2. `test_bootstrap_skill_routes_setup_through_setup_agents_script_only`
   - Verifies bootstrap does not parse YAML or edit frontmatter directly.
   - **Expected pre-implementation failure:** guidance absent.
3. `test_bootstrap_skill_mentions_restart_after_agent_refresh`
   - Verifies user guidance includes restart reminder.
   - **Expected pre-implementation failure:** refresh flow absent.
4. `test_canonical_agents_do_not_hardcode_model_or_variant`
   - Verifies canonical `agents/*.md` no longer contain those fields.
   - **Expected pre-implementation failure:** canonical files still contain them.

**Implementation step after failures are confirmed**

- Update bootstrap skill guidance, remove canonical `model` / `variant`, and regenerate project-level distributed agent copies through the existing distribution workflow.

## Focused Verification Strategy

Run focused tests incrementally after each work package, then run the combined regression slice at the end.

### Incremental commands

1. `python3 -m pytest tests/test_install_agents.py -v`
2. `python3 -m pytest tests/test_activate_agents_config.py -v`
3. `python3 -m pytest tests/test_setup_agents.py -v`
4. `python3 -m pytest tests/test_project_bootstrap_skills.py -v`
5. `python3 -m pytest tests/test_wrapper_contracts.py -v`

### Final focused regression

6. `python3 -m pytest tests/test_install_agents.py tests/test_activate_agents_config.py tests/test_setup_agents.py tests/test_project_bootstrap_skills.py tests/test_wrapper_contracts.py -v`

## EvalOps Candidates

These are not mandatory for the first implementation pass, but they are good future durable regression targets:

1. **Natural-language bootstrap request → correct script routing**
   - Example intent: “帮我 bootstrap 这个项目，启用 opencode agents”.
2. **Natural-language config refresh request → activation/setup path + restart reminder**
   - Example intent: “我改了 .opencode/agents/config/model-profiles.yaml，帮我刷新 agents”.
3. **Guardrail regression**
   - Ensure bootstrap guidance does not claim direct YAML parsing or direct frontmatter editing.

## Risks / Follow-ups

1. Decide whether `setup_agents.py` should expose an explicit `--activate-only` or equivalent refresh mode.
2. Confirm `.agent-install.json` stays an install artifact rather than becoming a full post-activation state ledger.
3. Future follow-up, outside this change: evaluate whether repeated real-world refresh requests justify a dedicated `sdlc-agent-config` skill. This is explicitly not part of the current implementation scope.

## Approval Request

Plan approved by the user. Proceed with implementation after spec-flow artifact generation/verification is completed, with these decisions fixed in scope:

- use a non-destructive refresh path for config-only changes;
- keep bootstrap initialization scope narrow; do not add `sdlc-agent-config` in this change; defer any dedicated refresh skill to a later focused change if real usage justifies it.
