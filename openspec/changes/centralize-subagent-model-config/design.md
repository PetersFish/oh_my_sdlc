## Context

The repository already distributes canonical agent prompts from `agents/` into target-specific derived copies under `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`. Today those prompts still carry some model coupling and the install path does not distinguish between prompt/template drift and effective per-target model configuration drift.

The approved scope is intentionally narrow:

- keep canonical prompts model-agnostic;
- add centralized per-agent model profile configuration;
- render effective `model` and `variant` only into target-side derived artifacts;
- preserve `sdlc-project-bootstrap` as an initialization-only skill;
- do not create a new `sdlc-agent-config` skill in this change.

This is a cross-cutting change because it touches canonical agent prompts, distribution scripts, derived target installs, bootstrap guidance, and focused tests.

## Goals / Non-Goals

**Goals:**

- Introduce a canonical `agents/config/model-profiles.yaml` template with fixed profiles and per-agent assignments.
- Make `install_agents.py` responsible only for template sync plus target config initialization/preservation.
- Add an activation step that resolves effective per-agent `model` and `variant` from target config and writes them into derived target markdown.
- Add an aggregate setup entry that composes install plus activation and exposes unified `--check`, `--dry-run`, and refresh-friendly behavior.
- Keep bootstrap guidance limited to initialization-time use of the script entrypoints.

**Non-Goals:**

- A runtime model resolver inside OpenCode or the agent loader.
- Provider capability fallback, category fallback, or dynamic runtime model negotiation.
- A new durable maintenance skill such as `sdlc-agent-config`.
- Expanding `sdlc-project-bootstrap` beyond initialization-time setup.
- Requiring users to hand-edit derived target agent markdown files.

## Decisions

### Decision 1: Split template sync from effective-config activation

`install_agents.py` will own canonical prompt/config distribution, while a new `activate_agents_config.py` will own rendering effective `model` and `variant` into target markdown. `setup_agents.py` will orchestrate both in order.

Rationale: config-only refreshes should not require destructive prompt reinstall, and drift checks must distinguish canonical prompt drift from activation-managed frontmatter drift.

Alternative considered: keep everything inside `install_agents.py`. Rejected because it blurs semantics, makes refresh heavier than necessary, and confuses drift reporting.

### Decision 2: Canonical prompts remain model-agnostic; target config becomes the source of truth

Canonical `agents/*.md` will not carry `model` or `variant`. The canonical template lives at `agents/config/model-profiles.yaml`, while each target keeps its own effective config under `<target>/config/model-profiles.yaml`.

Rationale: prompt content and model selection are different concerns, and each CLI target may legitimately diverge in model choice.

Alternative considered: keep `model` and `variant` in canonical agent frontmatter. Rejected because it couples prompt source to deployment config and prevents per-target overrides.

### Decision 3: Use one shared helper library for config resolution and frontmatter mutation

Introduce shared helper logic for target resolution, schema validation, effective model resolution, frontmatter update/insert, and normalized prompt comparison.

Rationale: install, activation, and aggregate setup all need the same parsing and mutation rules. Centralizing them reduces drift and makes focused tests reliable.

Alternative considered: duplicate small helpers inside each script. Rejected because the behavior would drift quickly across three entrypoints.

### Decision 4: Activation precedence is explicit and frontmatter insertion is supported

Model resolution order will be `agents.<name>.model` then `profiles.<profile>.model`. Variant resolution order will be `agents.<name>.variant`, then `profiles.<profile>.variant`, then `defaults.variant`, then implicit `medium`. Activation must preserve all non-managed frontmatter/body content and insert YAML frontmatter when a target file has none.

Rationale: the design needs deterministic overrides plus safe regeneration after template sync or local prompt edits.

Alternative considered: require every target file to already contain frontmatter. Rejected because template and target files may not always start in that shape.

### Decision 5: Install metadata remains about canonical sync, not activation state

Existing install metadata and drift semantics will continue to represent canonical template installation. Activation-managed `model` and `variant` fields are excluded from canonical prompt drift checks and validated separately by activation or aggregate check flows.

Rationale: once activation mutates target markdown, a raw whole-file hash no longer cleanly represents canonical install state.

Alternative considered: redefine install metadata as final target-file state. Rejected because it conflates two different sources of truth and makes config refreshes harder to reason about.

### Decision 6: Bootstrap stays initialization-only

`sdlc-project-bootstrap` documentation will describe initialization-time agent setup through `setup_agents.py`, and may mention rerunning the script after config changes, but it will not become a general maintenance skill and this change will not add `sdlc-agent-config`.

Rationale: the approved plan explicitly keeps skill taxonomy out of scope for this plumbing change.

Alternative considered: add a new skill or expand bootstrap into a refresh workflow now. Rejected because it broadens scope beyond the infrastructure needed for this change.

## Risks / Trade-offs

- Config schema or precedence confusion -> Mitigation: validate schema/version up front and cover precedence with focused tests.
- Activation mutates derived markdown after install -> Mitigation: separate normalized template-drift checks from activation-drift checks.
- Target configs could be accidentally overwritten on reinstall -> Mitigation: initialize missing target config from canonical template but preserve existing target config by default.
- Users may still force a prompt reinstall when they only changed config -> Mitigation: provide aggregate setup behavior and a non-destructive refresh-oriented path.
- Bootstrap wording could accidentally imply ongoing maintenance ownership -> Mitigation: keep docs explicit that bootstrap is initialization-only and route ongoing refreshes through scripts rather than new skill semantics.

## Migration Plan

1. Add the shared helper and canonical config template.
2. Remove canonical `model` / `variant` fields from `agents/*.md`.
3. Refactor `install_agents.py` to template-sync-only semantics and target config preservation.
4. Add `activate_agents_config.py` and `setup_agents.py`.
5. Update bootstrap guidance and regenerate derived agent copies through the existing distribution workflow.
6. Run focused tests for install, activation, setup, bootstrap guidance, and any wrapper-contract expectations affected by agent frontmatter drift rules.

Rollback is straightforward: remove the new config/render layer, restore canonical agent frontmatter fields if necessary, and return to the current install-only behavior.

## Open Questions

None for this change. A future separate change may decide whether repeated real-world refresh requests justify a dedicated maintenance skill.
